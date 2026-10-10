# PDC: afwijkingen van het prototype en ontwerp

Stand: 10 oktober 2026. De besluiten staan in `docs/functional-analysis.md` (versie 1.2) en, voor de koppeling met spic,
in `docs/stand-van-zaken.md` van `bvelsac/crystalclear`. Dit document zegt **wat er in de code van fase 1 afwijkt** van
die besluiten, beschrijft **het model van de eigen kopie** van de vergaderingen en zegt wat de beslissingen van
10 oktober 2026 (databank, vergrendeling, aanmelding, taal) in de code vragen. Er is nog niets aan de koppeling met spic
gebouwd.

**Beslissingen van de gebruiker op 10 oktober 2026** (over de voorstellen die hier stonden):

1. **Databank: SQLite.** Er zijn nog geen gegevens in het prototype.
2. **Model van de kopie:** vrij te kiezen; de twee toepassingen hebben hoe dan ook elk een eigen databank. Het model in §2
   is dus het ontwerp.
3. **De vergrendeling vervalt**, op voorwaarde dat de controle bij het opslaan geen grote vertraging geeft (dat doet ze
   niet: één of twee opzoekingen op een index binnen dezelfde transactie, enkele milliseconden).
4. **Aanmelding met Authelia, rechten zoals in spic.** PDC hangt daarmee **uitdrukkelijk af** van Authelia (identiteit) en
   van spic (de lijst van invoerders en beheerders).
5. **Taal van de code: Engels.** Een afspraak over Nederlands in de code is er nooit uitdrukkelijk geweest; dat is in
   `crystalclear` toevallig zo gegroeid.

## 1. Wat in het prototype afwijkt van wat besloten is

