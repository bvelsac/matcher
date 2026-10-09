"""Database models for Phase 1: users, interpreters, meetings and the editing lock.

Phase 2 adds the availability and booking model described in
docs/functional-analysis.md (time slots, availability declarations,
bookings and meeting assignments).
"""
from datetime import datetime

from flask_login import UserMixin

from extensions import db

MEETING_CATEGORIES = (
    ("parliament", "Parliament"),
    ("affiliated_organization", "Affiliated organization"),
    ("external_group", "External group"),
    ("special_event", "Special event"),
)
CATEGORY_LABELS = dict(MEETING_CATEGORIES)


class User(UserMixin, db.Model):
    """A person who logs in: editors change data, viewers only read."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("editor", "viewer", name="user_roles"), default="viewer", nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_editor(self):
        return self.role == "editor"

    def __repr__(self):
        return "<User {}>".format(self.username)


class Interpreter(db.Model):
    """An individual interpreter or a bureau, ranked in the legal priority order."""

    __tablename__ = "interpreters"

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    @property
    def display_name(self):
        if self.bureau_affiliation:
            return "{} ({})".format(self.full_name, self.bureau_affiliation)
        return self.full_name

    def __repr__(self):
        return "<Interpreter {}>".format(self.full_name)


class Meeting(db.Model):
    """A meeting that needs interpreters."""

    __tablename__ = "meetings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=False)
    estimated_duration = db.Column(db.Integer, nullable=False)  # hours
    interpreters_needed = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    category = db.Column(
        db.Enum(*CATEGORY_LABELS.keys(), name="meeting_categories"), nullable=False
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship("User", backref="created_meetings")

    @property
    def datetime_combined(self):
        return datetime.combine(self.date, self.time)

    @property
    def category_display(self):
        return CATEGORY_LABELS.get(self.category, self.category)

    def __repr__(self):
        return "<Meeting {} on {}>".format(self.name, self.date)


class SystemLock(db.Model):
    """Editing lock: while one editor holds it, other editors cannot change data."""

    __tablename__ = "system_locks"

    id = db.Column(db.Integer, primary_key=True)
    locked_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Unique, so two editors cannot take the same lock at the same moment.
    lock_type = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    locked_by_user = db.relationship("User", backref="system_locks")

    def __repr__(self):
        return "<SystemLock {}>".format(self.lock_type)
