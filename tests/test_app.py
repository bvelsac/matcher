from datetime import date, datetime, timedelta

from conftest import login, query
from extensions import db
from models import Interpreter, Meeting, SystemLock


def add_interpreter(client, first, last, email, bureau=""):
    return client.post("/interpreters/add", data={
        "first_name": first, "last_name": last, "email": email, "bureau_affiliation": bureau,
    })


def add_meeting(client, name="Bureau", days_ahead=3, time="12:15"):
    return client.post("/meetings/add", data={
        "name": name,
        "date": (date.today() + timedelta(days=days_ahead)).isoformat(),
        "time": time,
        "estimated_duration": "2",
        "interpreters_needed": "1",
        "location": "Room 1",
        "category": "parliament",
    })


def interpreter_count(app):
    return query(app, lambda: Interpreter.query.count())


def test_login_required(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_bad_login(client):
    response = client.post("/login", data={"username": "editor", "password": "wrong"})
    assert b"Invalid username or password" in response.data


def test_pages_render(app, client):
    login(client, "editor")
    add_interpreter(client, "Jose", "D'Hoore", "planning@bureau.example", "Bureau Beta")
    add_meeting(client)
    meeting_id = query(app, lambda: Meeting.query.first().id)
    for url in ["/", "/interpreters", "/interpreters/add", "/interpreters/1/edit",
                "/meetings", "/meetings/add", "/meetings/{}/edit".format(meeting_id)]:
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


def test_meetings_crud(app, client):
    login(client, "editor")
    add_meeting(client, name="Uitgebreid Bureau", time="12:00")
    meeting_id, meeting_date = query(app, lambda: (Meeting.query.one().id, Meeting.query.one().date))

    response = client.post("/meetings/{}/edit".format(meeting_id), data={
        "name": "Uitgebreid Bureau", "date": meeting_date.isoformat(), "time": "12:30",
        "estimated_duration": "3", "interpreters_needed": "2", "location": "Room 2",
        "category": "parliament",
    })
    assert response.status_code == 302
    saved = query(app, lambda: (Meeting.query.one().time.strftime("%H:%M"), Meeting.query.one().interpreters_needed))
    assert saved == ("12:30", 2)

    page = client.get("/meetings/{}/edit".format(meeting_id)).data
    assert b'value="12:30"' in page
    assert 'value="{}"'.format(meeting_date.isoformat()).encode() in page
    assert b'<option value="3" selected>' in page

    response = add_meeting(client, name="Broken", time="not-a-time")
    assert b"Check the date, time" in response.data
    assert b'value="Broken"' in response.data  # the form keeps what was typed

    client.post("/meetings/{}/delete".format(meeting_id))
    assert query(app, lambda: Meeting.query.count()) == 0


def test_viewer_cannot_change_data(app, client):
    login(client, "viewer")
    assert client.get("/interpreters").status_code == 200
    response = add_interpreter(client, "A", "B", "a@example.org")
    assert response.status_code == 302
    assert interpreter_count(app) == 0
    assert client.post("/system/lock", json={}).status_code == 403


def test_editing_lock_blocks_other_editors(app):
    first, second = app.test_client(), app.test_client()
    login(first, "editor")
    login(second, "editor2")

    assert first.post("/system/lock", json={}).get_json() == {"success": True}
    assert b"Unlock system" in first.get("/").data
    assert b"Locked by editor" in second.get("/").data

    assert second.post("/system/lock", json={}).status_code == 409
    add_interpreter(second, "A", "B", "a@example.org")
    assert interpreter_count(app) == 0
    add_interpreter(first, "A", "B", "a@example.org")
    assert interpreter_count(app) == 1

    assert second.post("/system/unlock", json={}).status_code == 404
    assert first.post("/system/unlock", json={}).get_json() == {"success": True}
    add_interpreter(second, "C", "D", "c@example.org")
    assert interpreter_count(app) == 2


def test_stale_lock_expires(app, client):
    def add_old_lock():
        db.session.add(SystemLock(locked_by_user_id=1, lock_type="editing",
                                  created_at=datetime.utcnow() - timedelta(days=1)))
        db.session.commit()

    query(app, add_old_lock)
    login(client, "editor2")
    add_interpreter(client, "A", "B", "a@example.org")
    assert interpreter_count(app) == 1
    assert query(app, lambda: SystemLock.query.count()) == 0


def test_404_page_for_logged_in_user(client):
    login(client, "editor")
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_csrf_is_enforced(app):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        client = app.test_client()
        response = client.post("/login", data={"username": "editor", "password": "password123"})
        assert response.status_code == 400
        page = client.get("/login").data.decode()
        token = page.split('name="csrf_token" value="')[1].split('"')[0]
        response = client.post("/login", data={
            "username": "editor", "password": "password123", "csrf_token": token,
        })
        assert response.status_code == 302
    finally:
        app.config["WTF_CSRF_ENABLED"] = False
