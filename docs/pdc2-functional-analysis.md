# Functional Analysis
## PDC2: booking occasional staff for Verslaggeving

**Version:** 1.0 (first version built)  
**Date:** 24 November 2026  
**Document Type:** Conceptual Model & Business Rules

> PDC2 helps the planner of the Verslaggeving directorate decide how many occasional staff members
> (gelegenheidsmedewerkers, **GM**) to book, and on which half-days, in which language and role. It is
> the "similar application for another category of freelancers" announced in the functional analysis
> of PDC (section 1): a separate application with its own database, built on the same foundations as
> PDC. The decisions of the user are dated; what is still a proposal says so. Section 10 lists the
> changes that PDC2 needs in other systems, section 11 what is still open.

**Version history**

| Version | Date | Change |
|---|---|---|
| 0.1 | 26 October 2026 | First draft: sources, calculation, roles, bookings |
| 0.2 | 26 October 2026 | spic's deadline per meeting instead of fixed pairs of days; meetings without questions bring no work |
| 0.3 | 27 October 2026 | Next working day |
| 1.0 | 24 November 2026 | Decisions on the open points (role rules and choice of half-days as proposed, rights by a list in the settings, no estimate for an unknown agenda, retention at least five years); architecture: HATEOAS APIs in spic and JK, htmx, parts of the Io design system, fake sources (9); the first version built |
| 0.9 | 16 November 2026 | Name PDC2; weeks in concept can be planned (2.1); meetings with an unknown agenda (2.1); the role rules and the proposal of half-days explained, with a proposal for the first version (3.3, 6.2); work no longer needed (6.2); offers entered by hand (2.3); rights (9.3); changes to other systems in one section (10) |

**Terms used in this document**

| Term | Meaning |
|------|---------|
| PDC2 | This application |
| GM | Occasional staff member (gelegenheidsmedewerker): works for Verslaggeving on half-days for which they offered themselves and were booked; occasional work with a Dimona declaration |
| staff | The permanent staff of Verslaggeving, whose presence is planned in the jaarkalender |
| half-day | AM or PM of a working day (dagdeel) |
| role | redacteur, revisor, hoofdredacteur or vertaler. One person does one role per half-day |
| spic | The planning of the meetings (repository `bvelsac/crystalclear`); source of the workload |
| JK | The jaarkalender (repository `bvelsac/infracriv`, folder `jaarkalender`); source of the presence of the staff |
| deadline | spic's deadline (termijn) of a meeting: same day or next day (4.6) |
| week status | Status of a week in spic: concept, pre-definitive or definitive |
| planner | The person who books the GMs |

---

## 1. Purpose and scope

The planner needs a **gauge**: for each day of a week, how much reporting work there is, how much
of it the staff present can do, and therefore how many hours, per language and role, are short. The
shortage is then filled by booking GMs from the half-days they offered. The planner is **never
obliged** to take an offer: which half-days are taken depends entirely on the shortage.

In scope:

- the workload per day and language, taken from spic (2.1), for any week, also a week in concept;
- the capacity of the staff per day, language and role, taken from JK (2.2), minus the half-days the
  planner marks as not available for this work (5);
- the shortage per day, after moving work to the next working day where spic's deadline allows it, for
  redacteurs and revisors (4);
- the GMs: their languages and roles, the half-days they offer (2.3), and the bookings (6);
- the Dimona declaration per booked half-day (6.3).

Not in scope:

- **Hoofdredacteur and vertaler are planned on sight** (the user, 26 October 2026). PDC2 shows who is
  present and available in those roles, without calculating a need or a shortage.
- Pay, contracts and the Dimona declaration itself: PDC2 only records that it was done, and keeps no
  national register number.
- Mail to the GMs: PDC2 sends nothing; it gives lists the planner can copy (7).
- Changing anything in spic or JK: PDC2 only reads them.

---

## 2. Sources of information

### 2.1 spic: the workload

- spic estimates, per meeting, the **working hours per language** (FR and NL), from the questions on
  the agenda: the minutes of each language × 0.87, divided by 5 (every five minutes of meeting are one
  working hour), rounded to half an hour (FA Opnamebeheer §4.4; `spic/app/schatting.py`).
