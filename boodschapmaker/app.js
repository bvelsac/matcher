'use strict';

// ---------- Vaste lijsten ----------

const WERKLAST = {
  geen: { label: 'Niet vermelden', nl: '', fr: '' },
  licht: {
    label: 'Rustig',
    nl: 'Werklast: een rustige dag. We verwachten op een normaal uur te eindigen.',
    fr: 'Charge de travail : une journée calme. Nous prévoyons de terminer à une heure normale.',
  },
  normaal: {
    label: 'Normaal',
    nl: 'Werklast: normaal. Met de huidige bezetting zouden we op een normaal uur moeten eindigen.',
    fr: 'Charge de travail : normale. Avec l’effectif actuel, nous devrions terminer à une heure normale.',
  },
  zwaar: {
    label: 'Zwaar',
    nl: 'Werklast: zwaar. Reken erop dat het later kan worden dan gewoonlijk.',
    fr: 'Charge de travail : lourde. Il est possible que nous terminions plus tard que d’habitude.',
  },
  zeerzwaar: {
    label: 'Zeer zwaar / onderbezetting',
    nl: 'Werklast: zeer zwaar, en we zijn met te weinig. Het wordt zeker een lange dag; elke hulp is welkom.',
    fr: 'Charge de travail : très lourde, et nous sommes en sous-effectif. La journée sera longue ; toute aide est la bienvenue.',
  },
};

// De kernboodschap is wat in het vak op de homepage staat: KERN_REGELS regels van ongeveer
// KERN_MAX tekens. De tekst loopt door over de regels; een nieuwe regel begint ook bij een regeleinde.
const KERN_MAX = 108;
const KERN_REGELS = 3;

const SLAGEN = [
  { id: 'agenda', nl: 'Alles onder voorbehoud van wijzigingen in de agenda.',
    fr: 'Le tout sous réserve de modifications de l’agenda.' },
  { id: 'vergaderingen', nl: 'Er kunnen nog vergaderingen bijkomen of wegvallen.',
    fr: 'Des réunions peuvent encore s’ajouter ou être annulées.' },
  { id: 'duur', nl: 'De duur van de vergaderingen is een inschatting.',
    fr: 'La durée des réunions est une estimation.' },
  { id: 'afwezig', nl: 'Onverwachte afwezigheden kunnen de verdeling nog wijzigen.',
    fr: 'Des absences imprévues peuvent encore modifier la répartition.' },
  { id: 'vertaling', nl: 'Vertalingen kunnen dringender worden dan voorzien.',
    fr: 'Des traductions peuvent devenir plus urgentes que prévu.' },
  { id: 'coordinator', nl: 'Bij onvoorziene omstandigheden stuurt de coördinator de prioriteiten bij.',
    fr: 'En cas d’imprévu, la coordination adaptera les priorités.' },
];

// Auteurs uit de citatenlijsten die (grotendeels) na de 19e eeuw leefden. Volgens de nota
// mogen de figuren ten laatste in de 19e eeuw geleefd hebben; deze worden standaard verborgen.
const MODERN = new Set([
  'Virginia Woolf', 'Franz Kafka', 'Albert Camus', 'Jorge Luis Borges', 'Simone de Beauvoir',
  'Fernando Pessoa', 'C.G. Jung', 'Khalil Gibran', 'Winston Churchill', 'Hannah Arendt',
  'Rainer Maria Rilke', 'Rabindranath Tagore', 'Marcel Proust', 'James Joyce', 'T.S. Eliot',
  'Italo Calvino', 'Gabriel García Márquez', 'Emil Cioran', 'Ludwig Wittgenstein', 'Gabriel Marcel',
  'Albert Einstein', 'Niels Bohr', 'Mahatma Gandhi', 'Nelson Mandela',
]);

// Franse schrijfwijze van auteursnamen die in de lijsten in het Nederlands staan.
const AUTEUR_FR = {
  'Marcus Aurelius': 'Marc Aurèle', 'Seneca': 'Sénèque', 'Epictetus': 'Épictète', 'Heraclitus': 'Héraclite',
  'Socrates': 'Socrate', 'Aristoteles': 'Aristote', 'Laozi': 'Lao-Tseu', 'Zhuangzi': 'Tchouang-Tseu',
  'Cicero': 'Cicéron', 'Jalal ad-Din Rumi': 'Djalâl ad-Dîn Rûmî', 'Omar Khayyam': 'Omar Khayyâm',
  'Teresa van Ávila': 'Thérèse d’Avila', 'Meester Eckhart': 'Maître Eckhart', 'Matsuo Basho': 'Matsuo Bashô',
  'Al-Ghazali': 'Al-Ghazâlî', 'Niccolò Machiavelli': 'Nicolas Machiavel', 'Desiderius Erasmus': 'Érasme',
  'Lev Tolstoj': 'Léon Tolstoï', 'Fjodor Dostojevski': 'Fiodor Dostoïevski', 'Cleanthes': 'Cléanthe',
  'Dante Alighieri': 'Dante', 'Boethius': 'Boèce', 'Plato': 'Platon', 'Democritus': 'Démocrite',
  'Chrysippus': 'Chrysippe', 'Plotinus': 'Plotin', 'Thomas van Aquino': 'Thomas d’Aquin',
  'Maimonides': 'Maïmonide', 'Li Bai (Li Po)': 'Li Bai', 'Dogen Zenji': 'Dôgen Zenji',
};

const CITATEN = window.CITATEN || [];
const OPSLAG_CONCEPT = 'boodschapmaker.concept.v1';
const OPSLAG_PLANNING = 'boodschapmaker.planning.v1';
const OPSLAG_INSTELLINGEN = 'boodschapmaker.instellingen.v1';

// ---------- Hulpfuncties ----------

