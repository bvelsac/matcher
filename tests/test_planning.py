"""The planner's rules: own meetings, bookings, assignments, the log, overtime, invoices, work lists."""
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError

import planning
import spic_copy
from conftest import MONDAY, make_booking, make_interpreter, make_spic_meeting, spic_item
from extensions import db
from models import AssignmentLog, Meeting, MeetingAssignment, MeetingChange
from planning import PlanningError


def own_fields(**changes):
    fields = dict(title="Reception", date=MONDAY, period="PM", effective_start=time(14, 0), expected_end=time(16, 0),
                  end_next_day=False, room="R1", interpreters_needed=2, category="special_event", notes=None,
                  actual_end=None, charged_half_hours=None)
    fields.update(changes)
    return fields


def actions(**filters):
    return [e.action for e in AssignmentLog.query.filter_by(**filters).order_by(AssignmentLog.id)]


# -- own meetings --------------------------------------------------------------------------------

def test_an_own_meeting_can_be_deleted_until_an_interpreter_was_assigned(ctx, user):
    meeting = planning.create_own_meeting(own_fields(), user)
    assert planning.can_delete_meeting(meeting)

    booking = make_booking(make_interpreter(), user=user)
    assignment = planning.assign(booking.positions[0], meeting, user)
    assert not planning.can_delete_meeting(meeting)
    planning.cancel_assignment(assignment, user)
    # Even a cancelled assignment, and the log entries, mean the meeting stays (BR-MTG-006).
    with pytest.raises(PlanningError, match="can only be cancelled"):
        planning.delete_own_meeting(meeting, user)
    planning.set_own_meeting_status(meeting, "cancelled", user)
    assert meeting.status == "cancelled"


def test_deleting_an_own_meeting_leaves_a_line_in_the_history(ctx, user):
    meeting = planning.create_own_meeting(own_fields(), user)
    meeting_id = meeting.id
    planning.delete_own_meeting(meeting, user)
    db.session.flush()
    assert Meeting.query.count() == 0
    kinds = [c.kind for c in MeetingChange.query.filter_by(meeting_id=meeting_id).order_by(MeetingChange.id)]
    assert kinds == ["new", "deleted"]


def test_a_meeting_from_spic_cannot_be_deleted_or_edited_in_pdc(ctx, user):
    meeting = make_spic_meeting(1)
    with pytest.raises(PlanningError, match="deleted in spic"):
        planning.delete_own_meeting(meeting, user)
    with pytest.raises(PlanningError, match="cancelled in spic"):
        planning.set_own_meeting_status(meeting, "cancelled", user)
    with pytest.raises(PlanningError, match="Room of a meeting from spic"):
        planning.update_meeting(meeting, {"room": "R9"}, user)
    # What PDC keeps itself can be changed, and the change is in the history.
    assert planning.update_meeting(meeting, {"interpreters_needed": 4, "notes": "VIP"}, user)
    db.session.flush()
    change = MeetingChange.query.filter_by(meeting_id=meeting.id, kind="edited").one()
    assert change.changed_by == "Plan Ner" and change.after == {"interpreters_needed": 4, "notes": "VIP"}
    assert not planning.update_meeting(meeting, {"interpreters_needed": 4}, user)  # nothing changed, no line


def test_database_rules_for_meetings(ctx):
    db.session.add(Meeting(origin="spic", status="planned", date=MONDAY, period="AM"))  # no spic id
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()
    db.session.add(Meeting(origin="own", status="planned", date=MONDAY, period="AM", title="x"))  # no room
    with pytest.raises(IntegrityError):
        db.session.flush()
    db.session.rollback()
    db.session.add(Meeting(origin="own", status="deleted", date=MONDAY, period="AM", title="x", room="R1",
                           category="parliament", interpreters_needed=1))
    with pytest.raises(IntegrityError):
        db.session.flush()


# -- bookings and positions ----------------------------------------------------------------------

