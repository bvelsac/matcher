"""Browser tests for the visual style (docs/visual-style.md), with Playwright and Chromium.

Skipped when Playwright is not installed. Bootstrap and its icons come from a CDN; where the
CDN cannot be reached, point PDC_CDN_DIR at a folder with the unpacked npm packages
(`<name>-<version>/package/...`, e.g. from `npm pack bootstrap@5.3.0`) and the tests serve
those files instead. PDC_CHROMIUM can point at a Chromium binary when Playwright's own
browser is not installed.
"""
import os
import re
import threading

import pytest
from werkzeug.serving import make_server

from conftest import login

sync_api = pytest.importorskip("playwright.sync_api")

CDN_URL = re.compile(r"https://cdn\.jsdelivr\.net/npm/([^@/]+)@([^/]+)/([^?#]*)")


@pytest.fixture
def server(app):
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:{}".format(srv.server_port)
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        executable = os.environ.get("PDC_CHROMIUM")
        try:
            chromium = p.chromium.launch(executable_path=executable) if executable else p.chromium.launch()
        except sync_api.Error as error:
            pytest.skip("Chromium is not available: {}".format(error))
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    cdn_dir = os.environ.get("PDC_CDN_DIR")
    if cdn_dir:
        def serve_local(route):
            match = CDN_URL.match(route.request.url)
            path = match and os.path.join(cdn_dir, "{}-{}".format(*match.groups()[:2]), "package", match.group(3))
            if path and os.path.isfile(path):
                route.fulfill(path=path)
            else:
                route.abort()

        page.route("https://cdn.jsdelivr.net/**", serve_local)
    yield page
    page.close()


def log_in(page, server, username="editor"):
    page.goto(server + "/login")
    page.fill("#username", username)
    page.fill("#password", "password123")
    page.click("button[type=submit]")
    page.wait_for_url(server + "/")


# Relative luminance and contrast ratio (WCAG 2.x), computed in the page.
CONTRAST_JS = """
(el) => {
    const rgb = (value) => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
    const lum = ([r, g, b]) => {
        const c = [r, g, b].map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    };
    const style = getComputedStyle(el);
    const a = lum(rgb(style.color)), b = lum(rgb(style.backgroundColor));
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}
"""


def test_login_page_has_the_pdc_look(page, server):
    page.goto(server + "/login")

    assert page.title() == "Login - PDC"
    body = page.evaluate("""() => {
        const s = getComputedStyle(document.body);
        const eye = getComputedStyle(document.body, '::before');
        return {font: s.fontFamily, background: s.backgroundColor,
                eye: eye.backgroundImage, rendering: eye.imageRendering, opacity: eye.opacity};
    }""")
    assert body["font"].startswith("Arial")
    assert body["background"] == "rgb(3, 0, 1)"
    assert "img/eye.png" in body["eye"]
    assert body["rendering"] == "pixelated"
    # The eye shows more on the login page than behind the working screens.
    assert float(body["opacity"]) > 0.4

    for asset in ("css/pdc.css", "img/eye.png", "img/grain.png", "img/edge.png"):
        assert page.request.get(server + "/static/" + asset).status == 200


def test_working_screens_keep_text_readable(app, page, server):
    log_in(page, server)

    assert page.inner_text(".navbar-brand .pdc-brand") == "PDC"
    eye_opacity = page.evaluate("() => getComputedStyle(document.body, '::before').opacity")
    assert float(eye_opacity) < 0.3

    # Filled buttons and badges: at least WCAG AA (4.5:1) between text and background.
    for selector in (".btn-primary", ".badge"):
        for element in page.query_selector_all(selector):
            assert element.evaluate(CONTRAST_JS) >= 4.5, selector

    # Body text on the page background.
    assert page.query_selector("body").evaluate(CONTRAST_JS) >= 7


def test_meeting_list_badges_are_readable(app, page, server):
    client = app.test_client()
    login(client, "editor")
    client.post("/meetings/add", data={
        "name": "Test meeting", "date": "2099-01-05", "time": "10:00", "estimated_duration": "2",
        "interpreters_needed": "2", "category": "parliament", "location": "Room 1",
    })
    log_in(page, server)
    page.goto(server + "/meetings")

    badges = page.query_selector_all("table .badge")
    assert badges
    for badge in badges:
        assert badge.evaluate(CONTRAST_JS) >= 4.5


@pytest.mark.parametrize("path, background, accent", [
    ("/", "bg-dashboard.png", "rgb(254, 219, 149)"),
    ("/interpreters", "bg-interpreters.png", "rgb(251, 180, 194)"),
    ("/interpreters/add", "bg-interpreter-form.png", "rgb(251, 180, 194)"),
    ("/meetings", "bg-meetings.png", "rgb(207, 161, 238)"),
    ("/meetings/add", "bg-meeting-form.png", "rgb(207, 161, 238)"),
    ("/does-not-exist", "bg-error.png", "rgb(254, 198, 184)"),
])
def test_each_screen_has_its_own_background_and_accent(page, server, path, background, accent):
    log_in(page, server)
    page.goto(server + path)

    image = page.evaluate("() => getComputedStyle(document.body, '::before').backgroundImage")
    assert "img/" + background in image
    assert page.request.get(server + "/static/img/" + background).status == 200
    # The icon of the page title (or of the error) carries the accent colour of the screen.
    icon = page.query_selector("h1 .bi, .error-icon")
    assert icon.evaluate("(el) => getComputedStyle(el).color") == accent

    active = page.query_selector(".sidebar .nav-link.active")
    if active:  # the error pages have no active menu item
        assert active.evaluate("(el) => getComputedStyle(el).backgroundColor") == accent
        assert active.evaluate(CONTRAST_JS) >= 4.5


def test_navbar_sits_at_the_bottom(page, server):
    log_in(page, server)
    page.goto(server + "/interpreters")

    box = page.query_selector(".pdc-navbar").bounding_box()
    viewport = page.viewport_size
    assert abs(box["y"] + box["height"] - viewport["height"]) < 1
    # The page keeps room for it, so the last content is not hidden behind the bar.
    padding = page.evaluate("() => parseFloat(getComputedStyle(document.body).paddingBottom)")
    assert padding >= box["height"]

    # The user menu opens upwards, inside the screen.
    toggle = page.query_selector(".pdc-navbar .dropdown-toggle")
    toggle.click()
    menu_box = page.wait_for_selector(".pdc-navbar .dropdown-menu.show").bounding_box()
    assert menu_box["y"] >= 0
    assert menu_box["y"] + menu_box["height"] <= toggle.bounding_box()["y"] + 1
