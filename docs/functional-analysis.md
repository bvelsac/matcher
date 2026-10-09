# Functional Analysis
## Interpreter Mission Management System

**Version:** 1.1  
**Date:** October 2026  
**Document Type:** Conceptual Model & Business Rules

> **1.1:** a booking is now a bucket of positions, one per interpreter, so that the
> interpreters of one bureau booking can each be dispatched to meetings independently
> (new section 2.5, scenario 6.4). Actual hours and the name of the person sent are kept
> per position.

---

## 1. Domain Overview

The system manages the reservation and allocation of interpreters across time periods, matching their declared availability with meetings that require interpretation services. The fundamental principle is that **availabilities are declared for time slots**, **bookings reserve interpreter capacity**, and **meetings consume booked capacity** - but these concepts remain distinct to handle the reality that meetings may be cancelled, rescheduled, or added after availabilities are collected.

A booking is the commitment towards the supplier (an individual interpreter or a bureau). Inside a booking, every interpreter is a separate **booking position**, and it is positions - not whole bookings - that are dispatched to meetings. A bureau booked for three interpreters is a bucket of three positions; each of the three can go to a different meeting.

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

**Business Rules**:
- **BR-POS-001**: A position belongs to exactly one booking; position_number is unique within that booking
- **BR-POS-002**: Meetings assigned to one position must not overlap (one person cannot be in two places)
- **BR-POS-003**: Different positions of the same booking may be assigned to the same meeting or to overlapping meetings - they are different people
- **BR-POS-004**: When a bureau replaces the person on a position (illness, schedule change), only interpreter_name changes; the position's meeting assignments remain valid. The change is recorded in notes
- **BR-POS-005**: Cancelling a position (the bureau cannot send that interpreter after all) cancels its meeting assignments; the affected meetings become understaffed and are flagged
- **BR-POS-006**: interpreter_name must be filled in before the booking is COMPLETED (needed for the overview to HR)
- **BR-POS-007**: Actual hours are recorded per position, because interpreters at the same meeting can work different hours (one stays longer than another)

**Derived Properties**:
- `interpreter_id`: From the booking (the individual or the bureau, whose priority applies)
- `assigned_meetings`: Meetings linked to this position by non-cancelled assignments
- `free_periods`: Parts of the booking's time block not covered by an assigned meeting
- `actual_duration_hours`: (actual_end_time - actual_start_time) in hours

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
| `created_at` | DateTime | System-generated | When assignment created |
| `created_by` | Integer | Foreign key to User | Who created this assignment |

**Business Rules**:
- **BR-ASGN-001**: The meeting must fall within the time slot of the position's booking
- **BR-ASGN-002**: Cannot assign overlapping meetings to the same position
- **BR-ASGN-003**: If the booking or the position is CANCELLED, its assignments are CANCELLED
- **BR-ASGN-004**: An assignment can be cancelled without cancelling the position or booking (e.g., meeting cancelled, interpreter stays booked)
- **BR-ASGN-005**: Assignment status cannot be CONFIRMED if booking status is not CONFIRMED
- **BR-ASGN-006**: A position can be assigned to a given meeting only once; each assignment puts exactly one interpreter on one meeting

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

**Definition**: A scheduled event requiring interpretation services, which consumes booked interpreter capacity.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `meeting_id` | Integer | Primary key, unique | System identifier |
| `name` | String | Required | Meeting title/description |
| `date` | Date | Required | Calendar date of meeting |
| `start_time` | Time | Required | Meeting start time |
| `end_time` | Time | Required | Meeting end time |
| `interpreters_needed` | Integer | Required, > 0 | Number of interpreters required |
| `location` | String | Required | Physical or virtual location |
| `category` | Enum | Required | PARLIAMENT, AFFILIATED_ORGANIZATION, EXTERNAL_GROUP, SPECIAL_EVENT |
| `estimated_duration` | Integer | Derived | Duration in hours |
| `created_at` | DateTime | System-generated | Timestamp of creation |
| `updated_at` | DateTime | System-maintained | Timestamp of last modification |
| `created_by` | Integer | Foreign key to User | Who created this meeting |

