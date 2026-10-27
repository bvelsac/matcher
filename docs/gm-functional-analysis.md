# Functional Analysis
## GM planning: booking occasional staff for Verslaggeving (working title)

**Version:** 0.3 (draft for review)  
**Date:** 27 October 2026  
**Document Type:** Conceptual Model & Business Rules

> This application helps the planner of the Verslaggeving directorate decide how many occasional
> staff members (gelegenheidsmedewerkers, **GM**) to book, and on which half-days, in which language
> and role. It is the "similar application for another category of freelancers" announced in the
> functional analysis of PDC (section 1): a separate application with its own database, built on the
> same foundations as PDC. Everything in this version was decided by the user between 18 and
> 26 October 2026 unless it is marked as a proposal or listed in section 10.

**Terms used in this document**

| Term | Meaning |
|------|---------|
| GM | Occasional staff member (gelegenheidsmedewerker): works for Verslaggeving on half-days for which they offered themselves and were booked; occasional work with a Dimona declaration |
| staff | The permanent staff of Verslaggeving, whose presence is planned in the jaarkalender |
| half-day | AM or PM of a working day (dagdeel) |
| role | redacteur, revisor, hoofdredacteur or vertaler. One person does one role per half-day |
| spic | The planning of the meetings (repository `bvelsac/crystalclear`); source of the workload |
| JK | The jaarkalender (repository `bvelsac/infracriv`, folder `jaarkalender`); source of the presence of the staff |
| deadline | spic's deadline (termijn) of a meeting: same day or next day (4.6) |
| planner | The person who books the GMs |

---

## 1. Purpose and scope

The planner needs a **gauge**: for each day of a week, how much reporting work there is, how much
of it the staff present can do, and therefore how many hours, per language and role, are short. The
shortage is then filled by booking GMs from the half-days they offered. The planner is **never
obliged** to take an offer: which half-days are taken depends entirely on the shortage.

In scope:

- the workload per day and language, taken from spic (2.1);
- the capacity of the staff per day, language and role, taken from JK (2.2), minus the half-days the
  planner marks as not available for this work (5);
- the shortage per day, after moving work to the next day where spic's deadline allows it, for
  redacteurs and revisors (4);
- the GMs: their languages and roles, the half-days they offer (2.3), and the bookings (6);
- the Dimona declaration per booked half-day (6.3).

Not in scope:

- **Hoofdredacteur and vertaler are planned on sight** (the user, 26 October 2026). The application
  shows who is present and available in those roles, without calculating a need or a shortage.
- Pay, contracts and the Dimona declaration itself (the application only records that it was done).
- Changing anything in spic or JK: the application only reads them.

---

## 2. Sources of information

### 2.1 spic: the workload

- spic already estimates, per meeting, the **working hours per language** (FR and NL), from the
  questions on the agenda: the minutes of each language × 0.87, divided by 5 (every five minutes of
  meeting are one working hour), rounded to half an hour (FA Opnamebeheer §4.4; `spic/app/schatting.py`).
  The user put it as "every 5 minutes represent one working hour".
- This application **takes those hours over and never recalculates them**, so that the rule lives in
  one place (spic, where the parameters can be changed).
- The hours are the work of the **redacteurs** in that language. The work of the revisors follows from
  it (4.3).
- The work of a meeting belongs to the **date of the meeting**, and must be done on that day or, when
  the meeting's **deadline** in spic is "next day", on that day or the next working day (4.6).
- A meeting without questions on its agenda has no working hours in spic and brings no work (the user,
  26 October 2026).
- The GMs are planned **week by week**: the weeks spic passes on (pre-definitive or definitive) are
  enough; weeks in concept are not needed (the user, 27 October 2026).
- A meeting that is cancelled or deleted in spic brings no work.
- The application reads spic like PDC does: through spic's export, with its own copy and its own
  token (PDC functional analysis 1.3). The export must carry the working hours FR and NL (10, point 2).

### 2.2 JK: the staff

- JK knows, per person and per half-day, whether the person works: the youngest **validated**
  version of the person's calendar, with the adjustments since then. A half-day counts as present when
  it holds a working day (`E`) that is not replaced by a type; a replacement type (absence, training,
  leave) makes the half-day absent. This is the same rule as the screen *Beheer → Aanwezigheden* of JK
  (`aanwezigheden` in `jaarkalender/app.py`). A person without a validated version counts as absent
  and is flagged.
