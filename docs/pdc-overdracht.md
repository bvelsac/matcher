# Overdracht voor PDC (Prestatiedatabank voor Conferentietolken)

> **Herkomst.** Momentopname van 10 oktober 2026 van `docs/pdc-overdracht.md` in de repository `bvelsac/crystalclear` (commit `0d37ae6`). De besluiten zelf staan in `docs/stand-van-zaken.md` van die repository; verandert een besluit, dan eerst daar en daarna hier. **Verwijder dit bestand zodra de besluiten in `docs/functional-analysis.md` van deze repository staan** (zie "Wat in de functionele analyse van `matcher` moet veranderen"), zodat er geen tweede bron blijft.

Bedoeld voor een sessie die aan de repository `bvelsac/matcher` gekoppeld is en PDC uitwerkt. PDC is de nieuwe naam van wat tot nu toe "tolkenplanning", "tolkenplanner" of `matcher` heette (de persoon die de tolken plant blijft de tolkenplanner). Dit document vat samen wat in de sessies over `crystalclear` over PDC besloten of besproken is, wat spic nu al biedt, en wat nog openstaat. Stand: 10 oktober 2026. De bron van elk punt staat in `docs/stand-van-zaken.md` van `crystalclear`; bij verschil gaat dat bestand voor.

## Wat PDC is

- Er bestaan al een **README en veel code voor fase 1 van het prototype** in `matcher` (Flask, MySQL, eigen aanmelding, vergaderingen nu met de hand ingevoerd, een functionele analyse). Dat is het uitgangspunt; dit document zegt wat intussen besloten is en wat daardoor verandert.
- Het hulpmiddel van de **tolkenplanner**, die er ongeveer 95 % van haar tijd mee bezig is: tolken zoeken, aan vergaderingen toewijzen, verschuiven. Het hoofdscherm is een **werkbank**, geen formulier.
- Voor **alle** vergaderingen zijn tolken nodig, ook als er geen verslag of transcriptie van komt.
- Een scherm voor alle invoerders en beheerders van spic (geen aparte rol); alle invoerders mogen PDC beheren.
- PDC bewaart de **toewijzingen** zorgvuldig gedocumenteerd: veel logging, een eigen alleen-aanvullend logboek met een momentopname van de vergadering bij elke toewijzing.
- Later komt een vergelijkbare toepassing voor een andere categorie freelancers, die ook van de gegevens van spic afhangt: hetzelfde patroon, geen uitbreiding van spic.

## Architectuur (besloten, behalve het laatste punt)

- **Twee aparte toepassingen, elk met een eigen databank.** spic is de enige bron van de vergaderingen. PDC bewaart een **eigen kopie** van elke vergadering (ook als ze later in spic verdwijnt: een verwijdering in spic wist de rij echt) en schrijft nooit rechtstreeks in de databank van spic. Redenen: eigen back-up en herstel (een herstel van spic mag toewijzingen niet terugdraaien), eigen bewaartermijn en toegang voor de persoonsgegevens van freelancers, en PDC blijft werken als spic even stilligt.
- **Bijwerken van de kopie:** bij gebruik (opent iemand een scherm, dan eerst bijwerken) **én** door een achtergrondtaak op de server, ook zonder open scherm. Voorstel van de uitwerking: elke 5 minuten één vraag "sinds N", een slot zodat twee bijwerkingen tegelijk niets dubbel doen, onderaan het scherm "kopie bijgewerkt tot nummer N om …" met een waarschuwing als dat te oud is, spic onbereikbaar is geen fout, en 's nachts een volledige vergelijking die afwijkingen herstelt (ook na het terugzetten van spic uit een back-up). Werken zonder achtergrondtaak is geen optie.
- **Geen polling en geen live meldingen** in het scherm: een openstaande weergave ververst bij het herladen; "gewijzigd sinds je laatste bezoek" wordt berekend bij het openen van het scherm.
- **Beantwoord (10 oktober 2026, gebruiker):** PDC draait in productie **op dezelfde server en in dezelfde omgeving als spic, span en jaarkalender**. Gevolgen (voorstellen, nog niet besloten):
  - PDC wordt een **eigen compose-project** op het gedeelde Docker-netwerk `infracriv`, met eigen volumes en een eigen versie en tag (`pdc-vX.Y.Z` of de naam die de gebruiker kiest), zodat een uitrol van PDC spic en span niet herstart en andersom. Zo werkt `crystalclear` ook (`compose.yaml`, `spic/docs/uitrol.md`).
  - PDC bereikt spic **binnen dat netwerk** (`http://spic:8000/…`), niet via Caddy en Authelia. Daarom krijgen de export en de schrijfroute van spic een **eigen token** (uit de `.env`, nooit in een repository) in plaats van de koppen van Authelia. Die koppen (`Remote-User`) vertrouwt spic alleen als ze via Caddy komen: een andere container op het netwerk kan ze namaken (zie `spic/docs/uitrol.md`, stap 4). Zet dus alleen vertrouwde containers op dat netwerk.
  - Toegang voor mensen loopt zoals bij spic: een route in de Caddyfile en een regel in Authelia, in `CAL` (repo `infracriv`), alleen op uitdrukkelijke vraag van de gebruiker en daarna met een herlaadbeurt van Caddy en Authelia.
  - Back-up en de achtergrondtaak draaien op dezelfde server; een nachtelijke back-up van PDC is nodig (de toewijzingen zijn niet uit spic terug te halen).
