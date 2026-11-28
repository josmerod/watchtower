"""Opening Videos costs one request: the one that renders it (T-211).

The layout drew 48 cards under an info line of its own, without the pager, and the controller then drew the page again
as its outputs landed: ``prevent_initial_call`` was off, and the renderer runs a callback on outputs it inserts unless it
is on. Every opening paid for the same page twice, and the second paint replaced the first a moment later.

Three guards, in the order in which they matter:

- each filter starts on an option it offers, so the component keeps the value the layout gave it;
- the layout draws the opening page with the painter the controller uses, pager included, so nothing is left for a callback to do;
- should the controller be asked anyway (its outputs landing, buttons just inserted, a filter losing its value as it
  mounts), it answers nothing.

The controller is called the way the browser calls it, POST /_dash-update-component on a Dash app through Flask's test
client, so what ``dash.ctx`` holds is Dash's own and not a mock (same harness as test_inserted_buttons.py). Fixtures
only: the frames are hand-built and swapped into the module-level VideoManager, and the theme keys come from a pinned
table; nothing under ``data/`` is read or written and no network is touched.
"""

import json
from datetime import datetime, timedelta, timezone

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import pytest
from dash import dcc, html

from src.etl.goldigging import channel_topics
from src.web.dashboard.components import videos_tab as tab

CHANNEL, THEME, SEARCH, DATE, SORT, PAGE_SIZE, REFRESH = "video-channel-dropdown-new", "videos-theme-dropdown", "video-search-input-new", "video-date-filter-new", "videos-sort-by", "videos-items-per-page-select", "videos-refresh-button"
FILTERS = (CHANNEL, THEME, DATE, SORT, PAGE_SIZE)
CONTAINER, PAGER, PAGE = "videos-container", "videos-pagination", "videos-page"
# A piece of the controller's output spec: how to tell it from the preset callbacks, which write the filters.
CONTROLLER = f"{CONTAINER}.children"
NEXT = {"dir": "next", "type": "videos-page-btn"}
PREV = {"dir": "prev", "type": "videos-page-btn"}
THEME_KEY = "aa-gen-ai"  # a key of channels.json: the name of the directory its ETL writes
THEME_VIDEOS = 20
CHANNEL_VIDEOS = 60  # with the theme's: two pages of 48, so the pager is on screen from the start
TOTAL_VIDEOS = CHANNEL_VIDEOS + THEME_VIDEOS
MARKED = 5  # videos of the channel whose title says "kubernetes"

# What the controller reads when the tab has just landed.
START = {CHANNEL: "all", THEME: "all", SEARCH: None, DATE: "all", SORT: "date_desc", PAGE_SIZE: 48, "refresh": 0, "clicks": (None, None), "page": 1}


def _days_ago(n: int) -> str:
    """ISO date n days before now."""
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def _frame(prefix: str, count: int, marked: int = 0) -> pd.DataFrame:
    """A channel DataFrame the same way VideoManager.load_data builds it; the first ``marked`` titles say kubernetes."""
    rows = [
        {
            "title": f"kubernetes {prefix} video {n}" if n < marked else f"{prefix} video {n}",
            "url": f"https://www.youtube.com/watch?v={prefix[0]}{n:010d}",  # an 11-character video id, as the card reads them
            "thumbnail": "",
            "channel": "fixture",
            "published_at": _days_ago(n + 1),
            "description": "",
            "views": 10,
            "length": 120,
        }
        for n in range(count)
    ]
    frame = pd.DataFrame(rows)
    frame["published_date"] = pd.to_datetime(frame["published_at"], errors="coerce", utc=True)
    return frame


