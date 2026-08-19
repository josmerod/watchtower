# Especificación de mejora — Tab Valencia Events

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/valencia_events_new_tab.py` + `src/etl/news/valencia_events_etl.py`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

"🌆 Valencia Events — Local and tech events in Valencia and surroundings." 4 tarjetas de stats (Total, Categorías, Tech, Gratis) + 2 subtabs (Todos / Próximos 30 días) con tabla estática (Título+descripción truncada, categoría con badge coloreado, fecha, fuente, link). **Cero callbacks** (el register es `pass`).

- Componente: `valencia_events_new_tab.py` (392 líneas). Legacy `valencia_events_tab.py` (505 líneas) **muerto pero presente** — tenía más features (vista tarjetas, DataTable con sort nativo, tooltips) y leía además `data/tech_events/tech_events_valencia.json` sin productor.
- ETL: `valencia_events_etl.py` (864 líneas, `BaseETL`): scrapea **visitvalencia.com/agenda** (mes actual+siguiente, 3 estrategias de parseo), **meetup.com** (Valencia, 20 cards), **eventbrite.es** (15 cards). Dedup por título con merge de campos.
- Enrichment desviado: `news_get_valencia_local.py` dice alimentar este tab pero alimenta el subtab "📍 Valencia Local" de News.

### 1.2 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| VE1 | **P0** (UI) | La stat "Free Events" **siempre equivale al total**: el modelo `ValenciaEvent` no tiene campo `cost`; el código usa `e.get("cost", 0) == 0`. Dato falso en el header. |
| VE2 | **P0** | "Upcoming" sin cota inferior: `_is_upcoming_event` solo comprueba `date <= cutoff` → **los eventos pasados cuentan como próximos**. Además solo parsea fechas `DD/MM/YYYY` con `/`: ISO `YYYY-MM-DD` falla silencioso. |
| VE3 | P1 | `create_event_card` (65–138) es función muerta dentro del tab activo; `len(upcoming_events_data)` calculado y descartado (línea 270). |
| VE4 | P1 | Ruta relativa `Path("data/valencia_events")` (CWD-dependiente, patrón repetido). |
| VE5 | P1 | Sin búsqueda, filtros, orden, paginación ni vista calendario; los campos de ubicación no existen en el modelo (no venue, no dirección, no coordenadas). |
| VE6 | P2 | Legacy 505 líneas + referencias a `tech_events` sin productor — confusión para mantenedores. |
| VE7 | P2 | Meetup scrape limitado a 20 cards y Eventbrite a 15 — muestras mínimas; sin manejo de páginas. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **Ticketmaster Discovery API** (`developer.ticketmaster.com`, key gratuita, `city=Valencia` o geoRadius) | REST oficial, paginado, con precios y fechas exactas | Conciertos/espectáculos con priceRanges y venue estructurados — arregla VE1/VE5 de origen | Bajo | ⭐⭐⭐ |
| **DOJO / VLC Tech meetups** — `github.com/devsValencia` (agenda) + Comunidad VLC tech calendar | Scrape/ICS | Eventos tech locales de calidad (charlas, meetups dev) | Bajo | ⭐⭐⭐ |
| **Las Naves** (`lasnaves.com` agenda innovación) + **La Nau UV** (`auv.uv.es` agenda cultural) | Scrape | Innovación/cultura pública, agendas estables | Bajo | ⭐⭐ |
| **IVAM / MuVIM exposiciones** (RSS/scrape) | Scrape | Exposiciones con fechas de inicio/fin — alimenta la vista "activas ahora" | Bajo | ⭐⭐ |
| **Predicción del tiempo** (Open-Meteo `api.open-meteo.com` sin key) para la fecha del evento | REST sin key | "¿Lloverá el sábado del concierto?" — enriquecimiento barato y muy visible | Bajo | ⭐⭐ |
| **Guía Lebrel / Música en Valencia** (agendas locales) | Scrape | Escena musical local | Medio | ⭐ |
| **Google Events** — no hay API pública; viajerospiratas? no aplica | — | Descartar | — | — |

## 3. Mejoras a funcionalidad existente

### M1 — Modelo con ubicación y precio (fix VE1/VE5)
Extender `ValenciaEvent` (`src/models/`): `venue: str | None`, `address`, `latitude/longitude: float | None`, `is_free: bool | None`, `price_range: str | None`, `end_date` ya existe. El ETL debe extraer precio/venue de VisitValencia (están en las cards) y Ticketmaster lo trae estructurado. La stat "Gratis" pasa a `is_free == True` real, y si `is_free` es desconocido mostrar "—" en la tarjeta (no fingir).

### M2 — Próximos con cota inferior y parseo ISO (fix VE2)
```python
def _is_upcoming_event(ev, today, horizon=30):
    d = _parse_event_date(ev)          # soporta ISO y DD/MM/YYYY
    return d is not None and today <= d <= today + timedelta(days=horizon)
