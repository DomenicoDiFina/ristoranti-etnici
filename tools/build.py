"""Scarica i ristoranti etnici da OpenStreetMap (Overpass API) e genera data/restaurants.json.

Uso:
  python tools/build.py                 # scarica da Overpass e genera
  python tools/build.py --raw raw.json  # usa un dump Overpass già scaricato
"""
import argparse, collections, datetime, json, math, os, sys, time, urllib.parse, urllib.request

CLAT, CLON = 45.6040, 8.8900   # tra Legnano e Busto Arsizio
RADIUS_M = 45000
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'restaurants.json')
ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
]
QUERY = f'''[out:json][timeout:180];
(nwr["amenity"~"^(restaurant|fast_food|cafe)$"]["cuisine"](around:{RADIUS_M},{CLAT},{CLON}););
out center tags;'''

# Gerarchia: continente -> area -> cucina
CONTINENTS = {
    'asia':    {'name': 'Asia',     'color': '#ff6b6b'},
    'mo':      {'name': 'Medio Oriente', 'color': '#ffa94d'},
    'africa':  {'name': 'Africa',   'color': '#ffd43b'},
    'americhe': {'name': 'Americhe', 'color': '#38d9a9'},
    'europa':  {'name': 'Europa',   'color': '#4dabf7'},
    'oceania': {'name': 'Oceania',  'color': '#b197fc'},
}

# tag cuisine OSM -> (cucina, continente, area, bandiera)
C = {}
def add(keys, label, cont, area, flag):
    for k in keys.split():
        C[k] = (label, cont, area, flag)

add('chinese cinese sichuan hong_kong dim_sum chinese_dumplings dumpling dumplings baozi hot_pot hotpot noodle noodles', 'Cinese', 'asia', 'Asia orientale', '🇨🇳')
add('japanese sushi ramen mochi edamame', 'Giapponese', 'asia', 'Asia orientale', '🇯🇵')
add('korean corean korean_bbq', 'Coreana', 'asia', 'Asia orientale', '🇰🇷')
add('taiwanese bubble_tea', 'Taiwanese', 'asia', 'Asia orientale', '🇹🇼')
add('asian oriental', 'Asiatica (mista)', 'asia', 'Asia orientale', '🥢')
add('thai', 'Thailandese', 'asia', 'Sud-est asiatico', '🇹🇭')
add('vietnamese', 'Vietnamita', 'asia', 'Sud-est asiatico', '🇻🇳')
add('filipino', 'Filippina', 'asia', 'Sud-est asiatico', '🇵🇭')
add('indian', 'Indiana', 'asia', 'Subcontinente indiano', '🇮🇳')
add('pakistani', 'Pakistana', 'asia', 'Subcontinente indiano', '🇵🇰')
add('sri_lankan srilankan singalese', 'Srilankese', 'asia', 'Subcontinente indiano', '🇱🇰')
add('bangladeshi', 'Bengalese', 'asia', 'Subcontinente indiano', '🇧🇩')
add('nepalese', 'Nepalese', 'asia', 'Subcontinente indiano', '🇳🇵')
add('uzbek', 'Uzbeka', 'asia', 'Asia centrale', '🇺🇿')
add('kyrgyz', 'Kirghisa', 'asia', 'Asia centrale', '🇰🇬')

add('turkish', 'Turca', 'mo', 'Anatolia e Caucaso', '🇹🇷')
add('georgian', 'Georgiana', 'mo', 'Anatolia e Caucaso', '🇬🇪')
add('kebab pizza_kebab', 'Kebab', 'mo', 'Street food mediorientale', '🥙')
add('arab middle_eastern falafel pita', 'Araba / Mediorientale', 'mo', 'Levante', '🧆')
add('lebanese', 'Libanese', 'mo', 'Levante', '🇱🇧')
add('kosher', 'Kosher / Israeliana', 'mo', 'Levante', '🇮🇱')
add('persian', 'Persiana', 'mo', 'Iran', '🇮🇷')

add('moroccan marocchina', 'Marocchina', 'africa', 'Nord Africa', '🇲🇦')
add('egyptian', 'Egiziana', 'africa', 'Nord Africa', '🇪🇬')
add('eritrean', 'Eritrea', 'africa', "Corno d'Africa", '🇪🇷')
add('somali', 'Somala', 'africa', "Corno d'Africa", '🇸🇴')
add('african', 'Africana (mista)', 'africa', 'Africa subsahariana', '🌍')
add('mauritian', 'Mauriziana', 'africa', 'Oceano Indiano', '🇲🇺')

