# Especificación de mejora — Tab Scavenging

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/scavenging_tab.py` + `src/etl/goldigging/{goldigging_scavenging_etl,audible_releases_etl,gumroad_scraper_etl,viajeros_piratas_etl,humble_books_etl}.py`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

"⛏️ Project Scavenging — Automated monitoring of free resources, audiobooks, and deal alerts." Subtabs **dinámicas** descubiertas por glob de `data/scavenging/*_rss_entries.json` + 3 ficheros explícitos (gumroad, viajeros_piratas, humble). Tabla de 4 columnas (Title+Source / Details / Price+Type badges / Date), búsqueda por categoría con `dcc.Store` + clear button.

- Componente: `scavenging_tab.py` (234 líneas). Usa `data_loader.deduplicate_items` y `search_utils`.
- Constantes: `MAX_ITEMS_PER_TAB = 100` (aplicado ANTES de guardar en el Store), `DATA_DIR = Path("data/scavenging")` **relativo al CWD**.

### 1.2 Fuentes actuales

| Categoría | ETL | Upstream | Nota |
|---|---|---|---|
| anime / audiobooks / courses | `goldigging_scavenging_etl.py` (config `scavenging.json`) | RSS de **IPTorrents** (credenciales en la URL) + `nyaa.si` RSS | 🔴 ver seguridad |
| audible | `audible_releases_etl.py` | `audible.es/newreleases` (scrape, ventana 30 días **hardcoded** `20260215-20260315`) | la ventana ya venció |
| gumroad_free | `gumroad_scraper_etl.py` | `gumroad.com/products/search?max_price=1` (Playwright, 500–10.000 items) | OK |
| viajeros_piratas | `viajeros_piratas_etl.py` | `viajerospiratas.es` (Playwright, checkpointed) | audit: NEVER/EMPTY |
| humble_books | `humble_books_etl.py` | `humble.dadand.dev` (tracker third-party) | fecha = fetched_at |

### 1.3 Bugs, deuda y seguridad (priorizados)

| # | Severidad | Problema |
|---|---|---|
| SC1 | **P0 — SEGURIDAD** | El user id y **passkey de IPTorrents están commiteados en texto claro** en `src/etl/goldigging/scavenging.json` (`u=1610514;tp=<passkey>`). Un passkey de tracker permite descargar en nombre del usuario. Rotar la clave, mover a env var (`IPT_USER_ID`, `IPT_PASSKEY`), purgar del historial si procede, y añadir al allowlist de detect-secrets solo tras rotación. |
| SC2 | **P0** | `DATA_DIR` relativo al CWD — mismo fallo que 4chan (F1). |
| SC3 | **P0** (UX) | El cap de 100 se aplica **antes** de almacenar/buscar: los ítems antiguos existen en el JSON pero son invisibles E inbuscables. |
| SC4 | P1 | El highlight de búsqueda muestra `<mark>` como texto literal: `filter_content` inyecta HTML que Dash escapa. (Mismo bug en Deals.) |
| SC5 | P1 | Audible: ventana de fechas hardcoded ya vencida → 0 resultados futuros garantizados. |
| SC6 | P1 | Viajeros Piratas: audit NEVER/EMPTY; además mantiene doble output (canónico + copia scavenging) con riesgo de drift — igual que Gumroad. |
| SC7 | P2 | Sin filtros de precio/fecha/tipo, sin paginación, sin export; sin indicador de frescura por categoría. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **Epic Games free games** (`store-site.ak.epicgames.com/api/v2/freeGamesPromotions?locale=es-ES&country=ES`) | REST JSON oficial, sin key | Juegos gratis semanales caducables — caso de uso perfecto del tab (vigilancia de ofertas con deadline) | Bajo | ⭐⭐⭐ |
| **Steam free-to-keep / promos** (`store.steampowered.com/api/appdetails?appids=…` + lista de apps) | REST oficial sin key | Promociones 100% gratis temporales; requiere descubrir appids (comunidad: github "steam-free-games" lists) | Medio | ⭐⭐ |
| **itch.io free games & bundles** (`itch.io/bundles-free`, RSS/search) | RSS/scrape | Bundles charity con cientos de juegos; complementa el games ETL existente (`games_get_itchio_trending.py` — patrón ya probado) | Bajo | ⭐⭐ |
| **GOG free games** (ya existe `games_get_gog_rss.py` en games/) | RSS | Duplicado barato: reutilizar ETL y cruzar a scavenging | Muy bajo | ⭐⭐ |
| **r/FreeGameFindings** (Reddit JSON — la infra reddit_unified ya existe) | REST | Descubrimiento comunitario multi-plataforma con score de calidad | Bajo | ⭐⭐⭐ |
| **Discudemy / coupons Udemy** (`discudemy.com` RSS) | RSS/scrape | Cupones 100% off de Udemy — encaja con el Google Sheet actual de Learning | Bajo | ⭐⭐ |
| **Humble Bundle oficial** (`humble.com/api/v1/tfg/chunks?...` endpoints no oficiales) | REST no oficial | Sustituir al proxy third-party dadand.dev | Medio | ⭐ |
| **Amazon Prime Gaming** | requiere auth | No viable sin sesión — descartar | — | — |

## 3. Mejoras a funcionalidad existente

### M1 — Remediación de seguridad (fix SC1)
1. Rotar passkey IPT ya.
2. `scavenging.json` sin credenciales: placeholders + lectura de `os.environ` (patrón `src/config/settings.py`).
3. Grep histórico (`git log -S`) para documentar la exposición y valorar purge.
4. `.secrets.baseline`: NO allowlistear el valor viejo (está comprometido).
Aceptación: `grep -rE "u=[0-9]+;tp=" src/` sin resultados; ETL funcional con env vars.

### M2 — Ruta absoluta (fix SC2)
`DATA_DIR = get_data_path("scavenging")`. Igual que 4chan M1.

### M3 — Búsqueda sobre el dataset completo (fix SC3)
Guardar el dataset íntegro en el `dcc.Store` y aplicar el límite 100 **en render** (o paginar directamente con `items_per_page_selector`). El buscador debe operar sobre todo el histórico disponible del fichero.

### M4 — Highlight funcional (fix SC4)
Opción recomendada: renderizar el texto con `html.Mark` componiendo children por segmentos (split por el match) en vez de inyectar HTML. Helper único en `search_utils.highlight_segments(text, term) -> list[html components]` reutilizable por News/Deals/Scavenging.

### M5 — Audible con ventana dinámica (fix SC5)
`publication_date = (hoy-30d)..(hoy)` calculado en runtime, no hardcoded.

### M6 — Un solo output por ETL (fix SC6)
Los ETLs viajeros/gumroad deben escribir SOLO su canónico (`data/<name>/output/…`) y el tab debe leer de las rutas canónicas vía config (como News), eliminando las copias en `data/scavenging/`. La "categoría" pasa a ser metadato del record, no un directorio.

## 4. Funcionalidades nuevas propuestas

### SA1 — Filtros facetados de recursos
Precio (gratis / <5€ / todos), tipo (Audiobook/Juego/Curso/Bundle/eBook), fuente (dropdown), rango de fechas. Con la normalización M6, `deal_type`/`price`/`currency` ya están en los records. 1 callback de filtros + Store. Esfuerzo: M.

### SA2 — "Caduca pronto" (deadline tracking)
Para ofertas con fin conocido (Epic, Steam promos, bundles): columna countdown con color (≤48 h rojo), orden por deadline, y filtro "Cierra esta semana". Requiere campo `expires_at` en el modelo unificado. **Killer feature** del tab. Esfuerzo: M.

### SA3 — Watcher de ofertas + keywords
Igual que Courses F3: `BaseWatcher` que difiera contra el run anterior y emita eventos "nuevo gratis en {fuente}: {título}" con filtro de keywords (p.ej. "audiobook", "rust", "switch"). Conecta con notifications (spec 14). Esfuerzo: M.

### SA4 — Historial de "lo que me llevé"
Checkbox "✔ reclamado" por item persistido (localStorage o `data/scavenging/claimed.json` vía API interna) para no reclamar dos veces — es un tab de acción, no solo lectura. Esfuerzo: B–M.

### SA5 — Estadísticas del scavenger
Header con tarjetas: N recursos gratis activos, ahorro estimado (Σ precio tachado cuando exista), por fuente. Esfuerzo: B.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | **M1 seguridad (hoy mismo)**, M2 ruta, M5 ventana Audible, M4 highlight |
| **Corto plazo** | Epic Free Games + r/FreeGameFindings (⭐⭐⭐), M3 búsqueda completa, SA5 stats |
| **Medio plazo** | SA2 countdown de deadlines, SA1 filtros facetados, M6 unificación de outputs, itch.io/Steam |
| **Estratégico** | SA3 watcher con keywords → notificaciones; SA4 reclamados; convertir el tab en "free stuff inbox" con digest semanal |

**Criterios de éxito:** 0 credenciales en el repo; búsqueda sobre histórico completo; ≥2 fuentes nuevas con deadline real (Epic/Steam); highlight visible; el usuario puede distinguir a simple vista qué caduca y cuándo.
