"""The screens of PDC2, end to end, with spic and the jaarkalender simulated (PDC2_SOURCE=fake)."""
import io
from datetime import date, timedelta

from pdc2 import fake
from pdc2.extensions import db
from pdc2.models import Booking, Exclusion, Gm, Offer, User
from pdc2.sample_data import load
from pdc2_tests.conftest import run, sign_in

THIS_MONDAY = date.today() - timedelta(days=date.today().weekday())


def week_url(monday=THIS_MONDAY, page=""):
    return "/weeks/{}{}".format(monday.isoformat(), page)


def with_sample_data(app):
    def go():
        load()
        db.session.commit()
    run(app, go)


def test_nobody_gets_in_without_authelia(pdc2_app):
    client = pdc2_app.test_client()
    assert client.get("/").status_code == 401
    assert client.get(week_url()).status_code == 401


def test_every_screen_opens(pdc2_app, planner):
    with_sample_data(pdc2_app)
    assert planner.get("/").headers["Location"].endswith(week_url())
    for url in [week_url(), week_url(page="/staff"), week_url(page="/offers"), week_url(page="/bookings"),
                "/gms", "/gms/new", "/gms/1", "/import", "/dimona", "/log", week_url(THIS_MONDAY + timedelta(days=21))]:
        response = planner.get(url)
        assert response.status_code == 200, url
        assert b"test data" in response.data           # the fake sources are announced
    # A date that is not a Monday leads to its week.
    assert planner.get("/weeks/{}".format((THIS_MONDAY + timedelta(days=2)).isoformat())).headers["Location"].endswith(week_url())


def test_the_week_shows_the_calculation(pdc2_app, planner):
    page = planner.get(week_url()).data.decode()
    assert "Shortage of the week" in page and "NL" in page and "FR" in page
    assert "Redacteur" in page and "Revisor" in page and "planned on sight" in page
    assert "io-meter" in page and "Staff counted in another role" in page
    assert "Wanda Michel has no validated calendar" in page
    assert "Xavier Coppens has no language or standard role" in page


def test_a_week_in_concept_is_marked_provisional(pdc2_app, planner):
    page = planner.get(week_url(THIS_MONDAY + timedelta(days=21))).data.decode()
    assert "concept" in page and "provisional" in page


def test_booking_with_htmx_answers_the_half_day_and_the_shortage(pdc2_app, planner):
    with_sample_data(pdc2_app)
    offer = run(pdc2_app, lambda: Offer.query.filter(Offer.date >= THIS_MONDAY, Offer.date <= THIS_MONDAY + timedelta(days=4))
                .join(Gm).filter(~Gm.bookings.any()).first())
    gm_id, day, period = offer.gm_id, offer.date, offer.period
    lang = run(pdc2_app, lambda: db.session.get(Gm, gm_id).languages[0])
    response = planner.post("/bookings", data={"gm_id": gm_id, "date": day.isoformat(), "period": period,
                                               "role": "redacteur", "language": lang}, headers={"HX-Request": "true"})
    page = response.data.decode()
    assert response.status_code == 200
    assert 'id="halfday-{}-{}"'.format(day.isoformat(), period) in page
    assert 'id="shortage-summary"' in page and 'hx-swap-oob="true"' in page
    assert "<html" not in page                               # a fragment, not a page
    assert run(pdc2_app, lambda: Booking.query.filter_by(gm_id=gm_id, date=day, period=period).one().status) == "proposed"

    # The same again is refused, with the reason in the fragment.
    page = planner.post("/bookings", data={"gm_id": gm_id, "date": day.isoformat(), "period": period,
                                           "role": "redacteur", "language": lang}, headers={"HX-Request": "true"}).data.decode()
    assert "BR-GM-001" in page

    booking_id = run(pdc2_app, lambda: Booking.query.filter_by(gm_id=gm_id, date=day, period=period).one().id)
    planner.post("/bookings/{}/confirm".format(booking_id), headers={"HX-Request": "true"})
    row = planner.post("/bookings/{}/dimona".format(booking_id), data={"target": "row"}, headers={"HX-Request": "true"}).data.decode()
    assert 'id="booking-{}"'.format(booking_id) in row and "declared" in row