function isoDatum(d) {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function morgen() { const d = new Date(); d.setDate(d.getDate() + 1); return isoDatum(d); }
function datumTekst(iso, taal) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(taal === 'nl' ? 'nl-BE' : 'fr-BE',
    { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}
function uurTekst(uur, taal) {
  if (!uur) return '';
  return taal === 'nl' ? uur : uur.replace(':', 'h');
}
function lezen(sleutel, standaard) {
  try { const v = localStorage.getItem(sleutel); return v ? JSON.parse(v) : standaard; } catch { return standaard; }
}
function schrijven(sleutel, waarde) {
  try { localStorage.setItem(sleutel, JSON.stringify(waarde)); } catch { /* opslag niet beschikbaar */ }
}
function el(tag, attrs = {}, ...kinderen) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k in e && typeof v !== 'string') e[k] = v;
    else e.setAttribute(k, v);
  }
  for (const k of kinderen.flat(Infinity)) if (k != null) e.append(k);
  return e;
}
// Lijnicoon van 24×24; de stijl van de sterknop zet streek en kleur.
function icoon(pad) {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS(ns, 'path');
  path.setAttribute('d', pad);
  svg.append(path);
  return svg;
}
const PAD = { kruis: 'M6.5 6.5l11 11M17.5 6.5l-11 11', plus: 'M12 5v14M5 12h14' };

// Spiegelveld: een invoerveld van één regel in een ovaal spiegelvlak.
function veld(label, attrs, tag = 'input') {
  const invoer = el(tag, Object.assign(tag === 'input' ? { type: 'text' } : {}, attrs, { class: 'dw-veld__invoer' }));
  return el('label', { class: 'dw-veld' }, el('span', { class: 'dw-veld__label' }, label),
    el('span', { class: 'dw-veld__ovaal' }, invoer));
}

// Sterknop in een sterkleur; standaard klein.
function sterknop(inhoud, kleur, attrs = {}, maat = 'dw-ster--klein') {
  return el('button', Object.assign({ type: 'button', class: `dw-ster ${maat} dw-${kleur}` }, attrs), inhoud);
}

function chip(kleur) { return el('i', { class: `dw-chip dw-${kleur}`, 'aria-hidden': 'true' }); }

const leeg = s => !s || !s.trim();
const fr = item => (item.fr && item.fr.trim()) || '';
const toegelaten = c => state.moderneAuteurs || !MODERN.has(c.auteur);
// Kiest een willekeurig citaat, bij voorkeur een dat in de kernboodschap past.
function willekeurigCitaat() {
  const pool = CITATEN.filter(toegelaten);
  const passend = pool.filter(c => citaatPast(c.id));
  const uit = passend.length ? passend : pool;
  return uit.length ? uit[Math.floor(Math.random() * uit.length)].id : null;
}

// ---------- Toestand ----------

function nieuweToestand(datum = morgen()) {
  return {
    datum,
    a: { geen: false, items: [{ nl: '', fr: '' }] },
    b: { prio: { nl: '', fr: '', wie: '' }, teams: false,
         team1: { wie: '', nl: '', fr: '' }, team2: { wie: '', nl: '', fr: '' } },
    c: { items: [] },
    werklast: 'geen', werklastNoot: { nl: '', fr: '' },
    coordinator: '',
    deadlines: [],
    slagen: [],
    citaat: null,
    moderneAuteurs: false,
    meerInfo: true,
    aangepast: {}, // sectie -> { nl: {tekst, basis}, fr: {tekst, basis} }
  };
}

// Ingevuld voorbeeld voor wie de app voor het eerst opent.
function voorbeeldToestand() {
  const t = nieuweToestand();
  t.a.items = [{ nl: 'Verslag van de plenaire vergadering van gisteren nalezen', fr: 'Relire le compte rendu de la séance plénière d\u2019hier' }];
  t.b.prio = { nl: 'Commissie Financiën', fr: 'Commission des Finances', wie: 'Jan' };
  t.c.items = [{ nl: 'Ordonnantie over huisvesting', fr: 'Ordonnance relative au logement', wie: 'Pieter' }];
  t.werklast = 'zwaar';
  t.coordinator = 'Sara';
  t.deadlines = [{ nl: 'Hoorzitting over mobiliteit: verslag klaar', fr: 'Audition sur la mobilité : rapport prêt', datum: '', wie: 'Lotte' }];
  return t;
}

const eersteBezoek = !lezen(OPSLAG_CONCEPT, null);
let state = normaliseer(lezen(OPSLAG_CONCEPT, null) || voorbeeldToestand());

// Vult ontbrekende velden aan en zet concepten uit een vroegere opzet (met de dagagenda) om.
function normaliseer(t) {
  t = Object.assign(nieuweToestand(), t);
  if (!t.b || !('prio' in t.b)) t.b = nieuweToestand().b;
  if (!Array.isArray(t.c.items)) t.c = { items: [] };
  for (const k of ['dag', 'kern']) delete t.aangepast[k];
  return t;
}
let instellingen = Object.assign({ volgorde: 'nl-fr' }, lezen(OPSLAG_INSTELLINGEN, {}));
if (state.citaat == null) state.citaat = willekeurigCitaat();

// ---------- Tekstvoorstellen per sectie ----------

