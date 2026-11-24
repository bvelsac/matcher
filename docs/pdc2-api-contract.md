# PDC2: the APIs of spic and the jaarkalender

Version 1, 24 November 2026. PDC2 reads two services: **spic** (the meetings and their workload) and
the **jaarkalender** (JK: the staff and their presence). Both offer a read-only API in the style of
**HATEOAS** (the user, 24 November 2026): the client knows one entry address and finds everything else by
following links in the answers. The format is **HAL** (`application/hal+json`): links under `_links`,
embedded resources under `_embedded`, templated links per RFC 6570 (`{maandag}`, `{?van,tot}`).

The field names are Dutch, as in the code of spic and JK. PDC2 depends only on the entry address and the
link relations named below, never on the shape of an address.

## Common rules

- **Token.** Every request carries `Authorization: Bearer <token>`. Each consumer has a token of its own,
  set in the service's environment (never in a repository). A request without a valid token gets `401`.
  The routes are for programs inside the server network (`http://spic:8000`, `http://jaarkalender:...`),
  not through Authelia; they do not read `Remote-User`.
- **Errors**: a JSON body `{"fout": "<text>", "_links": {"start": {"href": "<entry>"}}}`, with `400` for a
  wrong parameter, `401` for a missing or wrong token, `404` for something that does not exist or is not
  visible to this consumer.
- **Read only**: only `GET`. Nothing in the answers says why someone is absent.

## spic

Tokens: `SPIC_AFNEMERS="pdc:<token>,pdc2:<token>"`. Which weeks a consumer sees is a fixed rule in spic:
`pdc` sees pre-definitive and definitive weeks (`STATUSSEN_VOOR_AFNEMERS`), `pdc2` sees **all** weeks,
also those in concept (PDC2 FA 2.1).

### `GET /api/afnemers` (entry)

```json
{
  "afnemer": "pdc2",
  "weekstatussen": ["concept", "pre-definitief", "definitief"],
  "_links": {
    "self": {"href": "/api/afnemers"},
    "week": {"href": "/api/afnemers/weken/{maandag}", "templated": true},
    "deze-week": {"href": "/api/afnemers/weken/2026-11-23"}
  }
}
```

### `GET /api/afnemers/weken/{maandag}` (relation `week`)

`maandag` is the Monday of the week (`YYYY-MM-DD`); another date gives `400`. A week this consumer may not
see gives `404`. A week spic has no data for counts as a week in concept: `pdc2` gets status `concept`
and no meetings, `pdc` gets `404`.

```json
{
  "maandag": "2026-11-23",
  "status": "concept",
  "_links": {
    "self": {"href": "/api/afnemers/weken/2026-11-23"},
    "vorige": {"href": "/api/afnemers/weken/2026-11-16"},
    "volgende": {"href": "/api/afnemers/weken/2026-11-30"},
    "start": {"href": "/api/afnemers"}
  },
  "_embedded": {
    "vergaderingen": [
      {
        "id": "m-0a1b2c3d",
        "versie": 3,
        "status": "gepland",
        "datum": "2026-11-23",
        "periode": "PM",
        "effectief_begin": "14:00",
        "verwacht_einde": "17:30",
        "zaal": "R1",
        "domein": "PARL",
        "assemblee": "...",
        "type": "...",
        "volgnummer": 12,
        "volgnummer2": null,
        "termijn": "volgende-dag",
        "agenda_onbekend": false,
        "werkuren": {"nl": 4.0, "fr": 12.0},
        "_links": {"self": {"href": "/api/afnemers/vergaderingen/m-0a1b2c3d"}}
      }
    ]
  }
}
```

- `status`: `gepland` or `geannuleerd`. A deleted meeting is not in the list.
- `termijn`: `zelfde-dag` or `volgende-dag`, as spic holds it (standard per weekday or chosen by hand).
- `werkuren`: the working hours per language from spic's estimate (`schatting`: `nl_uren`, `fr_uren`),
  or `null` when spic has no estimate for the meeting (no questions).
