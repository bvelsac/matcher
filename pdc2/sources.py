"""What PDC2 reads from spic and the jaarkalender, by following the links of their APIs.

PDC2 knows only the entry addresses; every other address comes from a link (HATEOAS). The answers are
turned into the plain records of pdc2/calc.py. With PDC2_SOURCE=fake the same code reads the fake
services of pdc2/fake.py.
"""
from datetime import date, timedelta

from flask import current_app, g

from pdc2 import fake
from pdc2.calc import Meeting, StaffMember
from pdc2.hal import Client, HalError, HttpTransport

__all__ = ["HalError", "spic", "jaarkalender", "week_of_spic", "staff", "workdays"]


def _client(entry_key, token_key):
    cfg = current_app.config
    if cfg["PDC2_SOURCE"] == "fake":
        entry = fake.SPIC_ENTRY if entry_key == "PDC2_SPIC_API" else fake.JK_ENTRY
        return Client(entry, fake.FakeTransport())
    if not cfg.get(entry_key) or not cfg.get(token_key):
        raise HalError("{} and {} are not set.".format(entry_key, token_key))
    return Client(cfg[entry_key], HttpTransport(cfg[token_key]))


def _cached(key, load):
    """One request reads each document once."""
    cache = g.setdefault("pdc2_sources", {})
    if key not in cache:
        cache[key] = load()
    return cache[key]


def spic():
    return _cached("spic", lambda: _client("PDC2_SPIC_API", "PDC2_SPIC_TOKEN").root())


def jaarkalender():
    return _cached("jk", lambda: _client("PDC2_JK_API", "PDC2_JK_TOKEN").root())


def _time(value):
    return value or None


def week_of_spic(monday):
    """(week status, [Meeting]) for the week of `monday`."""
    def load():
        week = spic().follow("week", maandag=monday.isoformat())
        meetings = []
        for m in week.embedded("vergaderingen"):
            hours = m.get("werkuren")
            meetings.append(Meeting(
                id=m["id"], date=date.fromisoformat(m["datum"]), period=m.get("periode"),
                status=m.get("status", "gepland"), deadline=m.get("termijn") or "zelfde-dag",
                hours=None if hours is None else {"nl": float(hours.get("nl") or 0), "fr": float(hours.get("fr") or 0)},
                agenda_unknown=bool(m.get("agenda_onbekend")),
                label=" ".join(str(x) for x in (m.get("type"), m.get("volgnummer")) if x),
                start=_time(m.get("effectief_begin")), room=m.get("zaal")))
        return week.get("status"), meetings
    return _cached(("week", monday), load)


def staff(van, tot):
    """[StaffMember] with their half-days between `van` and `tot`."""
    def load():
        root = jaarkalender()
        people = {p["id"]: p for p in root.follow("medewerkers").embedded("medewerkers")}
        presence = root.follow("aanwezigheid", van=van.isoformat(), tot=tot.isoformat())
        out = []
        for entry in presence.embedded("personen"):
            person = people.get(entry["id"])
            if person is None or not person.get("actief", True):
                continue
            halves = entry.get("dagdelen")
            out.append(StaffMember(
                id=person["id"], name="{} {}".format(person.get("voornaam", ""), person.get("naam", "")).strip(),
                language=person.get("moedertaal"), standard_role=person.get("standaardrol"),
                roles=dict(person.get("rollen") or {}), validated=bool(entry.get("gevalideerd")),
                halves={date.fromisoformat(d): tuple(v) for d, v in halves.items()} if halves else {}))
        return out
    return _cached(("staff", van, tot), load)


def workdays(van, tot):
    """The working days between `van` and `tot`, by the jaarkalender."""
    def load():
        answer = jaarkalender().follow("werkdagen", van=van.isoformat(), tot=tot.isoformat())
        return [date.fromisoformat(d["datum"]) for d in answer.get("dagen", []) if d.get("werkdag")]
    return _cached(("workdays", van, tot), load)


def window(monday):
    """The days the calculation of a week needs: from the last working day before the week (work can be
    carried into Monday) to the first working day after it (work carried out of Friday)."""
    return monday - timedelta(days=10), monday + timedelta(days=13)
