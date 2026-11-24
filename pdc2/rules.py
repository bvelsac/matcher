"""The rules of PDC2 that change data: bookings, offers, marks on staff half-days, the GM register.

Functions change the session and do not commit; the caller commits, so a handling is one transaction.
A broken rule raises RuleError with a message for the planner. Every change adds a line to the log.
"""
import csv
import io
import re
from datetime import date, datetime

from pdc2.extensions import db
from pdc2.models import LANGUAGES, PERIODS, ROLES, Booking, Exclusion, Gm, LogEntry, Offer


class RuleError(Exception):
    """A rule of the functional analysis forbids this; the message says which."""


def _user(user):
    return (user.id if user else None), ((user.name or user.username) if user else "")


def log(action, user, *, gm=None, booking=None, person_id=None, day=None, period=None, **details):
    user_id, user_name = _user(user)
    if booking is not None:
        gm = gm or booking.gm
        day, period = day or booking.date, period or booking.period
    db.session.add(LogEntry(
        user_id=user_id, user_name=user_name, action=action, gm_id=gm.id if gm else None,
        booking_id=booking.id if booking else None, person_id=person_id, date=day, period=period,
        details={k: (v.isoformat() if isinstance(v, date) else v) for k, v in details.items()} or None))


# -- the GM register -----------------------------------------------------------------------------

def save_gm(gm, fields, user):
    """Create (gm None) or change a GM. Languages and roles are checked against the fixed lists."""
    if not fields.get("first_name") or not fields.get("last_name") or not fields.get("email"):
        raise RuleError("First name, last name and email are required.")
    languages = [x for x in fields.get("languages") or [] if x in LANGUAGES]
    if not languages:
        raise RuleError("Choose at least one language.")
    if fields.get("standard_role") not in ROLES:
        raise RuleError("Choose a standard role.")
    roles = sorted({r for r in fields.get("roles") or [] if r in ROLES} | {fields["standard_role"]},
                   key=ROLES.index)
    other = Gm.query.filter(Gm.email == fields["email"].lower()).first()
    if other is not None and other is not gm:
        raise RuleError("Another GM already has this email address.")
    new = gm is None
    gm = gm or Gm()
    gm.first_name, gm.last_name = fields["first_name"], fields["last_name"]
    gm.email, gm.phone = fields["email"].lower(), fields.get("phone") or None
    gm.languages, gm.standard_role, gm.roles = languages, fields["standard_role"], roles
    gm.active, gm.notes = bool(fields.get("active", True)), fields.get("notes") or None
    db.session.add(gm)
    db.session.flush()
    log("gm_added" if new else "gm_changed", user, gm=gm)
    return gm


# -- offers --------------------------------------------------------------------------------------

def offer(gm, day, period, user, source="manual", answered_at=None):
    """Record that a GM offers a half-day; a newer answer replaces an older one (FA 2.3)."""
    if period not in PERIODS:
        raise RuleError("Choose AM or PM.")
    existing = Offer.query.filter_by(gm_id=gm.id, date=day, period=period).first()
    if existing is not None:
        if answered_at and existing.answered_at and existing.answered_at > answered_at:
            return existing, False
        existing.source, existing.answered_at = source, answered_at or existing.answered_at
        return existing, False
    new = Offer(gm=gm, date=day, period=period, source=source, answered_at=answered_at)
    db.session.add(new)
    db.session.flush()
    log("offer_added", user, gm=gm, day=day, period=period, source=source)
    return new, True


def withdraw_offer(offer_row, user):
    log("offer_withdrawn", user, gm=offer_row.gm, day=offer_row.date, period=offer_row.period)
    db.session.delete(offer_row)


_HEADER = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\D+(?P<period>AM|PM|VM|NM)\b", re.IGNORECASE)
_TRUE = {"ja", "yes", "oui", "x", "1", "beschikbaar", "disponible", "available"}


def _header_half_day(header):
    match = _HEADER.search(header or "")
    if not match:
        return None
    raw = match.group("date")
    day = date.fromisoformat(raw) if "-" in raw else datetime.strptime(raw, "%d/%m/%Y").date()
    period = {"VM": "AM", "NM": "PM"}.get(match.group("period").upper(), match.group("period").upper())
    return day, period


def _timestamp(value):
    for pattern in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime((value or "").strip(), pattern)
        except ValueError:
            continue
    return None


