"""Client minimale per Google Places API (New) con cache su disco e tetto di chiamate per SKU.

Le richieste che includono `rating` sono fatturate come SKU "Enterprise":
quota gratuita 1000/mese per Text Search e 1000/mese per Nearby Search (SKU separati).
"""
import collections, datetime, hashlib, json, math, os, sys, time, urllib.error, urllib.request

from cuisines import CUISINES, GOOGLE, QUERY_HINT

API = 'https://places.googleapis.com/v1/'
FIELDS = ['id', 'displayName', 'location', 'rating', 'userRatingCount', 'types', 'primaryType',
          'googleMapsUri', 'businessStatus', 'websiteUri', 'nationalPhoneNumber', 'shortFormattedAddress',
          'regularOpeningHours.weekdayDescriptions']
PLACE_MASK = ','.join('places.' + f for f in FIELDS)
NEARBY_TYPES = ['restaurant', 'meal_takeaway', 'meal_delivery', 'fast_food_restaurant', 'cafe', 'bar',
                'kebab_shop', 'food_court']


class BudgetExceeded(Exception):
    pass


class Client:
    def __init__(self, key, cache_dir, budget):
        self.key = key
        self.cache_dir = cache_dir
        self.budget = dict(budget)          # sku -> chiamate massime
        self.used = collections.Counter()   # sku -> chiamate fatte (escluse quelle in cache)
        self.month = datetime.date.today().strftime('%Y-%m')
        os.makedirs(cache_dir, exist_ok=True)

    def _post(self, sku, endpoint, body):
        raw = json.dumps(body, sort_keys=True)
        h = hashlib.sha1(f'{self.month}|{endpoint}|{PLACE_MASK}|{raw}'.encode()).hexdigest()
        path = os.path.join(self.cache_dir, f'{h}.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        if self.used[sku] >= self.budget[sku]:
            raise BudgetExceeded(sku)
        mask = PLACE_MASK + (',nextPageToken' if sku == 'text' else '')
        req = urllib.request.Request(API + endpoint, data=raw.encode(), method='POST', headers={
            'Content-Type': 'application/json', 'X-Goog-Api-Key': self.key, 'X-Goog-FieldMask': mask})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    res = json.load(r)
                break
            except urllib.error.HTTPError as ex:
                msg = ex.read().decode(errors='replace')
                if ex.code in (429, 500, 503) and attempt < 3:
                    time.sleep(2 ** attempt * 3)
                    continue
                sys.exit(f'Places API {ex.code}: {msg}')
        self.used[sku] += 1
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False)
        return res

    def text(self, body):
        return self._post('text', 'places:searchText', body)

    def nearby(self, body):
        return self._post('nearby', 'places:searchNearby', body)


def km(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _rect_hits_circle(rect, clat, clon, r_km):
    s, w, n, e = rect
    lat = min(max(clat, s), n)
    lon = min(max(clon, w), e)
    return km(clat, clon, lat, lon) <= r_km


def _query_text(gtype):
    if gtype in QUERY_HINT:
        return QUERY_HINT[gtype]
    label = GOOGLE[gtype].split(' (')[0].split(' /')[0].lower()
    return f'ristorante {label}'


def discover(client, clat, clon, r_km, max_depth=4):
    """Cerca tutti i locali per ogni tipo di cucina Google. Divide l'area in quadranti
    quando una ricerca raggiunge il massimo di 60 risultati."""
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * math.cos(math.radians(clat)))
    root = (clat - dlat, clon - dlon, clat + dlat, clon + dlon)
    queue = collections.deque((t, root, 0) for t in GOOGLE)
    found, complete = {}, True
    while queue:
        gtype, rect, depth = queue.popleft()
        s, w, n, e = rect
        body = {'textQuery': _query_text(gtype), 'includedType': gtype, 'strictTypeFiltering': True,
                'languageCode': 'it', 'regionCode': 'IT', 'pageSize': 20,
                'locationRestriction': {'rectangle': {'low': {'latitude': s, 'longitude': w},
                                                      'high': {'latitude': n, 'longitude': e}}}}
        got, token = 0, None
        try:
            for _ in range(3):
                res = client.text({**body, 'pageToken': token} if token else body)
                for p in res.get('places', []):
                    found[p['id']] = p
                    got += 1
                token = res.get('nextPageToken')
                if not token:
                    break
        except BudgetExceeded:
            complete = False
            print('  tetto Text Search raggiunto: scoperta interrotta', file=sys.stderr)
            break
        if got >= 60 and depth < max_depth:
            mlat, mlon = (s + n) / 2, (w + e) / 2
            for q in [(s, w, mlat, mlon), (s, mlon, mlat, e), (mlat, w, n, mlon), (mlat, mlon, n, e)]:
                if _rect_hits_circle(q, clat, clon, r_km):
                    queue.append((gtype, q, depth + 1))
    return list(found.values()), complete


def nearby_lookup(client, lat, lon, radius_m=80):
    body = {'includedTypes': NEARBY_TYPES, 'maxResultCount': 5, 'rankPreference': 'DISTANCE',
            'languageCode': 'it', 'regionCode': 'IT',
            'locationRestriction': {'circle': {'center': {'latitude': lat, 'longitude': lon}, 'radius': radius_m}}}
    return client.nearby(body).get('places', [])


def cuisines_of(gplace):
    """Cucine etniche di un risultato Google, partendo dal tipo primario."""
    types = [gplace.get('primaryType')] + gplace.get('types', [])
    out = []
    for t in types:
        if t in GOOGLE and GOOGLE[t] not in out:
            out.append(GOOGLE[t])
    return out
