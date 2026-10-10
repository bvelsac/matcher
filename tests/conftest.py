import os

os.environ["APP_CONFIG"] = "testing"  # must be set before the app module is imported

import pytest

from app import app as flask_app
from extensions import db


@pytest.fixture
def app():
    # No app context stays pushed during requests: each request gets its own,
    # as in production (otherwise test clients would share Flask's `g`).
    with flask_app.app_context():
        db.create_all()
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, name=None):
    """Sign in as Authelia does: every request of this client carries Remote-User and
    Remote-Name. In the testing configuration "editor" and "editor2" may change data."""
    client.environ_base["HTTP_REMOTE_USER"] = username
    client.environ_base["HTTP_REMOTE_NAME"] = name or username.title()


def query(app, fn):
    """Run fn() inside an app context and return its result (for assertions)."""
    with app.app_context():
        return fn()
