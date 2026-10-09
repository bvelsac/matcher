"""Interpreter Mission Management System - Phase 1.

Users, interpreters (with priority order), meetings and the editing lock.
Run with `python app.py` for local development or `gunicorn app:app` in production.
"""
import os
from datetime import date, datetime
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from config import config
from extensions import csrf, db, login_manager
from models import CATEGORY_LABELS, MEETING_CATEGORIES, Interpreter, Meeting, SystemLock, User

LOCK_TYPE = "editing"

app = Flask(__name__)
app.config.from_object(config[os.environ.get("APP_CONFIG", "production")])
if not app.config.get("SECRET_KEY"):
    raise RuntimeError(
        "SECRET_KEY is not set. Put it in .env (see .env.example), "
        "or set APP_CONFIG=development for a local test setup."
    )

db.init_app(app)
csrf.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Editing lock and permissions
# ---------------------------------------------------------------------------

def current_lock():
    """Return the active editing lock, dropping it if it has expired."""
    lock = SystemLock.query.filter_by(lock_type=LOCK_TYPE).first()
    if lock and datetime.utcnow() - lock.created_at > app.config["SYSTEM_LOCK_TIMEOUT"]:
        db.session.delete(lock)
        db.session.commit()
        return None
    return lock


def _refuse(message, status):
    if request.is_json:
        return jsonify({"error": message}), status
    flash(message, "error")
    return redirect(url_for("dashboard"))