```
Reutilizar `utils.parse_date_universal` del dashboard en vez de regex propio. Tests con: fecha pasada, ISO, con `/`, inparseable.

### M3 — Heredar lo bueno del legacy y borrarlo (fix VE3/VE6)
El legacy tiene DataTable nativo (sort/filter/paginación) y vista tarjetas con venue+cost: portarlo al nuevo y **eliminar** `valencia_events_tab.py`. Eliminar `create_event_card` muerto y la línea 270.

### M4 — Ruta absoluta (fix VE4)
`get_data_path("valencia_events", "valencia_events.json")`.

### M5 — Paginación y profundidad del ETL (fix VE7)
Meetup/Eventbrite: iterar páginas hasta N=100 resultados o fin; respetar `request_delay` del BaseETL. Añadir `user-agent` y manejo de bloqueos (circuit breaker ya disponible).

## 4. Funcionalidades nuevas propuestas

### VA1 — Vista calendario
**Objetivo:** ver la agenda del mes de un vistazo.
**UI:** toggle Tabla/Calendario; calendario mensual (componente `calplot`/`dash-calendar` o grid propio de `dbc.Col`×7) con N eventos por día; click en día → detalle en modal; navegación mes anterior/siguiente.
**Callbacks:** 1 callback `valencia-calendar-render` (mes activo) + 1 `valencia-day-detail`.
**Aceptación:** eventos multidió (start/end) pintados en el rango correcto; hoy resaltado.
**Esfuerzo:** M.

### VA2 — Export ICS ("añadir a mi calendario")
**Objetivo:** subscripción tipo calendario del agregado.
**Implementación:** endpoint Flask ligero en el dashboard (`/feeds/valencia.ics`) que genere ICS desde el `latest.json` (lib `icalendar`, dependencia nueva menor) + botón "🔗 Suscribirse" con URL copiable (funciona con Google Calendar/Apple por URL). Botón por evento "add" con ICS de un solo evento descargable (clientside).
**Aceptación:** URL importable en Google Calendar; eventos con título/fecha/venue/descripción.
**Esfuerzo:** M (el endpoint es pequeño; el valor es altísimo).

### VA3 — Filtros: categoría, fuente, gratis, rango de fechas
Chips de categoría (los badges ya existen), dropdown fuente (VisitValencia/Meetup/Eventbrite/Ticketmaster), switch "Solo gratis", DatePickerRange. 1 callback. Esfuerzo: B–M.

### VA4 — Mapa de eventos
`dcc.Graph` con scatter_mapbox (o `folium` iframe estático para evitar token) de eventos con coordenadas; hover con título. Depende de M1 (coords: geocoding barato con Nominatim limitado o venue→coords de Ticketmaster). Esfuerzo: M.

### VA5 — "Este fin de semana"
Vista rápida con los eventos de vie–dom; considera el tiempo (Open-Meteo) por día. Alta reutilizabilidad para el dashboard "personal intelligence". Esfuerzo: M.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M2 (upcoming fix + tests), M3 heredar+borrar legacy, M4 ruta, VE1 ocultar stat falsa si no hay datos de precio |
| **Corto plazo** | Ticketmaster API (⭐⭐⭐) + DOJO/devsValencia, VA3 filtros, M1 modelo venue/price |
| **Medio plazo** | VA2 feed ICS (killer), VA1 calendario, M5 profundidad ETL |
| **Estratégico** | VA5 fin de semana + clima; VA4 mapa; converger "eventos" con "ayudas" (ambas son deadline-driven) en un patrón común de timeline |

**Criterios de éxito:** stats no falsas; "próximos" = futuro real; venue/precio en ≥50% de eventos (con Ticketmaster); el usuario puede llevarse un evento a su calendario en 1 click.
