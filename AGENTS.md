# AGENTS.md — Watchtower (MEGALITH)

Workspace instructions for ZCode agents working in this repository. They apply
in addition to the user-scope instructions in `~/.zcode/AGENTS.md`; where they
conflict, this file wins for this project. It is the single source of truth for
conventions here: `CLAUDE.md`, `GEMINI.md` and `.cursorrules` only point back.

Watchtower is a data-intelligence platform in three layers — **ETL → Watchers
→ Dashboard** — plus a FastAPI. Python 3.10+ (3.11 in CI and production),
managed with **uv**. Data is JSON under `data/`, which is gitignored.

**The repository is public.** Never write a LAN address, a private hostname or
a credential into a tracked file, a commit message, a PR or an issue; use a
placeholder such as `<host>`.

## Start of session

A SessionStart hook (`.zcode/hooks/session_context.py`, wired in
`.zcode/config.json`) injects a `<repo-state>` digest: branch and distance to
`origin/main`, whether the git hooks are installed, the task marked
`in-progress` on the board, and entries of `docs/FEEDBACK.md` not triaged yet.
Act on it:

1. Hooks missing: run
   `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`.
   A fresh clone has none, and then nothing gates a commit or a push.
2. Read `docs/TASK_BOARD.md` before planning work. One task is `in-progress`
   at a time. Triage untriaged feedback into the board.

To see the digest mid-session:
`uv run --no-project python .zcode/hooks/session_context.py .`

## Tooling & commands

ALWAYS run Python through **uv** so the locked environment is used.

| Task | Command |
| :--- | :--- |
| Install | `uv sync` (includes the `dev` group) |
| Run a script | `uv run python <script>` |
| Dashboard (Dash, port **7780**) | `uv run python run_watchtower_dashboard.py` |
| API (FastAPI, port **45714**) | `uv run uvicorn src.api.main:app --port 45714` |
| All ETLs | `./run_all_etl.sh` → `run_all_etl_orchestrator.py --workers 4` |
| Tests | `uv run pytest` |
| Coverage | `uv run pytest --cov=src --cov-report=html` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Type check (advisory) | `uv run mypy src` |
| All hooks | `uv run pre-commit run --all-files` |
| Deploy (Unraid) | `uv run --with paramiko python deployment/deploy.py` |

## Code style

- **Ruff** is the only linter and formatter (`[tool.ruff]` in `pyproject.toml`):
  line length **210**, double quotes, 4-space indent. `Tests/` is excluded from
  ruff. Do not reintroduce black or flake8.
- Docstrings are Google-style by convention; the `D` rules are not enabled yet.
- Type hints for **Python 3.10+**, modern syntax (`list[...]`, `X | None`).
- Resolve paths with `src.utils.file_system.get_project_root()` — never hardcode
  absolute paths.
- Dependencies: runtime in `[project.dependencies]`, dev tools in
  `[dependency-groups].dev`; then `uv lock` and `uv sync`.
- A new data source needs **no API key** unless the user opts in. RSS feeds and
  public endpoints first.

## Architecture

Counts were measured on 2026-11-28; re-check before quoting them.

- **ETL** (`src/etl/`, 23 subpackages, 139 modules). Two styles coexist:
  - **`BaseETL[I, O]`** (`src/etl/base.py`, 28 of the 100 ETL scripts). The
    constructor requires `name`; implement `extract()`, `transform()` and
    `load()`. `run()` adds retries, checkpointing, deduplication, a circuit
    breaker and run summaries under `data/<name>/output/`. An open circuit
    breaker skips the run silently (exit code 0); any other failure raises
    `ETLError`.
  - **Plain module with `main()`** (the other 72 ETL scripts, the majority).
    Fetch, transform, write JSON, with the path helpers in
    `src/utils/file_system.py`. Example: `src/etl/news/news_get_changelog.py`.
  - Both styles run in production only when listed in `ETL_SCRIPTS` in
    `run_all_etl_orchestrator.py` (103 entries: 100 ETLs, 2 watchers and
    1 miner; 4 workers). The data-freshness watcher runs on its own after
    the pool, so a cycle is 104 scripts.
