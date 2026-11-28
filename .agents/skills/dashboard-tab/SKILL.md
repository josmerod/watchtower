---
name: dashboard-tab
description: Build a Watchtower dashboard tab or subtab the standard way, write its callbacks without phantom requests, or wire an existing component so it actually appears and works. Use whenever the user wants to add a dashboard tab, page, section or subtab, surface ETL data in the UI, add a view, a table, a filter, a star, build a component, change a callback, or when a tab is not showing up, is empty, is slow or sends requests nobody asked for. Trigger on "add a tab", "new dashboard page", "subtab", "show X in the dashboard", "pestaña", "subpestaña", "the tab isn't appearing", "register a component", "la pestaña tarda", "duplicate callback outputs".
---

# Dashboard Tab

The dashboard is Dash + Bootstrap in `src/web/dashboard/`: each top-level tab
is a module under `components/` exporting `render_<name>_tab()`. A component
file alone renders nothing — it has to be wired in `app.py`, read by a test
and counted in the browser.

## Top-level tab, or a subtab?

- A **subtab** when the content belongs to a family that already has a tab
  (Open Source lives inside Knowledge Garden, Giveaways inside Games). This
  is the usual case, and the bar is full: 18 tabs.
- A **top-level tab** only for a family of its own.

Either way the module is self-contained — layout, callbacks and its tests —
and only the host tab or `app.py` imports it.

## Wiring a top-level tab

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

## Wiring a subtab

The host tab owns the subtab bar (`dbc.Tabs`) and is the only module that
registers callbacks with `app.py`. Add the content module, then in the host:

1. Import its render function and its `register_<sub>_callbacks(app)`.
2. Add a `dbc.Tab(label=..., tab_id=…)` to the host's subtab bar and map the
   id to the render function wherever the host resolves its subtabs.
3. Call its register function from the host's register function.
4. Extend the host's subtab test (`Tests/web/dashboard/test_<host>_subtabs.py`)
   and add the subtab's own test file next to it.

Give the bar `active_tab=` in the layout, and keep it lazy: a tab that renders
every subtab pays one controller call per subtab on open. The dispatcher and
per-subtab controller pattern, with what it measured, is in
`references/callbacks.md`.

## Every tab is lazy

`render_active_tab` in `app.py` — `Output("tab-content", "children")` from
`Input("dashboard-tabs", "active_tab")` — looks the active id up in
`_TAB_RENDERERS` and calls that renderer when the tab is selected, and once at
load for the default `tab-news`.

- `render_<name>_tab()` must return the default view — do not rely on
  load-time callbacks to finish drawing it. It runs on every switch, so read
  data inside it (cached), not at import time.
- The two ids must match. A nav tab missing from `_TAB_RENDERERS` silently
  shows the News tab; a renderer without a nav shell is unreachable.

## The component

Mirror `deals_tab.py` (searchable table with callbacks) or `games_tab.py`
(static), and reuse the shared helpers:

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
  `prevent_initial_call=True`.
- **`suppress_callback_exceptions=True`** in `app.py`, because the layout is
  dynamic — so Dash does not check ids either: a typo in an `Input`/`Output`
  id is silent.
- **`prevent_initial_call=True`** on callbacks that react to input — the
  convention in AGENTS.md, not universal in the code — since the renderer
  already drew the default view. Leave it off only where a callback must fill
  an empty container on load (`courses_tab.py`, `notifications_tab.py`,
  `videos_tab.py`).
- **A callback can run without a click.** When its buttons are inserted, or a
  tab was open across a deploy: guard with `only_inserted()`, `clicked_prop()`
  or `if not n_clicks`. What fires when, and the two `ctx` traps that left a
  feature dead for two months: `references/callbacks.md`.
- **Every Input stays in the page.** Dash skips a callback while one of its
  Inputs is missing, silently. A pager that is not rendered "because there is
  only one page" took the search box sharing its callback with it. Hide
  controls (`display: none`); do not drop them.
- **`dbc.Checkbox` state is `value`**, not `checked`: an Input on `checked`
  never fires.
- **Never thousands of pattern-matching ids in one layout.** The renderer
  reindexes every id on each update; 2,078 of them blocked the tab for 40 s.
- **IDs are global**: prefix every id with the tab slug —
  `pagination_controls(tab_slug, ...)` and `create_refresh_button(tab_slug)`
  already do.
- **Premium, minimalist UI**: Bootstrap components, responsive rows/cols, the
  shared styles in `src/web/dashboard/assets/`. A change to a CSS or JS asset
  that browsers cached needs its `?v=N` bumped where `app.py` links it
  (`zz_visual_refresh.css?v=9`).

## Reading data

Tabs read JSON files under `data/`; no tab calls the API over HTTP and no
callback scrapes (`etl-pipeline` skill). Three ways, in order of preference
when the tab is more than one table:

- **`src/services/data_loader.py`**: its `*_SOURCES_CONFIG` dicts map a
  source key to `{"path", "name"}`, and `load_data_from_file(path)` returns a
  list of dicts — `[]` when the file is missing or broken. Paths come from
  `get_data_path` in `src/web/dashboard/utils.py`.