def test_an_individual_has_one_position_and_a_bureau_several(ctx, user):
    individual, bureau = make_interpreter("Solo"), make_interpreter("Alpha", bureau="Bureau Alpha")
    slot = planning.get_or_create_slot(MONDAY, time(9, 0), time(13, 0))
    with pytest.raises(PlanningError, match="exactly one position"):
        planning.create_booking(individual, slot, 2, 4, user)
    booking = planning.create_booking(bureau, slot, 3, 4, user)
    assert [p.position_number for p in booking.positions] == [1, 2, 3]
    assert booking.quantity_booked == 3 and booking.status == "proposed"
    planning.add_position(booking, user)
    assert booking.quantity_booked == 4
    with pytest.raises(PlanningError):
        planning.create_booking(bureau, slot, 1, 5, user)  # the forfait is 3 or 4
    with pytest.raises(PlanningError, match="at least one"):
        planning.create_booking(bureau, slot, 0, 4, user)


def test_a_slot_is_shared_and_must_be_valid(ctx):
    first = planning.get_or_create_slot(MONDAY, time(9, 0), time(13, 0))
    assert planning.get_or_create_slot(MONDAY, time(9, 0), time(13, 0)) is first
    with pytest.raises(PlanningError):
        planning.get_or_create_slot(MONDAY, time(13, 0), time(9, 0))


def test_an_interpreter_has_no_overlapping_confirmed_bookings(ctx, user):
    interpreter = make_interpreter()
    make_booking(interpreter, start=time(9, 0), end=time(13, 0), user=user)
    second = make_booking(interpreter, start=time(12, 0), end=time(16, 0), user=user, confirm=False)
    with pytest.raises(PlanningError, match="already has a confirmed booking"):
        planning.confirm_booking(second, user)
    make_booking(interpreter, start=time(13, 0), end=time(16, 0), user=user)  # right after: fine


def test_completing_needs_the_name_of_every_person_sent(ctx, user):
    booking = make_booking(make_interpreter(), user=user)
    with pytest.raises(PlanningError, match="name of the person sent"):
        planning.complete_booking(booking, user)
    planning.set_position_name(booking.positions[0], "Pat Person", user)
    planning.complete_booking(booking, user)
    assert booking.status == "completed"


def test_replacing_the_person_sent_keeps_the_assignments_and_notes_it(ctx, user):
    meeting = make_spic_meeting(1)
    position = make_booking(make_interpreter("Alpha", bureau="Bureau Alpha"), user=user).positions[0]
    assignment = planning.assign(position, meeting, user)
    planning.set_position_name(position, "First Person", user)
    planning.set_position_name(position, "Second Person", user)
    assert assignment.status == "proposed" and position.interpreter_name == "Second Person"
    assert "First Person -> Second Person" in position.notes
    entry = AssignmentLog.query.filter_by(action="name_changed").order_by(AssignmentLog.id.desc()).first()
    assert entry.details["from"] == "First Person" and entry.details["to"] == "Second Person"


# -- assignments ---------------------------------------------------------------------------------

def test_assigning_logs_a_snapshot_of_the_meeting(ctx, user):
    meeting = make_spic_meeting(1, change_number=5)
    position = make_booking(make_interpreter(), user=user).positions[0]
    assignment = planning.assign(position, meeting, user)
    planning.confirm_assignment(assignment, user)
    db.session.flush()

    assert actions(assignment_id=assignment.id) == ["proposed", "confirmed"]
    entry = AssignmentLog.query.filter_by(action="confirmed").one()
    assert entry.user_name == "Plan Ner" and entry.recorded_at is not None
    assert entry.meeting_snapshot["spic_id"] == "m-00000001"
    assert entry.meeting_snapshot["effective_start"] == "14:00" and entry.meeting_snapshot["room"] == "R1"
    assert entry.meeting_snapshot["last_change_number"] == 5
    assert entry.details["forfait_hours"] == 4 and entry.details["engagement"] == "invoice"
    assert meeting.staffing_count == 1 and meeting.staffing_status == "understaffed"


def test_an_assignment_must_fit_the_booking_and_not_overlap(ctx, user):
    position = make_booking(make_interpreter(), start=time(13, 0), end=time(17, 0), user=user).positions[0]
    early = make_spic_meeting(1, start="09:00", end="10:00")
    late = make_spic_meeting(2, start="16:00", end="18:00")
    other_day = make_spic_meeting(3, day=MONDAY + timedelta(days=1))
    for meeting, message in [(early, "outside the booking"), (late, "ends after the booking"), (other_day, "booking is for")]:
        with pytest.raises(PlanningError, match=message):
            planning.assign(position, meeting, user)

    first = make_spic_meeting(4, start="13:00", end="15:00")
    overlapping = make_spic_meeting(5, start="14:30", end="16:00")
    adjacent = make_spic_meeting(6, start="15:00", end="16:30")
    planning.assign(position, first, user)
    with pytest.raises(PlanningError, match="already at"):
        planning.assign(position, overlapping, user)
    planning.assign(position, adjacent, user)
    with pytest.raises(PlanningError, match="already assigned to this meeting"):
        planning.assign(position, first, user)


