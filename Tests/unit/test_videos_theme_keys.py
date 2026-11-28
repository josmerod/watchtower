"""The Videos tab against the real theme keys, and a channel listed more than once (T-138).

A theme is a key of ``src/etl/goldigging/channels.json``: the directory ``goldigging_youtube_posts.py`` writes for it. The tab
used to tell a theme by the ``aa-``/``zz-`` prefix of the directory name, so the ``z-`` themes never reached its Tema dropdown.

The first tests read that tracked config file as it is today; no network and nothing under ``data/``. The rest pin the keys
they need. Data frames are hand-built and swapped into the module-level VideoManager, as in test_videos_theme_filter.py.

A channel listed under two themes is downloaded once per theme, so its videos are in both theme files. Listed twice in one
theme (the 2026-11-27 file had ``mugiwave`` and its raw channel id in ``z-soundtowork``), they are twice in one file. The tab
must show each video once and never drop it.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import md5

import pandas as pd
import pytest

from src.etl.goldigging import channel_topics
from src.web.dashboard.components import videos_tab as tab

# The regression: the two themes the prefix test ``aa-``/``zz-`` could not see.
SINGLE_Z_THEMES = ("z-sleepcore", "z-soundtowork")


def _frame(rows):
    """Build a channel DataFrame the same way VideoManager.load_data does."""
    df = pd.DataFrame(rows)
    df["published_date"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    return df


def _video(title, published_at="2026-11-20"):
    """A video record whose URL follows from its whole title: same title, same video."""
    return {
        "title": title,
        "url": f"https://www.youtube.com/watch?v={md5(title.encode()).hexdigest()[:11]}",
        "thumbnail": "",
        "channel": "fixture",
        "published_at": published_at,
        "description": "",
        "views": 10,
        "length": 120,
    }


def _days_ago(n: int) -> str:
    """ISO date n days before now."""
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


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


def _texts(layout) -> list[str]:
    roots = layout if isinstance(layout, (list, tuple)) else [layout]
    return [node for root in roots for node in _walk(root) if isinstance(node, str)]


def _by_id(layout, wanted_id) -> list:
    return [node for node in _walk(layout) if getattr(node, "id", None) == wanted_id]


def _theme_values() -> list[str]:
    return [option["value"] for option in tab._extract_theme_options(tab.video_manager.get_channels())]


def _titles(videos: list[dict]) -> list[str]:
    return [video["title"] for video in videos]


@pytest.fixture
def fixture_videos(monkeypatch: pytest.MonkeyPatch):
    """Swap the manager's data for hand-built frames and freeze its loader; returns the installer."""

    def install(frames: dict) -> dict:
        monkeypatch.setattr(tab.video_manager, "video_data", frames)
        monkeypatch.setattr(tab.video_manager, "ensure_loaded", lambda force_refresh=False: None)
        return frames

    return install


@pytest.fixture
def real_theme_keys() -> list[str]:
    """The theme keys as the real channels.json lists them today, with the file cache dropped around the test."""
    channel_topics._read_topics.cache_clear()
    keys = sorted(channel_topics.theme_names())
    channel_topics._read_topics.cache_clear()
    assert len(keys) > 1
    return keys


@contextmanager
def pinned_theme_keys(monkeypatch: pytest.MonkeyPatch, keys: tuple[str, ...]) -> Iterator[None]:
    """Answer every theme lookup from ``keys`` instead of the real file, cache dropped around it."""
    topics = {key: {"description": key, "channels": []} for key in keys}
    with monkeypatch.context() as patch:
        patch.setattr(channel_topics, "load_channel_topics", lambda: topics)
        channel_topics._read_topics.cache_clear()
        try:
            yield
        finally:
            channel_topics._read_topics.cache_clear()


# ---------------------------------------------------------------------------
# Every key of channels.json is a theme, whatever its prefix
# ---------------------------------------------------------------------------


def test_every_configured_theme_reaches_the_tema_dropdown(real_theme_keys, fixture_videos):
    frames = {key: _frame([_video(f"{key} one")]) for key in real_theme_keys}
    frames["MatthewBerman"] = _frame([_video("mb one")])
    fixture_videos(frames)

    assert _theme_values() == ["all", *real_theme_keys]


