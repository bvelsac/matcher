"""The planner's rules: own meetings, bookings, assignments, invoices, overtime and the work lists.

Every function changes the session but does not commit; the caller (a view, a command or a test)
commits, so a handling is one transaction. A rule that is broken raises PlanningError with a
message the planner can read. Everything that changes an assignment, a booking, a position or
an invoice adds an entry to the append-only assignment log (functional analysis 1.6).
"""
import math
from datetime import date, datetime, time

from sqlalchemy import func

from extensions import db
from models import (
    AssignmentLog, Booking, BookingPosition, Interpreter, Invoice, Meeting, MeetingAssignment,
    MeetingChange, TimeSlot, WATCHED_SNAPSHOT_FIELDS, utcnow,
)


class PlanningError(Exception):
    """A rule of the functional analysis forbids this; the message says which."""


def user_name(user):
    return (user.name or user.username) if user else ""


def user_id(user):
    return user.id if user else None


def jsonable(value):
    if isinstance(value, (date, time, datetime)):
        return value.isoformat(timespec="minutes") if isinstance(value, time) else value.isoformat()
    return value


# ---------------------------------------------------------------------------------------------
# The log and the history
# ---------------------------------------------------------------------------------------------

def log(action, user, *, assignment=None, position=None, booking=None, meeting=None,
        interpreter=None, reason=None, details=None):
    """Add an entry to the assignment log. Whatever can be derived from the arguments is filled in
    (the position of an assignment, the booking of a position...). `details` keeps the forfait,
    the engagement and the supplier as they were at that moment (BR-POS-009)."""
    if assignment is not None:
        position = position or assignment.position
        meeting = meeting or assignment.meeting
    if position is not None:
        booking = booking or position.booking
    if booking is not None:
        interpreter = interpreter or booking.interpreter
    extra = {}
    if booking is not None:
        extra.update(forfait_hours=booking.forfait_hours, slot=booking.slot.label)
    if interpreter is not None:
        extra.update(supplier=interpreter.display_name, engagement=interpreter.engagement)
    extra.update(details or {})
    if position is not None:
        person = position.person
    else:
        person = interpreter.display_name if interpreter is not None else None
    entry = AssignmentLog(
        user_id=user_id(user), user_name=user_name(user), action=action,
        assignment_id=assignment.id if assignment is not None else None,
        position_id=position.id if position is not None else None,
        booking_id=booking.id if booking is not None else None,
        interpreter_id=interpreter.id if interpreter is not None else None,
        interpreter_name=person,
        meeting_id=meeting.id if meeting is not None else None,
        meeting_snapshot=meeting.snapshot() if meeting is not None else None,
        reason=reason or None, details=extra or None,
    )
    db.session.add(entry)
    return entry


def record_change(meeting, kind, before, after, changed_by, change_number=None):
    """Add a line to the history of a meeting (the copy of spic or an own meeting)."""
    entry = MeetingChange(
        meeting_id=meeting.id, change_number=change_number, kind=kind,
        before={k: jsonable(v) for k, v in before.items()} if before is not None else None,
        after={k: jsonable(v) for k, v in after.items()} if after is not None else None,
        changed_by=changed_by,
    )
    db.session.add(entry)
    return entry


# ---------------------------------------------------------------------------------------------
# Own meetings (1.5, BR-MTG-006)
# ---------------------------------------------------------------------------------------------

# Fields the planner keeps in PDC for every meeting, also those that come from spic.
PDC_FIELDS = ("interpreters_needed", "category", "notes", "actual_end", "charged_half_hours")
# Fields of an own meeting, fully editable.
OWN_FIELDS = ("title", "date", "period", "effective_start", "expected_end", "end_next_day", "room") + PDC_FIELDS


def create_own_meeting(fields, user):
    start = fields.get("effective_start")
    meeting = Meeting(origin="own", status="planned", created_by=user_id(user), start_kind="time",
                      start_time=start, **fields)
    db.session.add(meeting)
    db.session.flush()
    record_change(meeting, "new", None, meeting.snapshot(), user_name(user))
    return meeting