- **Open, voor de PDC-sessie:** de **databank**. `matcher` gebruikt nu MySQL. De gebruiker zei eerder dat `matcher` nog in een embryonale fase is en gerust op SQLite kan worden overgezet. Voorstel: SQLite zoals spic (één bestand in een volume, WAL-modus, een consistente back-up met `sqlite3.backup`, geen aparte databankcontainer), tenzij er een concrete reden voor MySQL is. Dockerfile van `matcher`: "Python 3.8, the same version as the production server"; elke container heeft zijn eigen Python, dus dat hoeft niet gelijk te zijn aan wat de server heeft (spic draait op 3.12): overweeg een nieuwere versie.

## Wat PDC van spic krijgt: de regel

- Alleen vergaderingen van weken met status **pre-definitief of definitief** gaan naar andere toepassingen (PDC en span). Een conceptweek blijft in spic. In spic staat dit vast in `STATUSSEN_VOOR_AFNEMERS` (`spic/app/planning.py`) en in het tabblad Vaste regels.
- **Pre-definitief:** de week is ingevuld; verantwoordelijke ambtenaren en coördinatoren mogen nog ontbreken. **Definitief:** ambtenaren en een coördinator per dag zijn ingevuld, en wijzigingen worden gemarkeerd. De status wisselt in elke volgorde.
- De bezettingsstatus van PDC hoeft niet terug naar spic.

## Hoe spic wijzigingen nummert (wat PDC moet volgen)

- Elke wijziging in spic, ook een verandering van de weekstatus, krijgt het volgende nummer in **één doorlopende reeks** voor de hele databank (`volgnr` in de tabel `vergadering_historie`, een AUTOINCREMENT). PDC onthoudt alleen zijn eigen laatste nummer.
- De export (nog te bouwen, FA §13.2): `sinds=N` levert de wijzigingen na N, alleen voor weken die op dat moment pre-definitief of definitief zijn. Een statuswijziging van een week is zelf zo'n item: wordt een week pre-definitief, dan haalt PDC die **hele week** binnen (eerdere wijzigingen uit de conceptperiode waren onzichtbaar); wordt ze weer concept, dan verwijdert PDC ze uit het zichtbare deel.
- **Volg het nummer, niet de versie.** De versie van een vergadering stijgt niet bij afgeleide wijzigingen (herberekenen) en de versie van de planning bestaat alleen voor definitieve weken. De volgnummers wel altijd.
- Is het hoogste nummer in spic lager dan het nummer van PDC (spic uit een back-up teruggezet), dan moet PDC een volledige synchronisatie doen.
- Een vergadering heeft een stabiele ID (`m-xxxxxxxx`) en herkent PDC aan die ID, niet aan datum en uur. Verwijderen wist de rij in spic en wordt uitdrukkelijk gemeld; **herstellen** brengt dezelfde ID terug (een verwijdering gevolgd door dezelfde ID is dus normaal). Een vergadering kan ook naar een andere week verhuizen (dezelfde ID, andere `maandag`).

