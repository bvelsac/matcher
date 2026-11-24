"""Fake spic and jaarkalender: realistic but fictitious answers, in the form of the real APIs.

With PDC2_SOURCE=fake, PDC2 reads these instead of the services. They answer the same HAL documents as
docs/pdc2-api-contract.md, at the same addresses, so the HAL client, the links it follows and the whole
calculation run exactly as they will against spic and the jaarkalender. Every name is invented.

The data are deterministic: the same week always gives the same meetings and the same presence.
"""
import random
import urllib.parse
from datetime import date, timedelta

SPIC_ENTRY = "http://spic.fake/api/afnemers"
JK_ENTRY = "http://jaarkalender.fake/api/extern"

# Public holidays in Belgium, by (month, day); Easter Monday, Ascension and Whit Monday are left out.
HOLIDAYS = {(1, 1), (5, 1), (7, 21), (8, 15), (11, 1), (11, 11), (12, 25), (12, 26)}

# The staff: id, first name, last name, mother tongue, standard role, other roles.
STAFF = [
    ("ajans", "Anke", "Janssens", "nl", "redacteur", {"revisor": "mag"}),
    ("bpeet", "Bart", "Peeters", "nl", "redacteur", {"revisor": "liever-niet"}),
    ("cwout", "Carla", "Wouters", "nl", "redacteur", {}),
    ("dmaes", "Dirk", "Maes", "nl", "redacteur", {"revisor": "mag"}),
    ("evdbe", "Els", "Van den Berg", "nl", "redacteur", {}),
    ("fclae", "Filip", "Claes", "nl", "redacteur", {"vertaler": "mag"}),
    ("gverm", "Greet", "Vermeulen", "nl", "redacteur", {}),
    ("hgoos", "Hans", "Goossens", "nl", "revisor", {"redacteur": "mag"}),
    ("ijaco", "Ilse", "Jacobs", "nl", "revisor", {"redacteur": "mag"}),
    ("jmert", "Jan", "Mertens", "nl", "hoofdredacteur", {"revisor": "mag"}),
    ("kwill", "Katrien", "Willems", "nl", "vertaler", {"redacteur": "liever-niet"}),
    ("ldubo", "Luc", "Dubois", "fr", "redacteur", {"revisor": "mag"}),
    ("mlamb", "Marie", "Lambert", "fr", "redacteur", {}),
    ("nmart", "Nicolas", "Martin", "fr", "redacteur", {"revisor": "liever-niet"}),
    ("odupo", "Odile", "Dupont", "fr", "redacteur", {}),
    ("plero", "Pierre", "Leroy", "fr", "redacteur", {}),
    ("qmore", "Quentin", "Moreau", "fr", "redacteur", {"revisor": "mag"}),
    ("rlaur", "Rose", "Laurent", "fr", "redacteur", {}),
    ("ssimo", "Sophie", "Simon", "fr", "revisor", {"redacteur": "mag"}),
    ("tfont", "Thomas", "Fontaine", "fr", "revisor", {}),
    ("ugill", "Ursule", "Gilles", "fr", "hoofdredacteur", {"revisor": "mag"}),
    ("vrena", "Victor", "Renard", "fr", "vertaler", {}),
    ("wmich", "Wanda", "Michel", "fr", "redacteur", {}),       # no validated calendar (see below)
    ("xsecr", "Xavier", "Coppens", None, None, {}),             # secretariat: no role, never counted
]
NOT_VALIDATED = {"wmich"}
ROLES = ("redacteur", "revisor", "hoofdredacteur", "vertaler")


def is_workday(day):
    return day.weekday() < 5 and (day.month, day.day) not in HOLIDAYS


def monday_of(day):
    return day - timedelta(days=day.weekday())


def week_status(monday, today=None):
    """Past and current weeks definitive, next week pre-definitive, later weeks in concept."""
    this_monday = monday_of(today or date.today())
    if monday <= this_monday:
        return "definitief"
    return "pre-definitief" if monday == this_monday + timedelta(days=7) else "concept"


