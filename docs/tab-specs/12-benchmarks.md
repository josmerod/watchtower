# Especificación de mejora — Tab 🏆 Benchmarks

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/benchmarks_tab.py` + `src/etl/benchmarks/`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

Leaderboards de modelos AI: 3 subtabs — 🌐 Community Leaderboard (LMArena MT-bench/MMLU + pricing por proveedor), 🏆 BridgeBench.ai (6 categorías), 📊 Artificial Analysis (LLM + Image Arena). Tablas estáticas con heat-map coloring y medallas; **sin callbacks** (`register_benchmarks_callbacks` es `pass`).

- Componente: `benchmarks_tab.py` (1.044 líneas, 3 secciones mezcladas en un fichero).
- ETLs (los 3 registrados):
  - `llm_leaderboard_etl.py` → HF Space `lmarena-ai/arena-leaderboard` (CSVs) + repo GitHub `JonathanChavezTamales/llm-leaderboard` (pricing). ✅ único con datos hoy (341 scores / 211 precios).
  - `bridgebench_etl.py` → scrape bridgebench.ai (frágil: regex/Next.js JSON; su propio docstring lo da por "broken" por cambio de URL).
  - `artificial_analysis_etl.py` → API `artificialanalysis.ai/api/v2` con key (`ARTIFICIAL_ANALYSIS_API_KEY`, tier gratis 1.000/día). Define **6 endpoints** (llm, text-to-image, image-editing, tts, t2v, i2v) pero solo fetchea 2.

### 1.2 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| B1 | **P0** (UI) | `_fmt_score` definido **dos veces** (líneas 333 y 922): la segunda sobrescribe la primera y todos los scores de AA se renderizan "75.00"/"1300.00" en vez del formato corto. |
| B2 | **P0** | El hint del tab apunta a `api/v1/benchmarks/artificial-analysis` — **ruta inexistente** (la real es Flask `/api/benchmarks/...` sin registrar, y FastAPI no tiene ese subpath). Enlace muerto en producción. |
| B3 | P1 | BridgeBench roto upstream + 0 datos en disco → 1 de 3 subtabs es un placeholder permanente. |
| B4 | P1 | Lógica interactiva muerta: `_build_aa_llm_table(models, filter_open, sort_by)` soporta filtro open/proprietary y sort "lower is better" pero **solo se llama con defaults** (comentario en código lo admite). Caps hardcoded 100/50 sin paginar. |
| B5 | P2 | Muerte por mil cortes: `max(...)` calculado y descartado (línea 635), `_get_aa_meta_text` ignora `filename`, `_score_cell` compara `"—"` duplicado, `COLUMN_LABELS["bs"]` sin uso; 2 ETLs fuera del framework BaseETL (urllib plano). |
| B6 | P2 | Sin historial comparativo pese a escribirse snapshots timestamped; sin búsqueda de modelo; campos interesantes sin render (hle, livecodebench, math_500, aime, context_length, price_blended). |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **LiveBench** (results JSON en GitHub `LiveBench/LiveBench` — actualización mensual) | JSON en repo | Benchmark contamination-free con categorías (reasoning, coding, math, data); reemplaza la dependencia frágil de BridgeBench | Bajo | ⭐⭐⭐ |
| **SWE-bench Verified leaderboard** (datos en `swe-bench.github.io`, fuente JSON/CSV pública) | JSON/CSV | El estándar de coding agents — muy alineado con el uso dev del usuario | Bajo | ⭐⭐⭐ |
| **Aider LLM leaderboard** (`aider.chat/docs/leaderboards` — tabla publicada + datos en GitHub repo) | Scrape/JSON | Edit-code ability (polyglot) que otros benches no cubren | Bajo | ⭐⭐ |
| **OpenRouter rankings** (`openrouter.ai/api/v1/models` público) | REST sin key | Precio + **uso real** (tokens consumidos por la comunidad) = proxy de popularidad; enriquece la vista pricing | Bajo | ⭐⭐⭐ |
| **HF Open LLM Leaderboard** (datasets/spaces públicos) | Dataset | Modelos open-weights europeos/españoles; filtro por idioma ES interesante | Medio | ⭐⭐ |
| **Artificial Analysis: 4 endpoints ya definidos** (image-editing, TTS, t2v, i2v) | REST ya codificado | Subtabs nuevas (voz/vídeo) casi gratis — solo `PRIMARY_ENDPOINTS` + render | Bajo | ⭐⭐⭐ |
| **Epoch AI** (`epoch.ai/data` benchmarks públicos) | CSV/JSON | Frontier benchmarks longitudinales (GPQA, HLE) | Bajo | ⭐ |

## 3. Mejoras a funcionalidad existente

### M1 — Fix de formato y rutas (fix B1/B2)
Eliminar la primera `_fmt_score` (o unificar) y apuntar el hint a la ruta Flask real una vez registrada, o eliminar el hint. Tests de snapshot del render (dash.testing o simple assert de función) para evitar regresión.

### M2 — Decidir BridgeBench (fix B3)
Sustituir por LiveBench + SWE-bench (ambos ⭐⭐⭐ y estables) o aislar BridgeBench como "experimental" detrás de config. No mantener 1/3 del tab en placeholder permanente.

### M3 — Activar la interactividad latente (fix B4)
Wire de los parámetros existentes: checklist Open/Proprietary (valores del propio dataset), dropdown sort (intelligence/coding/math/price…), para LLM e Image Arena. 2 callbacks (`aa-llm-controls`, `aa-image-controls`). Añadir búsqueda por nombre de modelo (input con debounce filtrando la tabla) y paginación 50/100/todos.

### M4 — Partir el fichero
`benchmarks_tab/` paquete con `community_leaderboard.py`, `artificial_analysis.py`, `livebench.py` + `shared.py` (`_fmt_score`, `_score_cell`, medallas). Facilita M2/M3 y cumple la convención de isolación por componente.

### M5 — Limpieza (fix B5)
Eliminar dead code listado; migrar los 2 ETLs urllib a `SimpleETL` (consistencia + run summaries + circuit breaker).

## 4. Funcionalidades nuevas propuestas

### BM1 — Series temporales de precio/capacidad
**Objetivo:** ver la evolución "inteligencia por dólar" en el tiempo.
**Datos:** los snapshots timestamped ya existen (`artificial_analysis_llms_<ts>.json`, leaderboard CSVs datados).
**UI:** subtab "Trends": gráfica línea (median price_in por mes; median intelligence_index; ratio inteligencia/precio) + tabla de deltas (subida/bajada de precio por modelo entre snapshots).
**Aceptación:** al menos 2 puntos temporales; tooltip con modelo/valor.
**Esfuerzo:** M.

### BM2 — Comparador de modelos (2–4 side-by-side)
Checkbox en tablas → vista comparación columna-por-modelo con heat-map por celda (reutiliza `_score_cell`). Coste total estimado para carga de trabajo configurable (inputs × precio). Esfuerzo: M.

### BM3 — "Best for…" recomendador
Selección de caso de uso (coding local / API barata / visión / imagen) → ranking compuesto según pesos sobre los campos existentes + filtro open_weights y contexto. 1 callback. Esfuerzo: B–M.

### BM4 — Modalidades nuevas de AA (voz/vídeo)
Desbloquear `image-editing`, `tts`, `t2v`, `i2v` en `PRIMARY_ENDPOINTS` (config env) + subtabs con el patrón de render existente. La evaluación TTS/t2v es difícil de encontrar agregada — alto valor único. Esfuerzo: B por subtab (el render es tabular).

### BM5 — Cross-link con News/ArXiv
Nombre del modelo como link → búsqueda prefijada en News global search (F1 de News) y ArXiv. Convierte el tab en entrada de investigación. Esfuerzo: B.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M1 (formato + ruta), B5 dead code, BM5 cross-links |
| **Corto plazo** | M4 partir fichero, M3 filtros/sort/búsqueda, LiveBench + SWE-bench (⭐⭐⭐), OpenRouter pricing/uso |
| **Medio plazo** | BM4 modalidades AA restantes, BM1 series temporales, M2/M5 decisión BridgeBench + migración ETL |
| **Estratégico** | BM2 comparador con coste de carga de trabajo, BM3 recomendador de caso de uso; consolidar "benchmarks" como capa de referencia citable desde Deals/Videos (¿qué modelo mola ahora?) |

**Criterios de éxito:** 3/3 subtabs con datos reales (con LiveBench/SWE-bench); filtros y búsqueda operativos; 0 funciones duplicadas; ≥1 gráfica de evolución temporal.
