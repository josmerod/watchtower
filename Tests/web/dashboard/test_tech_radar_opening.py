"""Opening Tech Radar costs one request: the one that renders it (T-179).

The layout draws the whole tab: the per-source columns, the plot, the unified feed and the momentum panel.
It used to be drawn twice. The category dropdown started on ``all``, which was not among its options, so
right after mounting the component reset its value to null. That is a prop update like any other, which
``prevent_initial_call`` does not cover: the renderer reported it as a change and the controller ran again,
repainting all four (about 600 KiB more and a second blocked second in the browser).

Three guards, in the order in which they matter:

- each filter starts on an option it offers, so the component keeps the value the layout gave it;
- the layout already shows what the controller paints for that start, so nothing is left for a callback to do;
- should a filter lose its value anyway, the controller answers nothing instead of repainting.

The controller is called the way the browser calls it, POST /_dash-update-component on a Dash app through
Flask's test client, so what ``dash.ctx`` holds is Dash's own and not a mock (same harness as
test_inserted_buttons.py). Fixtures only: the tab reads a few files under tmp_path.
"""

import json
from types import SimpleNamespace

import dash
import dash_bootstrap_components as dbc
import pytest
from dash import dcc, html

from src.web.dashboard.components import saved_items
from src.web.dashboard.components import tech_radar_tab as tab
from src.web.dashboard.components.shared.cache import TTLDataCache

SEARCH = "tech-radar-search"
REFRESH = {"tab": "main", "type": "tech-radar-refresh"}
SOURCE_FILTER = "tech-radar-source-filter"
CATEGORY_FILTER = "tech-radar-category-filter"
FILTERS = (SOURCE_FILTER, CATEGORY_FILTER)
PLOT, FEED, MOMENTUM = "tech-radar-plot", "tech-radar-unified-feed", "tech-radar-momentum"
# A piece of the controller's output spec: how to tell it from the star and clear-button callbacks.
CONTROLLER = f"{FEED}.children"

# What the controller reads when the tab has just landed.
START = {SEARCH: None, "refresh": None, SOURCE_FILTER: "all", CATEGORY_FILTER: "all"}

# Mondays of three weeks: with two docker stories, then two, then six, docker rises +200% (T-048).
W3, W4, W5 = "2026-08-17", "2026-08-24", "2026-08-31"


def _story(title: str, day: str, hour: str = "10:00:00") -> dict:
    return {"title": title, "link": f"https://example.invalid/{title.replace(' ', '-')}", "published": f"{day}T{hour}+00:00", "summary": f"About {title}."}


HN = [_story("kubernetes rocks the homelab", "2026-08-27"), _story("unrelated hn story", "2026-08-26")]
CLOUD = [_story("cloud item one", "2026-08-27", "09:00:00"), _story("kubernetes on aws", "2026-08-25", "09:00:00")]
GOOGLE = [_story("google ai item", "2026-08-27", "08:00:00")]
STACK = [{"repo": "n8n", "title": "n8n@2.37.3", "link": "https://example.invalid/n8n", "published": "2026-08-25T13:03:52+00:00", "summary": "Bug fixes."}]
STORIES = {
    "news/hn_frontpage_latest.json": HN,
    "cloud_updates/cloud_updates_latest.json": CLOUD,
    "news/google_ai_blog_latest.json": GOOGLE,
    "github/stack_releases_latest.json": STACK,
}


