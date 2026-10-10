"""Invoices: recorded once, then linked to all positions they cover (functional analysis 2.9)."""
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required

import planning
from extensions import db
from helpers import acting_user, attempt, clean, editor_required, form_date
from models import Booking, BookingPosition, Interpreter, Invoice, TimeSlot
from planning import PlanningError

bp = Blueprint("invoices", __name__)


@bp.route("/invoices")
@login_required
def list_invoices():
    show = request.args.get("show", "all")
    query = Invoice.query
    if show == "unchecked":
        query = query.filter(Invoice.checked_on.is_(None))
    rows = query.order_by(Invoice.received_on.desc(), Invoice.id.desc()).all()
    return render_template("invoices/list.html", invoices=rows, show=show)


@bp.route("/invoices/add", methods=["GET", "POST"])
@editor_required
def add_invoice():
    suppliers = Interpreter.query.filter_by(engagement="invoice").order_by(Interpreter.priority_order).all()
    if request.method == "POST":
        interpreter = db.session.get(Interpreter, request.form.get("interpreter_id", type=int) or 0)
        created = []

        def create():
            if interpreter is None:
                raise PlanningError("Choose who sent the invoice.")
            created.append(planning.record_invoice(
                interpreter, clean("reference"), form_date("received_on", "received on"), clean("period"),
                clean("notes"), acting_user()))

        if attempt(create, "Invoice recorded. Link the services it covers."):
            return redirect(url_for("invoices.invoice_detail", id=created[0].id))
    return render_template("invoices/add.html", suppliers=suppliers)


def _open_positions(invoice):
    """Positions of the supplier that can still be linked: completed or running bookings, no invoice yet."""
    return (BookingPosition.query.join(Booking).join(TimeSlot)
            .filter(Booking.interpreter_id == invoice.interpreter_id, BookingPosition.status == "active",
                    Booking.status.in_(("confirmed", "completed")), BookingPosition.invoice_id.is_(None))
            .order_by(TimeSlot.date, Booking.id, BookingPosition.position_number).all())


@bp.route("/invoices/<int:id>")
@login_required
def invoice_detail(id):
    invoice = db.get_or_404(Invoice, id)
    linked = sorted(invoice.positions, key=lambda p: (p.booking.slot.date, p.booking_id, p.position_number))
    return render_template("invoices/detail.html", invoice=invoice, linked=linked, open_positions=_open_positions(invoice))


@bp.route("/invoices/<int:id>/link", methods=["POST"])
@editor_required
def link_invoice(id):
    invoice = db.get_or_404(Invoice, id)
    ids = request.form.getlist("position_id", type=int)
    positions = BookingPosition.query.filter(BookingPosition.id.in_(ids)).all() if ids else []

    def link():
        if not positions:
            raise PlanningError("Tick the services this invoice covers.")
        planning.link_invoice(invoice, positions, acting_user())

    attempt(link, "Services linked to the invoice.")
    return redirect(url_for("invoices.invoice_detail", id=id))


@bp.route("/invoices/<int:id>/<action>", methods=["POST"])
@editor_required
def invoice_action(id, action):
    invoice = db.get_or_404(Invoice, id)
    if action not in ("checked", "unchecked"):
        return render_template("errors/404.html"), 404
    attempt(lambda: planning.mark_invoice_checked(invoice, acting_user(), checked=action == "checked"),
            "Marked as checked." if action == "checked" else "Check withdrawn.")
    return redirect(url_for("invoices.invoice_detail", id=id))
