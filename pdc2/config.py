"""Configuration of PDC2, from the environment (a .env file is read too).

PDC2_CONFIG chooses "production" (default), "development" or "testing".
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("PDC2_SECRET_KEY") or None
    SQLALCHEMY_DATABASE_URI = os.environ.get("PDC2_DATABASE_URL") or "sqlite:////data/pdc2.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Identity from Authelia, as in PDC (auth.py). "dev" signs everyone in as PDC2_DEV_USER.
    PDC2_AUTH_MODE = os.environ.get("PDC2_AUTH_MODE", "authelia")
    PDC2_DEV_USER = os.environ.get("PDC2_DEV_USER", "developer")
    PDC2_DEV_NAME = os.environ.get("PDC2_DEV_NAME", "Developer")
    # Who may change data: Authelia user ids, separated by commas (decided 24 November 2026).
    PDC2_EDITORS = os.environ.get("PDC2_EDITORS", "")
    PDC2_LOGOUT_URL = os.environ.get("PDC2_LOGOUT_URL", "https://login.infracriv.net/logout")

    # Where the data of spic and the jaarkalender come from: "live" (their APIs) or "fake"
    # (realistic but fictitious data, pdc2/fake.py). Only the entry addresses are configured (HATEOAS).
    PDC2_SOURCE = os.environ.get("PDC2_SOURCE", "live")
    PDC2_SPIC_API = os.environ.get("PDC2_SPIC_API", "http://spic:8000/api/afnemers")
    PDC2_SPIC_TOKEN = os.environ.get("PDC2_SPIC_TOKEN", "")
    PDC2_JK_API = os.environ.get("PDC2_JK_API", "http://jaarkalender:8000/api/extern")
    PDC2_JK_TOKEN = os.environ.get("PDC2_JK_TOKEN", "")


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get("PDC2_SECRET_KEY") or "development-only-secret"
    SQLALCHEMY_DATABASE_URI = os.environ.get("PDC2_DATABASE_URL") or "sqlite:///pdc2_dev.db"
    PDC2_AUTH_MODE = os.environ.get("PDC2_AUTH_MODE", "dev")
    PDC2_EDITORS = os.environ.get("PDC2_EDITORS", Config.PDC2_DEV_USER)
    PDC2_SOURCE = os.environ.get("PDC2_SOURCE", "fake")


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    PDC2_AUTH_MODE = "authelia"
    PDC2_EDITORS = "planner,planner2"
    PDC2_SOURCE = "fake"


config = {"production": ProductionConfig, "development": DevelopmentConfig, "testing": TestingConfig}
