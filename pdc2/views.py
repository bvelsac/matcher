"""The screens of PDC2 (functional analysis section 7). Plain HTML pages; htmx makes the small handlings
(book, confirm, mark a half-day) answer with the piece of the page that changed: hypermedia, the HATEOAS
of the browser side."""
from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from pdc2 import rules, sources
from pdc2.calc import CALCULATED, LANGUAGES, GmShift, calculate
from pdc2.extensions import db
from pdc2.helpers import acting_user, attempt, editor_required, is_htmx, monday_of, parse_date
from pdc2.models import LANGUAGES as GM_LANGUAGES
from pdc2.models import PERIODS, ROLES, Booking, Exclusion, Gm, LogEntry, Offer
from pdc2.rules import RuleError

bp = Blueprint("pdc2", __name__, template_folder="templates")


def _monday(value):
    try:
        day = date.fromisoformat(value)
    except ValueError:
        abort(404)
    return day, monday_of(day)


def load_week(monday):
    """Everything the screens of a week need: what spic and the jaarkalender say, and the calculation."""
    friday = monday + timedelta(days=4)
    previous = monday - timedelta(days=7)
    data = {"monday": monday, "friday": friday, "status": None, "error": None, "result": None,
            "meetings": [], "staff": [], "days": []}
    try:
        van, tot = previous, friday
        workdays = sources.workdays(van, tot)
        status, meetings = sources.week_of_spic(monday)
        _, previous_meetings = sources.week_of_spic(previous)
        staff = sources.staff(van, tot)
    except sources.HalError as error:
        data["error"] = str(error)
        return data
    shown = [d for d in workdays if monday <= d <= friday]
    bookings = Booking.query.filter(Booking.date >= van, Booking.date <= tot, Booking.status != "cancelled").all()
    shifts = [GmShift(b.date, b.period, b.role, b.language, b.gm.name, b.id) for b in bookings]
    excluded = {(e.person_id, e.date, e.period) for e in
                Exclusion.query.filter(Exclusion.date >= van, Exclusion.date <= tot)}
    data.update(status=status, meetings=meetings, staff=staff, days=shown, result=calculate(
        [d for d in workdays if d <= friday], previous_meetings + meetings, staff, shifts, excluded, shown=shown))
    return data


def _week_or_redirect(value, endpoint):
    day, monday = _monday(value)
    if day != monday:
        return None, redirect(url_for(endpoint, monday=monday.isoformat()))
    return monday, None


@bp.route("/")
@login_required
def index():
    return redirect(url_for("pdc2.week", monday=monday_of(date.today()).isoformat()))


@bp.route("/weeks/<monday>")
@login_required
def week(monday):
    monday, redirected = _week_or_redirect(monday, "pdc2.week")
    if redirected:
        return redirected
    return render_template("pdc2/week.html", w=load_week(monday), languages=LANGUAGES, roles=CALCULATED)


# -- staff of the week (FA 5) --------------------------------------------------------------------

@bp.route("/weeks/<monday>/staff")
@login_required
def staff(monday):
    monday, redirected = _week_or_redirect(monday, "pdc2.staff")
    if redirected:
        return redirected
    w = load_week(monday)
    marks = {(e.person_id, e.date, e.period): e for e in
             Exclusion.query.filter(Exclusion.date >= monday, Exclusion.date <= w["friday"])}
    return render_template("pdc2/staff.html", w=w, marks=marks, periods=PERIODS, languages=LANGUAGES)


def _staff_cell(monday, person_id, day, period):
    w = load_week(monday)
    person = next((p for p in w["staff"] if p.id == person_id), None)
    if person is None:
        abort(404)
    mark = Exclusion.query.filter_by(person_id=person_id, date=day, period=period).first()
    moves = {(m.person.id, m.date, m.period): m for m in (w["result"].moves if w["result"] else [])}
    return render_template("pdc2/_staff_cell.html", w=w, p=person, d=day, period=period, mark=mark,
                           move=moves.get((person_id, day, period)))


