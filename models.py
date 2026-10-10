"""Database models of PDC (functional analysis 2).

Interpreters and the booking chain (time slot -> booking -> position -> assignment), meetings
(PDC's own copy of the spic meetings and the meetings entered in PDC, in one table), invoices,
the history of the copy and the append-only assignment log. Availability declarations and the
CSV sources (2.3, 2.8) come with Phase 2.
"""
from datetime import datetime, time, timedelta, timezone

from flask_login import UserMixin
from sqlalchemy import DDL, CheckConstraint, UniqueConstraint, event, or_

from extensions import db


def utcnow():
    """The current time in UTC, without time zone, as stored in the database."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


MEETING_CATEGORIES = (
    ("parliament", "Parliament"),
    ("affiliated_organization", "Affiliated organization"),
    ("external_group", "External group"),
    ("special_event", "Special event"),
)
CATEGORY_LABELS = dict(MEETING_CATEGORIES)

ORIGIN_LABELS = {"spic": "from spic", "own": "own"}
MEETING_STATUS_LABELS = {"planned": "Planned", "cancelled": "Cancelled", "deleted": "Deleted in spic"}
WEEK_STATUS_LABELS = {"pre_definitive": "Pre-definitive", "definitive": "Definitive", "concept": "Back in concept"}
VISIBLE_WEEK_STATUSES = ("pre_definitive", "definitive")
ENGAGEMENT_LABELS = {"invoice": "On invoice", "occasional_work": "Occasional work (Dimona)"}
BOOKING_STATUS_LABELS = {
    "proposed": "Proposed", "confirmed": "Confirmed", "completed": "Completed", "cancelled": "Cancelled",
}
ASSIGNMENT_STATUS_LABELS = {"proposed": "Proposed", "confirmed": "Confirmed", "cancelled": "Cancelled"}
FORFAIT_HOURS = (3, 4)


def _in(column, values):
    return "{} IN ({})".format(column, ", ".join("'{}'".format(v) for v in values))


class User(UserMixin, db.Model):
    """A person as Authelia identifies them, recorded the first time they are seen (auth.py).

    The role is not stored: it is worked out on every request (auth.role_for).
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # Remote-User
    name = db.Column(db.String(200), nullable=False, default="")       # Remote-Name
    created_at = db.Column(db.DateTime, default=utcnow)

    role = "viewer"  # set per request by auth.load_user_from_request

    @property
    def is_editor(self):
        return self.role == "editor"

    def __repr__(self):
        return "<User {}>".format(self.username)


class UserVisit(db.Model):
    """When a user last opened the meeting list, for "changed since your last visit" (1.3)."""

    __tablename__ = "user_visits"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    visited_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Interpreter(db.Model):
    """An individual interpreter or a bureau, ranked in the legal priority order (2.1)."""

    __tablename__ = "interpreters"
    __table_args__ = (CheckConstraint(_in("engagement", ENGAGEMENT_LABELS), name="ck_interpreters_engagement"),)

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    # Email identifies the respondent in the Google Forms data; stored lower-case.
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    bureau_affiliation = db.Column(db.String(200))
    priority_order = db.Column(db.Integer, nullable=False, index=True)
    additional_languages = db.Column(db.Text)
    notes = db.Column(db.Text)
    # "invoice" (FACT. in the spreadsheet) or "occasional_work" (DIM: Dimona declaration, no invoice)
    engagement = db.Column(db.String(20), nullable=False, default="invoice", server_default="invoice")
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    @property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    @property
    def display_name(self):
        if self.bureau_affiliation:
            return "{} ({})".format(self.full_name, self.bureau_affiliation)
        return self.full_name

    @property
    def is_bureau(self):
        return bool(self.bureau_affiliation)

    @property
    def engagement_display(self):
        return ENGAGEMENT_LABELS.get(self.engagement, self.engagement)

    def __repr__(self):
        return "<Interpreter {}>".format(self.full_name)


class Room(db.Model):
    """Copy of spic's fixed list of rooms (the export will supply it). Meetings refer to the
    code without a foreign key, so a meeting with a room that is not in the list yet still fits."""

    __tablename__ = "rooms"

    code = db.Column(db.String(20), primary_key=True)
    description = db.Column(db.String(200), nullable=False, default="")
    active = db.Column(db.Boolean, nullable=False, default=True)