def update_meeting(meeting, fields, user):
    """Save changed fields. A spic meeting accepts only the fields PDC keeps itself (BR-MTG-004)."""
    allowed = OWN_FIELDS if meeting.origin == "own" else PDC_FIELDS
    before, after = {}, {}
    for name, value in fields.items():
        if name not in allowed:
            raise PlanningError("{} of a meeting from spic is changed in spic.".format(name.replace("_", " ").capitalize()))
        if getattr(meeting, name) != value:
            before[name], after[name] = getattr(meeting, name), value
            setattr(meeting, name, value)
    if meeting.origin == "own" and "effective_start" in after:
        meeting.start_time = meeting.effective_start
    if after:
        record_change(meeting, "edited", before, after, user_name(user))
    return bool(after)


def set_own_meeting_status(meeting, status, user):
    """Cancel or reopen an own meeting. A spic meeting is cancelled in spic (write route, step 6)."""
    if meeting.origin != "own":
        raise PlanningError("A meeting from spic is cancelled in spic.")
    if meeting.status == status:
        return
    kind = "cancelled" if status == "cancelled" else "reopened"
    record_change(meeting, kind, {"status": meeting.status}, {"status": status}, user_name(user))
    meeting.status = status


def can_delete_meeting(meeting):
    """BR-MTG-005, BR-MTG-006: only an own meeting that never had an interpreter assigned."""
    if meeting.origin != "own":
        return False
    return not (MeetingAssignment.query.filter_by(meeting_id=meeting.id).first()
                or AssignmentLog.query.filter_by(meeting_id=meeting.id).first())


def delete_own_meeting(meeting, user):
    if meeting.origin != "own":
        raise PlanningError("A meeting from spic cannot be deleted in PDC; it is deleted in spic.")
    if not can_delete_meeting(meeting):
        raise PlanningError("An interpreter was assigned to this meeting at some point, so it can only be cancelled.")
    # The history keeps the last state; the meeting itself goes.
    record_change(meeting, "deleted", meeting.snapshot(), None, user_name(user))
    db.session.delete(meeting)


# ---------------------------------------------------------------------------------------------
# Time rules (BR-POS-002, BR-ASGN-001, "missing times" in 2.7)
# ---------------------------------------------------------------------------------------------

def meetings_overlap(first, second):
    """True when both meetings are known to overlap. A meeting without times never counts as
    overlapping: the assignment is allowed and flagged "time unknown" instead."""
    if not (first.time_known and second.time_known):
        return False
    return first.datetime_start < second.datetime_end and second.datetime_start < first.datetime_end


def check_meeting_in_slot(meeting, slot):
    if meeting.date != slot.date:
        raise PlanningError("The meeting is on {}, the booking is for {}.".format(meeting.date, slot.date))
    if meeting.effective_start is not None and not (slot.start_time <= meeting.effective_start < slot.end_time):
        raise PlanningError("The meeting starts at {:%H:%M}, outside the booking ({:%H:%M}-{:%H:%M}).".format(
            meeting.effective_start, slot.start_time, slot.end_time))
    if meeting.expected_end is not None and (meeting.end_next_day or meeting.expected_end > slot.end_time):
        raise PlanningError("The meeting ends after the booking ({:%H:%M}-{:%H:%M}).".format(
            slot.start_time, slot.end_time))


# ---------------------------------------------------------------------------------------------
# Assignments (2.6)
# ---------------------------------------------------------------------------------------------

