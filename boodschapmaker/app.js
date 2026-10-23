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
let instellingen = Object.assign({ volgorde: 'nl-fr', breedte: 520, hoogte: 600, max: 1500 },
  lezen(OPSLAG_INSTELLINGEN, {}));
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
      el('div', { class: 'flex' }, Object.entries(WERKLAST).map(([k, w]) =>
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
      el('div', {}, el('label', {}, 'Naam'),
        el('input', { type: 'text', value: state.coordinator, oninput: e => { state.coordinator = e.target.value; bijwerken(); } }))),
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
];

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
    el('div', {}, el('label', {}, labelNl),
      el('input', { type: 'text', value: obj.nl, oninput: e => { obj.nl = e.target.value; bijwerken(); } })),
    el('div', {}, el('label', {}, labelFr),
      el('input', { type: 'text', value: obj.fr, oninput: e => { obj.fr = e.target.value; bijwerken(); } })));
}

function geenVinkje(sectie, tekst) {
  return el('label', { class: 'check' },
    el('input', { type: 'checkbox', checked: sectie.geen, onchange: e => { sectie.geen = e.target.checked; tekenen(); } }),
    tekst);
}

function verwijderKnop(lijst, i) {
  return el('button', { class: 'small', type: 'button', title: 'Verwijderen',
    onclick: () => { lijst.splice(i, 1); tekenen(); } }, '✕');
}

function lijstInvoer(sectie, velden, sjabloon, geenTekst) {
  const kolommen = velden.map(v => v.veld === 'wie' ? '160px' : '1fr').join(' ') + ' auto';
  const rijen = sectie.geen ? [] : sectie.items.map((item, i) =>
    el('div', { class: 'row', style: `grid-template-columns: ${kolommen}` },
      velden.map(v => el('div', {}, el('label', {}, v.label),
        el('input', { type: 'text', value: item[v.veld] || '', oninput: e => { item[v.veld] = e.target.value; bijwerken(); } }))),
      verwijderKnop(sectie.items, i)));
  return [
    geenVinkje(sectie, geenTekst),
    rijen,
    sectie.geen ? null : el('button', { class: 'small', type: 'button',
      onclick: () => { sectie.items.push({ ...sjabloon }); tekenen(); } }, '+ Punt toevoegen'),
  ];
}

function vergaderingInvoer() {
  const b = state.b;
  const rijen = b.geen ? [] : b.vergaderingen.map((v, i) => {
    const veld = (naam, label, type = 'text') => el('div', {}, el('label', {}, label),
      el('input', { type, value: v[naam], oninput: e => { v[naam] = e.target.value; bijwerken(); } }));
    return el('div', { class: 'row', style: 'grid-template-columns: 100px 1fr 1fr 160px auto auto' },
      veld('uur', 'Uur', 'time'), veld('nl', 'Vergadering (NL)'), veld('fr', 'Réunion (FR)'), veld('wie', 'Wie'),
      el('label', { class: 'check', title: 'Deze vergadering heeft prioriteit' },
        el('input', { type: 'radio', name: 'prio', checked: v.prio,
          onchange: () => { b.vergaderingen.forEach(x => { x.prio = x === v; }); bijwerken(); } }), 'Prioriteit'),
      verwijderKnop(b.vergaderingen, i));
  });
  return [
    geenVinkje(b, 'Geen vergaderingen waarvoor verslag nodig is'),
    rijen,
    b.geen ? null : el('button', { class: 'small', type: 'button',
      onclick: () => { b.vergaderingen.push({ uur: '', nl: '', fr: '', wie: '', prio: false }); tekenen(); } }, '+ Vergadering toevoegen'),
    el('div', { style: 'margin-top:8px' }, tweetaligVeld(b.noot, 'Opmerking (NL, optioneel)', 'Remarque (FR, facultatif)')),
  ];
}

function deadlineInvoer() {
  return [
    state.deadlines.map((d, i) => {
      const veld = (naam, label, type = 'text') => el('div', {}, el('label', {}, label),
        el('input', { type, value: d[naam], oninput: e => { d[naam] = e.target.value; bijwerken(); } }));
      return el('div', { class: 'row', style: 'grid-template-columns: 1fr 1fr 150px 160px auto' },
        veld('nl', 'Project (NL)'), veld('fr', 'Projet (FR)'), veld('datum', 'Deadline', 'date'), veld('wie', 'Wie'),
        verwijderKnop(state.deadlines, i));
    }),
    el('button', { class: 'small', type: 'button',
      onclick: () => { state.deadlines.push({ nl: '', fr: '', datum: '', wie: '' }); tekenen(); } }, '+ Deadline toevoegen'),
  ];
}