def test_the_single_z_themes_are_not_left_out(real_theme_keys, fixture_videos):
    """``z-sleepcore`` and ``z-soundtowork`` start with neither ``aa-`` nor ``zz-``: the old rule skipped them."""
    listed = [theme for theme in SINGLE_Z_THEMES if theme in real_theme_keys]
    if not listed:
        pytest.skip("channels.json no longer lists a theme with the single z- prefix")
    fixture_videos({key: _frame([_video(f"{key} one")]) for key in real_theme_keys})

    assert set(listed) <= set(_theme_values())


def test_render_offers_every_configured_theme_in_both_dropdowns(real_theme_keys, fixture_videos):
    """Tema lists the keys alone; Channel lists them first, ahead of the real channels (spec 04 V6)."""
    frames = {key: _frame([_video(f"{key} one")]) for key in real_theme_keys}
    frames["MatthewBerman"] = _frame([_video("mb one")])
    fixture_videos(frames)

    (tema,) = _by_id(tab.render_videos_tab(), "videos-theme-dropdown")
    assert [option["value"] for option in tema.options] == ["all", *real_theme_keys]
    assert tema.options[0]["label"] == "Todos los temas"
    (channel,) = _by_id(tab.render_videos_tab(), "video-channel-dropdown-new")
    assert [option["value"] for option in channel.options] == ["all", *real_theme_keys, "MatthewBerman"]


def test_the_tema_dropdown_labels_every_theme_with_its_description(real_theme_keys, fixture_videos):
    """The key is a directory name (``zz-food_reviews``): the dropdown leads with what the file says the theme is."""
    fixture_videos({key: _frame([_video(f"{key} one")]) for key in real_theme_keys})

    options = tab._extract_theme_options(tab.video_manager.get_channels())[1:]

    assert [option["value"] for option in options] == real_theme_keys
    assert [option["label"] for option in options] == [f"{channel_topics.theme_description(key)} ({key})" for key in real_theme_keys]
    assert all(option["label"] != option["value"] for option in options), "a theme without a description reads as its key"


def test_channel_stats_and_admin_header_count_every_configured_theme(real_theme_keys, fixture_videos):
    frames = {key: _frame([_video(f"{key} one")]) for key in real_theme_keys}
    frames["MatthewBerman"] = _frame([_video("mb one")])
    fixture_videos(frames)

    stats = {row["channel"]: row["is_theme"] for row in tab.video_manager.get_channel_stats()}
    assert stats == dict.fromkeys(real_theme_keys, True) | {"MatthewBerman": False}

    header = _texts(tab._channels_admin_section(tab.video_manager.get_channel_stats()))
    assert f"{len(real_theme_keys)} temas" in header  # counted, no longer described by prefix
    assert not [text for text in header if "temas (" in text]


def test_a_theme_filter_reaches_the_videos_of_a_single_z_theme(real_theme_keys, fixture_videos):
    if not all(theme in real_theme_keys for theme in SINGLE_Z_THEMES):
        pytest.skip("channels.json no longer lists both single z- themes")
    frames = {theme: _frame([_video(f"{theme} one"), _video(f"{theme} two")]) for theme in SINGLE_Z_THEMES}
    frames["MatthewBerman"] = _frame([_video("mb one")])
    fixture_videos(frames)

    assert _titles(tab.video_manager.get_videos(channel="all", theme_filter="z-soundtowork")) == ["z-soundtowork one", "z-soundtowork two"]


# ---------------------------------------------------------------------------
# A directory is a theme only while channels.json lists it
# ---------------------------------------------------------------------------