def assign(position, meeting, user, notes=None):
    """Propose a position for a meeting. An assignment that was cancelled earlier comes back."""
    booking = position.booking
    if position.status != "active" or booking.status not in ("proposed", "confirmed"):
        raise PlanningError("This position can no longer be assigned ({} booking).".format(booking.status_display.lower()))
    if meeting.status != "planned":
        raise PlanningError("A {} meeting cannot get an interpreter.".format(meeting.status_display.lower()))
    if not meeting.is_visible:
        raise PlanningError("The week of this meeting is back in concept in spic.")
    check_meeting_in_slot(meeting, booking.slot)

    existing = None
    for other in position.assignments:
        if other.meeting_id == meeting.id:
            existing = other
        elif other.status != "cancelled" and meetings_overlap(other.meeting, meeting):
            raise PlanningError("This interpreter is already at '{}' at that time.".format(other.meeting.display_title))
    if existing is not None and existing.status != "cancelled":
        raise PlanningError("This position is already assigned to this meeting.")

    if existing is not None:
        existing.status = "proposed"
        existing.cancellation_communicated_on = None
        assignment = existing
    else:
        assignment = MeetingAssignment(position=position, meeting=meeting, status="proposed",
                                       notes=notes or None, created_by=user_id(user))
        db.session.add(assignment)
    db.session.flush()
    log("proposed", user, assignment=assignment)
    return assignment


def confirm_assignment(assignment, user):
    if assignment.status != "proposed":
        raise PlanningError("Only a proposed assignment can be confirmed.")
    if assignment.position.booking.status != "confirmed":
        raise PlanningError("Confirm the booking first (BR-ASGN-005).")
    if assignment.meeting.status != "planned":
        raise PlanningError("A {} meeting cannot be confirmed.".format(assignment.meeting.status_display.lower()))
    assignment.status = "confirmed"
    log("confirmed", user, assignment=assignment)


def cancel_assignment(assignment, user, reason=None, communicated_on=None):
    """Cancel an assignment (never delete it). `communicated_on`: when the interpreter was told."""
    if assignment.status == "cancelled":
        raise PlanningError("This assignment is already cancelled.")
    assignment.status = "cancelled"
    if communicated_on:
        assignment.cancellation_communicated_on = communicated_on
    log("cancelled", user, assignment=assignment, reason=reason,
        details={"communicated_on": jsonable(communicated_on)} if communicated_on else None)


def communicate_cancellation(assignment, user, communicated_on):
    """Note when the interpreter was told about the cancellation ("annulation transmise")."""
    if assignment.status != "cancelled":
        raise PlanningError("Only a cancelled assignment has a cancellation to communicate.")
    assignment.cancellation_communicated_on = communicated_on
    log("cancellation_communicated", user, assignment=assignment,
        details={"communicated_on": jsonable(communicated_on)})


def check_assignment(assignment, user, reason=None):
    """The planner has looked at a meeting that changed since the confirmation and closes the case:
    a new snapshot becomes the one to compare with (1.6)."""
    if assignment.status != "confirmed":
        raise PlanningError("Only a confirmed assignment can be checked.")
    log("checked", user, assignment=assignment, reason=reason)


# ---------------------------------------------------------------------------------------------
# Time slots and bookings (2.2, 2.4, 2.5)
# ---------------------------------------------------------------------------------------------

def get_or_create_slot(day, start, end, description=None):
    if not start < end:
        raise PlanningError("The booking must end after it starts.")
    slot = TimeSlot.query.filter_by(date=day, start_time=start, end_time=end).first()
    if slot is None:
        slot = TimeSlot(date=day, start_time=start, end_time=end, description=description or None)
        db.session.add(slot)
        db.session.flush()
    return slot


def create_booking(interpreter, slot, positions, forfait_hours, user, reason=None, notes=None):
    if forfait_hours not in (3, 4):
        raise PlanningError("The forfait is 3 or 4 hours.")
    if positions < 1:
        raise PlanningError("A booking has at least one interpreter.")
    if not interpreter.is_bureau and positions != 1:
        raise PlanningError("An individual interpreter has exactly one position (BR-BKG-002).")
    booking = Booking(interpreter=interpreter, slot=slot, status="proposed", forfait_hours=forfait_hours,
                      booking_reason=reason or None, notes=notes or None, created_by=user_id(user))
    for number in range(1, positions + 1):
        booking.positions.append(BookingPosition(position_number=number, status="active"))
    db.session.add(booking)
    db.session.flush()
    log("booking_created", user, booking=booking, details={"positions": positions})
    return booking


