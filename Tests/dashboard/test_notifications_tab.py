"""Tests for the notifications tab functionality.

Covers the live ``NotificationsManager`` / ``AlertRulesRepository`` API and the
``_get_rule_id`` helper. Tests run against a temporary ``data/`` root so no real
alert state is touched.
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from src.services.watcher_events import EventGroup, WatcherEventsSummary
from src.web.dashboard.components.notifications_tab import (
    NotificationsManager,
    _get_rule_id,
    render_daily_summary_section,
    render_notifications_tab,
    render_rules_list,
)


@pytest.fixture()
def isolated_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run with ``data/`` rooted inside a temp directory.

    The notifications module resolves paths relative to the CWD (``Path("data/...")``),
    so chdir into the temp root to keep tests hermetic.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestGetRuleId:
    """Tests for the ``_get_rule_id`` helper."""

    def test_get_rule_id_with_object(self) -> None:
        """An object with an ``id`` attribute yields its id."""
        rule = Mock()
        rule.id = "test-id"
        assert _get_rule_id(rule) == "test-id"

    def test_get_rule_id_with_dict(self) -> None:
        """A dict with an ``id`` key yields its id."""
        rule = {"id": "test-id", "name": "Test Rule"}
        assert _get_rule_id(rule) == "test-id"

    def test_get_rule_id_with_string(self) -> None:
        """A bare id value is returned as a string."""
        assert _get_rule_id("test-id") == "test-id"

    def test_get_rule_id_empty(self) -> None:
        """A dict without ``id`` yields an empty string."""
        assert _get_rule_id({"name": "Test Rule"}) == ""

    def test_get_rule_id_object_without_id(self) -> None:
        """An object without an ``id`` attribute falls back to its string form."""
        rule = Mock(spec=[])
        # No `id` attribute -> str(rule)
        assert _get_rule_id(rule) == str(rule)


class TestNotificationsManager:
    """Tests for the live ``NotificationsManager``."""

    def test_initialization(self, isolated_data_root: Path) -> None:
        """Manager initializes with the shared rules path and ensures the data dir."""
        manager = NotificationsManager()
        assert manager.rules_file == Path("data/alerts/rules.json")
        assert (isolated_data_root / "data" / "alerts").exists()

    def test_load_rules_empty_when_no_file(self, isolated_data_root: Path) -> None:
        """``load_rules`` returns an empty list when no rules file exists."""
        manager = NotificationsManager()
        assert manager.load_rules() == []

    def test_save_and_load_rule_roundtrip(self, isolated_data_root: Path) -> None:
        """A rule written to the rules file is retrievable by the manager.

        ``AlertRulesRepository.save_rule`` currently references ``self.load_rules()``
        which does not exist on the repository (only on ``NotificationsManager``),
        so it raises and is swallowed to ``False``. We write the file directly to
        exercise the read path that ``NotificationsManager.load_rules`` relies on.
        """
        import json

        manager = NotificationsManager()
        rule: dict[str, Any] = {
            "id": "rule-1",
            "name": "Test Rule",
            "conditions": [{"condition_type": "keyword_match", "value": "python"}],
            "active": True,
        }
        # Write directly (mirrors the file contract save_rule targets).
        rules_file = isolated_data_root / "data" / "alerts" / "rules.json"
        rules_file.write_text(json.dumps([rule]), encoding="utf-8")

        loaded = manager.load_rules()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "rule-1"
        assert loaded[0]["conditions"][0]["value"] == "python"

    def test_repo_save_rule_roundtrip(self, isolated_data_root: Path) -> None:
        """``NotificationsManager.save_rule`` persists and is readable back.

        Also covers the fresh-store case where the rules file does not exist yet.
        """
        manager = NotificationsManager()
        rule: dict[str, Any] = {"id": "rule-1", "name": "A", "active": True}
        assert manager.save_rule(rule) is True
        assert len(manager.load_rules()) == 1

    def test_repo_save_rule_updates_existing(self, isolated_data_root: Path) -> None:
        """Saving a rule with an existing id replaces it (no duplicates)."""
        manager = NotificationsManager()
        manager.save_rule({"id": "r1", "name": "original", "active": True})
        manager.save_rule({"id": "r1", "name": "updated", "active": False})

        rules = NotificationsManager().load_rules()
        assert len(rules) == 1
        assert rules[0]["name"] == "updated"

    def test_repo_delete_rule(self, isolated_data_root: Path) -> None:
        """``NotificationsManager.delete_rule`` removes a rule by id."""
        manager = NotificationsManager()
        manager.save_rule({"id": "rule-1", "name": "A"})
        assert manager.delete_rule("rule-1") is True
        assert NotificationsManager().load_rules() == []


class TestRenderFunctions:
    """Smoke tests that the render helpers build a layout without raising."""

    def test_render_notifications_tab_returns_container(self) -> None:
        """``render_notifications_tab`` returns a Dash component."""
        layout = render_notifications_tab()
        assert layout is not None

    def test_render_rules_list_empty(self) -> None:
        """``render_rules_list`` handles an empty rule list."""
        layout = render_rules_list([])
        assert layout is not None

    def test_render_rules_list_with_rules(self) -> None:
        """``render_rules_list`` renders one row per rule."""
        rules = [
            {"id": "r1", "name": "First", "active": True},
            {"id": "r2", "name": "Second", "active": False},
        ]
        layout = render_rules_list(rules)
        assert layout is not None


def _iter_text(component: Any) -> Any:
    """Yield every text string in a Dash component tree."""
    if isinstance(component, str):
        yield component
        return
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _iter_text(child)
    else:
        yield from _iter_text(children)


class TestRenderSeverityBadge:
    """Watcher-managed rules carry a severity; the rules list surfaces it (T-052)."""

    FRESHNESS_RULE: dict[str, Any] = {
        "id": "data_freshness_t",
        "name": "Freshness: Test",
        "description": "Fuente Test sin datos desde 2026-08-26 18:00 UTC (30h)",
        "severity": "high",
        "active": True,
    }

    def test_high_severity_badge_and_message_render(self) -> None:
        """A high-severity freshness rule shows its badge and message."""
        texts = list(_iter_text(render_rules_list([self.FRESHNESS_RULE])))
        assert "HIGH" in texts
        assert any("Fuente Test sin datos" in t for t in texts)
        assert any("(30h)" in t for t in texts)

    def test_medium_severity_badge(self) -> None:
        """A medium-severity rule renders a MEDIUM badge."""
        rule = {**self.FRESHNESS_RULE, "severity": "medium"}
        assert "MEDIUM" in list(_iter_text(render_rules_list([rule])))

    def test_rules_without_severity_render_without_badge(self) -> None:
        """Plain user rules keep the original rendering (no severity badge)."""
        texts = list(_iter_text(render_rules_list([{"id": "r1", "name": "Plain", "active": True}])))
        assert "HIGH" not in texts
        assert "MEDIUM" not in texts
        assert "Active" in texts


def _daily_summary(groups: list[EventGroup] | None = None) -> WatcherEventsSummary:
    """Build a summary fixture (default: courses x2 + data_freshness x1)."""
    if groups is None:
        groups = [
            EventGroup(
                watcher="courses",
                event_type="new_matching_course",
                count=2,
                latest=datetime(2026, 9, 3, 10, 0, 0),
                latest_relative="hace 2 h",
                message="Nuevo curso que matchea tus keywords: Python avanzado",
            ),
            EventGroup(
                watcher="data_freshness",
                event_type="freshness_stale_to_critical",
                count=1,
                latest=datetime(2026, 9, 3, 9, 0, 0),
                latest_relative="hace 3 h",
                message="Itch.io trending: stale → critical (27 h sin datos)",
            ),
        ]
    per_watcher: dict[str, int] = {}
    for group in groups:
        per_watcher[group.watcher] = per_watcher.get(group.watcher, 0) + group.count
    return WatcherEventsSummary(
        total=sum(group.count for group in groups),
        window_hours=24,
        groups=groups,
        per_watcher=per_watcher,
        generated_at=datetime(2026, 9, 3, 12, 0, 0),
    )


def _iter_ids(component: Any) -> Any:
    """Yield every component id in a Dash component tree."""
    comp_id = getattr(component, "id", None)
    if isinstance(comp_id, str):
        yield comp_id
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _iter_ids(child)
    else:
        yield from _iter_ids(children)


class TestDailySummarySection:
    """The 'Últimas 24h' resumen of watcher events (T-083)."""

    def test_zero_events_renders_calm_copy(self) -> None:
        """No events render a calm muted note, not an alarm."""
        texts = list(_iter_text(render_daily_summary_section(_daily_summary(groups=[]))))
        assert any("Sin eventos en las últimas 24h" in t for t in texts)

    def test_headline_counts_events(self) -> None:
        """The headline states the total for the window."""
        joined = "".join(_iter_text(render_daily_summary_section(_daily_summary())))
        assert "3 eventos en las últimas 24h" in joined

    def test_singular_headline(self) -> None:
        """One event reads in singular."""
        group = EventGroup(
            watcher="courses",
            event_type="new_matching_course",
            count=1,
            latest=datetime(2026, 9, 3, 10, 0, 0),
            latest_relative="hace 2 h",
            message="Nuevo curso",
        )
        joined = "".join(_iter_text(render_daily_summary_section(_daily_summary(groups=[group]))))
        assert "1 evento en las últimas 24h" in joined

    def test_group_rows_show_badges_message_and_relative_time(self) -> None:
        """Each group row shows watcher, type, sample message, count and 'hace Xh'."""
        texts = list(_iter_text(render_daily_summary_section(_daily_summary())))
        assert "courses" in texts
        assert "new_matching_course" in texts
        assert any("Nuevo curso que matchea tus keywords" in t for t in texts)
        assert "×2" in texts
        assert "hace 2 h" in texts
        assert "hace 3 h" in texts

    def test_per_watcher_footer(self) -> None:
        """The per-watcher breakdown is surfaced as a footer."""
        texts = list(_iter_text(render_daily_summary_section(_daily_summary())))
        assert any(t.startswith("Por watcher:") for t in texts)
        assert any("courses: 2" in t for t in texts)
        assert any("data_freshness: 1" in t for t in texts)

    def test_tab_layout_keeps_rules_ids_and_adds_summary_ids(self) -> None:
        """The rules section ids stay intact and the summary ids are added."""
        ids = set(_iter_ids(render_notifications_tab()))
        for existing in ("rules-list-container", "rule-save-status", "create-rule-btn", "reload-rules-btn", "rule-modal"):
            assert existing in ids
        for new in ("daily-summary-container", "daily-summary-refresh-btn"):
            assert new in ids
