"""Application configuration.

Which configuration is used is chosen with the APP_CONFIG environment
variable: "production" (default), "development" or "testing". Values can be
set in a .env file.

The database is SQLite (decided 10 October 2026): one file, in WAL mode, like
spic. In production it lives at /data/pdc.db, on the volume of the container.

People are identified by Authelia (functional analysis 9, point 3): Caddy
passes the headers Remote-User and Remote-Name after Authelia has checked the
login. See auth.py.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or None  # required in production, see app.py

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:////data/pdc.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # "authelia" (trust the headers Caddy passes on) or "dev" (a fixed user, for development)
    PDC_AUTH_MODE = os.environ.get("PDC_AUTH_MODE", "authelia")
    PDC_DEV_USER = os.environ.get("PDC_DEV_USER", "developer")
    PDC_DEV_NAME = os.environ.get("PDC_DEV_NAME", "Developer")
    # User ids (Authelia) that may change data. Interim, until spic gives PDC its list of
    # invoerders and beheerders (functional analysis 9, point 3); everyone else can only read.
    PDC_EDITORS = os.environ.get("PDC_EDITORS", "")
    PDC_LOGOUT_URL = os.environ.get("PDC_LOGOUT_URL", "https://login.infracriv.net/logout")


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY") or "development-only-secret"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///pdc_dev.db"
    PDC_AUTH_MODE = os.environ.get("PDC_AUTH_MODE", "dev")
    PDC_EDITORS = os.environ.get("PDC_EDITORS", Config.PDC_DEV_USER)


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    PDC_AUTH_MODE = "authelia"
    PDC_EDITORS = "editor,editor2"


config = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
