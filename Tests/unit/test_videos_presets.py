"""Saved presets of the Videos tab apply their page size and their theme (T-138).

A preset always stored ``per_page``; applying one wrote only the channel, the date window and the sort order, so the page size
never followed. The theme was neither stored nor applied, and the name of a preset spelled the default date window ``alld``.
The callbacks are called the way the browser calls them, POST /_dash-update-component on a Dash app through Flask's test
client, and the outputs of one call feed the next as the renderer chains them. Fixtures only: nothing under ``data/`` is read
or written and no network is touched.
"""

import json
from datetime import datetime, timedelta, timezone

import dash
import pandas as pd
import pytest
from dash import html

from src.web.dashboard.components import videos_tab as tab

SELECT = "videos-items-per-page-select"
CHANNEL = "video-channel-dropdown-new"
THEME = "videos-theme-dropdown"
DATE = "video-date-filter-new"
SORT = "videos-sort-by"
TOTAL_VIDEOS = 60  # five pages of 12, and more than one page of 48
THEME_KEY = "aa-gen-ai"  # a key of channels.json: the name of the directory its ETL writes
THEME_VIDEOS = 20


def _days_ago(n: int) -> str:
    """ISO date n days before now."""
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def _entry(ident: str, prop: str, value) -> dict:
    return {"id": ident, "property": prop, "value": value}


def _callback(app: dash.Dash, first_output: str) -> dict:
    """The callback whose output spec starts with ``first_output``, as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if cb["output"].startswith(first_output))


def _post(app: dash.Dash, cb: dict, inputs: list, changed: list[str], states: list | None = None) -> dict:
    """POST the callback as the browser would and return the outputs it changed, grouped by component id.

    A ``no_update`` output is left out, and a callback that updates nothing answers 204.
    """
    spec = cb["output"]
    if spec.startswith(".."):
        outputs = [dict(zip(("id", "property"), part.rsplit(".", 1), strict=True)) for part in spec[2:-2].split("...")]
        for output in outputs:
            output["property"] = output["property"].split("@")[0]  # a duplicate output carries its opt-in hash
    else:
        ident, _, prop = spec.rpartition(".")
        outputs = {"id": ident, "property": prop}
    body = {"output": spec, "outputs": outputs, "inputs": inputs, "changedPropIds": list(changed), "state": states if states is not None else [{**state, "value": None} for state in cb["state"]]}
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code in (200, 204), response.get_data(as_text=True)[-800:]  # 204: nothing to update
    if response.status_code == 204:
        return {}
    return response.get_json()["response"]


def _saved_presets(saved: dict) -> dict:
    """The preset store a 💾 click returns, keyed by preset name."""
    return saved["videos-presets"]["data"]


def _applied(applied: dict, ident: str, prop: str = "value"):
    """One filter a preset selection wrote; None when it wrote none."""
    return applied.get(ident, {}).get(prop)


def _save(app: dash.Dash, presets: dict, channel="all", theme="all", date_filter="all", sort_by="date_desc", per_page=48) -> dict:
    """Click 💾 with the given filters on screen; returns the callback's outputs."""
    cb = _callback(app, "..videos-presets.data")
    states = [
        _entry("videos-presets", "data", presets),
        _entry(CHANNEL, "value", channel),
        _entry(THEME, "value", theme),
        _entry(DATE, "value", date_filter),
        _entry(SORT, "value", sort_by),
        _entry(SELECT, "value", per_page),
    ]
    return _post(app, cb, [_entry("videos-preset-save", "n_clicks", 1)], ["videos-preset-save.n_clicks"], states)


def _apply(app: dash.Dash, name: str, presets: dict) -> dict:
    """Choose ``name`` in the preset dropdown; returns the callback's outputs."""
    cb = _callback(app, f"..{CHANNEL}.value")
    return _post(app, cb, [_entry("videos-preset-selector", "value", name)], ["videos-preset-selector.value"], [_entry("videos-presets", "data", presets)])


def _render(app: dash.Dash, channel="all", theme="all", date_filter="all", sort_by="date_desc", per_page=48) -> dict:
    """Run the combined controller with those values on screen, as the renderer does after a preset changes them."""
    cb = _callback(app, "..videos-container.children")
    inputs = [
        _entry(CHANNEL, "value", channel),
        _entry(THEME, "value", theme),
        _entry("video-search-input-new", "value", ""),
        _entry(DATE, "value", date_filter),
        _entry(SORT, "value", sort_by),
        _entry(SELECT, "value", per_page),
        _entry("videos-refresh-button", "n_clicks", None),
        [],
    ]
    return _post(app, cb, inputs, [f"{SELECT}.value"], [_entry("videos-page", "data", 1)])