def add_position(booking, user):
    if booking.status not in ("proposed", "confirmed"):
        raise PlanningError("Positions can only be added to a proposed or confirmed booking.")
    if not booking.interpreter.is_bureau:
        raise PlanningError("An individual interpreter has exactly one position (BR-BKG-002).")
    number = max((p.position_number for p in booking.positions), default=0) + 1
    position = BookingPosition(booking=booking, position_number=number, status="active")
    db.session.add(position)
    db.session.flush()
    log("position_added", user, position=position)
    return position


def confirm_booking(booking, user):
    if booking.status != "proposed":
        raise PlanningError("Only a proposed booking can be confirmed.")
    for other in Booking.query.filter(Booking.interpreter_id == booking.interpreter_id,
                                      Booking.status == "confirmed", Booking.id != booking.id):
        if other.slot.overlaps(booking.slot):
            raise PlanningError("{} already has a confirmed booking at {} (BR-BKG-007); add a position to it instead.".format(
                booking.interpreter.display_name, other.slot.label))
    booking.status = "confirmed"
    log("booking_confirmed", user, booking=booking)


def cancel_booking(booking, user, reason=None):
    """Cancelling a booking cancels its positions and their assignments (BR-ASGN-003)."""
    if booking.status == "cancelled":
        raise PlanningError("This booking is already cancelled.")
    for position in booking.positions:
        if position.status == "active":
            _cancel_position(position, user, reason)
    booking.status = "cancelled"
    log("booking_cancelled", user, booking=booking, reason=reason)


def complete_booking(booking, user):
    if booking.status != "confirmed":
        raise PlanningError("Only a confirmed booking can be completed.")
    missing = [p for p in booking.active_positions if not p.interpreter_name]
    if missing:
        raise PlanningError("Fill in the name of the person sent for every position first (BR-POS-006).")
    booking.status = "completed"
    log("booking_completed", user, booking=booking)


def _cancel_position(position, user, reason):
    for assignment in position.active_assignments:
        cancel_assignment(assignment, user, reason=reason or "position cancelled")
    position.status = "cancelled"
    log("position_cancelled", user, position=position, reason=reason)


def cancel_position(position, user, reason=None):
    """The bureau cannot send that interpreter after all (BR-POS-005)."""
    if position.status != "active":
        raise PlanningError("This position is already cancelled.")
    _cancel_position(position, user, reason)


def set_position_name(position, name, user):
    """The person actually sent (BR-POS-004): the assignments stay, the change is noted."""
    name = (name or "").strip() or None
    if name == position.interpreter_name:
        return
    old = position.interpreter_name
    position.interpreter_name = name
    note = "{:%Y-%m-%d}: {} -> {}".format(utcnow(), old or "(not filled in)", name or "(cleared)")
    position.notes = "{}\n{}".format(position.notes, note).strip() if position.notes else note
    log("name_changed", user, position=position, details={"from": old, "to": name})


def record_hours(position, start, end, user):
    """The hours actually worked, per position (BR-POS-007)."""
    if start and end and not end > start:
        raise PlanningError("The end must be after the start.")
    position.actual_start_time, position.actual_end_time = start, end
    log("hours_recorded", user, position=position,
        details={"start": jsonable(start), "end": jsonable(end),
                 "overtime_half_hours": position_overtime(position)})


# ---------------------------------------------------------------------------------------------
# Forfait and overtime (BR-BKG-009, BR-MTG-011)
# ---------------------------------------------------------------------------------------------

def half_hours_over(start, end, forfait_hours):
    """Half hours worked beyond the forfait; a half hour that has started counts in full."""
    if start is None or end is None:
        return None
    extra_minutes = (end - start).total_seconds() / 60 - forfait_hours * 60
    return math.ceil(extra_minutes / 30) if extra_minutes > 0 else 0


