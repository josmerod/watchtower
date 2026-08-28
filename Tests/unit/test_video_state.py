"""Unit tests for the Videos seen/watch-later + preview modal + NUEVO contracts.

Covers T-046 (spec 04 F1: seen/watch-later) and T-065 (spec 04 F3: embed
preview modal; F5: NUEVO badge + counter). Locks the DOM contract that
``assets/js/video_state.js`` depends on: cards carry ``data-video-hash`` and
``data-published-at`` plus the state/preview buttons; the layout exposes the
toolbar slot and the modal the script/callbacks use.
"""

import re
from pathlib import Path

import pandas as pd
import pytest

from src.web.dashboard.components.videos_tab import (
    _build_video_modal_content,
    _extract_youtube_id,
    _video_modal_layout,
    _video_registry,
    create_video_card,
)

_VIDEO = {"url": "https://youtu.be/abc", "title": "Test video", "channel": "Chan", "length": 120, "views": 10}
# Full 11-char YouTube id (the only shape the extraction accepts)
_VIDEO_YT = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "title": "Embeddable", "channel": "Chan", "published_at": "2026-08-20"}
_JS_PATH = Path(__file__).resolve().parents[2] / "src" / "web" / "dashboard" / "assets" / "js" / "video_state.js"


def _card_hash(card_repr: str) -> str:
    match = re.search(r"data-video-hash='?\"?([0-9a-f]{32})", card_repr)
    assert match, "card repr missing data-video-hash"
    return match.group(1)


def test_card_carries_video_hash_and_state_buttons():
    card = create_video_card(_VIDEO)
    s = str(card)
    assert "data-video-hash" in s
    assert "wt-video-seen-btn" in s
    assert "wt-video-later-btn" in s


def test_card_hash_is_stable_and_url_derived():
    a = str(create_video_card(_VIDEO))
    b = str(create_video_card({**_VIDEO, "title": "Renamed"}))
    hash_a, hash_b = _card_hash(a), _card_hash(b)
    assert hash_a == hash_b and len(hash_a) == 32  # md5 of the URL


def test_toolbar_slot_in_layout():
    from pathlib import Path

    from src.web.dashboard.components.videos_tab import render_videos_tab
    from src.web.dashboard.utils import get_data_path

    if not (Path(get_data_path("youtube")).exists()):
        pytest.skip("no local youtube data — toolbar only renders in the full layout")
    assert "videos-state-toolbar" in str(render_videos_tab())


# ---------------------------------------------------------------------------
# T-065 — spec 04 F3: embed-preview modal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?app=desktop&v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=30", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://vimeo.com/123456789", None),  # not YouTube
        ("https://youtu.be/abc", None),  # too short to be a real id
        ("", None),
        (None, None),
    ],
)
def test_extract_youtube_id_variants(url, expected):
    assert _extract_youtube_id(url) == expected


def test_card_has_preview_button_with_pattern_id():
    """The ▶ overlay carries the pattern id the modal callback matches on."""
    card = str(create_video_card(_VIDEO_YT))
    assert "wt-video-preview-btn" in card
    # pattern id: {"type": ..., "index": <hash>}
    match = re.search(r"type.{0,4}wt-video-preview-btn", card)
    assert match, "preview button id is not pattern-matching on type"
    index_match = re.search(r"index.{0,4}([0-9a-f]{32})", card)
    assert index_match, "preview button id is missing the per-card index"
    assert index_match.group(1) == _card_hash(card)


def test_card_registers_video_for_modal_lookup():
    """The hash the button carries must resolve back to the video record."""
    card_str = str(create_video_card(_VIDEO_YT))
    video = _video_registry.get(_card_hash(card_str))
    assert video is not None
    assert video["title"] == "Embeddable"
    assert video["url"] == _VIDEO_YT["url"]


def test_card_without_youtube_id_omits_preview_button():
    card = str(create_video_card({**_VIDEO_YT, "url": "https://vimeo.com/123456789"}))
    assert "wt-video-preview-btn" not in card


def test_modal_content_contains_nocookie_embed():
    """Modal body embeds via youtube-nocookie for the fixture video (F3)."""
    title, body, footer = _build_video_modal_content(_VIDEO_YT)
    body_str = str(body)
    assert title == "Embeddable"
    assert "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" in body_str
    assert "fullscreen" in body_str and "allow=" in body_str
    # 16:9 responsive box
    assert "56.25%" in body_str
    footer_str = str(footer)
    assert "wt-video-modal-close" in footer_str
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in footer_str


def test_modal_shell_starts_closed_with_slots():
    shell = str(_video_modal_layout())
    for el in ("wt-video-modal", "wt-video-modal-title", "wt-video-modal-body", "wt-video-modal-footer"):
        assert el in shell
    assert "is_open" in shell  # starts closed


def test_modal_in_layout_when_data_present():
    from src.web.dashboard.components.videos_tab import render_videos_tab
    from src.web.dashboard.utils import get_data_path

    if not (Path(get_data_path("youtube")).exists()):
        pytest.skip("no local youtube data — modal only renders in the full layout")
    layout = str(render_videos_tab())
    assert "wt-video-modal" in layout
    assert "wt-video-modal-title" in layout
    assert "wt-video-modal-body" in layout
    assert "wt-video-modal-footer" in layout


# ---------------------------------------------------------------------------
# T-065 — spec 04 F5: NUEVO badge + counter
# ---------------------------------------------------------------------------


def test_card_carries_published_date_attribute():
    """Parsed published_date wins; raw published_at is the fallback."""
    dated = str(create_video_card({**_VIDEO_YT, "published_date": pd.Timestamp("2026-08-20T10:00:00+00:00")}))
    assert "data-published-at" in dated
    assert "2026-08-20T10:00:00+00:00" in dated

    raw_only = str(create_video_card(_VIDEO_YT))
    assert "data-published-at" in raw_only
    assert "2026-08-20" in raw_only


def test_card_without_publish_date_has_empty_attribute():
    undated = str(create_video_card({"url": _VIDEO_YT["url"], "title": "No date"}))
    # Attribute always present; empty value is falsy so the JS skips it.
    assert "data-published-at=''" in undated or 'data-published-at=""' in undated


def test_js_contract_for_nuevo_badges():
    """Lock the hook points video_state.js must keep for F5."""
    js = _JS_PATH.read_text(encoding="utf-8")
    assert "wt_videos_last_visit" in js, "localStorage last-visit key renamed"
    assert "data-published-at" in js, "published-date attribute no longer read"
    assert "wt-video-new-badge" in js, "badge class renamed"
    assert "NUEVO" in js, "badge label changed"
    assert "wt-video-counts" in js, "toolbar counter target changed"
    # House rules: observer debounced, last-visit bump debounced
    assert "MutationObserver" in js and "scheduleRefresh" in js
    assert js.count("setTimeout") >= 2, "debounces removed (observer + last-visit stamp)"