- **A repository** (`BaseRepository` subclass under `src/repositories/`,
  documented in `docs/REPOSITORY_PATTERN.md`): transform once, cache, and a
  testable seam between files and tab. The cache lasts up to an hour and ends
  when the file changes (`mtime_ns` + size), so data a cycle just wrote shows
  at the next request.
- **`TTLDataCache(ttl_seconds=...)`** in
  `src/web/dashboard/components/shared/cache.py` for a short cache inside a tab
  (Knowledge Garden keeps 60 s on top of its repository).

## Starting one tab on its own

To see a tab in a browser before wiring it, or to check a layout change:

```bash
uv run python .agents/skills/dashboard-tab/scripts/run_dashboard_temp_root.py
```

It serves the whole app on `http://127.0.0.1:8790/` from the checkout you are
in, over a **copy** of `data/` under a temporary root: the dashboard writes
`data/garden/saved_items.json` when a star is clicked, and the real file is
the user's. `--root <dir>` keeps the copy between runs, `--no-copy` starts
empty. Stop it with Ctrl+C; never leave it running when you report.

Count requests while you click: open the browser's network panel filtered on
`_dash-update-component`. One user action should cost one request. More means
a controller without `prevent_initial_call=True` or an unguarded inserted
input (`references/callbacks.md`).

## Shared helpers — reuse them

| Need | Use |
| :--- | :--- |
| Table | `render_items_table(items, columns, empty_message=..., wrap_scroll=...)`, `title_cell`, `text_cell`, `badges_cell` — `src/web/dashboard/components/shared/table.py` |
| Paging, refresh | `paginate`, `pagination_controls`, `create_refresh_button` — same file |
| Short cache | `TTLDataCache(ttl_seconds=...).get(loader)` — `src/web/dashboard/components/shared/cache.py` |
| Source freshness | `source_health_dots` — `src/web/dashboard/components/shared/health.py` |
| Search | `create_search_input(input_id, placeholder, clear_button)`, `filter_content(query, items, fields)`, `highlight_segments` — `src/web/dashboard/search_utils.py` |
| Star (save for later) | `save_button(item, btn_type, tab=...)` in the layout, `register_save_toggle_callback(app, btn_type)` once per tab — `src/web/dashboard/components/saved_items.py` |

`create_search_input(..., clear_button=True)` adds a `<id>-clear` icon that
needs its own callback — a second writer of the search box `value`, hence
`allow_duplicate=True` (`deals_tab.py` has one).

## Tests

| What | Where | Example |
| :--- | :--- | :--- |
| A tab as a whole: layout, subtab list, callbacks through the endpoint | `Tests/web/dashboard/test_<tab>_<what>.py` — the convention since 2026-11-27 | `test_news_subtabs.py`, `test_inserted_buttons.py` |
| Every top-level tab renders | `RENDERERS` in `Tests/unit/test_tab_render.py` | add one row |
| A guard or helper shared by tabs | `Tests/unit/test_<subject>.py` | `test_repository_cache.py`, `test_saved_items_tabs.py` |

Older tab tests sit in `Tests/unit/` (`test_kg_lazy_render.py`,
`test_markets_tab.py`, `test_videos_theme_filter.py`) and in `Tests/dashboard/`
(`test_notifications_tab.py`). Extend them where they are; new tab tests go to
`Tests/web/dashboard/`.

- Never reach a real service and never read or write the real `data/` or
  `data/garden/saved_items.json`: build the app with `tmp_path` data, or patch
  the loader.
- For a callback, call it through the endpoint, not only as a function —
  `call()` in `Tests/web/dashboard/test_inserted_buttons.py` (`references/callbacks.md`).
- Run your files while you iterate: `uv run pytest Tests/web/dashboard/test_<tab>_<what>.py -q`.

## The one exception: `shortcuts_tab.py`

Hidden on user request (2026-08-27): no nav shell, no `_TAB_RENDERERS` entry.
It stays imported because the Ctrl+K palette reads `get_shortcuts_data()` from
it, and re-enabling is a 2-line change. Keep its callbacks registered and its
row in `RENDERERS`.

## Definition of done

- [ ] The launcher starts, the tab or subtab is in its bar and renders when
      clicked, with data.
- [ ] One request per user action in the network panel; the browser console
      shows no "Duplicate callback outputs" and no error.
- [ ] `uv run pytest Tests/unit/test_tab_render.py Tests/web/dashboard -q`
      passes with the new row and test; `uv run ruff check` and
      `uv run ruff format --check` are clean on the new files.
- [ ] The ETL behind the tab's data is registered (`etl-pipeline` skill).
- [ ] On a mobile width (below 768 px) the subtab bar still shows its tabs.
- [ ] After the deploy, the tab is checked in the browser on the public
      dashboard (`unraid-deploy` skill).

## When something "isn't showing up"

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
6. Too many requests, or slow to open — `references/callbacks.md`: count
   pattern ids and unguarded controllers.
