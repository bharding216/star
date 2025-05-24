import os
from datetime import timedelta
import typing as t
from dotenv import load_dotenv
from project.enums.app_mode import AppMode
import logging

load_dotenv()

class Config:
    # General settings
    SECRET_KEY: str = os.getenv('secret_key', '')  # Used to encrypt session cookie
    SECRET_ADMIN_CODE: str = os.getenv('secret_admin_code', '')
    APP_MODE: str = os.getenv('APP_MODE', AppMode.PROD.value)
    acceptable_status_codes: list[int] = [200, 301, 302]

    EMAILS_TO_RECEIVE_ALERTS: tuple[str, ...] = (
        'brandon@getsurmount.com',
    )  # tuple to ensure immutability

    SURMOUNT_GENERAL_EMAIL: str = 'hello@stxresources.org'

    PROD_LOGGING_LEVEL: str = 'WARNING' 

    # Database settings
    SQLALCHEMY_POOL_SIZE: int = 5
    SQLALCHEMY_POOL_RECYCLE: int = 450
    SQLALCHEMY_MAX_OVERFLOW: int = 2
    SQLALCHEMY_POOL_TIMEOUT: int = 20
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        'pool_pre_ping': True,  # Enable connection pool pre-ping
    }

    # Session settings
    SESSION_TYPE: str = 'filesystem'
    SESSION_PERMANENT: bool = True
    SESSION_PROTECTION: str = 'strong'
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(days=180)
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    SESSION_COOKIE_NAME: str = 'surmount_session_cookie'
    TIMEOUT: int = 300

    # Image settings
    ALLOWED_IMAGE_EXTENSIONS: set[str] = {'png', 'jpg', 'jpeg', 'gif'}
    ALLOWED_ATTACHMENT_EXTENSIONS: set[str] = {
        'pdf', 'png', 'jpg', 
        'jpeg', 'doc', 'docx', 
        'xls', 'xlsx', 'txt'
    }
    MAX_HEADSHOT_IMAGE_BYTES: int = 2 * 1024 * 1024  # 2 MB
    MAX_HEADSHOT_IMAGE_WIDTH: int = 240
    MAX_HEADSHOT_IMAGE_HEIGHT: int = 240
    MAX_FILENAME_LENGTH: int = 100
    MAX_PHOTOS_PER_MESSAGE: int = 3
    MAX_MB_PER_MMS: int = 5
    MAX_FILE_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB