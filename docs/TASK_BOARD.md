# Task Board

Single source of truth for actionable work on Watchtower. Edited in place by
humans and by the `task-board` skill (which iterates one task at a time).

> **Documentos hermanos:** `docs/ROADMAP.md` (horizonte priorizado + valor) ·
> `docs/TASK_BOARD_ARCHIVE.md` (tareas cerradas + changelog histórico) ·
> `docs/FEEDBACK.md` (cajón de sastre del usuario — triajear cada sesión).

## Conventions

- **One task per row.** Rows sorted: `in-progress` first, then `todo` (by
  priority, oldest first), then `blocked`.
- **Status:** `todo` · `in-progress` · `blocked` · `done`.
- **Priority:** `P0` (blocker / production down) · `P1` (high) · `P2` (medium) ·
  `P3` (nice-to-have).
- **Area:** `etl` · `dashboard` · `api` · `infra` · `quality` · `docs` · `sec`.
- **One task `in-progress` at a time.** Flip to `done` only after verification:
  run the command, cite the output, validate visually in production.
- **ID scheme:** `T-NNN`, zero-padded, never reused.
- Done rows move to `TASK_BOARD_ARCHIVE.md` verbatim (compactación).
- Keep `Notes` terse — long design goes in `docs/` or a commit.

## Board

| ID | Status | Priority | Title | Area | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| T-048 | todo | P2 | TR-F2 momentum por tecnología (spec 13) | dashboard | Menciones esta semana vs media móvil 4 semanas → "Subiendo 🔺/Bajando 🔻" bajo el radar plot. **Diferido hasta ~2026-09-16**: los snapshots M5 (kdnuggets + cloud_updates) empezaron el 2026-08-19 y la media de 4 semanas necesita historia. Desbloqueado por T-041/TR-F3 ya mergeado. |
| T-091 | todo | P2 | CVEs del stack vía OSV.dev (keyless, más allá del KEV) | sec | Extiende T-081: KEV solo cubre CVEs *activamente explotados*; OSV.dev (`POST api.osv.dev/v1/query`, keyless, verificado 2026-09-10) indexa GHSA+CVE por paquete — n8n (npm) y homeassistant (PyPI) consultables; para jellyfin/immich evaluar query por repo GHSA. Filtrar ≥high, unir a la card 🧰 "Tu stack" (severity + fixed-in) + reglas stack_cve_*. Pacing cortés + sidecar cache como en T-058/079. |
| T-092 | todo | P2 | EOL del stack vía endoflife.date (keyless) | etl | API v1 pública sin key (verificado 2026-09-10): fechas de EOL/soporte por producto. Mapear los productos del stack que cubra (Unraid OS, Ubuntu/Debian si aplica, lenguajes runtimes) → columna "EOL" en el subtab 🧮 Mi stack + regla de Notifications a <90 días ("n8n 2.x queda sin soporte en…"). Cierra el círculo salud-del-stack: releases (ya) + CVEs (T-081/091) + EOL (este). |
| T-047 | todo | P3 | Re-evaluate BridgeBench after V3 ships | etl | 2026-08-27: the Elo leaderboard page migrated to client-side rendering (Next.js behind Cloudflare — no `<table>` in HTML, no discoverable API endpoints, only 55KB shell). The ETL keeps last-good data and logs a warning on failure. When "V3 ships soon" lands: re-inspect for a JSON API, or render via the browserless container (BROWSERLESS_ENDPOINT already mounted) if the tab matters enough. |
| T-084 | todo | P3 | API v1: /digest, /security/kev, /valencia/events (+ consolidación) | api | Ampliar la API pública para n8n: digest compilado, KEVs activos, próximos eventos de Valencia (automatizaciones de calendario). Patrón public.py + test anti-drift si replica tablas. **Juntar en la misma pasada con la consolidación de T-095** (una sola revisión de routers.py). |
| T-085 | todo | P3 | KG: first_seen + badge NUEVO (spec 03 M6 backlog) | dashboard | Mismo patrón que Videos: first_seen en records de KG + badge "NUEVO" comparando localStorage.last_visit + contador en toolbar. Valor: ver qué llegó nuevo desde tu última revisión. |
| T-086 | todo | P3 | Markets: portfolio local (holdings × cotización) | dashboard | Holdings en localStorage (sin servidor, sin claves): tabla "Mi cartera" con cantidad × precio CoinGecko → valor actual, P/L vs precio medio de compra. Personal y keyless; el dato nunca sale del navegador. |
| T-088 | todo | P3 | Videos: dropdown de tema/categoría (spec 04 M4 backlog) | dashboard | El manager ya marca canales aa-*/zz-* como temas (los cuenta la vista Canales). Exponer filtro dropdown de tema junto a canal/fecha. |
| T-089 | todo | P3 | Dashboard: modal "Novedades del deploy" | dashboard | changelog.json versionado en el repo → modal primera-visita (localStorage.last_changelog) mostrando las novedades del deploy actual. Auto-documenta los cambios para el usuario final. |
| T-090 | todo | P3 | Backups: recrear run_backup.py + verificación de restore | infra | **Hallazgo 2026-09-10**: run_backup.py NO existe en disco (borrado en un commit antiguo) — la llamada del orquestador es un no-op silencioso (guard os.path.exists). `src/utils/backup_utils.py` (505 LOC, con test) sobrevive como librería. Recrear run_backup.py sobre backup_utils + smoke de restore: desempaquetar el último backup a tmp, contar ficheros críticos (latest de cada fuente), validar JSON de una muestra. "Un backup no verificado no es un backup". |
| T-093 | todo | P3 | Racionalizar fuentes invisibles (auditoría 2026-09-10) | etl | Museums, entertainment (trakt/spotify), sec_edgar, who_outbreaks y lesswrong corren cada ciclo del orquestador pero NINGÚN consumidor lee su output (tabs borrados hace meses, sin entrada en search ni API útil). Decidir por fuente: matar ETL+entrada data_loader, o devolverle visibilidad (subtab/API/search). Evidencia completa en la auditoría del commit 458cfd4. |
| T-094 | todo | P3 | Dedup de helpers del dashboard (auditoría) | quality | Cluster fechas: 6 parsers ISO copy-pasted (courses/games/spanish_aid/security/metrics/digest) → `utils.parse_date_universal` (que hoy solo usan tabs muertos). Cluster paginación: 4 copias hand-rolled (videos/news/courses ×2) → `shared/table.paginate` (1 usuario hoy). Bonus: prune de shortcuts.css (selectores de features muertas; conservar overrides genéricos .badge/.alert). |
| T-095 | todo | P3 | API v1: racionalizar rutas sin consumidor | api | routers.py sirve /ecommerce /games /travel /research /intelligence /museums /entertainment /benchmarks sin tests/docs/frontend + 6 rutas indocumentadas (/arxiv /ai-platforms /expanded /spanish-aid /cloud-updates /valencia-local). Con T-084: documentar las útiles (API_DOCS + página /api del dashboard), borrar las demás. Nota: la URL pública aún no proxy-ea /api (pendiente usuario). |
| T-096 | todo | P3 | Convención de logging única | quality | Split por drift: 112 módulos usan `src.utils.logging.get_logger` vs 77 stdlib `logging.getLogger` (api/services/base.py incluidos). Estandarizar sobre get_logger O santificar stdlib en AGENTS.md y simplificar el wrapper. Churn alto / valor bajo: hacerlo en pasadas pequeñas tocando fichero por otras razones. |
| T-038 | blocked | P3 | Fix Artificial Analysis ETL (API changed, needs paid key) | etl | Renumbered 2026-08-19 from the original T-026 proposal (ID collided with the spec-rollout rows). The AA v2 API requires an API key (401 without). `ARTIFICIAL_ANALYSIS_API_KEY` env var is supported by the ETL but none is configured; some v2 endpoints also 404'd, suggesting further restructuring. To restore: obtain a key from artificialanalysis.ai, set it in `.env`, verify endpoint paths. Blocked on the user providing a key. |