const SECTIES = [
  {
    key: 'a', titel: '1. Werk van gisteren', verplicht: true,
    hint: 'De eerste harde prioriteit: wat moet eerst worden afgewerkt van de vorige dag? Vink expliciet aan als er niets is.',
    invoer: () => lijstInvoer(state.a, [
      { veld: 'nl', label: 'Omschrijving (NL)' }, { veld: 'fr', label: 'Description (FR)' },
    ], { nl: '', fr: '' }, 'Niets van gisteren'),
    controle: () => lijstControle(state.a, 'Werk van gisteren', ['nl', 'fr']),
  },
  {
    key: 'b', titel: '2. Prioriteit van vandaag', verplicht: false,
    hint: 'Eventueel een commissie die vandaag voorrang krijgt, en eventueel een indeling in twee teams. De agenda zelf hoort hier niet: die heeft iedereen al.',
    invoer: prioriteitInvoer,
    controle: () => [
      ...tweetaligControle(state.b.prio, 'Prioriteit'),
      ...(state.b.teams ? [state.b.team1, state.b.team2].flatMap((t, i) => [
        ...(leeg(t.wie) ? [`Team ${i + 1}: wie zit erin?`] : []),
        ...tweetaligControle(t, `Team ${i + 1}`),
      ]) : []),
    ],
  },
  {
    key: 'c', titel: '3. Vertalingen', verplicht: false, inDetails: true,
    hint: 'Optioneel. Komt in de kernboodschap als er plaats is, en altijd volledig onder “Meer info”.',
    invoer: () => lijstInvoer(state.c, [
      { veld: 'nl', label: 'Vertaling (NL)' }, { veld: 'fr', label: 'Traduction (FR)' }, { veld: 'wie', label: 'Wie' },
    ], { nl: '', fr: '', wie: '' }, null),
    tekst: () => {
      const it = state.c.items.filter(i => !leeg(i.nl) || !leeg(i.fr));
      if (!it.length) return { nl: '', fr: '' };
      const wie = i => i.wie ? ` (${i.wie})` : '';
      return {
        nl: 'Vertalingen:\n' + it.map(i => `• ${i.nl}${wie(i)}`).join('\n'),
        fr: 'Traductions :\n' + it.map(i => `• ${fr(i)}${wie(i)}`).join('\n'),
      };
    },
    controle: () => lijstControle(state.c, 'Vertalingen', ['nl', 'fr']),
  },
  {
    key: 'slag', titel: '4. Citaat', verplicht: true, inDetails: true,
    hint: 'Altijd een echt of verzonnen citaat als slag om de arm. Citaten die niet in de kernboodschap passen, zijn gemarkeerd. ' +
      'De voorbehouden die je aanvinkt, komen onder “Meer info”.',
    invoer: citaatInvoer,
    tekst: () => {
      const gekozen = SLAGEN.filter(s => state.slagen.includes(s.id));
      return { nl: gekozen.map(s => s.nl).join(' '), fr: gekozen.map(s => s.fr).join(' ') };
    },
    controle: () => {
      if (!CITATEN.some(x => x.id === state.citaat)) return ['Kies een citaat.'];
      return citaatPast(state.citaat) ? [] : ['Het citaat past niet in de kernboodschap. Kies een korter citaat of kort de prioriteiten in.'];
    },
  },
  {
    key: 'kern', titel: '5. Kernboodschap', verplicht: true, kern: true,
    hint: `Dit staat in het vak op de homepage: ${KERN_REGELS} regels van ongeveer ${KERN_MAX} tekens per taal. ` +
      'Eerst de harde prioriteiten, dan eventueel de vertalingen, en altijd het citaat.',
    invoer: () => el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: state.meerInfo, onchange: e => { state.meerInfo = e.target.checked; tekenen(); } }),
      'Meer info toevoegen onder de kernboodschap (inklapbaar)'),
    tekst: () => ({ nl: kernVoorstel('nl'), fr: kernVoorstel('fr') }),
    controle: () => {
      const { uit } = sectieTekst(SECTIES.find(x => x.kern));
      const p = [];
      for (const t of ['nl', 'fr']) {
        const regels = kernRegels(uit[t]);
        if (!regels.length) p.push(`Kernboodschap (${TAALNAAM[t]}) is leeg.`);
        if (regels.length > KERN_REGELS) p.push(`Kernboodschap (${TAALNAAM[t]}): ${regels.length} regels, hooguit ${KERN_REGELS}.`);
      }
      return p;
    },
  },
  {
    key: 'werklast', titel: 'Werklast', extra: true, inDetails: true,
    hint: 'Wordt het zwaar, of is er genoeg personeel om op een normaal uur te eindigen?',
    invoer: () => [
      el('div', { class: 'keuzes' }, Object.entries(WERKLAST).map(([k, w]) =>
        el('label', { class: 'check' },
          el('input', { type: 'radio', name: 'werklast', checked: state.werklast === k,
            onchange: () => { state.werklast = k; bijwerken(); } }), w.label))),
      tweetaligVeld(state.werklastNoot, 'Bijkomende uitleg (NL, optioneel)', 'Précision (FR, facultatif)'),
    ],
    tekst: () => ({
      nl: (WERKLAST[state.werklast].nl + noot(state.werklastNoot.nl)).trim(),
      fr: (WERKLAST[state.werklast].fr + noot(state.werklastNoot.fr)).trim(),
    }),
    controle: () => noot2(state.werklastNoot, 'Werklast (uitleg)'),
  },
  {
    key: 'coordinator', titel: 'Coördinator', extra: true, inDetails: true,
    hint: 'Wie coördineert vandaag?',
    invoer: () => el('div', { class: 'row', style: 'grid-template-columns: minmax(0, 360px)' },
      veld('Naam', { value: state.coordinator, oninput: e => { state.coordinator = e.target.value; bijwerken(); } })),
    tekst: () => leeg(state.coordinator) ? { nl: '', fr: '' } : {
      nl: `Coördinatie: ${state.coordinator.trim()}`,
      fr: `Coordination : ${state.coordinator.trim()}`,
    },
    controle: () => [],
  },
  {
    key: 'deadlines', titel: 'Specifieke deadlines', extra: true, inDetails: true,
    hint: 'Deadlines voor bijzondere projecten (bv. hoorzittingen), en wie eraan werkt.',
    invoer: deadlineInvoer,
    tekst: () => {
      const dl = state.deadlines.filter(d => !leeg(d.nl) || !leeg(d.fr));
      if (!dl.length) return { nl: '', fr: '' };
      const regel = (d, taal) => {
        const wanneer = d.datum ? ` – ${datumTekst(d.datum, taal).replace(/ \d{4}$/, '')}` : '';
        return `• ${taal === 'nl' ? d.nl : fr(d)}${wanneer}${d.wie ? ` (${d.wie})` : ''}`;
      };
      return {
        nl: 'Deadlines:\n' + dl.map(d => regel(d, 'nl')).join('\n'),
        fr: 'Échéances :\n' + dl.map(d => regel(d, 'fr')).join('\n'),
      };
    },
    controle: () => {
      const p = [];
      state.deadlines.forEach((d, i) => {
        if (leeg(d.nl) && leeg(d.fr)) return;
        if (leeg(d.nl)) p.push(`Deadline ${i + 1}: Nederlandse omschrijving ontbreekt.`);
        if (leeg(d.fr)) p.push(`Deadline ${i + 1}: Franse omschrijving ontbreekt.`);
      });
      return p;
    },
  },
];

