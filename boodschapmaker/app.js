'use strict';

// ---------- Vaste lijsten ----------

const WERKLAST = {
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

// Werklast in de kernboodschap, van lang naar kort.
const WERKLAST_KORT = {
  licht: { nl: ['Rustige dag: we eindigen op een normaal uur', 'Rustige dag'],
           fr: ['Journée calme\u00A0: fin à l\u2019heure habituelle', 'Journée calme'] },
  normaal: { nl: ['Normale werklast: we eindigen op een normaal uur', 'Normale dag'],
             fr: ['Charge normale\u00A0: fin à l\u2019heure habituelle', 'Journée normale'] },
  zwaar: { nl: ['Zware dag: het kan later worden dan gewoonlijk', 'Zware dag'],
           fr: ['Journée chargée\u00A0: nous finirons peut-être plus tard', 'Journée chargée'] },
  zeerzwaar: { nl: ['Zeer zware dag met te weinig mensen: elke hulp is welkom', 'Zeer zware dag'],
               fr: ['Journée très chargée, en sous-effectif\u00A0: toute aide est bienvenue', 'Journée très chargée'] },
};

// De kernboodschap is wat in het vak op de homepage staat: KERN_REGELS regels van hooguit
// KERN_MAX tekens. De rest komt onder "Meer info".
const KERN_MAX = 108;
const KERN_REGELS = 3;

// Korte slag om de arm die altijd in de kernboodschap staat.
const KORT_VOORBEHOUD = {
  voorbehoud: { nl: 'Onder voorbehoud.', fr: 'Sous réserve.' },
  inchallah: { nl: 'Inch\u2019Allah.', fr: 'Inch\u2019Allah.' },
  quesera: { nl: 'Que sera, sera.', fr: 'Que sera, sera.' },
  quivivra: { nl: 'Wie leeft, die ziet.', fr: 'Qui vivra verra.' },
};

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
function willekeurigCitaat() {
  const pool = CITATEN.filter(toegelaten);
  return pool.length ? pool[Math.floor(Math.random() * pool.length)].id : null;
}

// ---------- Toestand ----------

function nieuweToestand(datum = morgen()) {
  return {
    datum,
    a: { geen: false, items: [{ nl: '', fr: '' }] },
    b: { geen: false, vergaderingen: [{ uur: '', nl: '', fr: '', wie: '', prio: false }], noot: { nl: '', fr: '' } },
    c: { geen: false, items: [{ nl: '', fr: '', wie: '' }] },
    werklast: 'normaal', werklastNoot: { nl: '', fr: '' },
    coordinator: '',
    deadlines: [],
    slagen: ['agenda', 'vergaderingen'],
    citaat: null,
    moderneAuteurs: false,
    kortVoorbehoud: 'voorbehoud',
    aangepast: {}, // sectie -> { nl: {tekst, basis}, fr: {tekst, basis} }
  };
}

// Ingevuld voorbeeld voor wie de app voor het eerst opent.
function voorbeeldToestand() {
  const t = nieuweToestand();
  t.a.items = [{ nl: 'Verslag van de plenaire vergadering van gisteren nalezen', fr: 'Relire le compte rendu de la séance plénière d\u2019hier' }];
  t.b.vergaderingen = [
    { uur: '09:30', nl: 'Commissie Financiën', fr: 'Commission des Finances', wie: 'Jan', prio: true },
    { uur: '14:00', nl: 'Commissie Leefmilieu', fr: 'Commission de l\u2019Environnement', wie: 'Amina', prio: false },
  ];
  t.c.items = [{ nl: 'Ordonnantie over huisvesting', fr: 'Ordonnance relative au logement', wie: 'Pieter' }];
  t.werklast = 'zwaar';
  t.coordinator = 'Sara';
  t.deadlines = [{ nl: 'Hoorzitting over mobiliteit: verslag klaar', fr: 'Audition sur la mobilité : rapport prêt', datum: '', wie: 'Lotte' }];
  return t;
}

const eersteBezoek = !lezen(OPSLAG_CONCEPT, null);
let state = lezen(OPSLAG_CONCEPT, null) || voorbeeldToestand();
let instellingen = Object.assign({ volgorde: 'nl-fr' }, lezen(OPSLAG_INSTELLINGEN, {}));
if (state.citaat == null) state.citaat = willekeurigCitaat();

// ---------- Tekstvoorstellen per sectie ----------

const SECTIES = [
  {
    key: 'dag', titel: '1. Dag', verplicht: true,
    hint: 'Op welke dag heeft de boodschap betrekking? Kies de datum bovenaan.',
    invoer: () => null,
    tekst: () => ({
      nl: `Boodschap voor ${datumTekst(state.datum, 'nl')}`,
      fr: `Message pour le ${datumTekst(state.datum, 'fr')}`,
    }),
    controle: () => state.datum ? [] : ['Kies een datum.'],
  },
  {
    key: 'a', titel: '2A. Dringend werk van gisteren', verplicht: true,
    hint: 'Werk dat dringend moet worden afgemaakt van de vorige dag. Vink expliciet aan als er niets is.',
    invoer: () => lijstInvoer(state.a, [
      { veld: 'nl', label: 'Omschrijving (NL)' }, { veld: 'fr', label: 'Description (FR)' },
    ], { nl: '', fr: '' }, 'Niets dringends van gisteren'),
    tekst: () => {
      if (state.a.geen) return { nl: 'A. Geen dringend werk van gisteren.', fr: 'A. Pas de travail urgent en suspens depuis hier.' };
      const it = state.a.items.filter(i => !leeg(i.nl) || !leeg(i.fr));
      return {
        nl: 'A. Dringend af te werken van gisteren:\n' + it.map(i => `• ${i.nl}`).join('\n'),
        fr: 'A. À terminer d’urgence (travail d’hier) :\n' + it.map(i => `• ${fr(i)}`).join('\n'),
      };
    },
    controle: () => lijstControle(state.a, 'A', ['nl', 'fr']),
  },
  {
    key: 'b', titel: '2B. Werk van de dag: vergaderingen met verslag', verplicht: true,
    hint: 'Welke vergaderingen zijn er, welke heeft prioriteit en wie werkt op elke vergadering?',
    invoer: vergaderingInvoer,
    tekst: () => {
      if (state.b.geen) {
        return {
          nl: 'B. Vandaag geen vergaderingen waarvoor verslag nodig is.' + noot(state.b.noot.nl),
          fr: 'B. Aujourd’hui, aucune réunion nécessitant un compte rendu.' + noot(state.b.noot.fr),
        };
      }
      const vg = state.b.vergaderingen.filter(v => !leeg(v.nl) || !leeg(v.fr));
      const regel = (v, taal) => {
        const uur = v.uur ? uurTekst(v.uur, taal) + ' ' : '';
        const naam = taal === 'nl' ? v.nl : fr(v);
        const wie = v.wie ? ` (${v.wie})` : '';
        const prio = v.prio ? (taal === 'nl' ? ' – PRIORITEIT' : ' – PRIORITAIRE') : '';
        return `• ${uur}${naam}${wie}${prio}`;
      };
      return {
        nl: 'B. Vergaderingen van vandaag (verslag):\n' + vg.map(v => regel(v, 'nl')).join('\n') + noot(state.b.noot.nl),
        fr: 'B. Réunions du jour (compte rendu) :\n' + vg.map(v => regel(v, 'fr')).join('\n') + noot(state.b.noot.fr),
      };
    },
    controle: () => {
      const p = [];
      if (state.b.geen) return noot2(state.b.noot, 'B (opmerking)');
      const vg = state.b.vergaderingen.filter(v => !leeg(v.nl) || !leeg(v.fr));
      if (!vg.length) p.push('B: voeg minstens één vergadering toe, of vink aan dat er geen zijn.');
      vg.forEach((v, i) => {
        if (leeg(v.nl)) p.push(`B: vergadering ${i + 1} heeft geen Nederlandse naam.`);
        if (leeg(v.fr)) p.push(`B: vergadering ${i + 1} heeft geen Franse naam.`);
        if (leeg(v.wie)) p.push(`B: wie werkt op vergadering ${i + 1}?`);
      });
      if (vg.length && !vg.some(v => v.prio)) p.push('B: duid aan welke vergadering prioriteit heeft.');
      return p.concat(noot2(state.b.noot, 'B (opmerking)'));
    },
  },
  {
    key: 'c', titel: '2C. Vertalingen', verplicht: true,
    hint: 'Welke vertalingen staan op het programma, en wie neemt ze op? Vink expliciet aan als er geen zijn.',
    invoer: () => lijstInvoer(state.c, [
      { veld: 'nl', label: 'Vertaling (NL)' }, { veld: 'fr', label: 'Traduction (FR)' }, { veld: 'wie', label: 'Wie' },
    ], { nl: '', fr: '', wie: '' }, 'Geen vertalingen gepland'),
    tekst: () => {
      if (state.c.geen) return { nl: 'C. Geen vertalingen gepland.', fr: 'C. Aucune traduction prévue.' };
      const it = state.c.items.filter(i => !leeg(i.nl) || !leeg(i.fr));
      const wie = i => i.wie ? ` (${i.wie})` : '';
      return {
        nl: 'C. Vertalingen:\n' + it.map(i => `• ${i.nl}${wie(i)}`).join('\n'),
        fr: 'C. Traductions :\n' + it.map(i => `• ${fr(i)}${wie(i)}`).join('\n'),
      };
    },
    controle: () => lijstControle(state.c, 'C', ['nl', 'fr']),
  },
  {
    key: 'werklast', titel: '3. Inschatting van de werklast', verplicht: true,
    hint: 'Wordt het zwaar, of is er genoeg personeel om op een normaal uur te eindigen?',
    invoer: () => [
      el('div', { class: 'keuzes' }, Object.entries(WERKLAST).map(([k, w]) =>
        el('label', { class: 'check' },
          el('input', { type: 'radio', name: 'werklast', checked: state.werklast === k,
            onchange: () => { state.werklast = k; bijwerken(); } }), w.label))),
      tweetaligVeld(state.werklastNoot, 'Bijkomende uitleg (NL, optioneel)', 'Précision (FR, facultatif)'),
    ],
    tekst: () => ({
      nl: WERKLAST[state.werklast].nl + noot(state.werklastNoot.nl),
      fr: WERKLAST[state.werklast].fr + noot(state.werklastNoot.fr),
    }),
    controle: () => noot2(state.werklastNoot, 'Werklast (uitleg)'),
  },
  {
    key: 'coordinator', titel: '4. Coördinator', verplicht: true,
    hint: 'Wie coördineert vandaag? Dit wordt altijd vermeld.',
    invoer: () => el('div', { class: 'row', style: 'grid-template-columns: minmax(0, 360px)' },
      veld('Naam', { value: state.coordinator, oninput: e => { state.coordinator = e.target.value; bijwerken(); } })),
    tekst: () => ({
      nl: `Coördinatie: ${state.coordinator.trim()}`,
      fr: `Coordination : ${state.coordinator.trim()}`,
    }),
    controle: () => leeg(state.coordinator) ? ['Vul de coördinator in.'] : [],
  },
  {
    key: 'deadlines', titel: '5. Specifieke deadlines', verplicht: false,
    hint: 'Eventueel deadlines voor bijzondere projecten (bv. hoorzittingen), en wie eraan werkt.',
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
  {
    key: 'slag', titel: '6. Slag om de arm', verplicht: true,
    hint: 'We kunnen niet alles voorspellen. Vink de voorbehouden aan; het citaat is altijd verplicht.',
    invoer: citaatInvoer,
    tekst: () => {
      const gekozen = SLAGEN.filter(s => state.slagen.includes(s.id));
      const c = CITATEN.find(x => x.id === state.citaat);
      const nl = gekozen.map(s => s.nl);
      const frl = gekozen.map(s => s.fr);
      if (c) {
        nl.push(`Deze prioriteiten kunnen veranderen. Zoals ${c.auteur} het zei: “${c.nl}”`);
        frl.push(`Ces priorités peuvent changer. Comme l’a dit ${AUTEUR_FR[c.auteur] || c.auteur} : « ${c.fr} »`);
      }
      return { nl: nl.join(' '), fr: frl.join(' ') };
    },
    controle: () => CITATEN.some(x => x.id === state.citaat) ? [] : ['Kies een citaat voor de slag om de arm.'],
  },
  {
    key: 'kern', titel: '7. Kernboodschap', verplicht: true, kern: true,
    hint: `Dit staat in het vak op de homepage: ${KERN_REGELS} regels van hooguit ${KERN_MAX} tekens per taal. ` +
      'Regel 1: dag, coördinatie en werklast. Regel 2: de vergaderingen, de prioriteit eerst. ' +
      'Regel 3: achterstand, vertalingen, deadlines en de slag om de arm. Wat niet past, staat onder \u201CMeer info\u201D.',
    invoer: () => el('div', { class: 'row', style: 'grid-template-columns: minmax(0, 360px)' },
      kortVoorbehoudVeld()),
    tekst: () => ({ nl: kernVoorstel('nl'), fr: kernVoorstel('fr') }),
    controle: () => {
      const { uit } = sectieTekst(SECTIES.find(x => x.kern));
      const p = [];
      for (const t of ['nl', 'fr']) {
        const regels = kernRegels(uit[t]);
        if (!regels.length) p.push(`Kernboodschap (${TAALNAAM[t]}) is leeg.`);
        if (regels.length > KERN_REGELS) p.push(`Kernboodschap (${TAALNAAM[t]}): ${regels.length} regels, hooguit ${KERN_REGELS}.`);
        regels.forEach((r, i) => {
          if (r.length > KERN_MAX) p.push(`Kernboodschap (${TAALNAAM[t]}), regel ${i + 1}: ${r.length} tekens, hooguit ${KERN_MAX}.`);
        });
      }
      return p;
    },
  },
];

function kernRegels(tekst) { return tekst.split('\n').map(r => r.trim()).filter(Boolean); }

// Bouwt één regel uit stukken in leesvolgorde. Elk stuk heeft een belang (0 = eerst) en varianten van
// lang naar kort. Eerst komen zoveel mogelijk stukken erin in hun kortste vorm, in volgorde van belang;
// daarna krijgt elk stuk, weer in volgorde van belang, de langste variant die de regel binnen max houdt.
// Geeft `telling.aantal` het aantal stukken dat in de regel staat, als telling meegegeven is.
function bouwRegel(stukken, max = KERN_MAX, telling = {}) {
  const gekozen = new Map();
  const tekst = () => stukken.filter(x => gekozen.has(x)).map(x => gekozen.get(x)).join(' \u00B7 ');
  const opBelang = stukken.filter(x => x.varianten.length).sort((a, b) => a.belang - b.belang);
  for (const stuk of opBelang) {
    gekozen.set(stuk, stuk.varianten[stuk.varianten.length - 1]);
    if (tekst().length > max) gekozen.delete(stuk);
  }
  for (const stuk of opBelang.filter(x => gekozen.has(x))) {
    for (const v of stuk.varianten) {
      gekozen.set(stuk, v);
      if (tekst().length <= max) break;
    }
  }
  telling.aantal = gekozen.size;
  return tekst();
}

// Varianten van een naam: volledig, dan ingekort met een beletselteken.
function namen(naam, voor = '', na = '') {
  return [voor + naam + na, ...[60, 45].filter(n => naam.length > n).map(n => voor + naam.slice(0, n).trimEnd() + '\u2026' + na)];
}

// Stelt de kernboodschap samen in drie regels.
function kernVoorstel(taal) {
  const nl = taal === 'nl';
  const tekstVan = x => (nl ? x.nl : x.fr || '').trim();
  const dp = nl ? ': ' : '\u00A0: ';

  // Regel 1: dag, coördinatie, werklast.
  const [y, m, d] = (state.datum || isoDatum(new Date())).split('-').map(Number);
  const datum = new Date(y, m - 1, d);
  const lang = datum.toLocaleDateString(nl ? 'nl-BE' : 'fr-BE', { weekday: 'long', day: 'numeric', month: 'long' });
  const kort = datum.toLocaleDateString(nl ? 'nl-BE' : 'fr-BE', { weekday: 'short' }).replace('.', '') + ` ${d}/${m}`;
  const hoofd = x => x.charAt(0).toUpperCase() + x.slice(1);
  const coord = state.coordinator.trim();
  const regel1 = bouwRegel([
    { belang: 0, varianten: [hoofd(lang), hoofd(kort)] },
    { belang: 0, varianten: coord ? [(nl ? 'Coördinatie' : 'Coordination') + dp + coord, (nl ? 'Coörd.' : 'Coord.') + dp + coord] : [] },
    { belang: 1, varianten: WERKLAST_KORT[state.werklast][taal] },
  ]);

  // Regel 2: de vergaderingen, de prioritaire eerst.
  let regel2;
  if (state.b.geen) regel2 = nl ? 'Vandaag geen vergaderingen waarvoor verslag nodig is.' : 'Aujourd\u2019hui, aucune réunion nécessitant un compte rendu.';
  else {
    const vg = state.b.vergaderingen.filter(v => tekstVan(v));
    const prio = vg.find(v => v.prio) || vg[0];
    const rest = vg.filter(v => v !== prio);
    const stuk = (v, belang, voor = '') => {
      const uur = v.uur ? ' ' + uurTekst(v.uur, taal) : '';
      const wie = v.wie.trim() ? ` (${v.wie.trim()})` : '';
      return { belang, varianten: [voor + tekstVan(v) + uur + wie, ...namen(tekstVan(v), voor, wie), ...namen(tekstVan(v), voor)] };
    };
    const stukken = prio ? [stuk(prio, 0, nl ? 'Prio: ' : 'Priorité\u00A0: '), ...rest.map((v, i) => stuk(v, i + 1))] : [];
    // Vergaderingen die niet passen, worden geteld.
    const telling = {};
    regel2 = bouwRegel(stukken, KERN_MAX - 14, telling);
    const weg = stukken.length - telling.aantal;
    if (weg > 0) regel2 += nl ? ` \u00B7 +${weg} andere` : ` \u00B7 +${weg} autre${weg > 1 ? 's' : ''}`;
  }

  // Regel 3: achterstand, vertalingen, deadlines, en altijd de korte slag om de arm.
  const slag = (KORT_VOORBEHOUD[state.kortVoorbehoud] || KORT_VOORBEHOUD.voorbehoud)[taal];
  const stukken3 = [];
  const a = state.a.geen ? [] : state.a.items.filter(i => tekstVan(i));
  if (a.length) stukken3.push({ belang: 0, varianten: [
    ...namen(tekstVan(a[0]), nl ? 'Eerst van gisteren: ' : 'D\u2019abord, d\u2019hier\u00A0: '),
    nl ? 'Eerst achterstand van gisteren' : 'D\u2019abord le retard d\u2019hier'] });
  const c = state.c.geen ? [] : state.c.items.filter(i => tekstVan(i));
  if (c.length) {
    const lijst = c.map(i => tekstVan(i) + (i.wie.trim() ? ` (${i.wie.trim()})` : '')).join(', ');
    stukken3.push({ belang: 1, varianten: [(nl ? 'Vertalingen' : 'Traductions') + dp + lijst, (nl ? 'Vertalingen' : 'Traductions') + dp + c.length] });
  }
  const dl = state.deadlines.filter(x => tekstVan(x));
  if (dl.length) stukken3.push({ belang: 2, varianten: namen(tekstVan(dl[0]), (nl ? 'Deadline' : 'Échéance') + dp,
    dl[0].wie.trim() ? ` (${dl[0].wie.trim()})` : '') });
  const regel3 = [bouwRegel(stukken3, KERN_MAX - slag.length - 3), slag].filter(Boolean).join(' \u2013 ');

  return [regel1, regel2, regel3].join('\n');
}

function noot(t) { return leeg(t) ? '' : '\n' + t.trim(); }
function noot2(n, naam) {
  if (leeg(n.nl) && !leeg(n.fr)) return [`${naam}: Nederlandse tekst ontbreekt.`];
  if (!leeg(n.nl) && leeg(n.fr)) return [`${naam}: Franse vertaling ontbreekt.`];
  return [];
}
function lijstControle(sectie, naam, talen) {
  if (sectie.geen) return [];
  const it = sectie.items.filter(i => talen.some(t => !leeg(i[t])));
  if (!it.length) return [`${naam}: vul minstens één punt in, of vink aan dat er niets is.`];
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
    geenVinkje(sectie, geenTekst),
    rijen,
    sectie.geen ? null : sterknop([icoon(PAD.plus), 'Punt toevoegen'], 'roos',
      { onclick: () => { sectie.items.push({ ...sjabloon }); tekenen(); } }),
  ];
}

function vergaderingInvoer() {
  const b = state.b;
  const rijen = b.geen ? [] : b.vergaderingen.map((v, i) => {
    const v1 = (naam, label, type = 'text') =>
      veld(label, { type, value: v[naam], oninput: e => { v[naam] = e.target.value; bijwerken(); } });
    return el('div', { class: 'row', style: 'grid-template-columns: 140px 1fr 1fr 180px auto auto' },
      v1('uur', 'Uur', 'time'), v1('nl', 'Vergadering (NL)'), v1('fr', 'Réunion (FR)'), v1('wie', 'Wie'),
      el('label', { class: 'check check--prio', title: 'Deze vergadering heeft prioriteit' },
        el('input', { type: 'radio', name: 'prio', checked: v.prio,
          onchange: () => { b.vergaderingen.forEach(x => { x.prio = x === v; }); bijwerken(); } }), 'Prioriteit'),
      verwijderKnop(b.vergaderingen, i));
  });
  return [
    geenVinkje(b, 'Geen vergaderingen waarvoor verslag nodig is'),
    rijen,
    b.geen ? null : sterknop([icoon(PAD.plus), 'Vergadering toevoegen'], 'roos',
      { onclick: () => { b.vergaderingen.push({ uur: '', nl: '', fr: '', wie: '', prio: false }); tekenen(); } }),
    el('div', { style: 'margin-top: var(--space-4)' }, tweetaligVeld(b.noot, 'Opmerking (NL, optioneel)', 'Remarque (FR, facultatif)')),
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
  const select = el('select', { class: 'dw-veld__invoer', onchange: e => { state.citaat = Number(e.target.value); bijwerken(); } },
    pool.map(c => el('option', { value: String(c.id), selected: c.id === state.citaat },
      `${c.auteur} (${c.status.toLowerCase()}): ${c.nl.length > 70 ? c.nl.slice(0, 70) + '…' : c.nl}`)));
  if (!pool.some(c => c.id === state.citaat)) select.prepend(el('option', { value: '', selected: true }, '— kies een citaat —'));
  return [
    SLAGEN.map(s => el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: state.slagen.includes(s.id), onchange: e => {
        state.slagen = e.target.checked ? [...state.slagen, s.id] : state.slagen.filter(x => x !== s.id);
        bijwerken();
      } }), `${s.nl} / ${s.fr}`)),
    el('div', { class: 'row', style: 'grid-template-columns: 1fr auto; margin-top: var(--space-4)' },
      el('label', { class: 'dw-veld dw-veld--breed' }, el('span', { class: 'dw-veld__label' }, `Citaat (${pool.length} beschikbaar)`),
        el('span', { class: 'dw-veld__ovaal' }, select)),
      sterknop('Ander citaat kiezen', 'sirius', { onclick: () => { state.citaat = willekeurigCitaat(); tekenen(); } })),
    el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: state.moderneAuteurs, onchange: e => { state.moderneAuteurs = e.target.checked; tekenen(); } }),
      'Ook auteurs van na de 19e eeuw tonen (volgens de nota niet de bedoeling)'),
  ];
}

