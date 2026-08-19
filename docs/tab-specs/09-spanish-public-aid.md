# Especificación de mejora — Tab 🏛️ Ayudas Públicas

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/spanish_public_aid_tab.py` + `src/etl/spanish_public_aid/`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

"Ayudas y subvenciones organizadas de local a nacional: Burjassot → Valencia → Comunidad Valenciana → España." El tab más completo del dashboard en visualización: botones de ámbito geográfico, 4 summary cards, buscador + 5 filtros, gráficos (pie categoría + bar ámbito), timeline de deadlines (plotly) y `DataTable` con sort/filter/pagination nativos, tooltips y conditional styling.

- Componente: `spanish_public_aid_tab.py` (854 líneas). Usa `get_data_path` (✅) y `BaseRepository`.
- ETL: `spanish_public_aid_etl.py` (1.204 líneas, `SimpleETL`) con **6 fuentes**: BDNS (PAP Hacienda), GVA procedimientos + dadesobertes, DOGV, Ayuntamiento Valencia, Burjassot (transparencia), LABORA.
- Módulos paralelos NO usados por el ETL: `scraping_service.py` (283 l), `classification_service.py` (181 l), `enhancement_service.py` (211 l) + un segundo config (`config.py` dataclass) — la refactorización descrita en `docs/SPANISH_AID_REFACTORING.md` quedó a medias.

### 1.2 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| A1 | **P0** (datos) | **`closing_date` y `amount` nunca se rellenan**: el ETL crea `AmountModel` con defaults y no fija fechas → la timeline de deadlines, el filtro urgente, "Días restantes" y la columna Importe son estructuralmente vacíos. La mitad del valor del tab (deadlines) es decorativa. |
| A2 | **P0** (UI) | Controles muertos en el layout: los **5 botones de ámbito** (Burjassot/Valencia/CV/España/Todos) y el **dropdown beneficiario** no participan en ningún callback. Además los valores del dropdown (`personal/ong/empresa`) no matchean el enum del modelo (`persona_fisica/empresa/ong`). |
| A3 | P1 | Filtro urgente sin cota inferior: `(closing - now).days <= 7` incluye ayudas cerradas hace meses (days negativo). La tabla clampea `days_left` a 0, el filtro no. |
| A4 | P1 | "Update Data" solo relee el JSON cacheado (TTL 1 h) — no ejecuta el ETL ni invalida; "Last updated" muestra `datetime.now()` del render, no la frescura del dato. |
| A5 | P1 | `stats_data` se carga con un repo dedicado y jamás se renderiza. |
| A6 | P2 | Búsqueda sin debounce con rebuild de `tooltip_data` completo por tecla; filtros hardcoded (el ETL emite más categorías de las que el dropdown ofrece). |
| A7 | P2 | Link del footer placeholder (`github.com/your-repo/...`); `__main__` de debug en producción; refactoring a medias (A8) confunde. |
| A8 | P2 | Duplicidad config: `src/config/models.py::SpanishPublicAidConfig` (20/source) vs `src/etl/spanish_public_aid/config.py` (100/source) sin usar. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **BDNS API transversal** (los endpoints JSON que consume el frontend Angular de `pap.hacienda.gob.es`, p.ej. `…/bdnstrans/api/…` con filtros por fecha/ámbito) | REST no documentada pero estable; inspección de red | **Registros con fechas y cuantías reales** → arregla A1 de raíz; además convocatorias resueltas y datos del beneficiario cuando es público | Medio | ⭐⭐⭐ |
| **DOGV Atom/RSS** (`dogv.gva.ca` / `dogv.gva.es` feed por materia subvenciones) | Feed | Entradas con enlace al PDF oficial y fecha de publicación — dedupe natural por número de DOCV | Bajo | ⭐⭐⭐ |
| **EU Funding & Tenders Portal** (`ec.europa.eu/info/funding-tenders` búsqueda; API `api.ted.europa.eu` para licitaciones, y `ec.europa.eu/api/…` para grants) | REST | Convocatorias europeas (Horizonte Europa, Digital Europe) aplicables desde España | Medio | ⭐⭐ |
| **GVA dadesobertes** (ya referenciada): ampliar a datasets de subvenciones de años en curso por consellería | CKAN API | Datos estructurados oficiales sin scraping frágil | Bajo | ⭐⭐ |
| **Red.es / CDTI / ICEX** (convocatorias de innovación) | Scrape | Ayudas de entidad pública empresarial que no siempre caen en BDNS | Bajo | ⭐⭐ |
| **Diputación de Valencia** (`dipvalencia.es` convocatorias) | Scrape | Cubre el hueco entre municipal y autonómico | Bajo | ⭐ |

## 3. Mejoras a funcionalidad existente

### M1 — Deadlines e importes reales (fix A1)
1. Priorizar BDNS API (§2): sus registros traen `fechaFinPlazo` y `cuantía` — mapear a `closing_date`/`amount`.
2. Fallback heurístico de parseo en las fuentes scrape (regex de "hasta el DD/MM/AAAA", "plazo", importes con €) en `enhancement_service.py` (ya existe, sin usar — es su propósito natural).
3. Marcar `is_verified`/`data_quality_score` según la fuente del dato (API=1.0, heurística=0.6).
Aceptación: ≥60% de registros con `closing_date`; timeline con puntos reales; test de regresión de parseo con textos reales de cada fuente.

### M2 — Cablear los controles muertos (fix A2)
- Botones de ámbito → `State("scope-filter","value")` dentro de `update_aids_table` (o dropdown `scope-filter` como salida compartida con `allow_duplicate`).
- Beneficiario: corregir opciones al enum del modelo y añadirlo como Input del callback. Un solo callback por salida (patrón single-callback del repo).

### M3 — Urgente con ventana válida (fix A3)
`0 <= days_left <= 7 and status == "abierta"`. Test unitario con cierre pasado, cierre en 3 días, sin fecha.

### M4 — Frescura honesta (fix A4)
- "Last updated" = `max(record.last_updated)` o mtime del `_latest.json`.
- Botón "Update Data" → invalida `force_refresh=True`; tooltip explicando que el ETL corre por cron (`run_all_etl.sh`), no desde la UI (o si se desea ejecutar: endpoint interno con confirmación — ver consideraciones en spec 15).

### M5 — Stats reales (fix A5)
Renderizar `spanish_public_aid_stats_latest.json` en las summary cards (por fuente: nº ayudas, última ejecución, calidad media) — el dato ya existe.

### M6 — Completar o revertir la refactorización (fix A7/A8)
Decidir: terminar la extracción a `scraping/classification/enhancement_service` (los tres ficheros ya existen) y borrar el segundo config, **o** borrar los ficheros no usados y documentar el monolito. Estado actual = lo peor de ambos.

## 4. Funcionalidades nuevas propuestas

### PU1 — Alertas de deadline (watcher de ayudas)
**Objetivo:** no perder una convocatoria por fecha.
**Implementación:** `BaseWatcher` (`src/watchers/spanish_aid_watcher.py`) que compare runs y emita eventos: (a) nueva convocatoria que matchee keywords del perfil (vivienda/emprendimiento/tech), (b) deadline a ≤7 días de una ayuda guardada. Eventos a `data/watchers/spanish_aid/events/` → canal de notificaciones (spec 14).
**Aceptación:** evento `new_aid` con título/URL/deadline; sin falsos positivos por dedup título.
**Esfuerzo:** M.

### PU2 — "Mis ayudas" (guardadas + estado)
⭐ por convocatoria + estado (pendiente/solicitada/descartada) persistido en `data/alerts/saved_aids.json` (o localStorage). Subtab/filtro "Guardadas" con countdown por tarjeta. Es el tab con mayor coste de no-seguimiento: esto lo convierte en herramienta activa. Esfuerzo: M.

### PU3 — Checklist de solicitud
Por ayuda guardada: checklist editable (documentación requerida — el modelo ya tiene `requirement/document` sub-models) con progreso. Esfuerzo: M.

### PU4 — Digest semanal
Resumen generado (JSON/HTML/email): nuevas ayudas del ámbito elegido + deadlines de la semana → integración con el futuro canal de notificaciones. Esfuerzo: M.

### PU5 — Calendario de plazos
Vista mensual estilo Valencia VA1 con los closing dates; color por categoría. Esfuerzo: B (si VA1 extrae el componente calendario como helper compartido).

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M2 cablear controles, M3 urgente, A5 stats, M4 frescura, fix enum beneficiario |
| **Corto plazo** | **M1/BDNS API (⭐⭐⭐ — desbloquea medio tab)**, DOGV feed, PU2 guardadas |
| **Medio plazo** | PU1 watcher de deadlines, PU5 calendario, EU Funding portal, M6 decisión refactor |
| **Estratégico** | PU3 checklists, PU4 digest semanal; patrón común "deadline-driven" con Valencia Events y Scavenging (countdown compartido) |

**Criterios de éxito:** closing_date en ≥60% de registros; 0 controles muertos; timeline y urgente operativos sobre datos reales; el usuario puede seguir una ayuda de principio a fin dentro del tab.
