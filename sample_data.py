"""Fictitious data for trying PDC out and for tests - never real interpreters or assignments.

The meetings are shaped like the export of spic (see spic_copy.py) and go through the same
functions that the link with spic will use, so the link later only replaces the source.
"""
from datetime import date, time, timedelta

import planning
import spic_copy
from extensions import db
from models import Interpreter, User

ROOMS = [
    {"code": "R1", "omschrijving": "Room 1", "actief": True},
    {"code": "R2", "omschrijving": "Room 2", "actief": True},
    {"code": "HEM", "omschrijving": "Hemicycle", "actief": True},
]

INTERPRETERS = [
    # first name, last name, email, bureau, languages, engagement
    ("Agence", "Alpha", "planning@alpha-bureau.example", "Bureau Alpha", "English, German", "invoice"),
    ("Bureau", "Beta", "contact@beta-bureau.example", "Bureau Beta", "English, Spanish", "invoice"),
    ("Anna", "Peeters", "anna.peeters@example.org", "", "English", "invoice"),
    ("Luc", "Dubois", "luc.dubois@example.org", "", "English, Italian", "invoice"),
    ("Sarah", "Janssens", "sarah.janssens@example.org", "", "", "occasional_work"),
]


def monday_after(day):
    """The Monday of the next week."""
    return day + timedelta(days=7 - day.weekday())


def spic_items(monday):
    """Meetings as spic reports them: two weeks, the first definitive and the second pre-definitive."""
    def item(n, day, period, kind, start, end, room, type_, number, week=monday, week_status="definitief"):
        return {
            "id": "m-{:08x}".format(0xA0000000 + n), "maandag": week.isoformat(), "weekstatus": week_status,
            "datum": day.isoformat(), "periode": period, "status": "gepland", "versie": 1,
            "start_soort": kind, "start_uur": start if kind == "uur" else "",
            "effectief_begin": start, "verwacht_einde": end, "einde_volgende_dag": False, "zaal": room,
            "domein": "PARL", "assemblee": "FICT", "type": type_, "volgnummer": number, "volgnummer2": None,
            "commentaar": "fictitious",  # a field PDC does not use: kept in spic_data
        }

    next_week = monday + timedelta(days=7)
    return [
        item(1, monday, "PM", "uur", "12:00", "14:00", "R1", "uitgebreid-bureau", 1),
        item(2, monday + timedelta(days=2), "PM", "uur", "12:15", "14:00", "R1", "bureau", 2),
        item(3, monday + timedelta(days=2), "PM", "uur", "14:30", "", "HEM", "plenaire", 3),
        item(4, monday + timedelta(days=3), "AM", "uur", "09:30", "12:30", "R2", "commissie", 4),
        item(5, monday + timedelta(days=3), "PM", "na afloop van", "", "", "R2", "commissie", 5),
        item(6, next_week, "PM", "uur", "12:00", "14:00", "R1", "uitgebreid-bureau", 6, next_week, "pre-definitief"),
        item(7, next_week + timedelta(days=1), "AM", "uur", "10:00", "12:00", "R2", "commissie", 7, next_week,
             "pre-definitief"),
    ]


def load(today=None):
    """Interpreters, rooms, a fictitious copy of spic, an own meeting, and a few bookings."""
    today = today or date.today()
    monday = monday_after(today)
    user = User.query.filter_by(username="sample-data").first()
    if user is None:
        user = User(username="sample-data", name="Sample data")
        db.session.add(user)
        db.session.flush()

    if Interpreter.query.count() == 0:
        for position, (first, last, email, bureau, languages, engagement) in enumerate(INTERPRETERS, start=1):
            db.session.add(Interpreter(first_name=first, last_name=last, email=email, bureau_affiliation=bureau,
                                       priority_order=position, additional_languages=languages, engagement=engagement))
        db.session.flush()

    spic_copy.apply_rooms(ROOMS)
    for number, item in enumerate(spic_items(monday), start=1):
        spic_copy.apply_item(item, change_number=number)
    spic_copy.advance(len(spic_items(monday)), highest=len(spic_items(monday)))

    own = planning.create_own_meeting(dict(
        title="Reception for a delegation (fictitious)", date=monday + timedelta(days=1), period="AM",
        effective_start=time(10, 0), expected_end=time(11, 30), end_next_day=False, room="R1",
        interpreters_needed=2, category="special_event", notes=None, actual_end=None, charged_half_hours=None), user)

    from models import Meeting
    first = Meeting.query.filter_by(spic_id="m-a0000001").one()
    commission = Meeting.query.filter_by(spic_id="m-a0000004").one()
    by_name = {i.last_name: i for i in Interpreter.query.all()}

    # A confirmed bureau booking with one interpreter at the first meeting...
    slot = planning.get_or_create_slot(first.date, time(11, 0), time(15, 0), "Monday afternoon")
    booking = planning.create_booking(by_name["Alpha"], slot, 1, 4, user)
    planning.confirm_booking(booking, user)
    planning.set_position_name(booking.positions[0], "Interpreter One", user)
    planning.confirm_assignment(planning.assign(booking.positions[0], first, user), user)
    # ... a proposed booking of two positions, not assigned yet...
    slot = planning.get_or_create_slot(first.date + timedelta(days=2), time(12, 0), time(16, 0), "Wednesday afternoon")
    planning.create_booking(by_name["Beta"], slot, 2, 3, user, reason="Plenary session")
    # ... and a booking in occasional work for the commission, confirmed.
    slot = planning.get_or_create_slot(commission.date, time(9, 0), time(13, 0), "Thursday morning")
    booking = planning.create_booking(by_name["Janssens"], slot, 1, 4, user)
    planning.confirm_booking(booking, user)
    planning.confirm_assignment(planning.assign(booking.positions[0], commission, user), user)
    return own