def _write(tmp_path, rel: str, payload) -> None:
    target = tmp_path / "data" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def radar(tmp_path, monkeypatch) -> SimpleNamespace:
    """The tab on fixture files under a temp root, with caches and a saved-items file of its own."""
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    monkeypatch.setattr(tab, "_MOMENTUM_CACHE", tab.TTLDataCache(ttl_seconds=1800))
    monkeypatch.setattr(saved_items, "SAVED_FILE", tmp_path / "garden" / "saved_items.json")
    for rel, stories in STORIES.items():
        _write(tmp_path, rel, stories)
    for week, count in ((W3, 2), (W4, 2), (W5, 6)):
        _write(tmp_path, f"news/google_ai_blog_{week.replace('-', '')}_120000.json", [_story(f"docker story {index}", week) for index in range(count)])
    app = dash.Dash("test-radar-opening", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = html.Div(id="root")  # Dash checks that the app has one before it hands a request to a callback
    tab.register_tech_radar_callbacks(app)
    return SimpleNamespace(app=app, write=lambda rel, payload: _write(tmp_path, rel, payload))


# --- The browser's request, and what the answer holds ---


def _sid(ident) -> str:
    """A pattern id as the renderer stringifies it: JSON, keys sorted, no spaces."""
    return ident if isinstance(ident, str) else json.dumps(ident, sort_keys=True, separators=(",", ":"))


def _entry(ident, prop: str, value) -> dict:
    return {"id": _sid(ident), "property": prop, "value": value}


def _controller(app) -> dict:
    """The controller as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if CONTROLLER in cb["output"])


def _declared_outputs(app) -> list[tuple[str, str]]:
    """The controller's outputs in the order the callback declares them: the request has to list them so."""
    return [tuple(part.rsplit(".", 1)) for part in _controller(app)["output"][2:-2].split("...")]


def _outputs(app) -> set[tuple[str, str]]:
    return set(_declared_outputs(app))


def _call(app, changed, **values) -> dict:
    """POST the controller as the browser would and return only the outputs it changed (``{}`` on a 204).

    ``changed`` are the ``id.prop`` keys the renderer reports; ``values`` replace what the controller reads
    (``START`` by default).
    """
    state = {**START, **values}
    entry = _controller(app)
    inputs = [_entry(SEARCH, "value", state[SEARCH]), [_entry(REFRESH, "n_clicks", state["refresh"])]]  # the ALL input is the list of every button
    inputs += [_entry(SOURCE_FILTER, "value", state[SOURCE_FILTER]), _entry(CATEGORY_FILTER, "value", state[CATEGORY_FILTER])]
    body = {
        "output": entry["output"],
        "outputs": [{"id": ident, "property": prop} for ident, prop in _declared_outputs(app)],
        "inputs": inputs,
        "changedPropIds": list(changed),
        "state": [{**spec, "value": None} for spec in entry["state"]],
    }
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code in (200, 204), response.get_data(as_text=True)[-800:]  # 204: a callback that prevented the update
    if response.status_code == 204:
        return {}
    return {ident: value for ident, value in response.get_json()["response"].items() if value is not None}


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)


def _plain(value):
    """A component tree, a figure or a JSON value as the plain Python that travels to the browser."""
    if hasattr(value, "to_plotly_json"):
        return _plain(value.to_plotly_json())
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _dicts(node):
    """Every object of a JSON tree."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _dicts(value)
    elif isinstance(node, list):
        for item in node:
            yield from _dicts(item)


def _texts(value) -> list[str]:
    """Every text the tree shows: a component's own string, or a piece of one in a list (a highlighted title)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in _texts(item)]
    if isinstance(value, dict):
        return _texts(value.get("props", {}).get("children"))
    return []


def _flat(value) -> str:
    return " ".join(_texts(value))


def _rows(value) -> int:
    return sum(1 for d in _dicts(value) if d.get("type") == "Li" and d.get("props", {}).get("className") == "mb-2")


def _stars(value) -> int:
    return sum(1 for d in _dicts(value) if isinstance(d.get("props", {}).get("id"), dict) and d["props"]["id"].get("type") == tab.TECH_RADAR_SAVE_BTN_TYPE)


def _dropdowns(layout) -> dict:
    return {node.id: node for node in _walk(layout) if isinstance(node, dcc.Dropdown) and getattr(node, "id", None) in FILTERS}


def _requests_to_open(app, layout) -> list[str]:
    """What the browser asks for to open the tab, by the rules the renderer follows.

    One request renders the tab. That answer inserts the controller's outputs, and the renderer runs a
    callback on inserted outputs unless it has ``prevent_initial_call``. A dropdown whose value is not one of
    its options resets the value right after mounting, and the renderer reports that to every callback that
    reads it as a change.
    """
    requests = ["tab-content.children"]
    if _controller(app)["prevent_initial_call"] is not True:
        requests.append("the controller, its outputs inserted")
    for dropdown_id, dropdown in _dropdowns(layout).items():
        if dropdown.value not in [option["value"] for option in dropdown.options]:
            requests.append(f"the controller, {dropdown_id}.value reset to null on mounting")
    return requests


# --- One opening, one request ---


def test_one_opening_is_one_request(radar):
    assert _requests_to_open(radar.app, tab.render_tech_radar_tab()) == ["tab-content.children"]


@pytest.mark.parametrize("dropdown_id", FILTERS)
def test_each_filter_starts_on_an_option_it_offers(radar, dropdown_id):
    dropdown = _dropdowns(tab.render_tech_radar_tab())[dropdown_id]

    offered = [option["value"] for option in dropdown.options]
    assert dropdown.clearable is False
    assert dropdown.value in offered
    assert offered[0] == "all"  # the only way back to the whole feed


def test_the_whole_feed_sentinel_is_no_source_key_nor_category():
    # "all" means no filter to _render_unified_feed: a source called like that would be filtered out.
    assert "all" not in {source["key"] for source in tab.RADAR_SOURCES}
    assert "all" not in {source["category"] for source in tab.RADAR_SOURCES}


