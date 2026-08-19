# Especificación de mejora — Tab 4chan Generals

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/fourchan_tab.py` + `src/etl/fourchan/fourchan_generals_etl.py`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

Muestra los hilos "General" activos (OP cuyo subject/comentario matchea `\bgeneral\b`) de 15 boards (g, vg, t, pol, biz, sci, tv, fit, mu, v, k, o, diy, his, int). Un subtab por board ordenado por actividad; `dash_table.DataTable` con sort/filter/paginación **nativos** — de hecho es el único tab que aprovecha DataTable native.

- Componente: `fourchan_tab.py` (325 líneas, ~100 de scaffolding comentado del migration).
- ETL: `fourchan_generals_etl.py` (`SimpleETL`, name `4chan_generals`): API oficial `a.4cdn.org/{board}/catalog.json`, 15 boards hardcoded, BeautifulSoup para limpiar HTML del comentario.
- Datos: `data/4chan_generals/output/latest.json` (+snapshots timestamped).
- Repositorio: `FourChanRepository(BaseRepository)` TTL 1 h.
- **Cero callbacks propios** (`register_fourchan_callbacks` es `pass` y app.py ni lo importa).

### 1.2 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| F1 | **P0** | `DATA_FILE = Path("data/4chan_generals/output/latest.json")` es **relativo al CWD** — rompe si el dashboard no se lanza desde la raíz (app.py lo admite en comentario). |
| F2 | P1 | `last_modified` se muestra como entero unix sin formatear; `timestamp` (creación) ni se muestra; `comment` (el OP) **jamás se renderiza** — es el campo con más señal. |
| F3 | P1 | Boards duplicados en dos sitios: lista del ETL y `board_descriptions` del tab → añadir un board exige tocar 2 ficheros. |
| F4 | P1 | ETL: si un run encuentra 0 generals, `load()` retorna temprano y `latest.json` conserva datos viejos sin marca de stale. |
| F5 | P2 | Caché 1 h sin botón refresh; sin búsqueda global cross-board; sin enlaces de archivo (desuarchive/warosu); sin fecha relativa ("hace 3 h"). |
| F6 | P2 | Docstring del ETL menciona Streamlit — stale (el dashboard es Dash). |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **Más boards vía config** (`a.4cdn.org/{board}/catalog.json` cubre todos: añadir p.ej. `ic`, `lit`, `g` ya está, `adv`, `wg`) | JSON oficial | El ETL es genérico; solo lista | Muy bajo | ⭐⭐ |
| **Archivos de hilos: desuarchive.org / warosu** (API JSON tipo foolfuuka: `/_/api/threads/…` según board) | REST | Historial de generals (cuándo empezó, hilos anteriores), posts archivados | Medio | ⭐⭐ |
| **4chan API boards.json** (`a.4cdn.org/boards.json`) | JSON oficial | Metadatos oficiales de boards (título, descripción) → elimina `board_descriptions` hardcoded (fix F3) | Muy bajo | ⭐⭐⭐ |
| **Futaba/2chan? no**; **lainchan/wired-7? niche** — opcional `lainchan.org/tech/catalog.json` (mismo formato 4chan API) | JSON compatible | Comunidad tech más pequeña pero afín | Bajo | ⭐ |

## 3. Mejoras a funcionalidad existente

### M1 — Ruta absoluta (fix F1)
`DATA_FILE = get_data_path("4chan_generals", "output", "latest.json")` (patrón de utils ya usado por otros tabs). Test: lanzar desde otro CWD y que cargue. Esfuerzo: B.

### M2 — Fechas legibles + columna OP preview (fix F2)
- `last_modified`/`timestamp` → fecha relativa ("hace 25 min") con tooltip ISO completo; DataTable `presentation="markdown"` permite formato enriquecido sin callbacks.
- Columna "OP" con los primeros 200 chars del `comment` (ya está HTML-stripped) + tooltip con el texto completo (`tooltip_data`).
Esfuerzo: B–M.

### M3 — Board registry único (fix F3)
Extraer `BOARDS` a `src/config/models.py` (Pydantic, env-driven `COMPONENT__SETTING` como el resto) o consumir `boards.json` del API y filtrar por la lista config. ETL y tab leen la misma fuente. Esfuerzo: B.

### M4 — Staleness en el ETL (fix F4)
Si 0 generals: escribir `latest.json` con `{"items": [], "generated_at": …}` + warning en run_summary (el estándar de BaseETL ya lo recoge en `run_summary_latest.json`). Esfuerzo: B.

## 4. Funcionalidades nuevas propuestas

### FA1 — Búsqueda global cross-board
Input sobre los subtabs que busque en subject+comment de todos los boards a la vez (1 callback, salida `4chan-global-results`). Los generals comparten recurrencia (nombres tipo "/dpt/ - Daily Programming Thread") — la búsqueda global es el caso de uso natural. Esfuerzo: B–M.

### FA2 — Fila expandida de hilo (detalle)
Click en fila → `dbc.Modal` con OP completo, stats del hilo (replies/images/velocity), link al hilo vivo + link a desuarchive del board. Esfuerzo: M.

### FA3 — Watcher de generals + alertas
`BaseWatcher` que corra el ETL cada N minutos, detecte **generals nuevos** (subject no visto en `state.json`) y emita eventos → base para notificaciones (spec 14). Caso obvio: "nuevo general en /g/ que matchea keyword {rust|homelab}". Esfuerzo: M.

### FA4 — Velocidad de hilo (activity score)
Columna derivada `replies / horas_desde_ultima_actividad` con color-coding; orden por defecto ya es actividad — hacerlo explícito y visible. Esfuerzo: B.

### FA5 — Vista compacta "todos los boards"
Tabla única con columna Board (badge) en vez de subtabs — mejor para dims de pantalla pequeñas y para FA1. Toggle subtabs/tabla. Esfuerzo: B.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M1 ruta absoluta, M2 fechas+OP preview, M4 staleness, F6 docstring, FA4 velocity |
| **Corto plazo** | M3 boards.json config única, FA1 búsqueda global, FA5 vista compacta |
| **Medio plazo** | FA2 detalle de hilo, FA3 watcher + alertas, archivos desuarchive (⭐⭐) |
| **Estratégico** | Convertir el tab en "community pulse": generals + HN Ask + Reddit ya indexados en una vista comparada (futuro) |

**Criterios de éxito:** CWD-independiente; OP visible sin salir del tab; añadir un board = cambio de config en un solo sitio; generals nuevos detectables (watcher o al menos visible diff entre runs).
