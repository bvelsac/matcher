# Functional Analysis
## PDC - Prestatiedatabank voor Conferentietolken

**Version:** 1.2  
**Date:** 10 October 2026  
**Document Type:** Conceptual Model & Business Rules

> **1.2:** the application is now called **PDC** (Prestatiedatabank voor Conferentietolken).
> It was called "Interpreter Mission Management System", "tolkenplanning" or `matcher`; the
> person who plans the interpreters is still the **planner** (tolkenplanner). This version adds
> what was decided for PDC in the sessions on spic: the meetings come from **spic** (new
> sections 1.1 to 1.6), the meeting model (2.7), cancellations that never remove an assignment
> (5.4, 6.2, 6.3), and the editing lock and the roles (9). The decisions are recorded in
> `docs/stand-van-zaken.md` of the repository `bvelsac/crystalclear`; the spic side of the
> contract is in FA Opnamebeheer §13.2 of that repository (`docs/FA_opnamebeheer_v1.2.md`, where
> spic is still called Banaan). This document describes PDC; the contract with spic is
> described there. Decisions of the user on 10 October 2026, after the proposals in
> `docs/pdc-voorstel.md`: SQLite as database, no editing lock, login through Authelia with the
> rights taken from spic, code in English (9, points 3 and 11). Also added, after the planner's
> spreadsheet for 2026-2027: invoices (new 2.9), invoice or occasional work (Dimona) per interpreter, the forfait of a
> booking, when a cancellation was passed on to the interpreter, and a default number of
> interpreters per meeting (9, point 17); and the instructions for booking of September 2026
> (4.5).
>
> **1.1:** a booking is now a bucket of positions, one per interpreter, so that the
> interpreters of one bureau booking can each be dispatched to meetings independently
> (new section 2.5, scenario 6.4). Actual hours and the name of the person sent are kept
> per position.

**Terms used in this document**

| Term | Meaning |
|------|---------|
| PDC | This application: the planner's tool for interpreters |
| spic | The planning of the meetings of the Verslaggeving directorate (repository `bvelsac/crystalclear`). The only source of the Parliament's meetings |
| planner | The person who plans the interpreters (tolkenplanner) |
| spic meeting | A meeting that comes from spic; PDC keeps a copy |
| own meeting | A meeting that is not in spic and is entered in PDC |
| week status | Status of a week in spic: concept, pre-definitive (pre-definitief) or definitive (definitief) |

---

## 1. Domain Overview

PDC manages the reservation and allocation of interpreters across time periods, matching their declared availability with meetings that require interpretation services. The fundamental principle is that **availabilities are declared for time slots**, **bookings reserve interpreter capacity**, and **meetings consume booked capacity** - but these concepts remain distinct to handle the reality that meetings may be cancelled, rescheduled, or added after availabilities are collected.

A booking is the commitment towards the supplier (an individual interpreter or a bureau). Inside a booking, every interpreter is a separate **booking position**, and it is positions - not whole bookings - that are dispatched to meetings. A bureau booked for three interpreters is a bucket of three positions; each of the three can go to a different meeting.

PDC is the planner's tool, used for about 95 % of their working time: finding interpreters, assigning them to meetings, moving them. The main screen is therefore a **workbench**, not a form. **All** meetings need interpreters, also those for which no report or transcript is made. Assignments are documented carefully (1.6).

Later a similar application will follow for another category of freelancers, also depending on the data of spic. It follows the same pattern as PDC; it is not an extension of spic.

### 1.1 Where meetings come from

- **spic is the only source of the Parliament's meetings.** Meetings are no longer entered by hand or imported from a CSV file. PDC keeps its **own copy** of every spic meeting it has received (1.3) and never writes in spic's database.
- **Only weeks that are pre-definitive or definitive** are passed on. A week in concept stays in spic and is invisible to PDC. Pre-definitive: the week is filled in; responsible officials and coordinators may still be missing. Definitive: officials and a coordinator per day are filled in, and changes are marked. The status of a week can change in any order, also back to concept.
- **Own meetings:** some meetings have no report and are therefore not in spic, but they do need interpreters. The secretary enters them in PDC (1.5).
- Spic meetings and own meetings appear **in one list**, labelled "from spic" or "own".
- The staffing status of PDC is not passed back to spic.

### 1.2 Two applications, two databases

- PDC and spic are **separate applications, each with its own database.** Reasons: own back-up and restore (restoring spic must not roll back assignments), own retention period and access rules for the personal data of freelancers, PDC keeps working while spic is briefly unavailable, and the later application for other freelancers follows the same pattern instead of making spic bigger.
- In production PDC runs **on the same server and in the same environment as spic** (Docker on the infracriv platform). Proposals that follow from this, not yet decided:
  - PDC is its own compose project on the shared Docker network `infracriv`, with its own volumes, version and tag, so that deploying PDC does not restart spic and vice versa.
  - PDC calls spic **inside that network** (`http://spic:8000/...`), not through Caddy and Authelia, with **its own token** (from `.env`, never in a repository). spic trusts the Authelia headers only when they come through Caddy, so only trusted containers may join that network.
  - People reach PDC like spic: a route in the Caddyfile and a rule in Authelia, in `CAL` (repository `infracriv`). That is changed only when the user explicitly asks for it.
  - PDC needs a **nightly back-up** of its own: assignments cannot be recovered from spic.
- PDC uses **SQLite**, like spic (decided 10 October 2026; 9, point 11).
- PDC **depends explicitly** on Authelia for the identity of its users and on spic for their rights (9, point 3).

### 1.3 Keeping the copy up to date

- **One running change number.** Every change in spic, including a change of week status, gets the next number in one sequence for the whole spic database. PDC only remembers the last number it processed and asks for "everything since change N".
- **Follow the number, not the version.** A meeting's version in spic does not increase for derived changes (recalculations), and the planning version exists only for definitive weeks. The change numbers always increase.
- **Week status changes are items too.** When a week becomes pre-definitive, PDC fetches the **whole week** (earlier changes during the concept period were invisible). When a week goes back to concept, its meetings disappear from PDC's visible list (BR-MTG-009).
- **Recognition by ID.** A spic meeting has a stable ID (`m-xxxxxxxx`). PDC recognises meetings by that ID, never by date and time. A meeting can move to another week (same ID, other week).
- **Deletion and restore.** Deleting a meeting in spic really removes the row there, and the deletion is reported explicitly. PDC keeps its copy with status DELETED (2.7). Restoring in spic brings back the **same ID**, so a deletion followed by the same ID is normal: the copy becomes active again.
- **When the copy is updated** (decided): when someone uses PDC (opening a screen first updates the copy) **and** by a background task on the server, also when no screen is open. Working without a background task is not an option. Proposal for the details: one request "since N" every 5 minutes; a lock so that two updates at the same time do not process anything twice; at the bottom of the screen "copy updated to change N at hh:mm", with a warning when that is too old; spic being unreachable is not an error, the task simply tries again; every night a **full comparison** with the complete list from spic that repairs any differences.
- **spic restored from a back-up:** if spic's highest change number is lower than PDC's last number, PDC performs a full synchronisation.
- **No polling and no live notifications** in the screen: an open view is refreshed when it is reloaded. "Changed since your last visit" is calculated when the screen is opened.
- Times from spic are Brussels time.

### 1.4 Changing a spic meeting from PDC

- The planner changes the basic data of a spic meeting only now and then, and only **start time, room and cancellation**: a small action, written immediately, **without any lock**. A spic meeting **cannot be deleted** in PDC, only cancelled; deleting is done in spic.
- The change goes through a very limited **write route in spic** (not built yet): start time, room or cancellation, with the name of the person. The route **never refuses a change because of a version difference**: it sets the value, also when the meeting was changed in the meantime, and only tells PDC that the value had changed ("the start time had meanwhile been set to 15:00 by Kathy"). It refuses only when the meeting no longer exists or the value is invalid.
- A planner who saves from an outdated form gets a **conflict window** in PDC (then, now, your input).
- In spic such a change appears in the history under the planner's name with "via PDC", marked like any other change. Someone who has the same meeting open in spic sees the change within 30 seconds in a yellow bar ("Start time: 14:00 → 14:30, by Anna").
- Proposal: after a successful write, PDC immediately updates its copy ("since N"), so that the change is visible with its change number.

### 1.5 Own meetings