# The meetings of a weekday: (period, type, chance of being held); hours drawn per meeting.
DAY_PLAN = {
    0: [("PM", "commissie", 1.0), ("PM", "commissie", 0.9), ("PM", "commissie", 0.6), ("AM", "uitgebreid-bureau", 1.0)],
    1: [("AM", "commissie", 1.0), ("PM", "commissie", 1.0), ("PM", "commissie", 0.9), ("PM", "commissie", 0.7)],
    2: [("AM", "commissie", 1.0), ("PM", "commissie", 1.0), ("PM", "commissie", 0.8), ("PM", "bureau", 1.0)],
    3: [("AM", "commissie", 1.0), ("PM", "commissie", 0.9), ("PM", "commissie", 0.5)],
    4: [("AM", "plenaire", 0.8), ("PM", "plenaire", 0.8)],
}
START = {"AM": ["09:30", "10:00", "10:30"], "PM": ["14:00", "14:30", "15:00"]}


def meetings(monday, today=None):
    """The meetings of a week, as spic would report them to PDC2."""
    rng = random.Random(monday.toordinal())
    concept = week_status(monday, today) == "concept"
    out = []
    for offset in range(5):
        day = monday + timedelta(days=offset)
        if not is_workday(day):
            continue
        for number, (period, kind, chance) in enumerate(DAY_PLAN[offset], start=1):
            if rng.random() > chance:
                continue
            start = rng.choice(START[period])
            plenary = kind == "plenaire"
            # Working hours as spic estimates them: a committee of two to three hours brings 10 to 35 hours
            # of work per language, a plenary session more; French usually more than Dutch.
            nl = rng.choice(range(30, 101 if plenary else 49)) / 2
            fr = rng.choice(range(40, 131 if plenary else 65)) / 2
            agenda_unknown = concept and rng.random() < 0.3
            # Monday and Wednesday "next day" by default; now and then a deadline chosen by hand.
            deadline = "volgende-dag" if day.weekday() in (0, 2) else "zelfde-dag"
            if rng.random() < 0.05:
                deadline = "zelfde-dag" if deadline == "volgende-dag" else "volgende-dag"
            mid = "m-{:08x}".format((monday.toordinal() * 100 + offset * 10 + number) & 0xFFFFFFFF)
            out.append({
                "id": mid, "versie": 1 + rng.randrange(3),
                "status": "geannuleerd" if rng.random() < 0.04 else "gepland",
                "datum": day.isoformat(), "periode": period,
                "effectief_begin": start, "verwacht_einde": None if agenda_unknown else _later(start, rng.choice((2, 3, 4))),
                "zaal": rng.choice(["R1", "R2", "R3", "HEM"]) if not plenary else "HEM",
                "domein": "PARL", "assemblee": "FICT", "type": kind,
                "volgnummer": offset * 10 + number, "volgnummer2": None,
                "termijn": deadline, "agenda_onbekend": agenda_unknown,
                "werkuren": None if agenda_unknown else {"nl": nl, "fr": fr},
                "_links": {"self": {"href": "/api/afnemers/vergaderingen/" + mid}},
            })
    return out


def _later(start, hours):
    hour, minute = map(int, start.split(":"))
    return "{:02d}:{:02d}".format(min(hour + hours, 23), minute)


def present(person_id, day, period):
    """Whether a staff member works a half-day: about four in five, fixed per person and day."""
    if not is_workday(day):
        return False
    rng = random.Random("{}|{}|{}".format(person_id, day.isoformat(), period))
    return rng.random() < 0.8


# ----------------------------------------------------------------------------------------------
# The two fake services, answering the addresses of the contract
# ----------------------------------------------------------------------------------------------

def _error(status, message, start):
    return status, {"fout": message, "_links": {"start": {"href": start}}}


