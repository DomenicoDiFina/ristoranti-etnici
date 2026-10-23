# 🌍 Sapori dal Mondo

Mappa interattiva dei ristoranti etnici nel raggio di 30 km da Legnano / Busto Arsizio.

**Sito:** https://domenicodifina.github.io/ristoranti-etnici/

## Funzioni

- Filtro a 3 livelli: **continente › area › cucina** (es. Asia › Sud-est asiatico › Thailandese)
- **Solo i 10 migliori per cucina** (disattivabile), in base alle stelle su Google Maps
- Raggio regolabile (2–30 km), centrato su Legnano, Busto, a metà strada o sulla tua posizione GPS
- Ordinamento per "Migliori" o "Più vicini"; ricerca per nome, città, cucina o specialità
- ⭐ "Da provare" e ✓ "Provati", salvati nel browser
- 🎲 "Sorprendimi": un locale a caso tra quelli filtrati

### Classifica

`stelle pesate = (stelle × recensioni + 3,9 × 15) / (recensioni + 15)` — un 5★ con 3 recensioni non batte un 4,7★ con 800.
Poi si sottraggono 0,02 stelle per ogni km dal centro scelto: a parità di voto (±0,1★ ≈ 5 km) vince il più vicino.

## Dati

1. **OpenStreetMap** (ODbL) via Overpass API: locali con tag `cuisine` non italiano.
2. **Google Places API (New)**, se è disponibile una chiave:
   - per ogni tipo di cucina Google (`japanese_restaurant`, `ethiopian_restaurant`, …) una Text Search nell'area, divisa in quadranti dove ci sono più di 60 risultati → trova i locali che mancano su OSM;
   - abbinamento ai locali OSM per distanza e somiglianza del nome; Nearby Search puntuale per quelli non trovati;
   - stelle, numero di recensioni, link Google Maps; i locali chiusi definitivamente vengono rimossi.

La tassonomia (tag OSM / tipi Google → cucina → area → continente) è in [`tools/cuisines.py`](tools/cuisines.py).

### Aggiornare i dati

```sh
# chiave in tools/.places_key (ignorato da git) oppure in GOOGLE_PLACES_KEY
python tools/build.py
python tools/build.py --no-google   # solo OpenStreetMap
```

Lo script si ferma a **950 chiamate per SKU** (Text Search ed Nearby Search Enterprise hanno 1000 chiamate gratuite al mese ciascuna)
e mette in cache le risposte del mese in `tools/.cache/`, quindi rilanciarlo nello stesso mese non costa nulla.

La GitHub Action `update-data.yml` lo esegue il 1° di ogni mese se nel repo c'è il secret `GOOGLE_PLACES_KEY`
(Settings → Secrets and variables → Actions). Evita di lanciarla a mano nello stesso mese di un aggiornamento locale.

## Stack

HTML/CSS/JS statico, [Leaflet](https://leafletjs.com/) + MarkerCluster, mappa Esri Dark Gray, bandiere da flagcdn.com.