def editor_required(view):
    """Only editors, and only when no other editor holds the editing lock."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_editor:
            return _refuse("You do not have permission to change data.", 403)
        lock = current_lock()
        if lock and lock.locked_by_user_id != current_user.id:
            return _refuse(
                "The system is locked for editing by {} since {:%H:%M}.".format(
                    lock.locked_by_user.username, lock.created_at
                ),
                423,
            )
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    lock = None
    if current_user.is_authenticated:
        try:
            lock = current_lock()
        except Exception:  # never let the lock lookup break page rendering
            db.session.rollback()
    return {
        "today": date.today(),
        "system_lock": lock,
        "meeting_categories": MEETING_CATEGORIES,
    }


# ---------------------------------------------------------------------------
# Form helpers
# ---------------------------------------------------------------------------

def _clean(field):
    return (request.form.get(field) or "").strip()


def _interpreter_fields():
    return {
        "first_name": _clean("first_name"),
        "last_name": _clean("last_name"),
        "email": _clean("email").lower(),
        "phone": _clean("phone"),
        "bureau_affiliation": _clean("bureau_affiliation"),
        "additional_languages": _clean("additional_languages"),
        "notes": _clean("notes"),
    }


def _meeting_fields():
    """Parse and validate the meeting form. Raises ValueError with a readable message."""
    category = _clean("category")
    if category not in CATEGORY_LABELS:
        raise ValueError("Choose a category.")
    try:
        fields = {
            "name": _clean("name"),
            "date": datetime.strptime(_clean("date"), "%Y-%m-%d").date(),
            "time": datetime.strptime(_clean("time"), "%H:%M").time(),
            "estimated_duration": int(_clean("estimated_duration")),
            "interpreters_needed": int(_clean("interpreters_needed")),
            "location": _clean("location"),
            "category": category,
        }
    except ValueError:
        raise ValueError("Check the date, time, duration and number of interpreters.")
    if not fields["name"] or not fields["location"]:
        raise ValueError("Name and location are required.")
    if fields["estimated_duration"] < 1 or fields["interpreters_needed"] < 1:
        raise ValueError("Duration and number of interpreters must be at least 1.")
    return fields


def renumber_priorities():
    """Keep the priority order a continuous sequence 1..N."""
    ordered = Interpreter.query.order_by(Interpreter.priority_order, Interpreter.id).all()
    for position, interpreter in enumerate(ordered, start=1):
        interpreter.priority_order = position


# ---------------------------------------------------------------------------
# Authentication and dashboard
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(username=_clean("username")).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            login_user(user)
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    next_meetings = (
        Meeting.query.filter(Meeting.date >= date.today())
        .order_by(Meeting.date, Meeting.time)
        .limit(5)
        .all()
    )
    return render_template(
        "dashboard.html",
        next_meetings=next_meetings,
        total_interpreters=Interpreter.query.count(),
        upcoming_meetings=Meeting.query.filter(Meeting.date >= date.today()).count(),
    )


# ---------------------------------------------------------------------------
# Interpreters
# ---------------------------------------------------------------------------

@app.route("/interpreters")
@login_required
def interpreters():
    rows = Interpreter.query.order_by(Interpreter.priority_order).all()
    return render_template("interpreters/list.html", interpreters=rows)


@app.route("/interpreters/add", methods=["GET", "POST"])
@editor_required
def add_interpreter():
    if request.method == "POST":
        max_priority = db.session.query(db.func.max(Interpreter.priority_order)).scalar() or 0
        interpreter = Interpreter(priority_order=max_priority + 1, **_interpreter_fields())
        db.session.add(interpreter)
        try:
            db.session.commit()
            flash("Interpreter added.", "success")
            return redirect(url_for("interpreters"))
        except IntegrityError:
            db.session.rollback()
            flash("An interpreter with this email address already exists.", "error")
    return render_template("interpreters/add.html")


@app.route("/interpreters/<int:id>/edit", methods=["GET", "POST"])
@editor_required
def edit_interpreter(id):
    interpreter = db.get_or_404(Interpreter, id)
    if request.method == "POST":
        for field, value in _interpreter_fields().items():
            setattr(interpreter, field, value)
        try:
            db.session.commit()
            flash("Interpreter updated.", "success")
            return redirect(url_for("interpreters"))
        except IntegrityError:
            db.session.rollback()
            flash("Another interpreter already uses this email address.", "error")
            interpreter = db.get_or_404(Interpreter, id)
    return render_template("interpreters/edit.html", interpreter=interpreter)


@app.route("/interpreters/<int:id>/delete", methods=["POST"])
@editor_required
def delete_interpreter(id):
    interpreter = db.get_or_404(Interpreter, id)
    db.session.delete(interpreter)
    db.session.flush()
    renumber_priorities()
    db.session.commit()
    flash("Interpreter deleted. Priority order renumbered.", "success")
    return redirect(url_for("interpreters"))


@app.route("/interpreters/reorder", methods=["POST"])
@editor_required
def reorder_interpreters():
    order = (request.get_json(silent=True) or {}).get("order", [])
    try:
        order = [int(x) for x in order]
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid order data."}), 400

    by_id = {i.id: i for i in Interpreter.query.all()}
    if len(order) != len(set(order)) or set(order) != set(by_id):
        return jsonify({"error": "The order must list every interpreter exactly once."}), 400

    for position, interpreter_id in enumerate(order, start=1):
        by_id[interpreter_id].priority_order = position
    db.session.commit()
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------

@app.route("/meetings")
@login_required
def meetings():
    rows = Meeting.query.order_by(Meeting.date.desc(), Meeting.time.desc()).all()
    return render_template("meetings/list.html", meetings=rows)


@app.route("/meetings/add", methods=["GET", "POST"])
@editor_required
def add_meeting():
    if request.method == "POST":
        try:
            meeting = Meeting(created_by=current_user.id, **_meeting_fields())
        except ValueError as error:
            flash(str(error), "error")
            return render_template("meetings/add.html")
        db.session.add(meeting)
        db.session.commit()
        flash("Meeting added.", "success")
        return redirect(url_for("meetings"))
    return render_template("meetings/add.html")


@app.route("/meetings/<int:id>/edit", methods=["GET", "POST"])
@editor_required
def edit_meeting(id):
    meeting = db.get_or_404(Meeting, id)
    if request.method == "POST":
        try:
            fields = _meeting_fields()
        except ValueError as error:
            flash(str(error), "error")
            return render_template("meetings/edit.html", meeting=meeting)
        for field, value in fields.items():
            setattr(meeting, field, value)
        db.session.commit()
        flash("Meeting updated.", "success")
        return redirect(url_for("meetings"))
    return render_template("meetings/edit.html", meeting=meeting)


@app.route("/meetings/<int:id>/delete", methods=["POST"])
@editor_required
def delete_meeting(id):
    meeting = db.get_or_404(Meeting, id)
    db.session.delete(meeting)
    db.session.commit()
    flash("Meeting deleted.", "success")
    return redirect(url_for("meetings"))


# ---------------------------------------------------------------------------
# Editing lock
# ---------------------------------------------------------------------------

@app.route("/system/lock", methods=["POST"])
@login_required
def lock_system():
    if not current_user.is_editor:
        return jsonify({"error": "Permission denied."}), 403
    lock = current_lock()
    if lock:
        if lock.locked_by_user_id == current_user.id:
            return jsonify({"success": True})
        return jsonify({"error": "Already locked by {}.".format(lock.locked_by_user.username)}), 409
    db.session.add(SystemLock(locked_by_user_id=current_user.id, lock_type=LOCK_TYPE))
    try:
        db.session.commit()
    except IntegrityError:  # another editor took the lock at the same moment
        db.session.rollback()
        return jsonify({"error": "Another editor just locked the system."}), 409
    return jsonify({"success": True})


@app.route("/system/unlock", methods=["POST"])
@login_required
def unlock_system():
    lock = SystemLock.query.filter_by(
        lock_type=LOCK_TYPE, locked_by_user_id=current_user.id
    ).first()
    if not lock:
        return jsonify({"error": "You do not hold the lock."}), 404
    db.session.delete(lock)
    db.session.commit()
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