def test_two_positions_of_one_bureau_booking_can_be_at_the_same_meeting(ctx, user):
    meeting = make_spic_meeting(1)
    booking = make_booking(make_interpreter("Alpha", bureau="Bureau Alpha"), positions=2, user=user)
    for position in booking.positions:
        planning.confirm_assignment(planning.assign(position, meeting, user), user)
    assert meeting.staffing_count == 2 and meeting.staffing_status == "fully_staffed"


def test_unknown_times_are_allowed_but_never_count_as_overlap(ctx, user):
    position = make_booking(make_interpreter(), user=user).positions[0]
    unknown = make_spic_meeting(1, start="", end="", start_soort="na afloop van")
    known = make_spic_meeting(2, start="14:00", end="16:00")
    planning.assign(position, unknown, user)
    planning.assign(position, known, user)
    assert not unknown.time_known and len(position.active_assignments) == 2


def test_only_planned_visible_meetings_get_interpreters(ctx, user):
    position = make_booking(make_interpreter(), user=user).positions[0]
    cancelled = make_spic_meeting(1, status="geannuleerd")
    with pytest.raises(PlanningError, match="cancelled meeting"):
        planning.assign(position, cancelled, user)
    concept = make_spic_meeting(2, weekstatus="concept")
    with pytest.raises(PlanningError, match="back in concept"):
        planning.assign(position, concept, user)


def test_confirming_needs_a_confirmed_booking(ctx, user):
    meeting = make_spic_meeting(1)
    position = make_booking(make_interpreter(), user=user, confirm=False).positions[0]
    assignment = planning.assign(position, meeting, user)
    with pytest.raises(PlanningError, match="Confirm the booking first"):
        planning.confirm_assignment(assignment, user)


def test_a_cancelled_assignment_comes_back_when_assigned_again(ctx, user):
    meeting = make_spic_meeting(1)
    position = make_booking(make_interpreter(), user=user).positions[0]
    assignment = planning.assign(position, meeting, user)
    planning.cancel_assignment(assignment, user, reason="illness", communicated_on=date(2030, 1, 3))
    assert assignment.status == "cancelled" and assignment.cancellation_communicated_on == date(2030, 1, 3)
    again = planning.assign(position, meeting, user)
    assert again is assignment and again.status == "proposed" and again.cancellation_communicated_on is None
    assert MeetingAssignment.query.count() == 1  # one row, never a second one (BR-ASGN-006)
    assert actions(assignment_id=assignment.id) == ["proposed", "cancelled", "proposed"]
    assert AssignmentLog.query.filter_by(action="cancelled").one().reason == "illness"


def test_cancelling_a_booking_cancels_positions_and_assignments_with_a_log(ctx, user):
    booking = make_booking(make_interpreter("Alpha", bureau="Bureau Alpha"), positions=2, user=user)
    meeting = make_spic_meeting(1)
    assignments = [planning.assign(p, meeting, user) for p in booking.positions]
    planning.cancel_booking(booking, user, reason="bureau cannot")
    assert booking.status == "cancelled"
    assert all(p.status == "cancelled" for p in booking.positions)
    assert all(a.status == "cancelled" for a in assignments)
    assert actions(booking_id=booking.id).count("cancelled") == 2
    assert MeetingAssignment.query.count() == 2  # cancelled, never deleted


def test_cancelling_one_position_leaves_the_others(ctx, user):
    booking = make_booking(make_interpreter("Alpha", bureau="Bureau Alpha"), positions=2, user=user)
    meeting = make_spic_meeting(1)
    first, second = [planning.assign(p, meeting, user) for p in booking.positions]
    planning.cancel_position(booking.positions[0], user, reason="ill")
    assert (first.status, second.status) == ("cancelled", "proposed")
    assert booking.quantity_booked == 1 and booking.free_positions == []