@bp.route("/weeks/<monday>/staff/mark", methods=["POST"])
@editor_required
def mark(monday):
    monday = _monday(monday)[1]
    person_id, period = request.form.get("person_id", ""), request.form.get("period", "")
    try:
        day = parse_date(request.form.get("date"))
    except RuleError as error:
        return str(error), 400
    reason = request.form.get("reason") or request.headers.get("HX-Prompt") or ""
    name = request.form.get("person_name", "")
    if request.form.get("action") == "unmark":
        _, error = attempt(lambda: rules.unmark(person_id, day, period, acting_user()))
    else:
        _, error = attempt(lambda: rules.mark(person_id, name, day, period, reason, acting_user()))
    if error:
        if is_htmx():
            return error, 422
        flash(error, "error")
    if is_htmx():
        return _staff_cell(monday, person_id, day, period)
    return redirect(url_for("pdc2.staff", monday=monday.isoformat()))


# -- offers and bookings (FA 6) ------------------------------------------------------------------

def _half_days(w):
    return [(d, p) for d in w["days"] for p in PERIODS]


def _offers_context(w):
    offers = Offer.query.join(Gm).filter(Offer.date >= w["monday"], Offer.date <= w["friday"]).all()
    bookings = Booking.query.filter(Booking.date >= w["monday"], Booking.date <= w["friday"]).all()
    by_half = {}
    for o in offers:
        by_half.setdefault((o.date, o.period), {"offers": [], "bookings": []})["offers"].append(o)
    for b in bookings:
        by_half.setdefault((b.date, b.period), {"offers": [], "bookings": []})["bookings"].append(b)
    return by_half


@bp.route("/weeks/<monday>/offers")
@login_required
def offers(monday):
    monday, redirected = _week_or_redirect(monday, "pdc2.offers")
    if redirected:
        return redirected
    w = load_week(monday)
    return render_template("pdc2/offers.html", w=w, by_half=_offers_context(w), half_days=_half_days(w),
                           gms=Gm.query.filter_by(active=True).order_by(Gm.last_name, Gm.first_name).all(),
                           roles=ROLES, gm_languages=GM_LANGUAGES, languages=LANGUAGES, calc_roles=CALCULATED)


def _after_booking_change(day, period, error=None):
    """For htmx: the half-day block again, and the shortage of the week out of band."""
    w = load_week(monday_of(day))
    return render_template("pdc2/_halfday_response.html", w=w, by_half=_offers_context(w), d=day,
                           period=period, roles=ROLES, error=error, languages=LANGUAGES, calc_roles=CALCULATED)


@bp.route("/bookings", methods=["POST"])
@editor_required
def book():
    gm = db.session.get(Gm, request.form.get("gm_id", type=int) or 0)
    try:
        day = parse_date(request.form.get("date"))
    except RuleError as error:
        return str(error), 400
    period = request.form.get("period", "")
    if gm is None:
        error = "Choose a GM."
    else:
        _, error = attempt(lambda: rules.book(gm, day, period, request.form.get("role", ""),
                                              request.form.get("language", ""), acting_user()))
    if is_htmx():
        return _after_booking_change(day, period, error)
    flash(error or "Booked.", "error" if error else "success")
    return redirect(request.form.get("next") or url_for("pdc2.offers", monday=monday_of(day).isoformat()))


@bp.route("/bookings/<int:id>/<action>", methods=["POST"])
@editor_required
def booking_action(id, action):
    booking = db.get_or_404(Booking, id)
    user = acting_user()
    handlings = {
        "confirm": lambda: rules.confirm(booking, user),
        "cancel": lambda: rules.cancel(booking, user, request.form.get("reason")),
        "dimona": lambda: rules.set_dimona(booking, True, user),
        "undimona": lambda: rules.set_dimona(booking, False, user),
    }
    if action not in handlings:
        abort(404)
    _, error = attempt(handlings[action])
    target = request.form.get("target", "halfday")
    if is_htmx() and target == "row":
        return render_template("pdc2/_booking_row.html", b=booking, error=error)
    if is_htmx():
        return _after_booking_change(booking.date, booking.period, error)
    flash(error or "Saved.", "error" if error else "success")
    return redirect(request.form.get("next") or url_for("pdc2.offers", monday=monday_of(booking.date).isoformat()))


