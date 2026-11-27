"""Unit tests for the Videos seen/watch-later + preview modal + NUEVO contracts.

Covers T-046 (spec 04 F1: seen/watch-later) and T-065 (spec 04 F3: embed
preview modal; F5: NUEVO badge + counter). Locks the DOM contract that
``assets/js/video_state.js`` depends on: cards carry ``data-video-hash`` and
``data-published-at`` plus the state/preview buttons; the layout exposes the
toolbar slot and the modal the script/callbacks use.
"""

import re
from pathlib import Path
from types import SimpleNamespace

import dash
import pandas as pd
import pytest

from src.web.dashboard.components.videos_tab import (
    _build_video_modal_content,
    _extract_youtube_id,
    _video_modal_layout,
    _video_modal_update,
    _video_registry,
    create_video_card,
    register_video_callbacks,
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
    # The close button lives in the STATIC modal shell (a string-id callback
    # Input must exist in the initial layout), not in the dynamic footer.
    from src.web.dashboard.components.videos_tab import _video_modal_layout

    assert "wt-video-modal-close" in str(_video_modal_layout())
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
# Embed-preview modal controller: only a click may change the modal
#
# The callback's first Input is pattern-matching, so it receives one n_clicks per
# card on screen and cannot tell which one changed: the click that set it running
# is in dash.ctx.triggered. Cards that were only (re)rendered are listed there as
# well, with no click on them yet.
# ---------------------------------------------------------------------------

_PREVIEW_ID = {"type": "wt-video-preview-btn", "index": None}
UNTOUCHED = (dash.no_update, dash.no_update, dash.no_update, dash.no_update)


def _two_cards():
    """Render two cards and return their (hash, video) pairs as the registry knows them."""
    pairs = []
    for video in (_VIDEO_YT, {**_VIDEO_YT, "title": "Second", "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}):
        video_hash = _card_hash(str(create_video_card(video)))
        pairs.append((video_hash, video))
    return pairs


def _preview_entry(video_hash, value):
    prop_id = f'{{"index":"{video_hash}","type":"wt-video-preview-btn"}}.n_clicks'
    return {"prop_id": prop_id, "value": value}


def _as_dash(monkeypatch, triggered, triggered_id):
    monkeypatch.setattr(dash, "ctx", SimpleNamespace(triggered=triggered, triggered_id=triggered_id))


def test_click_on_a_card_opens_its_video(monkeypatch):
    (first, _), (second, video) = _two_cards()
    _as_dash(monkeypatch, [_preview_entry(second, 1)], {**_PREVIEW_ID, "index": second})

    is_open, title, body, footer = _video_modal_update()

    assert is_open is True and title == video["title"] == "Second"  # the clicked card, not the first one
    assert "https://www.youtube-nocookie.com/embed/jNQXAC9IVRw" in str(body)
    assert "https://www.youtube.com/watch?v=jNQXAC9IVRw" in str(footer)
    assert first != second


def test_rendered_cards_alone_leave_the_modal_alone(monkeypatch):
    """Every page change re-renders the cards: the callback runs, and must change nothing."""
    (first, _), (second, _) = _two_cards()
    _as_dash(monkeypatch, [_preview_entry(first, None), _preview_entry(second, None)], {**_PREVIEW_ID, "index": first})

    assert _video_modal_update() == UNTOUCHED


def test_close_button_closes_the_modal(monkeypatch):
    _as_dash(monkeypatch, [{"prop_id": "wt-video-modal-close.n_clicks", "value": 1}], "wt-video-modal-close")

    assert _video_modal_update() == (False, *UNTOUCHED[1:])


def test_click_on_a_card_the_registry_does_not_know_opens_nothing(monkeypatch):
    _as_dash(monkeypatch, [_preview_entry("0" * 32, 1)], {**_PREVIEW_ID, "index": "0" * 32})

    assert _video_modal_update() == UNTOUCHED


def test_controller_survives_a_context_it_cannot_read(monkeypatch):
    _as_dash(monkeypatch, None, None)

    assert _video_modal_update() == UNTOUCHED


def test_modal_callback_reads_the_click_from_the_context_not_from_the_input_list(monkeypatch):
    """The ALL input is a list: comparing it with a number raised, and the modal never opened."""
    app = dash.Dash("test-video-modal")
    register_video_callbacks(app)
    key = next(k for k in app.callback_map if k.startswith("..wt-video-modal.is_open"))
    controller = app.callback_map[key]["callback"].__wrapped__
    (clicked, _), (other, _) = _two_cards()

    # The cards were rendered: the list has no click, and neither has the context
    _as_dash(monkeypatch, [_preview_entry(clicked, None), _preview_entry(other, None)], {**_PREVIEW_ID, "index": clicked})
    assert controller([None, None], None) == UNTOUCHED

    # A click on the second card: the list still carries the untouched first one
    _as_dash(monkeypatch, [_preview_entry(other, 1)], {**_PREVIEW_ID, "index": other})
    is_open, title, _, _ = controller([None, 1], None)
    assert is_open is True and title == "Second"


def test_modal_callback_wiring():
    app = dash.Dash("test-video-modal-wiring")
    register_video_callbacks(app)

    (entry,) = [e for e in app._callback_list if "wt-video-modal.is_open" in e["output"]]
    assert {"id": '{"index":["ALL"],"type":"wt-video-preview-btn"}', "property": "n_clicks"} in entry["inputs"]  # every card's ▶
    assert {"id": "wt-video-modal-close", "property": "n_clicks"} in entry["inputs"]
    assert entry["prevent_initial_call"] is True
    for slot in ("wt-video-modal.is_open", "wt-video-modal-title.children", "wt-video-modal-body.children", "wt-video-modal-footer.children"):
        assert slot in entry["output"]


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
