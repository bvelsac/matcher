"""Small helpers shared by the views: rights, form parsing and a uniform way to run a handling."""
from datetime import date, datetime, time, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from planning import PlanningError

BRUSSELS = ZoneInfo("Europe/Brussels")


def refuse(message, status):
    if request.is_json:
        return jsonify({"error": message}), status
    flash(message, "error")
    return redirect(url_for("dashboard"))


def editor_required(view):
    """Only editors change data. There is no editing lock (decided 10 October 2026):
    a form that is out of date is caught when it is saved (changed_since_loaded)."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_editor:
            return refuse("You do not have permission to change data.", 403)
        return view(*args, **kwargs)

    return wrapped


def changed_since_loaded(record):
    """True when someone saved the record after this form was loaded."""
    loaded = request.form.get("loaded_at", "")
    return bool(loaded) and record.updated_at is not None and record.updated_at.isoformat() != loaded


def safe_next(default):
    """Where to go after a handling: the address in `next` when it is on this site, else `default`."""
    target = request.form.get("next") or request.args.get("next") or ""
    return target if target.startswith("/") and not target.startswith("//") else default


def acting_user():
    """The signed-in user as a model object (not the proxy), for the log."""
    return current_user._get_current_object()


def begin_write():
    """Start a write transaction that checks the state as it is now. SQLite lets only one writer
    in at a time; asking for the write lock *before* the checks means that a second planner who
    handles the same position at the same moment waits, then sees what the first one did, and
    gets a clear message instead of a double assignment (functional analysis 9, point 3).
    What the session loaded earlier in the request is forgotten, so the checks read it again."""
    if db.engine.dialect.name == "sqlite":
        db.session.execute(db.text("BEGIN IMMEDIATE"))
    db.session.expire_all()


def attempt(action, success=None):
    """Run a handling in one transaction. A broken rule or a clash with a parallel handling is shown
    to the planner and nothing is kept. Returns True when it worked."""
    try:
        begin_write()
        action()
        db.session.commit()
    except PlanningError as error:
        db.session.rollback()
        flash(str(error), "error")
        return False
    except IntegrityError:
        db.session.rollback()
        flash("Someone else changed this at the same moment. Look at the current state and try again.", "error")
        return False
    if success:
        flash(success, "success")
    return True


# -- form parsing --------------------------------------------------------------------------------

def clean(field):
    return (request.form.get(field) or "").strip()


def form_date(field, label=None, required=True):
    value = clean(field)
    if not value and not required:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise PlanningError("Check the date{}.".format(" ({})".format(label) if label else ""))


def form_time(field, label=None, required=True):
    value = clean(field)
    if not value and not required:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise PlanningError("Check the time{}.".format(" ({})".format(label) if label else ""))


def form_int(field, label, minimum=None, required=True):
    value = clean(field)
    if not value and not required:
        return None
    try:
        number = int(value)
    except ValueError:
        raise PlanningError("{} must be a whole number.".format(label))
    if minimum is not None and number < minimum:
        raise PlanningError("{} must be at least {}.".format(label, minimum))
    return number


def form_datetime(field, label):
    """A date and time typed by the planner (Brussels time), stored as given: the hours worked."""
    value = clean(field)
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise PlanningError("Check the date and time of {}.".format(label))


# -- display -------------------------------------------------------------------------------------

def brussels(value, pattern="%Y-%m-%d %H:%M"):
    """A UTC time from the database in Brussels time (log entries are kept in UTC)."""
    if value is None:
        return ""
    return value.replace(tzinfo=timezone.utc).astimezone(BRUSSELS).strftime(pattern)


def hhmm(value):
    return value.strftime("%H:%M") if isinstance(value, time) else ""


def iso_date(value):
    return value.isoformat() if isinstance(value, date) else ""
