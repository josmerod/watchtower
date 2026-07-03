---
name: dashboard-tab
description: Build a new Watchtower dashboard tab the standard way, or wire an existing one so it actually appears in the app. Use whenever the user wants to add a dashboard tab/page/section, surface ETL data in the UI, add a new view, build a component, or when a tab exists but isn't showing up. Trigger on "add a tab", "new dashboard page", "show X in the dashboard", "add a view", "surface the data", "the tab isn't appearing", "register a component".
---

# Dashboard Tab

The dashboard is Dash + Bootstrap, ~25 tabs, single app in `src/web/dashboard/`.
Tabs are modular but must be wired into `app.py` in **three** places or they
won't render. This skill keeps new tabs consistent and registered.

## The 3 obligations of a new tab

A new `*_tab.py` file alone renders nothing. All three wirings below are required.

1. **Create the component** in `src/web/dashboard/components/<name>_tab.py`.
2. **Import it** in `src/web/dashboard/app.py`.
3. **Render it** in `app.py`'s layout — either a static `dbc.Tab(...)` or the
   lazy `render_active_tab` map.

## Obligation 1 — the component

Mirror a real sibling (e.g. `valencia_events_new_tab.py`,
`spanish_public_aid_tab.py`) before writing. Every component exports two names:
`render_<name>_tab()` and (if it has interactivity) `register_<name>_callbacks(app)`.

```python
"""<Name> tab — one-line purpose."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html
from dash import Dash


def render_my_tab() -> dbc.Container:
    """Return the layout for this tab. Pull data from the API or _latest.json."""
    return dbc.Container(
        [
            dbc.Row(dbc.Col([html.H3("My Tab"), html.Div(id="my-content")])),
        ],
        fluid=True,
    )


def register_my_callbacks(app: Dash) -> None:
    """Wire this tab's callbacks on the app. One callback per output component."""

    @app.callback(
        Output("my-content", "children"),
        Input("my-input", "value"),
        prevent_initial_call=True,
    )
    def _update(value):  # noqa: ANN001 - dash callback signature
        try:
            ...
            return f"Updated: {value}"
        except Exception as exc:  # noqa: BLE001 - surface errors in the UI
            return f"Error: {exc}"
```

Hard rules (these are in `AGENTS.md` and bite if ignored):

- **Single Callback Pattern**: exactly one callback per output component id.
  Multiple callbacks writing the same `Output` id throw `DuplicateCallback`
  errors at startup because `app.py` sets `suppress_callback_exceptions=True`
  and binds globally.
- **`prevent_initial_call=True`** unless you genuinely need first-load population.
- **Premium, minimalist UI**: Bootstrap components, semantic structure, responsive
  rows/cols. No inline CSS piles — reuse the shared styles in `/assets/`.
- **IDs are global**: prefix every component id with the tab's slug
  (`mytab-...`) to avoid collisions across the ~25 tabs in one app.
- **Data loading**: read from the API (`src/web/api/`) or from
  `data/<name>/output/<name>_latest.json`. Never scrape inside a callback —
  that's what ETLs are for (see the `etl-pipeline` skill).

## Obligation 2 — import in app.py

At the top of `src/web/dashboard/app.py`, next to the other tab imports:

```python
from src.web.dashboard.components.my_tab import (
    register_my_callbacks,
    render_my_tab,
)
```

If the tab has no callbacks, import only `render_my_tab`.

## Obligation 3 — render it in the layout

`app.py` has two rendering mechanisms. Look at how the existing tabs are wired and
use whichever they use:

**A) Static `dbc.Tab`** (in the `dbc.Tabs([...])` block, ~line 177):
```python
dbc.Tab(
    label="My Tab",
    tab_id="tab-mytab",
    children=render_my_tab(),
),
```

**B) Lazy via the `render_active_tab` map** (~line 564) — tabs render only when
activated, which is the pattern for heavier tabs. Add to the dict **and** ensure a
matching `dbc.Tab(tab_id="tab-mytab", label="My Tab")` shell exists in the
`dbc.Tabs` block:
```python
TAB_RENDERERS = {
    ...
    "tab-mytab": render_my_tab,
}
```

Then register callbacks once at module load (after the layout), where the other
`register_*_callbacks(app)` calls live:
```python
register_my_callbacks(app)
```

Pick **one** of A or B per tab — never both, or the tab renders twice.

## Definition of done

- [ ] `uv run python run_watchtower_dashboard.py` starts (port **7780**) with no
      `DuplicateCallback` / import errors in the console.
- [ ] The tab is visible in the navbar and renders content when clicked.
- [ ] `uv run ruff check src/web/dashboard/components/my_tab.py` is clean.
- [ ] No duplicate or stale tab file left behind (the `components/` folder already
      has `_broken` / `_backup` / `_basic` variants — don't add more; clean them up
      if you're refactoring one).
- [ ] If the tab reads ETL data, that ETL is registered in
      `run_all_etl_orchestrator.py` (see `etl-pipeline` skill) — otherwise the tab
      is empty in production.

## When a tab "isn't showing up"

In order of likelihood:
1. Component file exists but not imported in `app.py` → Obligation 2.
2. Imported but not added to the `dbc.Tabs` block / `TAB_RENDERERS` → Obligation 3.
3. Added to both static and lazy paths → renders twice / conflicts; pick one.
4. Import error in the component silently skipped → check the dashboard startup
   logs; Dash prints the failing import.
5. Component id collides with another tab → rename with the tab slug prefix.
