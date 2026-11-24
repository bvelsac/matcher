"""The calculation of PDC2, with the worked examples of the functional analysis (section 8) as fixed cases."""
from datetime import date, timedelta

import pytest

from pdc2.calc import GmShift, Meeting, StaffMember, calculate, need_of

MON = date(2030, 1, 7)
TUE, WED, THU, FRI = (MON + timedelta(days=i) for i in range(1, 5))
WEEK = [MON, TUE, WED, THU, FRI]


def redacteurs(day, hours, prefix="r", language="nl", **extra):
    """Staff giving `hours` of redacteur capacity on `day` (whole half-days of 4 hours)."""
    halves = int(hours // 4)
    people = []
    for i in range((halves + 1) // 2):
        am, pm = True, (2 * i + 1) < halves
        people.append(StaffMember(id="{}{}{}".format(prefix, day.day, i), name="{} {} {}".format(prefix, day, i),
                                  language=language, standard_role="redacteur",
                                  halves={day: (am, pm)}, **extra))
    return people


def meeting(day, nl, deadline, id="m", fr=0.0, **extra):
    return Meeting(id="{}-{}".format(id, day), date=day, deadline=deadline, hours={"nl": nl, "fr": fr}, **extra)


def red(result, day, language="nl"):
    return result.cell(language, "redacteur", day)


@pytest.mark.parametrize("need_mon, staff_mon, need_tue, staff_tue, carried, shortage_tue", [
    (40, 32, 20, 36, 8, 0),     # A, with whole half-days: Monday's rest fits on Tuesday
    (40, 32, 30, 36, 8, 2),     # B: two hours short on Tuesday
    (20, 36, 44, 36, 0, 8),     # C: a surplus on Monday does not help Tuesday
])
def test_work_moves_to_the_next_working_day_only_forward(need_mon, staff_mon, need_tue, staff_tue, carried, shortage_tue):
    meetings = [meeting(MON, need_mon, "volgende-dag"), meeting(TUE, need_tue, "zelfde-dag")]
    staff = redacteurs(MON, staff_mon, "a") + redacteurs(TUE, staff_tue, "b")
    result = calculate(WEEK, meetings, staff)
    assert red(result, MON).shortage == 0
    assert red(result, MON).carried_out == carried
    assert red(result, TUE).carried_in == carried
    assert red(result, TUE).shortage == shortage_tue
    assert red(result, TUE).shortage_from_previous_day == min(shortage_tue, carried)


def test_a_deadline_chosen_by_hand_moves_work_to_the_next_day():
    meetings = [meeting(MON, 40, "volgende-dag"), meeting(TUE, 20, "zelfde-dag", id="a"),
                meeting(TUE, 10, "volgende-dag", id="b")]
    staff = redacteurs(MON, 32, "a") + redacteurs(TUE, 32, "b")
    result = calculate(WEEK, meetings, staff)
    tue, wed = red(result, TUE), red(result, WED)
    assert (tue.due, tue.shortage) == (28, 0)          # 8 carried + 20 same day, 32 capacity
    assert tue.carried_out == 6                        # 4 hours left do 4 of the 10 that may wait
    assert (wed.carried_in, wed.shortage) == (6, 6)    # nobody on Wednesday
    assert wed.previous_day == TUE


def test_same_day_work_is_short_on_its_day():
    result = calculate(WEEK, [meeting(FRI, 12, "zelfde-dag")], redacteurs(FRI, 8))
    assert red(result, FRI).shortage == 4
    assert red(result, FRI).carried_out == 0


def test_the_next_working_day_skips_a_day_that_is_not_one():
    # Thursday is no working day: Wednesday's work waits until Friday.
    days = [MON, TUE, WED, FRI]
    result = calculate(days, [meeting(WED, 8, "volgende-dag")], redacteurs(FRI, 8))
    assert red(result, WED).carried_out == 8
    assert red(result, FRI).carried_in == 8 and red(result, FRI).shortage == 0
    assert red(result, FRI).previous_day == WED


def test_revision_is_three_and_a_half_per_twelve():
    m = meeting(MON, 48, "zelfde-dag")
    assert need_of(m, "nl", "revisor") == pytest.approx(14)
    result = calculate(WEEK, [m], [])
    assert result.cell("nl", "revisor", MON).shortage == 14


def test_languages_are_counted_apart_and_staff_only_in_their_mother_tongue():
    staff = redacteurs(MON, 8, language="fr")
    result = calculate(WEEK, [meeting(MON, 4, "zelfde-dag", fr=8)], staff)
    assert red(result, MON, "nl").shortage == 4
    assert red(result, MON, "fr").shortage == 0


def test_gm_hours_count_three_in_the_morning_and_four_in_the_afternoon():
    shifts = [GmShift(MON, "AM", "redacteur", "nl"), GmShift(MON, "PM", "redacteur", "nl")]
    result = calculate(WEEK, [meeting(MON, 10, "zelfde-dag")], [], shifts)
    assert red(result, MON).gm == 7 and red(result, MON).shortage == 3


def test_gm_hours_no_longer_needed_are_shown():
    shifts = [GmShift(MON, "PM", "redacteur", "nl")]
    result = calculate(WEEK, [meeting(MON, 2, "zelfde-dag", status="geannuleerd")], [], shifts)
    assert red(result, MON).gm_not_needed == 4


def test_a_cancelled_meeting_or_one_without_an_estimate_brings_no_work():
    meetings = [meeting(MON, 10, "zelfde-dag", status="geannuleerd"),
                Meeting(id="x", date=MON, hours=None, agenda_unknown=True)]
    result = calculate(WEEK, meetings, [])
    assert red(result, MON).need == 0
    assert [m.id for m in result.agenda_unknown[MON]] == ["x"]


def test_a_marked_half_day_does_not_count():
    staff = redacteurs(MON, 8)
    person = staff[0]
    result = calculate(WEEK, [meeting(MON, 8, "zelfde-dag")], staff, excluded={(person.id, MON, "PM")})
    assert red(result, MON).staff == 4 and red(result, MON).shortage == 4


def test_staff_without_validated_calendar_or_role_are_listed_not_counted():
    staff = [StaffMember("a", "A", "nl", "redacteur", validated=False),
             StaffMember("b", "B", None, None, halves={MON: (True, True)})]
    result = calculate(WEEK, [], staff)
    assert [p.id for p in result.not_validated] == ["a"]
    assert [p.id for p in result.incomplete] == ["b"]


# -- the role rules (3.3) ------------------------------------------------------------------------

def person(id, role, roles, day=WED, am=True, pm=True, language="nl"):
    return StaffMember(id=id, name=id, language=language, standard_role=role, roles=roles, halves={day: (am, pm)})


def test_a_hoofdredacteur_who_may_revise_covers_revision_when_redaction_has_no_half_day_to_spare():
    # 12 hours of redacteurs for 10 hours of redaction: 2 to spare, less than a half-day, so no
    # redacteur moves; the hoofdredacteur who may revise covers the 2.9 hours of revision.
    staff = [
        person("red1", "redacteur", {"revisor": "mag"}),                     # 8 hours
        person("red2", "redacteur", {"revisor": "liever-niet"}, pm=False),   # 4 hours
        person("chief", "hoofdredacteur", {"revisor": "mag"}),
    ]
    result = calculate(WEEK, [meeting(WED, 10, "zelfde-dag")], staff)
    assert [(m.person.id, m.period, m.to_role, m.level) for m in result.moves] == [("chief", "AM", "revisor", "mag")]
    assert result.cell("nl", "revisor", WED).shortage == 0
    assert red(result, WED).shortage == 0


def test_a_redacteur_who_may_revise_moves_only_when_redaction_has_a_half_day_to_spare():
    staff = [person("red1", "redacteur", {"revisor": "mag"}), person("red2", "redacteur", {})]
    result = calculate(WEEK, [meeting(WED, 6, "zelfde-dag")], staff)    # 16 hours for 6 of work
    rev = result.cell("nl", "revisor", WED)
    assert [(m.person.id, m.period) for m in result.moves] == [("red1", "AM")]
    assert rev.staff == 4 and rev.shortage == 0
    assert red(result, WED).staff == 12 and red(result, WED).shortage == 0


def test_rather_not_is_used_only_when_no_one_may():
    # 16 hours of redacteurs for 12 hours of redaction (4 to spare); 3.5 hours of revision.
    staff = [person("red1", "redacteur", {"revisor": "liever-niet"}), person("red2", "redacteur", {})]
    result = calculate(WEEK, [meeting(WED, 12, "zelfde-dag")], staff)
    assert [(m.person.id, m.level) for m in result.moves] == [("red1", "liever-niet")]
    assert result.cell("nl", "revisor", WED).shortage == 0

    staff.append(person("red3", "redacteur", {"revisor": "mag"}, pm=False))
    result = calculate(WEEK, [meeting(WED, 12, "zelfde-dag")], staff)
    assert [(m.person.id, m.level) for m in result.moves] == [("red3", "mag")]


def test_never_in_a_role_marked_not():
    staff = [person("red1", "redacteur", {"revisor": "niet"}), person("red2", "redacteur", {})]
    result = calculate(WEEK, [meeting(WED, 2, "zelfde-dag")], staff)
    assert result.moves == []
    assert result.cell("nl", "revisor", WED).shortage > 0


def test_hoofdredacteur_and_vertaler_are_listed_without_calculation():
    staff = [person("chief", "hoofdredacteur", {}), person("tr", "vertaler", {}, am=False)]
    result = calculate(WEEK, [], staff)
    assert result.present_uncalculated[("nl", "hoofdredacteur", WED)] == ["chief (AM)", "chief (PM)"]
    assert result.present_uncalculated[("nl", "vertaler", WED)] == ["tr (PM)"]


def test_only_the_days_shown_are_reported_but_earlier_days_feed_the_carry():
    previous_friday = MON - timedelta(days=3)
    m = meeting(previous_friday, 8, "volgende-dag")
    result = calculate([previous_friday] + WEEK, [m], [], shown=WEEK)
    assert result.days == WEEK
    assert red(result, MON).carried_in == 8 and red(result, MON).previous_day == previous_friday
    assert red(result, MON).shortage == 8
    assert red(result, FRI).carried_out == 0 and result.carried_beyond == {}
