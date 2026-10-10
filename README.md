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

- Sign-in through Authelia: PDC takes the identity from the headers Caddy passes on and has no
  passwords of its own. Everyone Authelia lets in can read; the user ids in `PDC_EDITORS` can
  change data (interim, until spic gives PDC its list of invoerders and beheerders)
- Interpreters and bureaus: add, edit, delete, drag-and-drop priority order (kept as 1..N)
- Meetings: add, edit, delete, search and filter by category
- No editing lock: a form that someone else saved in the meantime is caught when it is saved,
  and shows the current details
- SQLite database in WAL mode, with `manage.py backup`

Phase 2 (Google Forms import, time slots, availabilities, bookings) follows the model in the
functional analysis. See [docs/development-plan.md](docs/development-plan.md) for the phases.

**Phase 1 is a prototype, not yet PDC as decided.** In production PDC will run on the same
server and in the same environment as spic. The prototype still has meetings entered by hand;
the copy of the spic meetings, the own meetings and the assignment log come next (Phase 1b).
What differs from the decisions, and the design of the copy, are in
[docs/pdc-voorstel.md](docs/pdc-voorstel.md). Nothing has been built yet for the link with spic.

## Layout

```
app.py              routes and permissions
models.py           database tables
config.py           configuration (reads .env)
extensions.py       Flask extensions
auth.py             identity from Authelia, rights
manage.py           setup commands: tables, back-up, sample data
templates/          HTML pages (Bootstrap 5)
static/             stylesheet and images of the visual style
tools/              script that builds the style images
tests/              automated tests (pytest)
docs/               functional analysis, development plan, PDC proposals and visual style
```

## Requirements

- Python 3.12 (the version of spic; the dependency versions are pinned for it)
- Caddy and Authelia in front of PDC, as on the infracriv platform

## Installation and local trial

```bash
git clone https://github.com/bvelsac/matcher.git
cd matcher
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export APP_CONFIG=development        # SQLite file pdc_dev.db, fixed user "developer" (editor)
python manage.py init-db
python manage.py sample-data         # fictitious interpreters and meetings
python app.py                        # http://127.0.0.1:5000
```

In development PDC does not need Authelia: `PDC_AUTH_MODE=dev` (the default there) signs
everyone in as `PDC_DEV_USER`.

### Trial in GitHub Codespaces

On GitHub: **Code → Codespaces → Create codespace** on this branch. `.devcontainer/` installs PDC,
adds fictitious sample data and starts it in development mode; the browser opens on port 5000
(otherwise: the **Ports** tab, port 5000). Everyone is signed in as the editor "developer", so
keep the port private (the default) and never put real data in a codespace. It runs in a terminal of
its own; if it is not running, start it in a terminal with `sh .devcontainer/start.sh`.

## Configuration

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # paste as SECRET_KEY in .env
```

The application refuses to start in production without a `SECRET_KEY`. The database is
`/data/pdc.db` unless `DATABASE_URL` says otherwise. `PDC_EDITORS` lists the Authelia user
ids that may change data, separated by commas.

**PDC trusts the headers `Remote-User` and `Remote-Name`.** That is only safe when PDC is
reachable through Caddy and Authelia alone: never publish its port, and only put trusted
containers on the `infracriv` network (the same rule as for spic).

## Back-up

```bash
python manage.py backup /path/to/pdc-2026-10-10.db
```

This uses SQLite's own backup, which gives a consistent copy while PDC keeps running. It never
overwrites an existing file. A nightly back-up to a place outside the volume is still to be set
up on the server (the assignments cannot be recovered from spic).

## Test server on the infracriv platform (Docker)

`docker-compose.yml` runs PDC as one container, with its SQLite database on the volume
`matcher_data`. It joins the shared `infracriv` network, so Caddy can put it behind the
Authelia login like the other applications.

On the server:

```bash
git clone https://github.com/bvelsac/matcher.git
cd matcher
cp .env.example .env      # fill in SECRET_KEY and PDC_EDITORS
docker compose up -d --build
docker compose exec matcher python manage.py sample-data     # optional, fictitious data
docker compose exec matcher python manage.py backup /data/pdc-copy.db
```

The container creates missing tables when it starts. `docker compose logs -f matcher` shows
progress.

Route in `CAL/caddy/Caddyfile` of the infracriv repository, followed by a Caddy reload (only
when the user asks for it explicitly):

```
matcher.infracriv.net {
	import beveiligd
	reverse_proxy matcher:8000
}
```

The subdomain also needs a DNS record at Cloudflare, like the other subdomains.

To update: `git pull` and `docker compose up -d --build`. The data stays in the `matcher_data`
volume. The earlier test server with MySQL kept only fictitious data; its `matcher_db` volume
can be removed.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use an in-memory SQLite database and cover the sign-in through Authelia's headers,
rights, interpreters, the priority order, meetings, outdated forms and CSRF protection.

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
