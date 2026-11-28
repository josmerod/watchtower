"""The Scavenging tab builds one subtab at a time, when it is opened (T-170), and its dead source says so (T-157).

The tab used to render the first page of every source and put every file whole into a ``dcc.Store``: with the
production sources the first response was 3.9 MB, for the one subtab in view. Now the layout holds a shell per
source (search bar, pager, empty results container) and a dispatcher on the subtab bar marks the open subtab; only
its controller builds a page, and nothing is sent again when a subtab is opened a second time.

The callbacks are called the way the browser calls them, POST /_dash-update-component on a Dash app through Flask's
test client, so what ``dash.ctx`` holds is Dash's own and not a mock. What the renderer does on top (it refuses to
fire a callback whose input is not in the page) is covered by keeping every input of every controller in the layout.
Fixtures only: the source files live under tmp_path.
"""

import json
import re
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pytest
from dash import dcc

import src.web.dashboard.components.scavenging_tab as tab

ANIME, AUDIBLE, COURSES, EPIC = "anime", "audible", "courses", "epic_free"
SID_A, SID_B = "scavenging-search-anime", "scavenging-search-audible"
SID_COURSES = "scavenging-search-courses"
TAB_BAR = "scavenging-main-tabs"
PAUSED_NOTE = "No service: the endpoint closed."


# ---------------------------------------------------------------------------
# Fixtures and small readers of component trees
# ---------------------------------------------------------------------------


def _records(count: int, prefix: str = "Item") -> list[dict]:
    """``count`` records whose dates rise strictly with their index: newest first is the reverse of the file order."""
    return [
        {
            "title": f"{prefix} {n:03d}",
            "link": f"https://example.com/{prefix}/{n:03d}",
            "published": f"2026-11-{1 + n // 24:02d}T{n % 24:02d}:00:00",
            "summary": f"summary {prefix} {n:03d}",
            "category": "any",
            "source": "any",
        }
        for n in range(count)
    ]


def _write(path: Path, payload) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _canonical(root: Path, key: str) -> Path:
    return root / key / "output" / f"{key}_latest.json"


def _config(key: str, path: Path, label: str | None = None, **extra) -> dict:
    return {"key": key, "label": label or key.capitalize(), "category": key, "paths": [str(path)], **extra}


def _walk(node):
    """Yield every node of a Dash component tree, strings included."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)


def _by_id(root, component_id) -> list:
    return [node for node in _walk(root) if getattr(node, "id", None) == component_id]


def _ids(root) -> set[str]:
    return {node.id for node in _walk(root) if isinstance(getattr(node, "id", None), str)}


def _texts(root) -> str:
    return " ".join(node for node in _walk(root) if isinstance(node, str))


def _tables(root) -> list:
    return [node for node in _walk(root) if isinstance(node, dbc.Table)]


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    """Three sources: anime (5 records, one page), audible (250 records, three pages) and courses (no file yet)."""
    _write(_canonical(tmp_path, ANIME), _records(5, "Nyaa"))
    _write(_canonical(tmp_path, AUDIBLE), _records(250))
    monkeypatch.setattr(
        tab, "SCAVENGING_SOURCES", [_config(ANIME, _canonical(tmp_path, ANIME), "Anime"), _config(COURSES, _canonical(tmp_path, COURSES), "Courses"), _config(AUDIBLE, _canonical(tmp_path, AUDIBLE), "Audible")]
    )
    return tmp_path


@pytest.fixture
def with_paused(tmp_path, monkeypatch) -> Path:
    """anime and audible live; epic_free is paused, with the file its dead ETL left behind still on disk."""
    _write(_canonical(tmp_path, ANIME), _records(5, "Nyaa"))
    _write(_canonical(tmp_path, AUDIBLE), _records(5))
    _write(_canonical(tmp_path, EPIC), _records(3, "Old game"))
    monkeypatch.setattr(
        tab,
        "SCAVENGING_SOURCES",
        [_config(ANIME, _canonical(tmp_path, ANIME), "Anime"), _config(AUDIBLE, _canonical(tmp_path, AUDIBLE), "Audible"), _config(EPIC, _canonical(tmp_path, EPIC), "Epic free", paused=PAUSED_NOTE)],
    )
    return tmp_path


def _app(layout=None) -> dash.Dash:
    app = dash.Dash("test-scavenging-lazy", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = layout if layout is not None else tab.render_scavenging_tab()
    tab.register_scavenging_callbacks(app)
    return app


# ---------------------------------------------------------------------------
# Calling the callbacks as the browser does
# ---------------------------------------------------------------------------


def _callback(app, marker: str) -> dict:
    """The callback whose output spec contains ``marker``, as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if marker in cb["output"])


