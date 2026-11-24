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
- **Changelog:** newest first. Entries older than two months move verbatim to
  `## Changelog histórico` in the archive.
- No private addresses, hostnames or credentials in this file: it is tracked in
  a public repository (write `<host>`).

## Board

| ID | Status | Priority | Title | Area | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| T-106 | todo | P1 | Backups en producción: `run_backup.py` no viaja al contenedor | infra | `INCLUDE_PATHS` no lo incluye y el orquestador solo lo llama si existe (`run_all_etl_orchestrator.py:263`) → **sin backups en prod desde el 2026-09-10**; la fila T-090 daba por hecho que correría. Verificado 2026-11-24: `absent: run_backup.py` en el contenedor. Antes de incluirlo necesita un volumen persistente para `/app/backups` (hoy comprimiría ~3 GB en la capa del contenedor). |
| T-107 | todo | P1 | Decisión: las API keys no llegan al contenedor | infra | `docker run` de `deploy.py` solo pasa `TZ` y `BROWSERLESS_ENDPOINT`, y `.env` no va en el archivo. Verificado 2026-11-24 (solo nombres de variable): el contenedor no tiene ninguna clave. Afecta a los ETLs que leen `GITHUB_TOKEN`/`GH_TOKEN`, `PRODUCTHUNT_API_TOKEN`, `ARTIFICIAL_ANALYSIS_API_KEY`, `NVD_API_KEY` e `IPT_*`. Opciones: montar `.env` read-only en `/app/.env` o pasarlo con `--env-file`. De paso auditar `.env.example`: 17 de sus 40 claves no corresponden a ningún ajuste (`WATCHTOWER_NOTIFICATIONS__*`, `WATCHTOWER_SECURITY__*`, `CODA_API_KEY`…). Relacionada: T-038. |
| T-048 | todo | P2 | TR-F2 momentum por tecnología (spec 13) | dashboard | Menciones esta semana vs media móvil 4 semanas → "Subiendo 🔺/Bajando 🔻" bajo el radar plot. **Desbloqueada 2026-11-24**: los snapshots M5 (kdnuggets + cloud_updates) empezaron el 2026-08-19 y ya hay historia de 4 semanas. Desbloqueada por T-041/TR-F3 ya mergeado. |
| T-108 | todo | P2 | Tests que escriben en `data/` real | quality | `Tests/etl/test_base_etl.py` escribe en `data/` (~25 directorios de test por ejecución) y `_reset_circuit_breakers` borra todos los `circuit_breaker.json` que encuentra debajo. Aislar con `tmp_path` + redirección de la ruta de datos. |
| T-109 | todo | P2 | Una sola receta de imagen | infra | `Dockerfile` raíz (compose; `--no-dev`, 1.82 GB, copia `secrets/` sin excluirlo en `.dockerignore`) frente a `deployment/Dockerfile` (`deploy.py`; incluye el grupo dev, 2.13 GB). Además `deploy.py` compila con `docker build` a secas: si el servidor ya tiene la etiqueta base no pide una nueva, y CI puede compilar sobre otra base. |
| T-110 | todo | P2 | "Éxito" ≠ datos escritos: auditar los 109 ETLs | etl | `shoppy_etl.py` está en `ETL_SCRIPTS` (línea 113) sin bloque `__main__`: sale con 0 sin hacer nada cada ciclo; `linkedin_learning_etl.py` no está registrado; `epic_free_games_etl.py` está comentado (línea 75). El orquestador también da por buenos los errores tragados y el circuit breaker abierto. Objetivo: saber qué escribió cada uno en el último ciclo. |
| T-111 | todo | P2 | Watcher de frescura "MUST BE LAST" en el mismo pool | etl | `run_all_etl_orchestrator.py:51` lo marca como último, pero compite con los otros 108 en un pool de 4 workers: puede evaluar la frescura antes de que terminen las fuentes. Ejecutarlo después del pool. |
| T-115 | todo | P2 | CORS: valores por defecto con direcciones de LAN | sec | `src/config/models.py:85` (`APIConfig.cors_origins`), vivo en `src/api/main.py:21`. El repo es público y esas direcciones están en un fichero versionado. Cambiarlo altera lo que acepta prod: pasar los orígenes a `WATCHTOWER_API__CORS_ORIGINS` (ya existe) y dejar solo `localhost` por defecto. |
| T-120 | todo | P2 | Triage de las alerts de Dependabot en `main` | sec | GitHub avisa en cada push de 137 vulnerabilidades en la rama por defecto (8 críticas, 65 altas). Los bumps de T-103 cubren parte; el resto se revisa con el PR #31 mergeado, cuando las alerts se recalculen sobre `main`. |
| T-047 | todo | P3 | Re-evaluate BridgeBench after V3 ships | etl | **Probe 2026-09-11: la nueva versión YA está live** (redirect a www.bridgebench.ai, shell nuevo de 549KB vs 55KB) pero sigue client-rendered: sin `<table>` estático, sin endpoints de API visibles, sin fetch hints, el único window.__ es el beacon de Cloudflare. **La vía viable = browserless** (patrón LiveBench: render + capturar DOM/interceptar XHR). **Desbloqueada 2026-11-24**: browserless vuelve a responder (HTTP 200 en su puerto, comprobado en el server). Implementar: ETL render-vía-browserless + degradación elegante al last-good. |
| T-096 | todo | P3 | Convención de logging única | quality | Split por drift: 112 módulos usan `src.utils.logging.get_logger` vs 77 stdlib `logging.getLogger` (api/services/base.py incluidos). Estandarizar sobre get_logger O santificar stdlib en AGENTS.md y simplificar el wrapper. Churn alto / valor bajo: hacerlo en pasadas pequeñas tocando fichero por otras razones. |
| T-112 | todo | P3 | Orquestador en Windows: el hijo de Python sobrevive al timeout | quality | `run_all_etl_orchestrator.py:190` usa `pkill -9 -P`, que no existe en Windows: en el failover local (`--exclude`, `0edb25e`) los procesos colgados siguen vivos. Rama por plataforma (`psutil` o `taskkill /T`). |
| T-113 | todo | P3 | Minero de Udemy: 4 librerías sin instalar | etl | `src/miners/udemy-universal/` importa `browser_cookie3`, `browserforge`, `keyring` y `rookiepy` en cabecera; ninguna está en el lock, así que esos módulos no importan en ninguna imagen (verificado 2026-11-24 en el contenedor). Además 13 módulos hermanos se importan por nombre simple. Declarar un grupo de dependencias o hacerlos opcionales. |
| T-114 | todo | P3 | Dos planificadores con listas distintas | infra | `src/launcher/main.py` lista 44 scripts frente a los 109 del orquestador; el intervalo de `deployment/etl_scheduler.py` está fijo (`time.sleep(2 * 3600)`, línea 58) y `WATCHTOWER_ETL_INTERVAL` no tiene efecto en el contenedor. Decidir cuál es el camino soportado y borrar o marcar el otro. |
| T-116 | todo | P3 | Hook `pre-push` de ~8 min por push | quality | `pytest-check` corre la suite entera (470 s). Mientras tanto, en un clon nuevo: `git config --local core.sshCommand "ssh -o ServerAliveInterval=30"` o push por HTTPS — GitHub corta la sesión SSH inactiva a los ~362 s y el push falla después de que el hook haya pasado (medido 2026-11-24). Alternativa: hook selectivo por rutas modificadas. |
| T-117 | todo | P3 | Ensayo de despliegue como script del repo | infra | Construir en el servidor el archivo de `deploy.py` con etiqueta `watchtower:candidate` y probar API + ETLs en contenedores desechables destapó el 2026-11-24 tres fallos invisibles para CI (ver T-099). Los scripts viven fuera del repo; traerlos a `deployment/` para repetirlos antes de cada despliegue que toque imagen o dependencias. |
| T-118 | todo | P3 | El archivo de despliegue lleva CRLF | infra | Con `core.autocrlf=true` la copia de trabajo tiene 408 de 560 ficheros de texto en CRLF y `create_archive` los empaqueta tal cual (solo `run_all_etl.sh` pasa por `dos2unix`). Inofensivo para Python, TOML e ini, pero prod no es byte a byte el commit (verificado 2026-11-24 comparando md5). Normalizar al empaquetar. |
| T-119 | todo | P3 | Higiene pendiente del repo | docs | Sin `LICENSE`, `CODE_OF_CONDUCT` ni plantilla de PR (CONTRIBUTING cita un código de conducta); codespell no revisa `docs/`; `src/analytics/` solo lo importan sus tests; `write_json_file` sin usos; `scripts/` guarda scripts que ya no funcionan (`deploy_linux.sh`, `deploy_mac.sh`, `deploy_windows.bat`, `validate_project.py`: piden `requirements.txt`); 3 ramas obsoletas (`chore/agent-workflow-and-task-board`, `fix/audit-quick-wins`, `fix/etl-failures-browserless-and-deprecated-feeds`). La dirección de LAN que tenía T-047 sigue en el historial de git: reescribirlo es decisión del usuario. |
| T-121 | todo | P3 | Paleta de búsqueda en la URL pública | dashboard | `assets/js/command_palette.js` llama a `/api/v1/search` relativo; en la URL pública esa ruta la responde el dashboard con HTML (200), porque la API vive en otro hostname (el del botón "Open API"). Verificado 2026-11-24. Usar el hostname público de la API o enrutar la ruta en el proxy. |
| T-123 | todo | P3 | La capa de Playwright se reconstruye en cada despliegue | infra | En `deployment/Dockerfile`, `RUN uv run playwright install --with-deps chromium` está después de `COPY . .`, así que cualquier cambio de código invalida su caché. En el despliegue del 2026-11-24 las capas base, uv, apt y dependencias salieron de caché y ese paso volvió a bajar Chromium: 182 s de un build de unos 4 min, y cada despliegue depende del CDN de Playwright. Propuesta sin probar: subirlo junto a la capa de dependencias (`uv run --no-sync …` o `.venv/bin/playwright`) para que solo se reconstruya al cambiar `uv.lock`. Ensayar en el servidor al tocar la imagen. |
| T-038 | blocked | P3 | Fix Artificial Analysis ETL (API changed, needs paid key) | etl | Renumbered 2026-08-19 from the original T-026 proposal (ID collided with the spec-rollout rows). The AA v2 API requires an API key (401 without). `ARTIFICIAL_ANALYSIS_API_KEY` env var is supported by the ETL but none is configured; some v2 endpoints also 404'd, suggesting further restructuring. To restore: obtain a key from artificialanalysis.ai, set it in `.env`, verify endpoint paths. Blocked on the user providing a key — and on T-107: a key would not reach the container today. |

