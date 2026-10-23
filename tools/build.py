"""Genera data/restaurants.json: ristoranti etnici da OpenStreetMap, arricchiti (se c'è una chiave)
con stelle e locali mancanti da Google Places API.

Uso:
  python tools/build.py                    # OSM + Google (se la chiave è disponibile)
  python tools/build.py --no-google        # solo OSM
  python tools/build.py --raw osm.json     # usa un dump Overpass già scaricato

Chiave Google: variabile d'ambiente GOOGLE_PLACES_KEY oppure file tools/.places_key (non va su git).
"""
import argparse, collections, datetime, difflib, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from cuisines import CONTINENTS, CUISINES, OSM, SPECIALS  # noqa: E402
import google_places as gp  # noqa: E402

CLAT, CLON = 45.6040, 8.8900   # tra Legnano e Busto Arsizio
RADIUS_KM = 30
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, '..', 'data', 'restaurants.json')
CACHE = os.path.join(HERE, '.cache')
ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
]
QUERY = f'''[out:json][timeout:180];
(nwr["amenity"~"^(restaurant|fast_food|cafe)$"]["cuisine"](around:{RADIUS_KM * 1000},{CLAT},{CLON}););
out center tags;'''


def fetch_osm():
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    for attempt in range(3):
        for ep in ENDPOINTS:
            try:
                req = urllib.request.Request(ep, data=data, headers={
                    'User-Agent': 'ristoranti-etnici/1.0 (github.com/DomenicoDiFina/ristoranti-etnici)',
                    'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=240) as r:
                    return json.load(r)
            except Exception as ex:
                print(f'{ep}: {ex}', file=sys.stderr)
        time.sleep(30 * (attempt + 1))
    sys.exit('Overpass non raggiungibile')


def parse_osm(d):
    res, seen = [], set()
    for e in d['elements']:
        t = e.get('tags', {})
        name = t.get('name')
        lat = e.get('lat') or e.get('center', {}).get('lat')
        lon = e.get('lon') or e.get('center', {}).get('lon')
        if not name or lat is None or gp.km(CLAT, CLON, lat, lon) > RADIUS_KM:
            continue
        keys = [k.strip().lower().replace(' ', '_') for k in t.get('cuisine', '').split(';')]
        labels, specials = [], []
        for k in keys:
            if k in OSM and OSM[k] not in labels:
                labels.append(OSM[k])
            if k in SPECIALS and SPECIALS[k] not in specials:
                specials.append(SPECIALS[k])
        if not labels:
            continue
        key = (name.lower(), round(lat, 3), round(lon, 3))
        if key in seen:
            continue
        seen.add(key)
        r = {'id': f"{e['type'][0]}{e['id']}", 'n': name, 'lat': round(lat, 6), 'lon': round(lon, 6), 'c': labels}
        if specials:
            r['s'] = specials
        addr = ' '.join(x for x in [t.get('addr:street'), t.get('addr:housenumber')] if x)
        if t.get('addr:city'):
            r['city'] = t['addr:city']
        if addr:
            r['addr'] = addr
        for src, dst in [('phone', 'tel'), ('contact:phone', 'tel'), ('website', 'web'),
                         ('contact:website', 'web'), ('opening_hours', 'oh')]:
            if t.get(src) and dst not in r:
                r[dst] = t[src]
        if t.get('amenity') == 'fast_food':
            r['ff'] = 1
        res.append(r)
    return res


# ---------- abbinamento OSM <-> Google ----------
STOP = {'ristorante', 'restaurant', 'trattoria', 'pizzeria', 'bar', 'cafe', 'caffe', 'the', 'il', 'la', 'lo',
        'da', 'di', 'del', 'e', 'and', 'srl', 'snc', 'sas'}


def norm_name(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(w for w in re.findall(r'[a-z0-9]+', s) if w not in STOP)


def name_sim(a, b):
    a, b = norm_name(a), norm_name(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.9
    ta, tb = set(a.split()), set(b.split())
    jac = len(ta & tb) / len(ta | tb)
    return max(jac, difflib.SequenceMatcher(None, a, b).ratio())


def best_match(o, cands):
    best, score = None, 0.0
    for g in cands:
        loc = g.get('location', {})
        d = gp.km(o['lat'], o['lon'], loc.get('latitude', 0), loc.get('longitude', 0)) * 1000
        sim = name_sim(o['n'], g.get('displayName', {}).get('text', ''))
        ok = (d <= 150 and sim >= 0.55) or (d <= 30 and sim >= 0.3) or (d <= 400 and sim >= 0.85)
        s = sim - d / 2000
        if ok and s > score:
            best, score = g, s
    return best


def short_hours(days):
    """['lunedì: 11:00–23:00', …] -> 'Tutti i giorni 11:00–23:00' o 'lun 11:00–23:00 · mar …'"""
    parts = [d.split(': ', 1) for d in days]
    times = [p[1] if len(p) == 2 else p[0] for p in parts]
    if len(set(times)) == 1:
        return f'Tutti i giorni {times[0]}'
    return ' · '.join(f'{p[0][:3]} {t}' for p, t in zip(parts, times))


def apply_google(r, g):
    if g.get('rating') is not None:
        r['r'] = g['rating']
        r['rc'] = g.get('userRatingCount', 0)
    r['g'] = g.get('googleMapsUri')
    r.setdefault('tel', g.get('nationalPhoneNumber'))
    r.setdefault('web', g.get('websiteUri'))
    hours = g.get('regularOpeningHours', {}).get('weekdayDescriptions')
    if hours:
        r.setdefault('oh', short_hours(hours))
    if g.get('businessStatus') == 'CLOSED_TEMPORARILY':
        r['tc'] = 1
    for k in [k for k, v in r.items() if v is None]:
        del r[k]


# Google etichetta molte pizzerie-kebab come "turkish_restaurant" e i poke come "american_restaurant":
# il nome è più affidabile
NAME_RULES = [
    (re.compile(r'kebab|kebap|d[oö]ner|kebabbaro', re.I), 'Kebab'),
    (re.compile(r'pok[eé]\b', re.I), 'Hawaiana / Poke'),
]


def google_place(g):
    loc = g['location']
    name = g['displayName']['text']
    cs = gp.cuisines_of(g)
    for rx, label in NAME_RULES:
        if rx.search(name):
            cs = [label]
            break
    r = {'id': 'g' + g['id'], 'n': name, 'lat': round(loc['latitude'], 6),
         'lon': round(loc['longitude'], 6), 'c': cs}
    types = [g.get('primaryType')] + g.get('types', [])
    sp = []
    for t in types:
        if t in SPECIALS and SPECIALS[t] not in sp:
            sp.append(SPECIALS[t])
    if sp:
        r['s'] = sp
    if g.get('shortFormattedAddress'):
        r['addr'] = g['shortFormattedAddress']
    if g.get('primaryType') in ('fast_food_restaurant', 'kebab_shop', 'meal_takeaway'):
        r['ff'] = 1
    apply_google(r, g)
    return r


def enrich(osm, key):
    client = gp.Client(key, os.path.join(CACHE, 'google'), {'text': 950, 'nearby': 950})
    print('Google: scoperta per tipo di cucina…')
    found, complete = gp.discover(client, CLAT, CLON, RADIUS_KM)
    found = [g for g in found if 'location' in g and
             gp.km(CLAT, CLON, g['location']['latitude'], g['location']['longitude']) <= RADIUS_KM]
    print(f'  {len(found)} locali Google, {client.used["text"]} chiamate Text Search')

    # griglia ~1 km per cercare i candidati vicini
    grid = collections.defaultdict(list)
    cell = lambda lat, lon: (round(lat * 100), round(lon * 70))
    for g in found:
        grid[cell(g['location']['latitude'], g['location']['longitude'])].append(g)

    def near(lat, lon):
        cy, cx = cell(lat, lon)
        return [g for dy in (-1, 0, 1) for dx in (-1, 0, 1) for g in grid.get((cy + dy, cx + dx), [])]

    used, closed, unmatched = set(), set(), []
    for o in osm:
        g = best_match(o, [c for c in near(o['lat'], o['lon']) if c['id'] not in used])
        if g:
            used.add(g['id'])
            if g.get('businessStatus') == 'CLOSED_PERMANENTLY':
                closed.add(o['id'])
            else:
                apply_google(o, g)
        else:
            unmatched.append(o)

    print(f'Google: ricerca puntuale per {len(unmatched)} locali OSM non trovati…')
    unmatched.sort(key=lambda o: gp.km(CLAT, CLON, o['lat'], o['lon']))
    for o in unmatched:
        try:
            cands = gp.nearby_lookup(client, o['lat'], o['lon'])
        except gp.BudgetExceeded:
            print('  tetto Nearby Search raggiunto: i restanti restano senza stelle', file=sys.stderr)
            complete = False
            break
        g = best_match(o, [c for c in cands if c['id'] not in used])
        if g:
            used.add(g['id'])
            if g.get('businessStatus') == 'CLOSED_PERMANENTLY':
                closed.add(o['id'])
            else:
                apply_google(o, g)

    places = [o for o in osm if o['id'] not in closed]
    extra = [google_place(g) for g in found
             if g['id'] not in used and g.get('businessStatus') != 'CLOSED_PERMANENTLY' and gp.cuisines_of(g)]
    print(f'  chiamate: {dict(client.used)}; chiusi definitivamente: {len(closed)}; nuovi da Google: {len(extra)}')
    return places + extra, complete


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw')
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--no-google', action='store_true')
    a = ap.parse_args()

    raw = json.load(open(a.raw, encoding='utf-8')) if a.raw else fetch_osm()
    places = parse_osm(raw)
    print(f'OSM: {len(places)} ristoranti etnici entro {RADIUS_KM} km')

    key = os.environ.get('GOOGLE_PLACES_KEY')
    key_file = os.path.join(HERE, '.places_key')
    if not key and os.path.exists(key_file):
        key = open(key_file, encoding='utf-8').read().strip()
    google, complete = False, True
    if key and not a.no_google:
        places, complete = enrich(places, key)
        google = True
    else:
        print('Google: nessuna chiave, salto stelle e locali aggiuntivi')

    places.sort(key=lambda r: gp.km(CLAT, CLON, r['lat'], r['lon']))
    cnt = collections.Counter(l for r in places for l in r['c'])
    cuisines = {k: {**v, 'count': cnt[k]} for k, v in CUISINES.items() if cnt[k]}
    meta = {'center': [CLAT, CLON], 'radiusKm': RADIUS_KM, 'generated': datetime.date.today().isoformat(),
            'google': google, 'complete': complete}
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'continents': CONTINENTS, 'cuisines': cuisines, 'places': places},
                  f, ensure_ascii=False, separators=(',', ':'))
    rated = sum(1 for r in places if 'r' in r)
    print(f'Scritti {len(places)} ristoranti ({rated} con stelle), {len(cuisines)} cucine')


if __name__ == '__main__':
    main()
