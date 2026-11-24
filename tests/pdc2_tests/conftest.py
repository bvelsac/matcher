"""Fixtures for PDC2: its own app and in-memory database, with spic and the jaarkalender simulated."""
import pytest

from pdc2 import create_app
from pdc2.extensions import db as pdc2_db


@pytest.fixture
def pdc2_app():
    app = create_app("testing")
    with app.app_context():
        pdc2_db.create_all()
    yield app
    with app.app_context():
        pdc2_db.session.remove()
        pdc2_db.drop_all()


def sign_in(client, username, name=None):
    """As Authelia: every request carries Remote-User and Remote-Name. "planner" and "planner2" may edit."""
    client.environ_base["HTTP_REMOTE_USER"] = username
    client.environ_base["HTTP_REMOTE_NAME"] = name or username.title()
    return client


@pytest.fixture
def planner(pdc2_app):
    return sign_in(pdc2_app.test_client(), "planner", "Plan Ner")


def run(app, fn):
    with app.app_context():
        return fn()
