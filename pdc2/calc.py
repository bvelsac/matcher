"""The calculation of PDC2 (functional analysis section 4): need, capacity and shortage per day, language
and role, with work moved to the next working day where spic's deadline allows it, and staff counted in
another role by the role rules of 3.3.

Pure functions on plain records, so that every rule can be tested without a database or a service.
"""
from dataclasses import dataclass, field
from datetime import date

LANGUAGES = ("nl", "fr")
CALCULATED = ("redacteur", "revisor")
ROLES = ("redacteur", "revisor", "hoofdredacteur", "vertaler")
STAFF_HALF_DAY = 4.0                      # hours of a staff member per half-day (2.2)
GM_HOURS = {"AM": 3.0, "PM": 4.0}         # hours of a GM per half-day (2.3)
REVISION_RATIO = 3.5 / 12                 # 3.5 revisors per 12 redacteurs (4.3)
PERIODS = ("AM", "PM")


@dataclass
class Meeting:
    id: str
    date: date
    status: str = "gepland"
    deadline: str = "zelfde-dag"          # or "volgende-dag"
    hours: dict = None                    # {"nl": .., "fr": ..}; None when spic has no estimate
    agenda_unknown: bool = False
    period: str = None
    label: str = ""
    start: str = None
    room: str = None


@dataclass
class StaffMember:
    id: str
    name: str
    language: str = None
    standard_role: str = None
    roles: dict = field(default_factory=dict)     # other role -> "mag" | "liever-niet" | "niet"
    validated: bool = True
    halves: dict = field(default_factory=dict)    # date -> (am, pm)

    def present(self, day, period):
        return bool(self.halves.get(day, (False, False))[PERIODS.index(period)])


@dataclass
class GmShift:
    """A booked GM half-day that is not cancelled (4.7)."""
    date: date
    period: str
    role: str
    language: str
    name: str = ""
    booking_id: int = None

    @property
    def hours(self):
        return GM_HOURS[self.period]


@dataclass
class Move:
    """A staff half-day counted in another role than the person's standard role (3.3)."""
    person: StaffMember
    date: date
    period: str
    from_role: str
    to_role: str
    level: str                             # "mag" or "liever-niet" (a warning)


@dataclass
class Cell:
    """One day, one language, one role."""
    due_same_day: float = 0.0              # work of today's meetings that must be done today
    may_wait: float = 0.0                  # work of today's meetings with deadline "next day"
    carried_in: float = 0.0                # work carried from the previous working day
    staff: float = 0.0
    gm: float = 0.0
    shortage: float = 0.0
    carried_out: float = 0.0
    surplus: float = 0.0
    gm_not_needed: float = 0.0
    previous_day: date = None              # the working day the carried work comes from

    @property
    def need(self):
        return self.due_same_day + self.may_wait

    @property
    def due(self):
        return self.carried_in + self.due_same_day

    @property
    def capacity(self):
        return self.staff + self.gm

    @property
    def shortage_from_previous_day(self):
        """The part of the shortage a GM booked on the previous working day could also do."""
        return min(self.shortage, self.carried_in)

    @property
    def covered(self):
        """How much of the work due today the capacity covers, 0 to 1 (for the meter)."""
        return 1.0 if self.due <= 0 else min(1.0, self.capacity / self.due)


@dataclass
class Result:
    days: list                                       # the working days shown
    cells: dict                                      # (language, role, day) -> Cell
    moves: list = field(default_factory=list)
    present_uncalculated: dict = field(default_factory=dict)   # (language, role, day) -> [names]
    agenda_unknown: dict = field(default_factory=dict)         # day -> [Meeting]
    not_validated: list = field(default_factory=list)
    incomplete: list = field(default_factory=list)             # staff without language or role
    carried_beyond: dict = field(default_factory=dict)         # (language, role) -> hours after the last day

    def cell(self, language, role, day):
        return self.cells[(language, role, day)]


def need_of(meeting, language, role):
    """Hours of work of a meeting for a language and role (4.1, 4.3)."""
    if meeting.status != "gepland" or meeting.hours is None:
        return 0.0
    hours = float(meeting.hours.get(language) or 0)
    return hours if role == "redacteur" else hours * REVISION_RATIO


