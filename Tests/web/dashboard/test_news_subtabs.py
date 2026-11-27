"""Tests for the News tab's subtab list (T-126).

Two guards on `NEWS_TAB_DEFINITIONS`:

- every subtab key must resolve to a configured source, because a single-key
  subtab whose key is gone raises `KeyError` when the tab renders;
- sources the user removed on purpose stay out of News.
"""

from src.services.data_loader import NEWS_SOURCES_CONFIG
from src.web.dashboard.components.news_tab import _ALL_NEWS_SOURCES, NEWS_TAB_DEFINITIONS

REMOVED_FROM_NEWS = ("freecodecamp", "kagi_usa", "kagi_world")


def _subtab_keys():
    keys = []
    for tab in NEWS_TAB_DEFINITIONS:
        keys.extend([tab["keys"]] if isinstance(tab["keys"], str) else tab["keys"])
    return keys


def test_every_subtab_key_resolves_to_a_configured_source():
    missing = sorted(set(_subtab_keys()) - set(_ALL_NEWS_SOURCES))
    assert missing == []


def test_subtab_keys_carry_no_dash():
    # The search callback splits the input ID on "-" to recover the keys, so a key with a dash would break it.
    assert not [key for key in _subtab_keys() if "-" in key]


def test_low_quality_sources_stay_out_of_news():
    assert set(_subtab_keys()).isdisjoint(REMOVED_FROM_NEWS)
    assert set(NEWS_SOURCES_CONFIG).isdisjoint(REMOVED_FROM_NEWS)
