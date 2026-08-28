"""Tests for the Videos 📡 Canales admin view (spec 04 F4, T-074).

Fixture-based — swaps the module-level VideoManager's in-memory data with
hand-built DataFrames; no data/ files and no network.
"""

import dash
import pandas as pd
import pytest

from src.web.dashboard.components import videos_tab as tab


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


@pytest.fixture
def fixture_channels(monkeypatch):
    """Two variant dirs of one channel plus a theme bucket."""
    frames = {
        "MatthewBerman": _frame([_video("alpha vid", "2026-08-25"), _video("beta vid", "2026-08-27")]),
        "MatthewBerman-videos": _frame([_video("gamma vid", "2026-08-20")]),
        "aa-gen-ai": _frame([_video("delta vid", "2026-08-26"), _video("epsilon vid", "2026-08-18"), _video("zeta vid", "2026-08-24")]),
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


def _texts(layout):
    return [n for n in _walk(layout) if isinstance(n, str)]


def _by_id(layout, wanted_id):
    return [n for n in _walk(layout) if getattr(n, "id", None) == wanted_id]


def test_get_channel_stats_folds_variant_dirs(fixture_channels):
    stats = tab.video_manager.get_channel_stats()
    channels = {s["channel"] for s in stats}
    assert "MatthewBerman" in channels  # canonical display name wins
    assert "matthew-berman" not in channels  # variant dir folded into it
    assert "aa-gen-ai" in channels

    by_channel = {s["channel"]: s for s in stats}
    assert by_channel["MatthewBerman"]["count"] == 3  # 2 + 1 across variant dirs
    assert by_channel["MatthewBerman"]["last_seen"] == "2026-08-27"  # newest across both dirs
    assert "MatthewBerman-videos" not in by_channel  # variant dir folded away
    assert by_channel["aa-gen-ai"]["count"] == 3
    assert by_channel["aa-gen-ai"]["last_seen"] == "2026-08-26"
    assert by_channel["aa-gen-ai"]["is_theme"] is True  # aa-*/zz-* buckets are themes
    assert by_channel["MatthewBerman"]["is_theme"] is False
    # Sorted by count desc
    assert stats[0]["count"] >= stats[-1]["count"]


def test_render_videos_tab_shows_channels_section(fixture_channels):
    layout = tab.render_videos_tab()
    texts = _texts(layout)
    # Toggle button present with the folded channel count
    toggle = _by_id(layout, "videos-channels-toggle")
    assert len(toggle) == 1 and toggle[0].children == "📡 Canales (2)"
    # Collapsed by default
    collapse = _by_id(layout, "videos-channels-collapse")
    assert len(collapse) == 1 and collapse[0].is_open is False
    # Counts and dates from the fixture appear inside the summary table
    assert "MatthewBerman" in texts
    assert "aa-gen-ai" in texts
    assert "2026-08-27" in texts
    assert "tema" in texts and "canal" in texts  # type badges
    assert "6 vídeos" in " ".join(texts)  # header total: 3 + 3


def test_channels_admin_section_empty_state():
    card = tab._channels_admin_section([])
    assert "Sin canales cargados." in _texts(card)


def test_channels_collapse_callback_registered(fixture_channels):
    app = dash.Dash("test-videos-channels")
    tab.register_video_callbacks(app)
    assert "videos-channels-collapse.is_open" in " ".join(app.callback_map.keys())
