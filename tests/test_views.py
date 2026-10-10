"""The screens, end to end with the test client, on the fictitious sample data."""
from datetime import date

import pytest

import sample_data
import spic_copy
from conftest import login, meeting_form, query
from extensions import db
from models import AssignmentLog, Booking, BookingPosition, Interpreter, Invoice, Meeting, MeetingAssignment


@pytest.fixture
def sample(app):
    with app.app_context():
        sample_data.load(today=date.today())
        db.session.commit()


@pytest.fixture
def editor(app, sample):
    client = app.test_client()
    login(client, "editor")
    return client


def meeting_id(app, spic_number):
    return query(app, lambda: Meeting.query.filter_by(spic_id="m-{:08x}".format(0xA0000000 + spic_number)).one().id)


def test_the_list_shows_spic_and_own_meetings_with_their_state(app, editor):
    page = editor.get("/meetings").data.decode()
    assert "from spic" in page and ">own<" in page
    assert "Reception for a delegation" in page
    assert "time?" in page                    # the meeting after another one has no time
    assert "pre-def." in page                 # next week is pre-definitive
    assert "1 / 2" in page                    # the first meeting has one confirmed interpreter of two
    assert "3 / " in page or "0 / 3" in page  # the plenary session needs three


def test_filters_of_the_meeting_list(app, editor):
    assert "Reception" not in editor.get("/meetings?origin=spic").data.decode()
    own = editor.get("/meetings?origin=own").data.decode()
    assert "Reception" in own and "from spic" not in own
    assert "plenaire" in editor.get("/meetings?q=plenaire").data.decode()
    assert "plenaire" not in editor.get("/meetings?q=Reception").data.decode()
    assert "No meetings here" in editor.get("/meetings?when=past").data.decode()
    assert "commissie 4" not in editor.get("/meetings?q=m-a0000001").data.decode()


def test_a_meeting_deleted_in_spic_is_hidden_unless_asked_for(app, editor):
    def delete():
        spic_copy.apply_item({"id": "m-a0000004", "status": "verwijderd"}, change_number=50)
        db.session.commit()
    query(app, delete)
    assert "commissie 4" not in editor.get("/meetings").data.decode()
    assert "commissie 4" in editor.get("/meetings?deleted=1").data.decode()
    # The commission has a confirmed interpreter, so it is on the work list.
    assert "commissie 4" in editor.get("/worklists").data.decode()


def test_the_detail_of_a_meeting_shows_assignments_history_and_log(app, editor):
    page = editor.get("/meetings/{}".format(meeting_id(app, 1))).data.decode()
    assert "Interpreter One" in page            # the person sent
    assert "Confirmed" in page
    assert "Assignment log" in page and "confirmed" in page and "Sample data" in page
    assert "History of this meeting" in page
    assert "Start time, room and cancellation: in spic for now." in page


def test_proposing_confirming_and_cancelling_through_the_screen(app, editor):
    mid = meeting_id(app, 2)  # the Bureau meeting on Wednesday, 12:15-14:00
    page = editor.get("/meetings/{}".format(mid)).data.decode()
    position_id = query(app, lambda: Booking.query.filter_by(status="proposed").one().positions[0].id)
    assert 'value="{}"'.format(position_id) in page  # the proposed Wednesday booking fits

    response = editor.post("/meetings/{}/assign".format(mid), data={"position_id": position_id})
    assert response.status_code == 302
    assignment_id = query(app, lambda: MeetingAssignment.query.filter_by(meeting_id=mid).one().id)

    # The booking is only proposed: confirming the assignment is refused, with the reason.
    response = editor.post("/assignments/{}/confirm".format(assignment_id), follow_redirects=True)
    assert b"Confirm the booking first" in response.data

    booking_id = query(app, lambda: Booking.query.filter_by(status="proposed").one().id)
    editor.post("/bookings/{}/confirm".format(booking_id))
    editor.post("/assignments/{}/confirm".format(assignment_id))
    assert query(app, lambda: db.session.get(MeetingAssignment, assignment_id).status) == "confirmed"

    editor.post("/assignments/{}/cancel".format(assignment_id), data={"reason": "illness", "communicated_on": "2030-01-02"})
    saved = query(app, lambda: db.session.get(MeetingAssignment, assignment_id))
    assert saved.status == "cancelled" and saved.cancellation_communicated_on == date(2030, 1, 2)
    actions = query(app, lambda: [e.action for e in AssignmentLog.query.filter_by(assignment_id=assignment_id).order_by(AssignmentLog.id)])
    assert actions == ["proposed", "confirmed", "cancelled"]
    assert "illness" in editor.get("/meetings/{}".format(mid)).data.decode()