def import_offers(text, user):
    """Import the CSV of the Google Form (FA 2.3, 10.5): a column with the email address, a column with
    the timestamp, and one column per half-day whose header holds a date and AM/PM (or VM/NM); a cell
    "ja", "x" or "beschikbaar" (and their French and English forms) means the half-day is offered.
    Returns (number of offers recorded, [unknown email addresses])."""
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []
    email_column = next((h for h in headers if "mail" in h.lower()), None)
    time_column = next((h for h in headers if any(w in h.lower() for w in ("tijd", "time", "horodat"))), None)
    half_days = {h: _header_half_day(h) for h in headers}
    half_days = {h: v for h, v in half_days.items() if v}
    if not email_column or not half_days:
        raise RuleError("The file needs a column with the email address and one column per half-day "
                        "with a date and AM or PM in its header.")
    count, unknown = 0, []
    for row in reader:
        email = (row.get(email_column) or "").strip().lower()
        if not email:
            continue
        gm = Gm.query.filter_by(email=email).first()
        if gm is None:
            if email not in unknown:
                unknown.append(email)
            continue
        answered = _timestamp(row.get(time_column)) if time_column else None
        for header, (day, period) in half_days.items():
            if (row.get(header) or "").strip().lower() in _TRUE:
                offer(gm, day, period, user, source="import", answered_at=answered)
                count += 1
    log("offers_imported", user, offers=count, unknown=len(unknown))
    return count, unknown


# -- bookings (FA 6) -----------------------------------------------------------------------------

def book(gm, day, period, role, language, user):
    if period not in PERIODS:
        raise RuleError("Choose AM or PM.")
    if role not in gm.capable_roles:
        raise RuleError("{} cannot work as {} (BR-GM-002).".format(gm.name, role))
    if language not in (gm.languages or []):
        raise RuleError("{} does not work in {} (BR-GM-002).".format(gm.name, language.upper()))
    if not gm.active:
        raise RuleError("{} is not active.".format(gm.name))
    taken = Booking.query.filter(Booking.gm_id == gm.id, Booking.date == day, Booking.period == period,
                                 Booking.status != "cancelled").first()
    if taken is not None:
        raise RuleError("{} is already booked on that half-day (BR-GM-001).".format(gm.name))
    has_offer = Offer.query.filter_by(gm_id=gm.id, date=day, period=period).first() is not None
    booking = Booking(gm=gm, date=day, period=period, role=role, language=language, status="proposed",
                      without_offer=not has_offer, created_by=user.id if user else None)
    db.session.add(booking)
    db.session.flush()
    log("booked", user, booking=booking, role=role, language=language, without_offer=not has_offer)
    return booking


def confirm(booking, user):
    if booking.status != "proposed":
        raise RuleError("Only a proposed booking can be confirmed.")
    booking.status = "confirmed"
    log("confirmed", user, booking=booking)


def cancel(booking, user, reason=None):
    if booking.status == "cancelled":
        raise RuleError("This booking is already cancelled.")
    booking.status = "cancelled"
    log("cancelled", user, booking=booking, reason=reason or None)


def set_dimona(booking, declared, user):
    if booking.status != "confirmed":
        raise RuleError("A Dimona declaration is for a confirmed booking.")
    if booking.dimona_declared == declared:
        return
    booking.dimona_declared = declared
    log("dimona_declared" if declared else "dimona_withdrawn", user, booking=booking)


def dimona_to_declare():
    return (Booking.query.filter_by(status="confirmed", dimona_declared=False)
            .order_by(Booking.date, Booking.period, Booking.id).all())


# -- staff half-days that do not count (FA 5) ----------------------------------------------------

def mark(person_id, person_name, day, period, reason, user):
    if period not in PERIODS:
        raise RuleError("Choose AM or PM.")
    if not (reason or "").strip():
        raise RuleError("Give a short reason, for example training or coordination.")
    existing = Exclusion.query.filter_by(person_id=person_id, date=day, period=period).first()
    if existing is not None:
        return existing
    row = Exclusion(person_id=person_id, person_name=person_name, date=day, period=period,
                    reason=reason.strip()[:200], created_by=user.id if user else None)
    db.session.add(row)
    log("marked", user, person_id=person_id, day=day, period=period, reason=row.reason, name=person_name)
    return row


def unmark(person_id, day, period, user):
    row = Exclusion.query.filter_by(person_id=person_id, date=day, period=period).first()
    if row is None:
        return
    log("unmarked", user, person_id=person_id, day=day, period=period, name=row.person_name)
    db.session.delete(row)