def position_overtime(position):
    """From the hours recorded for the position, else from the meetings it is assigned to
    (the earliest start, the latest real end); None while that is unknown."""
    meetings = [a.meeting for a in position.active_assignments]
    start = position.actual_start_time or min(
        (m.datetime_start for m in meetings if m.datetime_start), default=None)
    end = position.actual_end_time or max(
        (m.actual_end_datetime for m in meetings if m.actual_end_datetime), default=None)
    return half_hours_over(start, end, position.booking.forfait_hours)


def paid_hours(position):
    over = position_overtime(position)
    return None if over is None else position.booking.forfait_hours + over / 2


def meeting_overtime_check(meeting):
    """What the real end of the meeting implies against the forfaits involved, next to the half
    hours charged; a difference is flagged (BR-MTG-011)."""
    implied = None
    if meeting.datetime_start and meeting.actual_end_datetime:
        values = [half_hours_over(meeting.datetime_start, meeting.actual_end_datetime, a.position.booking.forfait_hours)
                  for a in meeting.active_assignments]
        implied = max(values) if values else None
    charged = meeting.charged_half_hours
    return {"implied": implied, "charged": charged,
            "mismatch": implied is not None and charged is not None and implied != charged}


# ---------------------------------------------------------------------------------------------
# Invoices and Dimona (2.9, BR-POS-008, BR-POS-009, BR-INV-001..003)
# ---------------------------------------------------------------------------------------------

def record_invoice(interpreter, reference, received_on, period, notes, user):
    if interpreter.engagement != "invoice":
        raise PlanningError("{} works in occasional work: no invoice, a Dimona declaration instead.".format(
            interpreter.display_name))
    invoice = Invoice(interpreter=interpreter, reference=(reference or "").strip() or None,
                      received_on=received_on, period=(period or "").strip() or None,
                      notes=(notes or "").strip() or None, created_by=user_id(user))
    db.session.add(invoice)
    db.session.flush()
    log("invoice_recorded", user, interpreter=interpreter,
        details={"invoice_id": invoice.id, "reference": invoice.reference, "received_on": jsonable(received_on)})
    return invoice


def link_invoice(invoice, positions, user):
    """Link all positions an invoice covers in one handling."""
    for position in positions:
        if position.booking.interpreter_id != invoice.interpreter_id:
            raise PlanningError("{} does not belong to the supplier of this invoice (BR-INV-001).".format(position.label))
        if position.status != "active":
            raise PlanningError("{} is cancelled.".format(position.label))
        if position.invoice is not None and position.invoice is not invoice:
            raise PlanningError("{} is already linked to another invoice (BR-INV-002).".format(position.label))
    for position in positions:
        if position.invoice is not invoice:
            position.invoice = invoice
            log("invoice_linked", user, position=position,
                details={"invoice_id": invoice.id, "reference": invoice.reference})


def unlink_invoice(position, user):
    invoice = position.invoice
    if invoice is None:
        raise PlanningError("This position is not linked to an invoice.")
    position.invoice = None
    log("invoice_unlinked", user, position=position,
        details={"invoice_id": invoice.id, "reference": invoice.reference})


def mark_invoice_checked(invoice, user, checked=True):
    invoice.checked_on = utcnow().date() if checked else None
    invoice.checked_by = user_id(user) if checked else None
    log("invoice_checked" if checked else "invoice_unchecked", user, interpreter=invoice.interpreter,
        details={"invoice_id": invoice.id, "reference": invoice.reference})


def set_dimona(position, declared, user):
    if position.booking.interpreter.engagement != "occasional_work":
        raise PlanningError("A Dimona declaration is only for occasional work; this interpreter works on invoice.")
    if position.dimona_declared == declared:
        return
    position.dimona_declared = declared
    log("dimona_declared" if declared else "dimona_withdrawn", user, position=position)


