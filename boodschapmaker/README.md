# Boodschapmaker

Eenvoudige single page app om de dagelijkse tweetalige boodschap (NL/FR) voor het team op te stellen,
volgens de nota `Systeemuitbreidingen/boodschapmaker.md` in de repo *Notes*.

Openen: `index.html` in een browser (geen server of build nodig).

## Wat de app doet

- Vaste opbouw: dag, programma (A dringend werk van gisteren, B vergaderingen met verslag, C vertalingen),
  werklast, coördinator, eventuele deadlines en een slag om de arm.
- A, B, C, werklast, coördinator en het citaat zijn verplicht. Voor A, B en C moet je expliciet aanvinken
  dat er niets is. Bij B moet elke vergadering een verantwoordelijke hebben en moet er één prioriteit zijn.
- Per punt twee kolommen (Nederlands–Frans of Français–Néerlandais) met een tekstvoorstel dat het systeem
  opbouwt uit de invoer. Je kunt elk voorstel handmatig aanpassen; de app waarschuwt als je maar één taal
  aanpast of als de invoer nadien nog wijzigt.
- Slag om de arm: aan te vinken voorbehouden, plus altijd "Deze prioriteiten kunnen veranderen. Zoals X het
  zei: …" met een citaat uit `citaten.js`. Auteurs van na de 19e eeuw zijn standaard verborgen.
- Voorbeeld in een vak met instelbare breedte, hoogte en maximum aantal tekens; inplannen kan pas als alles
  in orde is en de boodschap in het vak past.
- Inplannen per datum, met een simulatie van wat de homepage toont (vanaf 07:00 op de dag zelf).

## Beperkingen

- Ingeplande boodschappen staan in de `localStorage` van de browser. Gebruik Exporteren (JSON kopiëren) en Importeren om ze
  te bewaren of over te zetten. Voor echt gebruik moet de opslag naar een server (bv. de Flask-app),
  zodat Tullio de boodschap kan ophalen.
- Toegang "enkel voor diensthoofden" kan een statische pagina niet afdwingen; dat moet via de hosting
  (bv. achter de login van de Flask-app).
- Er is geen automatische vertaling: vrije tekst (omschrijvingen, namen van vergaderingen) vul je in beide
  talen in. De vaste zinnen zijn al vertaald.

## Citaten

`citaten.js` is gegenereerd uit `citaten1.json` en `citaten2.json` (100 citaten met NL en FR) uit de map
`Systeemuitbreidingen` van de repo *Notes*.