def _page(rendered: dict):
    """What the controller wrote into the videos container."""
    return rendered["videos-container"]["children"]


def _cards(page) -> int:
    """Video cards on the page: each carries exactly one ``data-video-hash``."""
    return json.dumps(page).count('"data-video-hash"')


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> dash.Dash:
    """A Dash app with the Videos callbacks over 60 in-memory videos."""
    rows = [
        {"title": f"mb video {n}", "url": f"https://www.youtube.com/watch?v=id{n:010d}", "thumbnail": "", "channel": "fixture", "published_at": _days_ago(n + 1), "description": "", "views": 10, "length": 120}
        for n in range(TOTAL_VIDEOS)
    ]
    frame = pd.DataFrame(rows)
    frame["published_date"] = pd.to_datetime(frame["published_at"], errors="coerce", utc=True)
    monkeypatch.setattr(tab.video_manager, "video_data", {"MatthewBerman": frame})
    monkeypatch.setattr(tab.video_manager, "ensure_loaded", lambda force_refresh=False: None)
    app = dash.Dash("test-videos-presets")
    app.layout = html.Div(id="root")
    tab.register_video_callbacks(app)
    return app


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def test_the_preset_callbacks_are_the_renderers_to_reach_the_controller(app):
    """Applying a preset writes the page-size selector, which the combined controller reads."""
    apply = _callback(app, f"..{CHANNEL}.value")

    assert apply["inputs"] == [{"id": "videos-preset-selector", "property": "value"}]
    assert apply["prevent_initial_call"] is True
    assert f"...{SELECT}.value@" in apply["output"], "the page-size output must opt in as a duplicate writer"
    controller = _callback(app, "..videos-container.children")
    for ident, prop in ((CHANNEL, "value"), (THEME, "value"), (DATE, "value"), (SORT, "value"), (SELECT, "value")):
        assert {"id": ident, "property": prop} in controller["inputs"]


# ---------------------------------------------------------------------------
# The flow, as the browser chains it
# ---------------------------------------------------------------------------


def test_a_preset_applies_its_page_size(app):
    assert _cards(_page(_render(app, per_page=48))) == 48  # what the tab shows before

    saved = _save(app, {}, per_page=12)
    name = _applied(saved, "videos-preset-selector")
    assert _saved_presets(saved)[name]["per_page"] == 12

    applied = _apply(app, name, _saved_presets(saved))
    assert _applied(applied, SELECT) == 12
    assert (_applied(applied, CHANNEL), _applied(applied, THEME), _applied(applied, DATE), _applied(applied, SORT)) == ("all", "all", "all", "date_desc")

    # The renderer feeds those outputs to the controller
    page = _render(app, channel=_applied(applied, CHANNEL), theme=_applied(applied, THEME), date_filter=_applied(applied, DATE), sort_by=_applied(applied, SORT), per_page=_applied(applied, SELECT))
    assert _cards(_page(page)) == 12
    assert "Showing 12 of 60 videos" in json.dumps(_page(page))


@pytest.mark.parametrize("per_page", [12, 24, 48, 96])
def test_every_page_size_the_selector_offers_applies(app, per_page):
    saved = _save(app, {}, per_page=per_page)
    name = _applied(saved, "videos-preset-selector")

    applied = _apply(app, name, _saved_presets(saved))

    assert _applied(applied, SELECT) == per_page
    assert _cards(_page(_render(app, per_page=_applied(applied, SELECT)))) == min(per_page, TOTAL_VIDEOS)


def test_two_presets_carry_two_page_sizes(app):
    saved = _save(app, {}, per_page=12)
    saved = _save(app, _saved_presets(saved), channel="MatthewBerman", per_page=96)
    presets = _saved_presets(saved)
    by_name = {preset["per_page"]: name for name, preset in presets.items()}
    assert sorted(by_name) == [12, 96]

    assert _applied(_apply(app, by_name[96], presets), SELECT) == 96
    assert _applied(_apply(app, by_name[12], presets), SELECT) == 12


# ---------------------------------------------------------------------------
# A preset without a usable page size leaves the selector alone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "per_page",
    [{"date": "7"}, {"per_page": None, "date": "7"}, {"per_page": 0, "date": "7"}, {"per_page": -5, "date": "7"}, {"per_page": "24", "date": "7"}, {"per_page": 3.5, "date": "7"}],
    ids=["missing", "null", "zero", "negative", "string", "float"],
)
def test_a_preset_without_a_usable_page_size_leaves_the_selector_alone(app, per_page):
    presets = {"hand-edited": {"channel": "all", "sort": "date_desc", **per_page}}

    applied = _apply(app, "hand-edited", presets)

    assert SELECT not in applied  # nothing written: the page size stays what the selector shows
    assert _applied(applied, DATE) == "7"  # the filters it does have are applied


