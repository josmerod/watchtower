"""Tests for the Knowledge Garden's subtab list (T-127).

Guards on `KNOWLEDGE_TAB_DEFINITIONS`:

- every subtab key must resolve to a configured source (the render path indexes
  `KNOWLEDGE_SOURCES_CONFIG[key]["name"]` directly);
- every configured source must be reachable from a subtab: the API and the
  health dots list the whole config, so a config entry without a subtab would
  be an invisible source;
- sources the user removed on purpose stay out of the garden.

`Trendshift` left with T-127 (it stored a name, a link and "now" as the date)
and came back with T-134: one record per repository with its description,
language, stars and trend figure.
"""

from src.services.data_loader import KNOWLEDGE_SOURCES_CONFIG
from src.web.dashboard.components.knowledge_garden_tab import KNOWLEDGE_TAB_DEFINITIONS

REMOVED_FROM_GARDEN = ("gittrends", "stackoverflow_trends", "reddit_unified", "reddit_ai_ml", "reddit_programming", "reddit_devops")


def _subtab_keys():
    keys = []
    for tab in KNOWLEDGE_TAB_DEFINITIONS:
        keys.extend([tab["keys"]] if isinstance(tab["keys"], str) else tab["keys"])
    return keys


def test_every_subtab_key_resolves_to_a_configured_source():
    missing = sorted(set(_subtab_keys()) - set(KNOWLEDGE_SOURCES_CONFIG))
    assert missing == []


def test_every_configured_source_is_reachable_from_a_subtab():
    unreachable = sorted(set(KNOWLEDGE_SOURCES_CONFIG) - set(_subtab_keys()))
    assert unreachable == []


def test_low_quality_sources_stay_out_of_the_garden():
    assert set(_subtab_keys()).isdisjoint(REMOVED_FROM_GARDEN)
    assert set(KNOWLEDGE_SOURCES_CONFIG).isdisjoint(REMOVED_FROM_GARDEN)
