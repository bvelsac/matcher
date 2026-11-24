"""PDC2's database: the GMs, their offers, the bookings, the marks on staff half-days, and the log.

The meetings and the staff are not stored: they are read from spic and the jaarkalender (pdc2/sources.py).
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import DDL, CheckConstraint, Index, UniqueConstraint, event, text

from pdc2.extensions import db

ROLES = ("redacteur", "revisor", "hoofdredacteur", "vertaler")
ROLE_LABELS = {"redacteur": "Redacteur", "revisor": "Revisor", "hoofdredacteur": "Hoofdredacteur",
               "vertaler": "Vertaler"}
LANGUAGES = ("nl", "fr")
PERIODS = ("AM", "PM")
BOOKING_STATUS_LABELS = {"proposed": "Proposed", "confirmed": "Confirmed", "cancelled": "Cancelled"}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _in(column, values):
    return "{} IN ({})".format(column, ", ".join("'{}'".format(v) for v in values))


class User(UserMixin, db.Model):
    """A person as Authelia identifies them; the role is worked out on every request."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=utcnow)

    role = "viewer"

    @property
    def is_editor(self):
        return self.role == "editor"


class Gm(db.Model):
    """An occasional staff member (gelegenheidsmedewerker), with languages and roles (FA 3)."""

    __tablename__ = "gms"
    __table_args__ = (CheckConstraint(_in("standard_role", ROLES), name="ck_gms_standard_role"),)

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)     # recognises the form's answers
    phone = db.Column(db.String(30))
    languages = db.Column(db.JSON, nullable=False, default=list)     # ["nl"], ["fr"] or both
    standard_role = db.Column(db.String(20), nullable=False)
    roles = db.Column(db.JSON, nullable=False, default=list)          # every role the GM can take
    active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    offers = db.relationship("Offer", back_populates="gm")
    bookings = db.relationship("Booking", back_populates="gm")

    @property
    def name(self):
        return "{} {}".format(self.first_name, self.last_name)

    @property
    def capable_roles(self):
        return [r for r in ROLES if r == self.standard_role or r in (self.roles or [])]


class Offer(db.Model):
    """A half-day a GM offered (FA 2.3). A new answer for the same half-day replaces the earlier one."""

    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("gm_id", "date", "period", name="uq_offers_half_day"),
        CheckConstraint(_in("period", PERIODS), name="ck_offers_period"),
        CheckConstraint(_in("source", ("import", "manual")), name="ck_offers_source"),
    )

    id = db.Column(db.Integer, primary_key=True)
    gm_id = db.Column(db.Integer, db.ForeignKey("gms.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    period = db.Column(db.String(2), nullable=False)
    source = db.Column(db.String(10), nullable=False, default="import")
    answered_at = db.Column(db.DateTime)            # the form's timestamp, for "the latest counts"
    created_at = db.Column(db.DateTime, default=utcnow)

    gm = db.relationship("Gm", back_populates="offers")


class Booking(db.Model):
    """One GM, one half-day, one role, one language (FA 6). Never deleted, only cancelled."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(_in("period", PERIODS), name="ck_bookings_period"),
        CheckConstraint(_in("role", ROLES), name="ck_bookings_role"),
        CheckConstraint(_in("language", LANGUAGES), name="ck_bookings_language"),
        CheckConstraint(_in("status", BOOKING_STATUS_LABELS), name="ck_bookings_status"),
        # BR-GM-001: at most one booking that is not cancelled per GM and half-day.
        Index("uq_bookings_active_half_day", "gm_id", "date", "period", unique=True,
              sqlite_where=text("status <> 'cancelled'")),
    )

    id = db.Column(db.Integer, primary_key=True)
    gm_id = db.Column(db.Integer, db.ForeignKey("gms.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    period = db.Column(db.String(2), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    language = db.Column(db.String(2), nullable=False)
    status = db.Column(db.String(10), nullable=False, default="proposed")
    without_offer = db.Column(db.Boolean, nullable=False, default=False)
    dimona_declared = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    gm = db.relationship("Gm", back_populates="bookings")

    @property
    def hours(self):
        return 3.0 if self.period == "AM" else 4.0

    @property
    def status_display(self):
        return BOOKING_STATUS_LABELS[self.status]


class Exclusion(db.Model):
    """A staff half-day that does not count for this planning (FA 5). `person_id` is the jaarkalender's id."""

    __tablename__ = "exclusions"
    __table_args__ = (
        UniqueConstraint("person_id", "date", "period", name="uq_exclusions_half_day"),
        CheckConstraint(_in("period", PERIODS), name="ck_exclusions_period"),
    )

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.String(80), nullable=False, index=True)
    person_name = db.Column(db.String(200), nullable=False, default="")
    date = db.Column(db.Date, nullable=False, index=True)
    period = db.Column(db.String(2), nullable=False)
    reason = db.Column(db.String(200), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))


class LogEntry(db.Model):
    """The append-only log (FA 6.4): the database refuses to change or delete a line."""

    __tablename__ = "log"

    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)   # UTC
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user_name = db.Column(db.String(200), nullable=False, default="")
    action = db.Column(db.String(40), nullable=False)
    gm_id = db.Column(db.Integer, db.ForeignKey("gms.id"), index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), index=True)
    person_id = db.Column(db.String(80))
    date = db.Column(db.Date)
    period = db.Column(db.String(2))
    details = db.Column(db.JSON)


for _verb in ("UPDATE", "DELETE"):
    event.listen(LogEntry.__table__, "after_create", DDL(
        "CREATE TRIGGER log_no_{v} BEFORE {V} ON log BEGIN SELECT RAISE(ABORT, 'log is append-only'); END"
        .format(v=_verb.lower(), V=_verb)).execute_if(dialect="sqlite"))
