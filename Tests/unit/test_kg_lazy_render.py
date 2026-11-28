"""Unit tests for the lazy Knowledge Garden subtab render (T-136).

The tab used to build every subtab's table up front: with the production
sources that was ~600 KiB of layout and half a second of server time for the
one subtab in view, plus one read of the saved-items file per row. Now a subtab
renders its search bar, its pagination bar and a hidden list of its first
page's dates, and the table is built by the controller when the subtab is
first opened.

How a subtab gets opened matters as much as what is rendered: every Dash
response costs the browser a pass over all mounted components. A dispatcher
marks the open subtab in an activate store and only its controller runs, and
the stars are plain buttons handled by assets/js/kg_state.js, because Dash
runs a pattern-matching callback once per button inserted into the page.

Fixture-based like test_kg_card_view_toggle.py: the data loader is
monkeypatched and the saved-items file is a temp file, so nothing reads
data/ and nothing touches the network.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import dash
import pytest
from dash import dcc, html

from src.services.data_loader import KNOWLEDGE_SOURCES_CONFIG
from src.web.dashboard.components import knowledge_garden_tab as tab
from src.web.dashboard.components import saved_items
from src.web.dashboard.components.saved_items import SAVE_CANDIDATES
from src.web.dashboard.search_utils import create_search_input

PAGE = tab.MAX_ARTICLES_PER_SOURCE

# 60 items, one per hour. The fixture lists them oldest first, so the render has to sort.
_ITEMS = [{"title": f"Post {n:02d}", "url": f"http://example.com/{n:02d}", "source": "LessWrong", "published": f"2026-08-{1 + n // 24:02d}T{n % 24:02d}:00:00"} for n in range(60)]

IDLE = (dash.no_update,) * 7
LW_TAB = "knowledge-tab-lw"
LW_SEARCH = "knowledge-search-lesswrong"
POD_SEARCH = "knowledge-search-podcasts"
_JS_PATH = Path(__file__).resolve().parents[2] / "src" / "web" / "dashboard" / "assets" / "js" / "kg_state.js"


@pytest.fixture
def saved_file(tmp_path, monkeypatch):
    """A real temp file as the saved-items store: the star tests read back what was written."""
    fake = tmp_path / "saved_items.json"
    monkeypatch.setattr(saved_items, "SAVED_FILE", fake)
    monkeypatch.setattr(saved_items, "_saved_stamp", None)
    SAVE_CANDIDATES.clear()
    return fake


@pytest.fixture
def patched_data(saved_file, monkeypatch):
    """Freeze the tab's data source so tests are hermetic."""
    data = {"lesswrong": [dict(item) for item in _ITEMS]}
    monkeypatch.setattr(tab, "get_all_knowledge_data", lambda force_refresh=False: data)
    yield data
    SAVE_CANDIDATES.clear()


