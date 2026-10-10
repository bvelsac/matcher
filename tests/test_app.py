from conftest import login, meeting_form, query
from extensions import db
from models import Interpreter, Meeting, User


def add_interpreter(client, first, last, email, bureau=""):
    return client.post("/interpreters/add", data={
        "first_name": first, "last_name": last, "email": email, "bureau_affiliation": bureau,
    })


def add_meeting(client, **changes):
    return client.post("/meetings/add", data=meeting_form(**changes))


def interpreter_count(app):
    return query(app, lambda: Interpreter.query.count())


def test_without_authelia_nobody_gets_in(client):
    response = client.get("/")
    assert response.status_code == 401
    assert b"not signed in" in response.data
    assert client.get("/interpreters").status_code == 401
    assert client.post("/interpreters/reorder", json={"order": []}).status_code == 401


def test_identity_comes_from_authelia(app, client):
    login(client, "anna", "Anna Peeters")
    page = client.get("/").data.decode()
    assert "Anna Peeters" in page
    assert 'href="https://login.infracriv.net/logout"' in page
    client.get("/interpreters")
    assert query(app, lambda: User.query.filter_by(username="anna").count()) == 1

    # Authelia sends UTF-8, Werkzeug reads Latin-1: the name must still arrive intact.
    login(client, "anna", "Ann\u00e9e".encode("utf-8").decode("latin-1"))
    assert "Ann\u00e9e" in client.get("/").data.decode()
    assert query(app, lambda: User.query.filter_by(username="anna").one().name) == "Ann\u00e9e"


def test_rights_follow_the_list_of_editors(app, client):
    login(client, "Editor")  # user ids are compared without regard to case
    assert b">editor</span>" in client.get("/").data
    add_interpreter(client, "A", "B", "a@example.org")
    assert interpreter_count(app) == 1

    login(client, "someone-else")
    assert b">viewer</span>" in client.get("/").data


def test_development_mode_uses_a_fixed_user(app, client):
    app.config.update(PDC_AUTH_MODE="dev", PDC_DEV_USER="dev", PDC_DEV_NAME="Dev Eloper", PDC_EDITORS="dev")
    try:
        page = client.get("/").data.decode()
        assert "Dev Eloper" in page and ">editor</span>" in page
    finally:
        app.config.update(PDC_AUTH_MODE="authelia", PDC_EDITORS="editor,editor2")


def test_pages_render(app, client):
    login(client, "editor")
    add_interpreter(client, "Jose", "D'Hoore", "planning@bureau.example", "Bureau Beta")
    add_meeting(client)
    meeting_id = query(app, lambda: Meeting.query.first().id)
    for url in ["/", "/interpreters", "/interpreters/add", "/interpreters/1/edit",
                "/meetings", "/meetings/add", "/meetings/{}".format(meeting_id), "/meetings/{}/edit".format(meeting_id),
                "/bookings", "/bookings/add", "/invoices", "/invoices/add", "/worklists"]:
        response = client.get(url)
        assert response.status_code == 200, url
    # Names with an apostrophe are passed through data attributes, not inline JavaScript.
    assert b'data-name="Jose D&#39;Hoore"' in client.get("/interpreters").data


def test_add_interpreter_normalises_email_and_rejects_duplicates(app, client):
    login(client, "editor")
    add_interpreter(client, "Anna", "Peeters", "  Anna.Peeters@Example.org ")
    assert query(app, lambda: Interpreter.query.one().email) == "anna.peeters@example.org"
    response = add_interpreter(client, "Other", "Person", "anna.peeters@example.org")
    assert b"already exists" in response.data
    assert b'value="Other"' in response.data  # the form keeps what was typed
    assert interpreter_count(app) == 1


def test_priority_order_appends_reorders_and_renumbers(app, client):
    login(client, "editor")
    for n in range(1, 4):
        add_interpreter(client, "P", str(n), "p{}@example.org".format(n))

    def by_priority():
        return [i.id for i in Interpreter.query.order_by(Interpreter.priority_order)]

    ids = query(app, by_priority)
    assert query(app, lambda: [i.priority_order for i in Interpreter.query.order_by(Interpreter.id)]) == [1, 2, 3]

    response = client.post("/interpreters/reorder", json={"order": list(reversed(ids))})
    assert response.get_json() == {"success": True}
    assert query(app, by_priority) == list(reversed(ids))

    # Incomplete order lists are refused, so priorities cannot end up duplicated.
    assert client.post("/interpreters/reorder", json={"order": ids[:2]}).status_code == 400

    client.post("/interpreters/{}/delete".format(ids[1]))
    assert query(app, lambda: sorted(i.priority_order for i in Interpreter.query)) == [1, 2]