| # | Onderwerp | Prototype (fase 1) | Besloten (FA 1.2) | Gevolg |
|---|---|---|---|---|
| 1 | Herkomst van de vergaderingen | Met de hand ingevoerd (`/meetings/add`), met snelknoppen voor Uitgebreid Bureau en Bureau | Een kopie uit spic; alleen vergaderingen zonder verslag worden in PDC ingevoerd (§1.1, §1.5) | Tabel `meetings` wordt vervangen (§2 hieronder). Het formulier wordt het formulier voor eigen vergaderingen; de snelknoppen vervallen (die vergaderingen komen uit spic) |
| 2 | Herkenning | Eigen geheel getal, geen verwijzing naar spic | Herkenning op de ID van spic (`m-xxxxxxxx`), nooit op datum en uur (BR-MTG-008) | Kolom `spic_id` |
| 3 | Status en verwijderen | Geen status; verwijderen wist de rij, altijd toegelaten | Gepland, geannuleerd, verwijderd. Een spic-vergadering is in PDC niet te verwijderen; een eigen vergadering alleen zolang er nooit een tolk aan toegewezen was (BR-MTG-005, BR-MTG-006) | Kolom `status`; de verwijderknop alleen voor eigen vergaderingen, met de controle |
| 4 | Tijden | Beginuur verplicht, duur in hele uren (1 tot 8) | Beginuur kan ontbreken ("na afloop van"), einde is optioneel, het dagdeel (AM/PM) is er altijd (§2.7) | Velden `period`, `start_kind`, `effective_start`, `expected_end`; controles op overlap moeten met een ontbrekend uur overweg |
| 5 | Plaats | Vrije tekst (`location`) | Zaal uit de vaste lijst van spic, ook voor eigen vergaderingen | Kolom `room` (code) en een kopie van de lijst zalen; dat vraagt iets van de export van spic (§6) |
| 6 | Categorie | Vaste lijst van vier (Parliament, ...) | Voor spic-vergaderingen af te leiden van domein, assemblee en type; nog te ontwerpen (FA §9 punt 12) | Open; de vier blijven voorlopig voor eigen vergaderingen |
| 7 | Wijzigen | Een editor wijzigt alle velden | Van een spic-vergadering alleen beginuur, zaal en annulering, via de schrijfroute van spic, zonder vergrendeling (§1.4) | Het bewerkscherm geldt alleen voor eigen vergaderingen; voor spic-vergaderingen komt een kleine actie |
| 8 | Logboek en historiek | Geen. Alleen `created_by`, `created_at`, `updated_at` | Een eigen, alleen aanvullend logboek met een momentopname van de vergadering bij elke toewijzing; een historiek van de kopie; twee werklijsten (§1.6) | Nieuwe tabellen (§2) |
| 9 | Annuleren | Geen annulering; FA 1.1 annuleerde de toewijzingen automatisch | Een annulering wist of annuleert nooit een toewijzing; de planner beslist (§5.4) | Werklijst "geannuleerd met toegewezen tolk" |
| 10 | Bijwerken en achtergrondtaak | Alleen gunicorn, geen achtergrondtaak | Bijwerken bij gebruik én door een achtergrondtaak, met een slot en een nachtelijke vergelijking (§1.3) | Een tweede proces nodig; nog niet bouwen |
| 11 | Vergrendeling | Het hele systeem 4 uur op slot terwijl één editor toewijst | Beginuur, zaal en annulering direct en zonder vergrendeling, ook door een ander (§1.4) | Besloten: de vergrendeling vervalt (§4) |
| 12 | Aanmelding en rollen | Eigen accounts met wachtwoord (editor, viewer), na de aanmelding bij Authelia | Alle invoerders en beheerders van spic mogen PDC beheren, geen aparte rol; de naam van de persoon gaat mee naar de schrijfroute | Besloten: identiteit van Authelia, rechten uit spic (§5) |
| 13 | Naam | "Interpreter Management" in de schermen, "Interpreter Mission Management System" in de code en de documenten; `matcher` als repository, compose-project, image (`ghcr.io/bvelsac/matcher`), volume (`matcher_db`) en subdomein (`matcher.infracriv.net`) | PDC, Prestatiedatabank voor Conferentietolken | Schermen en documenten hernoemen. De namen op het platform (repository, image, volume, subdomein) zijn de keuze van de gebruiker; `CAL` alleen op uitdrukkelijke vraag |
| 14 | Databank | MySQL 8.0.40 in een eigen container | SQLite (besloten op 10 oktober 2026) | Overstappen (§3) |
| 15 | Python | Vastgezet op 3.8, "dezelfde versie als de productieserver" | PDC draait in Docker op dezelfde server als spic; spic gebruikt Python 3.12. Python 3.8 krijgt sinds oktober 2024 geen veiligheidsupdates meer | Naar Python 3.12 (image en vastgezette versies) |
| 16 | Uitrol | `git pull` en `docker compose up -d --build` op de server, image met tag `latest` | Eigen compose-project met eigen versie en tag; uitrollen via GitHub Actions; een sessie verbindt nooit zelf met de server | Een workflow en versienummers, zoals `spic.yml` in `crystalclear`. In `CAL` is er nog geen route voor `matcher` of PDC (alleen `jk`, `spic` en `um`), en de README noemt een DNS-record bij Cloudflare: beide alleen op uitdrukkelijke vraag van de gebruiker |
| 17 | Tijden | Opgeslagen en getoond in UTC (de vergrendeling toont "UTC") | Tijden van spic zijn Brusselse tijd | Vergaderingen in Brusselse tijd zoals spic; tijdstippen van het logboek bewaren in UTC en tonen in Brusselse tijd |
| 18 | Afspraken | Geen `CLAUDE.md` | Een `CLAUDE.md` met de afspraken en de naam PDC | Gemaakt op 10 oktober 2026 |
| 19 | Taal | Code, commentaar en FA in het Engels | Code, commentaar en commitberichten in het Engels (besloten op 10 oktober 2026) | Geen; de code blijft Engels (§7) |
| 20 | Tests | Tests met de testclient, geen browsertests | Een wijziging aan een pagina krijgt een browsertest | Browsertests (Playwright) toevoegen met de werkbank |

Wat **niet** afwijkt en blijft: de tolken en bureaus met de wettelijke prioriteitsvolgorde, de beschikbaarheden die
voorlopig via Google Forms (CSV) komen, het model van boekingen, posities en toewijzingen uit de FA, CSRF-bescherming,
en voorbeeldgegevens met verzonnen namen.

## 2. Ontwerp: het model van de eigen kopie