## Wat een vergadering in spic is (voor het model van de kopie)

Velden die PDC nodig heeft of kan krijgen: `id`, `maandag` (de week), `status` (`gepland` of `geannuleerd`), `versie`, `datum`, `periode` (`AM` of `PM`), `start_soort` (`uur` of `na-afloop`), `start_uur`, `na_vergadering` (alleen een verwijzing voor de tekst), `effectief_begin` en `verwacht_einde` (**kunnen leeg zijn**: bij "na afloop van" wordt niets berekend), `einde_bron`, `zaal`, `domein`, `assemblee`, `type`, `volgnummer` en `volgnummer2`, `vragen` (per agendapunt het aantal vragen in het Nederlands en in het Frans), `ambtenaren`, `commentaar`, `prioriteit`, `termijn`, `transcriberen`, `uitzonderlijk`, `agenda_onbekend`. Tijden zijn Brusselse tijd. Zalen en andere codes komen uit de vaste codelijsten van spic; **de zalen van PDC komen uit die lijst**. Daarnaast bestaan **evenementen** (blokken met een ID dat met `e-` begint, zonder verslag) en een **coördinator per dag**; of PDC die nodig heeft, is niet besproken.

"Na afloop van" is in spic alleen een tekstuele vermelding op de plaats van het beginuur, zonder berekening; het dagdeel stelt de gebruiker zelf in. PDC rekent er dus ook niets mee uit. Voor later (span) kan de standaardduur van het vergaderingstype als indicatie dienen.

## Wijzigen vanuit PDC

- De tolkenplanner wijzigt de basisgegevens van een vergadering maar af en toe: alleen **beginuur, zaal en annulering**, via een kleine actie, direct weggeschreven en **zonder vergrendeling**. **Verwijderen kan alleen in spic**, niet in PDC (daar alleen annuleren).
- Besloten ontwerp: een zeer beperkte **schrijfroute in spic** (beginuur, zaal, annulering, met de naam van de persoon, een token op het interne netwerk). Ze **weigert niets om een versieverschil**: ze zet de waarde direct, ook als de vergadering intussen gewijzigd was, en meldt aan PDC alleen dat de waarde intussen anders was ("het beginuur was intussen 15:00 door Kathy"). Alleen als de vergadering niet meer bestaat of de waarde ongeldig is, wordt de wijziging niet uitgevoerd. Een planner met een verouderd formulier krijgt in PDC een conflictvenster (toen, nu, jouw invoer).
- In spic verschijnen zulke wijzigingen in de historiek onder de naam van de planner met "via PDC", gemarkeerd zoals alle andere. Een ander die dezelfde vergadering in spic open heeft, ziet binnen 30 seconden in een gele balk wat er veranderde ("Beginuur: 14:00 → 14:30, door Anna").
- De schrijfroute bestaat nog niet.

## Eigen vergaderingen in PDC

Er zijn vergaderingen waarvan geen verslag wordt gemaakt; die staan niet in spic maar hebben wel tolken nodig. De secretaresse voert ze zelf in PDC in, in de eigen databank, naast de kopieën van de spic-vergaderingen en in één lijst (met een label "uit spic" of "eigen"). Velden: titel, datum, begin, einde of duur, zaal (uit de vaste lijst zalen van spic), categorie, aantal tolken, notities; geen volgnummer, ambtenaren, agendapunten of beurtrol. **Geen herhaling en geen reeksen** (dat klopt niet met de werkelijkheid): elke eigen vergadering wordt afzonderlijk ingevoerd. Een eigen vergadering kan alleen verwijderd worden zolang er nooit een tolk aan toegewezen was, anders alleen geannuleerd. Open: een latere koppeling als dezelfde vergadering toch in spic opduikt.

## Antwoordformulier voor de tolken (idee, niets beslist)

