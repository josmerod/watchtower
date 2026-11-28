"""The Learning tab builds one subtab at a time, when it is opened (T-177).

Every subtab is rendered as a shell (its controls, a pager, an empty table container) and painted by its own controller the
first time it is opened; a dispatcher on the subtab bar's ``active_tab`` marks the open subtab. The layout used to carry the
first page of every table, so opening the tab cost seven requests and about 1.4 MiB.

The controllers are called the way the browser calls them, POST /_dash-update-component on a Dash app through Flask's test
client. The dispatcher runs in the browser, so what is pinned here is what the app registers for it: its outputs, its input
and the state it reads, which is what keeps a subtab opened again from being built twice. What the renderer does on top (it
refuses to fire a callback whose input or output is not in the page) is covered by keeping every id of every callback in the
layout. Fixtures only: the in-memory catalogs are stubbed and the loader is kept away from data/.
"""

import re
import time

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import pytest
from dash import dcc, html

from src.web.dashboard.components import courses_tab

GLOBAL = "courses-global"
# The two Microsoft subtabs: the id of their search box, which prefixes their toggle and their store, and of their table
CERTS = courses_tab.MS_CREDENTIAL_KINDS["certs"]["search_id"]
CERTS_TABLE = courses_tab.MS_CREDENTIAL_KINDS["certs"]["table_id"]
APPLIED = courses_tab.MS_CREDENTIAL_KINDS["applied"]["search_id"]
APPLIED_TABLE = courses_tab.MS_CREDENTIAL_KINDS["applied"]["table_id"]
COURSERA_ROWS = 120
GCP_ROWS = courses_tab.CLOUD_PAGE_SIZE + 1
# What every provider contributes to the unified catalog (the retired credential stays out).
UNIFIED_ROWS = COURSERA_ROWS + 2 + 2 + GCP_ROWS

MS_ROWS = [
    {
        "title": "Microsoft Certified: Azure Administrator Associate",
        "category": "cert",
        "subject": "N/A",
        "level": "Intermediate",
        "roles": ["administrator"],
        "url": "https://example.com/ms/a",
        "detected_str": "2026-07-22",
        "retired": False,
        "retirement_date": None,
    },
    {
        "title": "Microsoft Certified: Old Certification",
        "category": "cert",
        "subject": "N/A",
        "level": "Beginner",
        "roles": "N/A",
        "url": "https://example.com/ms/old",
        "detected_str": "2026-03-01",
        "retired": True,
        "retirement_date": "2026-06-30",
    },
    {
        "title": "Microsoft Applied Skills: Develop AI agents on Azure",
        "category": "applied_skill",
        "subject": "Artificial Intelligence",
        "level": "Intermediate",
        "roles": ["ai-engineer"],
        "url": "https://example.com/ms/c",
        "detected_str": "2026-10-14",
        "retired": False,
        "retirement_date": None,
    },
]

# One marker per controller: an output only it writes.
CONTROLLERS = [
    f"{GLOBAL}-page-info.children",
    "coursera-pagination-info.children",
    "udemy-pagination-info.children",
    f"{CERTS_TABLE}.children",
    f"{APPLIED_TABLE}.children",
    "aws-skills-page-info.children",
    "gcp-skills-page-info.children",
]


# ---------------------------------------------------------------------------
# Component trees
# ---------------------------------------------------------------------------