- Empty times are `null`.

### `GET /api/afnemers/vergaderingen/{id}` (relation `self` of a meeting)

One meeting in the same form, with a link `week` to its week. `404` when it does not exist (deleted) or
lies in a week this consumer may not see.

## Jaarkalender

Tokens: `JK_API_TOKENS="pdc2:<token>"`.

### `GET /api/extern` (entry)

```json
{
  "_links": {
    "self": {"href": "/api/extern"},
    "medewerkers": {"href": "/api/extern/medewerkers"},
    "aanwezigheid": {"href": "/api/extern/aanwezigheid{?van,tot}", "templated": true},
    "werkdagen": {"href": "/api/extern/werkdagen{?van,tot}", "templated": true}
  }
}
```

### `GET /api/extern/medewerkers` (relation `medewerkers`)

```json
{
  "_links": {"self": {"href": "/api/extern/medewerkers"}, "start": {"href": "/api/extern"}},
  "_embedded": {
    "medewerkers": [
      {
        "id": "bvan",
        "voornaam": "...",
        "naam": "...",
        "actief": true,
        "moedertaal": "nl",
        "standaardrol": "redacteur",
        "rollen": {"revisor": "mag", "hoofdredacteur": "niet", "vertaler": "liever-niet"},
        "_links": {"self": {"href": "/api/extern/medewerkers/bvan"}}
      }
    ]
  }
}
```

- `moedertaal`: `nl`, `fr` or `null` (not filled in).
- `standaardrol`: `redacteur`, `revisor`, `hoofdredacteur`, `vertaler` or `null`.
- `rollen`: for each role other than the standard role, `mag`, `liever-niet` or `niet`.
- `GET /api/extern/medewerkers/{id}` gives one person in the same form.

### `GET /api/extern/aanwezigheid?van=YYYY-MM-DD&tot=YYYY-MM-DD` (relation `aanwezigheid`)

At most 62 days. Per person and per day the two half-days, AM and PM: `true` when the person works that
half-day by the youngest validated version of their calendar (a working day `E` without a replacement
type, the rule of *Beheer → Aanwezigheden*), else `false`. A person without a validated calendar has
`"gevalideerd": false` and `"dagdelen": null`.

```json
{
  "van": "2026-11-23",
  "tot": "2026-11-27",
  "_links": {
    "self": {"href": "/api/extern/aanwezigheid?van=2026-11-23&tot=2026-11-27"},
    "start": {"href": "/api/extern"}
  },
  "_embedded": {
    "personen": [
      {
        "id": "bvan",
        "gevalideerd": true,
        "dagdelen": {"2026-11-23": [true, true], "2026-11-24": [true, false]},
        "_links": {"medewerker": {"href": "/api/extern/medewerkers/bvan"}}
      }
    ]
  }
}
```

### `GET /api/extern/werkdagen?van=...&tot=...` (relation `werkdagen`)

Per day whether it is a working day of the service (not a weekend day or holiday), for the "next working
day" of PDC2 FA 4.6.

```json
{
  "van": "2026-11-23", "tot": "2026-11-29",
  "dagen": [{"datum": "2026-11-23", "werkdag": true}, {"datum": "2026-11-28", "werkdag": false}],
  "_links": {"self": {"href": "/api/extern/werkdagen?van=2026-11-23&tot=2026-11-29"}, "start": {"href": "/api/extern"}}
}
```

## In PDC2

PDC2 knows only the two entry addresses (`PDC2_SPIC_API`, `PDC2_JK_API`) and the tokens
(`PDC2_SPIC_TOKEN`, `PDC2_JK_TOKEN`). With `PDC2_SOURCE=fake` it answers the same documents itself, with
realistic but fictitious data (`pdc2/fake.py`), so the whole application works before the services are
deployed.