def test_the_layout_already_shows_what_the_controller_paints_for_the_start(radar):
    """Nothing is left for a callback to do when the tab lands: the answer to the start state is on screen."""
    painted = {node.id: node for node in _walk(tab.render_tech_radar_tab()) if isinstance(getattr(node, "id", None), str)}  # the stars and the refresh button have pattern ids
    answered = _call(radar.app, [f"{SEARCH}.value"])  # no search, both filters on "all": the state the layout starts on

    assert set(answered) == {ident for ident, _prop in _outputs(radar.app)}
    for ident, prop in _outputs(radar.app):
        assert _plain(answered[ident][prop]) == _plain(getattr(painted[ident], prop)), (ident, prop)
    # The panel and the plot compared above are not the empty notices: the fixtures give them content.
    momentum = _flat(answered[MOMENTUM]["children"])
    assert "+200%" in momentum and "docker" in momentum
    assert len(_plain(answered[PLOT]["figure"])["data"]) == 1  # kubernetes, named by two stories


def test_the_feed_the_controller_paints_keeps_its_stars(radar):
    answered = _call(radar.app, [f"{SEARCH}.value"])

    assert _rows(answered[FEED]["children"]) == 6  # two Hacker News, two Cloud Updates, one Google AI, one release
    assert _stars(answered[FEED]["children"]) == 6
    assert _stars(answered["tech-radar-col-hn_frontpage"]["children"]) == 0  # the per-source columns never carry one


# --- Should a filter lose its value anyway ---


@pytest.mark.parametrize("search", [None, "kubernetes"])
@pytest.mark.parametrize("dropdown_id", FILTERS)
def test_a_filter_that_loses_its_value_as_it_mounts_paints_nothing(radar, dropdown_id, search):
    """The request the browser makes when a dropdown resets itself right after mounting: nothing to repaint."""
    assert _call(radar.app, [f"{dropdown_id}.value"], **{dropdown_id: None, SEARCH: search}) == {}


def test_going_back_to_the_whole_feed_is_a_choice_and_repaints_it(radar):
    """``all`` is a real option: choosing it after a category repaints the feed, it is not a reset."""
    by_category = _call(radar.app, [f"{CATEGORY_FILTER}.value"], **{CATEGORY_FILTER: "Cloud"})
    assert "google ai item" not in _flat(by_category[FEED]["children"])

    back = _call(radar.app, [f"{CATEGORY_FILTER}.value"])

    assert set(back) == set(by_category)
    assert "google ai item" in _flat(back[FEED]["children"])


# --- The interactions the controller is for ---


def test_choosing_a_category_repaints_the_feed(radar):
    answered = _call(radar.app, [f"{CATEGORY_FILTER}.value"], **{CATEGORY_FILTER: "Cloud"})

    assert set(answered) == {ident for ident, _prop in _outputs(radar.app)}  # one controller: every output travels
    titles = _flat(answered[FEED]["children"])
    assert "cloud item one" in titles and "kubernetes on aws" in titles
    assert "kubernetes rocks the homelab" not in titles and "google ai item" not in titles and "n8n@2.37.3" not in titles


def test_choosing_a_source_repaints_the_feed(radar):
    answered = _call(radar.app, [f"{SOURCE_FILTER}.value"], **{SOURCE_FILTER: "hn_frontpage"})

    titles = _flat(answered[FEED]["children"])
    assert "unrelated hn story" in titles and "cloud item one" not in titles and "google ai item" not in titles


def test_typing_still_filters_the_columns_and_the_feed(radar):
    answered = _call(radar.app, [f"{SEARCH}.value"], **{SEARCH: "kubernetes"})

    assert set(answered) == {ident for ident, _prop in _outputs(radar.app)}
    hacker_news = _flat(answered["tech-radar-col-hn_frontpage"]["children"])
    assert "rocks the homelab" in hacker_news and "unrelated hn story" not in hacker_news
    assert "No articles matching 'kubernetes'." in _flat(answered["tech-radar-col-google_ai"]["children"])
    feed = _flat(answered[FEED]["children"])
    assert "rocks the homelab" in feed and " on aws" in feed
    assert "unrelated hn story" not in feed and "google ai item" not in feed and "n8n@2.37.3" not in feed
    assert _stars(answered[FEED]["children"]) == 2  # a star per row that is left


def test_the_refresh_button_still_repaints_everything_from_disk(radar):
    """A refresh bypasses the caches: a file rewritten after the first paint shows up in the answer."""
    before = _call(radar.app, [f"{SEARCH}.value"])
    radar.write("news/hn_frontpage_latest.json", [*HN, _story("fresh after refresh", "2026-08-28")])

    answered = _call(radar.app, [f"{_sid(REFRESH)}.n_clicks"], refresh=1)

    assert set(answered) == set(before)
    assert "fresh after refresh" in _flat(answered["tech-radar-col-hn_frontpage"]["children"])
    assert "fresh after refresh" in _flat(answered[FEED]["children"])
