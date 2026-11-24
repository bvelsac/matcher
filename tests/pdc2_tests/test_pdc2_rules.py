"""Bookings, offers, marks, the GM register and the log of PDC2."""
from datetime import date, datetime

import pytest
from sqlalchemy.exc import DatabaseError

from pdc2 import rules
from pdc2.extensions import db
from pdc2.models import Booking, Exclusion, Gm, LogEntry, Offer, User
from pdc2.rules import RuleError

DAY = date(2030, 1, 7)


@pytest.fixture
def ctx(pdc2_app):
    with pdc2_app.app_context():
        yield


@pytest.fixture
def user(ctx):
    u = User(username="planner", name="Plan Ner")
    db.session.add(u)
    db.session.flush()
    return u


def gm(user, email="a@example.org", languages=("nl",), role="redacteur", roles=("revisor",), active=True):
    return rules.save_gm(None, {"first_name": "Ann", "last_name": "Test", "email": email, "languages": list(languages),
                                "standard_role": role, "roles": list(roles), "active": active}, user)


def test_a_gm_needs_a_language_and_a_role_and_a_unique_email(user):
    with pytest.raises(RuleError, match="language"):
        gm(user, languages=())
    first = gm(user)
    assert first.capable_roles == ["redacteur", "revisor"] and first.email == "a@example.org"
    with pytest.raises(RuleError, match="already has this email"):
        gm(user, email="A@example.org")


def test_booking_follows_the_rules_of_the_analysis(user):
    g = gm(user)
    rules.offer(g, DAY, "AM", user)
    booking = rules.book(g, DAY, "AM", "revisor", "nl", user)
    assert booking.status == "proposed" and not booking.without_offer and booking.hours == 3
    with pytest.raises(RuleError, match="BR-GM-001"):
        rules.book(g, DAY, "AM", "redacteur", "nl", user)
    with pytest.raises(RuleError, match="cannot work as vertaler"):
        rules.book(g, DAY, "PM", "vertaler", "nl", user)
    with pytest.raises(RuleError, match="does not work in FR"):
        rules.book(g, DAY, "PM", "redacteur", "fr", user)
    without = rules.book(g, DAY, "PM", "redacteur", "nl", user)
    assert without.without_offer and without.hours == 4
    rules.cancel(booking, user)
    again = rules.book(g, DAY, "AM", "redacteur", "nl", user)          # a cancelled one frees the half-day
    assert Booking.query.count() == 3 and again.status == "proposed"


def test_the_database_allows_one_active_booking_per_half_day(user):
    g = gm(user)
    db.session.add_all([Booking(gm=g, date=DAY, period="AM", role="redacteur", language="nl"),
                        Booking(gm=g, date=DAY, period="AM", role="redacteur", language="nl")])
    with pytest.raises(Exception):
        db.session.flush()


def test_confirm_cancel_and_dimona(user):
    g = gm(user)
    b = rules.book(g, DAY, "AM", "redacteur", "nl", user)
    with pytest.raises(RuleError, match="confirmed booking"):
        rules.set_dimona(b, True, user)
    rules.confirm(b, user)
    assert rules.dimona_to_declare() == [b]
    rules.set_dimona(b, True, user)
    assert rules.dimona_to_declare() == []
    rules.cancel(b, user, "illness")
    with pytest.raises(RuleError):
        rules.cancel(b, user)
    actions = [e.action for e in LogEntry.query.order_by(LogEntry.id)]
    assert actions[-4:] == ["booked", "confirmed", "dimona_declared", "cancelled"]


def test_a_newer_answer_replaces_an_older_one(user):
    g = gm(user)
    rules.offer(g, DAY, "AM", user, "import", datetime(2030, 1, 2, 10))
    rules.offer(g, DAY, "AM", user, "import", datetime(2030, 1, 1, 10))    # older: ignored
    assert Offer.query.one().answered_at == datetime(2030, 1, 2, 10)


def test_import_of_the_google_form(user):
    gm(user, email="ann@example.org")
    text = ("Tijdstempel;E-mailadres;Maandag 2030-01-07 VM;Maandag 07/01/2030 NM;Dinsdag 2030-01-08 AM\n"
            "2030-01-02 10:00:00;Ann@example.org;ja;;x\n"
            "2030-01-02 11:00:00;nobody@example.org;ja;ja;ja\n")
    count, unknown = rules.import_offers(text, user)
    assert count == 2 and unknown == ["nobody@example.org"]
    assert sorted((o.date.isoformat(), o.period) for o in Offer.query) == [("2030-01-07", "AM"), ("2030-01-08", "AM")]
    with pytest.raises(RuleError, match="email address"):
        rules.import_offers("a,b\n1,2\n", user)


def test_marking_a_staff_half_day_needs_a_reason(user):
    with pytest.raises(RuleError, match="reason"):
        rules.mark("ajans", "Anke", DAY, "AM", " ", user)
    rules.mark("ajans", "Anke", DAY, "AM", "training", user)
    assert Exclusion.query.one().reason == "training"
    rules.unmark("ajans", DAY, "AM", user)
    assert Exclusion.query.count() == 0
    assert [e.action for e in LogEntry.query.order_by(LogEntry.id)] == ["marked", "unmarked"]


def test_the_log_is_append_only(user):
    gm(user)
    db.session.commit()
    for statement in ("UPDATE log SET action = 'x'", "DELETE FROM log"):
        with pytest.raises(DatabaseError, match="append-only"):
            db.session.execute(db.text(statement))
        db.session.rollback()
    assert LogEntry.query.count() == 1


def test_gm_inactive_cannot_be_booked(user):
    g = gm(user, active=False)
    with pytest.raises(RuleError, match="not active"):
        rules.book(g, DAY, "AM", "redacteur", "nl", user)
    assert Gm.query.count() == 1