## Changelog

- 2026-11-24 — **Puesta al día del repo y despliegue verificado** (PR #31, rama `chore/repo-state-and-workflow`; el merge queda pendiente). Cerrados: **T-098** suite restaurada (`1190 passed, 7 skipped`; roja desde el 10-08), **T-099** despliegue fiable (salud, rollback y tres fallos de imagen que solo aparecían en el servidor), **T-100** CI construye la imagen y comprueba `/health`, **T-101** flujo ZCode (AGENTS.md único, hook de sesión, skills, hooks de git instalados), **T-102** documentación, **T-103** Dependabot (PRs #25–#30 cerrados como absorbidos), **T-104** CRLF, **T-105** despliegue en Unraid verificado (`Successful: 109 \| Failed: 0`). Validadas en prod las tareas que tenían la validación diferida desde el 09-10: T-084, T-085, T-086, T-088, T-091, T-092 y T-095. T-047 y T-048 desbloqueadas. Nuevas abiertas: T-106…T-122 (backups, claves en el contenedor, tests en `data/`, receta de imagen única, ETLs que no escriben, CORS, alerts de Dependabot, paleta pública, higiene). Segundo despliegue de la jornada, desde `99278c4` y entre ciclos (22:44 CET): `changelog.json` ya viaja y el modal 🆕 se comprueba en prod → cerrada **T-122**; abierta **T-123** (la capa de Playwright se reconstruye en cada despliegue). Board: 21 abiertas.

- 2026-11-19 — `a1eefc2` (main): README con despliegue base sin credenciales (`cp .env.example .env`, claves opcionales).

- 2026-10-08 — `77f940c` (main): `goldigging_youtube_posts.py` acota memoria y tiempo (cachés con tope, `socket_timeout`, presupuesto de 45 min) tras el pico de carga del servidor de ese día. El mismo commit arrastró `linkedin_learning_etl.py` y su test sin el modelo que importaban → suite rota hasta el 2026-11-24 (T-098).

- 2026-09-17 — `e6c6adc` (main): `news_get_uneed.py` sobrevive al rediseño del sitio (nombre vía `aria-label` o `title`).

- 2026-09-16 — `5434cf7` (main): OpenAlex deja de honrar el `Retry-After` de 9 h (backoff corto y falla rápido) y no pisa `openalex_latest.json` con una carga vacía.

- 2026-09-15 — `733b0f0` (main): el orquestador mata el proceso hijo de Python al agotar el timeout por script.

- 2026-09-12 — `0edb25e` (main): orquestador con `--exclude` (failover: saltar los ETLs propensos a colgarse).

(Histórico completo en `docs/TASK_BOARD_ARCHIVE.md`.)