function kortVoorbehoudVeld() {
  const v = veld('Korte slag om de arm', { onchange: e => { state.kortVoorbehoud = e.target.value; bijwerken(); } }, 'select');
  v.querySelector('select').append(...Object.entries(KORT_VOORBEHOUD).map(([k, x]) =>
    el('option', { value: k, selected: k === state.kortVoorbehoud }, x.nl === x.fr ? x.nl : `${x.nl} / ${x.fr}`)));
  return v;
}

// ---------- Weergave ----------

const talen = () => instellingen.volgorde.split('-');
const TAALNAAM = { nl: 'Nederlands', fr: 'Français' };

function sectieTekst(s) {
  const voorstel = s.tekst();
  const aangepast = state.aangepast[s.key] || {};
  const uit = {};
  for (const t of ['nl', 'fr']) uit[t] = aangepast[t] ? aangepast[t].tekst : voorstel[t];
  return { voorstel, uit, aangepast };
}

function tekenen() {
  const houder = document.getElementById('secties');
  houder.replaceChildren(...SECTIES.map(s => {
    const invoer = s.invoer();
    const [code, naam] = s.titel.split('. ');
    return el('section', { class: 'kaart', id: 'sectie-' + s.key },
      el('div', { class: 'kaart__kop' },
        el('p', { class: 'label kaart__code' }, `Punt ${code} \u00B7 ${s.verplicht ? 'verplicht' : 'optioneel'}`),
        el('h2', { class: 'titel-s' }, naam),
        el('span', { class: 'status klein', role: 'status' })),
      el('p', { class: 'hint' }, s.hint),
      invoer ? el('div', { class: 'invoer' }, invoer) : null,
      el('div', { class: 'cols' }, talen().map(t => el('div', {},
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
  }));
  bijwerken();
}

// De uitgebreide tekst onder "Meer info": alle punten behalve de kernboodschap.
function detailTekst(taal) {
  return SECTIES.filter(s => !s.kern).map(s => sectieTekst(s).uit[taal].trim()).filter(Boolean).join('\n\n');
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
  state = Object.assign(nieuweToestand(), JSON.parse(JSON.stringify(toestand)));
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