## Changelog

- 2026-09-10 — **Limpieza profunda + brainstorm 4ª generación** (server en mantenimiento): auditoría completa con 4 agentes paralelos → **purge de ~18k LOC muertos** (15 tabs muertos del dashboard, cadena factory/DI/scraping aspiracional, AlertEngine inerte — rules_store es el camino real, 18 modelos huérfanos, ETL security_feeds duplicado que corría cada ciclo, sub-configs de settings sin lectores, constants 90+→2, root utils/ + setup.py + PNGs committeados, 44 skips e2e permanentes, fake tests sin aserciones). **6 bugs reales arreglados** (validators pydantic v2 de news con compute verificado en ambos paths, is_popular, health_monitor campo inexistente, pandas-3 adhd, fallback cloudscraper coursera muerto, APIConfig keys nunca definidas). Commits `458cfd4` + `e01b3bf`. **Verificación local: pytest 960/6, ruff, mypy 246 ficheros, pre-commit 20/20** — deploy + validación en prod PENDIENTES hasta que acabe el mantenimiento. Board compactado (T-061/T-062 verificados en código y cerrados; T-010 cerrado; T-059 duplicado eliminado; 37 filas done al archive). Brainstorm con investigación: **T-091 OSV.dev** (keyless, CVEs por paquete — el KEV solo ve lo explotado activamente) y **T-092 endoflife.date** (keyless, EOL del stack) + T-093..T-096 de hallazgos de auditoría. Pendiente de decisión del usuario: añadir pytest-playwright y escribir 2-3 e2e de tabs vivos, o aceptar cobertura unit+render.

- 2026-09-03 — **Oleada 7 (3 agentes)**: cerrados T-081 (CVEs KEV×stack — 0 matches hoy, machinery y reglas HIGH verificadas en prod), T-082 (Radar → **23 fuentes**: Lemmy/PH/Azure añadidas; GCP blog negativo por JS-render), T-083 (resumen 24h en Notifications). Suite **1192/52** (+83), mypy verde (327 ficheros), pre-commit 20/20; 4 commits, deploy + validación in-container/API. Nota menor: slot GCP muerto en cloud_updates detectado — **resuelto 2026-09-10** (feed eliminado).

- 2026-09-02 — **Brainstorm 3ª generación** (petición del usuario): 9 tareas nuevas T-081..T-090 (sin T-087, reservado). Ejes: personalización de stack (CVEs KEV×stack), ronda de probes #3, cierre del loop de eventos, API para n8n, UX/infra P3.

- 2026-09-02 — **Oleada 6 (3 agentes, brainstorm 2ª gen)**: cerrados T-078 (Radar → **20 fuentes**), T-079 (motor OpenAlex que INDEXA arXiv), T-080 (venue real 23/30 Valencia). Deuda mordida: tabla radar API desincronizada → sync + test anti-drift. Suite **1109/52**; 6 commits, 2 deploys.

- 2026-09-01 — **Oleada 5: T-003 CERRADO — mypy repo a CERO** (451→0 en dos días). T-077: 7 módulos muertos borrados + etl_registry reparado. ~13 bugs reales destapados por la campaña. Suite 1075/52; 5 commits; deploy + smoke completo.

(Histórico completo en `docs/TASK_BOARD_ARCHIVE.md`.)
