import numpy as np
from uuid import uuid4, UUID
from datetime import datetime
import base64
import os
from collections import Counter
import magic
import logging
from flask_login import current_user
import clamd
from functools import wraps
from flask_wtf.csrf import validate_csrf, CSRFError

from geoalchemy2.elements import WKBElement
from shapely.wkt import loads
from shapely import wkb

from models import *

logger = logging.getLogger(__name__)

clamd_client = clamd.ClamdNetworkSocket(host='clamav', port=3310, timeout=3600)

def convert_value(val):
    """Convert non-serializable values to JSON-compatible format."""
    if isinstance(val, UUID):  # Convert UUID to string
        return str(val)
    elif isinstance(val, (np.integer, np.int64, np.int32)):  # Convert NumPy integers to Python int
        return int(val)
    elif isinstance(val, (np.floating, np.float64, np.float32)):  # Convert NumPy floats to Python float
        return float(val)
    elif isinstance(val, bytes):  # Convert bytes to string
        return val.decode("utf-8")
    elif isinstance(val, datetime):  # Convert datetime to string
        return val.isoformat()
    elif isinstance(val, WKBElement):  # Convert Geometry to WKT
        return loads(val.data).wkt if val.data else None  # Extract WKT if exists
    elif isinstance(val, list):
        return ", ".join(val)
    else:
        return val


def convert_record(record):
    """Apply conversion function to each value in a record."""
    return {k: convert_value(v) for k, v in record.items()}


def decode_geometry(geom_bytes):
    # Adjust hex parameter if your bytestring is hex encoded
    return wkb.loads(geom_bytes, hex=True) if isinstance(geom_bytes, str) else wkb.loads(geom_bytes)


def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024


def calculate_map_zoom_and_position(df):
    all_lons = []
    all_lats = []
    for poly in df['polygon'].dropna():
        lons, lats = poly.exterior.coords.xy
        all_lons.extend(lons)
        all_lats.extend(lats)

    # Compute bounding box
    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)

    # Calculate the center of the bounding box
    lon = (min_lon + max_lon) / 2
    lat = (min_lat + max_lat) / 2

    # A heuristic function to estimate the zoom level.
    # Note: This is a rough estimate and may need adjustment based on your data and map dimensions.
    # Determine the maximum extent
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    max_diff = max(lat_diff, lon_diff)

    # This heuristic works in many cases, but you might need to tune the thresholds
    if max_diff < 0.01:
        zoom = 15
    elif max_diff < 0.1:
        zoom = 12
    elif max_diff < 1:
        zoom = 10
    elif max_diff < 10:
        zoom = 6
    else:
        zoom = 3

    return lat, lon, zoom


def update_map_traces(df, current_figure):
    new_names = []
    for idx, row in df.iterrows():
        new_names.append(row['filename'] + ' | ' + str(row['uuid']))

    trace_names = []
    traces_to_remove = []
    for index, trace in enumerate(current_figure['data']):
        if 'hovertext' in trace:
            trace_name = trace['hovertext']
            if trace_name not in new_names:
                traces_to_remove.append(index)
            else:
                trace_names.append(trace_name)

    for i in traces_to_remove:
        current_figure['data'].pop(i)

    return trace_names, current_figure


def filter_df_list(df, column, value):
    return df[df[column].apply(
        lambda x: bool(set(x) & set(value))
        if isinstance(x, (list, set)) else False
    )]


def decode(contents):
    content_type, content_string = contents.split(',')
    return base64.b64decode(content_string)


def validate_extension(dict_extension, filename):
    if filename.endswith(('.html', '.js', '.htm', '.svg')):
        raise Exception("Filename extension not allowed")
    elif dict_extension == 'shp':
        if not filename.endswith('.zip'):
            raise Exception("Shapefiles must be uploaded as a .zip file")
    elif not filename.endswith("." + dict_extension):
        raise Exception("Filename extension not valid for this catalogue item")


def validate_shapefile_directory(dir_path):
    # List only files (ignore subdirectories)
    all_entries = os.listdir(dir_path)
    files = [f for f in all_entries if
             os.path.isfile(os.path.join(dir_path, f))]

    # Max‑8 check
    if len(files) > 8:
        raise ValueError(
            f"Directory contains {len(files)} files; maximum allowed is 8.")

    if any(f.endswith(('.html', '.js', '.htm', '.svg')) for f in files):
        raise ValueError(f"Extension not allowed")

    # Unique extensions check
    exts = [os.path.splitext(f)[1].lower() for f in files]
    dup_exts = [ext for ext, count in Counter(exts).items() if count > 1]
    if dup_exts:
        raise ValueError(
            f"Duplicate extensions found: {dup_exts}. Each file must have a unique extension.")

    # Required‑count check for the four target extensions
    required = {'.shp', '.shx', '.dbf', '.prj'}
    found = set(exts)
    missing = required - found
    if missing:
        raise ValueError(
            f"Missing required extension(s): {sorted(missing)}. Need at least one of each {sorted(required)}.")

    # All checks passed
    return True


def validate_mime(mime_type, io_decoded):
    logger.debug("validate_mime: initiating validation")
    mime = magic.Magic(mime=True)
    detected_type = mime.from_buffer(io_decoded.read(2048))
    if detected_type == "application/x-empty":
        raise Exception("MIME Type suggests this file is empty")
    elif detected_type == "image/svg+xml":
        raise Exception("MIME Type 'image/svg+xml' not allowed")
    elif detected_type != mime_type:
        raise Exception("MIME Type not valid for this catalogue item")
    return detected_type


def clamav_scanner(file):
    logger.debug("clamav_scan: initiating scan")
    file.seek(0)
    scan = clamd_client.instream(file)
    file.seek(0)
    verdict, _ = scan.get('stream', (None, None))
    if verdict == 'FOUND':
        logger.critical("upload_file: File rejected: malware detected")
        raise Exception("File rejected: malware detected")
    if verdict != 'OK':
        logger.error("upload_file: ClamAV Scanning error")
        raise Exception("Scanning error, try again")
    logger.info("upload_file: passed ClamAV check")


def csrf_protected(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = args[-1]
        try:
            validate_csrf(token)
            logger.debug(
                f"csrf_protected: CSRF token valid, user: {current_user.email}"
            )
        except Exception as e:
            logger.debug(
                f"csrf_protected: CSRF token not valid or other exception, user"
                f": {current_user.email}, exception: {e}"
            )
            return "File not uploaded - session expired or invalid. Please refresh the page."
        return func(*args, **kwargs)
    return wrapper