def test_marking_staff_with_htmx(pdc2_app, planner):
    page = planner.get(week_url(page="/staff")).data.decode()
    assert "Anke Janssens" in page
    day, period = next((d, p) for d in (THIS_MONDAY + timedelta(days=i) for i in range(5)) for p in ("AM", "PM")
                       if fake.present("ajans", d, p))
    response = planner.post(week_url(page="/staff/mark"), data={"person_id": "ajans", "person_name": "Anke Janssens",
                            "date": day.isoformat(), "period": period}, headers={"HX-Request": "true", "HX-Prompt": "training"})
    assert response.status_code == 200
    assert run(pdc2_app, lambda: Exclusion.query.one().reason) == "training"
    assert "marked" in response.data.decode()
    planner.post(week_url(page="/staff/mark"), data={"person_id": "ajans", "date": day.isoformat(), "period": period,
                                                     "action": "unmark"}, headers={"HX-Request": "true"})
    assert run(pdc2_app, lambda: Exclusion.query.count()) == 0


def test_a_viewer_can_read_but_not_change(pdc2_app):
    with_sample_data(pdc2_app)
    viewer = sign_in(pdc2_app.test_client(), "someone")
    assert viewer.get(week_url(page="/offers")).status_code == 200
    assert b"Book</button>" not in viewer.get(week_url(page="/offers")).data
    before = run(pdc2_app, lambda: Booking.query.count())
    assert viewer.post("/bookings", data={"gm_id": 1, "date": THIS_MONDAY.isoformat(), "period": "AM",
                                          "role": "redacteur", "language": "nl"}, headers={"HX-Request": "true"}).status_code == 403
    assert viewer.post("/gms/new", data={"first_name": "x"}).status_code == 403
    assert run(pdc2_app, lambda: Booking.query.count()) == before


def test_gm_register_and_manual_offer(pdc2_app, planner):
    response = planner.post("/gms/new", data={"first_name": "Zoë", "last_name": "Zeegers", "email": "zoe@example.org",
                                              "languages": ["nl", "fr"], "standard_role": "redacteur",
                                              "roles": ["revisor"], "active": "1"})
    assert response.status_code == 302
    gm = run(pdc2_app, lambda: Gm.query.filter_by(email="zoe@example.org").one())
    assert gm.languages == ["nl", "fr"] and gm.capable_roles == ["redacteur", "revisor"]
    assert b"Choose at least one language" in planner.post("/gms/new", data={
        "first_name": "A", "last_name": "B", "email": "ab@example.org", "standard_role": "revisor"}).data
    planner.post("/offers", data={"gm_id": gm.id, "date": THIS_MONDAY.isoformat(), "period": "PM"})
    assert run(pdc2_app, lambda: Offer.query.filter_by(gm_id=gm.id).one().source) == "manual"


def test_import_screen(pdc2_app, planner):
    planner.post("/gms/new", data={"first_name": "Ann", "last_name": "A", "email": "ann@example.org",
                                   "languages": ["nl"], "standard_role": "redacteur", "active": "1"})
    csv_text = "Timestamp,Email address,{} AM,{} PM\n2030-01-01 10:00:00,ann@example.org,ja,\n".format(
        THIS_MONDAY.isoformat(), THIS_MONDAY.isoformat())
    page = planner.post("/import", data={"file": (io.BytesIO(csv_text.encode()), "offers.csv")},
                        content_type="multipart/form-data").data.decode()
    assert "<strong>1</strong> offers recorded" in page


def test_without_the_services_the_week_says_so(pdc2_app, planner):
    pdc2_app.config.update(PDC2_SOURCE="live", PDC2_SPIC_TOKEN="", PDC2_JK_TOKEN="")
    try:
        page = planner.get(week_url()).data.decode()
        assert "cannot be read" in page
    finally:
        pdc2_app.config.update(PDC2_SOURCE="fake")


def test_the_log_shows_what_happened(pdc2_app, planner):
    with_sample_data(pdc2_app)
    page = planner.get("/log").data.decode()
    assert "booked" in page and "Sample data" in page
    assert run(pdc2_app, lambda: User.query.filter_by(username="planner").count()) == 1


def test_htmx_requests_carry_the_csrf_token(pdc2_app, planner):
    with_sample_data(pdc2_app)
    pdc2_app.config["WTF_CSRF_ENABLED"] = True
    try:
        page = planner.get(week_url(page="/offers")).data.decode()
        token = page.split('"X-CSRFToken": "')[1].split('"')[0]
        data = {"gm_id": 1, "date": THIS_MONDAY.isoformat(), "period": "PM", "role": "redacteur", "language": "nl"}
        assert planner.post("/bookings", data=data, headers={"HX-Request": "true"}).status_code == 400
        response = planner.post("/bookings", data=data, headers={"HX-Request": "true", "X-CSRFToken": token})
        assert response.status_code == 200
    finally:
        pdc2_app.config["WTF_CSRF_ENABLED"] = False