- PDC2 **takes those hours over and never recalculates them**, so that the rule lives in one place
  (spic, where the parameters can be changed).
- The hours are the work of the **redacteurs** in that language. The work of the revisors follows from
  it (4.3).
- The work of a meeting belongs to the **date of the meeting**, and must be done on that day or, when
  the meeting's **deadline** in spic is "next day", on that day or the next working day (4.6).
- A meeting without questions on its agenda has no working hours in spic and brings no work (the user,
  26 October 2026).
- **Agenda unknown.** spic marks a meeting whose agenda is not known yet (`agenda_onbekend`). Such a
  meeting has no working hours yet, but will have work. PDC2 counts it as 0 hours, **without an
  estimate** (the user, 24 November 2026), and shows it as a warning on its day ("2 meetings with an
  unknown agenda"), so the planner knows the shortage of that day may be larger.
- A meeting that is cancelled or deleted in spic brings no work.
- **Every week can be planned, also a week in concept** (the user, 16 November 2026): the planner may
  want to reserve GMs for a week that spic still has in concept. PDC2 therefore receives the weeks in
  concept as well, and shows the week status prominently: the figures of a week in concept are
  provisional. This needs a change in spic's export (10.1).
- PDC2 reads spic through spic's API for consumers, with a token of its own (10.1). In the first version
  it reads the week it shows, and the week before it, each time a screen opens; it keeps no copy. A copy
  kept up to date by the change feed ("since change N", as PDC FA 1.3), with a background task, can come
  later if reading live turns out too slow or spic is too often unreachable.

### 2.2 JK: the staff

- JK knows, per person and per half-day, whether the person works: the youngest **validated**
  version of the person's calendar, with the adjustments since then. A half-day counts as present when
  it holds a working day (`E`) that is not replaced by a type; a replacement type (absence, training,
  leave) makes the half-day absent. This is the rule of the screen *Beheer → Aanwezigheden* of JK
  (`aanwezigheden` in `jaarkalender/app.py`). A person without a validated version counts as absent
  and is flagged.
- A half-day of a staff member is worth **4 hours** of work (the user, 26 October 2026).
- Everyone in JK may be read (the user, 26 October 2026). Who counts as capacity follows from the roles
  (3.2): a person without any of the four roles does not count.
- The staff count **only in their mother tongue** (the user, 26 October 2026).
- JK also tells which days are working days (holidays, recess), for the next working day of 4.6.
- What JK must add for this is in 10.2.

### 2.3 The GMs: their offers

- GMs offer half-days, as now through a **Google Form**; this yields a table with per person the
  half-days on which they can come and work. The form's results are imported as a CSV file; the GM is
  recognised by email address.
- A new answer of the same GM for the same half-days replaces the earlier one (the latest counts).
- The planner can also **enter an offer by hand** (a GM who calls), marked as such.
- An answer from an unknown email address is not imported but listed, so the planner can add the GM
  first.
- A GM half-day is worth **3 hours in the morning and 4 hours in the afternoon** (the user,
  26 October 2026).
- An offer is not a booking (6).
- An own form, as proposed for PDC (PDC FA 9, point 14), may replace the Google Form later.

### 2.4 Kept in PDC2

- the GMs: name, email, phone, languages, standard role, roles, active or not, notes (3);
- the offers (2.3);
- the half-days on which a staff member does not count for this work (5);
- the bookings and the Dimona declarations (6);
- a log of what the planner did (6.4);
- PDC2's own copy of the spic meetings (2.1).

---

## 3. People, languages and roles

### 3.1 Roles

Four roles: **redacteur**, **revisor**, **hoofdredacteur**, **vertaler**. A person can be capable of
several roles, but does **one role per half-day**, never two at once (the user, 26 October 2026).
Only redacteur and revisor are calculated (1).

### 3.2 Per person

| Property | Staff | GM |
|---|---|---|
| Languages | the mother tongue only (FR or NL) | FR, NL or both (a GM working in both languages is exceptional) |
| Standard role | one of the four | one of the four |
| Other roles | each with **may**, **rather not** or **not** | each role the GM is capable of |
| Where it is kept | in JK, with the person (10.2) | in PDC2 |

### 3.3 The role rules: when a person is counted in another role

The "role rules" decide in which role PDC2 counts a person on a half-day when it is not the person's
standard role. The user, 26 October 2026: "for one group the rule is different from the other".

**Staff.** PDC2 counts every staff member first in their **standard role**. When, after that, a
shortage is left in a calculated role on a day, PDC2 looks for staff present that day who can take that
role, in this order:

1. staff with **may** for that role whose own standard role has capacity to spare that day (the capacity
   left after all the work of that day, so that moving them creates no new shortage);
2. staff with **may** whose standard role is not calculated (hoofdredacteur, vertaler), for example a
   hoofdredacteur who may revise;
3. only then, staff with **rather not**, in the same order; each such use is shown as a **warning**.

Never in a role marked **not** or not listed. A half-day is moved as a whole (4 hours), and is then no
longer counted in the standard role. Every move is listed on the week overview with the person and the
day. If the planner does not want a person to be moved (the hoofdredacteur is needed as hoofdredacteur
that day), they mark that half-day "does not count for this planning" (5).

**GMs.** A GM's standard role gives no preference: the planner books a GM in **any role the GM is
capable of**, wherever the need is highest, without any warning. Example: GMs who are redacteurs by
default and have become revisors over time, and are glad to do revision work.

**Fixed rules.** These two rules are fixed in the first version and stated on the week overview (the
user, 24 November 2026). They can be made configurable later, when it turns out to be needed.

---

## 4. Calculation

All amounts are **hours**, per **day**, per **language**. The roles calculated are **redacteur** and
**revisor**.

### 4.1 Need for redacteurs

need_red(day, language) = the sum of the working hours in that language of the meetings of that day
(2.1).

### 4.2 Capacity of the staff

For each present half-day (2.2) of a staff member who is not marked unavailable (5): 4 hours, in the
mother tongue, in one role, following the role rules of 3.3.

### 4.3 Need for revisors

**3.5 revisors per 12 redacteurs**, in the same language (the user, 26 October 2026; "3 to 4 per 12",
calculated as 3.5). In hours:

need_rev(day, language) = need_red(day, language) × 3.5 / 12

Example: work for 12 redacteurs during a morning is 12 × 4 = 48 hours; revision is 48 × 3.5 / 12 =
14 hours, that is 3.5 half-days: three or four revisors that morning, or one and a half to two
revisors during the whole day.

### 4.4 Shortage per day

shortage(day, role, language) and surplus(day, role, language) follow from 4.6, which moves work to
the next working day where the deadline allows it.

### 4.5 Rounding

Shortages are shown in hours and in half-days of a GM (3 hours in the morning, 4 in the afternoon).
Bookings are whole half-days.

### 4.6 Moving work to the next working day: spic's deadline

Work can be moved to the next working day, when that day has more staff, rather than booking a GM;
unless the next day is busy too. Whether the work of a meeting may wait follows the **deadline of the
meeting in spic** (the user, 26 October 2026):

- **same day** (`zelfde-dag`): the work is done on the day of the meeting;
- **next day** (`volgende-dag`): the work is done on the day of the meeting or the **next working day**
  (the user, 27 October 2026): the next day on which JK has working days, so Monday after a Friday, or
  the first day after a holiday. When that day lies in the next week, the carried work is shown in the
  overview of that week too.

By default spic gives Monday and Wednesday "next day" and the other days "same day" (a parameter of
spic per weekday), which gives the pairs Monday with Tuesday and Wednesday with Thursday. A user of spic
can change the deadline of a single meeting; PDC2 follows it. Work only moves **forward**: a report
cannot be made before the meeting.

**Calculation**, for each role and language, day by day in date order (the work with the earliest
deadline first):

- *due today* = the work carried from the day before + the work of today's meetings with deadline
  "same day";
- *may wait* = the work of today's meetings with deadline "next day";
- capacity today = the staff (4.2) plus the GMs booked (4.7);
- **shortage of today** = max(0, due today − capacity today);
- the capacity left after the work due today goes to the work that may wait; what does not fit is
  *carried* to the next working day: carried = max(0, may wait − max(0, capacity today − due today));
- **surplus of today** = what is left of the capacity after the work due today and the work that may
  wait.

A surplus on a day helps only work of that day or work carried into it, never work of later days.

**Where the GM hours can go.** The shortage of a day is the work that has to be done that day. A GM
booked that day helps the whole of it. A GM booked the day before helps only the part that was carried
from that day. PDC2 shows both.

The revision of the work follows the work: the same deadlines apply to the revisors (the user,
26 October 2026).

### 4.7 GMs booked

Every booked GM half-day that is not cancelled adds its hours (3 or 4) to the capacity of its day, in
the language and role it is booked for. PDC2 recalculates the shortage after every booking, so the
planner sees what is still missing.

---

## 5. Staff not available for this work

JK says who works. On top of that, the planner can mark a staff member's half-day as **"does not count
for this planning"**, with a short reason: a revisor who follows a training, or coordinates the work
that day, and therefore does not really revise (the user, 26 October 2026). These tasks do not need to
be recorded in JK.

- The mark is per person and per half-day, and is kept in PDC2 only.
- Who set it and when is logged (6.4).
- An absence that is already in JK as a replacement type (leave, training entered as a type) needs no
  mark: it already makes the half-day absent (2.2).

---

## 6. Bookings

### 6.1 A booking

One GM, one date, one half-day, **one role, one language**, with a status: **proposed**,
**confirmed** or **cancelled**. A booking normally follows an offer of that GM for that half-day;
booking without an offer is allowed but flagged.

### 6.2 Rules

- **BR-GM-001**: A GM has at most one booking that is not cancelled per half-day.
- **BR-GM-002**: The role must be one the GM is capable of, and the language one of the GM's
  languages.
- **BR-GM-003**: A booking that is not cancelled counts as capacity (4.7); a proposed one is shown
  apart from a confirmed one.
- **BR-GM-004**: A booking is never deleted, only cancelled.
- **BR-GM-005**: **The planner chooses; PDC2 proposes no half-days on its own** in the first version
  (the user, 24 November 2026). PDC2 shows the shortage and, next to
  it, the offers that fit (language, role, day); the planner books, and the shortage is recalculated at
  once. An automatic proposal (PDC2 picking a set of offers that covers the shortage, which the planner
  then accepts or changes) is possible later.
- **BR-GM-006**: A booking is **never cancelled automatically**. When the work shrinks (a meeting
  cancelled, an agenda shortened, a week back in concept) PDC2 shows the booked hours that are no longer
  needed on that day, and the planner decides.

### 6.3 Dimona

GMs work as occasional workers; every service needs a Dimona declaration. Per booked half-day the
planner ticks that the declaration is done, as for interpreters in occasional work in PDC (PDC FA
2.5). Confirmed bookings without a declaration form the work list **Dimona to declare**.

### 6.4 Log

Every booking, confirmation, cancellation, Dimona tick, every mark of 5 and every change to a GM is
logged with who and when, in an append-only log like PDC's (PDC FA 1.6).

---

## 7. Screens

1. **Week overview** (the main screen): the planner picks any week, also one in concept; its week
   status is shown at the top. Days × language × role (redacteur, revisor), with per cell the need, the
   staff capacity, the work carried to the next day, the shortage, the GM hours booked and what is still
   missing or no longer needed. Below: the staff counted in another role (3.3) and every **rather not**
   use, the meetings with an unknown agenda, and the staff without a validated calendar. Hoofdredacteur
   and vertaler: who is present, without a calculation. The two role rules of 3.3 are stated on this
   screen.
2. **Staff of the week**: per person and half-day, present or not (from JK), the role counted, and the
   mark of 5, which the planner can set or remove here.
3. **Offers and bookings**: per half-day the GMs who offered, with their languages and roles; the
   planner books one in a role and a language, and sees the shortage change.
4. **Bookings of the week**: per GM the half-days, roles and languages booked, to copy into a mail to
   the GM; per day the GMs booked.
5. **GMs**: the register (name, email, phone, languages, standard role, roles, active, notes).
6. **Import**: the CSV of the Google Form, with the answers that could not be matched (2.3).
7. **Work list Dimona to declare** (6.3).

The look follows PDC (`docs/visual-style.md`), with a background and an accent of its own.

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

**Revisors.** Example B: need of redacteurs on Monday and Tuesday 70 hours, need of revisors
70 × 3.5 / 12 ≈ 20.4 hours, compared in the same way with the revisors present on Monday and Tuesday.

**Roles.** NL, Wednesday: a revisor shortage of 8 hours, and the redacteurs have 6 hours to spare that
day. One redacteur with **may** for revisor is moved (a half-day of 4 hours fits in the 6 to spare; a
second would leave the redacteurs 2 hours short, so it is not moved). A hoofdredacteur present with
**may** for revisor is counted for the other 4 hours. A redacteur with **rather not** would only have
been used if no one else could, with a warning. A GM who is a redacteur by default but capable of
revision can be booked as revisor without any warning.

These examples are the fixed test cases of the calculation (9.2).

---

## 9. Technical design

### 9.1 Place

- PDC2 is a **sibling of PDC in the same repository** (`bvelsac/matcher`), sharing what both need: the
  sign-in through Authelia, the copy of spic, the visual style, the Dimona tick and the log. Each
  application keeps **its own database** and its own container (PDC FA 1.2: own retention and access
  rules for the personal data of freelancers).
- Python 3.12, Flask, SQLite in WAL mode, migrations with Alembic, like PDC.

### 9.2 Tests

Every rule of section 4 has tests, with the examples of section 8 as fixed cases; the screens get
browser tests, as in PDC. Tests and sample data use fictitious names only.

### 9.3 Rights

Everyone Authelia lets in for PDC2 may read; who may change data is **a list of user ids in PDC2's
settings** (`PDC2_EDITORS`; the user, 24 November 2026).

### 9.4 Architecture (the user, 24 November 2026)

- **HATEOAS for the services.** spic and JK offer a read-only API in HAL (`application/hal+json`):
  PDC2 knows only their entry address and finds everything else by following named links. The contract
  is in `docs/pdc2-api-contract.md`; the client in `pdc2/hal.py`.
- **htmx for the client.** The pages are HTML from the server; htmx makes a handling (book, confirm,
  mark a half-day) answer with the part of the page that changed, and the shortage of the week out of
  band. That is hypermedia on the browser side as well.
- **Look.** PDC's look (`docs/visual-style.md`), with parts of the user's **Io** design system: the meter
  for how much of the work is covered, the badges on its warmth scale for a shortage, and the red glass
  line under today (`static/pdc2/io.css`).
- **Fake sources.** With `PDC2_SOURCE=fake`, PDC2 answers the documents of spic and JK itself, with
  realistic but fictitious data (`pdc2/fake.py`): the same HAL client and calculation run as against the
  real services. Every screen shows "test data" then. `python -m pdc2 sample-data` adds fictitious GMs,
  offers and bookings.

### 9.5 Retention

The data of the GMs, the offers and the bookings are kept **at least five years** (the user,
24 November 2026). PDC2 deletes nothing by itself; how data older than that is removed is decided
later.

---

## 10. Changes needed in other systems

Nothing below is done by a PDC2 session on its own initiative: each change is made in its own
repository, by its own rules, when the user asks for it. The user is the link between the sessions.

### 10.1 spic (repository `bvelsac/crystalclear`)

**Built on 24 November 2026**, on the branch `claude/pdc2-api` (not yet on `main`, not deployed): the
API of `docs/pdc2-api-contract.md` in `spic/app/afnemers.py`, with tests, and recorded in
`docs/stand-van-zaken.md` and FA Opnamebeheer §13.2.1. A meeting without questions has `werkuren: null`.
To deploy: a tag of spic, and `SPIC_AFNEMERS` with real tokens in the server's `.env`. Still to build:
the change feed and the full list for PDC (not needed by PDC2's first version). What PDC2 needs:

1. **Per meeting**: ID, date, status (planned, cancelled, deleted), week and **week status**, the
   **working hours FR and NL**, the **deadline** (`termijn`: same day or next day) and **agenda unknown**
   (`agenda_onbekend`). spic hides the working hours from readers today (`_voor_lezer` in
   `spic/app/planning.py`); PDC2 reads with its own token, not as a reader.
2. **Weeks in concept for PDC2.** §13.2 passes on only weeks that are pre-definitive or definitive. PDC2
   needs the weeks in concept too (2.1); PDC does not. So the visibility of the weeks becomes a property
   of the consumer's token: PDC sees pre-definitive and definitive weeks, PDC2 all weeks. **This changes
   the contract** and has to be agreed in the spic session first.
3. **A token of its own** for PDC2, inside the server network, like PDC's.
4. To be recorded in `docs/stand-van-zaken.md` of `crystalclear`.

### 10.2 JK (repository `bvelsac/infracriv`, folder `jaarkalender`)

**Built on 24 November 2026**, on the branch `claude/pdc2-api` (not yet on `main`, not deployed), with
tests and in `documentatie/specificatie.md` chapter 18. Choices made there: everyone in JK is listed
except accounts waiting for activation and the administrator account; a day is a working day when it
lies in a configured working year and is no weekend day or holiday (recess and suspension count as
working days); the rule of presence is shared with *Beheer → Aanwezigheden*. To deploy: `JK_API_TOKENS`
with a token for PDC2 in JK's environment. What PDC2 needs:

1. **Per staff member**: **mother tongue** (NL or FR), **standard role**, and for each other role
   **may**, **rather not** or **not**; editable by the administrators in *Beheer → Medewerkers*.
2. A **read-only API with a token of its own**, reachable inside the server network only, not through
   Authelia: for a period,
   - per person: the id, the name, the mother tongue and the roles of 1;
   - per person and half-day: present or not, by the rule of 2.2, **without the reason of an absence**,
     and whether the person has a validated calendar;
   - per day: whether it is a working day (for the next working day of 4.6).
3. Nothing else: the marks of 5 stay in PDC2. The rules of JK on quota and credit are not touched.

### 10.3 CAL (repository `bvelsac/infracriv`, folder `CAL`), only on the user's explicit request

1. A **route in the Caddyfile** for PDC2, behind Authelia (`import beveiligd`), and the rule in Authelia.
2. A **DNS record** at Cloudflare for its subdomain.
3. If rights go through a group (11, point 4): the group in **lldap** (an administrator's action, no
   code).

### 10.4 Server management (repository `bvelsac/infracriv`, folder `beheer`)

1. PDC2's volume in the **nightly back-up** (`VOLUMES` in the configuration of `beheer/back-up`), and in
   `back-up.conf.voorbeeld`.
2. The deployment itself: its own compose project on the network `infracriv`, its own version and tag,
   through GitHub Actions; a human puts it on the server.

### 10.5 The Google Form

1. A field with the **email address** of the GM, which PDC2 uses to recognise them.
2. One question per half-day, so that the CSV has one column per half-day.
3. An **example export with fictitious answers**, to build and test the import.

### 10.6 PDC (repository `bvelsac/matcher`)

The parts both applications use (sign-in, the copy of spic, the style, Dimona, the log) are moved into a
common part of the repository, with PDC's tests kept green.

---

## 11. Open points

1. **Shared parts with PDC** (10.6): PDC2 reuses PDC's stylesheet and images, and copies its sign-in;
   moving the sign-in and the Dimona tick into a common part is still to do.
2. **A copy of spic** kept up to date by the change feed (2.1), if reading live is not enough.
3. **Removing data older than five years** (9.5).
4. Settled: ~~name~~ (PDC2, 16 November 2026), ~~role rules~~ (two fixed rules, 24 November 2026),
   ~~proposal of half-days~~ (the planner chooses, 24 November 2026), ~~rights~~ (a list in the settings,
   24 November 2026), ~~agenda unknown~~ (no estimate, 24 November 2026), ~~retention~~ (at least five
   years, 24 November 2026), ~~weeks in concept~~ (can be planned, 2.1, 16 November 2026), ~~meetings without questions~~
   (no work, 26 October 2026), ~~pairs or deadline~~ (spic's deadline, 26 October 2026), ~~next working
   day~~ (27 October 2026).