Zoals nu met Google Forms, maar eigen: één link per ronde met een lange, onraadbare code, die de tolkenplanner zelf mailt; de tolk identificeert zich met zijn e-mailadres of ID; alleen bekende tolken worden aanvaard; een nieuw antwoord van dezelfde tolk vervangt het vorige tot de sluitingsdatum. **Geen mail vanuit het systeem** (geen mailserver, geen mailservice); de planner kan "alle adressen" en "adressen van wie nog niet antwoordde" kopiëren voor haar eigen mailprogramma. Antwoorden komen rechtstreeks in de databank (de CSV-import uit de analyse van `matcher` vervalt). Nog te regelen: een openbare route in `CAL` (alleen `/antwoord/…`, de rest blijft achter Authelia; `CAL` wijzig je alleen op uitdrukkelijke vraag), bescherming tegen misbruik, en of de server vanaf het internet bereikbaar is voor tolken buiten het huis.

## Wat waar gebouwd wordt

- **In de repo `matcher` (PDC):** het model en de databank (eigen kopie, toewijzingen, logboek), de werkbank, het bijwerken van de kopie, eigen vergaderingen, later het antwoordformulier.
- **In de repo `crystalclear` (spic):** de export `GET /api/export?sinds=N` met de zichtbaarheidsregel, een volledige lijst voor de nachtelijke vergelijking, en de schrijfroute. Dit is de spic-kant; het contract (URL, aanmelding met een token, JSON-vorm, het melden van verwijderingen en statuswijzigingen) wordt daar vastgelegd, in FA §13.2 en `docs/stand-van-zaken.md`. De gebruiker is de schakel tussen de twee sessies: wijzigt het contract, vraag dan eerst in de `crystalclear`-sessie.
- Voorstel voor de volgorde (nog niet besproken): eerst in PDC het model en de werkbank met testgegevens; intussen in spic de export (alleen lezen, dus veilig); daarna de koppeling in PDC; de schrijfroute als laatste.

## Afspraken die ook voor PDC passen (uit `CLAUDE.md` van `crystalclear`)

- Code, commentaar en commitberichten in het Nederlands. Documentatie bijhouden: elke beslissing van de gebruiker en elke afgeronde wijziging in `docs/stand-van-zaken.md` van `crystalclear` (de beslissingen over de koppeling) en in de eigen README van `matcher`.
- Een sessie verbindt **nooit** zelf met de server (geen `ssh`, `scp`, `rsync`). Uitrollen gaat via GitHub Actions; tags maakt de gebruiker. Meld wat er nodig is.
- Sleutels, wachtwoorden en `.env` komen nooit in een repository; tests gebruiken synthetische gegevens, geen echte tolken of toewijzingen.
- `CAL` (Caddy, Authelia, lldap; repo `infracriv`) wijzig je alleen op uitdrukkelijke vraag.
- Eerst een vaste, zichtbaar vermelde regel; een instelling pas als het echt moet. Tests voor elke wijziging; een wijziging aan de pagina krijgt een browsertest.
- `matcher` heeft een README maar nog **geen `CLAUDE.md`** (gecontroleerd op 10 oktober 2026). Maak er een met deze afspraken en de naam PDC.

## Wat in de functionele analyse van `matcher` moet veranderen

Er zijn **twee functionele analyses**: `docs/FA_opnamebeheer_v1.2.md` in `crystalclear` (Banaan = spic, Mango = span, transcriptie; PDC komt er alleen in voor als afnemer, §13.2, herzien op 10 oktober 2026) en `docs/functional-analysis.md` in `matcher` (versie 1.1, Engels, het model van de tolkenplanning). **De tweede is de FA van PDC en is nog niet bijgewerkt**; geen van de beslissingen hierboven staat erin. De PDC-sessie begint met die bij te werken (voor ze code schrijft), zodat de beslissingen op één plaats staan; `crystalclear` beschrijft alleen het contract met spic. Het gaat om:

