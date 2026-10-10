"""PDC - Prestatiedatabank voor Conferentietolken.

The planner's tool: interpreters with the legal priority order, meetings (the copy of spic and
own meetings), bookings, assignments, invoices and the work lists, behind Authelia (auth.py).
Run with `python app.py` for local development or `gunicorn app:app` in production.
"""
import os
from datetime import date

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

import planning
from config import config
from extensions import csrf, db, login_manager
from helpers import (
    acting_user, attempt, brussels, changed_since_loaded, clean, editor_required, form_date, form_int,
    form_time, hhmm, safe_next,
)
from models import (
    CATEGORY_LABELS, ENGAGEMENT_LABELS, MEETING_CATEGORIES,
    AssignmentLog, Booking, BookingPosition, Interpreter, Invoice, Meeting, MeetingAssignment, MeetingChange,
    Room, SyncState, UserVisit, utcnow,
)
from planning import PlanningError

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

import auth  # noqa: E402,F401  (registers the request loader)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    """WAL lets the web workers and later the background task read while one writes;
    foreign keys are off by default in SQLite; wait instead of failing when locked."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()


@login_manager.unauthorized_handler
def not_signed_in():
    """Without Authelia's headers nobody gets in. Behind Caddy this does not happen."""
    if request.is_json:
        return jsonify({"error": "Not signed in."}), 401
    return render_template("errors/401.html"), 401


app.add_template_filter(brussels, "brussels")
app.add_template_filter(hhmm, "hhmm")
app.add_template_global(planning.position_overtime, "planning_overtime")


