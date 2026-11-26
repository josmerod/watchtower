---
name: dashboard-tab
description: Build a new Watchtower dashboard tab the standard way, or wire an existing one so it actually appears in the app. Use whenever the user wants to add a dashboard tab/page/section, surface ETL data in the UI, add a new view, build a component, or when a tab exists but isn't showing up. Trigger on "add a tab", "new dashboard page", "show X in the dashboard", "add a view", "surface the data", "the tab isn't appearing", "register a component".
---

# Dashboard Tab

The dashboard is Dash + Bootstrap in `src/web/dashboard/`: 19 `*_tab.py`
modules under `components/`, 18 of them shown as top-level tabs. A component
file alone renders nothing — it has to be wired in `app.py` and covered by the
render test.

## Wiring a new tab

1. **Component**: `src/web/dashboard/components/<name>_tab.py`, exporting
   `render_<name>_tab()` and, when interactive, `register_<name>_callbacks(app)`.
2. **Nav**: `dbc.Tab(label=..., tab_id="tab-<id>")` inside the
   `dbc.Tabs(id="dashboard-tabs")` block of `src/web/dashboard/app.py`. Shells
   carry only `label` and `tab_id` — no `children`.
3. **Renderer**: `"tab-<id>": render_<name>_tab` in `_TAB_RENDERERS` in `app.py`.
4. **Callbacks**: `register_<name>_callbacks(app)` at the bottom of `app.py`,
   with the other `register_*` calls. Names are not always mechanical
   (`videos_tab.py` exports `register_video_callbacks`); static tabs such as
   `games_tab.py` have none.
5. **Test**: a row in `RENDERERS` in `Tests/unit/test_tab_render.py` —
   `("<name>_tab", "render_<name>_tab", ["<an id the layout must contain>"])`.

## Every tab is lazy

`render_active_tab` in `app.py` — `Output("tab-content", "children")` from
`Input("dashboard-tabs", "active_tab")` — looks the active id up in
`_TAB_RENDERERS` and calls that renderer when the tab is selected, and once at
load for the default `tab-news`.

- `render_<name>_tab()` must return the default view — do not rely on
  load-time callbacks to finish drawing it. It runs on every switch, so read
  data inside it (cached, e.g. with `TTLDataCache`), not at import time.
- The two ids must match. A nav tab missing from `_TAB_RENDERERS` silently
  shows the News tab; a renderer without a nav shell is unreachable.

## The component

Mirror `deals_tab.py` (searchable table with callbacks) or `games_tab.py`
(static), and reuse the shared helpers listed below:

```python
"""My tab — one-line purpose."""

import logging
from typing import Any

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, html

from src.services.data_loader import load_data_from_file
from src.web.dashboard.components.shared.table import render_items_table, title_cell
from src.web.dashboard.search_utils import create_search_input, filter_content
from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)

DATA_FILE = get_data_path("my_domain", "my_source_latest.json")


def _table(items: list[dict[str, Any]], term: str = "") -> Any:
    """Build the table; render_items_table returns an alert when there are no items."""
    columns = [{"header": "Title", "cell": lambda item: title_cell(item, term)}]
    return render_items_table(items, columns, empty_message="No data yet.")


def render_my_tab() -> dbc.Container:
    """Return the full default view; called every time the tab is selected."""
    return dbc.Container(
        [
            html.H3("My Tab", className="mb-3"),
            create_search_input(input_id="mytab-search", placeholder="Filter...", clear_button=False),
            html.Div(_table(load_data_from_file(DATA_FILE)), id="mytab-results"),
        ],
        fluid=True,
    )


def register_my_callbacks(app: Dash) -> None:
    """Wire this tab's callbacks: one callback per Output id."""

    @app.callback(
        Output("mytab-results", "children"),
        Input("mytab-search", "value"),
        prevent_initial_call=True,
    )
    def update_results(search_term: str | None) -> Any:
        """Rebuild the table for the search term."""
        try:
            term = search_term or ""
            items = filter_content(term, load_data_from_file(DATA_FILE), ["title"])
            return html.Div(_table(items, term))
        except Exception as exc:  # show the failure in the tab instead of breaking the app
            logger.exception("My tab search failed")
            return dbc.Alert(f"Error loading My Tab: {exc}", color="danger")
```