add('american diner bagel', 'Americana', 'americhe', 'Nord America', '🇺🇸')
add('mexican tacos tex-mex', 'Messicana', 'americhe', 'Centro America e Caraibi', '🇲🇽')
add('salvadoran salvadorean', 'Salvadoregna', 'americhe', 'Centro America e Caraibi', '🇸🇻')
add('cuban', 'Cubana', 'americhe', 'Centro America e Caraibi', '🇨🇺')
add('caribbean tropical', 'Caraibica', 'americhe', 'Centro America e Caraibi', '🌴')
add('peruvian', 'Peruviana', 'americhe', 'Sud America', '🇵🇪')
add('brazilian', 'Brasiliana', 'americhe', 'Sud America', '🇧🇷')
add('argentinian empanada', 'Argentina', 'americhe', 'Sud America', '🇦🇷')
add('ecuadorian', 'Ecuadoriana', 'americhe', 'Sud America', '🇪🇨')
add('venezuelan', 'Venezuelana', 'americhe', 'Sud America', '🇻🇪')
add('latin_american latin sudamericana', 'Sudamericana (mista)', 'americhe', 'Sud America', '🌎')

add('spanish tapas', 'Spagnola', 'europa', 'Europa occidentale', '🇪🇸')
add('portuguese', 'Portoghese', 'europa', 'Europa occidentale', '🇵🇹')
add('french crepe brasserie', 'Francese', 'europa', 'Europa occidentale', '🇫🇷')
add('fish_and_chips', 'Britannica', 'europa', 'Europa occidentale', '🇬🇧')
add('german bavarian pretzel', 'Tedesca', 'europa', 'Europa centrale', '🇩🇪')
add('austrian heuriger', 'Austriaca', 'europa', 'Europa centrale', '🇦🇹')
add('danish danese', 'Danese', 'europa', 'Nord Europa', '🇩🇰')
add('swedish', 'Svedese', 'europa', 'Nord Europa', '🇸🇪')
add('russian', 'Russa', 'europa', 'Europa orientale', '🇷🇺')
add('ukrainian', 'Ucraina', 'europa', 'Europa orientale', '🇺🇦')
add('romanian', 'Rumena', 'europa', 'Europa orientale', '🇷🇴')
add('greek', 'Greca', 'europa', 'Balcani e Grecia', '🇬🇷')
add('balkan', 'Balcanica', 'europa', 'Balcani e Grecia', '🇷🇸')

add('hawaiian poke', 'Hawaiana / Poke', 'oceania', 'Pacifico', '🌺')
add('australian', 'Australiana', 'oceania', 'Australia', '🇦🇺')

# specialità mostrate come etichette secondarie
SPECIALS = {'sushi': 'Sushi', 'ramen': 'Ramen', 'dim_sum': 'Dim sum', 'hot_pot': 'Hot pot', 'hotpot': 'Hot pot',
            'korean_bbq': 'BBQ coreano', 'bubble_tea': 'Bubble tea', 'tacos': 'Tacos', 'tapas': 'Tapas',
            'falafel': 'Falafel', 'poke': 'Poke', 'sichuan': 'Sichuan', 'dumpling': 'Ravioli', 'dumplings': 'Ravioli',
            'chinese_dumplings': 'Ravioli', 'baozi': 'Baozi', 'noodle': 'Noodles', 'noodles': 'Noodles',
            'empanada': 'Empanadas', 'crepe': 'Crêpes'}


def fetch():
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


def dist(lat, lon):
    p1, p2 = math.radians(CLAT), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - CLON)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def build(d):
    res, seen = [], set()
    for e in d['elements']:
        t = e.get('tags', {})
        name = t.get('name')
        lat = e.get('lat') or e.get('center', {}).get('lat')
        lon = e.get('lon') or e.get('center', {}).get('lon')
        if not name or lat is None:
            continue
        keys = [k.strip().lower().replace(' ', '_') for k in t.get('cuisine', '').split(';')]
        labels, specials = [], []
        for k in keys:
            if k in C and C[k][0] not in labels:
                labels.append(C[k][0])
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
        city = t.get('addr:city')
        addr = ' '.join(x for x in [t.get('addr:street'), t.get('addr:housenumber')] if x)
        if city: r['city'] = city
        if addr: r['addr'] = addr
        for src, dst in [('phone', 'tel'), ('contact:phone', 'tel'), ('website', 'web'),
                         ('contact:website', 'web'), ('opening_hours', 'oh')]:
            if t.get(src) and dst not in r:
                r[dst] = t[src]
        if t.get('amenity') == 'fast_food':
            r['ff'] = 1
        res.append((dist(lat, lon), r))
    res.sort(key=lambda x: x[0])
    places = [r for _, r in res]

    cnt = collections.Counter(l for r in places for l in r['c'])
    cuisines = {}
    for label, cont, area, flag in C.values():
        if cnt[label]:
            cuisines.setdefault(label, {'cont': cont, 'area': area, 'flag': flag, 'count': cnt[label]})
    meta = {'center': [CLAT, CLON], 'radiusKm': RADIUS_M / 1000,
            'generated': datetime.date.today().isoformat(), 'source': '© OpenStreetMap contributors (ODbL)'}
    return {'meta': meta, 'continents': CONTINENTS, 'cuisines': cuisines, 'places': places}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    raw = json.load(open(a.raw, encoding='utf-8')) if a.raw else fetch()
    out = build(raw)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(len(out['places']), 'ristoranti,', len(out['cuisines']), 'cucine')