function citaatInvoer() {
  const pool = CITATEN.filter(toegelaten);
  const select = el('select', { onchange: e => { state.citaat = Number(e.target.value); bijwerken(); } },
    pool.map(c => el('option', { value: String(c.id), selected: c.id === state.citaat },
      `${c.auteur} (${c.status.toLowerCase()}): ${c.nl.length > 90 ? c.nl.slice(0, 90) + '…' : c.nl}`)));
  if (!pool.some(c => c.id === state.citaat)) select.prepend(el('option', { value: '', selected: true }, '— kies een citaat —'));
  return [
    SLAGEN.map(s => el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: state.slagen.includes(s.id), onchange: e => {
        state.slagen = e.target.checked ? [...state.slagen, s.id] : state.slagen.filter(x => x !== s.id);
        bijwerken();
      } }), `${s.nl} / ${s.fr}`)),
    el('div', { class: 'row', style: 'grid-template-columns: 1fr auto; margin-top:8px' },
      el('div', {}, el('label', {}, `Citaat (${pool.length} beschikbaar)`), select),
      el('button', { type: 'button', onclick: () => { state.citaat = willekeurigCitaat(); tekenen(); } }, '🎲 Ander citaat')),
    el('label', { class: 'check' },
      el('input', { type: 'checkbox', checked: state.moderneAuteurs, onchange: e => { state.moderneAuteurs = e.target.checked; tekenen(); } }),
      'Ook auteurs van na de 19e eeuw tonen (volgens de nota niet de bedoeling)'),
  ];
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
    return el('section', { class: 'card', id: 'sectie-' + s.key, style: 'margin-bottom:16px' },
      el('h2', {}, s.titel,
        el('span', { class: 'badge ' + (s.verplicht ? 'req' : '') }, s.verplicht ? 'verplicht' : 'optioneel'),
        el('span', { class: 'badge status' })),
      el('p', { class: 'hint' }, s.hint),
      invoer ? el('div', { class: 'inputs' }, invoer) : null,
      el('div', { class: 'cols' }, talen().map(t => el('div', {},
        el('div', { class: 'col-head' }, el('span', {}, TAALNAAM[t]),
          el('span', { class: 'flex' },
            el('span', { class: 'badge warn aangepast-label', hidden: true }, 'handmatig aangepast'),
            el('button', { class: 'small herstel', type: 'button', hidden: true, title: 'Het voorstel van het systeem terugzetten',
              onclick: () => { delete (state.aangepast[s.key] || {})[t]; bijwerken(); } }, 'Voorstel herstellen'))),
        el('textarea', { class: 'draft', 'data-sectie': s.key, 'data-taal': t, rows: 3,
          oninput: e => {
            const a = state.aangepast[s.key] = state.aangepast[s.key] || {};
            a[t] = { tekst: e.target.value, basis: s.tekst()[t] };
            bijwerken(e.target);
          } })))),
      el('ul', { class: 'problems' }),
      el('p', { class: 'meta drift', hidden: true }));
  }));
  bijwerken();
}

function volledigeTekst(taal) {
  return SECTIES.map(s => sectieTekst(s).uit[taal].trim()).filter(Boolean).join('\n\n');
}

function alleProblemen() {
  const p = SECTIES.flatMap(s => s.controle());
  for (const t of ['nl', 'fr']) {
    const n = volledigeTekst(t).length;
    if (n > instellingen.max) p.push(`${TAALNAAM[t]}: ${n} tekens, maximum is ${instellingen.max}.`);
  }
  document.querySelectorAll('#preview-cols .preview-box.overflow').forEach(b =>
    p.push(`${TAALNAAM[b.dataset.taal]}: de boodschap past niet integraal in het vak.`));
  return p;
}