**Business Rules**:
- **BR-MTG-001**: start_time must be < end_time
- **BR-MTG-002**: estimated_duration = end_time - start_time (in hours)
- **BR-MTG-003**: A meeting is staffed through Meeting Assignments (2.6), each putting one interpreter (one booking position) on the meeting

**Derived Properties**:
- `datetime_start`: date + start_time combined
- `datetime_end`: date + end_time combined
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
3. Create/identify meetings
4. Assign positions to meetings
5. If a meeting cancels, cancel its assignments but keep the bookings and positions for reassignment

---

### 2.8 CSV Data Source

**Definition**: A configured external source providing availability declarations via HTTP-accessible CSV file.

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
- Bureau Tradho declared available (qty: 3)
- Booking created: Tradho, Monday 9-13h, 3 positions, status: CONFIRMED
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
- If a meeting is CANCELLED, only that meeting's assignments are cancelled

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
- If Meeting A cancels: Cancel its assignments, keep the positions, which become available for other meetings
- If a whole booking is no longer needed: Cancel booking (all positions and assignments also cancelled)

---

## 5. Key Processes

### 5.1 Availability Collection Process

**Objective**: Import interpreter availability declarations for time slots from external CSV sources.

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

**Objective**: Handle cancellation of a meeting while preserving bookings for potential reassignment.

**Input**: meeting_id

**Steps**:

1. **Find Meeting Assignments**
   ```sql
   SELECT * FROM meeting_assignments
   WHERE meeting_id = :meeting_id
     AND assignment_status IN ('PROPOSED', 'CONFIRMED')
   ```

2. **Cancel Assignments**
   - UPDATE meeting_assignments SET assignment_status = CANCELLED WHERE meeting_id = :meeting_id
   - ADD note: "Meeting [name] cancelled on [date]"
   - Positions and bookings remain intact

3. **Evaluate Positions and Bookings**
   - For each position that had an assignment to this meeting:
     - IF the position has other meetings: nothing changes for that interpreter
     - IF the position has no other meetings: it is free for the whole block and can be dispatched elsewhere
   - For each booking whose positions all ended up without meetings:
     - Option A: Keep booking CONFIRMED (reserved capacity, available for reassignment)
     - Option B: Cancel booking (status = CANCELLED, interpreters get forfait)

4. **Mark Meeting as Cancelled**
   - UPDATE meetings SET status = CANCELLED (or delete)
   - Retain in audit log

5. **Notify Interpreters**
   - Positions with other meetings: "Meeting X cancelled, you still have Meeting Y in the same time block"
   - Positions without other meetings: "Meeting X cancelled, you remain booked; we will reassign you or pay the forfait"

**Output**: Cancelled assignments, preserved bookings and positions (available for new assignments)

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
   - Parliamentary calendar finalized
   - Create specific meetings (names, locations, categories)
   - Match meetings to slots by datetime

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
   - Cancel Assignment 1: UPDATE meeting_assignments SET assignment_status = CANCELLED WHERE assignment_id = 1
   - Meeting A marked CANCELLED
   - Booking remains CONFIRMED (still has Meeting B)
   - Interpreter A still working Monday 9-13h (for Meeting B)

3. **Monday: New Urgent Meeting C Scheduled (10:00-11:00)**
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
   - Meeting B is cancelled
   - Position 3's assignment to B is cancelled; position 3 keeps C and is free 9:00-11:00
   - Urgent Meeting D (10:00-10:45) → position 3

6. **Actual Hours**
   - Meeting C runs late, until 13:30
   - Sophie and Thomas stay until 13:30; Lisa leaves at 12:30
   - Recorded per position: Sophie 9:00-13:30, Thomas 9:00-13:30, Lisa 10:00-12:30

**Key**: One commitment to the bureau, three people dispatched independently, with names, replacements and hours kept per person for the overview to HR.

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
- Complete audit trail: availability → booking → position → meeting assignment
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