// Breekt de tekst af zoals het vak doet: woorden lopen door tot ongeveer KERN_MAX tekens per regel;
// een regeleinde in de tekst begint een nieuwe regel.
function kernRegels(tekst) {
  const regels = [];
  for (const alinea of tekst.split('\n').map(r => r.trim()).filter(Boolean)) {
    let regel = '';
    // Alleen gewone spaties breken af; een harde spatie (zoals vóór een Frans dubbelpunt) niet.
    for (const woord of alinea.split(/[ \t]+/)) {
      if (regel && (regel + ' ' + woord).length > KERN_MAX) { regels.push(regel); regel = woord; }
      else regel = regel ? regel + ' ' + woord : woord;
    }
    regels.push(regel);
  }
  return regels;
}
function kernPast(tekst) { return kernRegels(tekst).length <= KERN_REGELS; }

// Kiest per stuk een variant (van lang naar kort) zodat het geheel past. Eerst komen de vaste stukken
// erin in hun kortste vorm, in volgorde van belang; daarna krijgt elk vast stuk, weer in volgorde van
// belang, de langste variant die nog past; tot slot komen de optionele stukken erbij als er plaats is.
// samen() zet de gekozen varianten om in tekst.
function kiesVarianten(stukken, samen, past) {
  const gekozen = new Map();
  const tekst = () => samen(stukken.filter(x => gekozen.has(x)).map(x => [x, gekozen.get(x)]));
  const opBelang = stukken.filter(x => x.varianten.length).sort((a, b) => a.belang - b.belang);
  const vast = opBelang.filter(x => !x.optioneel);
  for (const stuk of vast) {
    gekozen.set(stuk, stuk.varianten[stuk.varianten.length - 1]);
    if (!past(tekst())) gekozen.delete(stuk);
  }
  for (const stuk of vast.filter(x => gekozen.has(x))) {
    for (const v of stuk.varianten) {
      gekozen.set(stuk, v);
      if (past(tekst())) break;
    }
  }
  for (const stuk of opBelang.filter(x => x.optioneel)) {
    for (const v of stuk.varianten) {
      gekozen.set(stuk, v);
      if (past(tekst())) break;
      gekozen.delete(stuk);
    }
  }
  return { tekst: tekst(), gekozen };
}

function citaatZin(c, taal) {
  if (!c) return [];
  return taal === 'nl'
    ? [`Deze prioriteiten kunnen veranderen. Zoals ${c.auteur} zei: “${c.nl}”`, `Zoals ${c.auteur} zei: “${c.nl}”`]
    : [`Ces priorités peuvent changer. Comme disait ${AUTEUR_FR[c.auteur] || c.auteur} : « ${c.fr} »`,
       `Comme disait ${AUTEUR_FR[c.auteur] || c.auteur} : « ${c.fr} »`];
}

// Stelt de kernboodschap samen: de harde prioriteiten (werk van gisteren, de prioritaire commissie,
// de twee teams), dan de vertalingen als er plaats is, en het citaat, liefst op een eigen regel.
// Geeft ook terug of het citaat erin staat.
function kernOpbouw(taal, citaatId = state.citaat) {
  const nl = taal === 'nl';
  const tekstVan = x => (nl ? x.nl : x.fr || '').trim();
  const dp = nl ? ': ' : ' : ';
  const stukken = [];

  const a = state.a.geen ? [] : state.a.items.filter(i => tekstVan(i));
  const kopA = nl ? 'Eerst het werk van gisteren afwerken' : 'D’abord terminer le travail d’hier';
  if (a.length) stukken.push({ belang: 0, varianten: [
    `${kopA}${dp}${a.map(tekstVan).join('; ')}.`,
    ...(a.length > 1 ? [`${kopA}${dp}${tekstVan(a[0])} (+${a.length - 1}).`] : []),
    `${kopA}.`] });

  const prio = state.b.prio;
  if (tekstVan(prio)) {
    const wie = prio.wie.trim() ? ` (${prio.wie.trim()})` : '';
    const kop = a.length ? (nl ? 'Daarna voorrang voor ' : 'Ensuite, priorité : ') : (nl ? 'Vandaag voorrang voor ' : 'Aujourd’hui, priorité : ');
    stukken.push({ belang: 1, varianten: [`${kop}${tekstVan(prio)}${wie}.`, `${kop}${tekstVan(prio)}.`] });
  }

  if (state.b.teams) {
    const [t1, t2] = [state.b.team1, state.b.team2];
    const taak = t => tekstVan(t) ? ` (${tekstVan(t)})` : '';
    stukken.push({ belang: 2, varianten: nl
      ? [`Twee teams: ${t1.wie.trim()}${taak(t1)} en ${t2.wie.trim()}${taak(t2)}.`, `Team 1: ${t1.wie.trim()}; team 2: ${t2.wie.trim()}.`]
      : [`Deux équipes : ${t1.wie.trim()}${taak(t1)} et ${t2.wie.trim()}${taak(t2)}.`, `Équipe 1 : ${t1.wie.trim()} ; équipe 2 : ${t2.wie.trim()}.`] });
  }

  const citaat = { belang: 3, varianten: citaatZin(CITATEN.find(x => x.id === citaatId), taal), citaat: true };
  stukken.push(citaat);

  const c = state.c.items.filter(i => tekstVan(i));
  if (c.length) {
    const kop = nl ? 'Vertalingen' : 'Traductions';
    stukken.push({ belang: 4, voorCitaat: true, optioneel: true, varianten: [
      `${kop}${dp}${c.map(i => tekstVan(i) + (i.wie.trim() ? ` (${i.wie.trim()})` : '')).join(', ')}.`,
      `${kop}${dp}${c.length}.`] });
  }

  // Leesvolgorde: prioriteiten, vertalingen, citaat. Het citaat begint liefst op een nieuwe regel.
  const volgorde = x => x.citaat ? 2 : x.voorCitaat ? 1 : 0;
  const maak = scheiding => delen => {
    const g = [...delen].sort((x, y) => volgorde(x[0]) - volgorde(y[0]));
    const voor = g.filter(([x]) => !x.citaat).map(([, v]) => v).join(' ');
    const cit = g.find(([x]) => x.citaat);
    return [voor, cit ? cit[1] : ''].filter(Boolean).join(scheiding);
  };
  // Het citaat op een eigen regel kost plaats: doe dat alleen als de prioriteiten er niet korter door worden.
  const inhoud = r => r.gekozen.has(citaat) * 1e6 +
    [...r.gekozen].filter(([x]) => !x.citaat && !x.optioneel).reduce((n, [, v]) => n + v.length, 0);
  const eigenRegel = kiesVarianten(stukken, maak('\n'), kernPast);
  const doorlopend = kiesVarianten(stukken, maak(' '), kernPast);
  const r = inhoud(doorlopend) > inhoud(eigenRegel) ? doorlopend : eigenRegel;
  return { tekst: r.tekst, metCitaat: r.gekozen.has(citaat) };
}

