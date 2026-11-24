"""Small helpers for the views of PDC2: rights, one transaction per handling, dates, display."""
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo

from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from pdc2.extensions import db
from pdc2.models import ROLE_LABELS
from pdc2.rules import RuleError

BRUSSELS = ZoneInfo("Europe/Brussels")
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def is_htmx():
    return request.headers.get("HX-Request") == "true"


def editor_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_editor:
            if is_htmx():
                return "You may not change data.", 403
            flash("You may not change data.", "error")
            return redirect(url_for("pdc2.index"))
        return view(*args, **kwargs)
    return wrapped


def acting_user():
    return current_user._get_current_object()


def attempt(action):
    """Run a handling in one transaction; returns (result, error message or None)."""
    try:
        if db.engine.dialect.name == "sqlite":
            db.session.execute(db.text("BEGIN IMMEDIATE"))
        result = action()
        db.session.commit()
        return result, None
    except RuleError as error:
        db.session.rollback()
        return None, str(error)
    except IntegrityError:
        db.session.rollback()
        return None, "Someone else changed this at the same moment. Reload and try again."


def monday_of(day):
    return day - timedelta(days=day.weekday())


def parse_date(value):
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        raise RuleError("Check the date.")


def brussels(value, pattern="%Y-%m-%d %H:%M"):
    if value is None:
        return ""
    return value.replace(tzinfo=timezone.utc).astimezone(BRUSSELS).strftime(pattern)


def hours(value):
    """Hours to one decimal: 3.54 -> "3.5", 4.0 -> "4"."""
    return ("%.1f" % value).rstrip("0").rstrip(".") if value else "0"


def register_helpers(app):
    app.add_template_filter(brussels, "brussels")
    app.add_template_filter(hours, "hours")
    app.add_template_filter(lambda d: "{} {}".format(DAY_NAMES[d.weekday()], d.strftime("%d/%m")), "dayname")
    app.add_template_filter(lambda r: ROLE_LABELS.get(r, r), "role")
    app.jinja_env.globals["now"] = datetime.now
    app.jinja_env.globals["delta7"] = timedelta(days=7)