| Plaats in de FA van `matcher` | Wat verandert |
|---|---|
| Titel en overal | de naam PDC (Prestatiedatabank voor Conferentietolken) naast of in plaats van "Interpreter Mission Management System" en `matcher` |
| §1 Domain Overview, nieuw hoofdstuk | **De vergaderingen komen uit spic**: eigen kopie in PDC, herkenning op de ID van spic, bijwerken bij gebruik en door een achtergrondtaak, nachtelijke vergelijking, alleen pre-definitieve en definitieve weken, één doorlopend wijzigingsnummer, de schrijfroute, een eigen alleen aanvullend logboek. Verwijs naar FA Opnamebeheer §13.2 voor het contract |
| §2.7 Meeting | het model wordt: een vergadering **uit spic** (alleen lezen, behalve beginuur, zaal en annulering via de schrijfroute) of een **eigen** vergadering (volledig bewerkbaar in PDC, geen reeksen, alleen verwijderbaar zonder toewijzing); herkomst, ID van spic, status `gepland` / `geannuleerd` / `verwijderd`. Velden die spic niet kent: `interpreters_needed` (van PDC), en de indeling in `category` moet uit domein, assemblee en type van spic komen (nog te ontwerpen) |
| §2.7, open punt 9 (start en einde of start en duur) | spic geeft een beginuur (of "na afloop van", zonder uur), een optioneel ingevoerd einde en een geschatte duur uit de agenda of het type; `effectief begin` en `einde` kunnen leeg zijn; het dagdeel (AM/PM) is er altijd |
| §2.8 CSV Data Source en §5.1 | vergaderingen komen niet meer via CSV of met de hand; de beschikbaarheden blijven voorlopig via Google Forms (CSV), met als idee later een eigen antwoordformulier (zie hierboven) |
| §5.4 Meeting Cancellation Process, §6.2, §6.3 | annuleringen komen uit spic of via de schrijfroute van PDC; een annulering wist nooit een toewijzing; "geannuleerd met toegewezen tolk" en "gewijzigd sinds de bevestiging" zijn de werklijsten van de tolkenplanner |
| §6.2 Emergency Meeting Added | een nieuwe vergadering ontstaat in spic en komt binnen door de synchronisatie; een eigen vergadering ontstaat in PDC |
| §9 Open Points, punt 3 (gebruikers, rollen en de vergrendeling) | **de vergrendeling in `matcher` (het hele systeem op slot terwijl één persoon toewijst, 4 uur) botst met de besluiten**: beginuur, zaal en annulering moeten direct kunnen, zonder vergrendeling, ook door een andere gebruiker; spic kent geen harde vergrendeling maar samenvoegen per veld. De PDC-sessie beslist of de vergrendeling blijft, kleiner wordt, of vervalt |
| §9, punt 3 (rollen) | alle invoerders en beheerders van spic mogen PDC beheren, geen aparte rol; `matcher` heeft nu eigen accounts (editor en viewer) na de aanmelding bij Authelia. Open: eigen accounts houden, of de identiteit van Authelia en de rollen van spic overnemen. Voor "via PDC" in de historiek van spic moet de naam van de persoon bij de schrijfroute meegaan |
| README en `docs/development-plan.md` | `matcher` is nu "testserver"; PDC draait in productie op dezelfde server als spic. Een nieuwe fase voor de synchronisatie met spic hoort vóór de beschikbaarheden (Phase 2) of ernaast; de eigen vergaderingen en het logboek komen erbij |

Praktisch voor de uitrol: in `CAL` (repo `infracriv`) staan nu alleen de routes `jk`, `spic` en `um`; **er is geen route voor `matcher` of PDC**, en de README van `matcher` noemt ook een DNS-record bij Cloudflare. Beide vragen een uitdrukkelijke vraag van de gebruiker.

## Eerste bericht voor de nieuwe sessie (voorstel)

"We werken aan PDC (Prestatiedatabank voor Conferentietolken, tot nu toe `matcher`). Lees eerst `docs/pdc-overdracht.md` in deze repo, en dan de README, de functionele analyse en de code van fase 1. De besluiten staan in `docs/stand-van-zaken.md` van de repo `bvelsac/crystalclear` (koppel die repo als tweede repo, of vraag mij de tekst). Werk als eerste stap `docs/functional-analysis.md` bij met de tabel 'Wat in de functionele analyse van `matcher` moet veranderen' uit de overdracht. Maak een lijst van wat in het prototype afwijkt van wat besloten is (kopie van de vergaderingen uit spic in plaats van invoer met de hand, eigen logboek van toewijzingen, eigen vergaderingen, naam PDC, databank), en doe een voorstel voor het model van de eigen kopie en voor de databank (SQLite of MySQL). Bouw nog niets aan de koppeling met spic."
