# Interpreter Management System - Development Plan

> **Note:** this plan was written before the functional analysis. Where they differ,
> [functional-analysis.md](functional-analysis.md) is authoritative - in particular the data
> model, which replaces the single `assignments` table below with time slots, availability
> declarations, bookings and meeting assignments. pandas is not used; the standard `csv`
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

### Phase 2: CSV Import & Availability
**Goal**: Import availability data and basic matching

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
- System locking during assignment work
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
- Optional: forfait (3h/4h) and normal/late overtime calculation

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
- Production on the existing Python 3.8 / MySQL 8.0.40 server
- Gunicorn behind the existing web server as reverse proxy
- Environment-specific configuration via `.env`
- Git version control