**Eén tabel voor alle vergaderingen**, spic en eigen, zodat de toewijzingen naar één tabel verwijzen en de planner één
lijst ziet. De velden die PDC opzoekt of toont, krijgen een eigen kolom; **de volledige laatste toestand uit spic gaat
mee als JSON**, zodat een nieuw veld in spic geen migratie in PDC vraagt en de momentopname in het logboek volledig is.
De namen hieronder volgen de FA (Engels); zie §7 voor de taal.

### `meetings` (vervangt de tabel van fase 1)

| Kolom | Inhoud |
|---|---|
| `id` | eigen sleutel van PDC; toewijzingen en logboek verwijzen hiernaar. Blijft dezelfde als spic een vergadering verwijdert en later met dezelfde ID herstelt |
| `origin` | `spic` of `own` |
| `spic_id` | ID van spic, uniek; verplicht voor `spic`, leeg voor `own` (een CHECK bewaakt dat) |
| `status` | `planned`, `cancelled` of `deleted` (`deleted` alleen voor `spic`) |
| `week`, `week_status` | maandag van de week in spic en haar status (`pre-definitief`, `definitief`, of `concept` als de week teruggezet werd) |
| `title` | titel van een eigen vergadering; voor spic-vergaderingen afgeleid bij het tonen |
| `date`, `period` | datum en dagdeel (`AM`, `PM`), altijd ingevuld |
| `start_kind`, `start_time` | `time` of `after`, en het ingevoerde beginuur (leeg bij "na afloop van") |
| `effective_start`, `expected_end`, `end_next_day` | begin en einde voor de planning; kunnen leeg zijn. Een lege tekst uit spic wordt NULL |
| `room` | zaalcode uit de lijst van spic |
| `domain`, `assembly`, `type`, `sequence_number`, `sequence_number_2` | indeling van spic |
| `interpreters_needed` | van PDC. Voor een nieuwe spic-vergadering leeg tot de planner het invult (werklijst "nieuw uit spic"); later eventueel een standaard per type |
| `category`, `notes` | van PDC |
| `spic_data` | JSON: de volledige laatste toestand uit spic |
| `spic_version`, `last_change_number` | versie van spic en het wijzigingsnummer van de laatste toegepaste wijziging |
| `created_at`, `updated_at`, `created_by`, `first_seen_at`, `deleted_in_spic_at` | beheer |

Overzetten uit spic (veld van spic → kolom): `id` → `spic_id`, `maandag` → `week`, `status` → `status`, `versie` →
`spic_version`, `datum` → `date`, `periode` → `period`, `start_soort` → `start_kind`, `start_uur` → `start_time`,
`effectief_begin` → `effective_start`, `verwacht_einde` → `expected_end`, `einde_volgende_dag` → `end_next_day`, `zaal` →
`room`, `domein`, `assemblee`, `type`, `volgnummer`, `volgnummer2`. De rest (ambtenaren, vragen, commentaar, prioriteit,
termijn, transcriberen, uitzonderlijk, agenda onbekend, ...) staat alleen in `spic_data`.

### `meeting_changes` (historiek van de kopie en van de eigen vergaderingen, alleen aanvullend)

Eén regel per wijziging die PDC toepast: `id`, `meeting_id`, `change_number` (het nummer van spic, leeg voor een eigen
vergadering), `kind` (`new`, `changed`, `cancelled`, `reopened`, `deleted`, `restored`, `moved`, `week_status`,
`edited`), `before` en `after` (JSON, alleen de gewijzigde velden), `changed_by` (de naam uit spic als de export die
meegeeft, of de gebruiker van PDC), `recorded_at`. Hieruit volgt "gewijzigd sinds je laatste bezoek", berekend bij het
openen van het scherm.

### `assignment_log` (het logboek van de toewijzingen, alleen aanvullend)

`id`, `recorded_at` (UTC), `user_id` en `user_name` (zoals bij de aanmelding), `action` (`proposed`, `confirmed`,
`cancelled`, `name_changed`, `hours_recorded`, `checked`, ...), `assignment_id`, `position_id`, `booking_id`,
`interpreter_id`, `interpreter_name` (momentopname), `meeting_id`, **`meeting_snapshot`** (JSON: herkomst, ID van spic,
datum, dagdeel, begin, einde, zaal, status, versie en wijzigingsnummer van spic, titel), `reason`.

