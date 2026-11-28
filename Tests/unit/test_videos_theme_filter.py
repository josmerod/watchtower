"""Tests for the Videos 📺 Tema dropdown (T-088, spec 04).

Fixture-based — swaps the module-level VideoManager's in-memory data with
hand-built DataFrames (same pattern as test_videos_channels_admin.py); no
data/ files and no network. Covers the pure theme helpers, the filter
composition inside ``VideoManager.get_videos`` and the dropdown's wiring
into the single controller callback.

A theme is a key of ``src/etl/goldigging/channels.json`` (T-138): every test
here pins those keys to the names its directories use, so the fixtures do not
depend on what the real file lists today.
"""

from datetime import datetime, timedelta, timezone

import dash
import pandas as pd
import pytest

from src.etl.goldigging import channel_topics
from src.web.dashboard.components import videos_tab as tab
from src.web.dashboard.components.videos_tab import (
    _channel_matches_theme,
    _extract_theme_options,
    _is_theme_channel,
)

# The theme keys of every fixture below, as channels.json would list them.
THEME_KEYS = ("aa-gen-ai", "zz-python")


@pytest.fixture(autouse=True)
def fixture_theme_keys(monkeypatch):
    """Answer every theme lookup from THEME_KEYS instead of the real channels.json."""
    topics = {key: {"description": key, "channels": []} for key in THEME_KEYS}
    monkeypatch.setattr(channel_topics, "load_channel_topics", lambda: topics)
    # The helper caches the file per process: drop the cache before and after
    channel_topics._read_topics.cache_clear()
    yield THEME_KEYS
    channel_topics._read_topics.cache_clear()


def _frame(rows):
    """Build a channel DataFrame the same way VideoManager.load_data does."""
    df = pd.DataFrame(rows)
    df["published_date"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    return df


def _video(title, published_at):
    return {
        "title": title,
        "url": f"https://www.youtube.com/watch?v={title[:11]}",
        "thumbnail": "",
        "channel": "fixture",
        "published_at": published_at,
        "description": "",
        "views": 10,
        "length": 120,
    }


def _days_ago(n: int) -> str:
    """ISO date n days before now, for now-relative date-filter tests."""
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


@pytest.fixture
def fixture_channels(monkeypatch):
    """Two real channels, two theme buckets and a variant dir of one theme."""
    frames = {
        "MatthewBerman": _frame([_video("mb one", _days_ago(2)), _video("mb two", _days_ago(1))]),
        "aa-gen-ai": _frame([_video("gen ai one", _days_ago(1)), _video("gen ai two", _days_ago(30))]),
        # Variant directory of the same theme bucket (get_channels folds these)
        "aa-gen-ai-videos": _frame([_video("gen ai variant", _days_ago(3))]),
        "zz-python": _frame([_video("py vid", _days_ago(1))]),
    }
    monkeypatch.setattr(tab.video_manager, "video_data", frames)
    # Freeze the loader: the fixture lives only in memory
    monkeypatch.setattr(tab.video_manager, "ensure_loaded", lambda force_refresh=False: None)
    return frames


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


def _by_id(layout, wanted_id):
    return [n for n in _walk(layout) if getattr(n, "id", None) == wanted_id]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "channel,expected",
    [
        ("aa-gen-ai", True),
        ("zz-python", True),
        ("MatthewBerman", False),
        ("aa", False),  # not a listed key
        ("AA-Gen", False),  # detection is case-sensitive on the raw dir name
        ("", False),
    ],
)
def test_is_theme_channel(channel, expected):
    assert _is_theme_channel(channel) is expected


def test_is_theme_channel_needs_the_key_not_a_prefix():
    """A theme-like prefix is not a theme: only what channels.json lists is (T-138)."""
    assert _is_theme_channel("zz-unlisted") is False
    assert _is_theme_channel("aa-unlisted-videos") is False


def test_extract_theme_options_sorted_with_default_first():
    options = _extract_theme_options(["zz-python", "MatthewBerman", "aa-gen-ai", "aa-gen-ai"])
    assert [o["value"] for o in options] == ["all", "aa-gen-ai", "zz-python"]
    assert options[0]["label"] == "Todos los temas"
    assert [o["label"] for o in options[1:]] == ["aa-gen-ai", "zz-python"]


def test_extract_theme_options_without_themes():
    assert _extract_theme_options(["MatthewBerman", "TwoMinutePapers"]) == [{"label": "Todos los temas", "value": "all"}]


