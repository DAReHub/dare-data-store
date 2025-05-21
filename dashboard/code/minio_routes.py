from flask import Blueprint, Response, stream_with_context, abort, request, jsonify, current_app
from flask_login import login_required
from minio import Minio
import urllib3
import zipstream
from minio.commonconfig import Tags as minio_tags
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv
import logging
from datetime import datetime

from models import *

load_dotenv()

minio_bp = Blueprint('minioroutes', __name__)

http_client = urllib3.PoolManager(cert_reqs='CERT_NONE')
minio_client = Minio(
    f"{os.getenv('MINIO_HOST')}:{os.getenv('MINIO_PORT')}",
    access_key=os.getenv('MINIO_USER'),
    secret_key=os.getenv('MINIO_PASS'),
    http_client=http_client,
    secure=True
)
MODEL_BUCKET = os.getenv('MINIO_MODEL_BUCKET')
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE'))

logger = logging.getLogger(__name__)

def verify_token(token, files):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = s.loads(token, max_age=300)
    except SignatureExpired:
        logger.warning('verify_token: abort - signature expired')
        abort(403, description="Token expired. Please refresh the page and try again.")
    except BadSignature:
        logger.warning('verify_token: abort - bad signature')
        abort(403, description="Invalid token. Request not authorized.")
    if data.get('files') != files:
        logger.warning(f"verify_token: abort - token data does not match request parameters: files: {files}, data: {data.get('files')}")
        abort(403, description="Token data does not match the request parameters.")
    else:
        logger.info("verify_token: token data valid")

def verify_one_time_token(token: str, expected_purpose: str, files, max_age: int=300):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token, max_age=max_age)
    except SignatureExpired:
        logger.warning('verify_one_time_token: abort - signature expired')
        abort(403, description='Token expired.')
    except BadSignature:
        logger.warning('verify_one_time_token: abort - bad signature')
        abort(403, description='Invalid token.')

    uuid = data.get('uuid')
    purpose = data.get('purpose')

    if purpose != expected_purpose:
        logger.warning('verify_one_time_token: abort - not the correct purpose')
        abort(403, description='Token purpose mismatch.')

    if data.get('files') != files:
        logger.warning(f"verify_one_time_token: abort - token data does not match request parameters: files: {files}, data: {data.get('files')}")
        abort(403, description="Token data does not match the request parameters.")

    otp = OneTimeToken.query.filter_by(uuid=uuid, purpose=purpose).first()
    if not otp or otp.used or datetime.utcnow() > otp.expires_at:
        logger.warning('verify_one_time_token: abort - database token has already been used or does not exist')
        abort(403, description='Token already used or expired.')

    # Mark as used (or delete) to prevent replay
    otp.used = True
    db.session.commit()

    logger.info("verify_one_time_token: token data valid")
    return True


@minio_bp.route("/download_file", methods=['GET'])
@login_required
def download_file():
    logger.debug("download_file: route accessed")

    bucket_name = request.args.get('bucket')
    object_name = request.args.get('object')
    token = request.args.get('token')

    if not (bucket_name and object_name and token):
        logger.info("download_file: abort - one or multiple of bucket, object, or token not present")
        abort(404)

    files = bucket_name + '/' + object_name
    verify_one_time_token(token, 'download_file', files)

    try:
        response = minio_client.get_object(bucket_name, object_name)
        logger.info(f"download_file: get_object successful, bucket: {bucket_name}, object: {object_name}")
    except Exception as e:
        logger.error(f"download_file get_object exception, bucket: {bucket_name}, object: {object_name}, exception {e}")
        abort(404)

    # Generator to stream file chunks
    def generate():
        try:
            for chunk in response.stream(8192):
                yield chunk
        except Exception as e:
            logger.error(f"download_file generate chunk exception: {e}")
        finally:
            response.close()
            response.release_conn()

    filename = object_name.split('/')[-1]

    return Response(
        stream_with_context(generate()),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        mimetype="application/octet-stream"
    )


@minio_bp.route('/download_zip', methods=['GET'])
@login_required
def download_zip():
    logger.debug("download_zip: route accessed")

    # Assume you pass a comma-separated list of file keys via query parameter 'files'
    files = request.args.get('files', '')
    file_list = files.split(',') if files else []
    token = request.args.get('token')

    if not file_list:
        logger.info("download_zip: abort - no list of files")
        return "No files specified", 400

    verify_one_time_token(token, 'download_zip', files)

    # Create a streaming zip file
    z = zipstream.ZipFile(mode='w', compression=zipstream.ZIP_DEFLATED)

    for file_key in file_list:
        bucket = file_key.split('/')[0]
        filename = file_key.replace(bucket + '/', "")
        try:
            response = minio_client.get_object(bucket, filename)
            logger.info(f"download_zip: get_object successful, bucket: {bucket}, object: {filename}")
        except Exception as e:
            logger.error(f"download_zip get_object exception, bucket: {bucket}, object: {filename}, exception {e}")
            return f"Error retrieving {filename}: {str(e)}", 404

        # Define a generator to stream the file content in chunks
        def file_generator(resp):
            try:
                for chunk in resp.stream(8192):
                    yield chunk
            except Exception as e:
                logger.error(f"download_file generate chunk exception: {e}")
            finally:
                resp.close()
                resp.release_conn()

        uuid_and_filename = '/'.join(filename.split('/')[-2:])
        z.write_iter(uuid_and_filename, file_generator(response))

    # Stream the zip file as the response
    response = Response(z, mimetype='application/zip')
    response.headers['Content-Disposition'] = 'attachment; filename=files.zip'
    return response


@login_required
def upload_file(filename, io_decoded, mime):
    logger.debug("upload_file_to_minio: called")
    io_decoded.seek(0, os.SEEK_END)
    file_size = io_decoded.tell()
    if file_size > MAX_UPLOAD_SIZE:
        logger.info(
            f"upload_file_to_minio: abort – file too large ({file_size} bytes)"
        )
        raise ValueError(
            f"File too large: {file_size} bytes exceeds maximum {MAX_UPLOAD_SIZE}"
        )
    io_decoded.seek(0)
    minio_client.put_object(
        bucket_name=MODEL_BUCKET,
        object_name=filename,
        data=io_decoded,
        length=file_size,
        content_type=mime
    )


@login_required
def minio_tag(bucket_name, object_name, tag_key, tag_value):
    logger.debug("minio_tag: route accessed")
    tags = minio_tags.new_object_tags()
    tags[tag_key] = tag_value
    minio_client.set_object_tags(bucket_name, object_name, tags)


@login_required
def check_file_exists(bucket, filename):
    logger.debug("check_file_exists: route accessed")
    minio_client.stat_object(bucket, filename)