- A half-day of a staff member is worth **4 hours** of work (the user, 26 October 2026).
- Everyone in JK may be read (the user). Who counts as capacity follows from the roles (3.2): a person
  without any of the four roles does not count.
- The staff count **only in their mother tongue** (the user, 26 October 2026).
- JK has no language or role per person today, and no access for another program. What JK needs is in
  section 9.2.

### 2.3 The GMs: their offers

- GMs offer half-days, as now through a **Google Form**; this yields a table with per person the
  half-days on which they can come and work. The form's results are imported (as the CSV import of PDC,
  Phase 2). An own form, as proposed for PDC (PDC FA 9, point 14), may replace it later.
- A GM half-day is worth **3 hours in the morning and 4 hours in the afternoon** (the user,
  26 October 2026).
- An offer is not a booking (6).

### 2.4 Kept in this application

- the GMs: name, email (to recognise the form's answers), languages, roles (3);
- the half-days on which a staff member does not count for this work (5);
- the bookings and the Dimona declarations (6);
- a log of what the planner did (6.4).

---

## 3. People, languages and roles

### 3.1 Roles

Four roles: **redacteur**, **revisor**, **hoofdredacteur**, **vertaler**. A person can be capable of
several roles, but does **one role per half-day**, never two at once (the user, 26 October 2026).

### 3.2 Per person

| Property | Staff | GM |
|---|---|---|
| Languages | the mother tongue only (FR or NL) | FR, NL or both (a GM working in both languages is exceptional) |
| Standard role | one of the four | one of the four |
| Other roles | each with **may**, **rather not** or **not** | each role the GM is capable of |
| Where it is kept | in JK, with the person (9.2) | in this application |

### 3.3 How a role may be used: one rule for staff, another for GMs

The user, 26 October 2026: "for one group the rule is different from the other".

- **Staff** count first in their **standard role**. Only when a shortage remains in another role may a
  staff member be counted there:
  - first those for whom that role is **may** (for example a hoofdredacteur who may revise);
  - then, only if a shortage is left, those for whom it is **rather not**; every such use is shown to
    the planner as a warning;
  - never in a role marked **not** or not listed.
- **GMs** are used **where the need is highest**, in any role they are capable of; their standard role
  gives no preference. Example: GMs who are redacteurs by default and have become revisors over time,
  and are glad to do revision work.

These two rules are **fixed and stated on the screen** in this version. Making them configurable is
possible later, when it turns out to be needed (10, point 5).

---

## 4. Calculation

All amounts are **hours**, per **day**, per **language**. The roles calculated are **redacteur** and
**revisor**.

### 4.1 Need for redacteurs

need_red(day, language) = the sum of the working hours in that language of the meetings of that day
(2.1).

### 4.2 Capacity of the staff

For each present half-day (2.2) of a staff member who is not marked unavailable (5): 4 hours, in the
mother tongue, in one role. Which role follows the rule of 3.3: first everyone in their standard
role; then, where a shortage remains, staff with **may** for that role, then **rather not**. A
half-day used in another role is no longer available in the standard role.

### 4.3 Need for revisors

**3.5 revisors per 12 redacteurs**, in the same language (the user, 26 October 2026; "3 to 4 per 12",
calculated as 3.5). In hours:

need_rev(day, language) = need_red(day, language) × 3.5 / 12

Example: work for 12 redacteurs during a morning is 12 × 4 = 48 hours; revision is 48 × 3.5 / 12 =
14 hours, that is 3.5 half-days: three or four revisors that morning, or one and a half to two
revisors during the whole day.

### 4.4 Shortage per day

shortage(day, role, language) = max(0, need − capacity)  
surplus(day, role, language) = max(0, capacity − need)

### 4.5 Rounding

Shortages are shown in hours and in half-days of a GM (3 hours in the morning, 4 in the afternoon).
Bookings are whole half-days.

### 4.6 Moving work to the next day: spic's deadline

Work can be moved to the next day, when that day has more staff, rather than booking a GM; unless the
next day is busy too. Whether the work of a meeting may wait follows the **deadline of the meeting in
spic** (the user, 26 October 2026):

- **same day** (`zelfde-dag`): the work is done on the day of the meeting;
- **next day** (`volgende-dag`): the work is done on the day of the meeting or the **next working day**
  (the user, 27 October 2026): the next day on which JK has working days, so Monday after a Friday, or
  the first day after a holiday. When that day lies in a week that is not planned yet, the carried work
  is shown in the overview of that later week.

By default spic gives Monday and Wednesday "next day" and the other days "same day" (a parameter of
spic per weekday), which gives the pairs Monday with Tuesday and Wednesday with Thursday. A user of spic
can change the deadline of a single meeting; this application follows it. Work only moves **forward**:
a report cannot be made before the meeting.

**Calculation**, for each role and language, day by day in date order (the work with the earliest
deadline first):

- *due today* = the work carried from the day before + the work of today's meetings with deadline
  "same day";
- *may wait* = the work of today's meetings with deadline "next day";
- capacity today = the staff (4.2) plus the GMs booked (4.7);
- **shortage of today** = max(0, due today − capacity today);
- the capacity left after the work due today goes to the work that may wait; what does not fit is
  *carried* to the next working day: carried = max(0, may wait − max(0, capacity today − due today)).

A surplus on a day helps only work of that day or work carried into it, never work of later days.

**Where the GM hours can go.** The shortage of a day is the work that has to be done that day. A GM
booked that day helps the whole of it. A GM booked the day before helps only the part that was carried
from that day. The application shows both.

The revision of the work follows the work: the same deadlines apply to the revisors (the user,
26 October 2026).

### 4.7 GMs booked

Every booked GM half-day adds its hours (3 or 4) to the capacity of its day, in the language and role
it is booked for. The application recalculates the shortage after every booking, so the planner sees
what is still missing.

---

## 5. Staff not available for this work

JK says who works. On top of that, the planner can mark a staff member's half-day as **"does not count
for this planning"**, with a short reason: a revisor who follows a training, or coordinates the work
that day, and therefore does not really revise (the user, 26 October 2026). These tasks do not need to
be recorded in JK.

- The mark is per person and per half-day, and is kept in this application only.
- Who set it and when is logged (6.4).
- An absence that is already in JK as a replacement type (leave, training entered as a type) needs no
  mark: it already makes the half-day absent (2.2).

---

## 6. Bookings

### 6.1 A booking

One GM, one date, one half-day, **one role, one language**, with a status: **proposed**,
**confirmed** or **cancelled**. A booking needs an offer of that GM for that half-day; booking without
an offer is allowed but flagged (as for PDC, PDC FA 9, point 7).

### 6.2 Rules

- **BR-GM-001**: A GM has at most one booking that is not cancelled per half-day.
- **BR-GM-002**: The role must be one the GM is capable of, and the language one of the GM's
  languages.
- **BR-GM-003**: A booking that is not cancelled counts as capacity (4.7); a proposed one is shown
  apart from a confirmed one.
- **BR-GM-004**: A booking is never deleted, only cancelled.
- **BR-GM-005**: The application **proposes nothing on its own** in this version: it shows the shortage
  and the offers that fit, and the planner chooses (10, point 6).

### 6.3 Dimona

GMs work as occasional workers; every service needs a Dimona declaration. Per booked half-day the
planner ticks that the declaration is done, as for interpreters in occasional work in PDC (PDC FA
2.5). Confirmed bookings of the past without a declaration form the work list **Dimona to declare**.

### 6.4 Log

Every booking, confirmation, cancellation, Dimona tick and every mark of 5 is logged with who and when,
in an append-only log like PDC's (PDC FA 1.6).

---

## 7. Screens

1. **Week overview** (the main screen): days × language × role (redacteur, revisor), with per cell the
   need, the staff capacity, the work carried to the next day, the shortage, the GM hours booked and what
   is still missing. Staff used in another role (3.3) and every **rather not** use are listed with the
   day. Hoofdredacteur and vertaler: who is present, without a calculation.
2. **Staff of the week**: per person and half-day, present or not (from JK), the role counted, and the
   mark of 5, which the planner can set or remove here.
3. **Offers and bookings**: per half-day the GMs who offered, with their languages and roles; the
   planner books one in a role and a language, and sees the shortage change.
4. **GMs**: the register (name, email, languages, standard role, roles).
5. **Work list Dimona to declare** (6.3).

---

## 8. Worked examples

All amounts in hours, one language, redacteurs. The deadlines are spic's defaults: the Monday meetings
"next day", the Tuesday meetings "same day". "Carried" is the Monday work left for Tuesday (4.6).

| | Need | Staff | Carried | Shortage on Tuesday |
|---|---|---|---|---|
| A: Monday | 40 | 30 | 10 | |
| A: Tuesday | 20 | 35 | | max(0, 20 + 10 − 35) = **0**: nobody to book |
| B: Monday | 40 | 30 | 10 | |
| B: Tuesday | 30 | 35 | | max(0, 30 + 10 − 35) = **5**: two GM half-days (3 or 4 hours each); a GM on Monday helps up to 10 hours, on Tuesday the whole 5 |
| C: Monday | 20 | 35 | 0 (a surplus of 15 does not help Tuesday) | |
| C: Tuesday | 45 | 35 | | max(0, 45 + 0 − 35) = **10**: four GM mornings (4 × 3) or three afternoons (3 × 4), or a mix, all on Tuesday; on Monday they would be of no use |

**A deadline changed by hand.** Example B, but one Tuesday meeting with 10 hours of work gets the
deadline "next day" in spic: due on Tuesday 10 + 20 = 30, capacity 35, nothing short. The 5 hours of
capacity left do half of that meeting's work; the other 5 hours are carried into Wednesday, where they
are due.

**Revisors.** Example B: need of redacteurs on Monday and Tuesday 70 hours, need of revisors 70 × 3.5 / 12 ≈
20.4 hours, compared in the same way with the revisors present on Monday and Tuesday.

**Roles.** NL, Wednesday: a revisor shortage of 8 hours. A hoofdredacteur present that day with
**may** for revisor is counted as revisor (4 hours, shown on the screen); a redacteur with **rather
not** for revisor is counted for the remaining 4 hours only if there is no other way, with a warning,
and is then no longer counted as redacteur, which may make a redacteur shortage. A GM who is a
redacteur by default but capable of revision can be booked as revisor without any warning.

---

## 9. Technical design (proposals)

### 9.1 Place

- A **sibling of PDC in the same repository**, sharing what both need: the sign-in through Authelia,
  the copy of spic, the visual style, the Dimona tick and the log. Each application keeps **its own
  database** (PDC FA 1.2: own retention and access rules for the personal data of freelancers).
- Python 3.12, Flask, SQLite, like PDC; tests for every rule of section 4, with the examples of
  section 8 as fixed test cases.

### 9.2 What JK needs

Changes in JK, on a branch of the repository `infracriv`, in Dutch, as agreed there; nothing is
changed before the user asks for it:

1. Per staff member: **mother tongue** (FR or NL), **standard role**, and for each other role **may**,
   **rather not** or **not**.
2. A **read-only API with a token of its own**, reachable inside the server network only (like PDC
   reaches spic): for a period, per person and per half-day, present or not (the rule of 2.2, without
   the reason of an absence), with the language and roles of 1.
3. Nothing else: the marks of 5 stay in this application.

### 9.3 What spic needs

The export (FA Opnamebeheer §13.2, still to be built) must carry the working hours FR and NL and the
deadline of each meeting. spic hides them from readers today (`_voor_lezer` in `spic/app/planning.py`); this application
reads with its own token, not as a reader. To be agreed with the spic session.

---

## 10. Open points

1. **Name** of the application.
2. **The export of spic** must carry the working hours FR and NL (9.3).
3. ~~Weeks in concept~~: the GMs are planned week by week, so the weeks that spic passes on
   (pre-definitive or definitive) are enough (the user, 27 October 2026; 2.1).
4. ~~Meetings without questions~~: they bring no work (the user, 26 October 2026; 2.1).
5. **Configurable role rules** (3.3): fixed in this version; configurable later if needed.
6. **A proposal of half-days** (BR-GM-005): the application could propose a set of offers that covers
   the shortage. Not in this version.
7. ~~Pairs or deadline~~: the deadline of each meeting in spic is followed (the user, 26 October 2026;
   4.6). The pairs are what spic's default deadlines give.
8. ~~The next working day~~: when the deadline is "next day", the work may wait until the **next working
   day**, also after a Friday, a holiday or before a recess (the user, 27 October 2026; 4.6).