function kernVoorstel(taal) { return kernOpbouw(taal).tekst; }
function citaatPast(id) { return ['nl', 'fr'].every(t => kernOpbouw(t, id).metCitaat); }

function noot(t) { return leeg(t) ? '' : '\n' + t.trim(); }
function noot2(n, naam) {
  if (leeg(n.nl) && !leeg(n.fr)) return [`${naam}: Nederlandse tekst ontbreekt.`];
  if (!leeg(n.nl) && leeg(n.fr)) return [`${naam}: Franse vertaling ontbreekt.`];
  return [];
}
function tweetaligControle(x, naam) {
  if (leeg(x.nl) && !leeg(x.fr)) return [`${naam}: Nederlandse tekst ontbreekt.`];
  if (!leeg(x.nl) && leeg(x.fr)) return [`${naam}: Franse vertaling ontbreekt.`];
  return [];
}
// Een sectie met 'geen' is verplicht: invullen of aanvinken dat er niets is. Zonder 'geen' mag de lijst leeg zijn.
function lijstControle(sectie, naam, talen) {
  if (sectie.geen) return [];
  const it = sectie.items.filter(i => talen.some(t => !leeg(i[t])));
  if (!it.length) return 'geen' in sectie ? [`${naam}: vul minstens één punt in, of vink aan dat er niets is.`] : [];
  const p = [];
  it.forEach((i, n) => {
    if (leeg(i.nl)) p.push(`${naam}: punt ${n + 1} heeft geen Nederlandse tekst.`);
    if (leeg(i.fr)) p.push(`${naam}: punt ${n + 1} heeft geen Franse vertaling.`);
  });
  return p;
}

// ---------- Invoervelden ----------

function tweetaligVeld(obj, labelNl, labelFr) {
  return el('div', { class: 'row', style: 'grid-template-columns: 1fr 1fr' },
    veld(labelNl, { value: obj.nl, oninput: e => { obj.nl = e.target.value; bijwerken(); } }),
    veld(labelFr, { value: obj.fr, oninput: e => { obj.fr = e.target.value; bijwerken(); } }));
}

function geenVinkje(sectie, tekst) {
  return el('label', { class: 'check' },
    el('input', { type: 'checkbox', checked: sectie.geen, onchange: e => { sectie.geen = e.target.checked; tekenen(); } }),
    tekst);
}

function verwijderKnop(lijst, i) {
  return sterknop(icoon(PAD.kruis), 'ivoor', { 'aria-label': 'Verwijderen', title: 'Verwijderen',
    onclick: () => { lijst.splice(i, 1); tekenen(); } }, 'dw-ster--rond dw-ster--klein');
}

function lijstInvoer(sectie, velden, sjabloon, geenTekst) {
  const kolommen = velden.map(v => v.veld === 'wie' ? '180px' : '1fr').join(' ') + ' auto';
  const rijen = sectie.geen ? [] : sectie.items.map((item, i) =>
    el('div', { class: 'row', style: `grid-template-columns: ${kolommen}` },
      velden.map(v => veld(v.label, { value: item[v.veld] || '', oninput: e => { item[v.veld] = e.target.value; bijwerken(); } })),
      verwijderKnop(sectie.items, i)));
  return [
    geenTekst ? geenVinkje(sectie, geenTekst) : null,
    rijen,
    sectie.geen ? null : sterknop([icoon(PAD.plus), 'Punt toevoegen'], 'roos',
      { onclick: () => { sectie.items.push({ ...sjabloon }); tekenen(); } }),
  ];
}

function prioriteitInvoer() {
  const b = state.b;
  const tekstveld = (obj, k, label) => veld(label, { value: obj[k], oninput: e => { obj[k] = e.target.value; bijwerken(); } });
  const team = (t, n) => el('div', { class: 'row', style: 'grid-template-columns: 220px 1fr 1fr' },
    tekstveld(t, 'wie', `Team ${n}: wie`), tekstveld(t, 'nl', `Taak team ${n} (NL)`), tekstveld(t, 'fr', `Tâche équipe ${n} (FR)`));
  return [
    el('div', { class: 'row', style: 'grid-template-columns: 1fr 1fr 180px' },
      tekstveld(b.prio, 'nl', 'Commissie met voorrang (NL)'), tekstveld(b.prio, 'fr', 'Commission prioritaire (FR)'),
      tekstveld(b.prio, 'wie', 'Wie')),
    el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: b.teams, onchange: e => { b.teams = e.target.checked; tekenen(); } }),
      'Vandaag in twee teams'),
    b.teams ? [team(b.team1, 1), team(b.team2, 2)] : null,
  ];
}

function deadlineInvoer() {
  return [
    state.deadlines.map((d, i) => {
      const v1 = (naam, label, type = 'text') =>
        veld(label, { type, value: d[naam], oninput: e => { d[naam] = e.target.value; bijwerken(); } });
      return el('div', { class: 'row', style: 'grid-template-columns: 1fr 1fr 190px 180px auto' },
        v1('nl', 'Project (NL)'), v1('fr', 'Projet (FR)'), v1('datum', 'Deadline', 'date'), v1('wie', 'Wie'),
        verwijderKnop(state.deadlines, i));
    }),
    sterknop([icoon(PAD.plus), 'Deadline toevoegen'], 'roos',
      { onclick: () => { state.deadlines.push({ nl: '', fr: '', datum: '', wie: '' }); tekenen(); } }),
  ];
}