class Meeting(db.Model):
    """A meeting that needs interpreters: a copy of a spic meeting or one entered in PDC (2.7)."""

    __tablename__ = "meetings"
    __table_args__ = (
        CheckConstraint(_in("origin", ("spic", "own")), name="ck_meetings_origin"),
        CheckConstraint(_in("status", MEETING_STATUS_LABELS), name="ck_meetings_status"),
        CheckConstraint(_in("period", ("AM", "PM")), name="ck_meetings_period"),
        CheckConstraint("week_status IS NULL OR " + _in("week_status", WEEK_STATUS_LABELS),
                        name="ck_meetings_week_status"),
        CheckConstraint("start_kind IS NULL OR " + _in("start_kind", ("time", "after")),
                        name="ck_meetings_start_kind"),
        # spic meetings carry the ID of spic; own meetings do not and have to be complete.
        CheckConstraint(
            "(origin = 'spic' AND spic_id IS NOT NULL) OR "
            "(origin = 'own' AND spic_id IS NULL AND title IS NOT NULL AND room IS NOT NULL "
            "AND category IS NOT NULL AND interpreters_needed IS NOT NULL)",
            name="ck_meetings_origin_fields"),
        CheckConstraint("status <> 'deleted' OR origin = 'spic'", name="ck_meetings_deleted_is_spic"),
        CheckConstraint("interpreters_needed IS NULL OR interpreters_needed > 0", name="ck_meetings_needed"),
        CheckConstraint("charged_half_hours IS NULL OR charged_half_hours >= 0", name="ck_meetings_charged"),
    )

    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(5), nullable=False)
    spic_id = db.Column(db.String(40), unique=True)
    status = db.Column(db.String(10), nullable=False, default="planned")
    week = db.Column(db.Date)
    week_status = db.Column(db.String(15))
    title = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False, index=True)
    period = db.Column(db.String(2), nullable=False)
    start_kind = db.Column(db.String(5))
    start_time = db.Column(db.Time)
    effective_start = db.Column(db.Time)
    expected_end = db.Column(db.Time)
    end_next_day = db.Column(db.Boolean, nullable=False, default=False)
    room = db.Column(db.String(20))
    domain = db.Column(db.String(50))
    assembly = db.Column(db.String(50))
    type = db.Column(db.String(50))
    sequence_number = db.Column(db.Integer)
    sequence_number_2 = db.Column(db.Integer)
    interpreters_needed = db.Column(db.Integer)
    category = db.Column(db.String(30))
    notes = db.Column(db.Text)
    actual_end = db.Column(db.Time)
    charged_half_hours = db.Column(db.Integer)
    spic_data = db.Column(db.JSON)
    spic_version = db.Column(db.Integer)
    last_change_number = db.Column(db.Integer)
    first_seen_at = db.Column(db.DateTime)
    deleted_in_spic_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    creator = db.relationship("User", backref="created_meetings")
    assignments = db.relationship("MeetingAssignment", back_populates="meeting")

    # -- visibility (BR-MTG-009) -------------------------------------------------------------

    @staticmethod
    def visible_filter():
        """SQL condition: own meetings, and spic meetings of a pre-definitive or definitive week."""
        return or_(Meeting.origin == "own", Meeting.week_status.in_(VISIBLE_WEEK_STATUSES))

    @property
    def is_visible(self):
        return self.origin == "own" or self.week_status in VISIBLE_WEEK_STATUSES

    # -- display -----------------------------------------------------------------------------

    @property
    def display_title(self):
        if self.origin == "own":
            return self.title
        parts = [self.domain, self.assembly, self.type]
        numbers = [str(n) for n in (self.sequence_number, self.sequence_number_2) if n]
        label = " ".join(p for p in parts if p)
        if numbers:
            label = "{} {}".format(label, "/".join(numbers)).strip()
        return label or self.spic_id

    @property
    def origin_display(self):
        return ORIGIN_LABELS[self.origin]

    @property
    def status_display(self):
        return MEETING_STATUS_LABELS[self.status]

    @property
    def week_status_display(self):
        return WEEK_STATUS_LABELS.get(self.week_status, "")

    @property
    def category_display(self):
        return CATEGORY_LABELS.get(self.category, "-")

    # -- times (BR-MTG-001, BR-MTG-002) ------------------------------------------------------

    @property
    def time_known(self):
        return self.effective_start is not None and self.expected_end is not None

    @property
    def datetime_start(self):
        return datetime.combine(self.date, self.effective_start) if self.effective_start else None

    @property
    def datetime_end(self):
        if self.expected_end is None:
            return None
        end = datetime.combine(self.date, self.expected_end)
        return end + timedelta(days=1) if self.end_next_day else end

    @property
    def actual_end_datetime(self):
        """The real end (kept in PDC) as a date and time; after midnight when it is earlier than the start."""
        if self.actual_end is None:
            return None
        end = datetime.combine(self.date, self.actual_end)
        before_start = self.effective_start is not None and self.actual_end < self.effective_start
        if before_start or self.end_next_day:
            end += timedelta(days=1)
        return end

    @property
    def duration_minutes(self):
        if not self.time_known:
            return None
        return int((self.datetime_end - self.datetime_start).total_seconds() // 60)

    # -- staffing (derived properties of 2.7) --------------------------------------------------

    @property
    def active_assignments(self):
        return [a for a in self.assignments if a.status != "cancelled"]

    @property
    def staffing_count(self):
        return sum(1 for a in self.assignments if a.status == "confirmed")

    @property
    def staffing_status(self):
        count, needed = self.staffing_count, self.interpreters_needed
        if count == 0:
            return "unstaffed"
        if needed is None:
            return "staffed"
        if count < needed:
            return "understaffed"
        return "fully_staffed" if count == needed else "overstaffed"

    # -- snapshot for the log (1.6) ----------------------------------------------------------

    def snapshot(self):
        """The meeting as it is at this moment, kept in the assignment log."""
        return {
            "origin": self.origin,
            "spic_id": self.spic_id,
            "title": self.display_title,
            "date": self.date.isoformat(),
            "period": self.period,
            "effective_start": _hhmm(self.effective_start),
            "expected_end": _hhmm(self.expected_end),
            "end_next_day": bool(self.end_next_day),
            "room": self.room,
            "status": self.status,
            "week_status": self.week_status,
            "spic_version": self.spic_version,
            "last_change_number": self.last_change_number,
        }

    def __repr__(self):
        return "<Meeting {} on {}>".format(self.display_title, self.date)


def _hhmm(value):
    return value.strftime("%H:%M") if isinstance(value, time) else None


# Fields that make a meeting "changed since the confirmation" (1.6): compared with the snapshot.
WATCHED_SNAPSHOT_FIELDS = ("date", "effective_start", "expected_end", "room", "status")


class MeetingChange(db.Model):
    """History of the copy and of the own meetings; append-only (triggers below).

    meeting_id has no foreign key: the history of an own meeting stays after the meeting was
    deleted (BR-MTG-006), with a "deleted" entry that holds the last state."""

    __tablename__ = "meeting_changes"
    __table_args__ = (
        CheckConstraint(_in("kind", ("new", "changed", "cancelled", "reopened", "deleted", "restored",
                                     "moved", "week_status", "edited")), name="ck_meeting_changes_kind"),
    )

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, nullable=False, index=True)
    change_number = db.Column(db.Integer)  # spic's number; empty for an own meeting or a PDC field
    kind = db.Column(db.String(12), nullable=False)
    before = db.Column(db.JSON)
    after = db.Column(db.JSON)
    changed_by = db.Column(db.String(200), nullable=False, default="")
    recorded_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)