def test_a_preset_storing_true_does_not_become_one_item_per_page(app):
    """JSON ``true`` is an ``int`` in Python: without the bool check it would be a page size of 1."""
    assert tab._preset_page_size({"per_page": True}) is None
    assert tab._preset_page_size({"per_page": False}) is None


def test_an_unknown_preset_or_an_empty_store_changes_nothing(app):
    assert _apply(app, "never saved", {}) == {}
    assert _apply(app, "never saved", {"another one": {"channel": "all"}}) == {}


@pytest.mark.parametrize(
    "preset,expected",
    [({"per_page": 12}, 12), ({"channel": "all"}, None), ({"per_page": "12"}, None), ({"per_page": 0}, None), ({"per_page": 2.5}, None)],
    ids=["stored", "missing", "string", "zero", "float"],
)
def test_preset_page_size_reads_only_a_positive_integer(preset, expected):
    assert tab._preset_page_size(preset) == expected


# ---------------------------------------------------------------------------
# The theme is one of the filters
# ---------------------------------------------------------------------------


def test_a_preset_applies_its_theme(app):
    """A preset saved with a theme used to leave the Tema dropdown as it was: other videos than it was saved for."""
    tab.video_manager.video_data[THEME_KEY] = pd.DataFrame(
        [
            {
                "title": f"theme video {n}",
                "url": f"https://www.youtube.com/watch?v=theme{n:07d}",
                "thumbnail": "",
                "channel": "fixture",
                "published_at": _days_ago(n + 1),
                "description": "",
                "views": 10,
                "length": 120,
            }
            for n in range(THEME_VIDEOS)
        ]
    )
    tab.video_manager.video_data[THEME_KEY]["published_date"] = pd.to_datetime(tab.video_manager.video_data[THEME_KEY]["published_at"], errors="coerce", utc=True)
    assert _cards(_page(_render(app, per_page=96))) == TOTAL_VIDEOS + THEME_VIDEOS  # both directories, no theme chosen

    saved = _save(app, {}, theme=THEME_KEY, per_page=12)
    name = _applied(saved, "videos-preset-selector")
    assert _saved_presets(saved)[name]["theme"] == THEME_KEY

    applied = _apply(app, name, _saved_presets(saved))
    assert _applied(applied, THEME) == THEME_KEY

    # The renderer feeds those outputs to the controller
    page = _page(_render(app, theme=_applied(applied, THEME), per_page=_applied(applied, SELECT)))
    dumped = json.dumps(page)
    assert _cards(page) == 12
    assert "Showing 12 of 20 videos" in dumped
    assert "tema 'Generative AI (aa-gen-ai)'" in dumped
    assert "theme video" in dumped and "mb video" not in dumped


def test_a_preset_name_spells_the_default_date_window_all(app):
    """The name used to read ``all · alld · date_desc``: the window alone carried its unit."""
    assert _applied(_save(app, {}), "videos-preset-selector") == "all · all · date_desc"
    assert _applied(_save(app, {}, date_filter="7"), "videos-preset-selector") == "all · 7d · date_desc"
    assert _applied(_save(app, {}, theme=THEME_KEY), "videos-preset-selector") == f"all · {THEME_KEY} · all · date_desc"


@pytest.mark.parametrize(
    "filters,expected",
    [
        ((None, None, None, None), "all · all · date_desc"),
        (("MatthewBerman", "all", "30", "most_viewed"), "MatthewBerman · 30d · most_viewed"),
        (("all", THEME_KEY, "all", "date_asc"), f"all · {THEME_KEY} · all · date_asc"),
    ],
    ids=["nothing-chosen", "no-theme", "theme"],
)
def test_preset_name_lists_the_chosen_filters(filters, expected):
    assert tab._preset_name(*filters) == expected


def test_a_preset_saved_before_the_theme_leaves_the_theme_alone(app):
    """The presets in a browser's localStorage predate the theme: applying one keeps the Tema dropdown as it is."""
    applied = _apply(app, "old", {"old": {"channel": "all", "date": "7", "sort": "date_desc", "per_page": 12}})

    assert THEME not in applied
    assert (_applied(applied, DATE), _applied(applied, SELECT)) == ("7", 12)
