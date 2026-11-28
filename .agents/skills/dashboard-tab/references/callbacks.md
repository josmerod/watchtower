# When Dash runs a callback

Measured on 2026-11-27 in this app (Dash 4.1.0, dash-bootstrap-components
2.0.4) by reading the renderer, `dash/dash.py` and counting requests in the
browser. Phantom callbacks were most of the cost of opening Knowledge Garden
(62 requests) and News (16), and no unit test showed them.

## Inserted components

- **An inserted output does not fire** its callback when it has
  `prevent_initial_call=True`.
- **An inserted input fires on insertion** when its callback has
  `prevent_initial_call=False`: a request with `changedPropIds: []`. That is
  why a controller without the flag re-renders the table the layout already
  drew. With `prevent_initial_call=True` it does not fire when the callback
  also has an output in the same inserted chunk — literal and pattern (`ALL`)
  inputs alike.
- **A pattern input still fires on insertion when its callback's output is in
  another chunk**: one request whose `changedPropIds` lists every inserted
  component, each with `value=None`. So a callback can be called without a
  click: guard it (below).
- **A path that already existed never fires because of a render**, even when
  its value is rewritten. Callbacks fire on every prop update, value changed
  or not.
- **`dbc.Tabs` without `active_tab` sets it on mount** — a prop update, so a
  listener with `prevent_initial_call=True` still fires once on insertion
  (ArXiv: 166 KiB re-rendering the same table). Give `active_tab=` in the
  layout.
- **A callback writing its own input does not re-trigger itself** (the ArXiv
  controller empties `search.value`, which is also its Input: one request).
  Another callback writing that input does (the clear button → a second
  request).
- **A pager whose buttons are re-rendered as the callback's own output**
  (`pager.children`) does not re-trigger that callback: one request per
  click, page stable.

## An Input or Output that is not in the page