function bijwerken(actief) {
  for (const s of SECTIES) {
    const kaart = document.getElementById('sectie-' + s.key);
    if (!kaart) continue;
    const { voorstel, uit, aangepast } = sectieTekst(s);
    kaart.querySelectorAll('textarea.draft').forEach(ta => {
      const t = ta.dataset.taal;
      if (ta !== actief) ta.value = uit[t];
      ta.rows = Math.max(2, uit[t].split('\n').reduce((n, r) => n + Math.max(1, Math.ceil(r.length / 70)), 0));
      ta.classList.toggle('edited', !!aangepast[t]);
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
    kaart.querySelector('.problems').replaceChildren(...probs.concat(enkelEen).map(x => el('li', {}, x)));
    const st = kaart.querySelector('.status');
    st.className = 'badge status ' + (probs.length ? 'err' : 'ok');
    st.textContent = probs.length ? 'onvolledig' : 'in orde';
  }
  voorbeeldTekenen();
  schrijven(OPSLAG_CONCEPT, state);
}

function voorbeeldTekenen() {
  const cols = document.getElementById('preview-cols');
  cols.replaceChildren(...talen().map(t => {
    const tekst = volledigeTekst(t);
    const vak = el('div', { class: 'preview-box', 'data-taal': t,
      style: `width:min(100%, ${instellingen.breedte}px); height:${instellingen.hoogte}px` }, tekst);
    return el('div', {},
      el('div', { class: 'col-head' }, el('span', {}, TAALNAAM[t]),
        el('button', { class: 'small', type: 'button', onclick: () => kopieer(tekst) }, 'Kopiëren')),
      vak,
      el('p', { class: 'meta tellen' }, `${tekst.length} / ${instellingen.max} tekens`));
  }));
  cols.querySelectorAll('.preview-box').forEach(vak => {
    const over = vak.scrollHeight > vak.clientHeight + 1;
    vak.classList.toggle('overflow', over);
    const n = vak.textContent.length;
    const meta = vak.nextElementSibling;
    meta.classList.toggle('err', over || n > instellingen.max);
    if (over) meta.textContent += ' – past niet in het vak';
  });
  const probs = alleProblemen();
  document.getElementById('problemen').replaceChildren(...probs.map(x => el('li', {}, x)));
  const knop = document.getElementById('inplannen');
  knop.disabled = probs.length > 0;
  knop.textContent = `Inplannen voor ${datumTekst(state.datum, 'nl') || '…'}`;
  document.getElementById('plan-status').textContent = probs.length
    ? `Nog ${probs.length} punt(en) op te lossen.`
    : (planning()[state.datum] ? 'Er staat al een boodschap voor deze dag; inplannen overschrijft ze.' : '');
}

function kopieer(tekst) {
  navigator.clipboard?.writeText(tekst).catch(() => {});
}

// ---------- Planning ----------

function planning() { return lezen(OPSLAG_PLANNING, {}); }

function inplannen() {
  const p = planning();
  p[state.datum] = {
    nl: volledigeTekst('nl'), fr: volledigeTekst('fr'),
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
    body.replaceChildren(el('tr', {}, el('td', { colspan: '4', class: 'meta' }, 'Nog niets ingepland.')));
  } else {
    body.replaceChildren(...dagen.map(d => el('tr', {},
      el('td', {}, datumTekst(d, 'nl')),
      el('td', {}, p[d].toestand?.coordinator || ''),
      el('td', {}, new Date(p[d].opgeslagen).toLocaleString('nl-BE')),
      el('td', { class: 'flex' },
        el('button', { class: 'small', type: 'button', onclick: () => laden(p[d].toestand) }, 'Openen'),
        el('button', { class: 'small', type: 'button', onclick: e => tweeStappen(e.currentTarget, 'Zeker verwijderen?', () => {
          const q = planning(); delete q[d]; schrijven(OPSLAG_PLANNING, q); planningTekenen(); simuleren();
        }) }, 'Verwijderen')))));
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
  vak.style.width = `min(100%, ${instellingen.breedte}px)`;
  vak.style.height = `${instellingen.hoogte}px`;
  if (!moment) { vak.textContent = ''; return; }
  const [dag, uur] = moment.split('T');
  const b = planning()[dag];
  if (uur < '07:00') vak.textContent = taal === 'nl' ? '(De boodschap van vandaag verschijnt om 07:00.)' : '(Le message du jour apparaîtra à 7h00.)';
  else if (!b) vak.textContent = taal === 'nl' ? '(Geen boodschap ingepland voor deze dag.)' : '(Aucun message prévu pour ce jour.)';
  else vak.textContent = b[taal];
}

// ---------- Opstart ----------

function init() {
  const datum = document.getElementById('datum');
  datum.value = state.datum;
  datum.addEventListener('change', () => { state.datum = datum.value; bijwerken(); });

  const volgorde = document.getElementById('volgorde');
  volgorde.value = instellingen.volgorde;
  volgorde.addEventListener('change', () => { instellingen.volgorde = volgorde.value; schrijven(OPSLAG_INSTELLINGEN, instellingen); tekenen(); });

  for (const [id, sleutel] of [['vak-b', 'breedte'], ['vak-h', 'hoogte'], ['vak-max', 'max']]) {
    const inp = document.getElementById(id);
    inp.value = instellingen[sleutel];
    inp.addEventListener('input', () => {
      const v = Number(inp.value);
      if (v > 0) { instellingen[sleutel] = v; schrijven(OPSLAG_INSTELLINGEN, instellingen); voorbeeldTekenen(); simuleren(); }
    });
  }

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
