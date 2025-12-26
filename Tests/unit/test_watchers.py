"""Comprehensive unit tests for the watcher system.
Tests base watcher functionality and specialized watchers.
"""

import os
import tempfile
import unittest
from pathlib import Path

from src.watchers.base_watcher import BaseWatcher


class TestBaseWatcher(unittest.TestCase):
    """Test BaseWatcher functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "test_watcher_state.json"

        class TestWatcher(BaseWatcher):
            """Test implementation of BaseWatcher."""

            def extract_value(self, html_content):
                """Mock implementation."""
                return "test_value"

            def has_changed(self, old_value, new_value):
                """Mock implementation."""
                return old_value != new_value

        self.test_watcher = TestWatcher(name="test_watcher", url="https://example.com", check_interval=60)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_base_watcher_initialization(self):
        """Test BaseWatcher initialization."""
        self.assertEqual(self.test_watcher.name, "test_watcher")
        self.assertEqual(self.test_watcher.url, "https://example.com")
        self.assertEqual(self.test_watcher.check_interval, 60)

    def test_extract_value_implementation(self):
        """Test extract_value method implementation."""
        html_content = "<html><body>Test</body></html>"
        value = self.test_watcher.extract_value(html_content)

        self.assertEqual(value, "test_value")

    def test_has_changed_implementation(self):
        """Test has_changed method implementation."""
        # Same values should not be changed
        self.assertFalse(self.test_watcher.has_changed("same", "same"))

        # Different values should be changed
        self.assertTrue(self.test_watcher.has_changed("old", "new"))

    def test_state_file_path(self):
        """Test state file path is set correctly."""
        expected_path = str(self.test_watcher.data_dir / "state.json")
        self.assertEqual(str(self.test_watcher.state_file), expected_path)


if __name__ == "__main__":
    unittest.main()
