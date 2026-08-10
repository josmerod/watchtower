"""Tests for the notifications tab functionality.

Covers the live ``NotificationsManager`` / ``AlertRulesRepository`` API and the
``_get_rule_id`` helper. Tests run against a temporary ``data/`` root so no real
alert state is touched.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from src.web.dashboard.components.notifications_tab import (
    NotificationsManager,
    _get_rule_id,
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
        """Manager initializes with the default user and ensures the data dir."""
        manager = NotificationsManager()
        assert manager.user_id == "default_user"
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
        """``AlertRulesRepository.save_rule`` persists and is readable by the manager.

        Regression test for the bug where ``save_rule`` called ``self.load_rules()``
        (undefined on the repository), so it always raised and returned ``False``.
        Also covers the fresh-store case where the rules file does not exist yet.
        """
        manager = NotificationsManager()
        rule: dict[str, Any] = {"id": "rule-1", "name": "A", "active": True}
        assert manager.rules_repo.save_rule(rule) is True
        assert len(manager.load_rules()) == 1

    def test_repo_save_rule_updates_existing(self, isolated_data_root: Path) -> None:
        """Saving a rule with an existing id replaces it (no duplicates)."""
        manager = NotificationsManager()
        repo = manager.rules_repo
        repo.save_rule({"id": "r1", "name": "original", "active": True})
        repo.save_rule({"id": "r1", "name": "updated", "active": False})

        # Fresh manager so the cache doesn't mask the write.
        rules = NotificationsManager().load_rules()
        assert len(rules) == 1
        assert rules[0]["name"] == "updated"

    def test_repo_delete_rule(self, isolated_data_root: Path) -> None:
        """``AlertRulesRepository.delete_rule`` removes a rule by id."""
        manager = NotificationsManager()
        repo = manager.rules_repo
        repo.save_rule({"id": "rule-1", "name": "A"})
        assert repo.delete_rule("rule-1") is True
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