- **Alleen aanvullend, afgedwongen in de databank:** triggers weigeren elke UPDATE en DELETE op `assignment_log` en
  `meeting_changes`. Toewijzingen zelf worden ook nooit gewist, alleen geannuleerd.
- **Werklijst "gewijzigd sinds de bevestiging":** vergelijk de huidige datum, begin, einde, zaal en status met de
  momentopname van de laatste bevestiging van elke toewijzing. De planner sluit een geval af met een regel `checked`,
  die een nieuwe momentopname bewaart.
- **Werklijst "geannuleerd met toegewezen tolk":** vergaderingen met status `cancelled` of `deleted`, of in een week die
  terug in concept staat, met toewijzingen die niet geannuleerd zijn.

### `sync_state` (één rij) en het slot

`last_change_number`, `last_success_at`, `last_attempt_at`, `last_error`, `last_full_comparison_at`,
`spic_highest_number`. Elke reeks wijzigingen wordt in **één transactie** toegepast, samen met het nieuwe
`last_change_number`: een onderbreking laat niets half achter, en opnieuw "sinds N" vragen geeft hetzelfde resultaat. Het
slot is een bestandsslot naast de databank (zoals spic bij zijn migraties doet): is het bezet, dan slaat een tweede
bijwerking haar beurt over.

### `rooms` en `user_visits`

`rooms`: kopie van de vaste lijst zalen van spic (`code`, `description`, `active`). `user_visits`: per gebruiker het
tijdstip van het laatste bezoek, voor "gewijzigd sinds je laatste bezoek".

### Keuzes in dit ontwerp

- Een week die terug naar concept gaat: de vergaderingen worden **verborgen, niet gewist** (ze kunnen toewijzingen
  hebben), en wie toewijzingen heeft, komt op de werklijst.
- Ontbrekende tijden: koppelen aan een tijdvak op het dagdeel, toewijzing niet weigeren, wel markeren als "uur
  onbekend" (FA §2.7).
- Testgegevens voor de werkbank in de vorm van de export van spic, zodat de koppeling later alleen de bron vervangt.

## 3. Besloten: de databank wordt SQLite

**SQLite**, in WAL-modus, zoals spic. De redenen:

- **Hetzelfde als spic** op dezelfde server: dezelfde manier van back-up (de back-upfunctie van SQLite, die een
  consistente kopie maakt terwijl de toepassing draait), dezelfde kennis en dezelfde werkwijze voor migraties.
- **Eenvoudiger op het platform:** één container minder (geen MySQL-container om bij te werken en te beveiligen, geen
  MySQL-wachtwoorden in `.env`), en het hele gegeven is één bestand in één volume.
- **Past bij het gebruik:** enkele planners en duizenden vergaderingen per jaar. WAL laat de webtoepassing en de
  achtergrondtaak tegelijk lezen terwijl er één schrijft; de schrijfacties zijn klein.
- **Getest zoals het draait:** de tests draaien nu al op SQLite, de productie op MySQL; verschillen (bijvoorbeeld de
  Enum-kolommen) worden nu niet getest.
- **De regels van het logboek** (alleen aanvullend) kunnen in SQLite met triggers worden afgedwongen.
- **Nu is overstappen goedkoop:** het prototype heeft geen echte gegevens van belang (bevestigd door de gebruiker op
  10 oktober 2026).

MySQL zou pas nodig zijn bij veel gelijktijdige schrijvers, een aparte databankserver of rapportering die over het
netwerk verbindt; dat is niet het geval. De tweede toepassing voor andere freelancers krijgt hoe dan ook een eigen
databank.

Wat de overstap vraagt (pas na de beslissing): `DATABASE_URL` naar een bestand in een volume (bijvoorbeeld
`sqlite:////data/pdc.db`); bij elke verbinding WAL, `foreign_keys=ON` en een `busy_timeout`; de MySQL-container en
PyMySQL uit `docker-compose.yml` en `requirements.txt`; een migratiehulpmiddel, want `db.create_all()` maakt alleen
nieuwe tabellen en het model gaat veranderen (voorstel: Alembic via Flask-Migrate; alternatief: genummerde SQL-bestanden
zoals spic); een nachtelijke back-up naar een plaats buiten het volume.

