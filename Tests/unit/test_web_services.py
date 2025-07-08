"""
Unit tests for web data services and components.
"""

import unittest
from unittest.mock import MagicMock, patch
import tempfile
import json
from pathlib import Path

from src.web.fullstreamlit.utils.data_service import DataService


class TestDataService(unittest.TestCase):
    """Test DataService functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.data_service = DataService(data_root=str(self.test_dir))

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_data_service_initialization(self):
        """Test DataService initialization."""
        self.assertEqual(self.data_service.data_root, str(self.test_dir))

    def test_load_json_data_existing_file(self):
        """Test load_json_data with existing file."""
        test_data = [
            {"id": 1, "title": "Test Item 1"},
            {"id": 2, "title": "Test Item 2"}
        ]
        
        # Create test data directory and file
        domain_dir = self.test_dir / "test_domain"
        domain_dir.mkdir()
        data_file = domain_dir / "test_data.json"
        
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        result = self.data_service.load_json_data("test_domain", "test_data")
        
        self.assertEqual(result, test_data)
        self.assertEqual(len(result), 2)

    def test_load_json_data_missing_file(self):
        """Test load_json_data with missing file."""
        result = self.data_service.load_json_data("missing_domain", "missing_file")
        
        self.assertEqual(result, [])

    def test_get_file_stats_existing_file(self):
        """Test get_file_stats with existing file."""
        test_data = {"test": "data"}
        
        domain_dir = self.test_dir / "test_domain"
        domain_dir.mkdir()
        data_file = domain_dir / "test_data.json"
        
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        stats = self.data_service.get_file_stats("test_domain", "test_data", "json")
        
        self.assertIsInstance(stats, dict)
        self.assertIn("exists", stats)
        self.assertTrue(stats["exists"])

    def test_get_file_stats_missing_file(self):
        """Test get_file_stats with missing file."""
        stats = self.data_service.get_file_stats("missing_domain", "missing_file", "json")
        
        self.assertIsInstance(stats, dict)
        self.assertFalse(stats["exists"])


if __name__ == '__main__':
    unittest.main() 