def _walk(node):
    """Yield every node of a Dash component tree."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        yield from _walk(child)


def _texts(node):
    return " ".join(str(t) for t in _walk(node) if isinstance(t, str))


def _by_id(layout, component_id):
    return [n for n in _walk(layout) if getattr(n, "id", None) == component_id]


def _with_attribute(layout, attribute):
    return [n for n in _walk(layout) if getattr(n, attribute, None) is not None]


def _save_buttons(layout):
    return _with_attribute(layout, "data-kg-hash")


def _listens(entry, component_id, prop):
    return any(r.get("id") == component_id and r.get("property") == prop for r in entry["inputs"])


def _is_kg(ref):
    """Whether a callback dependency points at a Knowledge Garden component."""
    return isinstance(ref.get("id"), str) and (ref["id"].startswith(("knowledge-search-", "kg-")) or ref["id"] == tab.KG_TABS_ID)


# ---------------------------------------------------------------------------
# Layout: no table until the subtab is opened
# ---------------------------------------------------------------------------


def test_layout_builds_no_table_until_a_subtab_is_opened(patched_data):
    layout = tab.render_knowledge_garden_tab()

    assert _with_attribute(layout, "data-kg-date") == []  # neither list rows nor cards
    assert _save_buttons(layout) == []
    page_stores = [n for n in _walk(layout) if isinstance(n, dcc.Store) and n.id.endswith("-page")]
    assert len(page_stores) == len(tab.KNOWLEDGE_TAB_DEFINITIONS)
    assert all(getattr(store, "data", None) is None for store in page_stores)  # no data = table not built yet
    activate_stores = [n for n in _walk(layout) if isinstance(n, dcc.Store) and n.id.endswith("-activate")]
    assert [store.data for store in activate_stores] == [0] * len(tab.KNOWLEDGE_TAB_DEFINITIONS)  # 0 = not opened yet


def test_layout_carries_the_star_request_store_and_the_outcome_element(patched_data):
    layout = tab.render_knowledge_garden_tab()

    (request,) = _by_id(layout, tab.KG_SAVE_REQUEST_ID)
    assert isinstance(request, dcc.Store) and getattr(request, "data", None) is None
    (outcome,) = _by_id(layout, tab.KG_SAVE_OUTCOME_ID)
    assert outcome.hidden is True and getattr(outcome, "children", None) is None


def test_every_subtab_keeps_its_search_bar_buttons_and_stores(patched_data):
    layout = tab.render_knowledge_garden_tab()

    for tab_def in tab.KNOWLEDGE_TAB_DEFINITIONS:
        search_id = tab._knowledge_search_id(tab_def)
        for suffix in ("", "-view-toggle", "-refresh", "-clear", "-results", "-prev", "-next", "-page-info", "-activate"):
            assert len(_by_id(layout, f"{search_id}{suffix}")) == 1, f"{search_id}{suffix}"
        assert [s.data for s in _by_id(layout, f"{search_id}-view")] == ["list"]


def test_pagination_bar_is_rendered_before_the_table_and_waits(patched_data):
    layout = tab.render_knowledge_garden_tab()

    assert [n.children for n in _by_id(layout, f"{LW_SEARCH}-page-info")] == ["Cargando…"]
    assert all(n.disabled for suffix in ("-prev", "-next") for n in _by_id(layout, f"{LW_SEARCH}{suffix}"))


def _literal_ids(entry):
    """String ids of a callback's inputs and states (pattern-matching ids are skipped)."""
    return {ref["id"] for ref in entry["inputs"] + entry["state"] if isinstance(ref.get("id"), str)}


def _listening_callbacks():
    """Every callback of the real app, from any module, that reads a Knowledge Garden component."""
    from src.web.dashboard.app import app

    return [e for e in app._callback_list if any(_is_kg(r) for r in e["inputs"] + e["state"])]


def test_every_knowledge_garden_input_is_in_the_tab_before_any_table_is_built(patched_data):
    """Dash refuses to fire a callback whose input id is not in the page (T-136).

    A subtab's table is not in the page until the subtab is opened, so every
    callback that listens to a Knowledge Garden component must find its id in
    the tab's own layout.
    """
    in_page = {n.id for n in _walk(tab.render_knowledge_garden_tab()) if isinstance(getattr(n, "id", None), str)}
    listening = _listening_callbacks()

    results = tuple(f"{tab._knowledge_search_id(d)}-results.children" for d in tab.KNOWLEDGE_TAB_DEFINITIONS)
    assert sum(1 for e in listening if any(output in e["output"] for output in results)) == len(tab.KNOWLEDGE_TAB_DEFINITIONS)
    for entry in listening:
        assert _literal_ids(entry) <= in_page, (_literal_ids(entry) - in_page, entry["output"])


def test_no_knowledge_garden_callback_takes_a_pattern_id_input():
    """Dash runs a pattern-matching callback once per component inserted into the page.

    The stars were such an input: building a subtab's table sent fifty no-op
    star requests. Stars now go through assets/js/kg_state.js and the request
    store, and nothing in the tab may listen to a pattern id again.
    """
    pattern_inputs = [(r, e["output"][:80]) for e in _listening_callbacks() for r in e["inputs"] + e["state"] if isinstance(r.get("id"), dict)]

    assert pattern_inputs == []


