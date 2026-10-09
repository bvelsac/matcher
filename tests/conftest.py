import os

os.environ["APP_CONFIG"] = "testing"  # must be set before the app module is imported

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from extensions import db
from models import User


@pytest.fixture
def app():
    # No app context stays pushed during requests: each request gets its own,
    # as in production (otherwise test clients would share Flask's `g`).
    with flask_app.app_context():
        db.create_all()
        for username, role in (("editor", "editor"), ("editor2", "editor"), ("viewer", "viewer")):
            db.session.add(User(
                username=username,
                email="{}@example.org".format(username),
                role=role,
                password_hash=generate_password_hash("password123"),
            ))
        db.session.commit()
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username):
    return client.post("/login", data={"username": username, "password": "password123"})


def query(app, fn):
    """Run fn() inside an app context and return its result (for assertions)."""
    with app.app_context():
        return fn()
