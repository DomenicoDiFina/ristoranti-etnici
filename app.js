(() => {
  'use strict';

  const CENTERS = {
    legnano: { ll: [45.5966, 8.9128], name: 'Legnano' },
    busto: { ll: [45.6118, 8.8514], name: 'Busto Arsizio' },
    mezzo: { ll: [45.6040, 8.8900], name: 'Legnano / Busto' },
  };
  const PAGE = 80;
  const MAX_RADIUS = 30;
  const TOP_N = 10;
  // classifica: stelle "pesate" sul numero di recensioni (media bayesiana),
  // meno 0,02 stelle per km: a parità di voto vince il più vicino
  const PRIOR = 3.9, PRIOR_WEIGHT = 15, KM_PENALTY = 0.02;
  const $ = (s) => document.querySelector(s);

  // ---------- storage (per-viewer, best effort) ----------
  const store = {
    get(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch { return def; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
  };
  const status = store.get('se-status', {}); // id -> 'want' | 'done'
  const prefs = store.get('se-prefs', {});

  const state = {
    centerKey: prefs.centerKey && prefs.centerKey !== 'gps' ? prefs.centerKey : 'mezzo',
    center: null,
    radius: Math.min(prefs.radius || MAX_RADIUS, MAX_RADIUS),
    noFF: !!prefs.noFF,
    top: prefs.top ?? true,
    sort: prefs.sort || 'best',
    q: '',
    tab: 'all',
    sel: null,
    limit: PAGE,
  };
  state.center = CENTERS[state.centerKey].ll;

  let DATA, cuisines, continents, places = [], visible = [];
  const markers = new Map();

  // ---------- helpers ----------
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const norm = (s) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const fmtKm = (d) => (d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1).replace('.', ',')} km`);

  function flagHtml(flag) {
    const cps = [...flag].map((c) => c.codePointAt(0));
    if (cps.length === 2 && cps.every((c) => c >= 0x1f1e6 && c <= 0x1f1ff)) {
      const iso = cps.map((c) => String.fromCharCode(c - 0x1f1e6 + 97)).join('');
      return `<img class="flag" src="https://flagcdn.com/w40/${iso}.png" alt="" loading="lazy">`;
    }
    return `<span class="emo">${flag}</span>`;
  }

  function haversine(a, b) {
    const R = 6371, r = Math.PI / 180;
    const dLat = (b[0] - a[0]) * r, dLon = (b[1] - a[1]) * r;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  let toastT;
  function toast(msg, { html = false, big = false, ms = 2600 } = {}) {
    const t = $('#toast');
    if (html) t.innerHTML = msg;
    else t.textContent = msg;
    t.classList.toggle('big', big);
    t.classList.add('show');
    clearTimeout(toastT);
    toastT = setTimeout(() => t.classList.remove('show'), ms);
  }

  function savePrefs() {
    store.set('se-prefs', {
      centerKey: state.centerKey, radius: state.radius, noFF: state.noFF, top: state.top, sort: state.sort,
      off: Object.keys(cuisines).filter((n) => !state.sel.has(n)),
    });
  }

  const quality = (p) => (p.r ? (p.r * p.rc + PRIOR * PRIOR_WEIGHT) / (p.rc + PRIOR_WEIGHT) : PRIOR - 0.4);
  const score = (p) => quality(p) - KM_PENALTY * p.dist;
  const fmtStars = (p) => (p.r
    ? `<span class="stars">★ ${p.r.toFixed(1).replace('.', ',')}</span> <span class="rc">(${p.rc.toLocaleString('it-IT')})</span>`
    : '');

  // ---------- map ----------
  const map = L.map('map', { zoomControl: false, preferCanvas: false }).setView(state.center, 11);
  L.control.zoom({ position: 'topright' }).addTo(map);
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/';
  L.tileLayer(`${ESRI}World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`, {
    maxZoom: 19, maxNativeZoom: 16,
    attribution: 'Ristoranti &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, Google · Mappa &copy; Esri, HERE, Garmin',
  }).addTo(map);
  L.tileLayer(`${ESRI}World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}`, { maxZoom: 19, maxNativeZoom: 16, pane: 'shadowPane' }).addTo(map);

  const cluster = L.markerClusterGroup({
    maxClusterRadius: 48,
    disableClusteringAtZoom: 16,
    showCoverageOnHover: false,
    chunkedLoading: true,
    iconCreateFunction(c) {
      const n = c.getChildCount();
      const s = n < 10 ? 34 : n < 50 ? 42 : n < 200 ? 50 : 58;
      return L.divIcon({ html: `<div class="cluster" style="width:${s}px;height:${s}px">${n}</div>`, className: '', iconSize: [s, s] });
    },
  }).addTo(map);

  const ring = L.circle(state.center, { radius: state.radius * 1000, color: '#ff8a5b', weight: 1.5, dashArray: '6 6', fillColor: '#ff8a5b', fillOpacity: 0.035, interactive: false }).addTo(map);
  const home = L.marker(state.center, { icon: L.divIcon({ html: '<div class="home-pin"></div>', className: '', iconSize: [18, 18] }), interactive: false, zIndexOffset: 1000 }).addTo(map);

  function pinIcon(p) {
    const st = status[p.id] || '';
    return L.divIcon({
      html: `<div class="pin ${st}" style="--c:${p.color}">${flagHtml(p.flag)}</div>`,
      className: '', iconSize: [32, 32], iconAnchor: [16, 16], popupAnchor: [0, -16],
    });
  }

  function getMarker(p) {
    let m = markers.get(p.id);
    if (!m) {
      m = L.marker([p.lat, p.lon], { icon: pinIcon(p), title: p.n });
      m.bindPopup(() => popupHtml(p), { maxWidth: 320, autoPanPaddingTopLeft: [window.innerWidth > 760 ? 440 : 10, 20] });
      markers.set(p.id, m);
    }
    return m;
  }

  function popupHtml(p) {
    const st = status[p.id];
    const tags = p.c.map((c) => {
      const cu = cuisines[c];
      return `<span class="tag" style="--c:${continents[cu.cont].color}">${flagHtml(cu.flag)}${esc(c)}</span>`;
    }).join('') + (p.s || []).map((s) => `<span class="tag sp">${esc(s)}</span>`).join('');
    const where = [p.addr, p.city].filter(Boolean).join(', ');
    const web = p.web ? (p.web.startsWith('http') ? p.web : `https://${p.web}`) : '';
    const gq = encodeURIComponent([p.n, p.addr, p.city].filter(Boolean).join(' '));
    const gmaps = p.g || `https://www.google.com/maps/search/?api=1&query=${gq}`;
    return `<div class="pop">
      <h3>${esc(p.n)}</h3>
      ${p.r ? `<div class="rating">${fmtStars(p)} <span class="rc">su Google</span>${p.rank ? `<span class="rank">#${p.rank} ${esc(p.rankOf)}</span>` : ''}</div>` : ''}
      ${p.tc ? '<div class="info warn"><span>⚠️</span><span>Chiuso temporaneamente secondo Google</span></div>' : ''}
      <div class="info"><span>📏</span><span>${fmtKm(p.dist)} da ${esc(state.centerName)}${p.ff ? ' · fast food' : ''}</span></div>
      <div class="tags">${tags}</div>
      ${where ? `<div class="info"><span>📍</span><span>${esc(where)}</span></div>` : ''}
      ${p.oh ? `<div class="info"><span>🕒</span><span>${esc(p.oh)}</span></div>` : ''}
      ${p.tel ? `<div class="info"><span>📞</span><a href="tel:${esc(p.tel.replace(/\s/g, ''))}">${esc(p.tel)}</a></div>` : ''}
      ${web ? `<div class="info"><span>🌐</span><a href="${esc(web)}" target="_blank" rel="noopener">${esc(web.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, ''))}</a></div>` : ''}
      <div class="actions">
        <button data-act="want" data-id="${p.id}" class="want ${st === 'want' ? 'on' : ''}">⭐ ${st === 'want' ? 'Da provare!' : 'Da provare'}</button>
        <button data-act="done" data-id="${p.id}" class="done ${st === 'done' ? 'on' : ''}">✓ ${st === 'done' ? 'Provato!' : 'Provato'}</button>
        <a href="${esc(gmaps)}" target="_blank" rel="noopener">Google Maps</a>
        <a class="primary" href="https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}" target="_blank" rel="noopener">Indicazioni →</a>
      </div>
    </div>`;
  }

  // ---------- tree ----------
  function buildTree() {
    const byCont = {};
    for (const [name, cu] of Object.entries(cuisines)) {
      ((byCont[cu.cont] ||= {})[cu.area] ||= []).push(name);
    }
    const total = (cont) => Object.values(byCont[cont]).flat().reduce((s, n) => s + cuisines[n].count, 0);
    const order = Object.keys(byCont).sort((a, b) => total(b) - total(a));
    const html = order.map((cont) => {
      const c = continents[cont];
      const areas = Object.entries(byCont[cont])
        .map(([a, list]) => [a, list.sort((x, y) => cuisines[y].count - cuisines[x].count)])
        .sort((x, y) => y[1].reduce((s, n) => s + cuisines[n].count, 0) - x[1].reduce((s, n) => s + cuisines[n].count, 0));
      return `<div class="cont" data-cont="${cont}" style="--c:${c.color}">
        <div class="cont-row">
          <button class="exp" type="button" aria-label="Espandi">▸</button>
          <input type="checkbox" class="cb" data-lvl="cont">
          <span class="dot" style="background:${c.color};color:${c.color}"></span>
          <span class="nm">${esc(c.name)}</span>
          <span class="cnt"></span>
        </div>
        <div class="cont-body">
          ${areas.map(([a, list]) => `
            <div class="area-row" data-area="${esc(a)}">
              <input type="checkbox" class="cb" data-lvl="area"><span>${esc(a)}</span><span class="cnt"></span>
            </div>
            <div class="chips" data-area="${esc(a)}">
              ${list.map((n) => `<button type="button" class="chip" data-cu="${esc(n)}">${flagHtml(cuisines[n].flag)}${esc(n)} <small></small></button>`).join('')}
            </div>`).join('')}
        </div>
      </div>`;
    }).join('');
    const tree = $('#tree');
    tree.innerHTML = html;

    const cuOf = (el) => [...el.querySelectorAll('.chip')].map((b) => b.dataset.cu);
    tree.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (chip) {
        const n = chip.dataset.cu;
        state.sel.has(n) ? state.sel.delete(n) : state.sel.add(n);
        return refresh();
      }
      const cb = e.target.closest('.cb');
      if (cb) {
        const scope = cb.dataset.lvl === 'cont'
          ? cb.closest('.cont')
          : tree.querySelector(`.chips[data-area="${CSS.escape(cb.closest('.area-row').dataset.area)}"]`);
        cuOf(scope).forEach((n) => (cb.checked ? state.sel.add(n) : state.sel.delete(n)));
        return refresh();
      }
      const row = e.target.closest('.cont-row');
      if (row) row.parentElement.classList.toggle('open');
    });
  }

  function syncTree(counts) {
    const tree = $('#tree');
    tree.querySelectorAll('.chip').forEach((b) => {
      const n = b.dataset.cu, k = counts[n] || 0;
      b.classList.toggle('on', state.sel.has(n));
      b.classList.toggle('zero', !k);
      b.querySelector('small').textContent = k;
      b.style.setProperty('--c', continents[cuisines[n].cont].color);
    });
    const setCb = (cb, names) => {
      const on = names.filter((n) => state.sel.has(n)).length;
      cb.checked = on === names.length;
      cb.indeterminate = on > 0 && on < names.length;
    };
    tree.querySelectorAll('.area-row').forEach((row) => {
      const names = [...row.nextElementSibling.querySelectorAll('.chip')].map((b) => b.dataset.cu);
      setCb(row.querySelector('.cb'), names);
      row.querySelector('.cnt').textContent = names.reduce((s, n) => s + (counts[n] || 0), 0);
    });
    tree.querySelectorAll('.cont').forEach((el) => {
      const names = [...el.querySelectorAll('.chip')].map((b) => b.dataset.cu);
      setCb(el.querySelector('.cont-row .cb'), names);
      el.querySelector('.cont-row .cnt').textContent = names.reduce((s, n) => s + (counts[n] || 0), 0);
    });
  }

  // ---------- filtering ----------
  function recomputeDistances() {
    for (const p of places) p.dist = haversine(state.center, [p.lat, p.lon]);
    places.sort((a, b) => a.dist - b.dist);
  }

  function refresh({ keepLimit = false } = {}) {
    if (!keepLimit) state.limit = PAGE;
    const q = norm(state.q.trim());
    const counts = {};
    const byCuisine = {};
    let cands = [];
    for (const p of places) {
      if (p.dist > state.radius) break; // places sorted by distance
      if (state.noFF && p.ff) continue;
      if (state.tab !== 'all' && status[p.id] !== state.tab) continue;
      if (q && !p.search.includes(q)) continue;
      p.score = score(p);
      for (const c of p.c) {
        counts[c] = (counts[c] || 0) + 1;
        (byCuisine[c] ||= []).push(p);
      }
      if (p.c.some((c) => state.sel.has(c))) cands.push(p);
    }
    syncTree(counts);

    // classifica per cucina: posizione (#1, #2…) e, se attivo, solo i primi TOP_N
    for (const p of cands) p.rank = 0;
    const topMode = state.top && state.tab === 'all' && !q;
    const keep = new Set();
    for (const c of state.sel) {
      const list = (byCuisine[c] || []).sort((a, b) => b.score - a.score);
      list.forEach((p, i) => {
        if (!p.rank || i + 1 < p.rank || (i + 1 === p.rank && c === p.c[0])) { p.rank = i + 1; p.rankOf = c; }
        if (i < TOP_N) keep.add(p);
      });
    }
    const total = cands.length;
    if (topMode) cands = cands.filter((p) => keep.has(p));
    visible = state.sort === 'best' ? cands.sort((a, b) => b.score - a.score) : cands.sort((a, b) => a.dist - b.dist);
    $('#topNote').textContent = topMode && visible.length < total
      ? `i ${TOP_N} migliori per cucina, su ${total}` : '';

    cluster.clearLayers();
    cluster.addLayers(visible.map(getMarker));

    renderList();
    const nW = Object.values(status).filter((s) => s === 'want').length;
    $('#cWant').textContent = nW;
    $('#cDone').textContent = Object.keys(status).length - nW;
    $('#handleText').textContent = `${visible.length} ristoranti · ${state.radius} km`;
    savePrefs();
  }

  function renderList() {
    const list = $('#list');
    $('#resCount').textContent = `${visible.length} ${visible.length === 1 ? 'ristorante' : 'ristoranti'}`;
    if (!visible.length) {
      list.innerHTML = `<li class="empty">${state.tab === 'all' ? 'Nessun ristorante con questi filtri. Prova ad allargare il raggio 🔍' : state.tab === 'want' ? 'Nessun locale “da provare”. Aprine uno sulla mappa e premi ⭐' : 'Non hai ancora segnato locali provati.'}</li>`;
      $('#more').hidden = true;
      return;
    }
    list.innerHTML = visible.slice(0, state.limit).map((p) => {
      const cu = cuisines[p.c[0]];
      const st = status[p.id];
      return `<li class="item" data-id="${p.id}" style="--c:${p.color}">
        <span class="badge">${flagHtml(cu.flag)}</span>
        <span style="min-width:0"><div class="t">${esc(p.n)}</div><div class="m">${fmtStars(p)}${p.r ? ' · ' : ''}${esc(p.c.join(' · '))}${p.city ? ' — ' + esc(p.city) : ''}</div></span>
        <span class="d">${fmtKm(p.dist)}${st ? `<span class="st ${st}">${st === 'want' ? '★ da provare' : '✓ provato'}</span>` : ''}</span>
      </li>`;
    }).join('');
    $('#more').hidden = visible.length <= state.limit;
    $('#more').textContent = `Mostra altri (${visible.length - state.limit})`;
  }

  function focusPlace(p) {
    const m = getMarker(p);
    if (window.innerWidth <= 760) $('#panel').classList.remove('open');
    cluster.zoomToShowLayer(m, () => {
      map.panTo(m.getLatLng());
      m.openPopup();
    });
  }

  const fitPad = () => (window.innerWidth > 760
    ? { paddingTopLeft: [430, 0] }
    : { paddingTopLeft: [0, 0], paddingBottomRight: [0, 70] });

  function setCenter(key, ll, name) {
    state.centerKey = key;
    state.center = ll;
    state.centerName = name;
    ring.setLatLng(ll);
    home.setLatLng(ll);
    document.querySelectorAll('#centerSeg button').forEach((b) => b.classList.toggle('on', b.dataset.c === key));
    recomputeDistances();
    refresh();
    map.fitBounds(ring.getBounds(), fitPad());
  }

  // ---------- events ----------
  function bindUi() {
    let qT;
    $('#q').addEventListener('input', (e) => {
      clearTimeout(qT);
      qT = setTimeout(() => { state.q = e.target.value; refresh(); }, 150);
    });

    $('#radius').value = state.radius;
    $('#radiusVal').textContent = `${state.radius} km`;
    $('#radius').addEventListener('input', (e) => {
      state.radius = +e.target.value;
      $('#radiusVal').textContent = `${state.radius} km`;
      ring.setRadius(state.radius * 1000);
      refresh();
    });
    $('#radius').addEventListener('change', () => map.fitBounds(ring.getBounds(), fitPad()));

    $('#noFF').checked = state.noFF;
    $('#noFF').addEventListener('change', (e) => { state.noFF = e.target.checked; refresh(); });
    $('#topOnly').checked = state.top;
    $('#topOnly').addEventListener('change', (e) => { state.top = e.target.checked; refresh(); });

    document.querySelectorAll('#sortSeg button').forEach((b) => b.classList.toggle('on', b.dataset.s === state.sort));
    $('#sortSeg').addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      state.sort = b.dataset.s;
      document.querySelectorAll('#sortSeg button').forEach((x) => x.classList.toggle('on', x === b));
      refresh();
    });

    $('#centerSeg').addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      const key = b.dataset.c;
      if (key !== 'gps') return setCenter(key, CENTERS[key].ll, CENTERS[key].name);
      if (!navigator.geolocation) return toast('Geolocalizzazione non disponibile');
      toast('Cerco la tua posizione…');
      navigator.geolocation.getCurrentPosition(
        (pos) => { setCenter('gps', [pos.coords.latitude, pos.coords.longitude], 'te'); toast('📍 Centrato sulla tua posizione'); },
        () => toast('Non riesco a ottenere la posizione'),
        { enableHighAccuracy: true, timeout: 10000 },
      );
    });

    $('#tabs').addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      state.tab = b.dataset.t;
      document.querySelectorAll('#tabs button').forEach((x) => x.classList.toggle('on', x === b));
      refresh();
    });

    $('#selAll').addEventListener('click', (e) => { e.preventDefault(); state.sel = new Set(Object.keys(cuisines)); refresh(); });
    $('#selNone').addEventListener('click', (e) => { e.preventDefault(); state.sel = new Set(); refresh(); });

    $('#list').addEventListener('click', (e) => {
      const li = e.target.closest('.item');
      if (li) focusPlace(places.find((p) => p.id === li.dataset.id));
    });
    $('#list').addEventListener('mouseover', (e) => {
      const li = e.target.closest('.item');
      if (!li) return;
      const m = markers.get(li.dataset.id);
      if (m && m._icon) m._icon.firstChild.style.transform = 'scale(1.25)';
    });
    $('#list').addEventListener('mouseout', (e) => {
      const li = e.target.closest('.item');
      if (!li) return;
      const m = markers.get(li.dataset.id);
      if (m && m._icon) m._icon.firstChild.style.transform = '';
    });
    $('#more').addEventListener('click', () => { state.limit += PAGE; renderList(); });

    $('#surprise').addEventListener('click', () => {
      const pool = visible.filter((p) => status[p.id] !== 'done');
      if (!pool.length) return toast('Nessun locale da proporre con questi filtri');
      const p = pool[Math.floor(Math.random() * pool.length)];
      toast(`🎲 Stasera: ${p.n}`);
      focusPlace(p);
    });

    // cucina a caso tra quelle presenti nel raggio e mai provate (nessun locale segnato ✓)
    $('#randCuisine').addEventListener('click', () => {
      const tried = new Set();
      for (const p of places) if (status[p.id] === 'done') p.c.forEach((c) => tried.add(c));
      const avail = new Map();
      for (const p of places) {
        if (p.dist > state.radius) break;
        if (state.noFF && p.ff) continue;
        for (const c of p.c) avail.set(c, (avail.get(c) || 0) + 1);
      }
      const pool = [...avail.keys()].filter((c) => !tried.has(c) && !c.includes('(mista)'));
      if (!pool.length) return toast('🏆 Hai provato tutte le cucine nel raggio! Prova ad allargarlo');
      const rnd = () => pool[Math.floor(Math.random() * pool.length)];
      const pick = rnd();
      const label = (c) => `${flagHtml(cuisines[c].flag)}${esc(c)}`;
      const btn = $('#randCuisine');
      btn.disabled = true;

      const STEPS = 14;
      let i = 0;
      const spin = () => {
        if (i < STEPS) {
          toast(label(rnd()), { html: true, big: true, ms: 1500 });
          i += 1;
          setTimeout(spin, 50 + i * 14);
          return;
        }
        btn.disabled = false;
        state.sel = new Set([pick]);
        state.tab = 'all';
        state.q = '';
        $('#q').value = '';
        document.querySelectorAll('#tabs button').forEach((x) => x.classList.toggle('on', x.dataset.t === 'all'));
        document.querySelector(`.cont[data-cont="${cuisines[pick].cont}"]`)?.classList.add('open');
        refresh();
        const n = avail.get(pick);
        const howMany = state.top && n > TOP_N ? `i ${TOP_N} migliori su ${n}` : `${n} ${n === 1 ? 'locale' : 'locali'}`;
        toast(`🌍 Stasera: ${label(pick)} · ${howMany}`, { html: true, big: true, ms: 4000 });
        if (visible.length) map.fitBounds(visible.map((p) => [p.lat, p.lon]), { ...fitPad(), maxZoom: 15 });
      };
      spin();
    });

    document.addEventListener('click', (e) => {
      const b = e.target.closest('.pop [data-act]');
      if (!b) return;
      const id = b.dataset.id, act = b.dataset.act;
      if (status[id] === act) delete status[id];
      else status[id] = act;
      store.set('se-status', status);
      const p = places.find((x) => x.id === id);
      const m = markers.get(id);
      m.setIcon(pinIcon(p));
      m.setPopupContent(popupHtml(p));
      if (status[id]) toast(act === 'want' ? '⭐ Aggiunto a “da provare”' : '✓ Segnato come provato');
      refresh({ keepLimit: true });
      if (state.tab !== 'all' && !status[id]) m.closePopup();
    });

    $('#sheetHandle').addEventListener('click', () => $('#panel').classList.toggle('open'));
  }

  // ---------- boot ----------
  fetch('data/restaurants.json')
    .then((r) => r.json())
    .then((d) => {
      DATA = d;
      cuisines = d.cuisines;
      continents = d.continents;
      places = d.places.map((p) => {
        const cu = cuisines[p.c[0]];
        return {
          ...p,
          flag: cu.flag,
          color: continents[cu.cont].color,
          search: norm([p.n, p.city, p.addr, ...p.c, ...(p.s || []), ...p.c.map((c) => cuisines[c].area)].filter(Boolean).join(' ')),
        };
      });
      const known = new Set(Object.keys(cuisines));
      // si salvano le cucine escluse, così quelle nuove compaiono già selezionate
      const off = new Set(Array.isArray(prefs.off) ? prefs.off : []);
      state.sel = new Set([...known].filter((n) => !off.has(n)));
      if (!state.sel.size) state.sel = known;
      $('#gen').textContent = new Date(d.meta.generated).toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' });
      buildTree();
      bindUi();
      setCenter(state.centerKey, CENTERS[state.centerKey].ll, CENTERS[state.centerKey].name);
    })
    .catch((err) => {
      console.error(err);
      $('#handleText').textContent = 'Errore nel caricamento dati';
      toast('Errore nel caricamento dei dati');
    });
})();