def test_only_the_dispatcher_listens_to_the_subtab_bar():
    """Twelve controllers used to listen to it, so every switch ran them all."""
    listening = [e for e in _listening_callbacks() if _listens(e, tab.KG_TABS_ID, "active_tab")]

    assert len(listening) == 1
    assert all(f"{tab._knowledge_search_id(d)}-activate.data" in listening[0]["output"] for d in tab.KNOWLEDGE_TAB_DEFINITIONS)


def test_search_boxes_wait_for_a_pause_in_typing(patched_data):
    layout = tab.render_knowledge_garden_tab()
    boxes = [n for n in _walk(layout) if isinstance(getattr(n, "id", None), str) and n.id.startswith("knowledge-search-") and hasattr(n, "debounce")]

    assert len(boxes) == len(tab.KNOWLEDGE_TAB_DEFINITIONS)
    assert {box.debounce for box in boxes} == {tab.KG_SEARCH_DEBOUNCE_MS}
    assert tab.KG_SEARCH_DEBOUNCE_MS > 0


def test_create_search_input_debounces_only_when_asked():
    assert getattr(create_search_input("plain").children[0], "debounce", False) is False  # other tabs keep a callback per keystroke
    assert create_search_input("slow", debounce=400).children[0].debounce == 400


def test_clear_button_reports_clicks_and_matches_the_input_height():
    """The clear control used to be an InputGroupText, which has no n_clicks: the × did nothing in any tab."""
    from dash_bootstrap_components import Button

    group = create_search_input("box")
    clear = group.children[1]

    assert isinstance(clear, Button) and clear.id == "box-clear" and "n_clicks" in clear._prop_names
    assert clear.children == "×"
    assert "mb-3" not in getattr(group.children[0], "className", "") and "mb-3" in group.className  # the margin belongs to the group, or the × box grows taller than the input
    assert "mb-3" in create_search_input("bare", clear_button=False).className


def test_unopened_subtab_carries_its_first_page_dates_for_the_new_counter(patched_data):
    layout = tab.render_knowledge_garden_tab()

    results = _by_id(layout, f"{LW_SEARCH}-results")[0]
    pending = _with_attribute(results, "data-kg-dates")
    assert len(pending) == 1
    dates = [d for d in getattr(pending[0], "data-kg-dates").split(",") if d]
    assert len(dates) == PAGE
    # Same dates, same order as the rows the table will show: the counter does not change when the subtab opens.
    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong")
    row_dates = [getattr(n, "data-kg-date") for n in _with_attribute(content, "data-kg-date") if getattr(n, "data-kg-date")]
    assert dates == row_dates


def test_pending_dates_attribute_survives_serialization(patched_data):
    layout = tab.render_knowledge_garden_tab()
    pending = _with_attribute(layout, "data-kg-dates")[0]

    assert pending.to_plotly_json()["props"]["data-kg-dates"] == getattr(pending, "data-kg-dates")
    assert pending.hidden is True  # counted by kg_state.js, never shown


def test_subtab_without_items_carries_no_dates(patched_data):
    layout = tab.render_knowledge_garden_tab()
    results = _by_id(layout, "knowledge-search-podcasts-results")[0]

    assert [n for n in _with_attribute(results, "data-kg-dates") if getattr(n, "data-kg-dates")] == []


# ---------------------------------------------------------------------------
# Controller: decides from an explicit trigger (pure), so it is testable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("triggered", "activated", "page", "view", "expected"),
    [
        # Table never built: its own activation builds it, whatever else fired.
        (f"{LW_SEARCH}-activate", 1, None, None, (1, "list", False)),
        (LW_SEARCH, 1, None, "cards", (1, "list", False)),
        (f"{LW_SEARCH}-view-toggle", 1, None, None, (1, "list", False)),
        # …and until then there is nothing to act on.
        (None, 0, None, None, None),
        (f"{LW_SEARCH}-next", None, None, None, None),
        (tab.KG_TABS_ID, None, None, None, None),
        # Table already built: its own controls act, anything else is ignored.
        (f"{LW_SEARCH}-activate", 1, 3, "cards", None),
        (None, 1, 3, "cards", None),
        (LW_SEARCH, 1, 3, "cards", (1, "cards", False)),  # a new search term restarts from page 1
        (f"{LW_SEARCH}-prev", 1, 3, "cards", (2, "cards", False)),
        (f"{LW_SEARCH}-next", 1, 3, "list", (4, "list", False)),
        (f"{LW_SEARCH}-refresh", 1, 3, "list", (3, "list", True)),
        (f"{LW_SEARCH}-view-toggle", 1, 3, "list", (3, "cards", False)),
        (f"{LW_SEARCH}-view-toggle", 1, 3, "cards", (3, "list", False)),
        (f"{LW_SEARCH}-next", 1, 3, "unknown-view", (4, "list", False)),  # an unknown view falls back to the list
    ],
)
def test_controller_plan(triggered, activated, page, view, expected):
    assert tab._kg_controller_plan(triggered, activated, page, view, LW_SEARCH) == expected