@pytest.fixture
def videos(monkeypatch) -> dash.Dash:
    """A Dash app with the Videos callbacks over in-memory videos, and one theme key standing in for channels.json."""
    monkeypatch.setattr(tab.video_manager, "video_data", {"MatthewBerman": _frame("mb", CHANNEL_VIDEOS, MARKED), THEME_KEY: _frame("gen", THEME_VIDEOS)})
    monkeypatch.setattr(tab.video_manager, "ensure_loaded", lambda force_refresh=False: None)
    topics = {THEME_KEY: {"description": "Generative AI", "channels": []}}
    monkeypatch.setattr(channel_topics, "load_channel_topics", lambda: topics)
    # The helper caches the file per process: drop the cache before and after
    channel_topics._read_topics.cache_clear()
    app = dash.Dash("test-videos-opening", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = html.Div(id="root")  # Dash checks that the app has one before it hands a request to a callback
    tab.register_video_callbacks(app)
    yield app
    channel_topics._read_topics.cache_clear()


# --- The browser's request, and what the answer holds ---


def _sid(ident) -> str:
    """A pattern id as the renderer stringifies it: JSON, keys sorted, no spaces."""
    return ident if isinstance(ident, str) else json.dumps(ident, sort_keys=True, separators=(",", ":"))


def _entry(ident, prop: str, value) -> dict:
    return {"id": _sid(ident), "property": prop, "value": value}


def _key(ident, prop: str) -> str:
    """The ``id.prop`` the renderer puts in ``changedPropIds``."""
    return f"{_sid(ident)}.{prop}"


def _controller(app) -> dict:
    """The controller as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if CONTROLLER in cb["output"])


def _declared_outputs(app) -> list[tuple[str, str]]:
    """The controller's outputs in the order the callback declares them: the request has to list them so."""
    return [tuple(part.rsplit(".", 1)) for part in _controller(app)["output"][2:-2].split("...")]


def _answer(app, changed, **values) -> dict:
    """The controller's whole answer, as the browser gets it (``None`` where it wrote nothing)."""
    state = {**START, **values}
    inputs = [_entry(CHANNEL, "value", state[CHANNEL]), _entry(THEME, "value", state[THEME]), _entry(SEARCH, "value", state[SEARCH]), _entry(DATE, "value", state[DATE]), _entry(SORT, "value", state[SORT]), _entry(PAGE_SIZE, "value", state[PAGE_SIZE]), _entry(REFRESH, "n_clicks", state["refresh"])]
    inputs.append([_entry(PREV, "n_clicks", state["clicks"][0]), _entry(NEXT, "n_clicks", state["clicks"][1])])  # the ALL input is the list of every pager button
    body = {
        "output": _controller(app)["output"],
        "outputs": [{"id": ident, "property": prop} for ident, prop in _declared_outputs(app)],
        "inputs": inputs,
        "changedPropIds": list(changed),
        "state": [_entry(PAGE, "data", state["page"])],
    }
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code in (200, 204), response.get_data(as_text=True)[-800:]  # 204: a callback that prevented the update
    return {} if response.status_code == 204 else response.get_json()["response"]


def _call(app, changed, **values) -> dict:
    """POST the controller as the browser would and return only the outputs it wrote (``{}`` when it answered nothing)."""
    return {ident: value for ident, value in _answer(app, changed, **values).items() if value is not None}


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


def _texts(value) -> list[str]:
    """Every text the tree shows: a component's own string, or a piece of one in a list."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in _texts(item)]
    if isinstance(value, dict):
        return _texts(value.get("props", {}).get("children"))
    return []


def _flat(value) -> str:
    return " ".join(_texts(value))


def _cards(value) -> int:
    """Video cards on a page: each carries exactly one ``data-video-hash``."""
    return json.dumps(_plain(value)).count('"data-video-hash"')


def _dropdowns(layout) -> dict:
    """The controller's filter dropdowns as the layout holds them."""
    return {node.id: node for node in _walk(layout) if isinstance(node, dcc.Dropdown) and getattr(node, "id", None) in FILTERS}


def _on_screen(ident: str):
    """One of the controller's outputs as the layout draws it, as plain Python."""
    (node,) = [node for node in _walk(tab.render_videos_tab()) if getattr(node, "id", None) == ident]
    return _plain(node.children) if ident != PAGE else node.data


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


def test_one_opening_is_one_request(videos):
    assert _requests_to_open(videos, tab.render_videos_tab()) == ["tab-content.children"]


@pytest.mark.parametrize("dropdown_id", FILTERS)
def test_each_filter_starts_on_an_option_it_offers(videos, dropdown_id):
    dropdown = _dropdowns(tab.render_videos_tab())[dropdown_id]

    offered = [option["value"] for option in dropdown.options]
    assert dropdown.clearable is False
    assert dropdown.value in offered


def test_the_theme_filter_starts_on_every_theme_not_on_one_of_them(videos):
    """The first option is the whole feed: a tab that opened on a theme would hide most of its videos."""
    theme = _dropdowns(tab.render_videos_tab())[THEME]

    assert [option["value"] for option in theme.options] == ["all", THEME_KEY]
    assert theme.value == "all"


def test_the_layout_already_shows_what_the_controller_paints_for_the_start(videos):
    """Nothing is left for a callback to do when the tab lands: the answer to the start state is on screen."""
    answered = _call(videos, [_key(REFRESH, "n_clicks")], refresh=1)  # a refresh with the start filters on screen

    assert set(answered) == {CONTAINER, PAGER, PAGE}
    for ident in (CONTAINER, PAGER):
        assert _plain(answered[ident]["children"]) == _on_screen(ident), ident
    assert answered[PAGE]["data"] == _on_screen(PAGE) == 1
    # Compared above is the opening page, not an empty notice: the fixtures fill it and the pager.
    assert _cards(answered[CONTAINER]["children"]) == 48
    assert "📺 Showing 48 of 80 videos from all channels" in _flat(answered[CONTAINER]["children"])
    assert "Page 1 of 2 · 80 videos" in _flat(answered[PAGER]["children"])


def test_the_pager_is_on_screen_from_the_start_only_when_there_is_a_second_page(videos, monkeypatch):
    assert "Page 1 of 2 · 80 videos" in _flat(_on_screen(PAGER))

    monkeypatch.setattr(tab.video_manager, "video_data", {"MatthewBerman": _frame("mb", 7)})

    assert _on_screen(PAGER) is None
    assert _cards(_on_screen(CONTAINER)) == 7  # the info line is a text, so it counts no card


# --- Should the controller be asked anyway ---


@pytest.mark.parametrize("dropdown_id", FILTERS)
def test_a_filter_that_loses_its_value_as_it_mounts_paints_nothing(videos, dropdown_id):
    """The request the browser makes when a dropdown resets itself right after mounting: nothing to repaint."""
    assert _call(videos, [f"{dropdown_id}.value"], **{dropdown_id: None}) == {}


def test_the_call_the_renderer_makes_as_the_outputs_land_paints_nothing(videos):
    """No changed prop at all: what the renderer sends when it runs a callback for outputs it has just inserted."""
    assert _call(videos, []) == {}


def test_the_pager_buttons_just_inserted_change_nothing(videos):
    """The pager lands with the page: its two buttons are new components, whose clicks count nothing yet."""
    assert _call(videos, [_key(PREV, "n_clicks"), _key(NEXT, "n_clicks")]) == {}
    assert _call(videos, [_key(NEXT, "n_clicks")]) == {}


def test_the_refresh_button_mounting_paints_nothing_either(videos):
    assert _call(videos, [_key(REFRESH, "n_clicks")], refresh=None) == {}


# --- The interactions the controller is for ---


def test_choosing_a_theme_repaints(videos):
    answered = _call(videos, [f"{THEME}.value"], **{THEME: THEME_KEY})

    assert set(answered) == {CONTAINER, PAGER, PAGE}
    assert answered[PAGER]["children"] is None  # one page: the pager goes, as an empty container rather than no write
    assert _cards(answered[CONTAINER]["children"]) == THEME_VIDEOS
    assert f"📺 Showing {THEME_VIDEOS} of {THEME_VIDEOS} videos from all channels (tema 'Generative AI ({THEME_KEY})')" in _flat(answered[CONTAINER]["children"])
    assert answered[PAGE]["data"] == 1


def test_going_back_to_the_whole_feed_is_a_choice_and_repaints_it(videos):
    """``all`` is a real option: choosing it after a theme repaints the page, it is not a reset."""
    by_theme = _call(videos, [f"{THEME}.value"], **{THEME: THEME_KEY})
    assert _cards(by_theme[CONTAINER]["children"]) == THEME_VIDEOS

    back = _call(videos, [f"{THEME}.value"])

    assert set(back) == {CONTAINER, PAGER, PAGE}
    assert _cards(back[CONTAINER]["children"]) == 48


def test_choosing_a_channel_and_a_page_size_repaint(videos):
    answered = _call(videos, [f"{CHANNEL}.value"], **{CHANNEL: "MatthewBerman", PAGE_SIZE: 12})

    assert _cards(answered[CONTAINER]["children"]) == 12
    assert "Showing 12 of 60 videos from 'MatthewBerman'" in _flat(answered[CONTAINER]["children"])
    assert "Page 1 of 5 · 60 videos" in _flat(answered[PAGER]["children"])


@pytest.mark.parametrize("cleared", [None, ""], ids=["none", "empty"])
def test_typing_still_filters_and_clearing_the_box_restores_the_page(videos, cleared):
    """The search box is the one input that may hold nothing because the user emptied it: that is a change."""
    filtered = _call(videos, [f"{SEARCH}.value"], **{SEARCH: "kubernetes"})

    assert _cards(filtered[CONTAINER]["children"]) == MARKED
    assert f"Showing {MARKED} of {MARKED} videos from all channels (matching 'kubernetes')" in _flat(filtered[CONTAINER]["children"])

    restored = _call(videos, [f"{SEARCH}.value"], **{SEARCH: cleared})

    assert _cards(restored[CONTAINER]["children"]) == 48
    assert "Page 1 of 2 · 80 videos" in _flat(restored[PAGER]["children"])


def test_next_and_prev_still_move_through_the_pages(videos):
    second = _call(videos, [_key(NEXT, "n_clicks")], clicks=(None, 1))

    assert second[PAGE]["data"] == 2
    assert _cards(second[CONTAINER]["children"]) == TOTAL_VIDEOS - 48
    assert "Page 2 of 2 · 80 videos" in _flat(second[PAGER]["children"])

    first = _call(videos, [_key(PREV, "n_clicks")], clicks=(1, 1), page=2)

    assert first[PAGE]["data"] == 1
    assert _cards(first[CONTAINER]["children"]) == 48


def test_the_refresh_button_still_reloads_the_videos_and_repaints(videos, monkeypatch):
    """A refresh bypasses the cache: frames swapped in after the first paint show up in the answer."""
    source = {"MatthewBerman": _frame("mb", CHANNEL_VIDEOS), THEME_KEY: _frame("gen", THEME_VIDEOS)}

    def load_data() -> None:
        tab.video_manager.video_data = dict(source)  # what the real loader does: read everything again, then replace

    monkeypatch.setattr(tab.video_manager, "load_data", load_data)
    monkeypatch.setattr(tab.video_manager, "ensure_loaded", lambda force_refresh=False: load_data() if force_refresh else None)
    before = _call(videos, [f"{SEARCH}.value"], **{SEARCH: "fresh"})
    assert _cards(before[CONTAINER]["children"]) == 0

    source["MatthewBerman"] = _frame("mb", CHANNEL_VIDEOS + 3)

    without = _call(videos, [f"{SEARCH}.value"])  # a filter change keeps the frames loaded
    assert "Showing 48 of 80 videos" in _flat(without[CONTAINER]["children"])
    refreshed = _call(videos, [_key(REFRESH, "n_clicks")], refresh=1)
    assert "Showing 48 of 83 videos" in _flat(refreshed[CONTAINER]["children"])


def test_a_card_that_fails_to_build_does_not_take_the_page_down(videos, monkeypatch):
    """The painter the layout and the controller share keeps its fallback card on every page, not only on the first."""
    real_builder = tab.create_video_card

    def build(video):
        if video["title"] == "mb video 30":  # on the first page: the newest 48 of the channel
            raise ValueError("broken record")
        return real_builder(video)

    monkeypatch.setattr(tab, "create_video_card", build)

    page = _call(videos, [f"{CHANNEL}.value"], **{CHANNEL: "MatthewBerman"})[CONTAINER]["children"]

    assert _cards(page) == 47  # the 47 sound cards of the page; the fallback is a card of another shape
    assert _flat(page).count("Video Load Error") == 1 and "Failed to load: mb video 30" in _flat(page)
    assert "Error loading videos" not in _flat(page)  # the whole page is not replaced by the error notice
