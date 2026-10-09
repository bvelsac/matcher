# Functional Analysis
## Interpreter Mission Management System

**Version:** 1.0  
**Date:** November 2025  
**Document Type:** Conceptual Model & Business Rules

---

## 1. Domain Overview

The system manages the reservation and allocation of interpreters across time periods, matching their declared availability with meetings that require interpretation services. The fundamental principle is that **availabilities are declared for time slots**, **bookings reserve interpreter capacity**, and **meetings consume booked capacity** - but these three concepts remain distinct to handle the reality that meetings may be cancelled, rescheduled, or added after availabilities are collected.

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

**Definition**: A confirmed or proposed reservation of interpreter capacity for a specific time slot, which may or may not be linked to a meeting.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `booking_id` | Integer | Primary key, unique | System identifier |
| `interpreter_id` | Integer | Foreign key, required | Who is booked |
| `slot_id` | Integer | Foreign key, required | Which time slot (e.g., Monday 9:00-13:00) |
| `quantity_booked` | Integer | Required, > 0 | Number of interpreters reserved |
| `status` | Enum | Required | PROPOSED, CONFIRMED, COMPLETED, CANCELLED |
| `booking_reason` | String | Optional | Why booked if no meetings assigned yet |
| `assigned_individuals` | Text | Optional | For bureaus: names of specific interpreters sent |
| `actual_start_time` | DateTime | Optional | When work actually began (first meeting) |
| `actual_end_time` | DateTime | Optional | When work actually ended (last meeting) |
| `notes` | Text | Optional | Administrative notes, override reasons |
| `created_at` | DateTime | System-generated | When booking created |
| `updated_at` | DateTime | System-maintained | Last modification |
| `created_by` | Integer | Foreign key to User | Who created this booking |

**Business Rules**:
- **BR-BKG-001**: quantity_booked must be <= availability.quantity_available (if availability exists)
- **BR-BKG-002**: For INDIVIDUAL interpreters, quantity_booked must equal 1
- **BR-BKG-003**: For BUREAU interpreters, quantity_booked can be 1, 2, 3, ... up to their capacity
- **BR-BKG-004**: Status transitions: PROPOSED → CONFIRMED → COMPLETED, or → CANCELLED from any state
- **BR-BKG-005**: A booking reserves capacity for a time block (e.g., Monday 9-13h)
- **BR-BKG-006**: Multiple meetings can be assigned to one booking (via Meeting Assignment records)
- **BR-BKG-007**: Cannot have two CONFIRMED bookings for same interpreter with overlapping time slots
- **BR-BKG-008**: If status = COMPLETED, actual_start_time and actual_end_time should be populated

**Derived Properties**:
- `actual_duration_hours`: (actual_end_time - actual_start_time) in hours if completed
- `assigned_meeting_count`: Count of meetings assigned to this booking
- `has_meetings`: TRUE if any meetings are assigned
- `slot_datetime`: Combined date and time from related slot

**Invariants**:
- An interpreter cannot have overlapping CONFIRMED bookings (same or overlapping time slots)
- All meetings assigned to a booking must fall within the booking's time slot
- Meetings assigned to the same booking must not overlap with each other

**Key Insight**:
A booking is a commitment to a TIME BLOCK (e.g., "Monday morning 9-13h"). Within that block, the interpreter can work multiple non-overlapping meetings. If one meeting cancels, the interpreter remains booked and available for other meetings in that time block.

---

### 2.5 Meeting Assignment

**Definition**: The assignment of a booking to a specific meeting - represents that during the booked time block, the interpreter will work this particular meeting.

**Properties**:

| Property | Type | Constraint | Description |
|----------|------|------------|-------------|
| `assignment_id` | Integer | Primary key, unique | System identifier |
| `booking_id` | Integer | Foreign key, required | Which booking provides the capacity |
| `meeting_id` | Integer | Foreign key, required | Which meeting consumes the capacity |
| `assignment_status` | Enum | Required | PROPOSED, CONFIRMED, CANCELLED |
| `notes` | Text | Optional | Assignment-specific notes |
| `created_at` | DateTime | System-generated | When assignment created |
| `created_by` | Integer | Foreign key to User | Who created this assignment |

**Business Rules**:
- **BR-ASGN-001**: The meeting must fall within the booking's time slot
- **BR-ASGN-002**: Cannot assign overlapping meetings to the same booking (interpreter can't be in two places at once)
- **BR-ASGN-003**: If booking status = CANCELLED, all assignments must also be CANCELLED
- **BR-ASGN-004**: An assignment can be cancelled without cancelling the booking (e.g., meeting cancelled, booking preserved)
- **BR-ASGN-005**: Assignment status cannot be CONFIRMED if booking status is not CONFIRMED

**Derived Properties**:
- `interpreter_id`: Retrieved from booking.interpreter_id
- `time_conflict`: TRUE if this meeting overlaps with another meeting assigned to same booking

**Invariants**:
- All meetings assigned to a booking via assignments must be non-overlapping
- Assignment can only exist if booking exists
- Meeting datetime must be within booking's slot datetime range

**Key Insight**:
This junction entity enables ONE booking to serve MULTIPLE meetings. Example:
- Booking: Monday 9:00-13:00 (4-hour block)
- Assignment 1: Booking → Meeting A (9:00-10:30)
- Assignment 2: Booking → Meeting B (11:00-12:30)
- Interpreter works both meetings under one booking commitment

---

### 2.6 Meeting

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
- **BR-MTG-003**: A meeting is staffed through Meeting Assignments that link it to bookings (see 2.5)

**Derived Properties**:
- `datetime_start`: date + start_time combined
- `datetime_end`: date + end_time combined
- `staffing_count`: Sum of quantity_booked of the bookings linked to this meeting by CONFIRMED meeting assignments
- `staffing_status`: 
  - UNSTAFFED if staffing_count = 0
  - UNDERSTAFFED if staffing_count < interpreters_needed
  - FULLY_STAFFED if staffing_count = interpreters_needed
  - OVERSTAFFED if staffing_count > interpreters_needed

**Relationship to Time Slots**:
- A meeting typically aligns with a time slot or portion of a slot
- Multiple meetings can occur within the same time slot if non-overlapping
- When collecting availability, we create slots for expected meeting times

**Relationship to Bookings**:
- A meeting is staffed via Meeting Assignments
- One meeting can have multiple assignments (multiple interpreters)
- Each assignment links the meeting to a booking
- The booking provides the interpreter capacity

**Key Insight**:
Meetings are downstream consumers of booked capacity. The sequence is:
1. Declare availability for time slots
2. Create bookings from availability (reserves capacity for time blocks)
3. Create/identify meetings
4. Create assignments linking bookings to meetings (assign capacity to specific events)
5. If a meeting cancels, remove its assignments but preserve bookings for reassignment

---

### 2.7 CSV Data Source

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

### 3.1 The Availability → Booking → Meeting Assignment Flow

```
INTERPRETER
    |
    | declares capacity for
    ↓
TIME SLOT ← describes time block (e.g., Monday 9:00-13:00)
    |
    | referenced by
    ↓
AVAILABILITY DECLARATION (I CAN work Monday 9-13h, qty: 2)
    |
    | transforms into (when selected by priority algorithm)
    ↓
BOOKING (I WILL work Monday 9-13h, qty: 2, status: CONFIRMED)
    |
    | can be assigned to multiple meetings via
    ↓
MEETING ASSIGNMENT ← links → MEETING (Event 9:00-10:30)
MEETING ASSIGNMENT ← links → MEETING (Event 11:00-12:30)
MEETING ASSIGNMENT ← links → MEETING (Event 12:30-13:00)
```

**Key Principle**: ONE booking (time block) can serve MULTIPLE meetings (events within that block).

### 3.2 The Independence Principle

**Why separate availability, booking, and meeting?**

**Scenario 1: Meeting cancellation within booked block**
- Monday 9:00-13:00 time slot
- Bureau Tradho declared available (qty: 2)
- Booking created: Tradho, Monday 9-13h, qty: 2, status: CONFIRMED
- Assignments:
  - Meeting A (9:00-10:30) → Assignment A
  - Meeting B (11:00-12:30) → Assignment B
- Friday: Meeting A CANCELLED
- **Result**:
  - Delete Assignment A
  - Keep Assignment B (Meeting B still happens)
  - Booking remains CONFIRMED (interpreter commitment for full 9-13h block)
  - Can create new Assignment C for different meeting in 9-11h window

**Scenario 2: Entire booked block no longer needed**
- Same booking, both Meeting A and B cancel
- Delete both assignments
- Booking remains CONFIRMED (no meetings assigned)
- Options:
  - Find new meetings for this time block
  - Or: Cancel booking (interpreter gets forfait for blocked time)

**Scenario 3: Availability before meetings confirmed**
- July: Collect availability for "Monday mornings 9-13h" throughout September
- Interpreters declare: "I can work Sept 15, 9-13h"
- August: Create bookings from availability
- September: Meetings finalized, create assignments linking bookings to specific meetings
- Interpreter may work 1, 2, or 3 meetings during their 9-13h booking

**Scenario 4: Emergency meeting fits into existing booking**
- Existing booking: Monday 9-13h, assigned to Meeting A (9:00-10:30)
- Tuesday: Urgent Meeting B scheduled for Monday 11:00-12:00
- Check: Same booking has free time 11:00-13:00
- Create new assignment: Booking → Meeting B
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
    (Meeting occurs, work performed)
         ↓
    COMPLETED BOOKING (actual times logged)

Alternative path:
    CONFIRMED → CANCELLED (interpreter sick, meeting cancelled, etc.)
    PROPOSED → CANCELLED (decided not to use)
```

**Critical State Properties**:

- **PROPOSED**: No commitment yet, can be freely deleted/modified
- **CONFIRMED**: Commitment exists, interpreter expects work and payment
- **COMPLETED**: Work done, payment calculated
- **CANCELLED**: Was committed, no longer valid (still tracks for audit)

### 3.4 The Booking-Meeting Relationship (Many-to-Many)

**One Booking → Many Meetings**
- A booking reserves a time block (e.g., Monday 9:00-13:00)
- Multiple non-overlapping meetings can occur within that block
- Each meeting is linked via a Meeting Assignment
- Example: Booking (9-13h) → Meeting A (9-10:30) + Meeting B (11-12) + Meeting C (12:30-13)

**One Meeting → Many Bookings**
- A meeting needing 4 interpreters has 4 bookings assigned to it
- Each booking represents one interpreter (or one bureau slot)
- Sum of booking quantities should equal meeting.interpreters_needed
- Example: Meeting X → Booking 1 (Interpreter A) + Booking 2 (Interpreter B) + Booking 3 (Bureau C, qty=2)

**Many-to-Many Implementation**:
- Meeting Assignment is the junction table
- Enables flexible assignment and reassignment
- Supports partial cancellations (one meeting cancels, others remain)

**Assignment Rules**:
- Meetings assigned to same booking MUST NOT overlap temporally
- All meetings assigned to a booking MUST fall within the booking's time slot
- If booking is CANCELLED, all its assignments are CANCELLED
- If a meeting is CANCELLED, only that meeting's assignments are removed

**Reassignment Scenario**:
```
Initial:
- Booking: Mon 9-13h, Interpreter X
- Assignments: Meeting A (9-11h)

Meeting A cancels:
- Delete Assignment (Booking → Meeting A)
- Booking still exists, free capacity 9-13h

New meeting added:
- Meeting D (10-12h) scheduled
- Create Assignment (Booking → Meeting D)
- Reuses same booking

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
bookings_created = []

FOR each availability IN sorted_by_priority:
    IF remaining_need <= 0:
        BREAK
    
    can_book = MIN(availability.quantity_available, remaining_need)
    
    CREATE booking:
        interpreter_id = availability.interpreter_id
        slot_id = availability.slot_id
        quantity_booked = can_book
        status = PROPOSED

    IF staffing a meeting:
        CREATE meeting assignment (booking → meeting, status = PROPOSED)
    
    bookings_created.append(booking)
    remaining_need -= can_book

RETURN bookings_created, remaining_need
```

**BR-BOOK-003: Partial Fulfillment**
- If Priority #2 (bureau) has quantity_available = 2, but remaining_need = 5
- Book all 2 from Priority #2
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
- Cannot create CONFIRMED booking if interpreter already has CONFIRMED booking for overlapping time slot
- Check: SELECT bookings WHERE interpreter_id = X AND status = CONFIRMED AND slot overlaps
- Overlapping slots = same date + time ranges intersect

**BR-VAL-002: Capacity Limits**
- For INDIVIDUAL: quantity_booked must = 1
- For BUREAU: quantity_booked must <= quantity_available (if availability exists)
- Cannot book more than declared capacity

**BR-VAL-003: Status Transition Validation**
- PROPOSED → CONFIRMED: Allowed
- PROPOSED → CANCELLED: Allowed
- CONFIRMED → COMPLETED: Allowed only after slot.datetime_end has passed
- CONFIRMED → CANCELLED: Allowed with reason
- COMPLETED → any: Not allowed (terminal state)
- Any → PROPOSED: Not allowed (cannot uncommit)

**BR-VAL-004: Meeting Assignment Validation**
- When creating assignment linking booking to meeting:
  - Meeting datetime must fall within booking's time slot
  - Meeting must not overlap with other meetings assigned to same booking
- Check for temporal conflicts:
  ```sql
  SELECT * FROM meeting_assignments ma
  JOIN meetings m ON ma.meeting_id = m.meeting_id
  WHERE ma.booking_id = X
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
- A meeting's staffing is the sum of quantity_booked of the bookings linked to it by meeting assignments
- Count only CONFIRMED or COMPLETED assignments
- PROPOSED assignments don't count toward staffing
- CANCELLED assignments don't count

**BR-STAFF-002: Staffing Threshold**
- FULLY_STAFFED: staffing = meeting.interpreters_needed
- UNDERSTAFFED: staffing < needed
- OVERSTAFFED: staffing > needed (warning, but allowed)

**BR-STAFF-003: Unassigned Meeting Creation**
- Can create meeting even if no assignments exist yet
- Meeting starts in UNSTAFFED status
- Workflow: Create meeting → Match to time slot → Create bookings from availability → Create assignments linking bookings to meeting

**BR-STAFF-004: Assignment Flexibility**
- One booking can serve multiple meetings (via multiple assignments)
- If Meeting A cancels: Delete assignment, keep booking, booking available for other meetings
- If entire booking no longer needed: Cancel booking (all assignments also cancelled)

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

**Objective**: Create bookings from availability declarations for a time slot, optionally assigning them to a meeting.

**Input**:
- slot_id (which time slot)
- quantity_needed (how many interpreters)
- meeting_id (optional: if the bookings should be assigned to a specific meeting)

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

2. **Check Existing Bookings**
   - For each interpreter in availability list:
     - Check if they already have CONFIRMED booking for this slot
     - If yes: Exclude from available pool (no double-booking)

3. **Priority-Based Allocation**
   ```
   remaining = quantity_needed
   proposed_bookings = []
   
   FOR each availability IN sorted_by_priority:
       IF remaining <= 0:
           BREAK
       
       IF interpreter already has confirmed booking for this slot:
           CONTINUE (skip)
       
       can_book = MIN(availability.quantity_available, remaining)
       
       CREATE booking (status = PROPOSED):
           interpreter_id
           slot_id
           quantity_booked = can_book
           notes = "Priority #X, available Y, booked Z"

       IF meeting_id provided:
           CREATE meeting assignment (booking → meeting, status = PROPOSED)
       
       proposed_bookings.append(booking)
       remaining -= can_book
   ```

4. **Evaluate Result**
   - IF remaining = 0: Fully covered
   - IF remaining > 0: Insufficient capacity, flag for manual intervention

5. **Return**
   - List of PROPOSED bookings
   - Remaining unfilled quantity
   - Audit log (who was considered, why selected/skipped)

**Output**: Set of PROPOSED bookings + staffing status

---

### 5.3 Meeting Assignment Process

**Objective**: Create assignments linking bookings to a meeting.

**Input**: meeting_id

**Steps**:

1. **Determine Meeting Time Requirements**
   - Extract meeting.date, meeting.start_time, meeting.end_time
   - Find matching time slot: SELECT slot WHERE date = meeting.date AND start_time <= meeting.start_time AND end_time >= meeting.end_time
   - IF no matching slot exists: CREATE slot that encompasses meeting times

2. **Option A: Use Existing Bookings**
   - Find bookings at this slot that have free capacity:
     ```sql
     SELECT b.* FROM bookings b
     WHERE b.slot_id = :slot_id
       AND b.status = CONFIRMED
       AND NOT EXISTS (
         SELECT 1 FROM meeting_assignments ma
         JOIN meetings m ON ma.meeting_id = m.meeting_id
         WHERE ma.booking_id = b.booking_id
         AND m.start_time < :meeting_end_time
         AND m.end_time > :meeting_start_time
       )
     ```
   - These bookings have no conflicting meeting during the target time
   - Create assignments linking these bookings to the meeting
   - If sufficient bookings exist: Done

3. **Option B: Create New Bookings**
   - If insufficient existing bookings with free capacity:
     - Run Booking Creation Process (5.2) for this slot
     - quantity_needed = meeting.interpreters_needed - current staffing
     - Create new bookings
     - Create assignments linking new bookings to meeting

4. **Validate Staffing**
   - Staffing = sum of quantity_booked over bookings linked by CONFIRMED assignments
   - IF staffing = meeting.interpreters_needed: FULLY_STAFFED
   - IF staffing < meeting.interpreters_needed: UNDERSTAFFED (flag)
   - IF staffing > meeting.interpreters_needed: OVERSTAFFED (warning)

**Output**: Meeting with assignments linking it to bookings, staffing status

---

### 5.4 Meeting Cancellation Process

**Objective**: Handle cancellation of a meeting while preserving bookings for potential reassignment.

**Input**: meeting_id

**Steps**:

1. **Find Meeting Assignments**
   ```sql
   SELECT * FROM meeting_assignments
   WHERE meeting_id = :meeting_id
     AND assignment_status IN (PROPOSED, CONFIRMED)
   ```

2. **Cancel Assignments**
   - UPDATE meeting_assignments SET assignment_status = CANCELLED WHERE meeting_id = :meeting_id
   - ADD note: "Meeting [name] cancelled on [date]"
   - Assignments are removed/cancelled, but bookings remain intact

3. **Evaluate Booking Status**
   - For each booking that had assignments to this meeting:
     - Check if booking has OTHER assignments (to different meetings)
     - IF booking has other meetings: Keep booking CONFIRMED
     - IF booking has NO other meetings:
       - Option A: Keep booking CONFIRMED (reserved capacity, available for reassignment)
       - Option B: Cancel booking (status = CANCELLED, interpreter gets forfait)

4. **Mark Meeting as Cancelled**
   - UPDATE meetings SET status = CANCELLED (or delete)
   - Retain in audit log

5. **Notify Interpreters**
   - For bookings with other meetings: "Meeting X cancelled, you still have Meeting Y and Z in same time block"
   - For bookings with no other meetings: "Meeting X cancelled, you remain booked, will reassign or pay forfait"

**Output**: Cancelled assignments, preserved bookings (available for new assignments)

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
   - Create meeting assignments linking the bookings to the meetings
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

3. **Check Existing Bookings**
   - CONFIRMED bookings for this slot whose meeting assignments leave 10:00-13:00 free
   - These interpreters are already committed for the time block and can take the new meeting

4. **Two Paths**:
   
   **Path A: Bookings with free time exist**
   - Reuse: create meeting assignments from those bookings to the new meeting
   - Fast: No need to create new bookings

   **Path B: No suitable bookings exist**
   - Create new bookings from availability
   - Run priority algorithm
   - Assign the new bookings to the meeting

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
   - Booking: Interpreter A, Monday 9-13h, status = CONFIRMED
   - Assignments:
     - Meeting A (9:00-10:30) → Assignment 1
     - Meeting B (11:00-12:30) → Assignment 2

2. **Friday: Meeting A Cancelled**
   - Cancel Assignment 1: UPDATE meeting_assignments SET assignment_status = CANCELLED WHERE assignment_id = 1
   - Meeting A marked CANCELLED
   - Booking remains CONFIRMED (still has Meeting B)
   - Interpreter A still working Monday 9-13h (for Meeting B)

3. **Monday: New Urgent Meeting C Scheduled (10:00-11:00)**
   - Check booking: Interpreter A booked 9-13h
   - Check conflicts: Meeting B (11:00-12:30)
   - Time window 10:00-11:00 is FREE (no overlap with Meeting B)
   - CREATE Assignment 3: Booking → Meeting C
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

---

## 7. Success Criteria

### 7.1 Conceptual Clarity
- Team understands distinction: AVAILABILITY (can work) ≠ BOOKING (will work) ≠ MEETING (event)
- Workflows respect these separate lifecycles
- System design reflects these as independent entities

### 7.2 Operational Flexibility
- Can collect availability before meetings confirmed
- Can reassign bookings when meetings cancel
- Can handle three concurrent scheduling cycles (quarterly, weekly, emergency)
- Interpreter commitments honored even when meetings change

### 7.3 Legal Compliance
- Priority order enforced in booking creation
- Complete audit trail: availability → booking → meeting assignment
- Documentation for all priority overrides

### 7.4 Efficiency Gains
- Current: 8-10 hours per cycle (manual matching, spreadsheets, conflicts)
- Target: < 1 hour per cycle (automated import, priority algorithm, booking management)
- Error rate: From ~10-15% to < 1%

---

## 8. Conclusion

The core insight of this system is the separation of three distinct concepts with a many-to-many relationship:

1. **AVAILABILITY**: Interpreter capacity declaration for time blocks
2. **BOOKING**: Reservation of interpreter time for a time block (commitment)
3. **MEETING**: Specific event consuming booked capacity
4. **MEETING ASSIGNMENT**: Junction linking bookings to meetings (many-to-many)

**The Critical Many-to-Many Relationship**:
- ONE booking (e.g., Monday 9-13h) can serve MULTIPLE meetings (9-10:30h, 11-12h)
- ONE meeting can have MULTIPLE bookings (multiple interpreters assigned)
- This enables maximum flexibility for reassignment when meetings cancel or change

This separation enables:
- Collecting availability before meetings are fully defined
- Maintaining interpreter commitments when individual meetings cancel
- Flexible reassignment of booked capacity within the same time block
- Accurate tracking of what was promised vs. what was delivered
- Efficient use of booked time (fill empty slots with new meetings)

The system enforces legal priority obligations while providing operational flexibility to handle the reality of parliamentary/governmental scheduling where meetings are planned in multiple overlapping cycles and details frequently change within booked time blocks.