- **Data models** (`src/models/`, 19 modules): Pydantic, built on the bases
  `TimestampedModel`, `StatusModel`, `ErrorModel`, `PaginatedResponse`.
  `BaseETL.validate_data()` validates against them, but nothing forces it:
  using the models is a convention, so keep to it.
- **Watchers** (`src/watchers/`, 4 subclasses of `BaseWatcher`): implement
  `extract_value()` and `has_changed()`; state lives in
  `data/watchers/<name>/`.
- **Dashboard** (`src/web/dashboard/`): Dash + Bootstrap, 19 registered tabs
  (20 tab modules) in `components/`. **Use the Single Callback Pattern** — one
  callback per output component, `prevent_initial_call=True` — to avoid
  callback conflicts.
  Components must look premium and stay minimalist and responsive. Seven tabs
  load their data through `BaseRepository` subclasses (`src/repositories/`,
  documented in `docs/REPOSITORY_PATTERN.md`).
- **API** (`src/api/`): FastAPI, 20 GET endpoints: 19 under `/api/v1` and
  `/health`.
- **Config**: `src/config/settings.py`, Pydantic Settings, env-driven as
  `WATCHTOWER_<COMPONENT>__<SETTING>`. Get it via the `@lru_cache`d
  `get_settings()`.

## Data storage layout

`data/` is gitignored, historical and **never clobbered or committed**. There
is no single layout: most scripts write one file per source, `BaseETL` runs
add per-run output.

```
data/
├── <domain>/<name>.json     # e.g. data/changelog/changelog_news.json
├── <domain>/<name>_latest.json
├── <etl_name>/output/       # BaseETL runs: run_summary_{timestamp}.json, run_summary_latest.json
├── watchers/<watcher_name>/
│   ├── state.json
│   └── events/{timestamp}_{event_type}.json
└── metrics/etl_runs_latest.json
```

Follow the sibling scripts of the subpackage you are editing. The dashboard
and the API load data **by exact path**, so a new output is invisible until a
consumer reads it: `NEWS_SOURCES_CONFIG` in `src/services/data_loader.py`,
the tab's source list, and `SOURCE_FILES` in
`src/watchers/data_freshness_watcher.py`.

## New ETL

1. Read a sibling in the target subpackage and copy its style, output path and
   file name.
2. `BaseETL` style needs `name` in the constructor and an entry point:

   ```python
   from typing import Any

   from src.etl.base import BaseETL


   class MyCustomETL(BaseETL[dict[str, Any], dict[str, Any]]):
       """One-line summary of what the pipeline extracts and where it loads."""

       def extract(self) -> list[dict[str, Any]]:
           """Fetch raw records from the source."""
           ...

       def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
           """Normalize raw records into dictionaries shaped like the model."""
           ...

       def load(self, data: list[dict[str, Any]]) -> None:
           """Persist to the path the consumer reads."""
           ...


   if __name__ == "__main__":
       MyCustomETL(name="my_custom_etl").run()
   ```

3. Add the script to `ETL_SCRIPTS` in `run_all_etl_orchestrator.py`. An
   unlisted script never runs in production and its data goes stale.
4. Wire a consumer (see "Data storage layout") and the freshness watcher, in
   the same change as step 3: a registered script whose output nothing reads
   is an invisible source (`linkedin_learning_etl.py` stays unlisted for that
   reason).
5. Add a test under `Tests/etl/`.

The `etl-pipeline` skill has the full procedure.

## New dashboard tab

A tab is a module in `src/web/dashboard/components/` with a `render_<x>_tab()`
layout function and a `register_<x>_callbacks(app)` function:

```python
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html


def render_my_tab():
    """Return the Dash layout for this tab."""
    return dbc.Container(
        [
            html.H3("My Tab"),
            dcc.Input(id="my-input", placeholder="Filter...", debounce=True),
            html.Div(id="my-content"),
        ]
    )


def register_my_callbacks(app: Dash):
    """Register this tab's callbacks on the Dash app."""

    @app.callback(
        Output("my-content", "children"),
        Input("my-input", "value"),
        prevent_initial_call=True,
    )
    def update_content(value: str | None) -> str:
        """Show what the user typed."""
        return f"Updated: {value or ''}"
```

Wiring it takes four more edits, all in `src/web/dashboard/app.py` except the
last:

1. A `dbc.Tab(label=..., tab_id="tab-my-tab")` in the nav `dbc.Tabs`.
2. The same id in `_TAB_RENDERERS` (tabs are rendered lazily from it).
3. A `register_my_callbacks(app)` call next to the other registrations.
4. A row in `RENDERERS` in `Tests/unit/test_tab_render.py`.

Read data with `get_data_path(...)` from `src/web/dashboard/utils.py`. The
`dashboard-tab` skill has the full procedure.

## Testing

- Tests live in `Tests/` (`test_*.py` / `*_test.py`), grouped by area
  (`unit/`, `etl/`, `api/`, `dashboard/`, `e2e/`, ...). `--strict-markers` is
  on and only `e2e` and `slow` are registered.
- Unit tests never hit real external services: fixtures and stubs only.
- Two guards fail when a shared list gets out of date:
  `Tests/unit/test_tab_render.py` (tab renderers) and
  `Tests/unit/test_deploy.py` (what the container ships).

## Commit & workflow