- Entered by the secretary in PDC, in PDC's own database, next to the copies of the spic meetings.
- Fields: title, date, start, end or duration, room (from spic's fixed list of rooms), category, number of interpreters, notes. No sequence number, officials, agenda items or turn rota.
- **All services are at the Parliament's expense**, own meetings included. The Parliament does not organise interpreting for third-party payers; that is not allowed (the user, 10 October 2026). PDC therefore has no field for who pays.
- **No recurrence and no series:** each own meeting is entered on its own (a weekly series does not match reality).
- An own meeting is fully editable in PDC. It can be **deleted only as long as no interpreter was ever assigned** to it; after that it can only be cancelled.
- Open: linking an own meeting to a spic meeting if the same meeting later turns up in spic.

### 1.6 The assignment log

- PDC keeps its **own, append-only log** of assignments, with a lot of logging: every creation, confirmation, change and cancellation of an assignment is a new entry, with who, when, and a **snapshot of the meeting** at that moment. Entries are never changed or deleted.
- **A cancellation never removes an assignment.** When a meeting is cancelled (in spic or via PDC) or deleted in spic, its assignments stay as they are until the planner decides (5.4).
- Two work lists for the planner follow from this (they replace the formula columns TE BEHANDELEN and TE CONTROLEREN of the former Google Sheet):
  - **Cancelled with an assigned interpreter:** cancelled or deleted meetings that still have assignments that are not cancelled.
  - **Changed since the confirmation:** meetings whose date, start, end, room or status differ from the snapshot taken when an assignment was confirmed.

---

## 2. Core Concepts

### 2.1 Interpreter

**Definition**: A supplier of interpretation services, either an individual professional or a bureau representing multiple interpreters.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `interpreter_id` | Integer | Primary key, unique | System identifier |
| `first_name` | String | Required | Given name |
| `last_name` | String | Required | Family name |
| `email` | String | Required, unique | Email address - used as external identifier |
| `phone` | String | Optional | Contact telephone number |
| `priority_order` | Integer | Required, unique, > 0 | Position in legal priority sequence (1 = highest) |
| `bureau_affiliation` | String | Optional | Bureau name if representing an agency; null for individuals |
| `additional_languages` | String | Optional | Languages beyond Dutch/French |
| `notes` | Text | Optional | Free-form administrative notes |
| `engagement` | Enum | Required, default INVOICE | How the interpreter works (the user, 10 October 2026): INVOICE, an interpreter or bureau that works on invoice ("FACT." in the spreadsheet), or OCCASIONAL_WORK, an interpreter who works through the system of occasional work (gelegenheidswerk), which requires a Dimona declaration and has no invoice ("DIM") |

**Business Rules**:
- **BR-INT-001**: Email must be unique across all interpreters (used for availability matching)
- **BR-INT-002**: Priority order must form a continuous sequence starting at 1 with no gaps
- **BR-INT-003**: Bureau affiliation null = individual interpreter; non-null = bureau representative

**Derived Properties**:
- `interpreter_type`: INDIVIDUAL if bureau_affiliation is null, BUREAU if non-null

**Invariants**:
- At any moment, the set of all priority_order values equals {1, 2, 3, ..., N} where N is the count of interpreters
- No two interpreters can share the same email

---

### 2.2 Time Slot

**Definition**: A discrete period of time for which availability can be declared and bookings can be made.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `slot_id` | Integer | Primary key, unique | System identifier |
| `date` | Date | Required | Calendar date |
| `start_time` | Time | Required | When slot begins (24-hour format) |
| `end_time` | Time | Required | When slot ends (24-hour format) |
| `estimated_duration` | Integer | Derived | Duration in hours (end_time - start_time) |
| `description` | String | Optional | Human-readable label (e.g., "Monday afternoon session") |

**Business Rules**:
- **BR-SLOT-001**: start_time must be < end_time
- **BR-SLOT-002**: Typical durations are 2-4 hours, occasionally up to 8 hours
- **BR-SLOT-003**: Time slots may or may not correspond to meetings (slots are generic time periods)

**Derived Properties**:
- `datetime_start`: Combination of date + start_time
- `datetime_end`: Combination of date + end_time
- `duration_hours`: (end_time - start_time) in hours

**Key Insight**:
Time slots exist independently of meetings. We ask interpreters "Can you work Monday 14:00-17:00?" regardless of whether a meeting is scheduled. This allows:
- Collecting availability before all meetings are confirmed
- Rebooking interpreters if meetings are cancelled
- Maintaining interpreter commitments even when meeting details change

---

### 2.3 Availability Declaration

**Definition**: An interpreter's statement that they have capacity to work during a specific time slot.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `availability_id` | Integer | Primary key, unique | System identifier |
| `interpreter_id` | Integer | Foreign key, required | Who is declaring availability |
| `slot_id` | Integer | Foreign key, required | Which time slot |
| `quantity_available` | Integer | Required, >= 0 | Number of interpreters available (0 = not available) |
| `declaration_timestamp` | DateTime | Required | When interpreter submitted response |
| `source` | String | Required | Data source identifier (e.g., "Q4-2025-Quarterly-Form") |
| `notes` | Text | Optional | Any conditions or notes from interpreter |
| `leaves_at_end` | Boolean | Required, default FALSE | The interpreter says they must leave right at the end of the assignment. Set by the planner from the notes; such an availability is skipped (BR-INS-005) |

**Business Rules**:
- **BR-AVL-001**: For INDIVIDUAL interpreters, quantity_available is typically 0 or 1
- **BR-AVL-002**: For BUREAU interpreters, quantity_available can be 0, 1, 2, ..., 10 or more
- **BR-AVL-003**: quantity_available = 0 means "not available" (explicitly declared unavailable)
- **BR-AVL-004**: If multiple declarations exist for same (interpreter_id, slot_id), use the one with latest declaration_timestamp
- **BR-AVL-005**: Availability declaration does NOT guarantee a booking - it's a statement of capacity only

**Derived Properties**:
- `is_available`: TRUE if quantity_available > 0
- `interpreter_priority`: Retrieved from interpreter.priority_order for assignment decisions

**Invariants**:
- For any (interpreter_id, slot_id) pair, only one active availability exists (latest timestamp)
- quantity_available for individual interpreters should never exceed 1

**Key Distinction**:
An availability says "I CAN work" but not "I WILL work". Transformation from availability to booking requires a confirmation step.

---

### 2.4 Booking

**Definition**: A proposed or confirmed reservation of interpreter capacity for a time slot - the commitment towards one supplier. For an individual it reserves one interpreter; for a bureau it reserves a bucket of N interpreters. Each interpreter in the booking is a Booking Position (2.5).

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `booking_id` | Integer | Primary key, unique | System identifier |
| `interpreter_id` | Integer | Foreign key, required | Who is booked (individual or bureau) |
| `slot_id` | Integer | Foreign key, required | Which time slot (e.g., Monday 9:00-13:00) |
| `quantity_booked` | Integer | Derived | Number of ACTIVE positions in this booking |
| `status` | Enum | Required | PROPOSED, CONFIRMED, COMPLETED, CANCELLED |
| `booking_reason` | String | Optional | Why booked if no meetings assigned yet |
| `forfait_hours` | Integer | Required, 3 or 4, default 4 | The forfait the booking is paid on: everyone works on forfaits of 3 or 4 hours (the user, 10 October 2026; "forfait 3u", later "bloc 3" in the spreadsheet). When in doubt, four hours (BR-INS-002). Overtime is added per half hour, per position (BR-BKG-009) |
| `notes` | Text | Optional | Administrative notes, override reasons |
| `created_at` | DateTime | System-generated | When booking created |
| `updated_at` | DateTime | System-maintained | Last modification |
| `created_by` | Integer | Foreign key to User | Who created this booking |

**Business Rules**:
- **BR-BKG-001**: quantity_booked must be <= availability.quantity_available (if availability exists), unless overridden with a documented reason
- **BR-BKG-002**: For INDIVIDUAL interpreters, a booking has exactly 1 position
- **BR-BKG-003**: For BUREAU interpreters, a booking has 1, 2, 3, ... positions, up to the bureau's declared capacity
- **BR-BKG-004**: Status transitions: PROPOSED → CONFIRMED → COMPLETED, or → CANCELLED from any state
- **BR-BKG-005**: A booking reserves capacity for a time block (e.g., Monday 9-13h)
- **BR-BKG-006**: Creating a booking for N interpreters creates N positions, numbered 1..N
- **BR-BKG-007**: An interpreter or bureau has at most one CONFIRMED booking per time slot, and no CONFIRMED bookings with overlapping time slots. More interpreters from the same bureau for the same slot are added as extra positions on the existing booking (within the declared availability)
- **BR-BKG-008**: A booking is COMPLETED when the work is done; actual hours are recorded per position (2.5)
- **BR-BKG-009**: Every interpreter is paid the booking's forfait of 3 or 4 hours. When the meeting runs over, the extra time is added per half hour; a half hour that has started counts in full (the user, 10 October 2026). "forfait 3u + overuren" in the spreadsheet. The real end and the half hours charged are recorded per meeting (2.7, BR-MTG-011)

**Derived Properties**:
- `quantity_booked`: Count of ACTIVE positions
- `assigned_meeting_count`: Number of distinct meetings assigned to any of its positions
- `free_positions`: ACTIVE positions without any meeting assignment
- `slot_datetime`: Combined date and time from related slot

**Invariants**:
- An interpreter or bureau cannot have overlapping CONFIRMED bookings
- All meetings assigned to any position of a booking must fall within the booking's time slot

**Key Insight**:
A booking is the commitment to a supplier for a TIME BLOCK: "Bureau X, 3 interpreters, Monday 9-13h". It does not say where those interpreters go. That happens per position: within the block, each interpreter can work several non-overlapping meetings, and the three interpreters of the bucket can all be at different meetings at the same time.

---

### 2.5 Booking Position

**Definition**: One interpreter within a booking. An individual's booking has one position; a bureau booking for N interpreters has N positions. Each position is dispatched to meetings independently of the other positions in the same booking.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `position_id` | Integer | Primary key, unique | System identifier |
| `booking_id` | Integer | Foreign key, required | The booking (bucket) this position belongs to |
| `position_number` | Integer | Required, unique within the booking | 1..N, e.g. "Bureau X - interpreter 2 of 3" |
| `interpreter_name` | String | Optional | The person actually sent. For an individual: the interpreter. For a bureau: filled in when the bureau communicates it |
| `status` | Enum | Required | ACTIVE, CANCELLED |
| `actual_start_time` | DateTime | Optional | When this interpreter actually started |
| `actual_end_time` | DateTime | Optional | When this interpreter actually finished |
| `notes` | Text | Optional | E.g. "replacement for X, who fell ill" |
| `invoice_id` | Integer | Foreign key, optional | The invoice (2.9) that covers this service. Empty: not received yet. Only when the interpreter works on invoice |
| `dimona_declared` | Boolean | Required, default FALSE | The Dimona declaration for this service is done ("DIM / ok" in the spreadsheet). Only for occasional work |

**Business Rules**:
- **BR-POS-001**: A position belongs to exactly one booking; position_number is unique within that booking
- **BR-POS-002**: Meetings assigned to one position must not overlap (one person cannot be in two places)
- **BR-POS-003**: Different positions of the same booking may be assigned to the same meeting or to overlapping meetings - they are different people
- **BR-POS-004**: When a bureau replaces the person on a position (illness, schedule change), only interpreter_name changes; the position's meeting assignments remain valid. The change is recorded in notes
- **BR-POS-005**: Cancelling a position (the bureau cannot send that interpreter after all) cancels its meeting assignments; the affected meetings become understaffed and are flagged
- **BR-POS-006**: interpreter_name must be filled in before the booking is COMPLETED (needed for the overview to HR)
- **BR-POS-007**: Actual hours are recorded per position, because interpreters at the same meeting can work different hours (one stays longer than another)
- **BR-POS-008**: Whether the invoice for a service has come in, and its reference, are recorded per position, by linking the position to an invoice (2.9). One invoice often covers several positions (a bureau invoicing a month), so the planner records the invoice once and links all positions it covers in one action. Linking and unlinking are logged like any other change
- **BR-POS-009**: Whether a position needs an invoice or a Dimona declaration follows from the interpreter's engagement (2.1): an interpreter in occasional work sends no invoice; instead the planner ticks that the Dimona declaration is done. The engagement at the time is kept in the assignment log's snapshot

**Derived Properties**:
- `interpreter_id`: From the booking (the individual or the bureau, whose priority applies)
- `assigned_meetings`: Meetings linked to this position by non-cancelled assignments
- `free_periods`: Parts of the booking's time block not covered by an assigned meeting
- `actual_duration_hours`: (actual_end_time - actual_start_time) in hours
- `overtime_half_hours`: the number of half hours, started half hours counting in full, worked beyond the booking's forfait (BR-BKG-009), from the meeting's real end (2.7) unless the position's own actual end differs; 0 when the work stays within the forfait
- `paid_hours`: forfait_hours + overtime_half_hours / 2
- `invoice_received`: TRUE when the position is linked to an invoice. COMPLETED positions of interpreters on invoice without an invoice form the work list **invoice not received yet**; COMPLETED positions of interpreters in occasional work without a declaration form the work list **Dimona to declare**

**Key Insight**:
The position is the unit of dispatching. Example:
- Booking: Bureau X, Monday 9:00-13:00, 3 positions
- Position 1 → Meeting A (9:00-10:30), then Meeting C (11:00-12:30)
- Position 2 → Meeting A (9:00-10:30), then Meeting C (11:00-12:30)
- Position 3 → Meeting B (9:30-11:00), then Meeting C (11:00-12:30)

---

### 2.6 Meeting Assignment

**Definition**: The dispatching of one booking position - one interpreter - to one meeting.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `assignment_id` | Integer | Primary key, unique | System identifier |
| `position_id` | Integer | Foreign key, required | Which interpreter (booking position) is dispatched |
| `meeting_id` | Integer | Foreign key, required | Which meeting |
| `assignment_status` | Enum | Required | PROPOSED, CONFIRMED, CANCELLED |
| `notes` | Text | Optional | Assignment-specific notes |
| `cancellation_communicated_on` | Date | Optional | When the planner told the interpreter (or the bureau) that the meeting was cancelled ("annulation transmise" in the spreadsheet). Matters for what is still owed |
| `created_at` | DateTime | System-generated | When assignment created |
| `created_by` | Integer | Foreign key to User | Who created this assignment |

**Business Rules**:
- **BR-ASGN-001**: The meeting must fall within the time slot of the position's booking
- **BR-ASGN-002**: Cannot assign overlapping meetings to the same position
- **BR-ASGN-003**: If the booking or the position is CANCELLED, its assignments are CANCELLED
- **BR-ASGN-004**: An assignment can be cancelled without cancelling the position or booking (e.g., meeting cancelled, interpreter stays booked)
- **BR-ASGN-005**: Assignment status cannot be CONFIRMED if booking status is not CONFIRMED
- **BR-ASGN-006**: A position can be assigned to a given meeting only once; each assignment puts exactly one interpreter on one meeting
- **BR-ASGN-007**: Every creation, status change and cancellation of an assignment adds an entry to the assignment log (1.6), with the user, the time and a snapshot of the meeting. Assignments and log entries are never deleted
- **BR-ASGN-008**: A meeting that is cancelled or deleted in spic does not cancel its assignments automatically; the planner decides (5.4)

**Derived Properties**:
- `booking_id`, `interpreter_id`: Retrieved through the position
- `time_conflict`: TRUE if this meeting overlaps with another meeting assigned to the same position

**Invariants**:
- All meetings assigned to one position are non-overlapping
- An assignment can only exist if its position exists
- Meeting datetime must be within the booking's slot datetime range

**Key Insight**:
Because one assignment = one interpreter, staffing a meeting is a matter of counting its confirmed assignments, whether the interpreters come from one bureau booking, from several individuals, or a mix.

---

### 2.7 Meeting

**Definition**: A scheduled event requiring interpretation services, which consumes booked interpreter capacity. A meeting has one of two origins:

- **From spic** (SPIC): a copy of a spic meeting (1.1, 1.3). Read-only in PDC, except start time, room and cancellation, which go through spic's write route (1.4).
- **Own** (OWN): entered in PDC (1.5). Fully editable in PDC; no series.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `meeting_id` | Integer | Primary key, unique | PDC's own identifier; assignments refer to it |
| `origin` | Enum | Required | SPIC or OWN; shown as the label "from spic" / "own" |
| `spic_id` | String | Unique; required for SPIC, empty for OWN | spic's stable ID (`m-xxxxxxxx`) |
| `status` | Enum | Required | PLANNED, CANCELLED, DELETED (spic: `gepland`, `geannuleerd`, and deleted). DELETED only for spic meetings that were deleted in spic |
| `week` | Date | SPIC only | Monday of the spic week the meeting belongs to |
| `week_status` | Enum | SPIC only | PRE_DEFINITIVE, DEFINITIVE, or CONCEPT when the week went back to concept (BR-MTG-009) |
| `title` | String | Required for OWN | Title of an own meeting. For a spic meeting the title is derived from spic's domain, assembly, type and sequence numbers |
| `date` | Date | Required | Calendar date (Brussels time) |
| `period` | Enum | Required | AM or PM. Always present in spic, also when no start time is known |
| `start_kind` | Enum | SPIC only | TIME (a start time) or AFTER (after another meeting, without a time) |
| `start_time` | Time | Optional | Start time as entered. Empty for "after another meeting" |
| `effective_start` | Time | Optional | Start time used for planning. **Can be empty** in spic ("after another meeting" is not calculated) |
| `expected_end` | Time | Optional | End time. **Can be empty** in spic; in spic it is entered or estimated from the agenda or the meeting type |
| `room` | Code | Required for OWN | Room from spic's fixed list of rooms, for spic and own meetings alike |
| `domain`, `assembly`, `type` | Code | SPIC only | spic's classification of the meeting |
| `sequence_number`, `sequence_number_2` | Integer | SPIC only | spic's sequence numbers |
| `interpreters_needed` | Integer | > 0 | Number of interpreters required. **Kept in PDC**, also for spic meetings (spic does not know it). Required for own meetings. Proposal: a default for a new spic meeting, 3 for a plenary session and 2 otherwise (the spreadsheet has the rows Tolk 1, Tolk 2 and Tolk 3 (PLEN)); the planner can change it |
| `category` | Enum | Required | Category used in PDC. For spic meetings it must be derived from domain, assembly and type (still to be designed, 9 point 12) |
| `notes` | Text | Optional | PDC's own notes |
| `actual_end` | Time | Optional | The real end of the meeting according to our own staff. Kept in PDC, also for spic meetings |
| `charged_half_hours` | Integer | Optional, >= 0 | The number of half hours of overtime charged for the meeting |
| `spic_data` | Document | SPIC only | The complete last state received from spic, including the fields PDC does not use (officials, comment, questions per agenda item, priority, transcription...) |
| `last_change_number` | Integer | SPIC only | spic's change number of the last change applied to this copy |
| `created_at`, `updated_at` | DateTime | System-maintained | When the copy or the own meeting was created and last changed |
| `created_by` | User | OWN only | Who entered the own meeting |

**Business Rules**:
- **BR-MTG-001**: For an own meeting, the end (or start + duration) must be after the start. For a spic meeting the times are taken as they are and may be missing
- **BR-MTG-002**: The duration of a meeting is expected_end - effective_start when both are known; otherwise it is unknown and shown as such
- **BR-MTG-003**: A meeting is staffed through Meeting Assignments (2.6), each putting one interpreter (one booking position) on the meeting
- **BR-MTG-004**: A spic meeting is read-only in PDC, except start time, room and cancellation, which are changed through spic's write route (1.4), without a lock. All other changes are made in spic and reach PDC through the copy
- **BR-MTG-005**: A spic meeting cannot be deleted in PDC. A deletion in spic sets the copy's status to DELETED; the copy and its assignments are kept. A restore in spic (same ID) makes the copy active again
- **BR-MTG-006**: An own meeting can be deleted only as long as no interpreter was ever assigned to it (no assignment, whatever its status, and no entry in the assignment log); otherwise it can only be cancelled
- **BR-MTG-007**: No recurrence and no series: each own meeting is entered on its own
- **BR-MTG-008**: Spic meetings are recognised by `spic_id`, never by date and time. A meeting that moves to another week in spic stays the same meeting in PDC, with its assignments
- **BR-MTG-009**: Only meetings of pre-definitive and definitive weeks are visible. When a week goes back to concept, its meetings disappear from the visible list; their copies and assignments are kept, and a meeting that has assignments is flagged to the planner
- **BR-MTG-010**: Cancelling or deleting a meeting never cancels or removes its assignments automatically; the meeting appears on the work list "cancelled with an assigned interpreter" (1.6, 5.4)
- **BR-MTG-011**: When actual_end is filled in, PDC calculates the half hours of overtime it implies against the forfait of the bookings involved (BR-BKG-009) and shows them next to charged_half_hours; a difference is flagged for the planner, e.g. when checking an invoice

**Missing times** (proposal, to be confirmed): the checks that compare times (BR-POS-002, BR-ASGN-001, BR-ASGN-002, BR-VAL-004) use effective_start and expected_end when they are known. When one of them is missing, PDC uses the period (AM or PM) for matching the meeting to a time slot, does not refuse an assignment, and flags it as "time unknown" until spic provides the time.

**Derived Properties**:
- `datetime_start`: date + effective_start combined, when known
- `datetime_end`: date + expected_end combined, when known
- `time_known`: TRUE when both effective_start and expected_end are known
- `staffing_count`: Number of CONFIRMED meeting assignments for this meeting
- `staffing_status`: 
  - UNSTAFFED if staffing_count = 0
  - UNDERSTAFFED if staffing_count < interpreters_needed
  - FULLY_STAFFED if staffing_count = interpreters_needed
  - OVERSTAFFED if staffing_count > interpreters_needed

**Relationship to Time Slots**:
- A meeting typically aligns with a time slot or portion of a slot
- Multiple meetings can occur within the same time slot
- When collecting availability, we create slots for expected meeting times

**Relationship to Bookings**:
- A meeting is staffed by booking positions, via meeting assignments
- The positions may come from different bookings, or several may come from the same bureau booking
- The booking provides the commitment; the position provides the person

**Key Insight**:
Meetings are downstream consumers of booked capacity. The sequence is:
1. Declare availability for time slots
2. Create bookings from availability (reserves capacity for time blocks, one position per interpreter)
3. Meetings arrive from spic (or are entered as own meetings)
4. Assign positions to meetings
5. If a meeting cancels, the planner cancels its assignments (never automatically, 5.4) but keeps the bookings and positions for reassignment

---

### 2.8 CSV Data Source

**Definition**: A configured external source providing availability declarations via HTTP-accessible CSV file.

**Scope (1.2)**: CSV sources are only for **availabilities**, which keep coming from Google Forms for now. Meetings never come from a CSV file or are entered by hand any more: they come from spic, or are own meetings (1.1). A later idea, not decided, is PDC's own response form for the interpreters, which would replace the CSV import (9, point 14).

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `source_id` | Integer | Primary key, unique | System identifier |
| `name` | String | Required, unique | Human-readable identifier (e.g., "Q4 2025 Quarterly") |
| `url` | String | Required | HTTP URL returning CSV data |
| `source_type` | Enum | Required | QUARTERLY, WEEKLY, EMERGENCY |
| `is_active` | Boolean | Required, default TRUE | Whether to include in imports |
| `created_at` | DateTime | System-generated | When source was configured |
| `last_fetched` | DateTime | System-maintained | Last successful fetch timestamp |

**Business Rules**:
- **BR-SRC-001**: URL must return valid CSV with expected structure
- **BR-SRC-002**: Multiple sources can be active simultaneously
- **BR-SRC-003**: Each source may define different time slots (no overlap constraint)

**CSV Structure Expected**:
- Column 1: Timestamp (when form submitted)
- Column 2: Name/Identifier (informational)
- Column 3: Email (used for interpreter matching)
- Columns 4-N: Time slot columns
  - Header format describes the slot: "Date Time Description"
  - Cell values: "Niet beschikbaar" (0), "1 tolk beschikbaar" (1), "N tolken beschikbaar" (N)

---

### 2.9 Invoice

**Definition**: An invoice received from an interpreter or a bureau for services rendered. One invoice usually covers several services: a bureau sends one invoice per month for all its interpreters (2.5, BR-POS-008).

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `invoice_id` | Integer | Primary key, unique | System identifier |
| `interpreter_id` | Integer | Foreign key, required | Who sent the invoice (the individual or the bureau) |
| `reference` | String | Optional | The supplier's invoice number. The spreadsheet sometimes only notes "ok", without a number |
| `received_on` | Date | Required | When the invoice came in |
| `period` | String | Optional | The period it covers, e.g. a month |
| `checked_on`, `checked_by` | Date, User | Optional | When and by whom the invoice was checked against the services it covers. "ok" in the spreadsheet probably means received and checked (the user, 10 October 2026; to be confirmed with the staff) |
| `notes` | Text | Optional | E.g. "only one interpreter charged for this meeting" |
| `created_at`, `created_by` | DateTime, User | System-generated | Who recorded it, when |

**Business Rules**:
- **BR-INV-001**: An invoice is linked to the positions it covers; every linked position belongs to a booking of the same interpreter or bureau
- **BR-INV-002**: A position is linked to at most one invoice
- **BR-INV-003**: Recording, changing and unlinking an invoice are logged; an invoice that has linked positions is not deleted

**Derived Properties**:
- `positions`: the services the invoice covers, with their actual hours, for checking the invoice

---

## 3. Conceptual Relationships

### 3.1 The Availability → Booking → Position → Meeting Flow

```
INTERPRETER (individual or bureau)
    |
    | declares capacity for
    ↓
TIME SLOT ← describes time block (e.g., Monday 9:00-13:00)
    |
    ↓
AVAILABILITY DECLARATION   (Bureau X CAN provide 3 interpreters, Monday 9-13h)
    |
    | priority algorithm
    ↓
BOOKING                    (Bureau X WILL provide 3 interpreters, Monday 9-13h)
    |
    | one position per interpreter
    ↓
POSITION 1 ── assignment ──→ MEETING A (9:00-10:30)
           └─ assignment ──→ MEETING C (11:00-12:30)
POSITION 2 ── assignment ──→ MEETING A (9:00-10:30)
           └─ assignment ──→ MEETING C (11:00-12:30)
POSITION 3 ── assignment ──→ MEETING B (9:30-11:00)
           └─ assignment ──→ MEETING C (11:00-12:30)
```

**Key Principle**: The booking is the commitment to the supplier; the positions are the individual interpreters in it. Each position can serve several non-overlapping meetings within the block, independently of the other positions.

### 3.2 The Independence Principle

**Why separate availability, booking, position and meeting?**

**Scenario 1: Meeting cancellation within booked block**
- Monday 9:00-13:00 time slot
- Bureau DTITD declared available (qty: 3)
- Booking created: DTITD, Monday 9-13h, 3 positions, status: CONFIRMED
- Assignments:
  - Positions 1 and 2 → Meeting A (9:00-10:30, needs 2)
  - Position 3 → Meeting B (11:00-12:30, needs 1)
- Friday: Meeting A CANCELLED
- **Result**:
  - Cancel the assignments of positions 1 and 2 to Meeting A
  - Position 3 keeps Meeting B
  - Booking remains CONFIRMED (commitment for 3 interpreters, 9-13h)
  - Positions 1 and 2 are free for the whole block and can be dispatched to other meetings, separately

**Scenario 2: Entire booked block no longer needed**
- Same booking, both Meeting A and B cancel
- Cancel all assignments
- Booking remains CONFIRMED (no meetings assigned)
- Options:
  - Find new meetings for these positions
  - Or: Cancel booking (interpreters get forfait for blocked time)

**Scenario 3: Availability before meetings confirmed**
- July: Collect availability for "Monday mornings 9-13h" throughout September
- Interpreters declare: "I can work Sept 15, 9-13h"
- August: Create bookings from availability
- September: Meetings finalized, positions assigned to specific meetings
- An interpreter may work 1, 2, or 3 meetings during their 9-13h booking

**Scenario 4: Emergency meeting fits into existing booking**
- Existing booking: Monday 9-13h; position 1 assigned to Meeting A (9:00-10:30)
- Tuesday: Urgent Meeting B scheduled for Monday 11:00-12:00
- Check: position 1 is free from 10:30 to 13:00
- Assign position 1 → Meeting B
- No need to create new booking, reuse existing capacity

### 3.3 The Booking Status Lifecycle

```
[AVAILABILITY exists]
         ↓
    (Algorithm selects based on priority)
         ↓
    PROPOSED BOOKING (system suggestion)
         ↓
    (Human confirms)
         ↓
    CONFIRMED BOOKING (commitment made, capacity blocked)
         ↓
    (Meetings occur, work performed)
         ↓
    COMPLETED BOOKING (actual times logged per position)

Alternative path:
    CONFIRMED → CANCELLED (meeting cancelled, interpreter not needed, etc.)
    PROPOSED → CANCELLED (decided not to use)
```

**Critical State Properties**:

- **PROPOSED**: No commitment yet, can be freely deleted/modified
- **CONFIRMED**: Commitment exists, interpreters expect work and payment
- **COMPLETED**: Work done, actual hours recorded on each position
- **CANCELLED**: Was committed, no longer valid (still tracked for audit)

Positions have their own, simpler status: ACTIVE, or CANCELLED when the bureau cannot send that interpreter after all (BR-POS-005). Replacing the person does not cancel the position (BR-POS-004).

### 3.4 Relationships Between Booking, Position and Meeting

**One Booking → N Positions**
- A booking for an individual has one position; a bureau booking for N interpreters has N positions
- Extra interpreters from the same bureau for the same slot are added as positions to the same booking

**One Position → Many Meetings**
- A position belongs to a booking that reserves a time block (e.g., Monday 9:00-13:00)
- The interpreter in that position can work several non-overlapping meetings within the block
- Each meeting is linked via a Meeting Assignment

**One Meeting → Many Positions**
- A meeting needing 4 interpreters gets 4 assignments, each to one position
- The positions can come from different bookings, or several from one bureau booking
- Example: Meeting X → position 1 of Interpreter A's booking + position 1 of Interpreter B's booking + positions 2 and 3 of Bureau C's booking

**Implementation**:
- Meeting Assignment is the junction between Booking Position and Meeting
- Supports partial cancellations (one meeting cancels, others remain) and per-interpreter dispatching within a bureau booking

**Assignment Rules**:
- Meetings assigned to the same position MUST NOT overlap
- Different positions of one booking MAY be at overlapping meetings
- All meetings assigned to a position MUST fall within the booking's time slot
- If a booking or position is CANCELLED, its assignments are CANCELLED
- If a meeting is CANCELLED, only that meeting's assignments are cancelled, by the planner and never automatically (BR-MTG-010)

**Reassignment Scenario**:
```
Initial:
- Booking: Mon 9-13h, Interpreter X (one position)
- Assignments: position 1 → Meeting A (9-11h)

Meeting A cancels:
- Cancel assignment (position 1 → Meeting A)
- Booking and position still exist, free 9-13h

New meeting added:
- Meeting D (10-12h) scheduled
- Assign position 1 → Meeting D

Result:
- Interpreter X still works Monday 9-13h
- Different meeting, same time commitment
```

---

## 4. Business Rules

### 4.1 Priority-Based Booking Creation

**BR-BOOK-001: Availability as Input**
When creating bookings for a time slot, the system:
1. Retrieves all availability declarations for that slot where quantity_available > 0
2. Sorts by interpreter.priority_order ASC
3. Evaluates each in order

**BR-BOOK-002: Greedy Booking Algorithm**
```
remaining_need = desired_quantity (or the meeting's unfilled need when staffing a meeting)
positions_created = []

FOR each availability IN sorted_by_priority:
    IF remaining_need <= 0:
        BREAK
    
    IF availability.leaves_at_end:
        RECORD skip (interpreter, reason "must leave at the end of the assignment")
        CONTINUE                                   # BR-INS-005: take the next in the ranking

    capacity = availability.quantity_available
               - positions already booked for this interpreter in this slot
    can_book = MIN(capacity, remaining_need)
    IF can_book <= 0:
        CONTINUE

    booking = existing booking of this interpreter for this slot
              OR CREATE booking (interpreter_id, slot_id, status = PROPOSED)
    ADD can_book positions to booking

    IF staffing a meeting:
        FOR each new position:
            CREATE meeting assignment (position → meeting, status = PROPOSED)
    
    positions_created += new positions
    remaining_need -= can_book

RETURN positions_created, remaining_need
```

**BR-BOOK-003: Partial Fulfillment**
- If Priority #2 (bureau) has quantity_available = 2, but remaining_need = 5
- Book 2 positions from Priority #2
- Continue to Priority #3 for remaining 3

**BR-BOOK-004: Stopping Condition**
- Stop when remaining_need = 0 OR end of priority list
- If remaining_need > 0 at end: Flag as insufficient capacity

**BR-BOOK-005: Manual Override**
- Human can create bookings that violate priority order
- System MUST require documented reason in booking.notes
- Audit trail shows: algorithm suggestion vs. actual booking

**BR-BOOK-006: Priority Applies to Booking, Not to Dispatching**
- An interpreter is always booked before being assigned to a meeting
- The priority order governs who gets a booking
- Positions that are already booked are dispatched to meetings without applying the priority order again: free booked positions are used before any new booking is made (5.3, option A)

### 4.2 Booking Validation Rules

**BR-VAL-001: No Double-Booking**
- An interpreter or bureau has at most one CONFIRMED booking per time slot, and none with overlapping slots
- Check: SELECT bookings WHERE interpreter_id = X AND status = CONFIRMED AND slot overlaps
- Overlapping slots = same date + time ranges intersect

**BR-VAL-002: Capacity Limits**
- For INDIVIDUAL: exactly 1 position
- For BUREAU: number of ACTIVE positions <= quantity_available (if availability exists)
- Cannot book more than declared capacity without a documented override

**BR-VAL-003: Status Transition Validation**
- PROPOSED → CONFIRMED: Allowed
- PROPOSED → CANCELLED: Allowed
- CONFIRMED → COMPLETED: Allowed only after slot.datetime_end has passed
- CONFIRMED → CANCELLED: Allowed with reason
- COMPLETED → any: Not allowed (terminal state)
- Any → PROPOSED: Not allowed (cannot uncommit)

**BR-VAL-004: Meeting Assignment Validation**
- When assigning a position to a meeting:
  - Meeting datetime must fall within the booking's time slot
  - Meeting must not overlap with other meetings assigned to the same position
- Check for temporal conflicts:
  ```sql
  SELECT * FROM meeting_assignments ma
  JOIN meetings m ON ma.meeting_id = m.meeting_id
  WHERE ma.position_id = X
    AND ma.assignment_status <> 'CANCELLED'
    AND m overlaps with new_meeting
  ```
- If conflict found: Reject assignment or flag for manual override

### 4.3 Availability Declaration Rules

**BR-AVAIL-001: Latest Declaration Wins**
- If interpreter submits multiple declarations for same slot, use latest declaration_timestamp
- Previous declarations retained for audit but marked superseded

**BR-AVAIL-002: Zero Means Unavailable**
- quantity_available = 0 is explicit unavailability
- Missing declaration (no record) also means unavailable
- Distinction: Explicit "no" vs. no response

**BR-AVAIL-003: Email Matching**
- Declaration email must match interpreter.email (case-insensitive)
- Unmatched emails create orphan declarations (logged, require manual intervention)

**BR-AVAIL-004: Slot Identification from CSV**
- CSV column headers parsed to extract slot parameters
- System attempts to match to existing slot by (date, start_time)
- If no match: Create new slot automatically
- Or: Flag for manual slot creation

### 4.4 Meeting Staffing Rules

**BR-STAFF-001: Staffing via Meeting Assignments**
- A meeting's staffing is the number of its CONFIRMED meeting assignments (one interpreter each)
- PROPOSED assignments don't count toward staffing
- CANCELLED assignments don't count

**BR-STAFF-002: Staffing Threshold**
- FULLY_STAFFED: staffing = meeting.interpreters_needed
- UNDERSTAFFED: staffing < needed
- OVERSTAFFED: staffing > needed (warning, but allowed)

**BR-STAFF-003: Unassigned Meeting Creation**
- Can create meeting even if no assignments exist yet
- Meeting starts in UNSTAFFED status
- Workflow: Create meeting → Match to time slot → Use free booked positions, or create bookings from availability → Assign positions to meeting

**BR-STAFF-004: Assignment Flexibility**
- One position can serve multiple non-overlapping meetings
- The positions of one bureau booking can be dispatched to different meetings
- If Meeting A cancels: the planner cancels its assignments (never automatically, 5.4) and keeps the positions, which become available for other meetings
- If a whole booking is no longer needed: Cancel booking (all positions and assignments also cancelled)

### 4.5 Instructions for Booking (September 2026)

Instructions the user sent to the team at the start of September 2026, to prevent difficult situations. PDC follows them by default.

**BR-INS-001: Three or Four Hours, Always Stated**
- Every booking states whether it is for three or four hours (forfait_hours, 2.4), and so does every confirmation. In the spreadsheet this is the note "bloc 3" or "bloc 4" next to the time (seen from week 42 on; earlier weeks say "forfait 3u")

**BR-INS-002: When in Doubt, Four Hours**
- If there is any doubt about the length, the booking is for four hours. PDC proposes four hours; three hours is an explicit choice of the planner

**BR-INS-003: No End Time towards the Interpreters**
- Out of caution, nothing PDC sends or shows to interpreters predicts when the meeting ends: confirmations give the start time and the three or four hours, never an expected end. The expected end stays internal (2.7)

**BR-INS-004: The Start Is the Start of the Meeting**
- A booking starts at the start time of the meeting it is made for. When the start is not known yet (a meeting "after another meeting", 2.7), the planner sets it when it is known

**BR-INS-005: Interpreters Who Must Leave on Time Are Skipped**
- An interpreter who says they must leave right at the end of the assignment is skipped, because a meeting can always run over (the tender specifications say so); the next one in the ranking gets the booking. The skip and its reason are recorded, so the priority order stays documented (BR-BOOK-005)

**BR-INS-006: The Meeting Is for Information**
- The meeting is mentioned in the call for information only. The Parliament pays for a service of three or four hours, whatever the committee, and can deploy the interpreter on the spot at another meeting as needed: the booking is the commitment, the meeting assignment can change within the block (2.4, 2.6, 3.2)

**BR-INS-007: The Overrun Clause Stands Out**
- Confirmations show the clause "De opdrachtnemer verbindt zich ertoe te tolken tot aan het einde van de betrokken vergadering, zelfs in geval van overschrijding van de aanvankelijke geplande tijdsduur van de betrokken vergadering" in a box that stands out (another colour or place than the rest of the text)

---

## 5. Key Processes

### 5.1 Availability Collection Process

**Objective**: Import interpreter availability declarations for time slots from external CSV sources.

**Scope (1.2)**: availabilities only; for now they keep coming from Google Forms. Meetings come from spic (1.3) or are own meetings (1.5).

**Input**: CSV source URL(s)

**Steps**:

1. **Fetch CSV**
   - HTTP GET source.url
   - Parse CSV structure
   - Validate: has timestamp, email, time slot columns

2. **Process Time Slot Headers**
   - Columns 4-N represent time slots
   - Parse each header: extract date, start_time, end_time (or duration), description
   - FOR each header:
     - Check if slot exists: SELECT slot WHERE date = X AND start_time = Y
     - IF exists: Use existing slot_id
     - IF not exists: CREATE new slot
     - Map column_index → slot_id

3. **Process Interpreter Responses**
   - FOR each data row:
     - Extract email (column 3)
     - Match to interpreter: SELECT interpreter WHERE LOWER(email) = LOWER(csv_email)
     - IF not matched: Create orphan_declaration record, log warning, skip
     - Extract timestamp (column 1)
     - FOR each time slot column:
       - Parse cell value: "Niet beschikbaar" → 0, "N tolken beschikbaar" → N
       - Check existing availability: SELECT * WHERE interpreter_id = X AND slot_id = Y
       - IF exists AND csv_timestamp > existing_timestamp:
         - UPDATE availability SET quantity_available = N, declaration_timestamp = csv_timestamp
       - IF not exists:
         - INSERT availability (interpreter_id, slot_id, quantity_available, declaration_timestamp, source)

4. **Report Results**
   - Rows processed: R
   - Interpreters matched: M
   - Interpreters unmatched: U (list emails)
   - Slots found: S_existing
   - Slots created: S_new
   - Availability declarations created: A_new
   - Availability declarations updated: A_updated

**Output**: Populated availability_declarations table

---

### 5.2 Booking Creation Process (Priority-Based)

**Objective**: Book interpreters from availability declarations for a time slot, optionally assigning them to a meeting.

**Input**:
- slot_id (which time slot)
- quantity_needed (how many interpreters)
- meeting_id (optional: if the new positions should be assigned to a specific meeting)

**Steps**:

1. **Gather Available Capacity**
   ```sql
   SELECT a.*, i.priority_order
   FROM availability_declarations a
   JOIN interpreters i ON a.interpreter_id = i.interpreter_id
   WHERE a.slot_id = :slot_id
     AND a.quantity_available > 0
   ORDER BY i.priority_order ASC
   ```

2. **Subtract What Is Already Booked**
   - For each interpreter in the list: remaining capacity = quantity_available - ACTIVE positions already booked for this slot
   - Individuals already booked for this slot have no remaining capacity (no double-booking)
   - A bureau with remaining capacity gets extra positions on its existing booking

3. **Priority-Based Allocation**
   ```
   remaining = quantity_needed
   new_positions = []
   
   FOR each availability IN sorted_by_priority:
       IF remaining <= 0:
           BREAK
       
       can_book = MIN(remaining capacity of this interpreter, remaining)
       IF can_book <= 0:
           CONTINUE (skip)
       
       booking = existing booking for (interpreter, slot)
                 OR CREATE booking (status = PROPOSED)
       ADD can_book positions to booking
       ADD note "Priority #X, available Y, booked Z"

       IF meeting_id provided:
           FOR each new position:
               CREATE meeting assignment (position → meeting, status = PROPOSED)
       
       new_positions += the new positions
       remaining -= can_book
   ```

4. **Evaluate Result**
   - IF remaining = 0: Fully covered
   - IF remaining > 0: Insufficient capacity, flag for manual intervention

5. **Return**
   - List of PROPOSED bookings and their new positions
   - Remaining unfilled quantity
   - Audit log (who was considered, why selected/skipped)

**Output**: PROPOSED bookings and positions + staffing status

---

### 5.3 Meeting Assignment Process

**Objective**: Assign booked interpreters (positions) to a meeting.

**Input**: meeting_id

**Steps**:

1. **Determine Meeting Time Requirements**
   - Extract meeting.date, meeting.start_time, meeting.end_time
   - Find matching time slot: SELECT slot WHERE date = meeting.date AND start_time <= meeting.start_time AND end_time >= meeting.end_time
   - IF no matching slot exists: CREATE slot that encompasses meeting times

2. **Option A: Use Free Booked Positions**
   - Find positions in this slot that are free during the meeting:
     ```sql
     SELECT p.* FROM booking_positions p
     JOIN bookings b ON p.booking_id = b.booking_id
     JOIN interpreters i ON b.interpreter_id = i.interpreter_id
     WHERE b.slot_id = :slot_id
       AND b.status = 'CONFIRMED'
       AND p.status = 'ACTIVE'
       AND NOT EXISTS (
         SELECT 1 FROM meeting_assignments ma
         JOIN meetings m ON ma.meeting_id = m.meeting_id
         WHERE ma.position_id = p.position_id
           AND ma.assignment_status <> 'CANCELLED'
           AND m.start_time < :meeting_end_time
           AND m.end_time > :meeting_start_time
       )
     ORDER BY i.priority_order, p.position_number
     ```
   - These interpreters are already booked and have no conflicting meeting at that time
   - Create one assignment per position needed
   - If enough free positions exist: Done

3. **Option B: Book More Interpreters**
   - If there are not enough free positions:
     - Run Booking Creation Process (5.2) for this slot
     - quantity_needed = meeting.interpreters_needed - current staffing
     - Assign the new positions to the meeting

4. **Validate Staffing**
   - Staffing = number of CONFIRMED assignments for the meeting
   - IF staffing = meeting.interpreters_needed: FULLY_STAFFED
   - IF staffing < meeting.interpreters_needed: UNDERSTAFFED (flag)
   - IF staffing > meeting.interpreters_needed: OVERSTAFFED (warning)

**Output**: Meeting with assignments to positions, staffing status

---

### 5.4 Meeting Cancellation Process

**Objective**: Handle cancellation of a meeting while preserving bookings for potential reassignment. A cancellation never removes or cancels an assignment by itself (BR-MTG-010); the planner decides what happens to each one.

**Input**: a cancellation, which reaches PDC in one of three ways:
- it is made in spic and arrives with the update of the copy (1.3);
- the planner cancels a spic meeting in PDC, through spic's write route (1.4);
- the planner cancels an own meeting in PDC (1.5).

A meeting deleted in spic (status DELETED) follows the same process.

**Steps**:

1. **Record the Cancellation**
   - The meeting's status becomes CANCELLED (or DELETED); for a spic meeting the copy records spic's change number
   - Its assignments stay exactly as they were: nothing is removed, nothing is cancelled automatically
   - The meeting appears on the work list **cancelled with an assigned interpreter** as long as it has assignments that are not CANCELLED

2. **The Planner Handles Each Assignment**
   ```sql
   SELECT * FROM meeting_assignments
   WHERE meeting_id = :meeting_id
     AND assignment_status IN ('PROPOSED', 'CONFIRMED')
   ```
   - Cancel the assignment (assignment_status = CANCELLED, note "Meeting [name] cancelled on [date]"); positions and bookings remain intact
   - Each cancellation is a new entry in the assignment log, with a snapshot of the meeting (1.6)

3. **Evaluate Positions and Bookings**
   - For each position that had an assignment to this meeting:
     - IF the position has other meetings: nothing changes for that interpreter
     - IF the position has no other meetings: it is free for the whole block and can be dispatched elsewhere
   - For each booking whose positions all ended up without meetings:
     - Option A: Keep booking CONFIRMED (reserved capacity, available for reassignment)
     - Option B: Cancel booking (status = CANCELLED, interpreters get forfait)

4. **Reopening**
   - spic can reopen a cancelled meeting, and a deleted meeting can be restored with the same ID. Assignments that the planner has not cancelled are then valid again, and the meeting leaves the work list
   - Assignments that were cancelled stay cancelled; the planner makes new ones if needed

5. **Notify Interpreters**
   - The planner informs the interpreters; PDC sends no email itself
   - Positions with other meetings: "Meeting X cancelled, you still have Meeting Y in the same time block"
   - Positions without other meetings: "Meeting X cancelled, you remain booked; we will reassign you or pay the forfait"

**Output**: Cancelled meeting, assignments handled one by one by the planner and logged, preserved bookings and positions (available for new assignments)

---

## 6. Critical Business Scenarios

### 6.1 Scenario: Quarterly Planning with Generic Slots

**Context**: July, planning for September-December

**Steps**:

1. **Define Time Slots**
   - Create generic slots for expected meeting times
   - E.g., "Every Monday 14:00-17:00 in September"
   - 16 slots created (4 Mondays × 4 months)

2. **Collect Availability**
   - Send Google Form listing all 16 slots
   - Interpreters respond with availability for each slot
   - Import CSV → populate availability_declarations

3. **August: Meetings Confirmed**
   - Parliamentary calendar finalized in spic
   - The meetings reach PDC as their weeks become pre-definitive or definitive (1.3); the planner only adds own meetings and sets interpreters_needed
   - Match meetings to slots by datetime (by period when the time is still unknown, 2.7)

4. **Create Bookings**
   - For each meeting: run booking creation process
   - Assign the new positions to the meetings
   - Confirm bookings (status: PROPOSED → CONFIRMED)

5. **Notify Interpreters**
   - Generate weekly confirmations listing their bookings
   - Include meeting details now that meetings are known

**Key**: Availability collected BEFORE meetings finalized, bookings created AFTER.

### 6.2 Scenario: Emergency Meeting Added

**Context**: Thursday afternoon, urgent meeting tomorrow Friday 10:00-13:00

**Steps**:

0. **The Meeting Reaches PDC**
   - A Parliament meeting is created in spic and reaches PDC with the next update of the copy: when a PDC screen is opened, or within 5 minutes through the background task (1.3). It is visible only when its week is pre-definitive or definitive
   - A meeting without a report is not in spic: the secretary enters it in PDC as an own meeting (1.5)
   - The planner sets interpreters_needed

1. **Check Existing Slots**
   - SELECT slot WHERE date = '2025-11-01' AND start_time = '10:00'
   - Slot exists (from quarterly planning)

2. **Check Existing Availability**
   - SELECT * FROM availability_declarations WHERE slot_id = X AND quantity_available > 0
   - Interpreters already declared availability for this slot

3. **Check Free Positions**
   - Positions in CONFIRMED bookings for this slot that have no meeting between 10:00 and 13:00
   - These interpreters are already committed for the time block and can take the new meeting

4. **Two Paths**:
   
   **Path A: Free positions exist**
   - Assign them to the new meeting
   - Fast: No need to create new bookings

   **Path B: Not enough free positions**
   - Book more interpreters from availability (priority algorithm), adding positions to existing bureau bookings where possible
   - Assign the new positions to the meeting

5. **Urgent Notification**
   - Call interpreters (don't wait for email)
   - Confirm they can still make it tomorrow
   - Update booking status to CONFIRMED after verbal confirmation

**Key**: System can leverage existing availability and bookings even for last-minute meetings.

### 6.3 Scenario: Meeting Cancelled, Interpreter Reassigned Within Same Block

**Context**: Multiple meetings in Monday morning block, one cancels

**Steps**:

1. **Initial Setup**
   - Time slot: Monday 9:00-13:00
   - Booking: Interpreter A, Monday 9-13h, one position, status = CONFIRMED
   - Assignments:
     - Position 1 → Meeting A (9:00-10:30) → Assignment 1
     - Position 1 → Meeting B (11:00-12:30) → Assignment 2

2. **Friday: Meeting A Cancelled**
   - Meeting A is cancelled in spic (or by the planner in PDC, through spic's write route); with the next update of the copy it is marked CANCELLED
   - Assignment 1 is not touched automatically: Meeting A appears on the work list "cancelled with an assigned interpreter" (5.4)
   - The planner cancels Assignment 1: UPDATE meeting_assignments SET assignment_status = CANCELLED WHERE assignment_id = 1; the assignment log records it with a snapshot of Meeting A
   - Booking remains CONFIRMED (still has Meeting B)
   - Interpreter A still working Monday 9-13h (for Meeting B)

3. **Monday: New Urgent Meeting C Scheduled (10:00-11:00)** (arrives from spic, or entered as an own meeting)
   - Check position 1: booked 9-13h
   - Check conflicts: Meeting B (11:00-12:30)
   - Time window 10:00-11:00 is FREE (no overlap with Meeting B)
   - CREATE Assignment 3: Position 1 → Meeting C
   - Assignment 3 status = CONFIRMED

4. **Final State**
   - Booking: Still Monday 9-13h, CONFIRMED
   - Assignments:
     - Assignment 1 (Meeting A): CANCELLED
     - Assignment 2 (Meeting B 11:00-12:30): CONFIRMED
     - Assignment 3 (Meeting C 10:00-11:00): CONFIRMED
   - Interpreter works: Meeting C (10-11h), then Meeting B (11-12:30h)
   - Total: 2.5 hours actual work within 4-hour booking

5. **Payment**
   - Minimum: 4 hours (forfait for full booking)
   - Actual: 2.5 hours (but forfait guarantees 4h payment)

**Key**: One booking, multiple meetings, flexible reassignment within the time block.

### 6.4 Scenario: Bureau Bucket Dispatched Over Several Meetings

**Context**: A bureau is booked for three interpreters on Monday morning; the three are needed in different places.

**Steps**:

1. **Booking**
   - Bureau X declared 3 available for Monday 9:00-13:00
   - Booking: Bureau X, Monday 9-13h, positions 1, 2 and 3, status = CONFIRMED

2. **Meetings and Dispatching**
   - Meeting A (9:00-10:30) needs 2, Meeting B (9:30-11:00) needs 1, Meeting C (11:00-12:30) needs 3
   - Position 1 → A, then C
   - Position 2 → A, then C
   - Position 3 → B, then C
   - Check: no position has overlapping meetings (B ends at 11:00 when C starts); positions 1-2 and 3 overlap in time but are different people
   - A has 2, B has 1, C has 3 → all fully staffed

3. **Names**
   - Friday: the bureau says who comes
   - Position 1 = Sophie, position 2 = Marc, position 3 = Lisa

4. **Replacement**
   - Monday 7:30: Marc is ill, the bureau sends Thomas
   - Position 2: interpreter_name Marc → Thomas, note "replaces Marc (ill)"
   - Position 2's assignments to A and C are unchanged

5. **Cancellation**
   - Meeting B is cancelled in spic and appears on the planner's work list (5.4)
   - The planner cancels position 3's assignment to B; position 3 keeps C and is free 9:00-11:00
   - Urgent Meeting D (10:00-10:45) → position 3

6. **Actual Hours**
   - Meeting C runs late, until 13:30
   - Sophie and Thomas stay until 13:30; Lisa leaves at 12:30
   - Recorded per position: Sophie 9:00-13:30, Thomas 9:00-13:30, Lisa 10:00-12:30

7. **Invoice**
   - Early next month the bureau's invoice for the previous month comes in, with reference 2026-0412
   - The planner records the invoice once (bureau, reference, date received, month) and links positions 1, 2 and 3 to it, with the bureau's other services of that month
   - The invoice charges only two interpreters for Meeting C; the planner notes it on the invoice and follows it up
   - The linked positions leave the work list "invoice not received yet"

**Key**: One commitment to the bureau, three people dispatched independently, with names, replacements, hours and the invoice kept per person for the overview to HR.

---

## 7. Success Criteria

### 7.1 Conceptual Clarity
- Team understands distinction: AVAILABILITY (can work) ≠ BOOKING (will work) ≠ MEETING (event)
- A bureau booking is a bucket of positions; each position is one interpreter, dispatched on its own
- Workflows respect these separate lifecycles
- System design reflects these as independent entities

### 7.2 Operational Flexibility
- Can collect availability before meetings confirmed
- Can reassign booked interpreters when meetings cancel
- Can spread the interpreters of one bureau booking over different meetings
- Can handle three concurrent scheduling cycles (quarterly, weekly, emergency)
- Interpreter commitments honored even when meetings change

### 7.3 Legal Compliance
- Priority order enforced in booking creation
- Complete audit trail: availability → booking → position → meeting assignment, with the append-only assignment log and a snapshot of the meeting for every change (1.6)
- Documentation for all priority overrides

### 7.4 Efficiency Gains
- Current: 8-10 hours per cycle (manual matching, spreadsheets, conflicts)
- Target: < 1 hour per cycle (automated import, priority algorithm, booking management)
- Error rate: From ~10-15% to < 1%

---

## 8. Conclusion

The core insight of this system is the separation of distinct concepts:

1. **AVAILABILITY**: Interpreter capacity declaration for time blocks
2. **BOOKING**: Commitment to a supplier for a time block - one interpreter, or a bucket of N for a bureau
3. **BOOKING POSITION**: One interpreter within a booking, with the name of the person sent and the actual hours
4. **MEETING**: Specific event consuming booked capacity
5. **MEETING ASSIGNMENT**: Puts one position on one meeting

**The Relationships**:
- ONE booking has ONE or MORE positions
- ONE position (e.g., Monday 9-13h) can serve MULTIPLE non-overlapping meetings
- ONE meeting has MULTIPLE positions (one per interpreter needed), from one or several bookings

This separation enables:
- Collecting availability before meetings are fully defined
- Maintaining interpreter commitments when individual meetings cancel
- Dispatching each interpreter of a bureau booking independently
- Flexible reassignment of booked capacity within the same time block
- Accurate tracking of what was promised vs. what was delivered, per person
- Efficient use of booked time (fill empty slots with new meetings)

The system enforces legal priority obligations while providing operational flexibility to handle the reality of parliamentary scheduling, where meetings are planned in multiple overlapping cycles and details frequently change within booked time blocks.

---

## 9. Open Points

Not yet covered by this analysis:

1. **Confirmations**: the text per interpreter for a chosen period (default: a week starting Monday). Only mentioned in passing in scenario 6.1. Known requirements (4.5): the three or four hours, the start time of the meeting, the meeting for information only, no expected end, and the overrun clause in a box that stands out.
2. **Weekly overview for HR and monthly overview of prestations per interpreter**: referred to, not defined.
3. **Users, roles and the editing lock**:
   - *Editing lock* (decided 10 October 2026): **the editing lock goes.** Phase 1 locks the whole system for 4 hours while one editor dispatches, which conflicts with 1.4 (start time, room and cancellation at once, without a lock, also by another user). Instead, every action is one small transaction that checks, when saving, that the state still holds (the position is still free, the meeting still exists); if not, the user gets a clear message and the new state (then, now, your input). Conflicts only arise when two planners change the same position or meeting at the same moment, and the assignment log shows who did what.
   - *Login and roles* (decided 10 October 2026): PDC takes over the **identity from Authelia** (the headers `Remote-User`, `Remote-Name`, `Remote-Groups`, trusted only because the container is reachable only through Caddy), like spic; the own accounts and passwords of Phase 1 go. Everyone who enters data in spic or administers it (invoerders and beheerders) may manage PDC; there is no separate PDC role. spic keeps those lists in its administration screen, so spic gives them to PDC through a route with PDC's token (an addition to the contract). **PDC depends explicitly on Authelia and on spic.** What PDC does while that route does not exist yet is still to be decided. The name of the person goes with every write to spic ("via PDC", 1.4).
4. **Interpreter portal**: interpreters enter their own start and end times; the team lead validates them. Positions hold the times, but the entry and validation step is missing.
5. **Real duration of the meeting itself** (answered 10 October 2026): the meeting gets an optional real end according to our own staff and the number of half hours charged (2.7, BR-MTG-011).
6. **Interpreter becomes unavailable**: suggest the next interpreter in the priority list and record the communicated change. Only covered implicitly.
7. **Booking someone who did not respond to the form** (from the overall list): allowed, but not stated as a rule.
8. **BR-SRC-003** says "no overlap constraint", which contradicts the rule that the same meeting in two forms is a logical error and must be flagged.
9. **Meeting fields** (answered in 1.2): spic gives a start time (or "after another meeting", without a time), an optional entered end, and an estimated duration from the agenda or the meeting type; effective start and end can be empty; the period (AM/PM) is always present. Own meetings have a start plus an end or a duration (2.7). Still to confirm: how checks work when a time is missing (proposal in 2.7).
10. **Section 7.4**: the figures "8-10 hours per cycle" and "10-15% errors" are assumptions, not measured values. To be removed or replaced with real figures.
11. **Database** (decided 10 October 2026): **SQLite**, in WAL mode, like spic. Phase 1 still uses MySQL; there is no data to keep. The model of the copy and the assignment log is in `docs/pdc-voorstel.md` §2.
12. **Category of a spic meeting**: PDC's categories must be derived from spic's domain, assembly and type. Not designed yet; Phase 1's four categories (Parliament, affiliated organization, external group, special event) remain for own meetings until then.
13. **Events and coordinators**: spic also has events (blocks with an ID starting with `e-`, without a report) and a coordinator per day. Whether PDC needs them has not been discussed.
14. **Own response form for the interpreters** (idea, nothing decided): like Google Forms now, but PDC's own. One link per round with a long, unguessable code, which the planner sends out by email; the interpreter identifies with their email address or ID; only known interpreters are accepted; a new answer from the same interpreter replaces the previous one until the closing date. **No email from the system** (no mail server or service): the planner can copy "all addresses" and "addresses of those who did not answer yet" into their own mail program. Answers go straight into the database, so the CSV import (2.8, 5.1) would disappear. Still to settle: a public route in `CAL` (only `/antwoord/...`, the rest stays behind Authelia; `CAL` is changed only when the user explicitly asks), protection against abuse, and whether interpreters outside the building can reach the server from the internet.
15. **An own meeting that turns up in spic**: linking it to the spic meeting later. Open.
16. **spic's list of rooms**: PDC needs spic's fixed list of rooms (for own meetings and to show room names). The export described in FA Opnamebeheer §13.2 does not mention code lists yet; to be agreed with the spic session.
17. **The planner's spreadsheet** (`TOLKENPLANNING_2026-2027.xlsx`, seen on 10 October 2026; it holds real personal data and never goes into the repository). One sheet per week (sheets for recess weeks are named "SCHORSING" or "GESLOTEN"), five days, two columns of meetings per day; per meeting a block of rows: time, meeting, Tolk 1, Tolk 2, Tolk 3 (plenary only), with the bureau in brackets after the name of the interpreter it sends. Next to each row a column "FACT. of DIM". What it showed, and where it is now in this model:
    - Meetings are spic's committee codes, plenary sessions and (extended) bureau, plus events that are not in spic (an animation in the hemicycle, a visit): confirms 1.1 and the own meetings.
    - Times are free text ("09.30 - 12.30", "11.00", "14.30 - finish", "?"): end times are often unknown, as in 2.7.
    - "FACT. of DIM" next to an interpreter holds the invoice number, "ok", "DIM" or "DIM / ok": invoice or occasional work with a Dimona declaration, a property of the interpreter (2.1, 2.5), and the invoice (2.9). Next to a meeting it sometimes holds one invoice number for the whole meeting.
    - Next to the time: "forfait 3u", "forfait 3u + overuren": the forfait of the booking, 3 or 4 hours for everyone, with overtime added per half hour (2.4, BR-BKG-009). "bloc 3" and "bloc 4" appear from week 42 on, on meetings of 3 and 4 hours (e.g. 9:00 - 12:00 "bloc 3"): the booking of three or four hours that the instructions of September 2026 ask to state (4.5, BR-INS-001).
    - "annulation transmise dd/mm" next to an interpreter: when the cancellation was passed on (2.6).
    - "nom à confirmer": the bureau has not given the name yet (2.5, interpreter_name). Names struck through: an interpreter replaced or cancelled; PDC keeps that in the position's notes and the log. Cell comments note reasons ("ill", "time changed on 30/9") and invoice discrepancies ("only one interpreter charged on the September invoice").
    - A memo sheet holds a request from another department of the Parliament for interpreters at an event it organises, at the Parliament's expense (1.5).

    Still open: whether "ok" means received and checked (to be confirmed with the staff); and whether the bookings and invoices already in this spreadsheet for 2026-2027 must be imported into PDC, or PDC starts from a given week (spic's meetings arrive on their own).
