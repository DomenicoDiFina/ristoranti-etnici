# 🌍 Sapori dal Mondo

Mappa interattiva dei ristoranti etnici nel raggio di ~45 km da Legnano / Busto Arsizio.

**Sito:** https://domenicodifina.github.io/ristoranti-etnici/

## Funzioni

- Filtro a 3 livelli: **continente › area › cucina** (es. Asia › Sud-est asiatico › Thailandese)
- Raggio regolabile (2–45 km), centrato su Legnano, Busto, a metà strada o sulla tua posizione GPS
- Ricerca per nome, città, cucina o specialità (sushi, ramen, tacos…)
- Lista ordinata per distanza, link a Google Maps e indicazioni stradali
- ⭐ "Da provare" e ✓ "Provati", salvati nel browser
- 🎲 "Sorprendimi": un locale a caso tra quelli filtrati

## Dati

I ristoranti vengono da [OpenStreetMap](https://www.openstreetmap.org/) (licenza ODbL), tramite Overpass API.
Un locale compare se ha il tag `cuisine` con una cucina non italiana.
La mappatura tag → cucina/area/continente è in [`tools/build.py`](tools/build.py).

Aggiornamento automatico il 1° di ogni mese (GitHub Action `update-data.yml`), oppure a mano:

```sh
python tools/build.py
```

Manca un ristorante? Aggiungilo su OpenStreetMap con il tag `cuisine` e comparirà al prossimo aggiornamento.

## Stack

HTML/CSS/JS statico, [Leaflet](https://leafletjs.com/) + MarkerCluster, mappa Esri Dark Gray, bandiere da flagcdn.com.
