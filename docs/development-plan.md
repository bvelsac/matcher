# PDC - Development Plan

> **PDC (10 October 2026):** the application is now called PDC (Prestatiedatabank voor
> Conferentietolken). The meetings come from spic (functional analysis 1.2, section 1), so
> Phase 1b below was added. What the Phase 1 prototype does differently from the decisions,
> and the proposals for the database, the lock and the login, are in
> [pdc-voorstel.md](pdc-voorstel.md).

> **Note:** this plan was written before the functional analysis. Where they differ,
> [functional-analysis.md](functional-analysis.md) is authoritative - in particular the data
> model, which replaces the single `assignments` table below with time slots, availability
> declarations, bookings, booking positions and meeting assignments. pandas is not used; the standard `csv`
> module is enough for the Google Forms exports and keeps Python 3.8 support.

## System Architecture

### Backend Stack
- **Framework**: Flask (Python 3.8) with SQLAlchemy ORM
- **Database**: MySQL 8.0.40
- **Authentication**: Flask-Login for session management
- **CSV Processing**: Python `csv` module
- **HTTP Requests**: requests library for CSV fetching

### Frontend Stack
- **Framework**: HTML5 + Bootstrap 5 for responsive UI
- **Visual style**: grainy, high-contrast pink-and-black duotone; see [visual-style.md](visual-style.md)
- **JavaScript**: Vanilla JS for interactivity
- **AJAX**: For dynamic updates without page reloads

### Database Schema (Core Tables, original draft)

```sql
-- Interpreters management
interpreters (id, first_name, last_name, email, phone, bureau_affiliation, priority_order, additional_languages, notes, created_at)

-- Meeting/mission definitions
meetings (id, name, date, time, estimated_duration, interpreters_needed, location, category, created_by, created_at, updated_at)

-- CSV data source configuration
csv_sources (id, name, url, is_active, created_at)

-- Availability data (imported from CSV)
availability_responses (id, email, meeting_id, interpreters_available, response_timestamp, csv_source_id)

-- Assignment tracking
assignments (id, meeting_id, interpreter_id, assigned_interpreter_name, status, estimated_hours, actual_start_time, actual_end_time, notes, created_at, updated_at)

-- User management
users (id, username, email, role, password_hash, created_at)

-- System locking
system_locks (id, locked_by_user_id, lock_type, created_at)
```

## Development Phases

### Phase 1: Core Foundation
**Goal**: Basic working system for meeting management and interpreter database

**Features:**
- User authentication (login/logout)
- Interpreter management (CRUD)
  - Add/edit/delete interpreters
  - Priority order management
  - Bureau affiliation tracking
- Meeting management (CRUD)
  - Create/edit meetings with all basic fields
  - Category selection (parliament/affiliated/external/special)
- Basic responsive web interface

**Deliverable**: Admin can manage interpreters and meetings

Phase 1 is the prototype and test server. Its meetings are entered by hand; in PDC they come
from spic (Phase 1b).

### Phase 1b: Meetings from spic (PDC)
**Goal**: PDC's own copy of the spic meetings, own meetings and the assignment log, as decided in
the functional analysis 1.2. Comes before Phase 2, or alongside it.

**Steps** (proposed order, see [pdc-voorstel.md](pdc-voorstel.md) §8):
1. Decisions on the database, the editing lock, the login and the language of the code (taken
   10 October 2026: SQLite, no lock, Authelia with rights from spic, code in English)
2. Database switch to SQLite, with migrations and a nightly back-up; remove the editing lock;
   login through Authelia (rights from spic once spic provides the list)
3. New meeting model: copy of spic meetings and own meetings in one table, history of the copy,
   append-only assignment log, the two work lists; test data shaped like spic's export.
   No link with spic yet
4. The workbench for the planner
5. The link: `GET /api/export?sinds=N` on spic's side (built in `crystalclear`), the update in
   PDC when a screen opens and by a background task, the nightly full comparison
