"""Bookings and their positions: reserving interpreters for a time slot, naming the person sent,
the hours worked and the Dimona declaration (functional analysis 2.4, 2.5)."""
from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required

import planning
from extensions import db
from helpers import (
    acting_user, attempt, clean, editor_required, form_date, form_datetime, form_int, form_time, safe_next,
)
from models import BOOKING_STATUS_LABELS, FORFAIT_HOURS, AssignmentLog, Booking, BookingPosition, Interpreter, TimeSlot
from planning import PlanningError

bp = Blueprint("bookings", __name__)


@bp.route("/bookings")
@login_required
def list_bookings():
    when = request.args.get("when", "upcoming")
    status = request.args.get("status", "")
    query = Booking.query.join(TimeSlot)
    if when == "upcoming":
        query = query.filter(TimeSlot.date >= date.today())
    elif when == "past":
        query = query.filter(TimeSlot.date < date.today())
    if status in BOOKING_STATUS_LABELS:
        query = query.filter(Booking.status == status)
    elif request.args.get("cancelled") != "1":
        query = query.filter(Booking.status != "cancelled")
    rows = query.order_by(TimeSlot.date.desc() if when == "past" else TimeSlot.date, TimeSlot.start_time, Booking.id).all()
    return render_template("bookings/list.html", bookings=rows, when=when, status=status,
                           show_cancelled=request.args.get("cancelled") == "1",
                           statuses=BOOKING_STATUS_LABELS)


@bp.route("/bookings/add", methods=["GET", "POST"])
@editor_required
def add_booking():
    interpreters = Interpreter.query.order_by(Interpreter.priority_order).all()
    if request.method == "POST":
        interpreter = db.session.get(Interpreter, request.form.get("interpreter_id", type=int) or 0)
        created = []

        def create():
            if interpreter is None:
                raise PlanningError("Choose an interpreter or bureau.")
            slot = planning.get_or_create_slot(
                form_date("date"), form_time("start", "start"), form_time("end", "end"), clean("description"))
            created.append(planning.create_booking(
                interpreter, slot, form_int("positions", "The number of interpreters", minimum=1),
                form_int("forfait_hours", "The forfait"), acting_user(), reason=clean("reason"), notes=clean("notes")))

        if attempt(create, "Booking proposed."):
            return redirect(url_for("bookings.booking_detail", id=created[0].id))
    return render_template("bookings/add.html", interpreters=interpreters, forfaits=FORFAIT_HOURS)


@bp.route("/bookings/<int:id>")
@login_required
def booking_detail(id):
    booking = db.get_or_404(Booking, id)
    rows = [{"position": p, "overtime": planning.position_overtime(p), "paid": planning.paid_hours(p)}
            for p in booking.positions]
    log = AssignmentLog.query.filter_by(booking_id=id).order_by(AssignmentLog.id.desc()).limit(50).all()
    return render_template("bookings/detail.html", booking=booking, rows=rows, log=log)


@bp.route("/bookings/<int:id>/<action>", methods=["POST"])
@editor_required
def booking_action(id, action):
    booking = db.get_or_404(Booking, id)
    user = acting_user()
    actions = {
        "confirm": (lambda: planning.confirm_booking(booking, user), "Booking confirmed."),
        "cancel": (lambda: planning.cancel_booking(booking, user, reason=clean("reason")),
                   "Booking cancelled, with its positions and assignments."),
        "complete": (lambda: planning.complete_booking(booking, user), "Booking completed."),
        "add-position": (lambda: planning.add_position(booking, user), "Position added."),
    }
    if action not in actions:
        return render_template("errors/404.html"), 404
    run, done = actions[action]
    attempt(run, done)
    return redirect(url_for("bookings.booking_detail", id=id))


@bp.route("/positions/<int:id>/<action>", methods=["POST"])
@editor_required
def position_action(id, action):
    position = db.get_or_404(BookingPosition, id)
    user = acting_user()
    actions = {
        "name": (lambda: planning.set_position_name(position, clean("interpreter_name"), user), "Name saved."),
        "hours": (lambda: planning.record_hours(
            position, form_datetime("actual_start_time", "the start"), form_datetime("actual_end_time", "the end"), user),
            "Hours saved."),
        "cancel": (lambda: planning.cancel_position(position, user, reason=clean("reason")),
                   "Position cancelled, with its assignments."),
        "dimona": (lambda: planning.set_dimona(position, True, user), "Dimona declaration noted."),
        "undimona": (lambda: planning.set_dimona(position, False, user), "Dimona declaration withdrawn."),
        "unlink-invoice": (lambda: planning.unlink_invoice(position, user), "Invoice unlinked."),
    }
    if action not in actions:
        return render_template("errors/404.html"), 404
    run, done = actions[action]
    attempt(run, done)
    return redirect(safe_next(url_for("bookings.booking_detail", id=position.booking_id)))
