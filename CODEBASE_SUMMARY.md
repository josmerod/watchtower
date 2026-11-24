# Watchtower (MEGALITH) — Codebase Map

Snapshot of the repository on 2026-11-24. It maps what exists today: where each layer lives, how it is started, tested and deployed, and which conventions the code follows. `AGENTS.md` is the source of truth for commands and conventions.

## What the platform is

Watchtower collects data from public web sources, normalizes it into JSON files under `data/`, and serves those files through a dashboard and a read-only HTTP API. Python 3.10 or later is required, the containers run Python 3.11, and dependencies are managed with `uv`.

| Layer | Package | Role |
| :-- | :-- | :-- |
| ETL | `src/etl/` | Scrapes or downloads a source, validates and deduplicates, writes JSON |
| Watchers | `src/watchers/` | Polls a page, keeps the last seen value, records an event when it changes |
| Dashboard | `src/web/dashboard/` | Dash application with one component per tab |
| API | `src/api/` | FastAPI service that reads the same JSON files |

## Source map

| Path | Contents |
| :-- | :-- |
| `src/etl/` | 23 domain packages; 105 of their scripts are in the ETL cycle. Shared modules: `base.py` (`BaseETL`), `circuit_breaker.py`, `proxy_manager.py` |
| `src/models/` | 19 Pydantic modules; the bases (`TimestampedModel`, `StatusModel`, `ErrorModel`, `PaginatedResponse`) are in `base.py` |
| `src/watchers/` | `base_watcher.py` (`BaseWatcher`), four watchers, the `run_watcher.py` runner |
| `src/web/dashboard/` | `app.py` (layout and tab registry), `components/` (19 tab modules and shared helpers), `assets/` (CSS and JS) |
| `src/api/` | `main.py` (app, CORS, health), `routers.py`, `public.py`, `search.py`, `models.py`, `export_openapi.py` |
| `src/config/` | `settings.py` (`Settings`, `get_settings()`), `models.py` (per-component config classes) |
| `src/repositories/` | Cached file access for six dashboard components; see `docs/REPOSITORY_PATTERN.md` |
| `src/services/` | `data_loader.py` (reads for the dashboard and the API), `content_search.py`, `watcher_events.py` |
| `src/alerts/` | `rules_store.py`, used by the notifications tab, three ETLs and the freshness watcher |
| `src/intelligence/` | LLM client and `enrichment.py`, used by `BaseETL` when `enable_enrichment` is on |
| `src/data_quality/` | `deduplication.py` (`DeduplicationEngine`), used by `BaseETL` |
| `src/exceptions/` | `WatchtowerError` and the ETL, scraping and watcher errors |
| `src/utils/` | `file_system.py` (`get_project_root()`), logging, retry, snapshot retention, backup helpers |
| `src/constants/` | `etl.py`, constants shared by many ETLs |
| `src/miners/` | `crypto_sentiment_miner.py` (in the ETL cycle) and the `udemy-universal/` subproject, which ruff and mypy skip |
| `src/launcher/` | Separate launcher, used only by `Dockerfile.dev` and the files in `services/` |
| `src/analytics/` | Trends and models; nothing else under `src/` imports it |

## Entry points

| Command | What it does |
| :-- | :-- |
| `uv run python run_watchtower_dashboard.py` | Starts the dashboard on port 7780. The port comes from `WATCHTOWER_DASHBOARD_PORT`; there are no command-line flags |
| `uv run uvicorn src.api.main:app --port 45714` | Starts the API: 20 GET routes, 19 under `/api/v1` plus `/health` |
| `./run_all_etl.sh` | Runs `run_all_etl_orchestrator.py --workers 4` |
| `uv run python src/watchers/run_watcher.py` | Watcher runner (`--list`, `--once`); today it can only launch `ms_applied_skills` |
| `uv run --with paramiko python deployment/deploy.py` | Deploys to the Unraid server |

The orchestrator runs the 109 entries of `ETL_SCRIPTS` (105 ETLs, 3 watchers, 1 miner), each as `uv run python <script>` in a pool of 4 workers, with one log per script under `logs/`. After the pool it runs `src/utils/snapshot_retention.py` and, when the file exists, `run_backup.py`.

## Contracts to build on

