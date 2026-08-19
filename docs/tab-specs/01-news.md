# Especificación de mejora — Tab News

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/news_tab.py` + ETLs de `src/etl/news/`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

Tab por defecto del dashboard (`active_tab="tab-news"`). Renderiza un `dbc.Tabs` con **22 subtabs** (medios tech, comunidades dev, feeds Kagi Kite, medios en español, changelogs cloud, prensa local valenciana). Cada subtab muestra una tabla buscable (Título / Fuente / Fecha) ordenada por fecha descendente, con badge "trending" opcional.

- Componente: `news_tab.py` (593 líneas, toda la lógica en un fichero).
- Helpers: `src/services/data_loader.py` (config de 26 fuentes + carga + dedup), `src/web/dashboard/search_utils.py` (búsqueda con highlight), `src/web/dashboard/trend_utils.py` (badges 🔥), `recommendations_tab.py` (motor de contenido relacionado).
- Caché: `_NEWS_CACHE` global con TTL 60 s (idioma `global` + `try/except NameError`).

### 1.2 Fuentes actuales (26)

| Subtab | ETL (`src/etl/news/`) | Upstream real |
|---|---|---|
| Top Tech (combinado) | techcrunch + venturebeat + arstechnica + kagi_ai | RSS varios |
| freeCodeCamp | `news_get_freecodecamp.py` | `freecodecamp.org/news/rss` |
| Google AI Blog | `news_get_google_ai_blog.py` | `blog.google/technology/ai/rss` |
| Lobsters | `news_get_lobsters.py` | `lobste.rs/rss` |
| FutureTools & Ben's Bites | `news_get_futuretools.py`, `news_get_bensbites.py` | `news.futuretools.io/feed`, `news.bensbites.com` (scrape HTML) |
| Hacker News | `news_get_ycombinator.py` | API Firebase `hacker-news.firebaseio.com` (top 150) |
| Medium GenAI | `news_get_genai_medium.py` | ~12 tag feeds de Medium |
| KDnuggets | `news_get_kdnuggets.py` | `kdnuggets.com/feed` |
| Meneame (×2) | `news_get_meneame.py` | `meneame.net/rss`, `/m/tecnologia/rss` |
| Indie Hackers | `news_get_indiehackers.py` | ⚠️ en realidad Reddit JSON (`r/entrepreneur`, `r/startup`), **no** indiehackers.com |
| Kagi Kite (×7) | `news_get_kagi.py` | `kite.kagi.com/{world,usa,business,science,gaming,europe,spain,ai}.xml` |
| Microsiervos | `microsiervos_etl.py` | `microsiervos.com/index.xml` |
| 🇪🇸 Spanish Tech | `news_get_spanish_tech.py` | Xataka, Hipertextual, Genbeta, WWWhatsNew |
| ☁️ Cloud Updates | `news_get_cloud_updates.py` | AWS What's New, Google Cloud Blog, GitHub Blog, CNCF |
| 📍 Valencia Local | `news_get_valencia_local.py` | 20minutos CV, MetroValencia |

Todos los ETLs están registrados en `run_all_etl_orchestrator.py`.

### 1.3 Funcionalidad actual

- 22 subtabs con tabla (título enlazado, fuente, fecha), scroll `maxHeight: 800px`.
- Búsqueda por substring (case-insensitive) con botón de limpiar y highlight `<mark>` sobre `title/description/source/summary/source_display_name`; alert "📰 Found N articles".
- Badges trending 🔥 desde `data/analytics/trends/latest_trends.json`.
- ~57 callbacks generados en bucle sobre 19 `search_ids` (3 por id: update, clear, related-modal).

### 1.4 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| N1 | **P0** | `spanish_tech`, `cloud_updates` y `valencia_local` renderizan un input de búsqueda que **no hace nada**: no están en la lista hardcoded `search_ids` (líneas 255–275). |
| N2 | **P0** | El modal "Related Content" es una feature muerta: el callback `toggle_related_modal` escucha botones `{"type":"related-btn"}` que **nunca se renderizan** en ningún sitio. |
| N3 | **P0** | Microsiervos: el ETL escribe a `data/microsiervos/output/` pero el tab lee `data/news/microsiervos_latest.json` → subtab siempre vacía. |
| N4 | P1 | El pipeline de tendencias (`data/analytics/trends/latest_trends.json`) no existe → los badges 🔥 nunca se pintan. |
| N5 | P1 | `MAX_ARTICLES_PER_SOURCE = 50` aplicado tras el sort por subtab; los subtabs combinados ("Top Tech") comparten el mismo tope de 50 aunque agregan 4 fuentes. |
| N6 | P1 | ~120 líneas de render de tabla duplicadas entre el layout inicial y el callback de búsqueda. |
| N7 | P1 | Caché mutable: los artículos cacheados se mutan in-place (`article["source_display_name"] = ...`) compartiendo estado entre callbacks. |
| N8 | P2 | Cada subtab reconstruye todo el dataset (re-agregar, re-ordenar, re-render) por cada pulsación de tecla; sin debounce ni paginación. |
| N9 | P2 | Div oculto `{id}-data` serializa los artículos como `children` (uso inválido) y el `State` que alimenta no se usa. |
| N10 | P2 | Sin filtros de fecha, sin orden alternativo, sin export, sin indicador de frescura del dato. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **HN Algolia Search API** (`hn.algolia.com/api/v1/search?tags=front_page`) | REST JSON, sin key | Front page con puntos/comentarios/autor estandarizados; permite buscar por rango de puntos y fecha | Bajo (sustituye/completa Firebase) | ⭐⭐⭐ |
| **Dev.to API** (`dev.to/api/articles?top=7`) | REST JSON, sin key | Artículos dev community con reacciones; reutilizable también en Knowledge Garden | Bajo | ⭐⭐⭐ |
| **The Verge / Wired RSS** | RSS | Cobertura consumer-tech ausente | Bajo | ⭐⭐ |
| **tldr.tech** (newsletter RSS: Tech/AI/Data) | RSS | Digest diario curado, muy alto señal/ruido | Bajo | ⭐⭐⭐ |
| **Ars Technica feeds por sección** (`feeds.arstechnica.com/arstechnica/{security,science}`) | RSS | Granularidad temática del source ya integrado | Bajo | ⭐ |
| **El País Tecnología / Xataka ya cubiertos** → añadir **Microsiervos (fix N3)** y **Genbeta ya está**; **SomosXataka? no**; mejor **Computerhoy/PcWorld ES** opcional | RSS | Amplitud ES | Bajo | ⭐ |
| **Lobsters JSON** (`lobste.rs/hottest.json`) | JSON | Mismo contenido sin parseo RSS, con tags y score | Bajo | ⭐ |
| **Subreddits ya usados por reddit_unified** — exponer `r/technology` como subtab News vía `reddit_tech_latest.json` | Dato ya recogido | Cero ETL nuevo: el dato ya existe en `data/reddit_unified/` | Muy bajo | ⭐⭐ |
| **OpenRSS de newsletters** (p.ej. `n8n.itgiant.io`, `trendshift newsletter`) | RSS | Noticias SaaS/automation para Deals/Tech Radar | Bajo | ⭐ |
| **Google News RSS por query** (`news.google.com/rss/search?q=…&hl=es`) | RSS | Alertas temáticas arbitrarias (p.ej. "subvención Valencia", "LLM open source") sin key | Bajo | ⭐⭐⭐ |

**Recomendación:** las tres de prioridad ⭐⭐⭐ (Algolia, Dev.to, tldr.tech, Google News RSS) dan máximo valor por esfuerzo mínimo y no requieren API keys.

## 3. Mejoras a funcionalidad existente

### M1 — Búsqueda funcional en las 22 subtabs (fix N1)
Extender `search_ids` con `spanish_tech`, `cloud_updates`, `valencia_local` — o mejor: generar los ids dinámicamente desde `tab_definitions` para que sea imposible volver a desincronizar. Añadir test que verifique `set(search_ids) == set(tab_search_ids)`.

### M2 — Revivir "Related Content" (fix N2)
Renderizar un botón discreto 🔗 `related-btn` en cada fila (o al hacer click en el título con modifier). El callback ya existe y llama a `recommendations_manager.recommendation_engine.get_related_content(title, type)`. Añadir estado vacío elegante cuando no hay motor entrenado.

### M3 — Corregir Microsiervos (fix N3)
Alinear ETL y lector: o el ETL escribe además `data/news/microsiervos_latest.json` (consistente con el resto del tab) o el tab lee `data/microsiervos/output/microsiervos_latest.json` vía `data_loader`. Preferible lo segundo + entrada en `NEWS_SOURCES_CONFIG`.

### M4 — Paginación + "items por página"
Adoptar `items_per_page_selector.py` (ya existe, 1 solo usuario hoy) con opciones 25/50/100/250. Elimina el tope ciego de 50 y el scroll infinito de 800px.

### M5 — Deduplicación visible
Adoptar `duplicate_filter.py` + `deduplication_utils.py` (hoy **cero** adoptantes) para el subtab agregado "Top Tech": toggle "mostrar duplicados" + summary "N duplicados ocultos en M grupos". El dedup actual (`deduplicate_items` en carga) es invisible e irreversible para el usuario.

### M6 — Presets de filtro
Adoptar `filter_presets.py` (guardar combinación búsqueda+fuente+fecha en localStorage, máx 10 por tab). Primero hay que completar su integración clientside (ver spec `15-infraestructura-compartida.md`).

### M7 — Debounce y rendimiento
- `dcc.Input(..., debounce=True)` en los buscadores (elimina el re-render por tecla).
- Extraer `render_news_table(articles, search_term)` como función única usada por layout y callback (elimina N6).
- Sustituir la mutación de cacheados por copias (`dict(article)`) al inyectar `source_display_name` (N7).

### M8 — Pipeline de tendencias
Crear el productor de `data/analytics/trends/latest_trends.json` (p.ej. ETL que compute menciones cruzadas de título/keywords entre fuentes en las últimas 48 h) para que los badges 🔥 y el `trend_filter.py` sin adoptantes tengan sentido.

## 4. Funcionalidades nuevas propuestas

### F1 — Búsqueda global "todos los medios"
**Objetivo:** buscar un tema una vez y ver resultados de las 26 fuentes, agrupados por medio, ordenados por relevancia/fecha.
**UI:** subtab "🔎 Global" como primera pestaña: input grande + selector de rango de fechas (7d/30d/todo) + chips de fuentes activables. Resultado: tabla unificada con columna Fuente ordenable.
**Callbacks:** 1 callback `news-global-search` (patrón single-callback, `prevent_initial_call=True`), salida `news-global-results.children`.
**Datos:** reutiliza `_ALL_NEWS_SOURCES`; el índice agregado ya se construye para el cache.
**Aceptación:** buscar "llama" devuelve resultados de ≥5 fuentes <1 s; el estado vacío sugiere fuentes sin datos.
**Esfuerzo:** M (½ jornada).

### F2 — Vista de lectura / leído-no leído
**Objetivo:** marcar artículos como leídos (persistente en `localStorage` por URL hash) y ofrecer filtro "solo nuevos desde mi última visita".
**UI:** checkbox "Ocultar leídos" + atajo "marcar todo como visto"; fila leída con opacidad 0.5.
**Callbacks:** clientside para el toggle; el estado se guarda con un hash del título+URL.
**Aceptación:** recargar la página conserva los leídos; "Nuevos desde última visita" muestra delta real.
**Esfuerzo:** M.

### F3 — Export y compartir
Botón ⬇ por subtab: descarga CSV/JSON del dataset filtrado actual (clientside `Blob`+`URL.createObjectURL`), y URL con query-param `?news=q` para compartir búsquedas. Esfuerzo: B.

### F4 — Salud de fuentes
Fila de estado bajo el header: por cada fuente, un punto verde/ámbar/rojo según antigüedad del `_latest.json` correspondiente (`scripts/audit_stale_sources.py` ya calcula staleness — exponerlo). Esfuerzo: B–M.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins (1–2 días)** | M1 (fix search ids), M3 (Microsiervos), N9 cleanup, M7 debounce + extraer render común |
| **Corto plazo (semana)** | F1 búsqueda global, M4 paginación, F3 export, fuentes ⭐⭐⭐ (Algolia/Dev.to/tldr/Google News RSS) |
| **Medio plazo** | M2 related content + F2 leído/no leído, M5 dedup visible, M8 trends, F4 salud de fuentes |
| **Estratégico** | Unificar News + Tech Radar (ver `13-tech-radar.md`): hoy Google AI/KDNuggets/Cloud Updates se muestran duplicados en ambos tabs; decidir fuente canónica y cross-link |

**Criterios de éxito:** 22/22 subtabs con búsqueda funcional; 0 features muertas en el componente; tiempo de respuesta de búsqueda <300 ms con 26 fuentes cargadas.