def _run_controller(monkeypatch, *, triggered=None, activated=1, page=None, view="list", search_term=None, search_id=LW_SEARCH):
    """Call one subtab controller as Dash would, with an explicit triggering component."""
    app = dash.Dash("test-kg-lazy")
    tab.register_knowledge_garden_callbacks(app)
    key = next(k for k in app.callback_map if f"{search_id}-results.children" in k)
    controller = app.callback_map[key]["callback"].__wrapped__
    monkeypatch.setattr(dash, "ctx", SimpleNamespace(triggered_id=triggered))
    return controller(search_term, None, None, None, None, activated, page, view)


# ---------------------------------------------------------------------------
# Dispatcher: the only listener of the subtab bar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("active_tab", [None, "", "knowledge-tab-saved", "knowledge-tab-lw", "knowledge-tab-opensource", "knowledge-tab-nope"])
def test_dispatcher_marks_only_the_open_subtab(active_tab):
    values = tab._kg_activation(active_tab)

    assert len(values) == len(tab.KNOWLEDGE_TAB_DEFINITIONS)
    marked = [tab_def["label"] for tab_def, value in zip(tab.KNOWLEDGE_TAB_DEFINITIONS, values, strict=True) if value == 1]
    assert marked == [tab_def["label"] for tab_def in tab.KNOWLEDGE_TAB_DEFINITIONS if f"knowledge-tab-{tab_def['id']}" == active_tab]
    assert all(value == 1 or value is dash.no_update for value in values)  # the others keep their store, and their table


def test_dispatcher_wiring():
    app = dash.Dash("test-kg-dispatcher")
    tab.register_knowledge_garden_callbacks(app)

    listening = [e for e in app._callback_list if _listens(e, tab.KG_TABS_ID, "active_tab")]
    assert len(listening) == 1
    (entry,) = listening
    stores = [f"{tab._knowledge_search_id(tab_def)}-activate.data" for tab_def in tab.KNOWLEDGE_TAB_DEFINITIONS]
    assert entry["output"] == ".." + "...".join(stores) + ".."  # one store per subtab, in the order of _kg_activation
    assert entry["prevent_initial_call"] is False  # it also activates the subtab that is open when the tab first renders
    dispatch = app.callback_map[next(k for k in app.callback_map if stores[0] in k)]["callback"].__wrapped__
    assert dispatch(LW_TAB) == tab._kg_activation(LW_TAB)


def test_controller_builds_the_table_on_first_activation(patched_data, monkeypatch):
    built = []
    real_view = tab._knowledge_view
    monkeypatch.setattr(tab, "_knowledge_view", lambda *args, **kwargs: built.append(kwargs) or real_view(*args, **kwargs))

    content, page, view, toggle, info, prev_disabled, next_disabled = _run_controller(monkeypatch)

    assert len(built) == 1
    assert built[0]["page"] == 1 and built[0]["view"] == "list"
    assert len(_with_attribute(content, "data-kg-date")) == PAGE
    assert (page, view, toggle) == (1, "list", tab.KG_VIEW_TOGGLE_LABELS["list"])
    assert (info, prev_disabled, next_disabled) == (f"Showing {PAGE} of 60 · Page 1 of 2", True, False)  # the loading bar is replaced