def test_a_meeting_cancelled_in_spic_keeps_its_assignments_until_the_planner_decides(ctx, user):
    meeting = make_spic_meeting(1, change_number=1)
    position = make_booking(make_interpreter(), user=user).positions[0]
    assignment = planning.assign(position, meeting, user)
    planning.confirm_assignment(assignment, user)
    spic_copy.apply_item(spic_item(1, status="geannuleerd"), change_number=2)
    db.session.flush()

    assert meeting.status == "cancelled" and assignment.status == "confirmed"
    assert planning.worklist_cancelled_with_assignment() == [meeting]
    planning.cancel_assignment(assignment, user, reason="meeting cancelled", communicated_on=date(2030, 1, 4))
    assert planning.worklist_cancelled_with_assignment() == []


# -- the log cannot be changed -------------------------------------------------------------------

def test_the_log_and_the_history_are_append_only(ctx, user):
    meeting = make_spic_meeting(1)
    planning.assign(make_booking(make_interpreter(), user=user).positions[0], meeting, user)
    db.session.commit()

    for table in ("assignment_log", "meeting_changes"):
        for statement in ("UPDATE {} SET id = id + 100", "DELETE FROM {}"):
            with pytest.raises(DatabaseError, match="append-only"):
                db.session.execute(db.text(statement.format(table)))
            db.session.rollback()
    assert AssignmentLog.query.count() >= 1 and MeetingChange.query.count() >= 1


# -- forfait and overtime ------------------------------------------------------------------------

@pytest.mark.parametrize("minutes, forfait, expected", [
    (180, 3, 0), (190, 3, 1), (210, 3, 1), (211, 3, 2), (240, 4, 0), (241, 4, 1), (300, 4, 2), (60, 4, 0),
])
def test_a_started_half_hour_counts_in_full(minutes, forfait, expected):
    start = datetime(2030, 1, 7, 14, 0)
    assert planning.half_hours_over(start, start + timedelta(minutes=minutes), forfait) == expected


def test_overtime_is_unknown_without_a_real_end():
    assert planning.half_hours_over(None, datetime(2030, 1, 7, 18, 0), 4) is None


def test_overtime_follows_the_real_end_of_the_meeting_and_flags_a_difference(ctx, user):
    meeting = make_spic_meeting(1, start="14:00", end="17:00")
    booking = make_booking(make_interpreter(), forfait=3, user=user)
    position = booking.positions[0]
    planning.assign(position, meeting, user)
    assert planning.position_overtime(position) is None
    assert planning.meeting_overtime_check(meeting) == {"implied": None, "charged": None, "mismatch": False}

    planning.update_meeting(meeting, {"actual_end": time(17, 40), "charged_half_hours": 1}, user)
    assert planning.position_overtime(position) == 2  # 3h40 against a forfait of 3h: 40 minutes, two half hours
    assert planning.paid_hours(position) == 4.0
    check = planning.meeting_overtime_check(meeting)
    assert check == {"implied": 2, "charged": 1, "mismatch": True}
    planning.update_meeting(meeting, {"charged_half_hours": 2}, user)
    assert not planning.meeting_overtime_check(meeting)["mismatch"]


def test_hours_recorded_for_a_position_take_precedence(ctx, user):
    position = make_booking(make_interpreter(), forfait=4, user=user).positions[0]
    planning.record_hours(position, datetime(2030, 1, 7, 13, 0), datetime(2030, 1, 7, 17, 45), user)
    assert planning.position_overtime(position) == 2 and planning.paid_hours(position) == 5.0
    with pytest.raises(PlanningError, match="end must be after"):
        planning.record_hours(position, datetime(2030, 1, 7, 13, 0), datetime(2030, 1, 7, 12, 0), user)
    assert actions(position_id=position.id).count("hours_recorded") == 1


# -- work list: changed since the confirmation ---------------------------------------------------

def test_a_change_after_the_confirmation_shows_until_the_planner_checks_it(ctx, user):
    meeting = make_spic_meeting(1, change_number=1)
    assignment = planning.assign(make_booking(make_interpreter(), user=user).positions[0], meeting, user)
    planning.confirm_assignment(assignment, user)
    db.session.flush()
    assert planning.worklist_changed_since_confirmation() == []

    spic_copy.apply_item(spic_item(1, start="15:00", end="16:30", zaal="R2"), change_number=2)
    db.session.flush()
    (found, entry, changes), = planning.worklist_changed_since_confirmation()
    assert found is assignment and entry.action == "confirmed"
    assert changes == {"effective_start": ("14:00", "15:00"), "expected_end": ("16:00", "16:30"), "room": ("R1", "R2")}

    planning.check_assignment(assignment, user)
    db.session.flush()
    assert planning.worklist_changed_since_confirmation() == []
    spic_copy.apply_item(spic_item(1, start="15:00", end="16:30", zaal="R3"), change_number=3)
    db.session.flush()
    assert list(planning.worklist_changed_since_confirmation()[0][2]) == ["room"]  # compared with the check


