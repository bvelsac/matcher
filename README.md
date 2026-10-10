# PDC (matcher)

**PDC** (Prestatiedatabank voor Conferentietolken) is the new name of this application,
until now called `matcher`, "tolkenplanning" or "tolkenplanner". The person who plans the
interpreters is still the planner (tolkenplanner).

Match requests and availabilities.
Requests concern specific tasks linked to a timeframe and are defined by an organization.
Availabilities are communicated by freelancers and other collaborators.
The application provides various functionalities to match both and to keep proper records of the process.

The first use is planning freelance interpreters for the Parliament's meetings: the
interpreter list with its legal priority order, the meetings that need interpreters, and
(in later phases) availabilities from Google Forms, bookings, confirmations and reports.

The business model is described in [docs/functional-analysis.md](docs/functional-analysis.md).
Version 1.2 of that analysis adds what was decided for PDC: the meetings come from **spic**,
the meeting planning in the repository `bvelsac/crystalclear`. PDC keeps its own copy of them,
next to its own meetings, and an append-only log of the assignments.

## Status

**Phase 1** is implemented:

- Login with two roles: *editor* (changes data) and *viewer* (read only)
- Interpreters and bureaus: add, edit, delete, drag-and-drop priority order (kept as 1..N)
- Meetings: add, edit, delete, search and filter by category
- Editing lock: an editor can lock the system while dispatching; other editors can then
  only view. A forgotten lock expires after 4 hours (configurable).

Phase 2 (Google Forms import, time slots, availabilities, bookings) follows the model in the
functional analysis. See [docs/development-plan.md](docs/development-plan.md) for the phases.

**Phase 1 is a prototype and test server, not yet PDC as decided.** In production PDC will run
on the same server and in the same environment as spic. The prototype still has meetings
entered by hand, MySQL, its own accounts and a system-wide editing lock. What differs from the
decisions, and the design of the copy of the spic meetings, are in
[docs/pdc-voorstel.md](docs/pdc-voorstel.md). Decided on 10 October 2026: SQLite instead of
MySQL, no editing lock, login through Authelia with the rights taken from spic. Nothing has been
built yet for the link with spic.

## Layout

```
app.py              routes and permissions
models.py           database tables
config.py           configuration (reads .env)
extensions.py       Flask extensions
manage.py           setup commands: tables, users, sample data
templates/          HTML pages (Bootstrap 5)
static/             stylesheet and images of the visual style
tools/              script that builds the style images
tests/              automated tests (pytest)
docs/               functional analysis, development plan, PDC proposals and visual style
```

## Requirements

- Python 3.8 (the dependency versions are pinned for it; newer Python versions work too)
- MySQL 8.0
- A web server to act as reverse proxy in front of gunicorn (Apache, nginx, Caddy...)

## Installation

```bash
git clone https://github.com/bvelsac/matcher.git
cd matcher
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database

```sql
CREATE DATABASE interpreter_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'interpreter_user'@'localhost' IDENTIFIED BY 'choose-a-password';
GRANT ALL PRIVILEGES ON interpreter_system.* TO 'interpreter_user'@'localhost';
FLUSH PRIVILEGES;
```

### Configuration

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # paste as SECRET_KEY in .env
```

Fill in `MYSQL_PASSWORD` and the other values in `.env`. The application refuses to start
in production without a `SECRET_KEY`.

### Tables and users

```bash
python manage.py init-db
python manage.py create-user --username secretariaat --email ... --role editor
python manage.py create-user --username teamlead --email ... --role editor
python manage.py create-user --username director --email ... --role viewer
```

Each command asks for the password. To change one later: `python manage.py set-password --username ...`.
There is no default account.

## Running

Production, behind your web server:

```bash
gunicorn -w 3 -b 127.0.0.1:8000 app:app
```

Point the reverse proxy at `127.0.0.1:8000` and serve the site over HTTPS. To keep gunicorn
running, use a systemd service (or the process manager already used on the server).

Local trial without MySQL:

```bash
export APP_CONFIG=development        # SQLite file interpreter_system_dev.db
python manage.py init-db
python manage.py create-user
python manage.py sample-data         # fictitious interpreters and meetings
python app.py                        # http://127.0.0.1:5000
```

## Test server on the infracriv platform (Docker)

`docker-compose.yml` runs the application with its own MySQL 8.0.40 container, on the same
Python 3.8 as production. The application joins the shared `infracriv` network, so Caddy
can put it behind the Authelia login like the other applications.

On the server:

```bash
git clone https://github.com/bvelsac/matcher.git
cd matcher
cp .env.example .env      # fill in SECRET_KEY, MYSQL_PASSWORD and MYSQL_ROOT_PASSWORD
docker compose up -d --build
docker compose exec matcher python manage.py create-user
docker compose exec matcher python manage.py sample-data     # optional, fictitious data
```

The first start takes a minute: MySQL initialises its data directory, then the application
creates its tables. `docker compose logs -f matcher` shows progress.

Route in `CAL/caddy/Caddyfile` of the infracriv repository, followed by a Caddy reload:

```
matcher.infracriv.net {
	import beveiligd
	reverse_proxy matcher:8000
}
```

The subdomain also needs a DNS record at Cloudflare, like the other subdomains.

Users first pass the Authelia login and then log in to matcher with the account made by
`create-user`.

To update: `git pull` and `docker compose up -d --build`. The data stays in the `matcher_db` volume.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use an in-memory SQLite database and cover login, roles, interpreters, the priority
order, meetings, the editing lock and CSRF protection.

`tests/test_browser.py` checks the visual style in a real browser (Playwright and Chromium):
Arial, the pixelated eye in the background, and enough contrast on buttons and badges. Install
the browser once with `playwright install chromium`; without Playwright these tests are
skipped. Where the CDN for Bootstrap cannot be reached, set `PDC_CDN_DIR` to a folder with the
unpacked npm packages (see the docstring of that file); `PDC_CHROMIUM` can point at an existing
Chromium binary.

## Visual style

The look is described in [docs/visual-style.md](docs/visual-style.md) and lives in
`static/css/pdc.css`, on top of Bootstrap 5.3 in dark mode. The images in `static/img` are built
from the reference images by `tools/style_assets.py` (needs Pillow, which the application itself
does not use).

## Updating the server

```bash
cd matcher
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py init-db     # creates new tables only; existing data is left alone
```

Then restart gunicorn. `.env` and local databases are excluded by `.gitignore`, so
passwords and data never end up in the repository.

## Notes

- Python 3.8 no longer receives security updates from the Python project (end of life
  October 2024). Plan a move to a supported version when the server allows it; the code needs
  no changes for that, only newer versions in `requirements.txt`.
- Times shown for the editing lock are in UTC.