def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def spic(path, query, today=None):
    start = "/api/afnemers"
    if path == start:
        this_monday = monday_of(today or date.today())
        return 200, {
            "afnemer": "pdc2", "weekstatussen": ["concept", "pre-definitief", "definitief"],
            "_links": {"self": {"href": start},
                       "week": {"href": start + "/weken/{maandag}", "templated": True},
                       "deze-week": {"href": "{}/weken/{}".format(start, this_monday.isoformat())}}}
    if path.startswith(start + "/weken/"):
        monday = _date(path.rsplit("/", 1)[1])
        if monday is None or monday.weekday() != 0:
            return _error(400, "Geen maandag.", start)
        href = "{}/weken/{}".format(start, monday.isoformat())
        return 200, {
            "maandag": monday.isoformat(), "status": week_status(monday, today),
            "_links": {"self": {"href": href}, "start": {"href": start},
                       "vorige": {"href": "{}/weken/{}".format(start, (monday - timedelta(days=7)).isoformat())},
                       "volgende": {"href": "{}/weken/{}".format(start, (monday + timedelta(days=7)).isoformat())}},
            "_embedded": {"vergaderingen": meetings(monday, today)}}
    return _error(404, "Onbekend adres.", start)


def jaarkalender(path, query):
    start = "/api/extern"
    if path == start:
        return 200, {"_links": {
            "self": {"href": start},
            "medewerkers": {"href": start + "/medewerkers"},
            "aanwezigheid": {"href": start + "/aanwezigheid{?van,tot}", "templated": True},
            "werkdagen": {"href": start + "/werkdagen{?van,tot}", "templated": True}}}
    if path == start + "/medewerkers":
        people = [{
            "id": pid, "voornaam": first, "naam": last, "actief": True, "moedertaal": language,
            "standaardrol": role,
            "rollen": {r: other.get(r, "niet") for r in ROLES if r != role} if role else {},
            "_links": {"self": {"href": "{}/medewerkers/{}".format(start, pid)}},
        } for pid, first, last, language, role, other in STAFF]
        return 200, {"_links": {"self": {"href": path}, "start": {"href": start}},
                     "_embedded": {"medewerkers": people}}
    if path in (start + "/aanwezigheid", start + "/werkdagen"):
        van, tot = _date(query.get("van")), _date(query.get("tot"))
        if van is None or tot is None or tot < van or (tot - van).days > 61:
            return _error(400, "Geef van en tot, hoogstens 62 dagen.", start)
        days = [van + timedelta(days=i) for i in range((tot - van).days + 1)]
        self_href = "{}?{}".format(path, urllib.parse.urlencode({"van": van.isoformat(), "tot": tot.isoformat()}))
        links = {"self": {"href": self_href}, "start": {"href": start}}
        if path.endswith("/werkdagen"):
            return 200, {"van": van.isoformat(), "tot": tot.isoformat(), "_links": links,
                         "dagen": [{"datum": d.isoformat(), "werkdag": is_workday(d)} for d in days]}
        people = []
        for pid, *_ in STAFF:
            validated = pid not in NOT_VALIDATED
            people.append({
                "id": pid, "gevalideerd": validated,
                "dagdelen": {d.isoformat(): [present(pid, d, "AM"), present(pid, d, "PM")] for d in days}
                if validated else None,
                "_links": {"medewerker": {"href": "{}/medewerkers/{}".format(start, pid)}}})
        return 200, {"van": van.isoformat(), "tot": tot.isoformat(), "_links": links,
                     "_embedded": {"personen": people}}
    return _error(404, "Onbekend adres.", start)


class FakeTransport:
    """Answers a URL of the fake spic or jaarkalender, as the HTTP transport would."""

    def __init__(self, today=None):
        self.today = today

    def __call__(self, url):
        parts = urllib.parse.urlsplit(url)
        query = dict(urllib.parse.parse_qsl(parts.query))
        if parts.netloc == "spic.fake":
            return spic(parts.path, query, self.today)
        if parts.netloc == "jaarkalender.fake":
            return jaarkalender(parts.path, query)
        return 404, {"fout": "Onbekende dienst."}
