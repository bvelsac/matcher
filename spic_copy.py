"""PDC's own copy of the spic meetings (functional analysis 1.1 to 1.3, 2.7).

This module applies what spic reports to the copy: a meeting (new, changed, cancelled, deleted,
restored, moved to another week), the status of a week and the list of rooms. It does not talk to
spic: the link (the request "since change N", the background task) is built in a later step and
will call these functions with what spic returns. Until then the test data and the sample data
use them, so the link only has to replace the source.

THE SHAPE OF AN ITEM IS AN ASSUMPTION. The export of spic does not exist yet (FA Opnamebeheer
13.2 only lists the contents). The field names follow the table `vergaderingen` of spic as far as
the notes in docs/pdc-voorstel.md give them; the values of status, week status and start kind are
guesses. Everything that depends on the guess is in the dictionaries below, in one place.

    {"id": "m-0a1b2c3d", "maandag": "2026-10-12", "datum": "2026-10-14", "periode": "PM",
     "status": "gepland", "versie": 3, "start_soort": "uur", "start_uur": "14:00",
     "effectief_begin": "14:00", "verwacht_einde": "17:30", "einde_volgende_dag": false,
     "zaal": "R1", "domein": "...", "assemblee": "...", "type": "...", "volgnummer": 12,
     "volgnummer2": null, ...anything else spic knows, kept in spic_data}

A deleted meeting is reported with "status": "verwijderd" and may carry nothing more than its id:
the copy keeps its last state. Empty text stands for a missing value (no start time yet).
"""
from datetime import date, time

from extensions import db
from models import Meeting, Room, SyncState, utcnow
from planning import record_change

STATUS = {"gepland": "planned", "geannuleerd": "cancelled", "verwijderd": "deleted"}
WEEK_STATUS = {"concept": "concept", "pre-definitief": "pre_definitive", "definitief": "definitive"}
START_KIND = {"uur": "time", "tijd": "time", "na afloop van": "after", "na": "after"}
# Types of meeting that need three interpreters by default (2.7); every other type needs two.
# The codes are a guess until the export shows spic's own.
PLENARY_TYPES = ("plenaire", "plenair", "plenary", "plen")

# Columns that are copied from spic and compared for the history (not spic_data, not the numbers).
COPIED_COLUMNS = (
    "week", "week_status", "status", "date", "period", "start_kind", "start_time", "effective_start",
    "expected_end", "end_next_day", "room", "domain", "assembly", "type", "sequence_number",
    "sequence_number_2", "spic_version",
)


class SpicItemError(ValueError):
    """An item from spic that cannot be read; the message says which part."""


def _text(value):
    value = ("" if value is None else str(value)).strip()
    return value or None


def _date(value, name):
    try:
        return date.fromisoformat(_text(value))
    except (TypeError, ValueError):
        raise SpicItemError("'{}' is not a date: {!r}".format(name, value))


def _time(value, name):
    value = _text(value)
    if value is None:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        raise SpicItemError("'{}' is not a time: {!r}".format(name, value))