def test_controller_stays_idle_until_its_subtab_is_activated(patched_data, monkeypatch):
    built = []
    monkeypatch.setattr(tab, "_knowledge_view", lambda *args, **kwargs: built.append(kwargs))

    for activated in (0, None):
        assert _run_controller(monkeypatch, activated=activated) == IDLE
        assert _run_controller(monkeypatch, activated=activated, triggered=LW_SEARCH) == IDLE

    assert built == []  # not activated: no table, whatever else fired


def test_controller_of_a_built_subtab_ignores_a_trigger_that_is_not_its_own(patched_data, monkeypatch):
    built = []
    monkeypatch.setattr(tab, "_knowledge_view", lambda *args, **kwargs: built.append(kwargs))

    assert _run_controller(monkeypatch, page=2, triggered=None) == IDLE
    assert _run_controller(monkeypatch, page=2, triggered=tab.KG_TABS_ID) == IDLE
    assert built == []


def test_pagination_bar_follows_the_page(patched_data, monkeypatch):
    # 60 items make two pages: page 2 shows the remaining 10.
    content, page, _view, _toggle, info, prev_disabled, next_disabled = _run_controller(monkeypatch, page=1, triggered=f"{LW_SEARCH}-next")
    assert (page, len(_with_attribute(content, "data-kg-date")), info, prev_disabled, next_disabled) == (2, 10, "Showing 10 of 60 · Page 2 of 2", False, True)
    assert _run_controller(monkeypatch, page=2, triggered=f"{LW_SEARCH}-prev")[4:] == (f"Showing {PAGE} of 60 · Page 1 of 2", True, False)


def test_controller_of_an_empty_subtab_shows_an_empty_bar(patched_data, monkeypatch):
    content, page, _view, _toggle, info, prev_disabled, next_disabled = _run_controller(monkeypatch, search_id=POD_SEARCH)

    assert (page, info, prev_disabled, next_disabled) == (1, "Sin elementos.", True, True)
    assert "No knowledge items available for Podcasts." in _texts(content)


def test_controller_reports_an_error_in_place_of_the_table(patched_data, monkeypatch):
    def failing_view(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tab, "_knowledge_view", failing_view)

    content, page, view, toggle, info, prev_disabled, next_disabled = _run_controller(monkeypatch)

    assert "Error searching: boom" in _texts(content)
    assert (page, prev_disabled, next_disabled) == (1, True, True)  # no page to go to
    assert (view, toggle, info) == (dash.no_update, dash.no_update, dash.no_update)


def test_controller_refresh_reloads_the_sources(patched_data, monkeypatch):
    refreshes = []
    monkeypatch.setattr(tab, "get_all_knowledge_data", lambda force_refresh=False: refreshes.append(force_refresh) or patched_data)

    _run_controller(monkeypatch, page=2, triggered=f"{LW_SEARCH}-refresh")

    assert refreshes and refreshes[0] is True  # the sources are reloaded before the table is built from them


def test_controller_searches_from_the_first_page(patched_data, monkeypatch):
    content, page, view, _toggle, info, prev_disabled, next_disabled = _run_controller(monkeypatch, page=4, view="cards", triggered=LW_SEARCH, search_term="  post 5  ")

    assert (page, view) == (1, "cards")
    assert (info, prev_disabled, next_disabled) == ("Showing 10 of 10 · Page 1 of 1", True, True)  # the bar counts the filtered items
    cards = _with_attribute(content, "data-kg-date")
    assert len(cards) == 10  # Post 50 … Post 59
    assert all("Post 5" in _texts(card) for card in cards)


# ---------------------------------------------------------------------------
# Stars: kg_state.js writes the request store, the callback answers with the truth
# ---------------------------------------------------------------------------


def _star_hash(title="X"):
    return getattr(tab._save_button({"url": f"http://example.com/{title}", "title": title, "source": "LessWrong"}), "data-kg-hash")


def _on_disk(saved_file):
    return json.loads(saved_file.read_text(encoding="utf-8")) if saved_file.exists() else []


