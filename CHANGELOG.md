# Changelog

## 0.3.0 - PDC, step 3 (not tagged)

- **The model of the functional analysis 1.2**: one table of meetings for the copy of spic and the
  own meetings (origin, spic ID, status, week status, time of day, start time or "after another
  meeting", times that may be missing, room, real end, half hours charged, the complete state from
  spic as JSON); history of every change of the copy and of the own meetings.
- **Bookings, positions and assignments** with forfait of 3 or 4 hours, the person sent, hours
  worked and overtime per half hour; **invoices** linked to the services they cover; **Dimona**
  for interpreters in occasional work.
- **Append-only assignment log** with a snapshot of the meeting at every step; SQLite triggers
  refuse any change or deletion of the log and of the history.
- **Work lists**: cancelled with an assigned interpreter, changed since the confirmation, invoice
  not received yet, Dimona to declare.
- **`spic_copy.py`** applies what spic reports to the copy; **test data shaped like spic's export**
  (the export itself does not exist yet; its shape is an assumption, see the module).
- **Migrations** (Alembic), `manage.py make-migration`; `init-db` now creates or updates.
- **Parallel planners**: every handling starts with SQLite's write lock (`BEGIN IMMEDIATE`) and reads the state
  afresh, so two planners who assign the same interpreter at the same moment cannot both succeed; the second
  gets the message of the broken rule.
- Screens: meeting list with origin, status and staffing, meeting page with assignments, history
  and log, bookings, invoices, work lists; new backgrounds and accents for them.
- The prototype's meeting form (name, duration in hours, location, category) is gone: a database
  of the Phase 1 prototype cannot be updated (there was no data worth keeping).

## 0.2.0 - PDC, step 2 (not tagged)

- **Name and look**: the screens are called PDC and follow `docs/visual-style.md` (Arial, a
  pixelated background and an accent colour per screen, the bar at the bottom).
- **SQLite** instead of MySQL, in WAL mode, one container with the database on a volume;
  `manage.py backup` makes a consistent copy. The MySQL test data were fictitious.
- **Authelia**: identity from the headers Caddy passes on; no passwords, no login page, no
  `create-user`. Who may change data: `PDC_EDITORS`, until spic provides its list.
- **No editing lock**: an edit form saved after someone else changed the record is refused,
  with the current details shown.
- Browser tests (Playwright) for the style and the bottom bar.
- **Python 3.12** (like spic) instead of 3.8, which no longer gets security updates; current
  versions of Flask, SQLAlchemy and the other packages.

## 0.1.0 - Phase 1

First version in a repository. Compared with the code shown in the chat, these problems
were fixed so that it runs and does what the documentation says:

- **Did not start**: `models.py` and `app.py` imported each other; the database object is now
  created once in `extensions.py`.
- **Pages crashed**: the base template defined its content block twice, and the dashboard and
  meeting pages called a `moment()` function that does not exist in the templates.
- **Python 3.8**: removed pandas (unused, and pandas 2.x needs Python 3.9+). Dependencies are
  pinned to versions that support Python 3.8, including the security fixes in Werkzeug 3.0.6.
  Added `cryptography` (via `PyMySQL[rsa]`), which MySQL 8's default login method requires.
- **CSRF protection** was described but not present; it is now active on all forms and
  JavaScript requests.
- **Editing lock**: after a page reload the button no longer showed the real state, so a lock
  could not be released; other editors were not actually blocked. Both fixed, and an
  unreleased lock now expires (4 hours by default).
- **Accounts**: no more built-in `admin/admin123` account shown on the login page.
  `manage.py create-user` creates accounts with a prompted password; `set-password` changes it.
  `setup.py` was renamed to `manage.py` (a `setup.py` file is reserved for Python packaging).
- **Names with an apostrophe** (e.g. D'Hoore) broke the delete buttons.
- **Priority order** stays 1..N after deleting an interpreter, and a partial reorder request
  is refused instead of leaving duplicate numbers.
- **Email addresses** are stored in lower case, since matching with Google Forms is by email.
- **Data model**: the draft tables for CSV sources, availability responses and assignments were
  removed. Phase 2 implements the model in `docs/functional-analysis.md` instead (time slots,
  availability declarations, bookings, booking positions, meeting assignments).
- **Sample data** uses fictitious names and addresses instead of real interpreters' details.
- **Meeting shortcuts** on the "Add meeting" page are now the two recurring parliamentary
  meetings (Uitgebreid Bureau at 12:00, Bureau at 12:15).

Functional analysis (`docs/functional-analysis.md`), version 1.1:

- The remaining references to a single `linked_meeting_id` per booking were updated to the
  meeting-assignment model.
- A booking is now a bucket of **booking positions**, one per interpreter. Positions, not whole
  bookings, are assigned to meetings, so the interpreters of one bureau booking can each go to
  a different meeting. The name of the person a bureau sends, replacements and actual hours are
  kept per position. A meeting's staffing is the number of its confirmed assignments.
