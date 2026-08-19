# Especificación de mejora — Tab 📄 ArXiv Research

> Fecha: 2026-08-17 · Estado: borrador para revisión · Ámbito: `src/web/dashboard/components/arxiv_research_tab.py` + `src/etl/arxiv/arxiv_etl.py`

## 1. Diagnóstico actual

### 1.1 Propósito y arquitectura

Navegador de papers "simplified, mirroring the News tab style": 11 subtabs de categoría (All Papers, ML, CV, NLP, Neural Networks, Robotics, RL & AI, Security, Systems & Cloud, Quantum, Data Engineering), tabla (Título+GitHub link+badge trending, Autores, Fecha), búsqueda por subtab con contador, tope `MAX_PAPERS_PER_TAB = 150`.

- Componente: `arxiv_research_tab.py` (416 líneas). Cache TTL 60 s global.
- ETL: `arxiv_etl.py` (379 líneas, `BaseETL`): watcher `ArxivWatcher` → API Atom `export.arxiv.org/api/query` con query `cat:(cs.AI OR cs.LG OR cs.CL OR cs.CV OR cs.NE OR stat.ML OR cs.SE OR cs.PL OR cs.DC)` → clustering KMeans (`NLPContentClassifier`, `model.pkl` persistido) → enriquecimiento GitHub (17 campos por paper) → 1 fichero global + 10 splits por categoría + `data/processed/cluster_statistics.json`.
- Nota: `docs/ARXIV_REFACTORING.md` describe ficheros (`enhanced_arxiv_etl*.py`) que **no existen** — doc stale.

### 1.2 Bugs y deuda (priorizados)

| # | Severidad | Problema |
|---|---|---|
| X1 | **P0** (datos) | **Query vs subtabs desalineadas**: la query solo pide 9 categorías; Robotics (cs.RO), Security (cs.CR/CY), Systems (cs.AR/OS), Quantum (quant-ph) y Data Engineering (cs.DB/DS/IR) solo se llenan con tags secundarios de papers que traen la categoría extra → subtabs estructuralmente subalimentadas. |
| X2 | P1 | Campos calculados y jamás mostrados: `summary` (abstract), `pdf_url`, `cluster_id/label/keywords`, `extracted_keywords`, 17 campos GitHub (solo se pinta el link). |
| X3 | P1 | ~90 líneas de render duplicadas layout/callback; el sort muta la lista cacheada in-place; caché global sin lock. |
| X4 | P1 | Búsqueda sin debounce; re-render completo de tabla por tecla; `get_trending_items_map()` relee disco en cada callback. |
| X5 | P2 | Store serializa 150 papers al layout y el `State` no se usa; `sys.path.append` hack; sin paginación real (cap 150), sin export, sin vista detalle. |
| X6 | P2 | `docs/ARXIV_REFACTORING.md` stale; `config.py::EnhancedArxivConfig` y `services/` (scoring/analysis/integration) existen y no los usa el ETL — otra refactorización a medias. |

## 2. Fuentes de datos adicionales

| Fuente | Tipo / API | Qué aporta | Esfuerzo | Prioridad |
|---|---|---|---|---|
| **Semantic Scholar API** (`api.semanticscholar.org/graph/v1/paper/search?query=&fields=…` o match por `externalIds.ArXiv`) | REST, sin key (100 req/5 min; key gratuita para más) | Citaciones, `influentialCitationCount`, tldr — enriquecimiento directo del record actual por arxiv id | Bajo | ⭐⭐⭐ |
| **Hugging Face Daily Papers** (`huggingface.co/papers` — RSS/scrape de la home) | Scrape | Papers AI **curados con upvotes** de la comunidad — alta señal/bajo ruido; subtab nueva | Bajo | ⭐⭐⭐ |
| **Papers with Code** (`paperswithcode.com/api/v1/papers?arxiv_id=…`) | REST oficial | Paper↔repo↔leaderboard; el import ya está guardado en el ETL (unused) — revivirlo | Bajo | ⭐⭐⭐ |
| **OpenReview API v2** (`api2.openreview.net`) | REST | Reviews y notas de NeurIPS/ICML/ICLR — calidad de aceptación | Medio | ⭐⭐ |
| **alphaXiv / emergentmind** (agregadores de discusión de papers) | Scrape | Discusión comunitaria por paper | Medio | ⭐ |
| **bioRxiv/medRxiv RSS** (si se quiere fuera de CS) | RSS | Amplitud disciplinar | Bajo | ⭐ |
| **DBLP API** (`dblp.org/search/publ/api?q=…&format=json`) | REST oficial | Tracking por autor/institución — subtab "autores que sigo" | Bajo | ⭐⭐ |
| Ver además `docs/potentialsources/academic-research-sources.md` (OpenAlex ⭐ destacado: `api.openalex.org/works?filter=…` libre y estable para citaciones/autor). | REST libre | Citaciones y metadatos sin key | Bajo | ⭐⭐⭐ |

