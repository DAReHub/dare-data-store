from models import *
from extensions import db
import logging
from flask import current_app
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer

logger = logging.getLogger(__name__)

def record_pg_logins(action, email):
    logger.debug(f"record_pg_logins, user: {email}, action: {action}")
    record = Logins(
        email=email,
        action=action
    )
    db.session.add(record)
    db.session.commit()


def record_pg_downloads(email, file_uuids, file_count, filenames):
    logger.debug(f"record_pg_downloads, user: {email}")
    record = Downloads(
        email=email,
        file_uuids=file_uuids,
        file_count=file_count,
        minio_filenames=filenames
    )
    db.session.add(record)
    db.session.commit()


def record_pg_uploads(email, filename, size):
    logger.debug(f"record_pg_uploads, user: {email}, filename: {filename}")
    record = Uploads(
        email=email,
        minio_filename=filename,
        size=size
    )
    db.session.add(record)
    db.session.commit()


def record_pg_deletes(email, file_uuids, time, filename):
    logger.debug(f"record_pg_deletes, user: {email}, filename: {filename}, file UUIDs: {file_uuids}")
    record = TaggedDeletes(
        email=email,
        file_uuids=file_uuids,
        deletion_time=time,
        minio_filename=filename
    )
    db.session.add(record)
    db.session.commit()


def update_object_status(file_uuid, status, time):
    logger.debug(f"update_object_status, file UUID: {file_uuid}")
    item = db.session.query(Objects).filter_by(uuid=file_uuid).first()
    if item:
        item.status = status
        item.deletion_time = time
        db.session.commit()


def add_tag(email, tag):
    logger.debug(f"add_tag, user: {email}, tag: {tag}")
    record = Tags(
        email=email,
        tag=tag
    )
    db.session.add(record)
    db.session.commit()


def generate_one_time_token(purpose: str, files, max_age: int = 300):
    uuid = str(uuid4())
    now = datetime.utcnow()
    otp = OneTimeToken(
        uuid=uuid,
        purpose=purpose,
        created_at=now,
        expires_at=now + timedelta(seconds=max_age),
        used=False
    )
    db.session.add(otp)
    db.session.commit()
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps({'uuid': uuid, 'purpose': purpose, 'files': files})
    return token