def test_star_button_is_a_plain_button(patched_data, saved_file):
    """Not a callback input: that is what made Dash run the toggle once per inserted star."""
    item = {"url": "http://example.com/x", "title": "X"}
    h = saved_items.item_hash(item["url"], item["title"])

    star = tab._save_button(item)

    assert type(star) is html.Button and not hasattr(star, "id")
    assert (star.children, star.title) == ("☆", "Guardar para luego")
    assert "btn-outline-secondary" in star.className and "btn-warning" not in star.className
    assert (getattr(star, "data-kg-hash"), getattr(star, "data-kg-saved")) == (h, "0")
    assert star.to_plotly_json()["props"]["data-kg-hash"] == h  # kg_state.js reads it from the DOM
    assert saved_items.SAVE_CANDIDATES[h]["tab"] == "knowledge_garden"  # the toggle finds the full item

    saved_items.toggle_saved(saved_items.SAVE_CANDIDATES[h])
    star = tab._save_button(item)

    assert (star.children, star.title, getattr(star, "data-kg-saved")) == ("★", "Quitar de guardados", "1")
    assert "btn-warning" in star.className and "btn-outline-secondary" not in star.className


def test_star_click_is_persisted_and_answered_with_the_state_on_disk(patched_data, saved_file):
    h = _star_hash()

    saved_list, outcome = tab.toggle_saved_item({"hash": h, "n": 1})

    assert outcome == f"1|{h}|1"
    assert [record["title"] for record in _on_disk(saved_file)] == ["X"]
    assert "X" in _texts(saved_list)  # the Guardados subtab lists it
    saved_list, outcome = tab.toggle_saved_item({"hash": h, "n": 2})
    assert outcome == f"2|{h}|0"
    assert _on_disk(saved_file) == []
    assert "Todavía no has guardado nada" in _texts(saved_list)


def test_star_click_on_an_item_the_registry_lost_changes_nothing(patched_data, saved_file):
    """The registry is rebuilt on every render, so it is gone after a server restart: the answer puts the star back."""
    saved_list, outcome = tab.toggle_saved_item({"hash": "deadbeef", "n": 3})

    assert outcome == "3|deadbeef|0"
    assert not saved_file.exists()


def test_failed_star_write_answers_with_the_state_on_disk(patched_data, saved_file, monkeypatch):
    def failing_toggle(record):
        raise OSError("disk full")

    monkeypatch.setattr(saved_items, "toggle_saved", failing_toggle)
    h = _star_hash()

    saved_list, outcome = tab.toggle_saved_item({"hash": h, "n": 4})

    assert outcome == f"4|{h}|0"  # the optimistic flip of the star is undone
    assert not saved_file.exists()


@pytest.mark.parametrize("payload", [None, {}, {"n": 1}, {"hash": ""}, "x", 7, [{"hash": "deadbeef"}]])
def test_malformed_star_request_is_ignored(patched_data, saved_file, payload):
    assert tab.toggle_saved_item(payload) == (dash.no_update, dash.no_update)
    assert not saved_file.exists()


def test_star_callback_reads_the_request_store_and_answers_in_the_outcome_element():
    app = dash.Dash("test-kg-star")
    tab.register_knowledge_garden_callbacks(app)

    listening = [e for e in app._callback_list if _listens(e, tab.KG_SAVE_REQUEST_ID, "data")]
    assert len(listening) == 1
    (entry,) = listening
    assert entry["output"] == f"..kg-saved-results.children...{tab.KG_SAVE_OUTCOME_ID}.children.."
    assert entry["prevent_initial_call"] is True


def test_kg_state_js_flips_stars_through_the_request_store():
    """The callback is only reached through the script: both must agree on the ids."""
    js = _JS_PATH.read_text(encoding="utf-8")

    assert f'"{tab.KG_SAVE_REQUEST_ID}"' in js and f'"{tab.KG_SAVE_OUTCOME_ID}"' in js
    assert "set_props" in js and "data-kg-hash" in js and "data-kg-saved" in js
    assert "Quitar de guardados" in js and "Guardar para luego" in js  # same titles as the server renders