def test_a_viewer_can_look_but_not_change(app, sample):
    viewer = app.test_client()
    login(viewer, "someone-else")
    mid = meeting_id(app, 2)
    page = viewer.get("/meetings/{}".format(mid)).data.decode()
    assert "Propose" not in page and "Edit</a>" not in page
    before = query(app, lambda: (MeetingAssignment.query.count(), AssignmentLog.query.count()))
    for url, data in [("/meetings/{}/assign".format(mid), {"position_id": 1}), ("/assignments/1/confirm", {}),
                      ("/bookings/1/cancel", {}), ("/positions/1/cancel", {}), ("/invoices/add", {}),
                      ("/meetings/{}/cancel".format(mid), {})]:
        assert viewer.post(url, data=data).status_code == 302, url
    assert query(app, lambda: (MeetingAssignment.query.count(), AssignmentLog.query.count())) == before
    for url in ["/bookings", "/bookings/1", "/invoices", "/worklists"]:
        assert viewer.get(url).status_code == 200, url


def test_a_meeting_from_spic_keeps_its_fields_in_spic(app, editor):
    mid = meeting_id(app, 2)
    page = editor.get("/meetings/{}/edit".format(mid)).data.decode()
    assert "comes from spic" in page and 'name="room"' not in page and 'name="interpreters_needed"' in page

    # Whatever else is posted, only what PDC keeps itself is saved.
    editor.post("/meetings/{}/edit".format(mid), data={"interpreters_needed": "4", "category": "", "notes": "VIP",
                                                       "room": "R9", "title": "Hacked"})
    saved = query(app, lambda: db.session.get(Meeting, mid))
    assert (saved.interpreters_needed, saved.notes, saved.room, saved.title) == (4, "VIP", "R1", None)

    response = editor.post("/meetings/{}/delete".format(mid), follow_redirects=True)
    assert b"cannot be deleted in PDC" in response.data
    assert query(app, lambda: db.session.get(Meeting, mid)) is not None
    response = editor.post("/meetings/{}/cancel".format(mid), follow_redirects=True)
    assert b"cancelled in spic" in response.data


def test_an_own_meeting_is_cancelled_or_deleted_depending_on_its_history(app, editor):
    editor.post("/meetings/add", data=meeting_form(title="Lunch talk"))
    mid = query(app, lambda: Meeting.query.filter_by(title="Lunch talk").one().id)
    page = editor.get("/meetings/{}".format(mid)).data.decode()
    assert "Delete</button>" in page
    editor.post("/meetings/{}/cancel".format(mid))
    assert query(app, lambda: db.session.get(Meeting, mid).status) == "cancelled"
    editor.post("/meetings/{}/reopen".format(mid))
    editor.post("/meetings/{}/delete".format(mid))
    assert query(app, lambda: db.session.get(Meeting, mid)) is None

    own_id = query(app, lambda: Meeting.query.filter_by(origin="own").one().id)
    position_id = query(app, lambda: Booking.query.filter_by(status="proposed").one().positions[0].id)
    # A reception needs a booking on its own day; make one and assign.
    own_date = query(app, lambda: db.session.get(Meeting, own_id).date)
    editor.post("/bookings/add", data={"interpreter_id": 3, "date": own_date.isoformat(), "start": "09:00",
                                       "end": "13:00", "positions": "1", "forfait_hours": "3"})
    position_id = query(app, lambda: BookingPosition.query.join(Booking).filter(Booking.interpreter_id == 3).one().id)
    editor.post("/meetings/{}/assign".format(own_id), data={"position_id": position_id})
    page = editor.get("/meetings/{}".format(own_id)).data.decode()
    assert "Delete</button>" not in page and "Can only be cancelled" in page
    response = editor.post("/meetings/{}/delete".format(own_id), follow_redirects=True)
    assert b"can only be cancelled" in response.data