## 4. Besloten: de vergrendeling vervalt

De vergrendeling van het hele systeem (fase 1) botst met de besluiten en verdwijnt. In de plaats:

- Beginuur, zaal en annulering van een spic-vergadering: direct via de schrijfroute, zonder vergrendeling (FA §1.4).
- Toewijzen: elke handeling is één kleine transactie die bij het opslaan controleert of de toestand nog klopt (de
  positie is nog vrij, de vergadering bestaat nog). Klopt ze niet, dan een duidelijke melding en de nieuwe toestand,
  zoals het conflictvenster van spic (toen, nu, jouw invoer). Een conflict is er dus alleen als twee planners op
  hetzelfde ogenblik dezelfde positie of vergadering wijzigen.
- Wie wat deed, staat in het logboek.

## 5. Besloten: aanmelding met Authelia, rechten uit spic

- PDC neemt de identiteit over van Authelia (de koppen `Remote-User`, `Remote-Name`, `Remote-Groups`, alleen
  vertrouwd omdat de container alleen via Caddy bereikbaar is), zoals spic. De eigen accounts en wachtwoorden vervallen;
  voor ontwikkeling een dev-modus zoals `OB_AUTH_MODUS=dev` in spic.
- Rechten: wie in spic invoerder of beheerder is, mag PDC beheren (besloten). spic houdt die lijsten in zijn
  beheerscherm bij, niet in lldap. spic geeft die lijst daarom aan PDC via een route met het token van PDC (een
  aanvulling op het contract, §6). PDC hangt dus uitdrukkelijk af van Authelia en van spic. Zolang die route niet
  bestaat, kan PDC de rechten niet uit spic halen; wat PDC dan doet (bijvoorbeeld alleen lezen), is nog te bepalen.
- Lezers: wie in spic alleen leest, mag PDC lezen (te bevestigen).
- De naam van de persoon gaat mee bij elke schrijfactie naar spic ("via PDC").

## 6. Vragen voor de spic-kant (via de gebruiker naar de sessie van `crystalclear`)

- De export levert ook de **vaste lijst zalen** (en eventueel domeinen, assemblees en types, voor de categorie).
- Geeft de export bij een wijziging de **naam van wie wijzigde** mee? Handig voor "gewijzigd door".
- De **lijst van invoerders en beheerders** van spic voor de rechten in PDC (§5).
- De vorm van de JSON (veldnamen zoals in de tabel `vergaderingen` van spic, lege tekst of `null` voor een ontbrekend
  uur).
- In `docs/stand-van-zaken.md` staat bij "Koppeling spic naar de tolkenplanning" nog "Afgewezen door de gebruiker
  (9 okt 2026): ... een schrijfroute van spic", terwijl de beslissingen van 10 oktober en FA Opnamebeheer §13.2 van een
  schrijfroute uitgaan. Graag rechtzetten aan die kant.

## 7. Besloten: de code blijft Engels

Code, commentaar en commitberichten in het Engels, zoals het prototype en de FA. Notities voor de gebruiker, zoals dit
document, mogen Nederlands zijn.

## 8. Voorgestelde volgorde

1. ~~De gebruiker beslist over §3 (databank), §4 (vergrendeling), §5 (aanmelding) en §7 (taal).~~ Gedaan op 10 oktober 2026.
2. Overstap naar SQLite, met migraties en een back-up; de vergrendeling eruit; aanmelding met Authelia (de rechten pas
   als spic de lijst geeft).
3. Het nieuwe vergadermodel, het logboek en de eigen vergaderingen, met testgegevens in de vorm van de export van spic;
   daarna de werkbank. Intussen bouwt de spic-sessie de export (alleen lezen, dus veilig).
4. De koppeling in PDC: bijwerken bij gebruik, de achtergrondtaak, de nachtelijke vergelijking.
5. Als laatste de schrijfroute (beginuur, zaal, annulering).
