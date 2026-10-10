import os
from datetime import date, time, timedelta

os.environ["APP_CONFIG"] = "testing"  # must be set before the app module is imported

import pytest

import planning
import spic_copy
from app import app as flask_app
from extensions import db
from models import Interpreter, User


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


def meeting_form(days_ahead=3, **changes):
    data = {
        "title": "Reception", "date": (date.today() + timedelta(days=days_ahead)).isoformat(),
        "start": "10:00", "end": "11:30", "room": "R1", "interpreters_needed": "2", "category": "parliament",
    }
    data.update(changes)
    return data


# -- fixtures and factories for the tests of the rules (no requests: one app context) -------------

MONDAY = date(2030, 1, 7)  # a Monday far in the future, so nothing is "past"


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def user(ctx):
    planner = User(username="planner", name="Plan Ner")
    db.session.add(planner)
    db.session.flush()
    return planner


def make_interpreter(last="Peeters", bureau="", engagement="invoice", priority=None):
    count = Interpreter.query.count()
    interpreter = Interpreter(first_name="Test", last_name=last, email="{}{}@example.org".format(last.lower(), count),
                              bureau_affiliation=bureau, priority_order=priority or count + 1, engagement=engagement)
    db.session.add(interpreter)
    db.session.flush()
    return interpreter


def spic_item(number=1, day=MONDAY, start="14:00", end="16:00", **changes):
    """An item as spic reports a meeting (see spic_copy.py for the assumed shape)."""
    item = {
        "id": "m-{:08x}".format(number), "maandag": (day - timedelta(days=day.weekday())).isoformat(), "weekstatus": "definitief",
        "datum": day.isoformat(), "periode": "PM", "status": "gepland", "versie": 1, "start_soort": "uur",
        "start_uur": start, "effectief_begin": start, "verwacht_einde": end, "einde_volgende_dag": False,
        "zaal": "R1", "domein": "PARL", "assemblee": "FICT", "type": "commissie", "volgnummer": number,
        "volgnummer2": None,
    }
    item.update(changes)
    return item


def make_spic_meeting(number=1, change_number=None, **kwargs):
    meeting, _ = spic_copy.apply_item(spic_item(number, **kwargs), change_number)
    db.session.flush()
    return meeting


def make_booking(interpreter, day=MONDAY, start=time(13, 0), end=time(18, 0), positions=1, forfait=4, user=None,
                 confirm=True):
    slot = planning.get_or_create_slot(day, start, end)
    booking = planning.create_booking(interpreter, slot, positions, forfait, user)
    if confirm:
        planning.confirm_booking(booking, user)
    return booking
