from sqlalchemy import func
from uuid import uuid4, UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from geoalchemy2 import Geometry
from passlib.hash import bcrypt
from flask_login import UserMixin

from extensions import db


class Objects(db.Model):
    __tablename__ = 'object_store_metadata'
    uuid = db.Column(PG_UUID(as_uuid=True), server_default=func.uuid_generate_v4(), nullable=False, primary_key=True)
    filename = db.Column(db.String(), nullable=False)
    model_domain = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=True)
    filename_extension = db.Column(db.String(), nullable=False)
    data_dict_uuid = db.Column(PG_UUID(as_uuid=True), default=uuid4, nullable=False)
    owner = db.Column(db.String(), nullable=False)
    gis = db.Column(db.Boolean, default=False)
    spatial_extents = db.Column(Geometry("GEOMETRY", srid=4326), nullable=True)
    size = db.Column(db.Integer, nullable=False)
    tags = db.Column(ARRAY(db.String), nullable=True)
    record_insert_time = db.Column(db.DateTime, default=func.now(), nullable=False)
    minio_filename = db.Column(db.String(), nullable=False)
    minio_bucket = db.Column(db.String(), nullable=False)
    status = db.Column(db.String(), nullable=False)
    deletion_time = db.Column(db.DateTime, nullable=True)
    clamav_scan = db.Column(db.String(), nullable=True)


class DataDict(db.Model):
    __tablename__ = 'model_data_dictionary'
    uuid = db.Column(PG_UUID(as_uuid=True), default=uuid4, nullable=False, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    model_domain = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    filename_extensions = db.Column(ARRAY(db.String), nullable=False)
    mime_types = db.Column(ARRAY(db.String), nullable=False)
    field_names = db.Column(ARRAY(db.String), nullable=False)
    field_types = db.Column(ARRAY(db.String), nullable=False)
    field_delimiter = db.Column(db.String(1), nullable=False)
    relation_type = db.Column(db.String(), nullable=False)
    produced_by = db.Column(ARRAY(db.String), nullable=False)
    ingested_by = db.Column(ARRAY(db.String), nullable=False)
    modified_by = db.Column(ARRAY(db.String), nullable=False)
    gis = db.Column(db.Boolean, default=False)
    reference_documentation = db.Column(db.String(), nullable=False)
    notes = db.Column(db.String(), nullable=False)
    record_insert_time = db.Column(db.DateTime, nullable=False)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def check_password(self, password):
        return bcrypt.verify(password, self.password_hash)


class Logins(db.Model):
    __tablename__ = 'user_logins'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    action = db.Column(db.String(), nullable=False)
    insert_time = db.Column(db.DateTime, default=func.now(), nullable=False)


class Downloads(db.Model):
    __tablename__ = 'user_object_downloads'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    insert_time = db.Column(db.DateTime, default=func.now(), nullable=False)
    file_uuids = db.Column(ARRAY(db.String), nullable=False)
    file_count = db.Column(db.Integer, nullable=False)
    minio_filenames = db.Column(db.String(), nullable=False)


class Uploads(db.Model):
    __tablename__ = 'user_object_uploads'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    insert_time = db.Column(db.DateTime, default=func.now(), nullable=False)
    minio_filename = db.Column(db.String(), nullable=False)
    size = db.Column(db.Integer, nullable=False)


class TaggedDeletes(db.Model):
    __tablename__ = 'user_tagged_deletes'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    insert_time = db.Column(db.DateTime, default=func.now(), nullable=False)
    file_uuids = db.Column(ARRAY(db.String), nullable=False)
    deletion_time = db.Column(db.DateTime, nullable=True)
    minio_filename = db.Column(db.String(), nullable=False)


class Tags(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    insert_time = db.Column(db.DateTime, default=func.now(), nullable=False)
    tag = db.Column(db.String(), nullable=False)


class OneTimeToken(db.Model):
    __tablename__ = 'one_time_tokens'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(PG_UUID(as_uuid=True), default=uuid4, nullable=False)
    purpose = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)