The renderer skips a callback while any of its Inputs **or Outputs** is
missing from the page, and with `suppress_callback_exceptions=True` nothing
says so: the browser console gets one line ("A nonexistent object was used in
an `Input` of a Dash callback") and the control does nothing. Scavenging
shipped a dead search box that way (2026-11-27): a source that fitted on one
page rendered an **empty** pager, so the search controller, which also listens
to Prev and Next, never ran there. Keep every Input in the layout and hide the
controls instead when there is nothing to page (`_pager` in
`scavenging_tab.py` wraps the bar in `html.Div(bar, hidden=True)`).

The same holds for an **Output** ("…used in an `Output` of a Dash callback.
The id of this object is `…`"). The next day the Scavenging dispatcher wrote
one activate store per live source, two of which had no subtab in the layout:
the whole dispatcher was skipped, the first subtab stayed at "Loading…" and
no Python log said why. Every id a callback touches has to be in the page:

- stores that several subtabs share go in one container that is always
  rendered (`_activate_stores()` in `scavenging_tab.py`);
- a subtab with nothing to build keeps its whole shell — controls, table
  container, pager, stores — hidden under its message (`_inactive()` in
  `courses_tab.py`): its controller's ids have to be in the page too, or the
  console gets one line per missing id and clicking the subtab does nothing;
- pin it with a test that walks `app._callback_list` and checks the id of
  every Input, State and Output against the layout
  (`test_every_id_every_callback_uses_is_in_the_layout` in
  `Tests/web/dashboard/test_courses_lazy.py`).

## Checkbox state

`dbc.Checkbox` (2.0.4) has `value` and no `checked` prop. `Input(id,
"checked")` is accepted at registration and never fires.

## Search boxes

A search that runs on the server sends a request per keystroke unless the box
waits: up to 60 KiB a key in Learning. `dbc.Input(debounce=400)` sends one
request after a pause. The number is in **milliseconds**: `dbc.Input`
documents it, and the installed `dcc.Input` (4.1.0) says "seconds" in its
docstring and measured 400 as 440 ms. `debounce=True` is the other contract:
Enter or blur only. Enter does not cut a numeric pause short: a real Enter
4 ms after the last key still waited, the request left at 420 ms.

## Guards for a call without a click

| The callback's Input | Guard |
| :--- | :--- |
| `{"type": …, "hash": MATCH}, "n_clicks"` | `if not n_clicks: return dash.no_update, …` |
| `{"type": …, "keys": ALL}, "n_clicks"` | `if only_inserted(n_clicks): raise dash.exceptions.PreventUpdate` |
| Need the button that was clicked | `clicked_prop(dash.ctx)` |

`only_inserted()` and `clicked_prop()` live in `src/web/dashboard/utils.py`.
They look at the changed value, never at the argument: with `ALL` the
argument is a **list**, and comparing it with an int raised, so the video
modal never opened.

**`dash.ctx.triggered`** is `[{"prop_id": x, "value": input_values.get(x)} for
x in changedPropIds]`, and on an initial call a falsy list holding one dummy
item, `{"prop_id": ".", "value": None}`. `ctx.triggered_id` is the id of the
**first** entry — a dict for pattern ids. Entries carry `prop_id` and `value`
only: there is no `id` key. Comparing `entry["id"]` was always false and left
«Mi cartera» dead for two months. Use `dash.ctx.triggered_prop_ids[prop_id]`
for the id object, or index the dict (`triggered_id["keys"]` — `.keys` is the
method, which killed the News CSV export).

## Cost: pattern-matching ids

The renderer reindexes the ids of the whole layout on every update — a
recursive walk that compares each id with the previous list by deep equality
— so the cost is quadratic in the components sharing an id-key signature.
2,078 pattern ids (1,039 papers, an expander and a detail each) blocked the
main thread for 40 s or more. Render the active view only; never thousands of
pattern-matching components in one layout.

## Lazy subtabs

A tab that renders every subtab pays one controller call per subtab on open.
Knowledge Garden went from 62 requests to 3 (T-136) with:

- a dispatcher: `Output(<prefix>-activate.data) ← Input(<tabs-id>, "active_tab")`;
- one controller per subtab, `prevent_initial_call=True`, idle until its
  store is non-empty (`_kg_controller_plan` in `knowledge_garden_tab.py`);
- 2 requests per subtab switch.

Scavenging (T-170) is the same shape for a shell per source
(`_scavenging_activation`, `_scavenging_trigger` and
`register_scavenging_callbacks` in `scavenging_tab.py`), with two
differences worth copying:

- the dispatcher takes the activate stores as **State** and answers
  `no_update` for one that is marked already, so opening a subtab a second
  time costs no request;
- the controllers are registered for every configured source, file or not,
  and the layout shows only the sources that have a file: one that appears
  after startup gets its subtab and its search without a restart.

A source marked `"paused"` in the config keeps its subtab, which shows the
note, and gets no controller (T-157).

Learning (T-177) runs its dispatcher in the browser
(`app.clientside_callback`, no request) and reads the same State: without it
the dispatcher wrote 1 again on every return and the subtab was rebuilt —
61 KiB for the rows already on screen — because a callback fires on every
prop update, value changed or not. Opening the tab is the layout and one
controller (85 KiB in the test root) and a subtab switch is one request.

For a bar of categories over one data family, one controller is enough:
`arxiv_research_tab.py` (`_arxiv_category_update`) — 1 request on open and 1
per switch.

## Stars

`save_button(item, btn_type, tab=…)` and
`register_save_toggle_callback(app, btn_type)` in `saved_items.py`: one
pattern-matching (`MATCH`) callback per button type, with `n_clicks` as its
Input and the button's own `children`, `color` and `title` as its outputs.
Measured on 2026-11-27: inserting 200 of them costs no request — the outputs
are the buttons themselves, the same chunk.

## Starting one tab on its own

`uv run python -m src.web.dashboard.components.<tab>` works where the module
has a `build_test_app()` (`games_tab.py`), and only through the skill's
launcher: the dashboard reads `data/` and writes the saved items. Two facts
that cost an evening:

- `app.run(...)` — `app.run_server` was removed in Dash 4
  (`ObsoleteAttributeException`).
- A server started with `debug=True` runs a reloader, a parent and a child
  process: kill only the listener and the child comes back. Find the parent
  by its command line, not by the port.

## Requests the server refuses

Three ways Dash refuses a request before any callback runs: a callback that
does not exist (`CallbackException`), empty `outputs` (`KeyError: 'id'`), and
fewer inputs than declared (`IndexError` — a tab left open across a deploy
that added an Input). All three are a 204 and one warning line through
`callback_request_refused` in `app.py`, which re-raises anything whose
traceback went through `src/` (a callback of ours). Keep that guard when
touching it, or a `KeyError` in a callback loses its traceback.

## Testing callbacks

- `app._callback_list` entries carry `prevent_initial_call` and stringified
  pattern ids (`'{"index":["ALL"],"type":…}'`); `app.callback_map` entries do
  not carry the flag, and `callback_map[k]["callback"]` has no
  `.prevent_initial_call` — call `["callback"].__wrapped__`.
- Call the function directly with a simulated context:
  `monkeypatch.setattr(dash, "ctx", SimpleNamespace(triggered=[…], triggered_id=…))`.
- **Drive the real endpoint** — the harness that found two bugs the direct
  calls hid: `server.test_client().post("/_dash-update-component", json=body)`
  with `body = {"output": "<spec>", "outputs": <dict | list>, "inputs": [...],
  "changedPropIds": [...], "state": [...]}`; the test app needs `app.layout`
  set. Each Input/State slot is a dict `{id, property, value}` for a literal
  or `MATCH` id and a **list of dicts** (one per component on screen, `[]`
  when none) for `ALL`. Pattern ids are JSON strings in `inputs` and
  `changedPropIds` and dicts in `outputs`. `outputs` is a **dict for a callback
  with one output and a list of dicts for several**: a list of one is taken
  for a group and the server answers 500 ("wildcard multi-output"). The
  property of an `allow_duplicate` output goes without its `@…` suffix. A
  multi-output is listed as `..id.prop...id.prop..`, so an id cannot be read
  in front of the first dot. The answer is nested
  `{"<id>": {"<prop>": value}}`; every output `no_update` gives
  `"response": {}`, and `PreventUpdate` gives HTTP 204. `call()` in
  `Tests/web/dashboard/test_inserted_buttons.py` and `_post()` in
  `Tests/web/dashboard/test_scavenging_lazy.py` wrap it.
- Posting to the server is not the renderer: it says nothing about a callback
  that the browser would refuse (missing Input or Output, above) and it never
  runs a `clientside_callback` — check those ids against the layout and open
  the tab in a browser once before shipping a lazy tab.
- Headless Chromium throttles `requestAnimationFrame`, so React commits late:
  wait before reading the DOM after a click.
- Read the visible pane: `.tab-content .tab-pane.active` matches the outer
  pane. Filter `.tab-pane` by bounding box and take the last one.