@bp.route("/offers", methods=["POST"])
@editor_required
def add_offer():
    gm = db.session.get(Gm, request.form.get("gm_id", type=int) or 0)
    try:
        day = parse_date(request.form.get("date"))
        if gm is None:
            raise RuleError("Choose a GM.")
    except RuleError as error:
        flash(str(error), "error")
        return redirect(request.form.get("next") or url_for("pdc2.index"))
    _, error = attempt(lambda: rules.offer(gm, day, request.form.get("period", ""), acting_user(), "manual"))
    flash(error or "Offer recorded.", "error" if error else "success")
    return redirect(request.form.get("next") or url_for("pdc2.offers", monday=monday_of(day).isoformat()))


@bp.route("/weeks/<monday>/bookings")
@login_required
def bookings(monday):
    monday, redirected = _week_or_redirect(monday, "pdc2.bookings")
    if redirected:
        return redirected
    w = {"monday": monday, "friday": monday + timedelta(days=4)}
    rows = (Booking.query.join(Gm).filter(Booking.date >= monday, Booking.date <= w["friday"])
            .order_by(Gm.last_name, Gm.first_name, Booking.date, Booking.period).all())
    per_gm = {}
    for b in rows:
        per_gm.setdefault(b.gm, []).append(b)
    return render_template("pdc2/bookings.html", w=w, per_gm=per_gm)


# -- GMs -----------------------------------------------------------------------------------------

@bp.route("/gms")
@login_required
def gms():
    return render_template("pdc2/gms.html", gms=Gm.query.order_by(Gm.active.desc(), Gm.last_name, Gm.first_name).all())


def _gm_fields():
    f = request.form
    return {"first_name": f.get("first_name", "").strip(), "last_name": f.get("last_name", "").strip(),
            "email": f.get("email", "").strip(), "phone": f.get("phone", "").strip(),
            "languages": f.getlist("languages"), "standard_role": f.get("standard_role"),
            "roles": f.getlist("roles"), "active": f.get("active") == "1", "notes": f.get("notes", "").strip()}


@bp.route("/gms/new", methods=["GET", "POST"])
@bp.route("/gms/<int:id>", methods=["GET", "POST"])
@login_required
def gm_form(id=None):
    gm = db.get_or_404(Gm, id) if id else None
    if request.method == "POST":
        from flask_login import current_user
        if not current_user.is_editor:
            abort(403)
        saved, error = attempt(lambda: rules.save_gm(gm, _gm_fields(), acting_user()))
        if not error:
            flash("GM saved.", "success")
            return redirect(url_for("pdc2.gms"))
        flash(error, "error")
        return render_template("pdc2/gm_form.html", gm=gm, values=_gm_fields(), roles=ROLES, languages=GM_LANGUAGES)
    values = {"first_name": gm.first_name, "last_name": gm.last_name, "email": gm.email, "phone": gm.phone or "",
              "languages": gm.languages, "standard_role": gm.standard_role, "roles": gm.roles,
              "active": gm.active, "notes": gm.notes or ""} if gm else {"languages": [], "roles": [], "active": True}
    return render_template("pdc2/gm_form.html", gm=gm, values=values, roles=ROLES, languages=GM_LANGUAGES)


# -- import, Dimona, log -------------------------------------------------------------------------

@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_offers():
    outcome = None
    if request.method == "POST":
        from flask_login import current_user
        if not current_user.is_editor:
            abort(403)
        upload = request.files.get("file")
        text = upload.read().decode("utf-8-sig", errors="replace") if upload else ""
        outcome, error = attempt(lambda: rules.import_offers(text, acting_user()))
        if error:
            flash(error, "error")
    return render_template("pdc2/import.html", outcome=outcome)


@bp.route("/dimona")
@login_required
def dimona():
    return render_template("pdc2/dimona.html", rows=rules.dimona_to_declare())


@bp.route("/log")
@login_required
def log():
    return render_template("pdc2/log.html", entries=LogEntry.query.order_by(LogEntry.id.desc()).limit(300).all())