class SyncState(db.Model):
    """The state of the copy of spic (one row, id 1). Filled in by the link with spic (step 5)."""

    __tablename__ = "sync_state"

    id = db.Column(db.Integer, primary_key=True)
    last_change_number = db.Column(db.Integer, nullable=False, default=0)
    last_success_at = db.Column(db.DateTime)
    last_attempt_at = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    last_full_comparison_at = db.Column(db.DateTime)
    spic_highest_number = db.Column(db.Integer)


class TimeSlot(db.Model):
    """A period for which interpreters are booked (2.2). Availability comes with Phase 2."""

    __tablename__ = "time_slots"
    __table_args__ = (CheckConstraint("start_time < end_time", name="ck_time_slots_order"),)

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    description = db.Column(db.String(200))

    @property
    def label(self):
        text = "{} {}-{}".format(self.date.isoformat(), _hhmm(self.start_time), _hhmm(self.end_time))
        return "{} ({})".format(text, self.description) if self.description else text

    def overlaps(self, other):
        return self.date == other.date and self.start_time < other.end_time and other.start_time < self.end_time


class Booking(db.Model):
    """The commitment towards one supplier for a time slot: a bucket of positions (2.4)."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(_in("status", BOOKING_STATUS_LABELS), name="ck_bookings_status"),
        CheckConstraint(_in("forfait_hours", FORFAIT_HOURS), name="ck_bookings_forfait"),
    )

    id = db.Column(db.Integer, primary_key=True)
    interpreter_id = db.Column(db.Integer, db.ForeignKey("interpreters.id"), nullable=False, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("time_slots.id"), nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False, default="proposed")
    booking_reason = db.Column(db.String(200))
    forfait_hours = db.Column(db.Integer, nullable=False, default=4, server_default="4")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    interpreter = db.relationship("Interpreter", backref="bookings")
    slot = db.relationship("TimeSlot")
    positions = db.relationship("BookingPosition", back_populates="booking",
                                order_by="BookingPosition.position_number")

    @property
    def status_display(self):
        return BOOKING_STATUS_LABELS[self.status]

    @property
    def active_positions(self):
        return [p for p in self.positions if p.status == "active"]

    @property
    def quantity_booked(self):
        return len(self.active_positions)

    @property
    def free_positions(self):
        return [p for p in self.active_positions if not p.active_assignments]

    def __repr__(self):
        return "<Booking {} {}>".format(self.id, self.status)


class BookingPosition(db.Model):
    """One interpreter within a booking; the unit that is dispatched to meetings (2.5)."""

    __tablename__ = "booking_positions"
    __table_args__ = (
        UniqueConstraint("booking_id", "position_number", name="uq_positions_number"),
        CheckConstraint(_in("status", ("active", "cancelled")), name="ck_positions_status"),
        CheckConstraint("actual_end_time IS NULL OR actual_start_time IS NULL OR actual_end_time > actual_start_time",
                        name="ck_positions_hours"),
    )

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False, index=True)
    position_number = db.Column(db.Integer, nullable=False)
    interpreter_name = db.Column(db.String(200))
    status = db.Column(db.String(10), nullable=False, default="active")
    actual_start_time = db.Column(db.DateTime)
    actual_end_time = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), index=True)
    dimona_declared = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    booking = db.relationship("Booking", back_populates="positions")
    invoice = db.relationship("Invoice", back_populates="positions")
    assignments = db.relationship("MeetingAssignment", back_populates="position")

    @property
    def label(self):
        return "{} - interpreter {} of {}".format(
            self.booking.interpreter.display_name, self.position_number, len(self.booking.positions))

    @property
    def active_assignments(self):
        return [a for a in self.assignments if a.status != "cancelled"]

    @property
    def interpreter(self):
        return self.booking.interpreter

    @property
    def person(self):
        """The person sent, when known; otherwise the interpreter or bureau that is booked."""
        return self.interpreter_name or self.booking.interpreter.display_name


class MeetingAssignment(db.Model):
    """One booking position dispatched to one meeting (2.6). Never deleted, only cancelled."""

    __tablename__ = "meeting_assignments"
    __table_args__ = (
        UniqueConstraint("position_id", "meeting_id", name="uq_assignments_position_meeting"),
        CheckConstraint(_in("status", ASSIGNMENT_STATUS_LABELS), name="ck_assignments_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey("booking_positions.id"), nullable=False, index=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False, default="proposed")
    notes = db.Column(db.Text)
    cancellation_communicated_on = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    position = db.relationship("BookingPosition", back_populates="assignments")
    meeting = db.relationship("Meeting", back_populates="assignments")

    @property
    def status_display(self):
        return ASSIGNMENT_STATUS_LABELS[self.status]


class AssignmentLog(db.Model):
    """The append-only log (1.6): one entry for every creation, confirmation, change and
    cancellation, with who, when and a snapshot of the meeting. The database refuses UPDATE and
    DELETE (triggers below)."""

    __tablename__ = "assignment_log"

    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)  # UTC
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user_name = db.Column(db.String(200), nullable=False, default="")
    action = db.Column(db.String(30), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey("meeting_assignments.id"), index=True)
    position_id = db.Column(db.Integer, db.ForeignKey("booking_positions.id"), index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), index=True)
    interpreter_id = db.Column(db.Integer, db.ForeignKey("interpreters.id"))
    interpreter_name = db.Column(db.String(200))
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    meeting_snapshot = db.Column(db.JSON)
    reason = db.Column(db.Text)
    details = db.Column(db.JSON)


class Invoice(db.Model):
    """An invoice received from an interpreter or bureau, usually for several services (2.9)."""

    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    interpreter_id = db.Column(db.Integer, db.ForeignKey("interpreters.id"), nullable=False, index=True)
    reference = db.Column(db.String(100))  # sometimes only "ok" in the spreadsheet: no number
    received_on = db.Column(db.Date, nullable=False)
    period = db.Column(db.String(100))
    checked_on = db.Column(db.Date)
    checked_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    interpreter = db.relationship("Interpreter", backref="invoices")
    positions = db.relationship("BookingPosition", back_populates="invoice")
    checker = db.relationship("User", foreign_keys=[checked_by])

    @property
    def label(self):
        return self.reference or "(no reference)"


# ---------------------------------------------------------------------------------------------
# Append-only: the database itself refuses to change or remove a log entry (1.6).
# ---------------------------------------------------------------------------------------------

def _append_only(table, name):
    for verb in ("UPDATE", "DELETE"):
        event.listen(table, "after_create", DDL(
            "CREATE TRIGGER {n}_no_{v} BEFORE {V} ON {n} "
            "BEGIN SELECT RAISE(ABORT, '{n} is append-only'); END".format(n=name, v=verb.lower(), V=verb)
        ).execute_if(dialect="sqlite"))


APPEND_ONLY_TABLES = ("assignment_log", "meeting_changes")
_append_only(AssignmentLog.__table__, "assignment_log")
_append_only(MeetingChange.__table__, "meeting_changes")