def test_a_directory_the_file_no_longer_lists_is_a_plain_channel(fixture_videos, monkeypatch):
    """A retired theme keeps its videos, under Channel like any other channel, and leaves the Tema dropdown."""
    fixture_videos(
        {
            "aa-dev": _frame([_video("dev one")]),
            "zz-retired": _frame([_video("old one")]),
            "MatthewBerman": _frame([_video("mb one")]),
        }
    )

    with pinned_theme_keys(monkeypatch, ("aa-dev",)):
        assert _theme_values() == ["all", "aa-dev"]
        (channel,) = _by_id(tab.render_videos_tab(), "video-channel-dropdown-new")
        assert [option["value"] for option in channel.options] == ["all", "aa-dev", "MatthewBerman", "zz-retired"]
        stats = {row["channel"]: row["is_theme"] for row in tab.video_manager.get_channel_stats()}
        assert stats == {"aa-dev": True, "MatthewBerman": False, "zz-retired": False}
        assert sorted(_titles(tab.video_manager.get_videos(channel="all"))) == ["dev one", "mb one", "old one"]


# ---------------------------------------------------------------------------
# A channel listed more than once
# ---------------------------------------------------------------------------


@pytest.fixture
def repeated_channel_frames() -> dict:
    """One channel under three themes, as the ETL writes it: the same three videos in each of the theme files."""
    shared = [_video(f"shared {n}", _days_ago(n)) for n in (1, 2, 3)]
    return {
        "z-sleepcore": _frame([*shared, _video("sleepcore only", _days_ago(4))]),
        "z-soundtowork": _frame([*shared, _video("soundtowork only", _days_ago(5))]),
        "zz-chill": _frame(shared),
        "MatthewBerman": _frame([_video("mb one", _days_ago(6)), _video("mb two", _days_ago(7))]),
    }


def test_a_channel_listed_under_several_themes_shows_once_in_the_all_feed(repeated_channel_frames, fixture_videos):
    frames = fixture_videos(repeated_channel_frames)
    all_urls = [video["url"] for frame in frames.values() for video in frame.to_dict("records")]

    videos = tab.video_manager.get_videos(channel="all")

    assert len(all_urls) == 13 and len(set(all_urls)) == 7  # the three shared videos are in three files each

    urls = [video["url"] for video in videos]
    assert len(urls) == len(set(urls)), "a video of the repeated channel was shown more than once"
    assert set(urls) == set(all_urls), "a video was dropped"


def test_a_channel_listed_under_several_themes_stays_under_each_of_its_themes(repeated_channel_frames, fixture_videos):
    """Filing a channel under several themes is the user's choice: each theme keeps its videos."""
    fixture_videos(repeated_channel_frames)

    per_theme = {theme: _titles(tab.video_manager.get_videos(channel="all", theme_filter=theme)) for theme in ("z-sleepcore", "z-soundtowork", "zz-chill")}

    assert [len(titles) for titles in per_theme.values()] == [4, 4, 3]
    for titles in per_theme.values():
        assert [title for title in titles if title.startswith("shared")] == ["shared 1", "shared 2", "shared 3"]


def test_the_first_page_shows_a_channel_listed_under_several_themes_once(repeated_channel_frames, fixture_videos):
    fixture_videos(repeated_channel_frames)

    assert "📺 Showing 7 videos from all channels" in _texts(tab.get_initial_video_display(limit=48))


def test_a_channel_listed_twice_in_one_theme_shows_once(fixture_videos):
    """The same video twice in one file, as a handle listed next to its own channel id produces."""
    twice = _video("mugiwave one", _days_ago(1))
    fixture_videos(
        {
            "z-soundtowork": _frame([twice, _video("other one", _days_ago(2)), {**twice, "views": 11}, _video("mugiwave two", _days_ago(3))]),
            "MatthewBerman": _frame([_video("mb one", _days_ago(4))]),
        }
    )

    in_theme = ["mugiwave one", "other one", "mugiwave two"]
    assert _titles(tab.video_manager.get_videos(channel="z-soundtowork")) == in_theme
    assert _titles(tab.video_manager.get_videos(channel="all", theme_filter="z-soundtowork")) == in_theme
    assert _titles(tab.video_manager.get_videos(channel="all")) == [*in_theme, "mb one"]
    assert "📺 Showing 4 videos from all channels" in _texts(tab.get_initial_video_display(limit=48))
