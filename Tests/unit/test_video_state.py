"""Unit tests for the Videos seen/watch-later contract (T-046, spec 04 F1).

Locks the DOM contract that ``assets/js/video_state.js`` depends on: cards
carry ``data-video-hash`` and the two state buttons; the layout exposes the
toolbar slot the script fills.
"""

import re

import pytest

from src.web.dashboard.components.videos_tab import create_video_card

_VIDEO = {"url": "https://youtu.be/abc", "title": "Test video", "channel": "Chan", "length": 120, "views": 10}


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