function citaatInvoer() {
  const pool = CITATEN.filter(toegelaten);
  // Citaten die niet in de kernboodschap passen, staan achteraan en zijn gemarkeerd.
  const past = new Map(pool.map(c => [c.id, citaatPast(c.id)]));
  const geordend = [...pool].sort((x, y) => past.get(y.id) - past.get(x.id));
  const aantalPassend = geordend.filter(c => past.get(c.id)).length;
  const select = el('select', { class: 'dw-veld__invoer', onchange: e => { state.citaat = Number(e.target.value); tekenen(); } },
    geordend.map(c => el('option', { value: String(c.id), selected: c.id === state.citaat },
      `${past.get(c.id) ? '' : '[past niet] '}${c.auteur} (${c.status.toLowerCase()}): ${c.nl.length > 70 ? c.nl.slice(0, 70) + '\u2026' : c.nl}`)));
  if (!pool.some(c => c.id === state.citaat)) select.prepend(el('option', { value: '', selected: true }, '— kies een citaat —'));
  const gekozen = CITATEN.find(c => c.id === state.citaat);
  return [
    el('div', { class: 'row', style: 'grid-template-columns: 1fr auto' },
      el('label', { class: 'dw-veld dw-veld--breed' }, el('span', { class: 'dw-veld__label' }, `Citaat (${aantalPassend} van ${pool.length} passen)`),
        el('span', { class: 'dw-veld__ovaal' }, select)),
      sterknop('Ander citaat kiezen', 'sirius', { onclick: () => { state.citaat = willekeurigCitaat(); tekenen(); } })),
    gekozen ? el('p', { class: 'klein citaat-bron' }, chip(gekozen.status === 'Echt' ? 'azuur' : 'roos'),
      gekozen.status === 'Echt' ? `Echt citaat${gekozen.bron ? ': ' + gekozen.bron : ''}` : 'Verzonnen citaat') : null,
    el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: state.moderneAuteurs, onchange: e => { state.moderneAuteurs = e.target.checked; tekenen(); } }),
      'Ook auteurs van na de 19e eeuw tonen (volgens de nota niet de bedoeling)'),
    el('p', { class: 'label subkop' }, 'Voorbehouden onder \u201CMeer info\u201D'),
    SLAGEN.map(s => el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: state.slagen.includes(s.id), onchange: e => {
        state.slagen = e.target.checked ? [...state.slagen, s.id] : state.slagen.filter(x => x !== s.id);
        bijwerken();
      } }), `${s.nl} / ${s.fr}`)),
  ];
}

// ---------- Weergave ----------

const talen = () => instellingen.volgorde.split('-');
const TAALNAAM = { nl: 'Nederlands', fr: 'Français' };

function sectieTekst(s) {
  const voorstel = s.tekst ? s.tekst() : { nl: '', fr: '' };
  const aangepast = state.aangepast[s.key] || {};
  const uit = {};
  for (const t of ['nl', 'fr']) uit[t] = aangepast[t] ? aangepast[t].tekst : voorstel[t];
  return { voorstel, uit, aangepast };
}

function tekenen() {
  const houder = document.getElementById('secties');
  const eersteExtra = SECTIES.find(s => s.extra);
  houder.replaceChildren(...SECTIES.flatMap(s => {
    const invoer = s.invoer();
    const [code, naam] = s.extra ? [null, s.titel] : s.titel.split('. ');
    const tussenkop = s === eersteExtra ? el('div', { class: 'tussenkop' },
      el('p', { class: 'label kaart__code' }, 'Meer info \u00B7 optioneel'),
      el('h2', { class: 'titel' }, 'Bijkomende informatie'),
      el('p', { class: 'hint' }, 'Komt alleen onder \u201CMeer info\u201D, als je dat aanzet bij de kernboodschap. Laat leeg wat niet nodig is.')) : null;
    const kaart = el('section', { class: 'kaart', id: 'sectie-' + s.key },
      el('div', { class: 'kaart__kop' },
        el('p', { class: 'label kaart__code' }, code ? `Punt ${code} \u00B7 ${s.verplicht ? 'verplicht' : 'optioneel'}` : 'Meer info'),
        el('h2', { class: 'titel-s' }, naam),
        el('span', { class: 'status klein', role: 'status' })),
      el('p', { class: 'hint' }, s.hint),
      invoer ? el('div', { class: 'invoer' }, invoer) : null,
      !s.tekst ? null : el('div', { class: 'cols' }, talen().map(t => el('div', {},
        el('div', { class: 'col-head' }, el('span', { class: 'label' }, TAALNAAM[t]),
          el('span', { class: 'flex' },
            el('span', { class: 'dw-badge dw-glas dw-glas--zacht aangepast-label', hidden: true }, 'Aangepast'),
            sterknop('Voorstel herstellen', 'ivoor', { class: 'dw-ster dw-ster--klein dw-ivoor herstel', hidden: true,
              title: 'Het voorstel van het systeem terugzetten',
              onclick: () => { delete (state.aangepast[s.key] || {})[t]; bijwerken(); } }))),
        el('textarea', { class: 'draft', 'data-sectie': s.key, 'data-taal': t, rows: 3,
          oninput: e => {
            const a = state.aangepast[s.key] = state.aangepast[s.key] || {};
            a[t] = { tekst: e.target.value, basis: s.tekst()[t] };
            bijwerken(e.target);
          } }),
        s.kern ? el('div', { class: 'kernteller' }, Array.from({ length: KERN_REGELS }, (_, i) =>
          el('div', { class: 'dw-glasbalk' },
            el('div', { class: 'dw-glasbalk__kop' }, el('span', { id: `kernteller-${t}-${i}` }, `Regel ${i + 1}`),
              el('span', { class: 'dw-glasbalk__waarde' })),
            el('div', { class: 'dw-glasbalk__spoor', role: 'meter', 'aria-labelledby': `kernteller-${t}-${i}`,
              'aria-valuemin': '0', 'aria-valuemax': String(KERN_MAX) },
              el('span', { class: 'dw-glasbalk__vulling' }))))) : null))),
      el('ul', { class: 'problems klein' }),
      el('p', { class: 'klein drift', hidden: true }));
    return [tussenkop, kaart].filter(Boolean);
  }));
  bijwerken();
}

// De tekst onder "Meer info": vertalingen, voorbehouden en de bijkomende informatie, als dat aanstaat.
function detailTekst(taal) {
  if (!state.meerInfo) return '';
  return SECTIES.filter(s => s.inDetails).map(s => sectieTekst(s).uit[taal].trim()).filter(Boolean).join('\n\n');
}
function kernTekst(taal) { return sectieTekst(SECTIES.find(s => s.kern)).uit[taal].trim(); }

function alleProblemen() { return SECTIES.flatMap(s => s.controle()); }