def test_a_proposed_assignment_is_not_on_that_list(ctx, user):
    meeting = make_spic_meeting(1, change_number=1)
    planning.assign(make_booking(make_interpreter(), user=user).positions[0], meeting, user)
    spic_copy.apply_item(spic_item(1, zaal="R2"), change_number=2)
    db.session.flush()
    assert planning.worklist_changed_since_confirmation() == []


# -- invoices and Dimona -------------------------------------------------------------------------

def completed_booking(interpreter, user, day=MONDAY, positions=1):
    booking = make_booking(interpreter, day=day, positions=positions, user=user)
    for position in booking.positions:
        planning.set_position_name(position, "Pat Person", user)
    planning.complete_booking(booking, user)
    return booking


def test_services_without_an_invoice_form_a_work_list_until_linked(ctx, user):
    bureau = make_interpreter("Alpha", bureau="Bureau Alpha")
    first = completed_booking(bureau, user, positions=2)
    second = completed_booking(bureau, user, day=MONDAY + timedelta(days=1))
    assert len(planning.worklist_invoice_not_received()) == 3

    invoice = planning.record_invoice(bureau, "2030-017", date(2030, 2, 1), "January 2030", None, user)
    planning.link_invoice(invoice, first.positions + second.positions[:1], user)
    db.session.flush()
    assert planning.worklist_invoice_not_received() == []
    assert actions().count("invoice_linked") == 3

    planning.unlink_invoice(second.positions[0], user)
    assert planning.worklist_invoice_not_received() == [second.positions[0]]
    assert "invoice_unlinked" in actions()
    planning.mark_invoice_checked(invoice, user)
    assert invoice.checked_on is not None and invoice.checked_by == user.id


def test_an_invoice_covers_only_services_of_its_supplier_and_each_service_once(ctx, user):
    alpha, beta = make_interpreter("Alpha", bureau="Bureau Alpha"), make_interpreter("Beta", bureau="Bureau Beta")
    alpha_position = completed_booking(alpha, user).positions[0]
    invoice = planning.record_invoice(beta, None, date(2030, 2, 1), None, None, user)
    with pytest.raises(PlanningError, match="supplier of this invoice"):
        planning.link_invoice(invoice, [alpha_position], user)

    own = planning.record_invoice(alpha, "A-1", date(2030, 2, 1), None, None, user)
    other = planning.record_invoice(alpha, "A-2", date(2030, 2, 2), None, None, user)
    planning.link_invoice(own, [alpha_position], user)
    with pytest.raises(PlanningError, match="already linked to another invoice"):
        planning.link_invoice(other, [alpha_position], user)
    assert invoice.reference is None  # "ok" without a number is allowed


def test_occasional_work_means_dimona_and_no_invoice(ctx, user):
    worker = make_interpreter("Janssens", engagement="occasional_work")
    with pytest.raises(PlanningError, match="no invoice, a Dimona declaration instead"):
        planning.record_invoice(worker, "x", date(2030, 2, 1), None, None, user)
    position = completed_booking(worker, user).positions[0]
    assert planning.worklist_invoice_not_received() == []
    assert planning.worklist_dimona_to_declare() == [position]

    planning.set_dimona(position, True, user)
    assert planning.worklist_dimona_to_declare() == []
    planning.set_dimona(position, False, user)
    assert actions(position_id=position.id)[-2:] == ["dimona_declared", "dimona_withdrawn"]

    invoice_worker = make_interpreter("Peeters")
    with pytest.raises(PlanningError, match="only for occasional work"):
        planning.set_dimona(completed_booking(invoice_worker, user).positions[0], True, user)


def test_only_completed_services_are_on_the_invoice_and_dimona_lists(ctx, user):
    make_booking(make_interpreter(), user=user)  # confirmed, not completed
    assert planning.worklist_invoice_not_received() == []
    assert planning.worklist_counts() == {"cancelled": 0, "changed": 0, "invoice": 0, "dimona": 0}