## 3. Mejoras a funcionalidad existente

### M1 — Alinear query con las subtabs (fix X1)
Opción recomendada: partir el fetch en 2–3 queries por grupos de categorías (para no revivir el "Query too complex" documentado) p.ej. `(cs.RO) OR (cs.CR OR cs.CY)`, `(quant-ph AND cat:quant-ph…)`, y ejecutarlas secuencialmente con el delay existente. Aceptación: subtab Robotics/Security/Quantum con volúmenes comparables a ML/NLP tras 1 run.

### M2 — Fila expandible con abstract + cluster
Reemplazo de bajo esfuerzo para X2: columna "▸" que expande (`dash_table` row-selectable o rebuild por callback) mostrando abstract completo, `cluster_label` + `cluster_keywords`, y badges de GitHub (⭐/issues/última actualización — datos ya presentes). Mantener un solo callback por output.

### M3 — Consolidar el render (fix X3)
Función única `render_papers_table(papers, search_term)` usada por layout y callback (patrón pedido también en News M7); sort sobre copia (`sorted(...)` no in-place); caché con `threading.Lock` o migración a `BaseRepository`.

### M4 — Debounce + caché de trends (fix X4)
`debounce=True`; `get_trending_items_map` memoizada con el TTL de la caché de papers.

### M5 — Decidir el destino de services/ (fix X6)
`scoring_service/analysis_service/integration_service` + `EnhancedArxivConfig`: integrarlos de verdad (son el diseño natural para M1 y para el enriquecimiento de Semantic Scholar) o eliminarlos. Actualizar/borrar `docs/ARXIV_REFACTORING.md`.

## 4. Funcionalidades nuevas propuestas

### AR1 — Vista "Temas" (clusters) del corpus
**Objetivo:** aprovechar el clustering KMeans ya computado (`cluster_statistics.json` existe, sin consumidor).
**UI:** subtab "🧩 Temas": cards por cluster (label, keywords, nº papers esta semana, δ vs semana previa si hay histórico) → click filtra la tabla a ese cluster.
**Callbacks:** 1 render + 1 filtro.
**Aceptación:** cluster con keywords legibles; navegación cluster→papers sin recargar datos.
**Esfuerzo:** M.

### AR2 — Métricas de citación enriquecidas
Columnas Citas / Citas influyentes (Semantic Scholar u OpenAlex por `arxiv_id`), badge "📈 trending en citas" si Δcitaciones ≥ X entre snapshots (requiere histórico: los timestamped ya existen). Cache de enriquecimiento por id para respetar rate limits. Esfuerzo: M.

### AR3 — Biblioteca personal de papers
⭐ guardar + tags propios (`data/arxiv/library.json` vía callback), subtab "Mi biblioteca" con export BibTeX (generación clientside o endpoint ligero). Integración con recommendations engine. Esfuerzo: M.

### AR4 — Digest diario de IA
Snapshot diario de top-N por categoría (score = cluster keywords match + citas + HF upvotes si AR/HF papers) → página "Today" tipo feed + base para email/notificación. Esfuerzo: M.

### AR5 — Seguimiento de autores
Lista configurable de autores (config) → subtab "Autores" con papers recientes por autor (dato ya en records `authors[]`; nuevas apariciones detectables entre runs). Esfuerzo: B–M.

## 5. Recomendaciones y roadmap

| Horizonte | Acciones |
|---|---|
| **Quick wins** | M3, M4, X5 store muerto, fix doc stale |
| **Corto plazo** | M1 queries por grupo (desbloquea 5 subtabs), M2 abstract/expand, Semantic Scholar + Papers with Code + HF Daily Papers (⭐⭐⭐) |
| **Medio plazo** | AR1 clusters, AR2 citaciones, AR3 biblioteca BibTeX |
| **Estratégico** | AR4 digest + AR5 autores; M5 decisión sobre services/; evaluar consolidar "ArXiv" + futuro "AI Research" (ai_research_tab.py legacy) en un único tab de investigación |

**Criterios de éxito:** 11/11 subtabs alimentadas; abstract y clusters visibles (0 campos muertos); ≥1 fuente de citación enriquecida; export BibTeX operativo.