def _walk(node):
    """Yield every node of a Dash component tree, strings included."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)


def _texts(root) -> list[str]:
    """The strings of a component tree, in order."""
    return [node for node in _walk(root) if isinstance(node, str)]


def _toggle_wrapper(layout, toggle_id) -> html.Div:
    """The div around a retired toggle: it is what hides the box when there is nothing to show."""
    return next(node for node in _walk(layout) if isinstance(node, html.Div) and getattr(node, "children", None) is not None and getattr(node.children, "id", None) == toggle_id)


def _by_id(root, component_id) -> list:
    return [node for node in _walk(root) if getattr(node, "id", None) == component_id]


def _ids(root) -> set[str]:
    return {node.id for node in _walk(root) if isinstance(getattr(node, "id", None), str)}


def _shown(node, under_children=False) -> list[str]:
    """The strings Dash will show in a serialized component tree: those under a ``children`` key, not the other props."""
    if isinstance(node, str):
        return [node] if under_children else []
    if isinstance(node, dict):
        return [text for key, value in node.items() for text in _shown(value, key == "children")]
    if isinstance(node, list):
        return [text for item in node for text in _shown(item, under_children)]
    return []


def _text(node) -> str:
    """What a callback's answer shows, blanks squeezed: a plain string as it is, a tree by the strings under its ``children``."""
    if isinstance(node, str):
        return " ".join(node.split())
    return " ".join(" ".join(_shown(node)).split())


def _rows(node, parent=None) -> int:
    """Rows of the tables in a serialized component tree: the ``Tr`` of every ``Tbody``, the header apart.

    A serialized component is ``{"type": ..., "props": {...}}``: what it holds sits under ``props``, so the parent a child
    sees is the type of the component its ``props`` belong to.
    """
    if isinstance(node, dict):
        kind = node.get("type")
        own = int(kind == "Tr" and parent == "Tbody")
        return own + sum(_rows(value, kind if key == "props" else parent) for key, value in node.items())
    if isinstance(node, list):
        return sum(_rows(item, parent) for item in node)
    return 0


# ---------------------------------------------------------------------------
# A Learning tab on stubbed catalogs
# ---------------------------------------------------------------------------


def _stub(monkeypatch, **frames):
    """Keep every catalog in memory: ``data/`` is never read and the loader never runs."""
    data = {key: pd.DataFrame() for key in courses_tab.ALL_COURSES_DATA} | frames
    monkeypatch.setattr(courses_tab, "ALL_COURSES_DATA", data)
    monkeypatch.setattr(courses_tab, "COURSES_DATA_LOADED", dict.fromkeys(data, True))
    monkeypatch.setattr(courses_tab, "_COURSES_LOADED_AT", time.time())
    monkeypatch.setattr(courses_tab, "load_all_courses_data", lambda: None)


def _frames() -> dict:
    """Coursera (eight pages), Microsoft (one retired certification), AWS and GCP (two pages); Udemy stays empty."""
    coursera = pd.DataFrame(
        [
            {
                "title": f"Course {n:03d}",
                "url": f"https://example.com/coursera/{n:03d}",
                "description": "A course",
                "institution": "Example",
                "subject": "AI",
                "language": "en",
                "duration": "1 hour",
                "start_date": None,
                "scraped_at": None,
                "is_free": n % 2 == 0,
                "certificate_offered": False,
            }
            for n in range(COURSERA_ROWS)
        ]
    )
    aws = pd.DataFrame(
        [
            {"title": "Introducción a AWS", "url": "https://example.com/aws/1", "language": "es", "description": "Beginner · 1 hour · Free", "detected_str": "2026-11-27"},
            {"title": "Introduction to Blockchain", "url": "https://example.com/aws/2", "language": "en", "description": "Beginner · 1 hour · Free", "detected_str": "2026-11-27"},
        ]
    )
    gcp = pd.DataFrame(
        [
            {
                "title": f"Lab {n:03d}",
                "url": f"https://example.com/gcp/{n:03d}",
                "language": "en",
                "course_type": "lab",
                "description": "Create a VPC",
                "duration": "1 hour",
                "level": "introductory",
                "detected_str": "2026-11-27",
            }
            for n in range(GCP_ROWS)
        ]
    )
    return {"coursera": coursera, "ms_skills": pd.DataFrame(MS_ROWS), "aws_skills": aws, "gcp_skills": gcp}


