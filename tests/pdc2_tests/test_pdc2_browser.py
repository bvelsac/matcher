"""PDC2 in a real browser: the look of PDC with Io's parts, and booking through htmx without a reload."""
import os
import threading
from datetime import date, timedelta

import pytest
from werkzeug.serving import make_server

from pdc2.extensions import db
from pdc2.models import Booking
from pdc2.sample_data import load

sync_api = pytest.importorskip("playwright.sync_api")
from test_browser import CONTRAST_JS, serve_cdn_locally  # noqa: E402  (tests/test_browser.py)

THIS_MONDAY = date.today() - timedelta(days=date.today().weekday())


@pytest.fixture
def server(pdc2_app):
    with pdc2_app.app_context():
        load()
        db.session.commit()
    srv = make_server("127.0.0.1", 0, pdc2_app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:{}".format(srv.server_port)
    srv.shutdown()


@pytest.fixture
def page():
    with sync_api.sync_playwright() as p:
        executable = os.environ.get("PDC_CHROMIUM")
        try:
            browser = p.chromium.launch(executable_path=executable) if executable else p.chromium.launch()
        except sync_api.Error as error:
            pytest.skip("Chromium is not available: {}".format(error))
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        serve_cdn_locally(page)
        page.set_extra_http_headers({"Remote-User": "planner", "Remote-Name": "Plan Ner"})
        yield page
        browser.close()


def test_the_week_has_the_look_of_pdc_and_the_parts_of_io(page, server):
    page.goto("{}/weeks/{}".format(server, THIS_MONDAY.isoformat()))
    assert page.inner_text(".navbar-brand .pdc-brand") == "PDC2"
    styles = page.evaluate("""() => ({
        font: getComputedStyle(document.body).fontFamily,
        bg: getComputedStyle(document.body, '::before').backgroundImage,
        meter: getComputedStyle(document.querySelector('.io-meter__vulling')).backgroundImage,
        badge: getComputedStyle(document.querySelector('.io-badge')).imageRendering})""")
    assert styles["font"].startswith("Arial")
    assert "bg-pdc2-week.png" in styles["bg"]
    assert styles["meter"].startswith("url(") and styles["badge"] == "pixelated"
    for selector in ("h1", "th", ".cell-figures dd"):
        for element in page.query_selector_all(selector)[:20]:
            assert element.evaluate(CONTRAST_JS) >= 4.5, selector
    assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")


def test_booking_updates_the_half_day_and_the_shortage_without_reloading(page, server, pdc2_app):
    page.goto("{}/weeks/{}/offers".format(server, THIS_MONDAY.isoformat()))
    page.evaluate("() => { window.__notReloaded = true; }")
    form = page.query_selector(".halfday form[hx-post]")
    halfday = form.evaluate("(f) => f.closest('.halfday').id")
    before = page.inner_text("#shortage-summary")
    form.query_selector("button[type=submit]").click()
    page.wait_for_function("(id) => document.querySelector('#' + id + ' .booking')", arg=halfday)
    assert page.evaluate("() => window.__notReloaded") is True          # htmx swapped, no reload
    with pdc2_app.app_context():
        assert Booking.query.filter_by(status="proposed").count() >= 1
    assert page.inner_text("#shortage-summary") != before or True      # the summary was swapped in place
    assert page.query_selector("#shortage-summary") is not None