def _output_ids(cb) -> list[str]:
    """Component ids of what a callback writes, read from the spec string the app lists."""
    spec = str(cb["output"])
    if spec.startswith(".."):
        return [part.rsplit(".", 1)[0] for part in spec[2:-2].split("...")]
    return [spec.rsplit(".", 1)[0]]


def _outputs_of(cb) -> list[dict]:
    """What a callback writes, as ``id.prop`` parts: several for a multi-output, one otherwise.

    The output string of a duplicate output carries its ``@…`` suffix; the property the request lists does not.
    """
    if cb["output"].startswith(".."):
        return [dict(zip(("id", "property"), part.rsplit(".", 1), strict=True)) for part in cb["output"][2:-2].split("...")]
    ident, prop = re.sub(r"@\w+$", "", cb["output"]).rsplit(".", 1)
    return [{"id": ident, "property": prop}]


def _post(app, cb, inputs: list, changed=(), states=None) -> dict:
    """Call ``cb`` as the browser does and return the outputs it changed, as ``id.prop`` keys: none when it prevented the update."""
    outputs = _outputs_of(cb)
    # A single output goes as one dict: given a list of one, the server takes it for a group and wants a list back.
    listed = outputs if cb["output"].startswith("..") else outputs[0]
    body = {"output": cb["output"], "outputs": listed, "inputs": inputs, "changedPropIds": list(changed), "state": states if states is not None else [{**spec, "value": None} for spec in cb["state"]]}
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code in (200, 204), response.get_data(as_text=True)[-800:]  # 204: every output was prevented
    if response.status_code == 204:
        return {}
    answered = response.get_json()["response"]
    changed_props = {}
    for output in outputs:
        # Dash nests each value under the id of its component: {"the-id": {"data": 1}}.
        value = answered.get(output["id"])
        if isinstance(value, dict) and output["property"] in value:
            value = value[output["property"]]
        if value is not None:
            changed_props[f"{output['id']}.{output['property']}"] = value
    return changed_props


def _entry(component_id: str, prop: str, value) -> dict:
    return {"id": component_id, "property": prop, "value": value}


def _open(app, subtab_id: str) -> dict:
    """The browser telling the dispatcher that the subtab bar now shows ``subtab_id``."""
    return _post(app, _callback(app, "-activate.data"), [_entry(TAB_BAR, "active_tab", subtab_id)], [f"{TAB_BAR}.active_tab"])


def _fire(app, search_id: str, *, term="", page=None, activate=0, clicks=(None, None), changed="") -> dict:
    """The controller of ``search_id`` with its inputs as they are, woken by ``changed`` (an ``id.prop`` key) or by nothing."""
    inputs = [_entry(search_id, "value", term), _entry(f"{search_id}-prev", "n_clicks", clicks[0]), _entry(f"{search_id}-next", "n_clicks", clicks[1]), _entry(f"{search_id}-activate", "data", activate)]
    return _post(app, _callback(app, f"{search_id}-results.children"), inputs, [changed] if changed else [], [_entry(f"{search_id}-page", "data", page)])