def test_extract_theme_options_labels_a_theme_with_its_description(monkeypatch):
    """The dropdown leads with what the theme is about; the key is kept because it is what orders the themes."""
    monkeypatch.setattr(channel_topics, "load_channel_topics", lambda: {"zz-food": {"description": "Food Reviews", "channels": []}})
    channel_topics._read_topics.cache_clear()
    try:
        options = _extract_theme_options(["zz-food"])
    finally:
        channel_topics._read_topics.cache_clear()

    assert options[1:] == [{"label": "Food Reviews (zz-food)", "value": "zz-food"}]


def test_extract_theme_options_empty_input():
    assert _extract_theme_options([]) == [{"label": "Todos los temas", "value": "all"}]


def test_channel_matches_theme():
    assert _channel_matches_theme("aa-gen-ai", "aa-gen-ai") is True
    assert _channel_matches_theme("aa-gen-ai-videos", "aa-gen-ai") is True  # variant dir folds in
    assert _channel_matches_theme("zz-python", "aa-gen-ai") is False
    assert _channel_matches_theme("MatthewBerman", "aa-gen-ai") is False


# ---------------------------------------------------------------------------
# Filter composition in VideoManager.get_videos
# ---------------------------------------------------------------------------


def test_theme_filter_restricts_to_theme_bucket(fixture_channels):
    videos = tab.video_manager.get_videos(channel="all", theme_filter="aa-gen-ai")
    assert len(videos) == 3  # 2 from aa-gen-ai + 1 from the aa-gen-ai-videos variant dir
    assert {v["channel"] for v in videos} == {"aa-gen-ai", "aa-gen-ai-videos"}


def test_theme_filter_other_bucket(fixture_channels):
    videos = tab.video_manager.get_videos(channel="all", theme_filter="zz-python")
    assert len(videos) == 1 and videos[0]["channel"] == "zz-python"


@pytest.mark.parametrize("theme", ["all", None, ""], ids=["all", "none", "empty"])
def test_theme_filter_default_values_are_no_ops(fixture_channels, theme):
    unfiltered = tab.video_manager.get_videos(channel="all")
    assert len(tab.video_manager.get_videos(channel="all", theme_filter=theme)) == len(unfiltered) == 6


def test_theme_filter_composes_with_search(fixture_channels):
    videos = tab.video_manager.get_videos(channel="all", search_term="variant", theme_filter="aa-gen-ai")
    assert len(videos) == 1 and "variant" in videos[0]["title"]


def test_theme_filter_composes_with_date_filter(fixture_channels):
    videos = tab.video_manager.get_videos(channel="all", days_filter="7", theme_filter="aa-gen-ai")
    # gen ai two is 30 days old; only the recent ones survive the composition
    assert {v["title"] for v in videos} == {"gen ai one", "gen ai variant"}


def test_theme_filter_composes_with_channel_as_intersection(fixture_channels):
    # Disjoint selectors: no video is in both the channel and the theme
    assert tab.video_manager.get_videos(channel="MatthewBerman", theme_filter="aa-gen-ai") == []
    # Overlapping selectors: the theme filter narrows inside the channel
    assert len(tab.video_manager.get_videos(channel="aa-gen-ai", theme_filter="aa-gen-ai")) == 2
    # Channel filter narrows inside the theme too (variant dir excluded)
    assert len(tab.video_manager.get_videos(channel="aa-gen-ai-videos", theme_filter="aa-gen-ai")) == 1


# ---------------------------------------------------------------------------
# Layout + controller wiring
# ---------------------------------------------------------------------------


def test_render_videos_tab_includes_theme_dropdown(fixture_channels):
    layout = tab.render_videos_tab()
    dropdowns = _by_id(layout, "videos-theme-dropdown")
    assert len(dropdowns) == 1
    dropdown = dropdowns[0]
    assert dropdown.value == "all"
    assert dropdown.clearable is False
    assert [o["value"] for o in dropdown.options] == ["all", "aa-gen-ai", "zz-python"]
    assert dropdown.options[0]["label"] == "Todos los temas"


def test_theme_dropdown_wired_into_combined_controller(fixture_channels):
    """The Tema dropdown is an Input of the single controller callback."""
    app = dash.Dash("test-videos-theme")
    tab.register_video_callbacks(app)
    # dash 4.x keys multi-output callbacks by the flattened output list
    # (e.g. "..videos-container.children...videos-pagination.children..")
    combined = [entry for key, entry in app.callback_map.items() if "videos-container.children" in key]
    assert combined, "combined controller callback not registered"
    # "raw_inputs" in dash 4.x, "input" in dash 2.x — accept either shape
    inputs = str(combined[0].get("raw_inputs") or combined[0].get("inputs"))
    assert "videos-theme-dropdown.value" in inputs