- Branch off `main` before committing; commit and push only when asked.
- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`,
  `refactor:`, `ci:`), subject ≤50 chars, imperative; small, focused commits;
  branches `feat/`, `fix/`, `chore/`, `docs/` + kebab-case.
- pre-commit (`.pre-commit-config.yaml`) runs on every commit: Ruff, codespell,
  detect-secrets, shellcheck and file hygiene hooks. The pre-push hook runs the
  full pytest suite (about 8 minutes) when the push touches code — `src/`,
  `Tests/`, `deployment/`, the root scripts, `pyproject.toml`, `uv.lock` or
  the root `Dockerfile`; a docs-only push skips it. Over SSH, GitHub can close
  the idle session before the hook ends, and the push then fails after a green
  run: set it once per clone with
  `git config --local core.sshCommand "ssh -o ServerAliveInterval=30"`, or
  push over HTTPS. Never bypass the hook.
- mypy is a manual stage (`uv run pre-commit run --hook-stage manual mypy`)
  and does not block commits, but `uv run mypy src` is clean today. Keep it
  clean.
- Never commit secrets. `.secrets.baseline` is the detect-secrets allowlist;
  real credentials come from env vars or `.env` (gitignored).

## Working with this repo (agent good practices)

Non-obvious rules that keep work correct and reviewable:

- **Verify before claiming done.** Run the actual commands and paste the
  output — never assert success without evidence. Before handing over:
  `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` and
  `uv run pre-commit run --all-files`. If a step was skipped, say so. See
  `superpowers:verification-before-completion`.
- **Never `cat .env`.** It holds live credentials. List key names with
  `grep -oE '^[A-Z_][A-Z0-9_]*=' .env`.
- **Agents working in parallel** get disjoint file scopes. Never `git stash`,
  `git restore`, `git checkout` or `git reset` outside your own files: another
  agent's uncommitted work lives in the same tree.
- **Worktrees** have no `.venv` (the first `uv run` syncs one) and no `.env`.
  If `git status` shows many modified files right after a checkout, check
  `git diff --ignore-cr-at-eol --stat` before believing it.
- **Task tracking:** `docs/TASK_BOARD.md` holds open work, one task
  `in-progress` at a time; `docs/TASK_BOARD_ARCHIVE.md` the closed tasks;
  `docs/ROADMAP.md` the horizons; `docs/FEEDBACK.md` the feedback notebook.
  Use the `task-board` skill and record work there as you go.

## Signals in the user's prompts

Phrases the user uses to raise or lower the bar:

- "I'll tip you…", "bet you can't…": maximum depth, and prove that it works.
- "Take a deep breath…": work through the problem step by step before coding.
- "Important to my career…": safety first. Check for destructive side effects
  and warn about risks before acting.
- "Rate your confidence…": answer with a probability. Below 0.9, list the
  risks and the alternatives.

## Deploys

- `uv run --with paramiko python deployment/deploy.py` ships to the Unraid
  server. The `unraid-deploy` skill has the procedure and the recovery steps.
- The deploy packs the **working tree**, uncommitted changes included. Deploy
  from a clean tree on the branch you mean. Text files are normalized to LF
  as the archive is packed, so the bytes on the server match the commit even
  on a checkout with `core.autocrlf=true`.
- `deploy.py` uploads an archive of `INCLUDE_PATHS`, builds
  `deployment/Dockerfile` on the server, swaps the container and waits for its
  health check. On failure it rolls back to the image tagged
  `watchtower:previous` and exits non-zero. A script the container must run,
  or a repo-root file the code reads by name (`changelog.json`), belongs in
  `INCLUDE_PATHS`; `Tests/unit/test_deploy.py` enforces it.
- API keys reach the container only through the allowlist `CONTAINER_ENV_KEYS`
  in `deploy.py`. The names on it that are set in `.env` (or the shell) are
  written to an owner-only file on the server and passed with
  `docker run --env-file`; nothing else travels, and `UNRAID_*` is not on the
  list. A new key needs its name there and in `.env.example`, and
  `Tests/unit/test_deploy.py` fails on a variable the ETLs read that is not
  forwarded.
- When `deployment/Dockerfile`, `pyproject.toml` or `uv.lock` change, rehearse
  first: build the archive on the server under a throwaway tag and boot a
  disposable container. CI builds the same image on its own runner and boots
  only the API; three image defects showed up only on the server.
- Every deploy or container restart starts a **full ETL cycle** (104 scripts,
  4 workers) before the scheduler settles into its 2-hour rhythm. Do not
  restart casually, and deploy between cycles: one takes about 47 minutes and
  the next starts 2 hours after it ends.
- Exit 0 means the API answered `/health`. The health gate never opens the
  dashboard, and the public dashboard hostname answers every path —
  `/api/v1/*` included — with dashboard HTML and status 200. Read the API
  against the container or its own hostname, and check a deployed feature in
  the browser before calling it done.
- Production `data/` lives in a Docker volume; a deploy never touches it.
  After each cycle `run_backup.py` makes a verified archive of `data/` and
  `logs/` — at most one a day — in the `backups` volume next to it, and
  keeps 7. Same disk as the data: there is no off-site copy. The
  `unraid-deploy` skill says how to check it and how to restore.

## Skills and reference docs

- Skills in `.agents/skills/`: `etl-pipeline`, `dashboard-tab`,
  `unraid-deploy`, `task-board`. Invoke the one that matches the task.
- Agents in `.zcode/agents/`: `watchtower-dev` (ETLs, repositories,
  dashboard tabs), `watchtower-deployer` (production, the only role that
  touches it) and `watchtower-board` (the task documents). Each loads its
  skill before planning. A skill's `scripts/` hold the helpers its text
  runs by path; its `references/`, the long form of a topic.
- `CODEBASE_SUMMARY.md` — map of the codebase as it is today.
- `README.md`, `docs/QUICKSTART.md`, `docs/CONTRIBUTING.md`, `docs/INDEX.md`.
- `docs/archive/` — historical material kept for reference, not maintained.
  Do not follow it over this file.
