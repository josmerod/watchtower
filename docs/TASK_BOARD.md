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
| T-047 | todo | P3 | Re-evaluate BridgeBench after V3 ships | etl | 2026-08-27: the Elo leaderboard page migrated to client-side rendering (Next.js behind Cloudflare — no `<table>` in HTML, no discoverable API endpoints, only 55KB shell). The ETL keeps last-good data and logs a warning on failure. When "V3 ships soon" lands: re-inspect for a JSON API, or render via the browserless container (BROWSERLESS_ENDPOINT already mounted) if the tab matters enough. |
| T-010 | in-progress | P2 | Reduce `except Exception` overuse (798 occurrences in `src/`) | quality | Broad exception swallowing hides bugs. Audit high-risk call sites (ETL `run()`, API handlers) and narrow to specific exceptions or re-raise. Many are `# noqa: BLE001` in dashboards — leave those, focus on `src/etl` + `src/api`. **Progress 2026-08-10:** narrowed all 16 `except Exception` in `src/api/routers.py` to `(OSError, json.JSONDecodeError, ValueError, TypeError, ValidationError)` — the realistic data-loading failure set; unexpected programming errors now propagate instead of being masked as 500s. API tests green. ETL tier (413 sites, many intentional resilience catches in `BaseETL.run`/retry/circuit-breaker) deferred — narrowing those risks breaking the resilience guarantee and needs per-site judgement; better as dedicated follow-up. |
| T-003 | in-progress | P2 | Work down mypy errors in `src/` (433 across 104 files) | quality | Hotspots: `src/data_quality/deduplication.py`, `src/etl/anime/mal_etl.py`, `src/utils/file_system.py`, `src/utils/logging.py`. Goal: get `uv run mypy src` green so the manual pre-commit hook can be promoted to blocking. **Progress 2026-08-10:** added `[[tool.mypy.overrides]] ignore_missing_imports` for 13 third-party libs lacking stubs (dash_bootstrap_components, feedparser, plotly.*, yt_dlp, psutil, cloudscraper, nltk, pytesseract, sklearn.*) — cleared 109 `[import-untyped]` errors (565→456). Remaining 456 are real per-site type errors (`arg-type` 69, `attr-defined` 68, `assignment` 60) concentrated in spanish_public_aid/arxiv services/deduplication; these need per-site fixes. |
| T-038 | blocked | P3 | Fix Artificial Analysis ETL (API changed, needs paid key) | etl | Renumbered 2026-08-19 from the original T-026 proposal (ID collided with the spec-rollout rows). The AA v2 API requires an API key (401 without). `ARTIFICIAL_ANALYSIS_API_KEY` env var is supported by the ETL but none is configured; some v2 endpoints also 404'd, suggesting further restructuring. To restore: obtain a key from artificialanalysis.ai, set it in `.env`, verify endpoint paths. Blocked on the user providing a key. |
| T-048 | todo | P2 | TR-F2 momentum por tecnología (spec 13) | dashboard | Menciones esta semana vs media móvil 4 semanas → "Subiendo 🔺/Bajando 🔻" bajo el radar plot. **Diferido hasta ~2026-09-16**: los snapshots M5 (kdnuggets + cloud_updates) empezaron el 2026-08-19 y la media de 4 semanas necesita historia. Desbloqueado por T-041/TR-F3 ya mergeado. |
| T-049 | todo | P1 | CI: hacer pytest bloqueante (suite verde) | quality | `ci.yml` mantiene `continue-on-error: true` en el step de tests desde la era T-023 (~145 failures). La suite unit está verde desde 2026-08-19 (260 passed / 5 skipped hoy). Quitar el flag y verificar un run verde en GitHub Actions. Quick win de 15 min que endurece todas las futuras contribuciones. |
| T-050 | todo | P1 | Security intelligence — CISA KEV + BleepingComputer + The Hacker News | etl | Área NUEVA sin cobertura: vulnerabilidades y seguridad ofensiva/defensiva. Fuentes keyless verificables: CISA KEV (`cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`), BleepingComputer RSS, The Hacker News RSS. Valor personal directo: conciencia de exposición del homelab (Unraid + servicios expuestos). ETL + columna Radar o subtab propio. |
| T-051 | todo | P2 | "Mi stack" release radar (spec 13 TR-F4) | dashboard | Atom feeds de releases de GitHub (`github.com/{repo}/releases.atom`) para el stack personal configurado (n8n, Home Assistant, Immich, Jellyfin, ArchiSteamFarm, Tdarr…). Vista "novedades relativas a tu stack" en el Radar. Keyless, patrón multi-feed de selfhosted. Futuro: cruzar con CISA (CVEs que afectan a tu stack). |
| T-052 | todo | P2 | DataFreshnessWatcher → reglas de Notifications | dashboard | Pieza diferida de T-042: los eventos fresh→stale ya se graban; falta crear/actualizar reglas de alerta para que las fuentes stale salgan en el tab Notifications (cierra el loop card→alerta). AlertEngine ya existe en el watcher (importado pero sin usar). |
| T-053 | todo | P2 | ⭐ Guardados en News/Radar/Markets | dashboard | `components/saved_items.py` es genérico pero solo KG lo usa (patrón _SAVE_REGISTRY). Añadir ⭐ a filas de News global, feed Todos del Radar y Markets. Criterio: mismo fichero data/garden/saved_items.json, mismo toggle. |
| T-054 | todo | P2 | Digest semanal | dashboard | ETL local-files (patrón trends_etl) que compila un resumen dominical: top términos 🔥, mejores artículos del radar por menciones, movers de Markets. Nueva vista "📅 Digest" (o subtab Metrics). Convierte el dashboard en revisión semanal de 5 minutos. |
| T-055 | todo | P3 | Retención de snapshots en data/ | infra | 95 ETLs escriben timestamped snapshots cada 2h → crecimiento ilimitado. Script de poda (keep-last-N por prefijo, p.ej. 30) + registro en el watcher/orquestador. Higiene de disco a largo plazo. |
| T-056 | todo | P3 | API pública: /api/v1/markets, /radar, /freshness | api | src/api ya existe (FastAPI 45714). Exponer los datasets nuevos para automatización n8n del usuario (notificaciones externas, webhooks). Solo lectura, sin auth nueva (red local). |
| T-057 | todo | P3 | Búsqueda global unificada cross-tab | dashboard | News y KG tienen búsquedas globales separadas. Unificar en un índice único (título+resumen+fuente) consultable desde la palette Ctrl+K o un subtab global. Medio esfuerzo; valor discoverability. |
| T-058 | todo | P3 | Investigar: enriquecer HF Trending con citas CrossRef | etl | CrossRef REST es keyless: contar citas de los papers HF Trending por DOI → columna "citas" en el subtab 🔥. Solo si el tab demuestra uso. Alternativa bio: bioRxiv/medRxiv RSS si el usuario quiere ángulo bio. |

## Changelog

(Histórico completo en `docs/TASK_BOARD_ARCHIVE.md`.)

- 2026-08-27 — Compactación del board: 33 filas done movidas íntegras a `docs/TASK_BOARD_ARCHIVE.md`; este fichero queda solo con tareas abiertas. Cerrado T-041 (TR-F3 feed unificado validado en prod: 426 artículos, filtros fuente/categoría OK). Añadidas del brainstorm: T-048 (momentum, diferido a ~09-16), T-049 (CI bloqueante), T-050 (security keyless), T-051 (mi stack), T-052 (watcher→alerts), T-053 (guardados multi-tab), T-054 (digest), T-055 (retención), T-056 (API pública), T-057 (búsqueda global), T-058 (CrossRef, investigar).