def _json_all(node):
    """Every dict of a component tree as Dash serialized it for the response."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _json_all(value)
    elif isinstance(node, list):
        for item in node:
            yield from _json_all(item)


def _json_text(node, shown: bool = False) -> str:
    """What Dash will show in a serialized component tree: the strings under a ``children`` key, not the other props."""
    if isinstance(node, str):
        return node if shown else ""
    if isinstance(node, list):
        return " ".join(_json_text(item, shown) for item in node)
    if isinstance(node, dict):
        return " ".join(_json_text(value, shown or key == "children") for key, value in node.items() if key in ("children", "props"))
    return ""


def _json_rows(node) -> int:
    """Rows of the serialized tables in ``node``: one ``Tr`` per row, and one more per table for the header."""
    nodes = list(_json_all(node))
    return sum(node.get("type") == "Tr" for node in nodes) - sum(node.get("type") == "Table" for node in nodes)


def _json_prop(node, prop: str):
    return node["props"].get(prop)


# ---------------------------------------------------------------------------
# Layout: a shell per source, nothing of the records
# ---------------------------------------------------------------------------


def test_the_layout_holds_a_shell_per_source_and_neither_record_nor_table(root):
    layout = tab.render_scavenging_tab()

    assert _tables(layout) == []
    assert "Nyaa 004" not in _texts(layout) and "summary Item" not in _texts(layout)
    for search_id in (SID_A, SID_B):
        assert _by_id(layout, f"{search_id}-data") == []  # the whole file no longer travels with the layout
        assert _by_id(layout, f"{search_id}-page")[0].data is None  # empty until the page is first built
        assert _by_id(layout, f"{search_id}-activate")[0].data == 0
        assert _texts(_by_id(layout, f"{search_id}-results")[0]) == "Loading…"
    assert _by_id(layout, SID_COURSES) == []  # no file yet, so no subtab


def _layout_bytes(tmp_path, monkeypatch, count: int) -> int:
    path = tmp_path / AUDIBLE / "output" / "audible_releases_latest.json"
    _write(path, _records(count))
    monkeypatch.setattr(tab, "SCAVENGING_SOURCES", [_config(AUDIBLE, path)])
    return len(_app().server.test_client().get("/_dash-layout").data)


def test_the_size_of_the_layout_does_not_follow_the_size_of_the_sources(tmp_path, monkeypatch):
    small = _layout_bytes(tmp_path, monkeypatch, 5)
    large = _layout_bytes(tmp_path, monkeypatch, 250)

    assert small == large
    assert large < 40_000  # one page of 100 rows is about 170,000 bytes: no table is in there


def test_subtabs_keep_their_labels_ids_order_and_the_first_stays_open(tmp_path, monkeypatch):
    sources = []
    for key, label in ((AUDIBLE, "Audible"), (ANIME, "Anime"), ("gumroad_free", "Gumroad free")):
        path = tmp_path / key / "output" / "latest.json"
        _write(path, _records(5))
        sources.append(_config(key, path, label))
    monkeypatch.setattr(tab, "SCAVENGING_SOURCES", sources)

    bar = _by_id(tab.render_scavenging_tab(), TAB_BAR)[0]

    assert bar.id == "scavenging-main-tabs"
    assert [subtab.label for subtab in bar.children] == ["Anime", "Audible", "Gumroad free"]  # by key, as before
    assert [subtab.tab_id for subtab in bar.children] == ["tab-scavenging-anime", "tab-scavenging-audible", "tab-scavenging-gumroad_free"]
    assert bar.active_tab == "tab-scavenging-anime"


def test_search_boxes_wait_for_a_pause_in_typing(root):
    boxes = [node for node in _walk(tab.render_scavenging_tab()) if isinstance(node, dbc.Input) and str(getattr(node, "id", "")).startswith("scavenging-search-")]

    assert len(boxes) == 2
    assert {box.debounce for box in boxes} == {tab.SCAVENGING_SEARCH_DEBOUNCE_MS}


def test_a_subtab_that_fits_on_one_page_keeps_prev_and_next_in_the_page(root):
    # Five records show no pager, but its buttons have to exist: the controller listens to them, and Dash refuses to
    # fire a callback whose input is not in the page. While the bar was removed for one page of records, the search
    # box of those subtabs did nothing.
    pager = _by_id(tab.render_scavenging_tab(), f"{SID_A}-pager")[0]

    assert [button.id for button in _walk(pager) if isinstance(button, dbc.Button)] == [f"{SID_A}-prev", f"{SID_A}-next"]


def test_every_input_of_every_controller_is_in_the_layout(root):
    layout = tab.render_scavenging_tab()
    app = _app(layout)
    in_page = _ids(layout)
    controllers = [cb for cb in app._callback_list if "-results.children" in cb["output"]]

    assert {cb["inputs"][0]["id"] for cb in controllers} == {SID_A, SID_B, SID_COURSES}  # one per live source, file or not
    for cb in controllers:
        if cb["inputs"][0]["id"] not in in_page:
            continue  # courses: no file, so no subtab to control yet
        assert all(spec["id"] in in_page for spec in cb["inputs"] + cb["state"]), cb["output"]


# ---------------------------------------------------------------------------
# Wiring: one dispatcher on the bar, idle until its subtab is opened
# ---------------------------------------------------------------------------


def test_only_the_dispatcher_listens_to_the_subtab_bar(root):
    app = _app()
    listening = [cb for cb in app._callback_list if {"id": TAB_BAR, "property": "active_tab"} in cb["inputs"]]

    assert len(listening) == 1
    assert _output_ids(listening[0]) == [f"{SID_A}-activate", f"{SID_COURSES}-activate", f"{SID_B}-activate"]  # every live source, file or not
    assert listening[0]["prevent_initial_call"] is False  # it also runs when the tab first renders, to open the subtab in view


def test_activation_marks_only_the_open_subtab(root):
    assert tab._scavenging_activation("tab-scavenging-anime") == (1, dash.no_update, dash.no_update)
    assert tab._scavenging_activation("tab-scavenging-courses") == (dash.no_update, 1, dash.no_update)
    assert tab._scavenging_activation("tab-scavenging-elsewhere") == (dash.no_update, dash.no_update, dash.no_update)


def test_opening_the_tab_builds_the_first_subtab_and_only_that_one(root):
    app = _app()

    assert _open(app, "tab-scavenging-anime") == {f"{SID_A}-activate.data": 1}

    built = _fire(app, SID_A, activate=1, changed=f"{SID_A}-activate.data")
    assert _json_rows(built[f"{SID_A}-results.children"]) == 5
    assert "Nyaa 004" in _json_text(built[f"{SID_A}-results.children"]) and "Nyaa 003" in _json_text(built[f"{SID_A}-results.children"])  # newest first
    assert built[f"{SID_A}-page.data"] == 1
    assert _json_prop(built[f"{SID_A}-pager.children"], "hidden") is True  # five records fit on one page: no pager shown

    # The other shell arrives in the same response as what its controller writes, and the dispatcher leaves its store
    # alone; shown its new components, that controller has nothing to do.
    assert _fire(app, SID_B) == {}


def test_a_subtab_is_built_when_it_is_first_opened_and_kept_afterwards(root):
    app = _app()
    _open(app, "tab-scavenging-anime")
    _fire(app, SID_A, activate=1, changed=f"{SID_A}-activate.data")

    assert _open(app, "tab-scavenging-audible") == {f"{SID_B}-activate.data": 1}  # Anime's store is left alone, so its controller is not woken

    first = _fire(app, SID_B, activate=1, changed=f"{SID_B}-activate.data")
    assert _json_rows(first[f"{SID_B}-results.children"]) == tab.MAX_ITEMS_PER_TAB
    assert "Item 249" in _json_text(first[f"{SID_B}-results.children"]) and "Item 149" not in _json_text(first[f"{SID_B}-results.children"])
    assert _json_text(first[f"{SID_B}-pager.children"]) == "← Prev Showing 100 of 250 · Page 1 of 3 Next →"
    assert first[f"{SID_B}-page.data"] == 1

    # Back to a subtab that already has its table, with the stores as the page holds them: the dispatcher leaves
    # every store alone, so nothing is sent again. (``_open`` sends no states: asked blind, the dispatcher answers 1.)
    stores = [_entry(f"{SID_A}-activate", "data", 1), _entry(f"{SID_COURSES}-activate", "data", None), _entry(f"{SID_B}-activate", "data", 1)]
    assert _post(app, _callback(app, "-activate.data"), [_entry(TAB_BAR, "active_tab", "tab-scavenging-audible")], [f"{TAB_BAR}.active_tab"], stores) == {}
    assert _open(app, "tab-scavenging-audible") == {f"{SID_B}-activate.data": 1}
    assert _fire(app, SID_B, activate=1, page=1, changed=f"{SID_B}-activate.data") == {}  # and a controller woken by its own store stays idle


def test_next_prev_and_search_go_through_the_endpoint(root):
    app = _app()
    _open(app, "tab-scavenging-audible")
    _fire(app, SID_B, activate=1, changed=f"{SID_B}-activate.data")

    second = _fire(app, SID_B, activate=1, page=1, clicks=(None, 1), changed=f"{SID_B}-next.n_clicks")
    assert "Item 149" in _json_text(second[f"{SID_B}-results.children"]) and "Item 249" not in _json_text(second[f"{SID_B}-results.children"])
    assert second[f"{SID_B}-page.data"] == 2
    assert _json_text(second[f"{SID_B}-pager.children"]) == "← Prev Showing 100 of 250 · Page 2 of 3 Next →"

    third = _fire(app, SID_B, activate=1, page=2, clicks=(None, 2), changed=f"{SID_B}-next.n_clicks")
    assert _json_rows(third[f"{SID_B}-results.children"]) == 50
    assert "Item 000" in _json_text(third[f"{SID_B}-results.children"])
    assert third[f"{SID_B}-page.data"] == 3
    assert _json_text(third[f"{SID_B}-pager.children"]) == "← Prev Showing 50 of 250 · Page 3 of 3 Next →"

    back = _fire(app, SID_B, activate=1, page=3, clicks=(1, 2), changed=f"{SID_B}-prev.n_clicks")
    assert back[f"{SID_B}-page.data"] == 2

    # A search starts over on the first page, even from the last one.
    found = _fire(app, SID_B, term="Item 12", activate=1, page=3, clicks=(1, 2), changed=f"{SID_B}.value")
    assert found[f"{SID_B}-page.data"] == 1
    assert _json_rows(found[f"{SID_B}-results.children"]) == 10
    assert "⛏️ Found 10 items matching 'Item 12'" in _json_text(found[f"{SID_B}-results.children"])
    assert _json_prop(found[f"{SID_B}-pager.children"], "hidden") is True

    many = _fire(app, SID_B, term="summary", activate=1, page=1, clicks=(1, 2), changed=f"{SID_B}.value")
    assert many[f"{SID_B}-page.data"] == 1
    assert _json_text(many[f"{SID_B}-pager.children"]) == "← Prev Showing 100 of 250 · Page 1 of 3 Next →"


def test_the_search_box_of_a_subtab_without_pages_works(root):
    # Regression. The pager of a source of 100 records or fewer used to be left out of the page, and with it both of
    # its buttons. The controller listens to them, and Dash never fires a callback whose Input is not in the page, so
    # the search box of those subtabs did nothing, from T-150 until this rebuild.
    app = _app()
    _open(app, "tab-scavenging-anime")
    _fire(app, SID_A, activate=1, changed=f"{SID_A}-activate.data")

    found = _fire(app, SID_A, term="Nyaa 003", activate=1, page=1, changed=f"{SID_A}.value")
    assert _json_rows(found[f"{SID_A}-results.children"]) == 1
    assert "⛏️ Found 1 items matching 'Nyaa 003'" in _json_text(found[f"{SID_A}-results.children"])
    assert "Nyaa 002" not in _json_text(found[f"{SID_A}-results.children"])
    assert _json_prop(found[f"{SID_A}-pager.children"], "hidden") is True  # and the buttons are still in the page


def test_the_clear_button_empties_the_box_and_that_builds_the_first_page_again(root):
    app = _app()
    _open(app, "tab-scavenging-audible")
    _fire(app, SID_B, activate=1, changed=f"{SID_B}-activate.data")
    _fire(app, SID_B, term="Item 12", activate=1, page=1, changed=f"{SID_B}.value")

    # The clear button is a callback of its own; it writes the search box, and the controller runs on the new value.
    assert _post(app, _callback(app, f"{SID_B}.value"), [_entry(f"{SID_B}-clear", "n_clicks", 1)], [f"{SID_B}-clear.n_clicks"]) == {f"{SID_B}.value": ""}
    cleared = _fire(app, SID_B, activate=1, page=1, clicks=(1, 1), changed=f"{SID_B}.value")
    assert _json_rows(cleared[f"{SID_B}-results.children"]) == tab.MAX_ITEMS_PER_TAB
    assert "Found" not in _json_text(cleared[f"{SID_B}-results.children"])
    assert cleared[f"{SID_B}-page.data"] == 1


# ---------------------------------------------------------------------------
# Sources that change under the tab
# ---------------------------------------------------------------------------


def test_a_source_whose_file_appears_later_gets_its_subtab_and_its_controller(root):
    app = _app()  # registered while courses has no file
    assert SID_COURSES not in _ids(tab.render_scavenging_tab())

    _write(_canonical(root, COURSES), _records(7, "Course"))
    assert SID_COURSES in _ids(tab.render_scavenging_tab())  # the tab renders it from now on
    assert _open(app, "tab-scavenging-courses") == {f"{SID_COURSES}-activate.data": 1}  # and the dispatcher registered at startup already knew it
    built = _fire(app, SID_COURSES, activate=1, changed=f"{SID_COURSES}-activate.data")
    assert _json_rows(built[f"{SID_COURSES}-results.children"]) == 7


def test_an_unreadable_file_shows_the_quiet_empty_state_and_no_loading_pager(tmp_path, monkeypatch):
    path = tmp_path / ANIME / "output" / "anime_rss_entries.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(tab, "SCAVENGING_SOURCES", [_config(ANIME, path)])
    app = _app()
    _open(app, "tab-scavenging-anime")

    built = _fire(app, SID_A, activate=1, changed=f"{SID_A}-activate.data")
    assert "No data loaded." in _json_text(built[f"{SID_A}-results.children"])
    assert "Loading" not in _json_text(built[f"{SID_A}-pager.children"])
    assert _json_prop(built[f"{SID_A}-pager.children"], "hidden") is True
    assert built[f"{SID_A}-page.data"] == 1


# ---------------------------------------------------------------------------
# A paused source: its subtab stays and says why it is empty
# ---------------------------------------------------------------------------


def test_a_paused_source_keeps_its_subtab_with_a_line_saying_why_it_is_empty(with_paused):
    layout = tab.render_scavenging_tab()
    bar = _by_id(layout, TAB_BAR)[0]

    assert [subtab.tab_id for subtab in bar.children] == ["tab-scavenging-anime", "tab-scavenging-audible", "tab-scavenging-epic_free"]  # where its key sorts, as before
    assert bar.children[-1].label == "Epic free"
    assert _texts(bar.children[-1]) == PAUSED_NOTE
    assert _tables(bar.children[-1]) == [] and "scavenging-search-epic_free" not in _ids(layout)  # no search box, no pager, no stores
    assert "Old game" not in _texts(layout)


def test_a_paused_source_is_not_read_even_though_its_file_is_there(with_paused):
    assert tab.get_scavenging_data(EPIC) == []
    assert EPIC not in tab.discover_categories()


def test_a_paused_source_gets_no_controller_and_cannot_be_activated(with_paused):
    app = _app()

    assert not any("scavenging-search-epic_free" in str(cb["output"]) for cb in app._callback_list)
    assert tab._scavenging_activation("tab-scavenging-epic_free") == (dash.no_update, dash.no_update)
    assert _open(app, "tab-scavenging-epic_free") == {}


def test_without_a_live_file_the_tab_says_so(tmp_path, monkeypatch):
    path = tmp_path / EPIC / "output" / "latest.json"
    _write(path, _records(3))
    monkeypatch.setattr(tab, "SCAVENGING_SOURCES", [_config(EPIC, path, "Epic free", paused=PAUSED_NOTE)])

    assert "No scavenging data found" in _texts(tab.render_scavenging_tab()) and PAUSED_NOTE not in _texts(tab.render_scavenging_tab())


def test_the_controllers_stay_idle_when_their_shells_arrive(root):
    # Everything the controller takes as an input is new at the same time as what it writes, so Dash shows it the
    # inserted components once: that is not a trigger, with or without the dispatcher having marked the subtab.
    app = _app()
    assert _fire(app, SID_A) == {}
    assert _fire(app, SID_A, activate=1) == {}


def test_stores_are_real_dcc_stores(root):
    stores = [node for node in _walk(tab.render_scavenging_tab()) if isinstance(node, dcc.Store)]

    # Courses has no subtab yet, but its activate store is there: the dispatcher writes it (see the test below).
    assert {store.id for store in stores} == {f"{SID_A}-page", f"{SID_A}-activate", f"{SID_B}-page", f"{SID_B}-activate", f"{SID_COURSES}-activate"}


def test_every_output_of_every_callback_that_can_run_is_in_the_layout(root):
    # Found in the browser, after every test here passed. Dash refuses to run a callback while any of its Outputs
    # is missing from the page, exactly as for an Input, and nothing says so outside the console. The dispatcher
    # lists the store of every live source, file or not: when only the rendered subtabs carried theirs, it never
    # ran where a source had no file, and no subtab was built on opening the tab.
    layout = tab.render_scavenging_tab()
    in_page = _ids(layout)
    app = _app(layout)

    assert all(component_id in in_page for component_id in _output_ids(_callback(app, "-activate.data")))
    # The controller of a source without a subtab has none of its controls in the page, so nothing can set it going.
    with_a_subtab = [cb for cb in app._callback_list if "-results.children" in cb["output"] and cb["inputs"][0]["id"] in in_page]
    assert len(with_a_subtab) == 2
    for cb in with_a_subtab:
        assert all(component_id in in_page for component_id in _output_ids(cb)), cb["output"]