def test_changes_since_the_last_visit_are_marked_for_others_only(app, editor):
    editor.get("/meetings")  # the first visit

    def spic_changes():
        spic_copy.apply_item(sample_data.spic_items(sample_data.monday_after(date.today()))[3] | {"zaal": "R1"},
                             change_number=60, changed_by="Kathy")
        db.session.commit()
    query(app, spic_changes)
    assert "changed</span>" in editor.get("/meetings").data.decode()
    assert "changed</span>" not in editor.get("/meetings").data.decode()  # seen now

    editor.post("/meetings/{}/edit".format(meeting_id(app, 2)), data={"interpreters_needed": "3"})
    other = app.test_client()
    login(other, "editor2")
    other.get("/meetings")
    editor.post("/meetings/{}/edit".format(meeting_id(app, 2)), data={"interpreters_needed": "2"})
    assert "changed</span>" in other.get("/meetings").data.decode()
    assert "changed</span>" not in editor.get("/meetings").data.decode()  # your own change is not news to you


def test_booking_screens(app, editor):
    response = editor.post("/bookings/add", data={
        "interpreter_id": 2, "date": "2030-03-04", "start": "09:00", "end": "13:00", "positions": "2", "forfait_hours": "3"},
        follow_redirects=True)
    page = response.data.decode()
    assert "Booking proposed" in page and "Interpreter 2 of 2" in page and "forfait" in page.lower()
    booking_id = query(app, lambda: Booking.query.order_by(Booking.id.desc()).first().id)

    assert b"exactly one position" in editor.post("/bookings/add", data={
        "interpreter_id": 3, "date": "2030-03-04", "start": "09:00", "end": "13:00", "positions": "2",
        "forfait_hours": "4"}).data
    assert b"must end after" in editor.post("/bookings/add", data={
        "interpreter_id": 3, "date": "2030-03-04", "start": "13:00", "end": "09:00", "positions": "1",
        "forfait_hours": "4"}).data

    editor.post("/bookings/{}/confirm".format(booking_id))
    response = editor.post("/bookings/{}/complete".format(booking_id), follow_redirects=True)
    assert b"name of the person sent" in response.data
    position_ids = query(app, lambda: [p.id for p in db.session.get(Booking, booking_id).positions])
    for n, pid in enumerate(position_ids):
        editor.post("/positions/{}/name".format(pid), data={"interpreter_name": "Person {}".format(n)})
    editor.post("/positions/{}/hours".format(position_ids[0]), data={
        "actual_start_time": "2030-03-04T09:00", "actual_end_time": "2030-03-04T12:20"})
    page = editor.get("/bookings/{}".format(booking_id)).data.decode()
    assert "3.5 h paid" in page and "1 half hour over" in page  # a started half hour counts
    editor.post("/bookings/{}/complete".format(booking_id))
    assert query(app, lambda: db.session.get(Booking, booking_id).status) == "completed"
    assert "Completed" in editor.get("/bookings?when=all").data.decode()


