"""Unit tests for the 2026-08 audit quick-win fixes.

Covers:
- Valencia events: upcoming-event window (lower bound + ISO date support)
- News tab: search input IDs derived from tab definitions
- Scavenging ETL: ${VAR} environment-token expansion for feed URLs
"""

from datetime import datetime, timedelta

import pytest

from src.etl.goldigging.goldigging_scavenging_etl import _expand_env_tokens
from src.web.dashboard.components.news_tab import NEWS_TAB_DEFINITIONS, _search_id_for_tab
from src.web.dashboard.components.shortcuts_tab import _normalize_shortcuts_dict, _normalize_url
from src.web.dashboard.components.valencia_events_new_tab import _is_upcoming_event, _parse_event_date


class TestIsUpcomingEvent:
    """The upcoming view must only contain events in the future."""

    def test_past_event_is_not_upcoming(self):
        past = (datetime.now() - timedelta(days=3)).strftime("%d/%m/%Y")
        assert _is_upcoming_event(past, datetime.now(), datetime.now() + timedelta(days=30)) is False

    def test_future_event_within_horizon_is_upcoming(self):
        soon = (datetime.now() + timedelta(days=10)).strftime("%d/%m/%Y")
        assert _is_upcoming_event(soon, datetime.now(), datetime.now() + timedelta(days=30)) is True

    def test_event_beyond_horizon_is_not_upcoming(self):
        far = (datetime.now() + timedelta(days=60)).strftime("%d/%m/%Y")
        assert _is_upcoming_event(far, datetime.now(), datetime.now() + timedelta(days=30)) is False

    def test_iso_date_is_parsed(self):
        iso = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        assert _is_upcoming_event(iso, datetime.now(), datetime.now() + timedelta(days=30)) is True

    def test_unparseable_date_is_rejected(self):
        assert _is_upcoming_event("not a date", datetime.now(), datetime.now() + timedelta(days=30)) is False

    def test_parse_event_date_formats(self):
        assert _parse_event_date("25/12/2026") == datetime(2026, 12, 25)
        assert _parse_event_date("2026-12-25") == datetime(2026, 12, 25)
        assert _parse_event_date("2026-12-25T10:00:00") == datetime(2026, 12, 25)
        assert _parse_event_date("") is None


class TestNewsSearchIds:
    """Every tab definition must yield exactly one wired search input ID."""

    def test_definitions_exist(self):
        # 20 desde T-044 (Google AI/KDNuggets/Cloud Updates viven solo en Tech Radar)
        assert len(NEWS_TAB_DEFINITIONS) >= 20

    def test_search_id_for_single_source(self):
        tab = {"label": "Lobsters", "keys": "lobsters", "id": "lobsters"}
        assert _search_id_for_tab(tab) == "news-search-lobsters"

    def test_search_id_for_combined_source(self):
        tab = {"label": "Top Tech", "keys": ["techcrunch", "venturebeat", "arstechnica", "kagi_ai"], "id": "top_tech"}
        assert _search_id_for_tab(tab) == "news-search-techcrunch-venturebeat-arstechnica-kagi_ai"

    @pytest.mark.parametrize(
        ("label", "expected_key"),
        [
            ("🇪🇸 Spanish Tech", "spanish_tech"),
            ("📍 Valencia Local", "valencia_local"),
        ],
    )
    def test_previously_dead_subtabs_have_search_ids(self, label, expected_key):
        """Subtabs whose search boxes were dead before the fix.

        (Cloud Updates se movió a Tech-Radar-only en T-044; su búsqueda ya no
        es un subtab de News.)
        """
        tab = next(t for t in NEWS_TAB_DEFINITIONS if t["label"] == label)
        assert _search_id_for_tab(tab) == f"news-search-{expected_key}"


class TestScavengingEnvTokens:
    """IPTorrents credentials must come from the environment, not the config."""

    def test_expands_known_env_var(self, monkeypatch):
        monkeypatch.setenv("IPT_USER_ID", "12345")
        monkeypatch.setenv("IPT_PASSKEY", "abc")
        url = "https://iptorrents.com/t.rss?u=${IPT_USER_ID};tp=${IPT_PASSKEY};60;download"
        expanded, missing = _expand_env_tokens(url)
        assert expanded == "https://iptorrents.com/t.rss?u=12345;tp=abc;60;download"
        assert missing == []

    def test_reports_missing_env_vars(self, monkeypatch):
        monkeypatch.delenv("IPT_USER_ID", raising=False)
        monkeypatch.delenv("IPT_PASSKEY", raising=False)
        url = "https://iptorrents.com/t.rss?u=${IPT_USER_ID};tp=${IPT_PASSKEY};60;download"
        expanded, missing = _expand_env_tokens(url)
        assert set(missing) == {"IPT_USER_ID", "IPT_PASSKEY"}
        assert "${IPT_USER_ID}" in expanded

    def test_plain_url_is_untouched(self):
        expanded, missing = _expand_env_tokens("https://nyaa.si/?page=rss")
        assert expanded == "https://nyaa.si/?page=rss"
        assert missing == []


class TestShortcutsHelpers:
    """Shortcuts CRUD helpers (spec 02)."""

    def test_normalize_url_adds_scheme(self):
        assert _normalize_url("example.com/x") == "https://example.com/x"

    def test_normalize_url_accepts_https(self):
        assert _normalize_url("https://a.b/c") == "https://a.b/c"

    def test_normalize_url_rejects_garbage(self):
        assert _normalize_url("not a url") is None
        assert _normalize_url("") is None
        assert _normalize_url("ftp://only") is None

    def test_normalize_shortcuts_dict_both_formats(self):
        modern = {"Tools": [{"name": "A", "url": "u"}]}
        legacy = {"categories": [{"category": "Tools", "items": [{"name": "B", "url": "v"}]}]}
        assert _normalize_shortcuts_dict(modern) == modern
        assert _normalize_shortcuts_dict(legacy) == {"Tools": [{"name": "B", "url": "v"}]}
        assert _normalize_shortcuts_dict(["not", "a", "dict"]) == {}