def test_every_controller_listens_to_its_own_activate_store():
    app = dash.Dash("test-kg-lazy-wiring")
    tab.register_knowledge_garden_callbacks(app)

    for tab_def in tab.KNOWLEDGE_TAB_DEFINITIONS:
        search_id = tab._knowledge_search_id(tab_def)
        entry = next(e for e in app._callback_list if f"{search_id}-results.children" in e["output"])
        assert _listens(entry, f"{search_id}-activate", "data")
        assert _listens(entry, search_id, "value")
        assert not _listens(entry, tab.KG_TABS_ID, "active_tab")  # otherwise every switch runs every controller
        assert entry["prevent_initial_call"] is True  # idle on insertion: the dispatcher says when to build
        for output in (f"{search_id}-results.children", f"{search_id}-page.data", f"{search_id}-view.data", f"{search_id}-view-toggle.children", f"{search_id}-page-info.children", f"{search_id}-prev.disabled", f"{search_id}-next.disabled"):
            assert output in entry["output"]
            assert sum(1 for e in app._callback_list if output in e["output"]) == 1  # single callback per output


# ---------------------------------------------------------------------------
# Loading: one sort per cache period, a real Refresh, no shared-dict mutation
# ---------------------------------------------------------------------------


def _write_source(path, items):
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


def _repository(path, source_name="LessWrong"):
    return tab.KnowledgeGardenRepository(str(path), source_name)


class _FakeRepo:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def get(self, force_refresh=False):
        self.calls.append(force_refresh)
        return self.items


def test_repositories_cover_every_configured_source():
    assert set(tab._repositories) == set(KNOWLEDGE_SOURCES_CONFIG)
    for key, repo in tab._repositories.items():
        assert (repo.data_path, repo.source_name) == (tab.Path(KNOWLEDGE_SOURCES_CONFIG[key]["path"]), KNOWLEDGE_SOURCES_CONFIG[key]["name"])


def test_refresh_button_reaches_the_repositories(monkeypatch):
    repos = {key: _FakeRepo([]) for key in KNOWLEDGE_SOURCES_CONFIG}
    monkeypatch.setattr(tab, "_repositories", repos)

    tab._load_all_knowledge_data()
    tab._load_all_knowledge_data(force_refresh=True)

    assert all(repo.calls == [False, True] for repo in repos.values())


def test_a_broken_source_is_empty_instead_of_failing_the_others(monkeypatch, tmp_path):
    broken = tab.KnowledgeGardenRepository(str(tmp_path / "missing.json"), "Broken")
    healthy = _repository(_write_source(tmp_path / "ok.json", [_ITEMS[0]]))
    monkeypatch.setattr(tab, "_repositories", {"broken": broken, "lesswrong": healthy})

    data = tab._load_all_knowledge_data()

    assert data["broken"] == []
    assert [item["title"] for item in data["lesswrong"]] == ["Post 00"]


def test_forced_get_bypasses_the_module_cache_and_says_so(monkeypatch):
    loads = []
    monkeypatch.setattr(tab, "_load_all_knowledge_data", lambda **kwargs: loads.append(kwargs) or {"lesswrong": []})
    tab._knowledge_cache.invalidate()

    tab.get_all_knowledge_data()
    tab.get_all_knowledge_data()  # fresh: served by the 60 s module cache
    tab.get_all_knowledge_data(force_refresh=True)

    assert loads == [{}, {"force_refresh": True}]


def test_repository_returns_copies_sorted_newest_first_with_the_sort_date(tmp_path):
    path = _write_source(tmp_path / "source.json", _ITEMS)  # oldest first in the file

    items = _repository(path).get()

    assert [item["title"] for item in items[:2]] == ["Post 59", "Post 58"]
    assert all("_kg_sort" in item and item["source_display_name"] == "LessWrong" for item in items)
    assert items[0] is not _ITEMS[-1]  # a copy: tagging an item never reaches the parsed file
    assert json.loads(path.read_text(encoding="utf-8")) == _ITEMS  # …and the file is never rewritten