def test_invoice_screens_and_the_work_lists(app, editor):
    editor.post("/bookings/add", data={"interpreter_id": 1, "date": "2030-03-04", "start": "09:00", "end": "13:00",
                                       "positions": "2", "forfait_hours": "4"})
    booking_id = query(app, lambda: Booking.query.order_by(Booking.id.desc()).first().id)
    editor.post("/bookings/{}/confirm".format(booking_id))
    for pid in query(app, lambda: [p.id for p in db.session.get(Booking, booking_id).positions]):
        editor.post("/positions/{}/name".format(pid), data={"interpreter_name": "Person {}".format(pid)})
    editor.post("/bookings/{}/complete".format(booking_id))
    worklist = editor.get("/worklists").data.decode()
    assert "Invoice not received yet" in worklist and "2030-03-04" in worklist

    response = editor.post("/invoices/add", data={"interpreter_id": 1, "reference": "2030-017", "received_on": "2030-04-02",
                                                  "period": "March 2030"}, follow_redirects=True)
    assert b"Invoice recorded" in response.data
    invoice_id = query(app, lambda: Invoice.query.one().id)
    page = editor.get("/invoices/{}".format(invoice_id)).data.decode()
    assert page.count('name="position_id"') == 3  # the two new ones and the confirmed one of the sample data

    assert b"Tick the services" in editor.post("/invoices/{}/link".format(invoice_id), follow_redirects=True).data
    editor.post("/invoices/{}/link".format(invoice_id), data={"position_id": query(
        app, lambda: [p.id for p in db.session.get(Booking, booking_id).positions])})
    assert query(app, lambda: len(db.session.get(Invoice, invoice_id).positions)) == 2
    assert "2030-03-04" not in editor.get("/worklists").data.decode().split("Invoice not received yet")[1].split("Dimona to declare")[0]
    editor.post("/invoices/{}/checked".format(invoice_id))
    assert query(app, lambda: Invoice.query.one().checked_on) is not None
    assert "2030-017" in editor.get("/invoices").data.decode()
    assert "not yet" not in editor.get("/invoices").data.decode()

    # An interpreter in occasional work sends no invoice.
    response = editor.post("/invoices/add", data={"interpreter_id": 5, "received_on": "2030-04-02"})
    assert b"no invoice, a Dimona declaration instead" in response.data


def test_dimona_through_the_work_list(app, editor):
    editor.post("/bookings/add", data={"interpreter_id": 5, "date": "2030-03-05", "start": "09:00", "end": "13:00",
                                       "positions": "1", "forfait_hours": "4"})
    booking_id = query(app, lambda: Booking.query.order_by(Booking.id.desc()).first().id)
    editor.post("/bookings/{}/confirm".format(booking_id))
    pid = query(app, lambda: db.session.get(Booking, booking_id).positions[0].id)
    editor.post("/positions/{}/name".format(pid), data={"interpreter_name": "Sarah"})
    editor.post("/bookings/{}/complete".format(booking_id))
    assert "Dimona to declare" in editor.get("/worklists").data.decode()
    assert query(app, lambda: __import__("planning").worklist_counts()["dimona"]) == 1

    response = editor.post("/positions/{}/dimona?next=/worklists".format(pid))
    assert response.headers["Location"].endswith("/worklists")
    assert query(app, lambda: __import__("planning").worklist_counts()["dimona"]) == 0
    # A redirect target outside this site is ignored.
    response = editor.post("/positions/{}/undimona?next=//evil.example/".format(pid))
    assert "evil" not in response.headers["Location"]


def test_the_interpreter_form_has_the_engagement(app, editor):
    editor.post("/interpreters/add", data={"first_name": "Z", "last_name": "Z", "email": "z@example.org",
                                           "engagement": "occasional_work"})
    assert query(app, lambda: Interpreter.query.filter_by(email="z@example.org").one().engagement) == "occasional_work"
    assert b"Choose how the interpreter works" in editor.post("/interpreters/add", data={
        "first_name": "Y", "last_name": "Y", "email": "y@example.org", "engagement": "weird"}).data
    assert b"DIM" in editor.get("/interpreters").data


def test_an_interpreter_with_bookings_is_not_deleted(app, editor):
    response = editor.post("/interpreters/1/delete", follow_redirects=True)
    assert b"has bookings or invoices" in response.data
    assert query(app, lambda: Interpreter.query.count()) == 5


def test_the_dashboard_counts_the_work(app, editor):
    page = editor.get("/").data.decode()
    assert "Work lists" in page and "still need interpreters" in page


def test_the_state_of_the_copy_is_shown_at_the_bottom(app, editor):
    page = editor.get("/").data.decode()
    assert "Copy of spic updated to change 7" in page  # the sample data advanced the number to 7