def _round(value):
    return round(value + 0.0, 2)


def calculate(days, meetings, staff, shifts=(), excluded=(), shown=None):
    """Run the calculation over `days`, the working days in date order (a meeting on another day is
    counted on that day). `excluded` holds (person id, date, period) marked "does not count" (5).
    `shown`: the days to report (default all); the others only feed what is carried in."""
    excluded = set(excluded)
    meeting_days = {m.date for m in meetings if m.status == "gepland" and m.hours}
    all_days = sorted(set(days) | meeting_days)
    shown = sorted(shown) if shown is not None else all_days
    result = Result(days=shown, cells={})

    for person in staff:
        if not person.validated:
            result.not_validated.append(person)
        elif not person.language or not person.standard_role:
            result.incomplete.append(person)
    for meeting in meetings:
        if meeting.status == "gepland" and meeting.agenda_unknown and meeting.date in shown:
            result.agenda_unknown.setdefault(meeting.date, []).append(meeting)

    for language in LANGUAGES:
        carry = {role: 0.0 for role in CALCULATED}
        previous = None
        for day in all_days:
            cells = {role: Cell(carried_in=carry[role], previous_day=previous if carry[role] else None)
                     for role in CALCULATED}
            for meeting in meetings:
                if meeting.date != day:
                    continue
                for role in CALCULATED:
                    hours = need_of(meeting, language, role)
                    if meeting.deadline == "volgende-dag":
                        cells[role].may_wait += hours
                    else:
                        cells[role].due_same_day += hours

            # Every present half-day of a member of this language, first in the standard role (3.3).
            assigned = []
            for person in sorted(staff, key=lambda p: (p.name, p.id)):
                if not (person.validated and person.language == language and person.standard_role):
                    continue
                for period in PERIODS:
                    if person.present(day, period) and (person.id, day, period) not in excluded:
                        assigned.append([person, period, person.standard_role])
            for shift in shifts:
                if shift.date == day and shift.language == language and shift.role in CALCULATED:
                    cells[shift.role].gm += shift.hours

            def count(role):
                return sum(STAFF_HALF_DAY for a in assigned if a[2] == role)

            def free(role):
                c = cells[role]
                return c.gm + count(role) - c.due - c.may_wait

            for role in CALCULATED:
                for level in ("mag", "liever-niet"):
                    # First people whose own calculated role has time to spare, then the others.
                    for calculated_first in (True, False):
                        for entry in assigned:
                            c = cells[role]
                            if c.gm + count(role) >= c.due:
                                break
                            person, period, current = entry
                            if current != person.standard_role or current == role:
                                continue
                            if person.roles.get(role) != level or (current in CALCULATED) != calculated_first:
                                continue
                            if current in CALCULATED and free(current) < STAFF_HALF_DAY:
                                continue
                            entry[2] = role
                            result.moves.append(Move(person, day, period, current, role, level))

            for role in CALCULATED:
                c = cells[role]
                c.staff = count(role)
                c.shortage = max(0.0, c.due - c.capacity)
                left = max(0.0, c.capacity - c.due)
                c.carried_out = max(0.0, c.may_wait - left)
                c.surplus = max(0.0, left - c.may_wait)
                c.gm_not_needed = min(c.gm, c.surplus)
                carry[role] = c.carried_out
                for name in ("due_same_day", "may_wait", "carried_in", "staff", "gm", "shortage",
                             "carried_out", "surplus", "gm_not_needed"):
                    setattr(c, name, _round(getattr(c, name)))
                result.cells[(language, role, day)] = c
            for role in ("hoofdredacteur", "vertaler"):
                result.present_uncalculated[(language, role, day)] = [
                    "{} ({})".format(a[0].name, a[1]) for a in assigned if a[2] == role]
            previous = day
        for role in CALCULATED:
            last = result.cells.get((language, role, shown[-1])) if shown else None
            if last and last.carried_out:
                result.carried_beyond[(language, role)] = last.carried_out

    result.moves = [m for m in result.moves if m.date in shown]
    return result