def _int(value, name):
    value = _text(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        raise SpicItemError("'{}' is not a number: {!r}".format(name, value))


def _choice(value, mapping, name):
    key = (_text(value) or "").lower()
    if key not in mapping:
        raise SpicItemError("'{}' has an unknown value: {!r}".format(name, value))
    return mapping[key]


def parse_item(item):
    """The columns of a meeting from an item of spic. A deleted meeting without its fields gives
    only its id and status."""
    spic_id = _text(item.get("id"))
    if not spic_id:
        raise SpicItemError("An item without an id.")
    status = _choice(item.get("status", "gepland"), STATUS, "status")
    if status == "deleted" and not item.get("datum"):
        return {"spic_id": spic_id, "status": status}

    period = (_text(item.get("periode")) or "").upper()
    if period not in ("AM", "PM"):
        raise SpicItemError("'periode' must be AM or PM: {!r}".format(item.get("periode")))
    start_kind = _text(item.get("start_soort"))
    return {
        "spic_id": spic_id,
        "status": status,
        "week": _date(item.get("maandag"), "maandag"),
        "week_status": _choice(item.get("weekstatus", "definitief"), WEEK_STATUS, "weekstatus"),
        "date": _date(item.get("datum"), "datum"),
        "period": period,
        "start_kind": _choice(start_kind, START_KIND, "start_soort") if start_kind else None,
        "start_time": _time(item.get("start_uur"), "start_uur"),
        "effective_start": _time(item.get("effectief_begin"), "effectief_begin"),
        "expected_end": _time(item.get("verwacht_einde"), "verwacht_einde"),
        "end_next_day": bool(item.get("einde_volgende_dag")),
        "room": _text(item.get("zaal")),
        "domain": _text(item.get("domein")),
        "assembly": _text(item.get("assemblee")),
        "type": _text(item.get("type")),
        "sequence_number": _int(item.get("volgnummer"), "volgnummer"),
        "sequence_number_2": _int(item.get("volgnummer2"), "volgnummer2"),
        "spic_version": _int(item.get("versie"), "versie"),
    }


def default_interpreters_needed(meeting_type):
    return 3 if (meeting_type or "").strip().lower() in PLENARY_TYPES else 2


def _kind(old_status, values, changed):
    """The one word for what happened to the meeting in the history."""
    new_status = values["status"]
    if new_status == "deleted":
        return "deleted"
    if old_status == "deleted":
        return "restored"
    if old_status != new_status:
        return "cancelled" if new_status == "cancelled" else "reopened"
    if "week" in changed:
        return "moved"
    if set(changed) <= {"week_status"}:
        return "week_status"
    return "changed"


def apply_item(item, change_number=None, changed_by="spic"):
    """Apply one meeting of spic to the copy. Returns (meeting, changed); meeting is None for the
    deletion of a meeting PDC never received.

    Applying a change number that was already applied does nothing, so asking "since N" again
    gives the same result (1.3)."""
    values = parse_item(item)
    meeting = Meeting.query.filter_by(spic_id=values["spic_id"]).first()
    now = utcnow()

    if meeting is None:
        if values["status"] == "deleted":
            return None, False
        meeting = Meeting(origin="spic", first_seen_at=now, spic_data=dict(item), last_change_number=change_number,
                          interpreters_needed=default_interpreters_needed(values["type"]), **values)
        db.session.add(meeting)
        db.session.flush()
        record_change(meeting, "new", None, {k: values[k] for k in COPIED_COLUMNS if k in values},
                      changed_by, change_number)
        return meeting, True

    if (change_number is not None and meeting.last_change_number is not None
            and meeting.last_change_number >= change_number):
        return meeting, False

    before, after = {}, {}
    for column in COPIED_COLUMNS:
        if column in values and getattr(meeting, column) != values[column]:
            before[column], after[column] = getattr(meeting, column), values[column]
    old_status = meeting.status
    if after:
        for column, value in after.items():
            setattr(meeting, column, value)
        if "datum" in item:
            meeting.spic_data = dict(item)
        if values["status"] == "deleted":
            meeting.deleted_in_spic_at = now
        elif old_status == "deleted":
            meeting.deleted_in_spic_at = None
        record_change(meeting, _kind(old_status, values, after), before, after, changed_by, change_number)
    elif "datum" in item and meeting.spic_data != item:
        meeting.spic_data = dict(item)  # a field PDC does not use changed
    if change_number is not None:
        meeting.last_change_number = change_number
    return meeting, bool(after)


def apply_week_status(week, status, change_number=None, changed_by="spic"):
    """The status of a week changed. Going back to concept hides its meetings and keeps them, with
    their assignments (BR-MTG-009). Becoming pre-definitive: the caller then fetches the whole
    week and applies its meetings with apply_item."""
    week_status = _choice(status, WEEK_STATUS, "weekstatus")
    changed = []
    for meeting in Meeting.query.filter_by(origin="spic", week=week).all():
        if meeting.week_status != week_status:
            record_change(meeting, "week_status", {"week_status": meeting.week_status},
                          {"week_status": week_status}, changed_by, change_number)
            meeting.week_status = week_status
            changed.append(meeting)
        if change_number is not None:
            meeting.last_change_number = max(meeting.last_change_number or 0, change_number)
    return changed


def apply_rooms(rooms):
    """The fixed list of rooms of spic: [{"code": "R1", "omschrijving": "...", "actief": true}]."""
    for item in rooms:
        code = _text(item.get("code"))
        if not code:
            raise SpicItemError("A room without a code.")
        room = db.session.get(Room, code) or Room(code=code)
        room.description = _text(item.get("omschrijving")) or ""
        room.active = bool(item.get("actief", True))
        db.session.add(room)


def sync_state():
    state = db.session.get(SyncState, 1)
    if state is None:
        state = SyncState(id=1, last_change_number=0)
        db.session.add(state)
    return state


def advance(change_number, highest=None):
    """Remember the last change number processed (in the same transaction as the changes)."""
    state = sync_state()
    state.last_change_number = max(state.last_change_number, change_number)
    state.last_success_at = utcnow()
    if highest is not None:
        state.spic_highest_number = highest
    return state

