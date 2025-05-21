import os
from datetime import timedelta, datetime
from dotenv import load_dotenv
import logging
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SESSION')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=20)

    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASS')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    logging.basicConfig(
        filename='logs/all.log', encoding='utf-8', level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_TIME_LIMIT = None

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE'))