// Het vak op de homepage: de kernboodschap, met de rest in een inklapbaar blok.
const MEER_INFO = { nl: 'Meer info', fr: 'Plus d\u2019infos' };
function homevak(kern, details, taal) {
  return el('div', { class: 'homevak', lang: taal },
    el('div', { class: 'homevak__kern' }, kernRegels(kern).map(r => el('p', {}, r))),
    details ? el('details', {}, el('summary', { class: 'label' }, MEER_INFO[taal]),
      el('div', { class: 'homevak__details' }, details)) : null);
}

function bijwerken(actief) {
  for (const s of SECTIES) {
    const kaart = document.getElementById('sectie-' + s.key);
    if (!kaart) continue;
    const { voorstel, uit, aangepast } = sectieTekst(s);
    kaart.querySelectorAll('textarea.draft').forEach(ta => {
      const t = ta.dataset.taal;
      if (ta !== actief) ta.value = uit[t];
      ta.rows = s.kern ? KERN_REGELS + 1 : Math.max(2, uit[t].split('\n').reduce((n, r) => n + Math.max(1, Math.ceil(r.length / 70)), 0));
      ta.classList.toggle('edited', !!aangepast[t]);
      const teller = ta.nextElementSibling;
      if (teller && teller.classList.contains('kernteller')) {
        const regels = kernRegels(uit[t]);
        teller.querySelectorAll('.dw-glasbalk').forEach((balk, i) => {
          const n = (regels[i] || '').length;
          balk.querySelector('.dw-glasbalk__waarde').textContent = `${n} / ${KERN_MAX}`;
          balk.querySelector('.dw-glasbalk__spoor').setAttribute('aria-valuenow', String(n));
          balk.querySelector('.dw-glasbalk__vulling').style.setProperty('--waarde', `${Math.min(100, n / KERN_MAX * 100)}%`);
          balk.classList.toggle('te-lang', n > KERN_MAX);
        });
      }
      const kop = ta.previousElementSibling;
      kop.querySelector('.aangepast-label').hidden = !aangepast[t];
      kop.querySelector('.herstel').hidden = !aangepast[t];
    });
    const verouderd = ['nl', 'fr'].filter(t => aangepast[t] && aangepast[t].basis !== voorstel[t]);
    const drift = kaart.querySelector('.drift');
    drift.hidden = !verouderd.length;
    drift.textContent = verouderd.length
      ? `De invoer is gewijzigd na je handmatige aanpassing (${verouderd.map(t => TAALNAAM[t]).join(', ')}). Controleer de tekst of herstel het voorstel.`
      : '';
    const enkelEen = !!aangepast.nl !== !!aangepast.fr ? ['Je paste maar één taal handmatig aan: controleer of de vertaling nog klopt.'] : [];
    const probs = s.controle();
    kaart.querySelector('.problems').replaceChildren(...probs.concat(enkelEen).map(x => el('li', {}, chip('citroen'), x)));
    kaart.querySelector('.status').replaceChildren(chip(probs.length ? 'abrikoos' : 'pistache'), probs.length ? 'Onvolledig' : 'In orde');
  }
  voorbeeldTekenen();
  schrijven(OPSLAG_CONCEPT, state);
}

function voorbeeldTekenen() {
  const cols = document.getElementById('preview-cols');
  const open = new Set([...cols.querySelectorAll('details[open]')].map(d => d.closest('.voorbeeld').dataset.taal));
  cols.replaceChildren(...talen().map(t => {
    const kern = kernTekst(t), details = detailTekst(t);
    const vak = homevak(kern, details, t);
    if (open.has(t)) vak.querySelector('details')?.setAttribute('open', '');
    return el('div', { class: 'voorbeeld', 'data-taal': t },
      el('div', { class: 'col-head' }, el('span', { class: 'label' }, TAALNAAM[t]),
        el('span', { class: 'flex' },
          sterknop('Kern kopiëren', 'sirius', { onclick: () => kopieer(kern) }),
          sterknop('Meer info kopiëren', 'sirius', { onclick: () => kopieer(details) }))),
      vak,
      voorbeeldTeller(kernRegels(kern)));
  }));
  const probs = alleProblemen();
  document.getElementById('problemen').replaceChildren(...probs.map(x => el('li', {}, x)));
  document.getElementById('problemen-melding').hidden = !probs.length;
  const knop = document.getElementById('inplannen');
  knop.disabled = probs.length > 0;
  knop.textContent = `Inplannen voor ${datumTekst(state.datum, 'nl') || '…'}`;
  document.getElementById('plan-status').textContent = probs.length
    ? `Nog ${probs.length} punt(en) op te lossen.`
    : (planning()[state.datum] ? 'Er staat al een boodschap voor deze dag; inplannen overschrijft ze.' : '');
}

function voorbeeldTeller(regels) {
  const fout = regels.length > KERN_REGELS || regels.some(r => r.length > KERN_MAX);
  return el('p', { class: 'klein voorbeeld__teller' }, chip(fout ? 'koraal' : 'pistache'),
    fout ? `Past niet: hooguit ${KERN_REGELS} regels van ${KERN_MAX} tekens`
      : `${regels.length} van ${KERN_REGELS} regels \u00B7 ${regels.map(r => r.length).join(' / ')} tekens`);
}