Rules that bite:

- **Single Callback Pattern**: one callback per `Output` id. Two callbacks
  writing the same output are rejected by dash-renderer — "Duplicate callback
  outputs" in the **browser** console, not a Python exception at startup. A
  second writer must opt in with `allow_duplicate=True` and
  `prevent_initial_call=True` (12 callbacks do).
- **`suppress_callback_exceptions=True`** in `app.py`, because the layout is
  dynamic — so Dash does not check ids either: a typo in an `Input`/`Output`
  id is silent.
- **`prevent_initial_call=True`** on callbacks that react to input — the
  convention in AGENTS.md, not universal in the code — since the renderer
  already drew the default view. Leave it off only where a callback must fill
  an empty container on load (`courses_tab.py`, `notifications_tab.py`,
  `videos_tab.py`).
- **IDs are global**: prefix every id with the tab slug —
  `pagination_controls(tab_slug, ...)` and `create_refresh_button(tab_slug)`
  already do.
- **Premium, minimalist UI**: Bootstrap components, responsive rows/cols, the
  shared styles in `src/web/dashboard/assets/`.

## Reading data

Tabs read JSON files under `data/` through `get_data_path` in
`src/web/dashboard/utils.py`; no tab calls the API over HTTP and no callback
scrapes (`etl-pipeline` skill). `src/services/data_loader.py` builds on it:
its `*_SOURCES_CONFIG` dicts map a source key to `{"path", "name"}`, and
`load_data_from_file(path)` returns a list of dicts — `[]` when the file is
missing or broken. A few tabs (`benchmarks_tab.py`, `security_tab.py`,
`markets_tab.py`, `digest_tab.py`, `tech_radar_tab.py`) join a project root
and `"data"` by hand instead.

## Shared helpers — reuse them

| Need | Use |
| :--- | :--- |
| Table | `render_items_table(items, columns, empty_message=..., wrap_scroll=...)`, `title_cell`, `text_cell`, `badges_cell` — `src/web/dashboard/components/shared/table.py` |
| Paging, refresh | `paginate`, `pagination_controls`, `create_refresh_button` — same file |
| Short cache | `TTLDataCache(ttl_seconds=...).get(loader)` — `src/web/dashboard/components/shared/cache.py` |
| Source freshness | `source_health_dots` — `src/web/dashboard/components/shared/health.py` |
| Search | `create_search_input(input_id, placeholder, clear_button)`, `filter_content(query, items, fields)`, `highlight_segments` — `src/web/dashboard/search_utils.py` |

`create_search_input(..., clear_button=True)` adds a `<id>-clear` icon that
needs its own callback — a second writer of the search box `value`, hence
`allow_duplicate=True` (`deals_tab.py` has one).

## The one exception: `shortcuts_tab.py`

Hidden on user request (2026-08-27): no nav shell, no `_TAB_RENDERERS` entry.
It stays imported because the Ctrl+K palette reads `get_shortcuts_data()` from
it, and re-enabling is a 2-line change. Keep its callbacks registered and its
row in `RENDERERS`.

## Definition of done

- [ ] `uv run python run_watchtower_dashboard.py` starts (port **7780**) with no
      import errors.
- [ ] The tab is in the navbar and renders when clicked; the browser console
      shows no "Duplicate callback outputs".
- [ ] `uv run pytest Tests/unit/test_tab_render.py` passes with the new
      `RENDERERS` row; `uv run ruff check` is clean on the new file.
- [ ] The ETL behind the tab's data is registered (`etl-pipeline` skill).

## When a tab "isn't showing up"

1. Nav shell or `_TAB_RENDERERS` entry missing — the News content shows
   instead, or the tab is unreachable.
2. A callback never fires: its `Input` id is not in the layout, and nothing
   warns; with `prevent_initial_call=True` it will not fire at load either.
3. Import error in the component — not silent: `app.py` imports every tab, so
   the dashboard fails at startup (traceback in the terminal, or
   `dashboard.err.log` on the server).
4. Component id collides with another tab — rename with the tab slug prefix.
5. The tab renders but is empty — the data path differs from what the ETL
   writes, or the ETL is not registered.
