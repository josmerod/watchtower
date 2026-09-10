"""Integration tests for the BaseWatcher change-detection workflow.

The alert-engine evaluation hooks were removed with the engine (2026-09-10
cleanup): watchers persist their own events and the Notifications tab reads the
shared ``data/alerts/rules.json`` store. What remains under test here is the
core loop — check → extract → change detection → alarm → event recording.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.watchers.base_watcher import BaseWatcher


class MockWatcher(BaseWatcher):
    """Concrete watcher for tests (hoisted: the fixture-local class raised
    NameError in tests that re-instantiated it directly)."""

    def extract_value(self, html_content: str):
        return f"Extracted value from {self.name}"

    def has_changed(self, old_value, new_value):
        return old_value != new_value

    def fetch_page(self):
        return "<html>Mock HTML content</html>"


class TestBaseWatcherIntegration:
    """Test the BaseWatcher change-detection workflow end to end."""

    @pytest.fixture()
    def mock_watcher(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Create a mock BaseWatcher isolated in a temporary data root."""
        monkeypatch.chdir(tmp_path)
        watcher = MockWatcher(
            name="test_watcher",
            url="https://example.com/test",
            check_interval=1,  # 1 second for testing
        )
        # data_dir/events_dir anchor to the repo root (file-based discovery),
        # so point them at the tmp root to keep event writes isolated.
        isolated_events = tmp_path / "data" / "watchers" / "test_watcher" / "events"
        isolated_events.mkdir(parents=True, exist_ok=True)
        watcher.events_dir = isolated_events
        return watcher

    def test_trigger_alarm_records_change_event(self, mock_watcher):
        """trigger_alarm logs and records a change_detected event, no engine."""
        mock_watcher.trigger_alarm("old_value", "new_value")

        events = list(mock_watcher.events_dir.glob("*.json"))
        assert len(events) == 1
        assert "change_detected" in events[0].name

    def test_full_watcher_workflow_detects_change(self, mock_watcher):
        """The complete check() workflow fires the alarm exactly once per change.

        check() reads self.previous_state (loaded at __init__ from disk —
        persisted between runs), so set it directly for determinism. This is
        the regression area of the T-049 first-run bug fix.
        """
        mock_watcher.previous_state = {
            "last_check": datetime.now().isoformat(),
            "last_value": None,
            "first_seen": datetime.now().isoformat(),
        }

        with patch.object(mock_watcher, "_save_state"):
            with patch.object(mock_watcher, "fetch_page", return_value="<html>test</html>"):
                # Alarm mocked before any check; the extracted value changes
                # between checks so exactly one change is detected
                with patch.object(mock_watcher, "trigger_alarm") as mock_alarm:
                    with patch.object(mock_watcher, "extract_value", side_effect=["value_1", "value_2"]):
                        mock_watcher.check()
                        mock_watcher.check()
                        mock_alarm.assert_called_once()

    def test_first_check_initializes_without_alarm(self, mock_watcher):
        """A watcher with no previous value records state without alarming."""
        with patch.object(mock_watcher, "_save_state"):
            with patch.object(mock_watcher, "fetch_page", return_value="<html>test</html>"):
                with patch.object(mock_watcher, "trigger_alarm") as mock_alarm:
                    mock_watcher.check()
                    mock_alarm.assert_not_called()
                    assert mock_watcher.previous_state.get("last_value") == "Extracted value from test_watcher"
