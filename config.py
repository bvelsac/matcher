"""Application configuration.

Which configuration is used is chosen with the APP_CONFIG environment
variable: "production" (default, MySQL), "development" (SQLite file) or
"testing" (in-memory SQLite). Values can be set in a .env file.
"""
import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _mysql_uri():
    user = os.environ.get("MYSQL_USER", "interpreter_user")
    password = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))
    host = os.environ.get("MYSQL_HOST", "localhost")
    port = os.environ.get("MYSQL_PORT", "3306")
    database = os.environ.get("MYSQL_DATABASE", "interpreter_system")
    return "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4".format(
        user, password, host, port, database
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or None  # required in production, see app.py

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or _mysql_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280, "pool_pre_ping": True}

    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    # An editing lock that is not released is dropped automatically after this time.
    SYSTEM_LOCK_TIMEOUT = timedelta(
        hours=int(os.environ.get("SYSTEM_LOCK_TIMEOUT_HOURS", "4"))
    )


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY") or "development-only-secret"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or "sqlite:///interpreter_system_dev.db"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {}


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False


config = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
