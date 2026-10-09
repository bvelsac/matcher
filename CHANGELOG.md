# Changelog

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
