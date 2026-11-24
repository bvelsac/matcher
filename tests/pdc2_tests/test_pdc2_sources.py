"""The HAL client follows links only, and the fake services answer the documents of the contract."""
from datetime import date

import pytest

from pdc2 import fake
from pdc2.hal import Client, HalError, expand


def test_templated_links_are_filled_in():
    assert expand("/weken/{maandag}", maandag="2030-01-07") == "/weken/2030-01-07"
    assert expand("/aanwezigheid{?van,tot}", van="2030-01-07", tot="2030-01-11") == \
        "/aanwezigheid?van=2030-01-07&tot=2030-01-11"
    assert expand("/x{?van,tot}", van="a") == "/x?van=a"
    with pytest.raises(HalError):
        expand("/weken/{maandag}")


def test_the_client_finds_a_week_of_spic_by_following_links():
    client = Client(fake.SPIC_ENTRY, fake.FakeTransport(today=date(2030, 1, 9)))
    root = client.root()
    assert root["afnemer"] == "pdc2"
    week = root.follow("week", maandag="2030-01-07")
    assert week["maandag"] == "2030-01-07" and week["status"] == "definitief"
    meetings = week.embedded("vergaderingen")
    assert meetings and all(m["datum"].startswith("2030-01") for m in meetings)
    assert {"id", "status", "termijn", "agenda_onbekend", "werkuren", "_links"} <= set(meetings[0])
    later = week.follow("volgende").follow("volgende")
    assert later["status"] == "concept"
    with pytest.raises(HalError) as error:
        root.follow("week", maandag="2030-01-08")      # not a Monday
    assert error.value.status == 400


def test_the_fake_week_is_always_the_same():
    assert fake.meetings(date(2030, 1, 7)) == fake.meetings(date(2030, 1, 7))


def test_the_jaarkalender_gives_staff_presence_and_working_days():
    root = Client(fake.JK_ENTRY, fake.FakeTransport()).root()
    people = root.follow("medewerkers").embedded("medewerkers")
    assert {"id", "moedertaal", "standaardrol", "rollen"} <= set(people[0])
    presence = root.follow("aanwezigheid", van="2030-01-07", tot="2030-01-11")
    entries = {p["id"]: p for p in presence.embedded("personen")}
    assert entries["wmich"]["gevalideerd"] is False and entries["wmich"]["dagdelen"] is None
    assert len(entries["ajans"]["dagdelen"]["2030-01-07"]) == 2
    days = root.follow("werkdagen", van="2030-11-10", tot="2030-11-12")["dagen"]
    assert [d["werkdag"] for d in days] == [False, False, True]   # Sunday, 11 November, Tuesday
    with pytest.raises(HalError):
        root.follow("aanwezigheid", van="2030-01-01", tot="2030-06-01")   # more than 62 days


def test_a_service_that_cannot_be_reached_is_a_hal_error():
    def down(url):
        raise HalError("down")
    with pytest.raises(HalError):
        Client("http://spic:8000/api/afnemers", down).root()
