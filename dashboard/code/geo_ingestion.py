import geopandas as gpd
from shapely.geometry import box
from pyproj import Transformer, CRS
import tempfile
import zipfile
import os
import glob

import utils

def geopackage(filepath, crs=4326):
    print(filepath)
    gdf = gpd.read_file(filepath)

    minx, miny, maxx, maxy = gdf.total_bounds
    print("Spatial extents in source CRS:", (minx, miny, maxx, maxy))

    src_crs = gdf.crs
    if src_crs is None:
        raise ValueError("No CRS found in the GeoPackage. Please define the source CRS.")
    else:
        print("source CRS:", src_crs)

    target_crs = CRS.from_epsg(crs)

    # Create a transformer from the source CRS to target CRS
    transformer = Transformer.from_crs(src_crs, target_crs, always_xy=True)

    # Transform the lower-left and upper-right corners
    bl_x, bl_y = transformer.transform(minx, miny)
    tr_x, tr_y = transformer.transform(maxx, maxy)
    print("Transformed spatial extents:", (bl_x, bl_y, tr_x, tr_y))

    # Create a polygon (bounding box) from the original bounds
    original_polygon = box(minx, miny, maxx, maxy)

    # Reproject the polygon to the target CRS using GeoPandas' to_crs
    gdf_proj = gdf.to_crs(epsg=crs)
    projected_polygon = box(*gdf_proj.total_bounds)
    print("WKT:", projected_polygon.wkt)

    return projected_polygon.wkt


def shapefile(path_or_dir, filepath, crs=4326):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(path_or_dir, 'r') as z:
            z.extractall(tmpdir)

        path = tmpdir + '/' + filepath.replace(".zip", "")

        # Directory → find .shp inside
        if os.path.isdir(path):
            shp_list = glob.glob(os.path.join(path, '*.shp'))
            if not shp_list:
                raise ValueError(f"No .shp found in directory {path}")

        if not utils.validate_shapefile_directory(path):
            raise ValueError("Shapefile directory not valid")

        gdf = gpd.read_file(shp_list[0])

        # Compute original bounds
        minx, miny, maxx, maxy = gdf.total_bounds
        src_crs = gdf.crs
        if src_crs is None:
            raise ValueError("No CRS found on shapefile; include a .prj or set CRS manually.")

        # Reproject bounds manually
        transformer = Transformer.from_crs(src_crs, CRS.from_epsg(crs), always_xy=True)  # :contentReference[oaicite:1]{index=1}
        bl_x, bl_y = transformer.transform(minx, miny)
        tr_x, tr_y = transformer.transform(maxx, maxy)

        # Also build polygon via to_crs
        gdf_proj = gdf.to_crs(epsg=crs)
        projected_polygon = box(*gdf_proj.total_bounds)
        return projected_polygon.wkt


def main(filepath, decoded, crs=4326):
    suffix = "." + filepath.split(".")[-1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(decoded)
        tmp.flush()  # Ensure all data is written
        tmp_filename = tmp.name  # Store filename for reading

    if filepath.endswith('.gpkg'):
        extents = geopackage(tmp_filename)
        tmp.close()
        return extents
    elif filepath.endswith('.zip'):
        extents = shapefile(tmp_filename, filepath)
        tmp.close()
        return extents
    else:
        tmp.close()
        raise ValueError("Not a valid extension")