6. Last: spic's write route for start time, room and cancellation

**Deliverable**: The planner sees the spic meetings and own meetings in one list, and every
assignment is logged with a snapshot of the meeting

### Phase 2: CSV Import & Availability
**Goal**: Import availability data and basic matching

Only availabilities come from Google Forms (CSV); meetings come from spic (Phase 1b). A later
idea, not decided, is PDC's own response form instead of the CSV import (functional analysis,
open point 14).

**Features:**
- CSV source configuration
  - Add/edit HTTP URLs with friendly names
  - Test CSV fetch functionality
- CSV import mechanism
  - Fetch data from configured URLs
  - Parse availability responses
  - Handle interpreter identification by email
- Availability data management
  - View imported availability
  - Select which sources to include
- Basic matching algorithm
  - Priority-based assignment suggestions
  - Bureaus and individuals in one priority list

**Deliverable**: System can import availability and suggest bookings

### Phase 3: Assignment Management
**Goal**: Human review and assignment editing

**Features:**
- Proposal interface
  - Display suggested matches
  - Show priority order reasoning
- Editing
  - Change interpreter assignments
  - Assign interpreters not in availability data
  - Handle conflicts and warnings
- System locking during assignment work (Phase 1 has it; the decisions on PDC conflict with it,
  proposal: drop it, see [pdc-voorstel.md](pdc-voorstel.md) §4)
- Status tracking (proposed → confirmed → completed)

**Deliverable**: Complete assignment workflow

### Phase 4: Reporting & Communications
**Goal**: Generate confirmations and reports

**Features:**
- Confirmation text generation
  - Per interpreter for defined period
  - Customizable date ranges (default: weekly from Monday)
- Weekly overview for HR
- Monthly overview per interpreter
- Invoices and Dimona: an invoice (reference, date received, period) recorded once and linked
  to all positions it covers; Dimona declared per position; work lists "invoice not received
  yet" and "Dimona to declare" (functional analysis 2.5, 2.9)

**Deliverable**: Complete scheduling and reporting system

### Phase 5: Time Tracking Portal
**Goal**: Interpreter self-service time logging

**Features:**
- Simple interpreter portal
  - Login
  - View assigned meetings
  - Enter start/end times
- Time validation and approval
  - Team lead approval interface
  - Actual vs estimated duration tracking
- Forfait (3h or 4h, for everyone) plus overtime counted per half hour (functional analysis
  2.4, BR-BKG-009); whether late hours have another rate is still open

**Deliverable**: Complete system with time tracking

### Phase 6: Enhancements (Ongoing)
- Replacement suggestions when interpreters become unavailable
- Advanced reporting
- Performance optimizations

## Matching Algorithm (sketch)

```python
def suggest(slot, needed):
    """Walk the single priority list (bureaus and individuals alike),
    taking as many interpreters as each can offer until the need is covered."""
    proposals = []
    for availability in available_for(slot, order_by="priority_order"):
        if needed <= 0:
            break
        take = min(availability.quantity_available, needed)
        proposals.append((availability.interpreter, take))
        needed -= take
    return proposals, needed  # needed > 0 means insufficient availability
```

## Deployment Strategy

- Local development with the Flask development server and SQLite
- Test server (Phase 1): Docker on the infracriv platform, with its own MySQL 8.0.40 container
  (`docker-compose.yml`)
- Production (PDC): on the same server and in the same environment as spic. Proposals, not yet
  decided: its own compose project on the `infracriv` network with its own version and tag,
  deployed through GitHub Actions; a token for spic's export and write route; SQLite in a volume
  with a nightly back-up; Python 3.12 like spic
- Gunicorn behind Caddy and Authelia; the route lives in `CAL` (repository `infracriv`) and is
  changed only when the user explicitly asks
- Environment-specific configuration via `.env`
- Git version control
