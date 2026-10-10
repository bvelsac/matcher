"""The copy of spic: how items from the export are applied (functional analysis 1.3, 2.7)."""
import pytest
from sqlalchemy import select

import spic_copy
from conftest import MONDAY, make_booking, make_interpreter, make_spic_meeting, spic_item
from extensions import db
from models import Meeting, MeetingChange, Room, SyncState
from planning import assign, worklist_cancelled_with_assignment


def history(meeting):
    return [c.kind for c in MeetingChange.query.filter_by(meeting_id=meeting.id).order_by(MeetingChange.id)]


def test_a_new_meeting_is_copied_with_everything_spic_knows(ctx):
    item = spic_item(1, commentaar="keep me", ambtenaren=["x"])
    meeting, changed = spic_copy.apply_item(item, change_number=10)
    db.session.flush()

    assert changed
    assert (meeting.origin, meeting.spic_id, meeting.status) == ("spic", "m-00000001", "planned")
    assert (meeting.date, meeting.period, meeting.room) == (MONDAY, "PM", "R1")
    assert (meeting.effective_start.strftime("%H:%M"), meeting.expected_end.strftime("%H:%M")) == ("14:00", "16:00")
    assert meeting.week == MONDAY and meeting.week_status == "definitive"
    assert meeting.last_change_number == 10 and meeting.first_seen_at is not None
    assert meeting.spic_data["commentaar"] == "keep me"  # fields PDC does not use are kept
    assert history(meeting) == ["new"]
    assert meeting.display_title == "PARL FICT commissie 1"


def test_interpreters_needed_defaults_to_three_for_a_plenary_and_two_otherwise(ctx):
    assert make_spic_meeting(1, day=MONDAY).interpreters_needed == 2
    plenary, _ = spic_copy.apply_item(spic_item(2, type="plenaire"))
    assert plenary.interpreters_needed == 3
    # The planner's own number survives later changes from spic.
    plenary.interpreters_needed = 4
    spic_copy.apply_item(spic_item(2, type="plenaire", zaal="R2"), change_number=5)
    assert plenary.interpreters_needed == 4


def test_missing_times_stay_empty(ctx):
    meeting, _ = spic_copy.apply_item(spic_item(1, start="", end="", start_soort="na afloop van"))
    assert (meeting.start_kind, meeting.start_time, meeting.effective_start, meeting.expected_end) == ("after", None, None, None)
    assert not meeting.time_known and meeting.duration_minutes is None
    assert meeting.period == "PM"  # always known


def test_applying_the_same_change_number_again_changes_nothing(ctx):
    meeting = make_spic_meeting(1, change_number=10)
    again, changed = spic_copy.apply_item(spic_item(1, zaal="R2"), change_number=10)
    assert not changed and again.room == "R1"
    assert history(meeting) == ["new"]
    older, changed = spic_copy.apply_item(spic_item(1, zaal="R2"), change_number=9)
    assert not changed and older.room == "R1"


def test_a_change_is_recorded_with_before_and_after(ctx):
    meeting = make_spic_meeting(1, change_number=10)
    spic_copy.apply_item(spic_item(1, start="14:30", zaal="R2", versie=2), change_number=11, changed_by="Kathy")
    db.session.flush()

    change = MeetingChange.query.filter_by(meeting_id=meeting.id, kind="changed").one()
    assert change.changed_by == "Kathy" and change.change_number == 11
    assert change.before["room"] == "R1" and change.after["room"] == "R2"
    assert change.before["effective_start"] == "14:00" and change.after["effective_start"] == "14:30"
    assert meeting.last_change_number == 11


def test_cancel_reopen_move_and_week_status_are_told_apart(ctx):
    meeting = make_spic_meeting(1, change_number=1)
    spic_copy.apply_item(spic_item(1, status="geannuleerd"), change_number=2)
    spic_copy.apply_item(spic_item(1, status="gepland"), change_number=3)
    next_monday = MONDAY.replace(day=MONDAY.day + 7)
    spic_copy.apply_item(spic_item(1, day=next_monday), change_number=4)
    spic_copy.apply_item(spic_item(1, day=next_monday, weekstatus="pre-definitief"), change_number=5)
    db.session.flush()
    assert history(meeting) == ["new", "cancelled", "reopened", "moved", "week_status"]
    assert meeting.week == next_monday  # same meeting, other week


def test_deleting_keeps_the_copy_and_a_restore_brings_back_the_same_meeting(ctx):
    meeting = make_spic_meeting(1, change_number=1)
    spic_copy.apply_item({"id": "m-00000001", "status": "verwijderd"}, change_number=2)  # only the id
    assert meeting.status == "deleted" and meeting.deleted_in_spic_at is not None
    assert meeting.room == "R1" and meeting.date == MONDAY  # the last state is kept

    restored, _ = spic_copy.apply_item(spic_item(1), change_number=3)
    assert restored.id == meeting.id and restored.status == "planned" and restored.deleted_in_spic_at is None
    assert Meeting.query.count() == 1
    db.session.flush()
    assert history(meeting) == ["new", "deleted", "restored"]

    # Nothing to keep of a meeting PDC never received.
    assert spic_copy.apply_item({"id": "m-0000ffff", "status": "verwijderd"}) == (None, False)


def test_a_week_back_in_concept_hides_the_meetings_but_keeps_them_and_their_assignments(ctx, user):
    meeting = make_spic_meeting(1)
    booking = make_booking(make_interpreter(), user=user)
    assign(booking.positions[0], meeting, user)
    db.session.flush()
    assert meeting.is_visible

    changed = spic_copy.apply_week_status(MONDAY, "concept", change_number=7)
    db.session.flush()
    assert changed == [meeting] and meeting.week_status == "concept"
    assert not meeting.is_visible
    assert Meeting.query.filter(Meeting.visible_filter()).count() == 0
    assert Meeting.query.count() == 1
    assert meeting.active_assignments  # kept
    assert worklist_cancelled_with_assignment() == [meeting]  # and flagged to the planner

    spic_copy.apply_week_status(MONDAY, "definitief", change_number=8)
    assert meeting.is_visible


def test_the_last_change_number_is_remembered(ctx):
    assert db.session.get(SyncState, 1) is None
    spic_copy.advance(12, highest=15)
    spic_copy.advance(10)  # never goes back
    state = db.session.get(SyncState, 1)
    assert (state.last_change_number, state.spic_highest_number) == (12, 15)
    assert state.last_success_at is not None


def test_rooms_are_copied(ctx):
    spic_copy.apply_rooms([{"code": "R1", "omschrijving": "Room 1", "actief": True}])
    spic_copy.apply_rooms([{"code": "R1", "omschrijving": "Room one", "actief": False}])
    room = db.session.get(Room, "R1")
    assert (room.description, room.active) == ("Room one", False)


@pytest.mark.parametrize("changes, message", [
    ({"id": ""}, "without an id"),
    ({"datum": "tomorrow"}, "datum"),
    ({"periode": "evening"}, "periode"),
    ({"status": "weird"}, "status"),
    ({"start_uur": "25:00"}, "start_uur"),
    ({"volgnummer": "x"}, "volgnummer"),
])
def test_an_item_that_cannot_be_read_is_refused(ctx, changes, message):
    with pytest.raises(spic_copy.SpicItemError, match=message):
        spic_copy.apply_item(spic_item(1, **changes))
    assert db.session.execute(select(Meeting)).first() is None