- **ETL**: subclass `BaseETL[I, O]` and implement `extract()`, `transform()` and `load()`. `run()` is the template method and returns `ETLMetrics`. The base class brings the circuit breaker, proxy rotation, tenacity retries, checkpointing, deduplication and optional LLM enrichment. 31 of the 105 ETL scripts use it (29 directly, 2 through `SimpleETL`); the other 74 are plain scripts.
- **Watcher**: subclass `BaseWatcher` and implement `extract_value(html_content)` and `has_changed(old_value, new_value)`. State is written to `data/watchers/<name>/state.json` and events to `data/watchers/<name>/events/`. `MSAppliedSkillsWatcher`, `CoursesWatcher` and `DataFreshnessWatcher` are entries of the ETL cycle, and `ArxivWatcher` is a component of the ArXiv ETL.
- **Dashboard tab**: one module under `components/` exposing a `render_*_tab()` function, registered in `_TAB_RENDERERS` in `app.py`; only the active tab is rendered. Callbacks follow the Single Callback Pattern: one callback per output component, with `prevent_initial_call=True`. 18 tabs are registered. `shortcuts_tab.py` is the 19th module; its tab is hidden, but `app.py` still calls `register_shortcuts_callbacks`.
- **API**: three routers (`router`, `public_router`, `search_router`) mounted under `/api/v1`. GET only, with Pydantic response models.
- **Settings**: `get_settings()` returns a cached pydantic-settings `Settings` that reads `.env` and `.env.local`. Nested variables are written `WATCHTOWER_<COMPONENT>__<SETTING>`.
- **Output**: ETLs write `data/<component>/`; `BaseETL` also updates `data/metrics/etl_runs_latest.json`. `data/` is gitignored.

## Testing

- 82 test files under `Tests/`, 49 of them in `Tests/unit/`. The rest sit beside it, grouped by layer (`etl`, `api`, `dashboard`, `models`, `alerts`, `analytics`, `data_quality`, `web`) and by kind (`e2e`, `integration`, `performance`), plus one file at the root of `Tests/`.
- `uv run pytest` runs everything; `uv run pytest --cov=src --cov-report=html` adds coverage.
- The only registered markers are `e2e` and `slow`, and `--strict-markers` is on, so any other marker fails.
- Unit tests must not call real services: use fixtures and stubs.

## Deployment

- **Production (Unraid)**: `deployment/deploy.py` archives the paths in its `INCLUDE_PATHS` (`src`, `deployment`, `config`, `Tests` and the project files), uploads the archive over SSH, builds `deployment/Dockerfile` on the server and replaces the container. If the new container does not pass its health check, the previous image is restored. `.env` and `secrets/` are not part of the archive.
- **Inside the container**: `deployment/supervisord.conf` runs three programs: `dashboard`, `api` and `etl_scheduler`. The scheduler runs the whole ETL cycle when it starts and then every 2 hours, and restarts the API after each cycle. The host publishes the dashboard on 7777 and the API on 45714; only the `data` and `logs` volumes are mounted.
- **Local Docker**: the root `Dockerfile` and `docker-compose.yml` start the same supervisor configuration, but this image copies `./secrets/` and compose also mounts `./secrets` read-only.
- **CI**: on every push to `main` and on pull requests, the `CI` workflow runs `uv sync`, `ruff check`, `ruff format --check`, a bytecode compile of the shipped code and `uv run pytest Tests/`. The `Docker Build` workflow builds the image from the deploy archive and checks `/health`.

## Conventions

- **Ruff only**: `uv run ruff check .` and `uv run ruff format .`. Line length 210, double quotes, rules `E`, `F`, `W`, `I`, `UP`, `C4`, `B`, `RUF` and `SIM`. `Tests/` and `src/miners/udemy-universal` are excluded. Docstrings follow the Google convention, but the `D` rules are not enabled.
- **mypy is advisory**: `uv run mypy src` runs on the `manual` pre-commit stage and does not block commits.
- **Pre-commit is mandatory**: `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`. The commit stage runs the basic `pre-commit-hooks`, ruff, codespell, shellcheck and detect-secrets; the push stage runs the tests.
- **Pydantic models** for everything an ETL or the API outputs.
- **Paths**: resolve them with `get_project_root()`; no absolute paths.
- **License**: `pyproject.toml` declares MIT. The repository has no `LICENSE` file.

## Deliberately gone

These were removed on purpose and are not in the code: the ETL factory, the dependency-injection container, the scraping strategies and the alert engine (September 2026 cleanup), and the Streamlit dashboard (removed earlier). The design notes for the first three are in `docs/archive/` with an "Archived" first line: `ETL_FACTORY_PATTERN.md`, `DEPENDENCY_INJECTION.md` and `SCRAPING_STRATEGY_PATTERN.md`. `src/alerts/rules_store.py` is the only part left of the alerts package.
