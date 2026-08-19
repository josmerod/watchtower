# Especificación — Infraestructura compartida del dashboard

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: componentes compartidos de `src/web/dashboard/components/`, `src/services/data_loader.py`, `src/repositories/`, `src/alerts/`, `src/recommendations/`, API `src/api/`

## 1. Diagnóstico

### 1.1 Componentes compartidos: construidos y NO adoptados

La auditoría grep lo dice todo:

| Componente | Líneas | Adoptantes reales | Estado |
|---|---|---|---|
| `duplicate_filter.py` + `deduplication_utils.py` (+ guía de migración de 220 líneas) | 175+203 | **0** | Código aspiracional muerto |
| `filter_presets.py` | 329 | **0** | Incompleto: los callbacks clientside que persisten en localStorage existen como strings JS que nadie registra |
| `trend_filter.py` | 23 | **0** | Switch sin cablear |
| `items_per_page_selector.py` | 126 | **1** (Videos) | OK pero opciones fijas 12/24/48/96 |
| `rule_form.py` | 265 | 0 (solo lo importa `notifications_tab_broken.py`) | Muerto |

**Conclusión:** existe una capa de UX reutilizable diseñada (dedup toggle, presets, trending, paginación) que ningún tab usa. A la inversa, cada tab re-implementa: tabla+link+fecha, buscador, caché global con `try/NameError`, y duplicación layout/callback (documentada en News/KG/ArXiv/Deals).

### 1.2 Duplicación estructural detectada (cross-tab)

1. **Render de tabla duplicado layout/callback** en news, arxiv, deals, scavenging (~90–120 líneas por tab).
2. **Caché:** 3 patrones conviven — `BaseRepository` (TTL 1 h), cachés de módulo con `global`+`NameError` (TTL 60 s en news/arxiv/deals), singletons al importar (videos, courses). Sin invalidación compartida ni botón refresh.
3. **Rutas de datos:** mezcla de `get_data_path()` (correcto), `get_project_root()` (correcto), `Path("data/...")` relativo al CWD (4chan, valencia, scavenging — roto fuera de la raíz).
4. **Highlight de búsqueda roto** en 3 tabs (inyectan `<mark>` que Dash escapa): news, deals, scavenging.
5. **`search_ids` hardcoded** en News → 3 subtabs sin búsqueda (el patrón "generar ids dinámicamente" no existe en ningún tab).
6. **Serialización de `dcc.Store` inconsistente** (lista vs json-string).
7. **`sys.path.append` hacks** en deals y arxiv.
8. **Config drift** en `data_loader.py`: `TRAVEL_SOURCES_CONFIG` espera gumroad que no está; `ECOMMERCE_SOURCES_CONFIG` perdió viajeros → repos `None` en tabs dormidos.

### 1.3 Funcionalidades transversales existentes

- **Alertas:** `src/alerts/` con `AlertEngine`, modelos de condiciones Pydantic, `data/alerts/rules.json` — sin UI (ver spec 14 §3.2).
- **Recomendaciones:** `src/recommendations/` (engine + activity_tracker) — consumido solo por el callback muerto de "related content" de News.
- **Tendencias:** `trend_utils.py` lee `data/analytics/trends/latest_trends.json` — **el productor no existe**; badges en News/ArXiv nunca renderizan.
- **API:** FastAPI (`src/api/`, 18 endpoints `/api/v1/*`) leyendo los mismos JSON que el dashboard — el dashboard NO la usa (acceso directo a ficheros). Blueprint Flask legacy (`src/web/api/routes.py`) sin registrar.

## 2. Mejoras (adopción y consolidación)

### M1 — Tabla base compartida `shared/table.py`
Extraer `render_items_table(items, columns, search_term=None)` + `highlight_segments(text, term) -> list` (fix del `<mark>` en los 3 tabs) + builder de `dbc.Table` con scroll estándar (maxHeight 800). Migrar news/deals/scavenging/KG como pilot y luego el resto. Elimina ~400 líneas duplicadas.
**Aceptación:** render idéntico visualmente (screenshot test o revisión manual); highlight visible en los 3 tabs.

### M2 — Cache y rutas unificadas
- Todo acceso a datos vía `BaseRepository` (TTL estándar 5–15 min según fuente) + `get_data_path()`/`get_project_root()` exclusivamente; eliminar los 3 antipatrones (cachés `NameError`, singletons al importar, rutas relativas CWD).
- Añadir botón 🔄 estándar `create_refresh_button(tab_slug)` que llama `repo.get(force_refresh=True)` — 1 helper, N tabs.
**Aceptación:** grep sin `Path("data` relativo en components/; grep sin `except NameError` en caches.