function duizendtal(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0'); }

function kopieer(tekst) {
  navigator.clipboard?.writeText(tekst).catch(() => {});
}

// ---------- Planning ----------

function planning() { return lezen(OPSLAG_PLANNING, {}); }

function inplannen() {
  const p = planning();
  p[state.datum] = {
    kern: { nl: kernTekst('nl'), fr: kernTekst('fr') }, details: { nl: detailTekst('nl'), fr: detailTekst('fr') },
    toestand: JSON.parse(JSON.stringify(state)), opgeslagen: new Date().toISOString(),
  };
  schrijven(OPSLAG_PLANNING, p);
  planningTekenen();
  voorbeeldTekenen();
  document.getElementById('plan-status').textContent = 'Ingepland.';
}

function planningTekenen() {
  const p = planning();
  const body = document.getElementById('planning');
  const dagen = Object.keys(p).sort();
  if (!dagen.length) {
    body.replaceChildren(el('tr', {}, el('td', { colspan: '4' },
      el('div', { class: 'leeg' }, el('div', { class: 'dw-schijven dw-schijven--fijn leeg__veld', 'aria-hidden': 'true' }),
        el('p', { class: 'klein' }, 'Nog niets ingepland. Vul de boodschap in en klik op \u201CInplannen\u201D.')))));
  } else {
    body.replaceChildren(...dagen.map(d => el('tr', {},
      el('td', {}, datumTekst(d, 'nl')),
      el('td', {}, p[d].toestand?.coordinator || ''),
      el('td', { class: 'data' }, new Date(p[d].opgeslagen).toLocaleString('nl-BE')),
      el('td', {}, el('div', { class: 'flex' },
        sterknop('Openen', 'sirius', { onclick: () => laden(p[d].toestand) }),
        sterknop('Verwijderen', 'ivoor', { onclick: e => tweeStappen(e.currentTarget, 'Zeker verwijderen?', () => {
          const q = planning(); delete q[d]; schrijven(OPSLAG_PLANNING, q); planningTekenen(); simuleren();
        }) }))))));
  }
  simuleren();
}

// Vraagt bevestiging op de knop zelf: de eerste klik verandert de tekst, de tweede voert uit.
function tweeStappen(knop, vraag, actie) {
  if (knop.dataset.bevestig) { delete knop.dataset.bevestig; actie(); return; }
  const oud = knop.textContent;
  knop.dataset.bevestig = '1';
  knop.textContent = vraag;
  knop.classList.add('bevestig');
  setTimeout(() => {
    if (!knop.dataset.bevestig) return;
    delete knop.dataset.bevestig; knop.textContent = oud; knop.classList.remove('bevestig');
  }, 4000);
}

function melden(tekst) {
  const m = document.getElementById('melding');
  m.textContent = tekst;
}

function laden(toestand) {
  state = normaliseer(JSON.parse(JSON.stringify(toestand)));
  document.getElementById('datum').value = state.datum;
  tekenen();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Toont wat de homepage op een gegeven moment zou tonen: de boodschap van die dag, vanaf 07:00.
function simuleren() {
  const moment = document.getElementById('sim-moment').value;
  const taal = document.getElementById('sim-taal').value;
  const vak = document.getElementById('sim-vak');
  if (!moment) { vak.replaceChildren(); return; }
  const [dag, uur] = moment.split('T');
  const b = planning()[dag];
  const leegVak = tekst => homevak(tekst, '', taal);
  if (uur < '07:00') vak.replaceChildren(leegVak(taal === 'nl' ? '(De boodschap van vandaag verschijnt om 07:00.)' : '(Le message du jour apparaîtra à 7h00.)'));
  else if (!b) vak.replaceChildren(leegVak(taal === 'nl' ? '(Geen boodschap ingepland voor deze dag.)' : '(Aucun message prévu pour ce jour.)'));
  // Boodschappen van vóór de kernboodschap hebben alleen een volledige tekst.
  else vak.replaceChildren(b.kern ? homevak(b.kern[taal], b.details[taal], taal) : homevak('', b[taal], taal));
}

// ---------- Opstart ----------

function init() {
  const datum = document.getElementById('datum');
  datum.value = state.datum;
  datum.addEventListener('change', () => { state.datum = datum.value; bijwerken(); });

  const volgorde = document.getElementById('volgorde');
  volgorde.value = instellingen.volgorde;
  volgorde.addEventListener('change', () => { instellingen.volgorde = volgorde.value; schrijven(OPSLAG_INSTELLINGEN, instellingen); tekenen(); });

  const nieuw = document.getElementById('nieuw');
  nieuw.addEventListener('click', () => tweeStappen(nieuw, 'Concept wissen?', () => {
    nieuw.textContent = 'Nieuwe boodschap'; nieuw.classList.remove('bevestig');
    state = nieuweToestand(); state.citaat = willekeurigCitaat(); datum.value = state.datum; melden(''); tekenen();
  }));

  // Neemt de laatst ingeplande boodschap vóór de gekozen dag over als vertrekpunt.
  document.getElementById('kopieer-vorige').addEventListener('click', () => {
    const p = planning();
    const vorige = Object.keys(p).filter(d => d < state.datum).sort().pop();
    if (!vorige) { melden('Er is geen eerder ingeplande boodschap om van te vertrekken.'); return; }
    melden(`Vertrokken van de boodschap van ${datumTekst(vorige, 'nl')}.`);
    const doel = state.datum;
    laden({ ...p[vorige].toestand, datum: doel, aangepast: {}, citaat: willekeurigCitaat() });
  });

  document.getElementById('inplannen').addEventListener('click', inplannen);

  // Exporteren toont de planning als JSON om te kopiëren; importeren leest een JSON-bestand.
  const exportVak = document.getElementById('export-json');
  document.getElementById('export').addEventListener('click', () => {
    exportVak.hidden = false;
    exportVak.value = JSON.stringify(planning(), null, 2);
    exportVak.select();
    navigator.clipboard?.writeText(exportVak.value).then(
      () => melden('De planning is als JSON gekopieerd.'), () => melden('Kopieer de JSON uit het vak.'));
  });
  const imp = document.getElementById('import');
  document.getElementById('import-knop').addEventListener('click', () => imp.click());
  imp.addEventListener('change', async () => {
    const f = imp.files[0]; if (!f) return;
    try {
      const data = JSON.parse(await f.text());
      schrijven(OPSLAG_PLANNING, Object.assign(planning(), data));
      planningTekenen();
      melden('Planning geïmporteerd.');
    } catch { melden('Dit bestand kon niet gelezen worden. Kies een JSON-bestand dat met Exporteren is gemaakt.'); }
    imp.value = '';
  });

  const nu = new Date();
  document.getElementById('sim-moment').value = `${isoDatum(nu)}T${String(nu.getHours()).padStart(2, '0')}:${String(nu.getMinutes()).padStart(2, '0')}`;
  document.getElementById('sim-moment').addEventListener('input', simuleren);
  document.getElementById('sim-taal').addEventListener('change', simuleren);

  if (eersteBezoek) melden('Dit is een ingevuld voorbeeld. Klik op \u201CNieuwe boodschap\u201D om met een leeg concept te beginnen.');
  tekenen();
  planningTekenen();
}

init();
