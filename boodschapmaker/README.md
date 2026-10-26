# Boodschapmaker

Eenvoudige single page app om de dagelijkse tweetalige boodschap (NL/FR) voor het team op te stellen,
volgens de nota `Systeemuitbreidingen/boodschapmaker.md` in de repo *Notes*.

Openen: `index.html` in een browser (geen server of build nodig).

De opmaak volgt het design system Dwergster: `dwergster.css` bevat de tokens (Nacht als hoofdthema,
Nevel als licht thema) en de componentstijlen uit dat systeem. De lettertypes komen van Google Fonts.

## Wat de app doet

- Kernboodschap: wat in het vak op de homepage staat, drie regels van ongeveer 108 tekens per taal. Ze
  bevat alleen het essentiële, in deze volgorde:
  1. de harde prioriteiten: eerst het werk van de vorige dag (verplicht: invullen of aanvinken dat er
     niets is), dan eventueel een commissie met voorrang en eventueel een indeling in twee teams;
  2. eventueel de vertalingen, als er plaats is;
  3. altijd een echt of verzonnen citaat als slag om de arm, liefst op een eigen regel.
  De dagagenda staat er niet in: die heeft iedereen al. Het systeem kiest per onderdeel de langste
  formulering die past; je kunt de tekst aanpassen. Citaten die niet passen, zijn gemarkeerd, en
  "Ander citaat kiezen" kiest alleen uit citaten die passen.
- Meer info (optioneel, inklapbaar onder de kernboodschap): vertalingen, voorbehouden, werklast,
  coördinator en deadlines.
- Inplannen kan pas als alles in orde is en de kernboodschap in beide talen in drie regels past.
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
