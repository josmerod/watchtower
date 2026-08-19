# Especificación de mejora — Tab 🌱 Knowledge Garden

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/knowledge_garden_tab.py` + ETLs de `src/etl/{news,intelligence,opensource,substack,trendshift,rss_feeds,expanded}/`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

Tab de "conocimiento de vida larga": 18 subtabs de comunidades y agregadores (Reddit ×5, Git Trends, HN Ask, Product Hunt, Dev.to, HypeURLs, Open Source, Substack, TrendShift, RSS Feeds, LessWrong, Good Devs, Podcasts, Stack Overflow). Render **estático**: tablas de 3 columnas (Title/Source/Date), sin un solo callback propio.

- Componente: `knowledge_garden_tab.py` (300 líneas).
- Helpers: `src/services/data_loader.py` (`KNOWLEDGE_SOURCES_CONFIG`, 19 entradas), `BaseRepository` (TTL 1 h) + caché de módulo (60 s) → **doble caché con TTLs distintos**.
- Constante clave: `MAX_ARTICLES_PER_SOURCE = 50`.

### 1.2 Fuentes actuales (18 subtabs / 19 claves)

| Subtab | ETL | Upstream real | Estado |
|---|---|---|---|
| LessWrong | `src/etl/intelligence/lesswrong_etl.py` | GraphQL `lesswrong.com` | OK |
| Good Devs | `src/etl/news/news_get_gooddevs.py` | ~31 blogs personales (simonwillison, jvns, danluu, krebsonsecurity…) | OK |
| Podcasts | `news_get_podcasts.py` | 18 feeds (Syntax, Changelog, LexFridman, PracticalAI…) | OK |
| Reddit AI/ML, Programming, Tech, DevOps, All | `news/reddit_unified_etl.py` | ~40 subreddits vía `.rss`/`hot.json`, umbral `score ≥ 10` | OK |
| Git Trends | `news/news_get_gittrends.py` | GitHub Search API repos+topics (sin token: 60 req/h) | Frágil |
| HN Ask | `news/news_get_hackernews_ask.py` | Firebase `askstories` (100) | OK |
| Stack Overflow | — | **ETL inexistente** (`news_get_stackoverflow_trends.py` borrado; el launcher aún lo referencia) | 🔴 MUERTA |
| Product Hunt | `news/news_get_producthunt.py` | GraphQL oficial (token) con fallback RSS | ⚠️ bug fecha (ver K3) |
| Dev.to | — | **ETL inexistente** (`news_get_devto.py` borrado) | 🔴 MUERTA |
| HypeURLs | `reddit_unified_etl` (cat. news) | r/hypeurls (no hypeurls.com) | OK |
| Open Source | `opensource/opensource_projects_etl.py` + reddit | opensourceprojects.dev (Playwright) + r/coolgithubprojects | OK |
| Substack | `substack/substack_etl.py` | **Solo 2 newsletters** (`aimadesimple0`, `adhdweasel`) | Minúscula |
| TrendShift | `trendshift/trendshift_etl.py` | trendshift.io (BeautifulSoup) | ⚠️ fechas sin sentido |
| RSS Feeds | `rss_feeds/rss_feed_etl.py` | **Solo 1 feed** (tom-doerr.github.io) | Minúscula |

### 1.3 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| K1 | **P0** | 2 subtabs muertas (Dev.to, Stack Overflow): sin ETL y sin datos → alerta "No knowledge items" permanente. El launcher referencia scripts borrados. |
| K2 | **P0** (producto) | **Cero interactividad**: sin búsqueda, sin filtro, sin orden alternativo, sin paginación. Es el tab con fuentes más heterogéneas y el más "plano" del dashboard. Ignora toda la infra compartida (duplicate_filter, filter_presets, items_per_page_selector — todas sin adoptar). |
| K3 | **P0** (datos) | Product Hunt: la query GraphQL interpola `postedAfter = now()` → solo puede devolver 0 posts; siempre cae al fallback RSS (sin votos ni comentarios). |
| K4 | P1 | Campos riquísimos descartados: score/num_comments (Reddit), votes/tagline (PH), stars/forks/language (Git Trends), author/tags (casi todo). Solo se pinta Title/Source/Date. |
| K5 | P1 | TrendShift fija `published_at = utcnow()` en el ETL → ordenar por fecha es meaningless para esa fuente; además usa `datetime.utcnow()` deprecado. |
| K6 | P1 | Doble caché (60 s módulo + 3600 s repo) sin control de invalidación; mutación in-place de `source_display_name` sobre objetos cacheados compartidos entre subtabs. |
| K7 | P2 | Subtab activa por defecto = `knowledge-tab-opensource` (la 15ª de la lista) — llegada desconcertante. |
| K8 | P2 | Git Trends: dict de topics construido y descartado; ~200 repos/run; sin token. |
| K9 | P2 | `data/reddit_unified/` acumula JSONs timestamped por subreddit sin límite. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **Dev.to API** (`dev.to/api/articles?top=1&per_page=50`) | REST JSON, **sin key** | Revive la subtab muerta K1 con reacciones/labels/autor. ETL trivial | Bajo | ⭐⭐⭐ |
| **StackExchange API** (`api.stackexchange.com/2.3/questions?order=desc&sort=hot&site=stackoverflow&filter=withbody`) | REST JSON, sin key (quota 300/día, 10k con key registrada gratis) | Revive "Stack Overflow" con hot questions, score, tags, is_answered | Bajo | ⭐⭐⭐ |
| **Hacker News Best/Show** (`hn.algolia.com/api/v1/search?tags=story,show_hn`) | REST JSON | Subtab "Show HN" (proyectos) distinta de HN Ask | Bajo | ⭐⭐ |
| **Lobsters JSON** (`lobste.rs/hottest.json`) | JSON | Tagged links dev con score; complementa Good Devs | Bajo | ⭐⭐ |
| **Substack: catálogo ampliado** — el ETL ya soporta N slugs vía config; añadir p.ej. `astralcodexten`, `thepragmaticengineer` (feeds públicos) | RSS | Multiplica el valor de una subtab hoy de 2 fuentes | Muy bajo (config) | ⭐⭐⭐ |
| **RSS Feeds: catálogo ampliado** — mismo patrón; candidatos: blog deVALUA? no; sí: `xeiaso.net`, `martinfowler.com/feed`, `interconnects.ai`, `simonwillison.net` (si no duplicar Good Devs, elegir otros) | RSS | El ETL está hecho; es solo lista | Muy bajo | ⭐⭐⭐ |
| **Kagi Kite ya cubre news**; para KG: **Papers con código** vía `paperswithcode.com/api/v1/...` (ya hay import opcional en arxiv_etl) | REST | Papers↔repos: encaja en Open Source | Medio | ⭐⭐ |
| **lobsters/lemmy** (`lemmy.world/c/technology/feed.xml` RSS ActivityPub) | RSS | Fediverse tech community | Bajo | ⭐ |
| **Google Scholar Alerts → RSS por query** (vía scraper ligero o `scholar.google.com` user feed) | RSS/frágil | Seguimiento de autores; alternativo: **OpenAlex API** (`api.openalex.org/works?filter=…`) JSON libre | Medio | ⭐⭐ (OpenAlex ⭐⭐⭐ como API libre y estable) |

**Nota:** el propio repo documenta decenas de fuentes académicas y de mercado en `docs/potentialsources/*.md` — este tab es el destino natural de las académicas de bajo umbral (OpenAlex, DBLP).

## 3. Mejoras a funcionalidad existente

### M1 — Revivir Dev.to y Stack Overflow (fix K1)
Dos ETLs `SimpleETL` de ~100 líneas cada uno (los anteriores existieron: el launcher los llama). Dev.to: paginación `page=1..3`, mapear a `{title,url,published_at,source,author,tags,reactions}`. StackExchange: `sort=hot`, mapear score/tags/answer_count. Registrar en `run_all_etl_orchestrator.py`. Aceptación: subtabs con datos reales tras 1 run.

### M2 — Búsqueda + filtros por subtab (fix K2)
Replicar el patrón del tab News (`create_search_input` + callback por subtab con ids generados **dinámicamente** desde `tab_definitions`, no hardcoded — evitar el bug N1 de News). Incluir: búsqueda con highlight, selector items-per-page (infra existente), toggle dedup (infra existente) para Open Source/Reddit All.

### M3 — Mostrar los campos ricos (fix K4)
- Reddit: columnas Score (con badge 🔥 si > umbral) y 💬 comentarios (link al thread).
- Product Hunt: votos y tagline bajo el título (cuando M4 arregle la query).
- Git Trends: ⭐ stars, lenguaje (badge coloreado), forks; el campo `trending_score` ya existe.
- Podcasts/Good Devs: author + duración si disponible.
Alternativa de bajo esfuerzo: tooltip por fila con el JSON enriquecido (`tooltip_data` como el tab Ayudas).

### M4 — Corregir Product Hunt (fix K3)
`postedAfter` debe ser `now - 7d` (o parámetro `days`). Con token válido la query GraphQL devuelve votos/creator; mantener fallback RSS. Añadir test unitario que falle si `postedAfter > now - 1d`.

### M5 — Unificar caché (fix K6)
Eliminar `_KNOWLEDGE_CACHE` de módulo y fiarlo todo a `BaseRepository` (TTL 1 h, invalidable con `force_refresh=True` desde un futuro botón refresh). Copiar (no mutar) los dicts al inyectar `source_display_name`.

### M6 — TrendShift con fechas reales (fix K5)
Extraer la fecha del card si existe; si no, marcar `published_at: null` y ordenar la subtab por "recién descubierto" (campo `first_seen_at` que el ETL puede mantener al estilo del incremental de opensourceprojects.dev).

### M7 — Subtab activa por defecto
`active_tab = "knowledge-tab-opensource"` → primera subtab o la última visitada (localStorage clientside). Esfuerzo: B.

### M8 — Higiene de datos Reddit (fix K9)
Retención de timestamped por subreddit (p.ej. `keep_last=30` — `src/utils/` ya tiene utilidades de limpieza de outputs en otros ETLs). Esfuerzo: B.

## 4. Funcionalidades nuevas propuestas

### F1 — "Garden global search": buscar en las 19 fuentes a la vez
**Objetivo:** encontrar un tema (p.ej. "kubernetes rust") en toda la garden en una consulta.
**UI:** input fijo bajo el header + resultados agrupados por fuente con contadores; click en contador filtra a esa fuente.
**Callback:** 1 callback agregado sobre un `dcc.Store` con el dataset combinado (llenado en render, ~19×50 items).
**Aceptación:** respuesta <500 ms; resultados de ≥6 fuentes para términos comunes.
**Esfuerzo:** M.

### F2 — Vista de tarjetas para proyectos (Git Trends / Open Source / Show HN)
Card grid (xs=12 sm=6 md=4) con ⭐, lenguaje, descripción 2 líneas y link — reutilizable del patrón de `videos_tab.py`. Toggle tabla/tarjetas por subtab. Esfuerzo: M.

### F3 — Persistencia de "guardados" (read-it-later del dashboard)
⭐ por item → `data/garden/saved_items.json` vía API interna o callback que escriba el fichero (con confirmación). Subtab "⭐ Guardados" al inicio. Integrable con el motor de recomendaciones (`src/recommendations/`). Esfuerzo: M.

### F4 — Panel de salud de fuentes
Fila de puntos por subtab (verde = `_latest.json` <24 h; ámbar <7 d; rojo = sin datos), alimentada por `scripts/audit_stale_sources.py`. Click → tooltip con última ejecución. Esfuerzo: B.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M4 (postedAfter), M7 (subtab por defecto), ampliar catálogos Substack/RSS (solo config), M6 |
| **Corto plazo** | M1 revivir Dev.to + StackExchange (⭐⭐⭐), M2 búsqueda/filtros/paginación, M3 campos ricos, F4 salud |
| **Medio plazo** | F1 garden search, F2 vista tarjetas, M5/M8 higiene caché y retención |
| **Estratégico** | F3 guardados + integración con recommendations/alerts (convertir la garden en el "inbox" del dashboard); OpenAlex como subtab académica |

**Criterios de éxito:** 0 subtabs muertas; ≥1 control interactivo por subtab (hoy 0); campos score/votos/stars visibles; subtabs configurables sin tocar código (catálogos en config).
