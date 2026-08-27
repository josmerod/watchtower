"""Unit tests for the Videos seen/watch-later contract (T-046, spec 04 F1).

Locks the DOM contract that ``assets/js/video_state.js`` depends on: cards
carry ``data-video-hash`` and the two state buttons; the layout exposes the
toolbar slot the script fills.
"""

from src.web.dashboard.components.videos_tab import create_video_card

_VIDEO = {"url": "https://youtu.be/abc", "title": "Test video", "channel": "Chan", "length": 120, "views": 10}


def test_card_carries_video_hash_and_state_buttons():
    card = create_video_card(_VIDEO)
    s = str(card)
    assert "data-video-hash" in s
    assert "wt-video-seen-btn" in s
    assert "wt-video-later-btn" in s


def test_card_hash_is_stable_and_url_derived():
    a = str(create_video_card(_VIDEO))
    b = str(create_video_card({**_VIDEO, "title": "Renamed"}))
    hash_a = a.split('data-video-hash="')[1].split('"')[0]
    hash_b = b.split('data-video-hash="')[1].split('"')[0]
    assert hash_a == hash_b and len(hash_a) == 32  # md5 of the URL


def test_toolbar_slot_in_layout():
    from src.web.dashboard.components.videos_tab import render_videos_tab

    assert "videos-state-toolbar" in str(render_videos_tab())