def test_repository_caches_until_the_file_changes_or_a_forced_refresh(tmp_path):
    path = _write_source(tmp_path / "source.json", [_ITEMS[0]])
    repo = _repository(path)

    assert [item["title"] for item in repo.get()] == ["Post 00"]
    assert [item["title"] for item in repo.get()] == ["Post 00"]  # the file did not change: served from the cache
    _write_source(path, [_ITEMS[0], _ITEMS[1]])
    assert [item["title"] for item in repo.get()] == ["Post 01", "Post 00"]  # an ETL write is seen at the next request, not an hour later (T-197)
    _write_source(path, [_ITEMS[1]])
    assert [item["title"] for item in repo.get(force_refresh=True)] == ["Post 01"]  # and Refresh never serves the cache


def test_repository_names_a_bare_item_after_its_source(tmp_path):
    path = _write_source(tmp_path / "source.json", [{"title": "Bare", "url": "http://example.com/bare"}])

    assert _repository(path, "Podcasts").get()[0]["source_display_name"] == "Podcasts"
    assert tab.KnowledgeGardenRepository(str(path)).get()[0]["source_display_name"] == "source"  # no name given: the file's own


def test_repository_drops_junk_and_reads_wrapped_lists(tmp_path):
    path = tmp_path / "source.json"
    path.write_text(json.dumps({"items": [_ITEMS[0], "junk", None]}), encoding="utf-8")

    assert [item["title"] for item in _repository(path).get()] == ["Post 00"]
    path.write_text(json.dumps({"title": "Single", "url": "http://example.com/single", "published": "2026-08-05T10:00:00"}), encoding="utf-8")
    assert [item["title"] for item in _repository(path).get(force_refresh=True)] == ["Single"]


def test_repository_parses_each_sort_date_once_per_load(tmp_path, monkeypatch):
    repo = _repository(_write_source(tmp_path / "source.json", _ITEMS))
    parsed = []
    real_parse = tab.get_sortable_date

    def counting(article):
        parsed.append(article["title"])
        return real_parse(article)

    monkeypatch.setattr(tab, "get_sortable_date", counting)

    first, second = repo.get(), repo.get()

    assert len(parsed) == len(_ITEMS)  # once per item on load…
    assert first is second  # …then the same list is served from the cache


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("<!-- SC_OFF --><div class=\"md\"><p>Before AI, open source\nwas a place</div>", "Before AI, open source was a place"),  # Reddit selftext
        ("<table> <tr> <td> <a href=\"https://example.com/x\">a link</a>", "a link"),
        ("Pliable &amp; portable &lt;3", "Pliable & portable <3"),
        ("Plain text with no markup", "Plain text with no markup"),
        ("a < b and 3 > 2", "a < b and 3 > 2"),  # a lone comparison sign is not a tag
    ],
)
def test_card_snippets_are_plain_text(raw, expected):
    assert tab._plain_text(raw) == expected


def test_card_shows_the_snippet_without_markup(patched_data):
    patched_data["lesswrong"][0].update({"summary": "<!-- SC_OFF --><div class=\"md\"><p>Build it &amp; ship it", "source_display_name": "LessWrong"})

    card = tab._knowledge_card(patched_data["lesswrong"][0])

    assert "Build it & ship it" in _texts(card)
    assert "<" not in _texts(card) and "SC_OFF" not in _texts(card)


def test_build_uses_the_sort_date_computed_at_load(patched_data, monkeypatch):
    for item in patched_data["lesswrong"]:
        item["_kg_sort"] = tab.get_sortable_date(item)

    def must_not_parse(article):
        raise AssertionError("the sort date must come from the load, not be parsed again on every render")

    monkeypatch.setattr(tab, "get_sortable_date", must_not_parse)

    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong")

    assert len(_with_attribute(content, "data-kg-date")) == PAGE


def test_build_still_sorts_items_that_come_without_a_sort_date(patched_data):
    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong")

    assert "Post 59" in _texts(_with_attribute(content, "data-kg-date")[0])


def test_build_does_not_mutate_the_cached_items(patched_data):
    before = [dict(item) for item in patched_data["lesswrong"]]

    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong", view="cards")

    assert patched_data["lesswrong"] == before
    assert "LessWrong" in _texts(content)  # the Source badge still names the source
