# AGENTS.md — Watchtower (MEGALITH)

Workspace instructions for ZCode agents working in this repository. These rules
apply in addition to the user-scope instructions in `~/.zcode/AGENTS.md`; where
they conflict, this file wins for this project.

Watchtower is a 3-layer data intelligence platform: **ETL → Watchers → Dashboard**.
Python 3.10+, managed with **UV**. Data is persisted as timestamped JSON under
`data/` (which is gitignored).

## Tooling & commands

ALWAYS run Python through **UV** so the locked environment is used.

| Task | Command |
| :--- | :--- |
| Run a script | `uv run python <script>` |
| Dashboard (primary, Dash, port **7780**) | `uv run python run_watchtower_dashboard.py` |
| All ETLs | `./run_all_etl.sh` (Unix) — orchestrates `run_all_etl_orchestrator.py` |
| Tests | `uv run pytest` |
| Coverage | `uv run pytest --cov=src --cov-report=html` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Type check | `uv run mypy src` |
| Deploy (Unraid) | `uv run --with paramiko deployment/deploy.py` |

## Code style

- **Ruff** is the source of truth for lint + format. Line length **210**, double
  quotes, 4-space indent, **Google-style docstrings** (`[tool.ruff.lint.pydocstyle]`).
- Strict **Python 3.10+** type hints. Prefer modern syntax (`list[...]`, `X | None`).
- Resolve paths with `src.utils.file_system.get_project_root()` — never hardcode
  absolute paths.
- New dependencies go in `pyproject.toml` under the right section, then
  `uv lock` + `uv sync`.

## Architecture patterns

- **ETL** (`src/etl/`): Template Method via `BaseETL` in `src/etl/base.py`. Every
  pipeline subclasses `BaseETL[I, O]` and implements `extract()`, `transform()`,
  `load()`. Reuse the built-in resilience: circuit breaker
  (`circuit_breaker.py`), proxy rotation (`proxy_manager.py`), checkpointing,
  retry. 22+ domain subpackages (arxiv, news, games, intelligence, etc.).
- **Data models** (`src/models/`, 38 files): Pydantic. Build on the bases
  `TimestampedModel`, `StatusModel`, `ErrorModel`, `PaginatedResponse`.
  Pydantic is strictly enforced for extraction/transformation output.
- **Watchers** (`src/watchers/`): subclass `BaseWatcher`; persist JSON state under
  `data/watchers/<name>/` and events under `data/watchers/<name>/events/`.
- **Dashboard** (`src/web/dashboard/`): Dash + Bootstrap, ~25 tabs in
  `components/`. Each tab renders a layout and registers its own callbacks.
  **Use the Single Callback Pattern** — one callback per output component,
  `prevent_initial_call=True`, to avoid callback conflicts. Components must look
  premium and stay minimalist/responsive. Streamlit (`src/web/fullstreamlit/`) is
  legacy; do not extend it.
- **Config**: `src/config/settings.py`, Pydantic Settings, env-driven
  (`COMPONENT__SETTING` nested form). Get it via the `@lru_cache`d `get_settings()`.

## Data storage layout

```
data/
├── {component}/output/
│   ├── {component}_{timestamp}.json
│   ├── {component}_latest.json
│   └── run_summary_latest.json
├── watchers/{watcher_name}/
│   ├── state.json
│   └── events/{timestamp}_{event_type}.json
└── metrics/etl_runs_latest.json
```

`data/` is gitignored — do not commit scraped data, logs, or caches.

## New ETL recipe

```python
from typing import Any

from src.etl.base import BaseETL


class MyCustomETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """One-line summary.

    Longer description of what the pipeline extracts and where it loads.
    """

    def extract(self) -> list[dict[str, Any]]:
        """Fetch raw records from the source."""
        ...

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize/classify raw records into Pydantic-validated output."""
        ...

    def load(self, data: list[dict[str, Any]]) -> None:
        """Persist to timestamped + latest JSON under data/{component}/output/."""
        ...
```

## New dashboard tab recipe

```python
import dash_bootstrap_components as dbc
from dash import Input, Output, html


def render_my_tab():
    """Return the Dash layout for this tab."""
    return dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    [
                        html.H3("My Tab"),
                        html.Div(id="my-content"),
                    ]
                )
            )
        ]
    )


def register_my_callbacks(app):
    """Register this tab's callbacks on the Dash app."""

    @app.callback(
        Output("my-content", "children"),
        Input("my-input", "value"),
        prevent_initial_call=True,
    )
    def update_content(value):
        try:
            return f"Updated: {value}"
        except Exception as e:  # noqa: BLE001 - surface errors in the UI
            return f"Error: {e}"
```

## Testing

- Tests live in `Tests/` (`test_*.py` / `*_test.py`), configured via
  `[tool.pytest.ini_options]`. Mark slow/E2E tests with `@pytest.mark.slow` /
  `@pytest.mark.e2e`.
- Don't hit real external services in unit tests — fixtures/stubs only. Live
  network belongs behind an explicit integration marker.

## Commit & workflow

- Branch off `main` before committing; only commit/push when asked.
- Keep commits focused. The repo uses pre-commit (`.pre-commit-config.yaml`) with
  Ruff, mypy, codespell, detect-secrets, and shellcheck — run
  `uv run pre-commit run --all-files` before finalizing a change.
- Never commit secrets. `.secrets.baseline` is the detect-secrets allowlist; real
  credentials must come from env vars / `.env` (gitignored).

## Reference docs in-repo

- `README.md` — overview, install, deployment.
- `CODEBASE_SUMMARY.md` — architectural deep-dive.
- `CLAUDE.md` / `GEMINI.md` — AI-assistant guidance (same conventions as here).
