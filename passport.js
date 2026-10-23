// Passaporto dei sapori: mappamondo con i paesi delle cucine provate.
(() => {
  'use strict';

  const $ = (s) => document.querySelector(s);
  const WORLD_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json';
  const TOPO_URL = 'https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js';
  const ITALY = '380';

  // ISO alpha-2 -> codice numerico usato da world-atlas
  const ISO_NUM = {
    cn: '156', jp: '392', kr: '410', tw: '158', mn: '496', th: '764', vn: '704', ph: '608', id: '360', my: '458',
    mm: '104', kh: '116', in: '356', pk: '586', lk: '144', bd: '050', np: '524', af: '004', uz: '860', kg: '417',
    tr: '792', ge: '268', lb: '422', il: '376', ir: '364', ma: '504', eg: '818', tn: '788', er: '232', et: '231',
    so: '706', sn: '686', ng: '566', us: '840', mx: '484', sv: '222', cu: '192', pe: '604', br: '076', ar: '032',
    co: '170', cl: '152', ec: '218', ve: '862', es: '724', pt: '620', fr: '250', be: '056', nl: '528', gb: '826',
    de: '276', at: '040', ch: '756', hu: '348', cz: '203', se: '752', no: '578', dk: '208', ru: '643', ua: '804',
    ro: '642', pl: '616', gr: '300', rs: '688', ba: '070', me: '499', mk: '807', hr: '191', au: '036', sy: '760',
    jo: '400', ps: '275', jm: '388', ht: '332', do: '214', it: '380',
  };
  const NUM_ISO = Object.fromEntries(Object.entries(ISO_NUM).map(([k, v]) => [v, k]));

  // cucine che non corrispondono a una sola bandiera
  const GEO_OVERRIDE = {
    'Kebab': { iso: ['tr'] },
    'Araba / Mediorientale': { iso: ['sy', 'jo', 'ps'] },
    'Scandinava': { iso: ['se', 'no', 'dk'] },
    'Balcanica': { iso: ['rs', 'ba', 'me', 'mk'] },
    'Caraibica': { iso: ['jm', 'ht', 'do'] },
    'Hawaiana / Poke': { pt: [20.8, -156.3], name: 'Hawaii' },
    'Mauriziana': { pt: [-20.2, 57.5], name: 'Mauritius' },
    'Tibetana': { pt: [31.5, 88.5], name: 'Tibet' },
  };

  let regionName;
  try { regionName = new Intl.DisplayNames(['it'], { type: 'region' }); } catch { regionName = null; }

  function isoOfFlag(flag) {
    const cps = [...flag].map((c) => c.codePointAt(0));
    if (cps.length === 2 && cps.every((c) => c >= 0x1f1e6 && c <= 0x1f1ff)) {
      return cps.map((c) => String.fromCharCode(c - 0x1f1e6 + 97)).join('');
    }
    return null;
  }

  function geoOf(cuisine, cu) {
    if (GEO_OVERRIDE[cuisine]) return GEO_OVERRIDE[cuisine];
    const iso = isoOfFlag(cu.flag);
    return iso && ISO_NUM[iso] ? { iso: [iso] } : null; // cucine "miste": nessun paese
  }

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = res;
      s.onerror = rej;
      document.head.appendChild(s);
    });
  }

  let worldMap, countriesLayer, pointsLayer, worldReady;

  function ensureWorld() {
    if (!worldReady) {
      worldReady = Promise.all([fetch(WORLD_URL).then((r) => r.json()), loadScript(TOPO_URL)]).then(([topo]) => {
        const geo = topojson.feature(topo, topo.objects.countries);
        geo.features = geo.features.filter((f) => f.id !== '010'); // senza Antartide
        // Russia e Fiji attraversano il meridiano 180°: sposta le longitudini negative oltre 180
        // per evitare strisce orizzontali attraverso la mappa
        const fixRing = (ring) => {
          if (ring.some(([x]) => x > 160) && ring.some(([x]) => x < -160)) ring.forEach((pt) => { if (pt[0] < 0) pt[0] += 360; });
        };
        for (const f of geo.features) {
          const g = f.geometry;
          const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
          polys.forEach((poly) => poly.forEach(fixRing));
        }
        worldMap = L.map('worldMap', {
          zoomControl: false, attributionControl: false, minZoom: 1, maxZoom: 6, zoomSnap: 0.25,
          worldCopyJump: false, maxBounds: [[-70, -200], [85, 200]], maxBoundsViscosity: 0.8,
        });
        L.control.zoom({ position: 'bottomright' }).addTo(worldMap);
        countriesLayer = L.geoJSON(geo, { style: { weight: 0.6 } }).addTo(worldMap);
        pointsLayer = L.layerGroup().addTo(worldMap);
      });
    }
    return worldReady;
  }

  // stato per paese: { done: Map(cucina -> [locali]), want: Set(cucina) }
  function collect() {
    const { places, status, cuisines } = window.SDM;
    const byCuisine = {};
    for (const p of places) {
      const st = status[p.id];
      if (!st) continue;
      for (const c of p.c) {
        const e = (byCuisine[c] ||= { done: [], want: [] });
        e[st].push(p);
      }
    }
    const countries = {};
    const points = [];
    for (const [c, e] of Object.entries(byCuisine)) {
      const g = geoOf(c, cuisines[c]);
      if (!g) continue;
      if (g.pt) {
        points.push({ c, e, g });
        continue;
      }
      for (const iso of g.iso) {
        const k = ISO_NUM[iso];
        const s = (countries[k] ||= { done: [], want: [] });
        if (e.done.length) s.done.push({ c, places: e.done });
        else if (e.want.length) s.want.push({ c, places: e.want });
      }
    }
    return { byCuisine, countries, points };
  }

  function countryName(id, fallback) {
    const iso = NUM_ISO[id];
    try { return (iso && regionName && regionName.of(iso.toUpperCase())) || fallback; } catch { return fallback; }
  }

  function tipHtml(title, flagIso, s) {
    const { esc } = window.SDM;
    const flag = flagIso ? `<img class="flag" src="https://flagcdn.com/w40/${flagIso}.png" alt=""> ` : '';
    let body;
    if (s && s.done.length) {
      body = s.done.map((d) => `<div>✓ <b>${esc(d.c)}</b>: ${d.places.map((p) => esc(p.n)).join(', ')}</div>`).join('');
    } else if (s && s.want.length) {
      body = s.want.map((d) => `<div>⭐ <b>${esc(d.c)}</b> da provare: ${d.places.map((p) => esc(p.n)).join(', ')}</div>`).join('');
    } else {
      body = '<div class="muted">Ancora da scoprire</div>';
    }
    return `<div class="wtip"><div class="wt">${flag}${esc(title)}</div>${body}</div>`;
  }

  function colorOf(cuisine) {
    const { cuisines, continents } = window.SDM;
    return continents[cuisines[cuisine].cont].color;
  }

  function styleFor(s) {
    if (s && s.done.length) {
      return { fillColor: colorOf(s.done[0].c), fillOpacity: 0.9, color: '#0d1117', weight: 0.6, dashArray: null };
    }
    if (s && s.want.length) {
      const col = colorOf(s.want[0].c);
      return { fillColor: col, fillOpacity: 0.16, color: col, weight: 1.2, dashArray: '3 3' };
    }
    return { fillColor: '#1c2431', fillOpacity: 1, color: '#0d1117', weight: 0.6, dashArray: null };
  }

  function renderMap(data) {
    countriesLayer.eachLayer((layer) => {
      const id = layer.feature.id;
      const name = countryName(id, layer.feature.properties.name);
      if (id === ITALY) {
        layer.setStyle({ fillColor: '#3a4456', fillOpacity: 1, color: '#0d1117', weight: 0.6, dashArray: null });
        layer.bindTooltip(`<div class="wtip"><div class="wt">🏠 Italia</div><div class="muted">Casa nostra 🍝</div></div>`, { sticky: true, className: 'wtip-wrap' });
        return;
      }
      const s = data.countries[id];
      layer.setStyle(styleFor(s));
      layer.bindTooltip(tipHtml(name, NUM_ISO[id], s), { sticky: true, className: 'wtip-wrap' });
    });
    pointsLayer.clearLayers();
    for (const { c, e, g } of data.points) {
      const s = { done: e.done.length ? [{ c, places: e.done }] : [], want: e.done.length ? [] : [{ c, places: e.want }] };
      const st = styleFor(s);
      L.circleMarker(g.pt, { radius: 7, ...st, color: st.fillColor, weight: 2 })
        .bindTooltip(tipHtml(`${g.name}`, null, s), { className: 'wtip-wrap' })
        .addTo(pointsLayer);
    }
  }

  function renderStats(data) {
    const { cuisines, continents, status } = window.SDM;
    const real = Object.keys(cuisines).filter((c) => !c.includes('(mista)'));
    const triedC = real.filter((c) => data.byCuisine[c]?.done.length);
    const countries = Object.values(data.countries).filter((s) => s.done.length).length
      + data.points.filter((p) => p.e.done.length).length;
    const conts = new Set(triedC.map((c) => cuisines[c].cont));
    const nPlaces = Object.values(status).filter((s) => s === 'done').length;
    const pct = Math.round((triedC.length / real.length) * 100);
    $('#passStats').innerHTML = `
      <div class="stat"><b>${triedC.length}<small>/${real.length}</small></b><span>cucine provate</span>
        <div class="bar"><i style="width:${pct}%"></i></div></div>
      <div class="stat"><b>${countries}</b><span>paesi</span></div>
      <div class="stat"><b>${conts.size}<small>/${Object.keys(continents).length}</small></b><span>continenti</span></div>
      <div class="stat"><b>${nPlaces}</b><span>locali provati</span></div>`;
    return triedC;
  }

  function renderList(data, triedC) {
    const { cuisines, flagHtml, esc } = window.SDM;
    const wantC = Object.keys(data.byCuisine).filter((c) => !data.byCuisine[c].done.length && data.byCuisine[c].want.length);
    const doneAll = Object.keys(data.byCuisine).filter((c) => data.byCuisine[c].done.length);
    const card = (c, list, kind) => `
      <div class="pcard ${kind}" style="--c:${colorOf(c)}">
        <div class="pc-head">${flagHtml(cuisines[c].flag)}<b>${esc(c)}</b><small>${esc(cuisines[c].area)}</small></div>
        ${list.map((p) => `<button type="button" class="pc-place" data-id="${p.id}">${kind === 'done' ? '✓' : '⭐'} ${esc(p.n)}${p.r ? ` <span class="stars">★ ${p.r.toFixed(1).replace('.', ',')}</span>` : ''}</button>`).join('')}
      </div>`;
    const left = Object.keys(cuisines).filter((c) => !c.includes('(mista)')).length - triedC.length;
    $('#passList').innerHTML = `
      ${doneAll.length ? `<h3>✓ Provate</h3><div class="pgrid">${doneAll.map((c) => card(c, data.byCuisine[c].done, 'done')).join('')}</div>`
        : '<div class="pempty">Il passaporto è ancora vuoto ✈️<br>Apri un ristorante sulla mappa e premi <b>✓ Provato</b>: il suo paese si colorerà qui.</div>'}
      ${wantC.length ? `<h3>⭐ In programma</h3><div class="pgrid">${wantC.map((c) => card(c, data.byCuisine[c].want, 'want')).join('')}</div>` : ''}
      ${left > 0 ? `<div class="pnext"><span>Ancora <b>${left}</b> cucine da scoprire nella zona</span>
        <button type="button" id="passRandom" class="btn-ghost btn-hot">🌍 Cucina a caso</button></div>` : ''}`;
  }

  async function open() {
    const pass = $('#passport');
    pass.hidden = false;
    requestAnimationFrame(() => pass.classList.add('show'));
    document.body.classList.add('pass-open');
    const data = collect();
    const tried = renderStats(data);
    renderList(data, tried);
    try {
      await ensureWorld();
    } catch {
      window.SDM.toast('Non riesco a caricare la mappa del mondo');
      return;
    }
    worldMap.invalidateSize();
    if (!worldMap._loaded) worldMap.fitBounds([[-50, -165], [72, 175]]);
    renderMap(data);
  }

  function close() {
    const pass = $('#passport');
    pass.classList.remove('show');
    document.body.classList.remove('pass-open');
    setTimeout(() => { pass.hidden = true; }, 250);
  }

  function updateBadge() {
    if (!window.SDM) return;
    const { places, status } = window.SDM;
    const tried = new Set();
    for (const p of places) if (status[p.id] === 'done') p.c.forEach((c) => { if (!c.includes('(mista)')) tried.add(c); });
    $('#passCount').textContent = tried.size;
  }

  document.addEventListener('sdm:change', updateBadge);
  $('#passBtn').addEventListener('click', open);
  $('#passClose').addEventListener('click', close);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('#passport').hidden) close(); });
  $('#passList').addEventListener('click', (e) => {
    const b = e.target.closest('.pc-place');
    if (b) {
      const p = window.SDM.places.find((x) => x.id === b.dataset.id);
      close();
      if (p) setTimeout(() => window.SDM.focusPlace(p), 260);
      return;
    }
    if (e.target.closest('#passRandom')) {
      close();
      setTimeout(() => $('#randCuisine').click(), 260);
    }
  });
})();