def test_own_meetings_crud(app, client):
    login(client, "editor")
    response = add_meeting(client, title="Uitgebreid Bureau", start="12:00", end="")
    assert b"Fill in the end or the duration" in response.data
    assert b'value="Uitgebreid Bureau"' in response.data  # the form keeps what was typed

    add_meeting(client, title="Uitgebreid Bureau", start="12:00", end="", duration_hours="1,5")
    meeting = query(app, lambda: Meeting.query.one())
    assert (meeting.origin, meeting.status, meeting.period) == ("own", "planned", "PM")
    assert meeting.expected_end.strftime("%H:%M") == "13:30"
    meeting_id, meeting_date = meeting.id, meeting.date

    response = client.post("/meetings/{}/edit".format(meeting_id), data=meeting_form(
        title="Uitgebreid Bureau", date=meeting_date.isoformat(), start="12:30", end="14:00",
        room="R2", interpreters_needed="3", notes="Bring the folder"))
    assert response.status_code == 302
    saved = query(app, lambda: Meeting.query.one())
    assert (saved.effective_start.strftime("%H:%M"), saved.interpreters_needed, saved.room) == ("12:30", 3, "R2")

    page = client.get("/meetings/{}/edit".format(meeting_id)).data
    assert b'value="12:30"' in page
    assert 'value="{}"'.format(meeting_date.isoformat()).encode() in page
    assert b'<option value="parliament" selected>' in page

    for broken, message in [({"start": "not-a-time"}, b"Check the time"), ({"end": "09:00"}, b"end must be after"),
                            ({"title": ""}, b"Title and room are required"),
                            ({"interpreters_needed": "0"}, b"at least 1"), ({"category": ""}, b"Choose a category")]:
        response = add_meeting(client, **broken)
        assert message in response.data, broken
    assert query(app, lambda: Meeting.query.count()) == 1

    client.post("/meetings/{}/delete".format(meeting_id))
    assert query(app, lambda: Meeting.query.count()) == 0


def test_viewer_cannot_change_data(app, client):
    login(client, "viewer")
    assert client.get("/interpreters").status_code == 200
    response = add_interpreter(client, "A", "B", "a@example.org")
    assert response.status_code == 302
    assert interpreter_count(app) == 0


def test_there_is_no_editing_lock(app):
    first, second = app.test_client(), app.test_client()
    login(first, "editor")
    login(second, "editor2")
    assert first.post("/system/lock", json={}).status_code == 404
    add_interpreter(first, "A", "B", "a@example.org")
    add_interpreter(second, "C", "D", "c@example.org")
    assert interpreter_count(app) == 2
    assert b"Lock system" not in first.get("/").data


def edit_form(client, url):
    """The loaded_at value of an edit form, as the browser would send it back."""
    page = client.get(url).data.decode()
    return page.split('name="loaded_at" value="')[1].split('"')[0]


def test_an_outdated_form_is_caught_when_saved(app):
    first, second = app.test_client(), app.test_client()
    login(first, "editor")
    login(second, "editor2")
    add_interpreter(first, "Anna", "Peeters", "anna@example.org")
    url = "/interpreters/1/edit"
    loaded_first, loaded_second = edit_form(first, url), edit_form(second, url)

    fields = {"first_name": "Anna", "last_name": "Peeters-Janssens", "email": "anna@example.org"}
    assert first.post(url, data=dict(fields, loaded_at=loaded_first)).status_code == 302

    response = second.post(url, data=dict(fields, last_name="Other", loaded_at=loaded_second))
    assert b"Someone else changed this interpreter" in response.data
    assert b"Peeters-Janssens" in response.data  # the current details are shown
    assert query(app, lambda: Interpreter.query.one().last_name) == "Peeters-Janssens"

    # Saving again from the refreshed form works.
    response = second.post(url, data=dict(fields, last_name="Other", loaded_at=edit_form(second, url)))
    assert response.status_code == 302
    assert query(app, lambda: Interpreter.query.one().last_name) == "Other"


def test_an_outdated_meeting_form_is_caught(app, client):
    login(client, "editor")
    add_meeting(client)
    url = "/meetings/1/edit"
    loaded = edit_form(client, url)
    assert client.post(url, data=dict(meeting_form(room="R2"), loaded_at=loaded)).status_code == 302
    response = client.post(url, data=dict(meeting_form(room="R3"), loaded_at=loaded))
    assert b"Someone else changed this meeting" in response.data
    assert query(app, lambda: Meeting.query.one().room) == "R2"


def test_sqlite_enforces_foreign_keys(app):
    def pragma():
        return db.session.execute(db.text("PRAGMA foreign_keys")).scalar()
    assert query(app, pragma) == 1


def test_404_page_for_logged_in_user(client):
    login(client, "editor")
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_csrf_is_enforced(app):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        client = app.test_client()
        login(client, "editor")
        fields = {"first_name": "A", "last_name": "B", "email": "a@example.org"}
        assert client.post("/interpreters/add", data=fields).status_code == 400
        page = client.get("/interpreters/add").data.decode()
        token = page.split('name="csrf_token" value="')[1].split('"')[0]
        response = client.post("/interpreters/add", data=dict(fields, csrf_token=token))
        assert response.status_code == 302
    finally:
        app.config["WTF_CSRF_ENABLED"] = False