@app.context_processor
def inject_globals():
    return {
        "today": date.today(),
        "meeting_categories": MEETING_CATEGORIES,
        "engagement_labels": ENGAGEMENT_LABELS,
        "logout_url": app.config["PDC_LOGOUT_URL"],
        "sync": db.session.get(SyncState, 1) if current_user.is_authenticated else None,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    upcoming = (Meeting.query.filter(Meeting.visible_filter(), Meeting.status == "planned", Meeting.date >= date.today())
                .order_by(Meeting.date, Meeting.period, Meeting.effective_start).all())
    needing = [m for m in upcoming if m.interpreters_needed and m.staffing_count < m.interpreters_needed]
    return render_template(
        "dashboard.html",
        next_meetings=upcoming[:5],
        total_interpreters=Interpreter.query.count(),
        upcoming_meetings=len(upcoming),
        meetings_needing=len(needing),
        counts=planning.worklist_counts(),
    )


# ---------------------------------------------------------------------------
# Interpreters
# ---------------------------------------------------------------------------

def _interpreter_fields():
    engagement = clean("engagement") or "invoice"
    if engagement not in ENGAGEMENT_LABELS:
        raise PlanningError("Choose how the interpreter works.")
    return {
        "first_name": clean("first_name"),
        "last_name": clean("last_name"),
        "email": clean("email").lower(),
        "phone": clean("phone"),
        "bureau_affiliation": clean("bureau_affiliation"),
        "additional_languages": clean("additional_languages"),
        "notes": clean("notes"),
        "engagement": engagement,
    }


def renumber_priorities():
    """Keep the priority order a continuous sequence 1..N."""
    ordered = Interpreter.query.order_by(Interpreter.priority_order, Interpreter.id).all()
    for position, interpreter in enumerate(ordered, start=1):
        interpreter.priority_order = position


@app.route("/interpreters")
@login_required
def interpreters():
    rows = Interpreter.query.order_by(Interpreter.priority_order).all()
    return render_template("interpreters/list.html", interpreters=rows)


@app.route("/interpreters/add", methods=["GET", "POST"])
@editor_required
def add_interpreter():
    if request.method == "POST":
        try:
            fields = _interpreter_fields()
        except PlanningError as error:
            flash(str(error), "error")
            return render_template("interpreters/add.html")
        max_priority = db.session.query(db.func.max(Interpreter.priority_order)).scalar() or 0
        db.session.add(Interpreter(priority_order=max_priority + 1, **fields))
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
        if changed_since_loaded(interpreter):
            flash("Someone else changed this interpreter while you were editing. "
                  "These are the current details; enter your changes again.", "error")
            return render_template("interpreters/edit.html", interpreter=interpreter)
        try:
            fields = _interpreter_fields()
        except PlanningError as error:
            flash(str(error), "error")
            return render_template("interpreters/edit.html", interpreter=interpreter)
        for field, value in fields.items():
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
    if Booking.query.filter_by(interpreter_id=id).first() or Invoice.query.filter_by(interpreter_id=id).first():
        flash("This interpreter has bookings or invoices and cannot be deleted; the history stays.", "error")
        return redirect(url_for("interpreters"))
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

def _hhmm_or_empty(value):
    return value.strftime("%H:%M") if value else ""


def meeting_values(meeting):
    """The values of the meeting form for a meeting that is being edited."""
    return {
        "title": meeting.title or "", "date": meeting.date.isoformat(),
        "start": _hhmm_or_empty(meeting.effective_start), "end": _hhmm_or_empty(meeting.expected_end),
        "room": meeting.room or "", "interpreters_needed": meeting.interpreters_needed or "",
        "category": meeting.category or "", "notes": meeting.notes or "",
        "actual_end": _hhmm_or_empty(meeting.actual_end),
        "charged_half_hours": "" if meeting.charged_half_hours is None else meeting.charged_half_hours,
    }


def _pdc_fields(require_category):
    """The fields PDC keeps for every meeting, also those from spic."""
    category = clean("category") or None
    if category is not None and category not in CATEGORY_LABELS:
        raise PlanningError("Choose a category.")
    if category is None and require_category:
        raise PlanningError("Choose a category.")
    return {
        "interpreters_needed": form_int("interpreters_needed", "The number of interpreters", minimum=1),
        "category": category,
        "notes": clean("notes") or None,
        "actual_end": form_time("actual_end", "real end", required=False),
        "charged_half_hours": form_int("charged_half_hours", "The charged half hours", minimum=0, required=False),
    }


def _own_meeting_fields():
    """Parse and validate the form of an own meeting (1.5, BR-MTG-001)."""
    title = clean("title")
    room = clean("room")
    if not title or not room:
        raise PlanningError("Title and room are required.")
    known_rooms = {r.code for r in Room.query.all()}
    if known_rooms and room not in known_rooms:
        raise PlanningError("Choose a room from the list of spic.")
    start = form_time("start", "start")
    end = form_time("end", "end", required=False)
    duration = clean("duration_hours")
    if end is None and duration:
        try:
            minutes = round(float(duration.replace(",", ".")) * 60)
        except ValueError:
            raise PlanningError("Check the duration.")
        total = start.hour * 60 + start.minute + minutes
        if minutes <= 0 or total >= 24 * 60:
            raise PlanningError("The meeting must end the same day, after it starts.")
        end = start.replace(hour=total // 60, minute=total % 60)
    if end is None:
        raise PlanningError("Fill in the end or the duration.")
    if not end > start:
        raise PlanningError("The end must be after the start.")
    fields = _pdc_fields(require_category=True)
    fields.update(
        title=title, date=form_date("date"), period="AM" if start.hour < 12 else "PM",
        effective_start=start, expected_end=end, end_next_day=False, room=room,
    )
    return fields


def _meeting_page(meeting, **extra):
    template = "meetings/edit.html" if meeting else "meetings/add.html"
    return render_template(template, meeting=meeting, rooms=Room.query.order_by(Room.code).all(), **extra)


@app.route("/meetings")
@login_required
def meetings():
    when = request.args.get("when", "upcoming")
    origin = request.args.get("origin", "")
    text = (request.args.get("q") or "").strip()
    show_deleted = request.args.get("deleted") == "1"

    query = Meeting.query.filter(Meeting.visible_filter())
    if when == "upcoming":
        query = query.filter(Meeting.date >= date.today())
    elif when == "past":
        query = query.filter(Meeting.date < date.today())
    if origin in ("spic", "own"):
        query = query.filter(Meeting.origin == origin)
    if not show_deleted:
        query = query.filter(Meeting.status != "deleted")
    if text:
        like = "%{}%".format(text)
        query = query.filter(db.or_(Meeting.title.ilike(like), Meeting.domain.ilike(like), Meeting.assembly.ilike(like),
                                    Meeting.type.ilike(like), Meeting.room.ilike(like), Meeting.spic_id.ilike(like)))
    descending = when == "past"
    order = (Meeting.date.desc(), Meeting.period.desc(), Meeting.effective_start.desc()) if descending else \
        (Meeting.date, Meeting.period, Meeting.effective_start)
    rows = query.order_by(*order).all()

    # "Changed since your last visit" (1.3): worked out now, from the history of the copy.
    visit = db.session.get(UserVisit, current_user.id)
    changed_ids = set()
    if visit:
        changed_ids = {c.meeting_id for c in MeetingChange.query.filter(
            MeetingChange.recorded_at > visit.visited_at, MeetingChange.changed_by != planning.user_name(current_user))}
    previous_visit = visit.visited_at if visit else None
    if visit:
        visit.visited_at = utcnow()
    else:
        db.session.add(UserVisit(user_id=current_user.id, visited_at=utcnow()))
    db.session.commit()

    return render_template("meetings/list.html", meetings=rows, when=when, origin=origin, q=text,
                           show_deleted=show_deleted, changed_ids=changed_ids, previous_visit=previous_visit)


@app.route("/meetings/<int:id>")
@login_required
def meeting_detail(id):
    meeting = db.get_or_404(Meeting, id)
    assignments = sorted(meeting.assignments, key=lambda a: (a.status == "cancelled", a.position.booking_id, a.position.position_number))
    return render_template(
        "meetings/detail.html", meeting=meeting, assignments=assignments,
        candidates=planning.assignable_positions(meeting) if current_user.is_editor else [],
        changes=MeetingChange.query.filter_by(meeting_id=id).order_by(MeetingChange.id.desc()).limit(50).all(),
        log=AssignmentLog.query.filter_by(meeting_id=id).order_by(AssignmentLog.id.desc()).limit(50).all(),
        overtime=planning.meeting_overtime_check(meeting),
        can_delete=planning.can_delete_meeting(meeting),
    )


@app.route("/meetings/add", methods=["GET", "POST"])
@editor_required
def add_meeting():
    if request.method == "POST":
        try:
            fields = _own_meeting_fields()
        except PlanningError as error:
            flash(str(error), "error")
            return _meeting_page(None, values=request.form)
        meeting = []
        if attempt(lambda: meeting.append(planning.create_own_meeting(fields, acting_user())), "Meeting added."):
            return redirect(url_for("meeting_detail", id=meeting[0].id))
        return _meeting_page(None, values=request.form)
    return _meeting_page(None, values={})


@app.route("/meetings/<int:id>/edit", methods=["GET", "POST"])
@editor_required
def edit_meeting(id):
    meeting = db.get_or_404(Meeting, id)
    if request.method == "POST":
        if changed_since_loaded(meeting):
            flash("Someone else changed this meeting while you were editing. "
                  "These are the current details; enter your changes again.", "error")
            return _meeting_page(meeting, values=meeting_values(meeting))
        try:
            fields = _own_meeting_fields() if meeting.origin == "own" else _pdc_fields(require_category=False)
        except PlanningError as error:
            flash(str(error), "error")
            return _meeting_page(meeting, values=request.form)
        if attempt(lambda: planning.update_meeting(meeting, fields, acting_user()), "Meeting updated."):
            return redirect(url_for("meeting_detail", id=id))
        return _meeting_page(meeting, values=request.form)
    return _meeting_page(meeting, values=meeting_values(meeting))


@app.route("/meetings/<int:id>/delete", methods=["POST"])
@editor_required
def delete_meeting(id):
    meeting = db.get_or_404(Meeting, id)
    if attempt(lambda: planning.delete_own_meeting(meeting, acting_user()), "Meeting deleted."):
        return redirect(url_for("meetings"))
    return redirect(url_for("meeting_detail", id=id))


@app.route("/meetings/<int:id>/<action>", methods=["POST"])
@editor_required
def meeting_status(id, action):
    if action not in ("cancel", "reopen"):
        return render_template("errors/404.html"), 404
    meeting = db.get_or_404(Meeting, id)
    status = "cancelled" if action == "cancel" else "planned"
    attempt(lambda: planning.set_own_meeting_status(meeting, status, acting_user()),
            "Meeting cancelled. Its assignments stay until you cancel them." if status == "cancelled"
            else "Meeting planned again.")
    return redirect(url_for("meeting_detail", id=id))


@app.route("/meetings/<int:id>/assign", methods=["POST"])
@editor_required
def assign_to_meeting(id):
    meeting = db.get_or_404(Meeting, id)
    position = db.session.get(BookingPosition, request.form.get("position_id", type=int) or 0)
    if position is None:
        flash("Choose a position.", "error")
    else:
        attempt(lambda: planning.assign(position, meeting, acting_user(), notes=clean("notes")), "Interpreter proposed.")
    return redirect(url_for("meeting_detail", id=id))


@app.route("/assignments/<int:id>/<action>", methods=["POST"])
@editor_required
def assignment_action(id, action):
    assignment = db.get_or_404(MeetingAssignment, id)
    user = acting_user()
    if action == "confirm":
        run = lambda: planning.confirm_assignment(assignment, user)
        done = "Assignment confirmed."
    elif action == "cancel":
        run = lambda: planning.cancel_assignment(
            assignment, user, reason=clean("reason"), communicated_on=form_date("communicated_on", required=False))
        done = "Assignment cancelled."
    elif action == "communicated":
        run = lambda: planning.communicate_cancellation(assignment, user, form_date("communicated_on"))
        done = "Noted that the interpreter was told."
    elif action == "check":
        run = lambda: planning.check_assignment(assignment, user, reason=clean("reason"))
        done = "Marked as checked."
    else:
        return render_template("errors/404.html"), 404
    attempt(run, done)
    return redirect(safe_next(url_for("meeting_detail", id=assignment.meeting_id)))


# ---------------------------------------------------------------------------
# Work lists
# ---------------------------------------------------------------------------

@app.route("/worklists")
@login_required
def worklists():
    return render_template(
        "worklists.html",
        cancelled=planning.worklist_cancelled_with_assignment(),
        changed=planning.worklist_changed_since_confirmation(),
        invoice_missing=planning.worklist_invoice_not_received(),
        dimona=planning.worklist_dimona_to_declare(),
    )


from bookings import bp as bookings_blueprint  # noqa: E402
from invoices import bp as invoices_blueprint  # noqa: E402

app.register_blueprint(bookings_blueprint)
app.register_blueprint(invoices_blueprint)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

@app.errorhandler(401)
def unauthorized_error(error):
    return render_template("errors/401.html"), 401


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