# ---------------------------------------------------------------------------------------------
# Work lists (1.6, 2.5)
# ---------------------------------------------------------------------------------------------

def snapshot_changes(snapshot, current):
    """Fields of WATCHED_SNAPSHOT_FIELDS in which `current` differs from `snapshot`."""
    return {f: (snapshot.get(f), current.get(f)) for f in WATCHED_SNAPSHOT_FIELDS
            if snapshot.get(f) != current.get(f)}


def worklist_cancelled_with_assignment():
    """Cancelled or deleted meetings, or meetings of a week back in concept, that still have an
    assignment that is not cancelled (BR-MTG-010)."""
    return (Meeting.query
            .filter((Meeting.status.in_(("cancelled", "deleted"))) | (Meeting.week_status == "concept"))
            .filter(Meeting.assignments.any(MeetingAssignment.status != "cancelled"))
            .order_by(Meeting.date, Meeting.effective_start).all())


def worklist_changed_since_confirmation():
    """Confirmed assignments whose meeting differs from the snapshot of the last confirmation or
    check. Returns (assignment, log entry, {field: (then, now)}) rows."""
    last = (db.session.query(AssignmentLog.assignment_id, func.max(AssignmentLog.id).label("last_id"))
            .filter(AssignmentLog.action.in_(("confirmed", "checked")), AssignmentLog.assignment_id.isnot(None))
            .group_by(AssignmentLog.assignment_id).subquery())
    rows = (db.session.query(MeetingAssignment, AssignmentLog)
            .join(last, last.c.assignment_id == MeetingAssignment.id)
            .join(AssignmentLog, AssignmentLog.id == last.c.last_id)
            .filter(MeetingAssignment.status == "confirmed").all())
    result = []
    for assignment, entry in rows:
        changes = snapshot_changes(entry.meeting_snapshot or {}, assignment.meeting.snapshot())
        if changes:
            result.append((assignment, entry, changes))
    result.sort(key=lambda r: (r[0].meeting.date, r[0].id))
    return result


def _completed_positions(engagement):
    return (BookingPosition.query.join(Booking).join(Interpreter)
            .filter(Booking.status == "completed", BookingPosition.status == "active",
                    Interpreter.engagement == engagement))


def worklist_invoice_not_received():
    return (_completed_positions("invoice").filter(BookingPosition.invoice_id.is_(None))
            .join(TimeSlot, Booking.slot_id == TimeSlot.id).order_by(TimeSlot.date, Booking.id).all())


def worklist_dimona_to_declare():
    return (_completed_positions("occasional_work").filter(BookingPosition.dimona_declared.is_(False))
            .join(TimeSlot, Booking.slot_id == TimeSlot.id).order_by(TimeSlot.date, Booking.id).all())


def worklist_counts():
    return {
        "cancelled": len(worklist_cancelled_with_assignment()),
        "changed": len(worklist_changed_since_confirmation()),
        "invoice": len(worklist_invoice_not_received()),
        "dimona": len(worklist_dimona_to_declare()),
    }


def assignable_positions(meeting):
    """Positions that can be proposed for the meeting: booked for that day, within the booking's
    time, not yet at this meeting and not at another meeting at the same time. In the order of the
    legal priority of the interpreter or bureau (4.1)."""
    if meeting.status != "planned" or not meeting.is_visible:
        return []
    positions = (BookingPosition.query.join(Booking).join(TimeSlot)
                 .filter(TimeSlot.date == meeting.date, Booking.status.in_(("proposed", "confirmed")),
                         BookingPosition.status == "active").all())
    result = []
    for position in positions:
        try:
            check_meeting_in_slot(meeting, position.booking.slot)
        except PlanningError:
            continue
        others = position.active_assignments
        if any(a.meeting_id == meeting.id or meetings_overlap(a.meeting, meeting) for a in others):
            continue
        result.append(position)
    result.sort(key=lambda p: (p.booking.interpreter.priority_order, p.booking_id, p.position_number))
    return result
