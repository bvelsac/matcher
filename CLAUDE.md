# PDC (matcher)

**PDC** (Prestatiedatabank voor Conferentietolken) is het hulpmiddel van de tolkenplanner: tolken en bureaus met de
wettelijke prioriteitsvolgorde, beschikbaarheden, boekingen en toewijzingen aan vergaderingen. Tot 10 oktober 2026 heette
het `matcher`, "tolkenplanning" of "tolkenplanner"; de persoon die de tolken plant blijft de tolkenplanner. Schrijf in
nieuwe documentatie "PDC".

## Waar staat wat

- `docs/functional-analysis.md` (versie 1.2, Engels): de functionele analyse van PDC, met de besluiten.
- `docs/pdc-voorstel.md`: wat in het prototype van fase 1 afwijkt van de besluiten, en de voorstellen die op een
  beslissing van de gebruiker wachten.
- `docs/development-plan.md`: de fasen; `docs/visual-style.md`: de gevraagde stijl.
- De vergaderingen komen uit **spic**, in de repository `bvelsac/crystalclear`. De besluiten over de koppeling staan
  daar in `docs/stand-van-zaken.md`, het contract (export, schrijfroute, token) in `docs/FA_opnamebeheer_v1.2.md` §13.2.
  Wijzigt het contract, vraag dan eerst in de sessie van `crystalclear`; de gebruiker is de schakel tussen de twee.

## Werkwijze

- Commitberichten en nieuwe documentatie in het Nederlands. De bestaande code, het commentaar en de FA zijn in het
  Engels; of nieuwe code Nederlands wordt (zoals in `crystalclear`), beslist de gebruiker (`docs/pdc-voorstel.md` §7).
- Documentatie bijhouden: leg elke beslissing van de gebruiker en elke afgeronde wijziging vast in de FA of de README,
  in dezelfde commit of vlak erna. Een beslissing die de koppeling met spic raakt, hoort ook in
  `docs/stand-van-zaken.md` van `crystalclear`: meld ze aan de gebruiker.
- Eerst een vaste, zichtbaar vermelde regel; een instelling pas als het echt moet.
- Tests voor elke wijziging (`pip install -r requirements-dev.txt`, dan `pytest`; de tests gebruiken een SQLite-databank
  in het geheugen). Een wijziging aan een pagina krijgt een browsertest (Playwright, Chromium staat klaar in de
  cloudomgeving).
- Sleutels, wachtwoorden en `.env` komen nooit in de repository, ook geen voorbeelden met echte waarden. Tests en
  voorbeeldgegevens gebruiken verzonnen namen, geen echte tolken of toewijzingen.
- PDC schrijft nooit rechtstreeks in de databank van spic.

## Uitrollen

- Een sessie verbindt **nooit** zelf met de server (geen `ssh`, `scp`, `rsync`). Uitrollen gaat via GitHub Actions;
  tags maakt de gebruiker. Meld wat er nodig is.
- `CAL` (Caddy, Authelia, lldap; repository `infracriv`) wijzig je alleen op uitdrukkelijke vraag van de gebruiker.
- PDC draait in productie op dezelfde server en in dezelfde omgeving als spic. De testserver van fase 1 staat in
  `docker-compose.yml` en de README.