### M3 — Completar y adoptar `filter_presets.py`
1. Registrar los clientside callbacks (la pieza que falta: `app.clientside_callback(src, Output(...), ...)` con los strings existentes).
2. Corregir `apply_preset` para usar `dash.no_update` en vez de `[None]*n`.
3. Adoptar en News (subtabs con filtros nuevos), Ayudas, Scavenging, Deals.
**Aceptación:** crear/aplicar/borrar preset persiste en localStorage entre sesiones.

### M4 — Adoptar `duplicate_filter` en agregados
Solo donde hay agregación multi-fuente (News "Top Tech", KG "Reddit All"/"Open Source", futuro feed unificado de Tech Radar): requiere que el pipeline de dedup marque `is_duplicate/duplicate_group_id/quality_score` (el modelo TimestampedModel ya tiene los campos). Empezar por el dedup en `data_loader.deduplicate_items` extendido para escribir esos flags.

### M5 — Productor de tendencias
ETL `analytics/trends_etl.py`: computar menciones cruzadas (títulos + keywords normalizadas) entre fuentes últimas 48 h → `latest_trends.json`. Habilita badges 🔥 (news, arxiv) y `trend_filter` switch. Reutilizable para Tech Radar momentum (13 TR-F2).

### M6 — Higiene general
- Eliminar `*_broken/*_backup/*_basic/*_minimal` y `valencia_events_tab.py` legacy.
- Quitar `sys.path.append` (imports de paquete).
- `print()` → `logger` en shortcuts (y revisar resto).
- Config drift de `data_loader.py`: regenerar configs desde un único catálogo tipado (p.ej. `SOURCES.yaml` o modelos Pydantic) del que ETLs, tabs y API lean — eliminar la divergencia tabs/API/config.
- Blueprint Flask: registrar las rutas AA que el tab Benchmarks referencia (B2) o eliminar el Blueprint y moverlas a FastAPI (recomendado — un solo API).

## 3. Funcionalidades nuevas transversales

### T1 — Capa de datos única dashboard↔API
**Decisión pendiente de arquitectura** (requiere consenso): hoy el dashboard lee JSON y la API lee JSON duplicando la lógica (`data_loader` + `UnifiedItem` vs componentes). Opciones:
a) Dashboard sigue leyendo ficheros (rápido, sin red) y la API queda para terceros — **recomendado** con M2 como disciplina común (misma capa repositorios en ambos).
b) Dashboard consume su API (`/api/v1/*`) — indirección extra y dependencia de uptime propio; solo si se desea caché/transform central.
**Acción:** documentar la decisión en `docs/architecture.md` y borrar el perdedor (Blueprint Flask si toca).

### T2 — Estado de usuario unificado (ActivityTracker v2)
Hoy se proponen múltiples persistencias locales (leído/visto en News/Videos, guardados en KG/ArXib/Courses, reclamados en Scavenging, favoritos en Shortcuts). Unificar en un único cliente `user_state.js` (namespaced por tab en localStorage) + sync opcional a `data/analytics/user_state.json` vía endpoint `POST /api/v1/user-state` — alimenta el motor de recomendaciones (que ya tiene activity_tracker).
**Aceptación:** un helper JS/Python usado por ≥4 tabs; los "guardados" aparecen en el panel "Para ti" (14 §3.6).

### T3 — Debounce y clientside estándar
Norma de código (añadir a AGENTS.md/skill dashboard-tab): todo input de búsqueda con `debounce=True`; filtros que no requieran datos nuevos como clientside cuando sea posible. Reduce el re-render server-side por tecla en ~8 tabs.

### T4 — Testing de UI del dashboard
Añadir a `Tests/` una suite mínima de render por tab (dash.testing o simplemente pytest sobre `render_*_tab()` sin explosión + presencia de ids esperados) — la tarea T-023 (API drift de tests) lo agradecerá y los rewires (14) quedan cubiertos.

## 4. Roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M6 higiene (borrar legacy, sys.path, prints), highlight M1 (solo el helper, aplicar a 3 tabs), fix configs drift |
| **Corto plazo** | M1 tabla base + migración de 4 tabs, M2 caché/rutas/refresh, M3 completar presets |
| **Medio plazo** | M5 tendencias, M4 dedup en agregados, T2 estado unificado, T4 tests de render |
| **Estratégico** | T1 decisión arquitectónica dashboard↔API documentada; catálogo único de fuentes (config-driven) para ETLs+tabs+API |

**Criterios de éxito:** 0 componentes compartidos sin adoptantes; 0 antipatrones de caché/ruta; el alta de un tab nuevo reusa tabla/búsqueda/paginación/presets sin copiar código (se reduce la receta de la skill `dashboard-tab` a wiring).