def _app(monkeypatch):
    """The Learning tab rendered on the stubbed catalogs, with its callbacks registered on a Dash app."""
    _stub(monkeypatch, **_frames())
    layout = courses_tab.render_courses_tab()
    app = dash.Dash("test-courses-lazy", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = layout
    courses_tab.register_courses_callbacks(app)
    return app, layout


# ---------------------------------------------------------------------------
# Calling the callbacks as the browser does
# ---------------------------------------------------------------------------


def _callback(app, marker: str) -> dict:
    """The callback whose output spec contains ``marker``, as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if marker in cb["output"])


def _outputs_of(cb) -> list[dict]:
    """What a callback writes, as ``id.prop`` parts: several for a multi-output, one otherwise."""
    if cb["output"].startswith(".."):
        return [dict(zip(("id", "property"), part.rsplit(".", 1), strict=True)) for part in cb["output"][2:-2].split("...")]
    ident, prop = re.sub(r"@\w+$", "", cb["output"]).rsplit(".", 1)
    return [{"id": ident, "property": prop}]


def _entry(component_id: str, prop: str, value) -> dict:
    return {"id": component_id, "property": prop, "value": value}


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
        # Dash nests each value under the id of its component: {"the-id": {"data": 1}}. A component written twice in one
        # answer keeps both props in that dict, and one left alone by no_update is simply not in it.
        value = answered.get(output["id"])
        if isinstance(value, dict):
            value = value.get(output["property"])
        if value is not None:
            changed_props[f"{output['id']}.{output['property']}"] = value
    return changed_props


def _fire(app, marker: str, values=None, *, activate=0, page=None, changed="") -> dict:
    """The controller that writes ``marker``, with its inputs as they are: ``activate`` is its subtab's activation store and ``page`` its page store."""
    cb = _callback(app, marker)
    values = {**(values or {})}
    for spec in cb["inputs"]:
        if spec["id"].endswith("-activate"):
            values[spec["id"]] = activate
    inputs = [_entry(spec["id"], spec["property"], values.get(spec["id"])) for spec in cb["inputs"]]
    states = [_entry(spec["id"], spec["property"], page) for spec in cb["state"]]
    return _post(app, cb, inputs, [changed] if changed else [], states)


# ---------------------------------------------------------------------------
# The layout: shells, never tables
# ---------------------------------------------------------------------------


def test_the_layout_holds_shells_and_activation_stores_but_no_table(monkeypatch):
    _, layout = _app(monkeypatch)

    assert not [node for node in _walk(layout) if isinstance(node, dbc.Table)]
    containers = [f"{prefix}-table-container" for prefix in ("coursera", "udemy", "aws-skills", "gcp-skills")] + [CERTS_TABLE, APPLIED_TABLE, f"{GLOBAL}-results"]
    for container_id in containers:
        assert _texts(_by_id(layout, container_id)[0].children) == ["Cargando…"], container_id

    stores = {node.id: node for node in _walk(layout) if isinstance(node, dcc.Store)}
    prefixes = [prefix for _, prefix in courses_tab.COURSES_SUBTABS]
    assert set(stores) == {f"{prefix}-activate" for prefix in prefixes} | {"courses-global-page", "coursera-page", "udemy-page", "aws-skills-page", "gcp-skills-page"}
    assert all(stores[f"{prefix}-activate"].data == 0 for prefix in prefixes)  # nothing is activated before the dispatcher runs
    # A page store is empty until its controller has built a page: that is how a controller knows it has not run yet.
    assert all(getattr(stores[page_id], "data", None) is None for page_id in ("courses-global-page", "coursera-page", "udemy-page", "aws-skills-page", "gcp-skills-page"))


def test_a_subtab_without_data_says_so_and_keeps_its_shell_hidden(monkeypatch):
    """The renderer refuses a callback while one of its ids is missing: an empty subtab keeps everything its controller uses."""
    app, layout = _app(monkeypatch)  # Udemy is empty here

    (udemy_tab,) = [node for node in _walk(layout) if isinstance(node, dbc.Tab) and node.tab_id == "tab-udemy"]
    message, hidden = udemy_tab.children.children
    assert "No Udemy courses data currently available (file might be empty)." in message.children
    assert hidden.hidden is True
    assert {"udemy-table-container", "udemy-search-input", "udemy-page", "udemy-activate", "udemy-page-input", "udemy-next-btn", "udemy-pagination-info"} <= _ids(hidden)

    # Opened all the same, its controller answers an empty state into the hidden container
    page = _fire(app, "udemy-pagination-info.children", activate=1)
    assert _text(page["udemy-table-container.children"]) == "No Udemy courses match your filters."


def test_a_catalog_that_failed_to_load_says_so_and_keeps_its_shell_hidden(monkeypatch):
    _stub(monkeypatch, coursera=pd.DataFrame([{"title": "A course"}]))
    monkeypatch.setitem(courses_tab.COURSES_DATA_LOADED, "coursera", False)

    (coursera_tab,) = [node for node in _walk(courses_tab.render_courses_tab()) if isinstance(node, dbc.Tab) and node.tab_id == "tab-coursera"]

    message, hidden = coursera_tab.children.children
    assert message.color == "danger" and "failed to load" in message.children
    assert hidden.hidden is True and "coursera-table-container" in _ids(hidden)


def test_search_boxes_wait_for_a_pause_in_typing(monkeypatch):
    """Each search runs on the server over a whole catalog: a request per keystroke would send a table per key."""
    _, layout = _app(monkeypatch)
    boxes = {node.id for node in _walk(layout) if isinstance(node, dbc.Input) and node.id.endswith("search-input")} | {"courses-global-search"}

    assert boxes == {"courses-global-search", "coursera-search-input", "udemy-search-input", CERTS, APPLIED, "aws-skills-search-input", "gcp-skills-search-input"}
    assert all(node.debounce == courses_tab.SEARCH_DEBOUNCE_MS for node in _walk(layout) if isinstance(node, dbc.Input) and node.id in boxes)


def test_the_dispatcher_marks_the_open_subtab_once_and_reads_what_it_marked(monkeypatch):
    """The dispatcher runs in the browser. Its state is what lets it leave a subtab that is opened again alone."""
    app, _ = _app(monkeypatch)
    (dispatcher,) = [cb for cb in app._callback_list if cb.get("clientside_function")]
    prefixes = [prefix for _, prefix in courses_tab.COURSES_SUBTABS]

    assert [output["id"] for output in _outputs_of(dispatcher)] == [f"{prefix}-activate" for prefix in prefixes]
    assert dispatcher["inputs"] == [{"id": courses_tab.COURSES_TABS_ID, "property": "active_tab"}]
    assert [spec["id"] for spec in dispatcher["state"]] == [f"{prefix}-activate" for prefix in prefixes]
    # The function it is given marks the open subtab unless its store is marked already.
    (script,) = app._inline_scripts
    assert "tabId === activeTab && !marked[i] ? 1 : window.dash_clientside.no_update" in script


def test_every_id_every_callback_uses_is_in_the_layout(monkeypatch):
    """The renderer refuses to fire a callback while one of its inputs or outputs is not in the page (seen in the browser)."""
    app, layout = _app(monkeypatch)
    ids = _ids(layout)

    missing = [(cb["output"][:60], spec["id"]) for cb in app._callback_list for spec in [*_outputs_of(cb), *cb["inputs"], *cb["state"]] if spec["id"] not in ids]
    assert not missing


# ---------------------------------------------------------------------------
# The controllers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("marker", CONTROLLERS)
def test_a_controller_stays_idle_until_its_subtab_is_activated(monkeypatch, marker):
    app, _ = _app(monkeypatch)

    assert _fire(app, marker) == {}


def test_activation_builds_the_first_page_of_each_subtab(monkeypatch):
    app, _ = _app(monkeypatch)

    page = _fire(app, f"{GLOBAL}-page-info.children", {"courses-global-search": None, "courses-free-only": None}, activate=1)
    assert page[f"{GLOBAL}-page.data"] == 1
    assert _rows(page[f"{GLOBAL}-results.children"]) == courses_tab.UNIFIED_PAGE_SIZE
    assert f"1–{courses_tab.UNIFIED_PAGE_SIZE} de {UNIFIED_ROWS} · Página 1 de 2" in _text(page[f"{GLOBAL}-page-info.children"])
    assert page[f"{GLOBAL}-prev.disabled"] is True and page[f"{GLOBAL}-next.disabled"] is False

    page = _fire(app, "coursera-pagination-info.children", activate=1)
    assert page["coursera-page.data"] == 1
    assert _rows(page["coursera-table-container.children"]) == courses_tab.PAGE_SIZE
    assert _text(page["coursera-pagination-info.children"]) == f"Showing 1-{courses_tab.PAGE_SIZE} of {COURSERA_ROWS} courses"
    assert page["coursera-total-pages.children"] == "8" and page["coursera-page-input.max"] == 8
    assert page["coursera-prev-btn.disabled"] is True and page["coursera-next-btn.disabled"] is False

    for search_id, table_id in ((CERTS, CERTS_TABLE), (APPLIED, APPLIED_TABLE)):
        page = _fire(app, f"{table_id}.children", {search_id: None, f"{search_id}-retired": False}, activate=1)
        assert _rows(page[f"{table_id}.children"]) == 1, search_id
    for prefix, rows in (("aws-skills", 2), ("gcp-skills", courses_tab.CLOUD_PAGE_SIZE)):
        page = _fire(app, f"{prefix}-page-info.children", activate=1)
        assert page[f"{prefix}-page.data"] == 1 and _rows(page[f"{prefix}-table-container.children"]) == rows, prefix


def test_activation_again_leaves_a_built_subtab_alone(monkeypatch):
    app, _ = _app(monkeypatch)

    for marker in (f"{GLOBAL}-page-info.children", "coursera-pagination-info.children", "gcp-skills-page-info.children"):
        assert _fire(app, marker, activate=1, page=1) == {}, marker


def test_the_pager_and_the_filters_drive_the_unified_catalog_after_its_first_build(monkeypatch):
    app, _ = _app(monkeypatch)
    marker = f"{GLOBAL}-page-info.children"

    page = _fire(app, marker, {"courses-global-search": "", "courses-free-only": False}, activate=1, page=1, changed=f"{GLOBAL}-next.n_clicks")
    assert page[f"{GLOBAL}-page.data"] == 2
    assert _rows(page[f"{GLOBAL}-results.children"]) == UNIFIED_ROWS - courses_tab.UNIFIED_PAGE_SIZE
    assert page[f"{GLOBAL}-prev.disabled"] is False and page[f"{GLOBAL}-next.disabled"] is True

    page = _fire(app, marker, {"courses-global-search": "lab", "courses-free-only": False}, activate=1, page=2, changed="courses-global-search.value")
    assert page[f"{GLOBAL}-page.data"] == 1  # a new search restarts from the first page
    assert _rows(page[f"{GLOBAL}-results.children"]) == GCP_ROWS
    assert f"🔎 {GCP_ROWS} cursos para 'lab'" in _text(page[f"{GLOBAL}-results.children"])

    page = _fire(app, marker, {"courses-global-search": "", "courses-free-only": True}, activate=1, page=1, changed="courses-free-only.value")
    assert _rows(page[f"{GLOBAL}-results.children"]) == COURSERA_ROWS // 2  # every other Coursera course is free
    assert "solo gratis" in _text(page[f"{GLOBAL}-results.children"])


def test_the_page_box_of_the_coursera_pager_jumps_and_is_not_rewritten_with_what_was_typed(monkeypatch):
    app, _ = _app(monkeypatch)
    marker = "coursera-pagination-info.children"

    page = _fire(app, marker, {"coursera-page-input": "3"}, activate=1, page=1, changed="coursera-page-input.value")
    assert page["coursera-page.data"] == 3
    assert "coursera-page-input.value" not in page  # rewriting the box just typed would run the controller twice
    page = _fire(app, marker, {"coursera-page-input": "not a page"}, activate=1, page=3, changed="coursera-page-input.value")
    assert page == {}
    page = _fire(app, marker, {"coursera-search-input": "Course 00"}, activate=1, page=3, changed="coursera-search-input.value")
    assert page["coursera-page.data"] == 1 and page["coursera-page-input.value"] == 1
    assert _rows(page["coursera-table-container.children"]) == 10  # Course 000 … Course 009


def test_ms_subtabs_hide_retired_credentials_until_asked_for(monkeypatch):
    app, _ = _app(monkeypatch)
    marker = f"{CERTS_TABLE}.children"
    toggle = f"{CERTS}-retired"

    built = _fire(app, marker, {CERTS: None, toggle: False}, activate=1)
    text = _text(built[marker])
    assert "Azure Administrator Associate" in text and "Old Certification" not in text and "Retirada" not in text

    built = _fire(app, marker, {CERTS: None, toggle: True}, activate=1, changed=f"{toggle}.value")
    text = _text(built[marker])
    assert "Old Certification" in text and "Retirada" in text and "2026-06-30" in text

    built = _fire(app, marker, {CERTS: "administrator", toggle: True}, activate=1, changed=f"{CERTS}.value")
    assert "Azure Administrator Associate" in _text(built[marker]) and "Old Certification" not in _text(built[marker])

    applied_marker = f"{APPLIED_TABLE}.children"
    built = _fire(app, applied_marker, {APPLIED: "AI-ENGINEER", f"{APPLIED}-retired": False}, activate=1)
    text = _text(built[applied_marker])
    assert "Develop AI agents on Azure" in text and "Artificial Intelligence" in text and "AI Engineer" in text


def test_the_ms_toggles_count_the_retired_credentials_of_their_own_kind(monkeypatch):
    """A toggle is shown only when its own kind has retired credentials: one count for both kinds would show a dead box."""
    _, layout = _app(monkeypatch)  # one retired certification, none among the applied skills

    (certs_toggle,) = _by_id(layout, f"{CERTS}-retired")
    (applied_toggle,) = _by_id(layout, f"{APPLIED}-retired")
    assert (certs_toggle.label, certs_toggle.value) == ("Mostrar retiradas (1)", False)
    assert applied_toggle.label == "Mostrar retiradas (0)"
    assert _toggle_wrapper(layout, f"{CERTS}-retired").style == {}
    assert _toggle_wrapper(layout, f"{APPLIED}-retired").style == {"display": "none"}


def test_page_plan():
    plan = courses_tab._page_plan
    filters = ("a-search", "a-language")

    assert plan("a-search", 0, None, "a", filters) is None  # not activated yet: nothing to build
    assert plan("", 1, None, "a", filters) == 1  # first activation: the first page
    assert plan("a-activate", 1, 1, "a", filters) is None  # activated again: the table built is kept
    assert plan("a-next", 1, 1, "a", filters) == 2
    assert plan("a-prev", 1, 2, "a", filters) == 1
    assert plan("a-prev-btn", 1, 2, "a", filters) == 1
    assert plan("a-page-input", 1, 1, "a", filters, "4") == 4
    assert plan("a-page-input", 1, 1, "a", filters, "x") is None
    assert plan("a-search", 1, 3, "a", filters) == 1  # a new search restarts from the first page
    assert plan("something-else", 1, 3, "a", filters) is None
