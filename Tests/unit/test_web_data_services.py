"""
Comprehensive unit tests for web data services and components.
Tests data loading, caching, and service functionality.
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.web.fullstreamlit.utils.data_service import DataService
from src.web.fullstreamlit.utils.data_loader import DataLoader
from src.web.fullstreamlit.utils.ultra_optimized_data_service import UltraOptimizedDataService


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
        self.assertIsInstance(self.data_service.cache, dict)

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

    def test_load_csv_data_existing_file(self):
        """Test load_csv_data with existing file."""
        # Create test CSV data
        csv_content = "id,title,description\n1,Item 1,Description 1\n2,Item 2,Description 2"
        
        domain_dir = self.test_dir / "test_domain"
        domain_dir.mkdir()
        csv_file = domain_dir / "test_data.csv"
        
        csv_file.write_text(csv_content)
        
        result = self.data_service.load_csv_data("test_domain", "test_data")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[0]["title"], "Item 1")

    def test_load_csv_data_missing_file(self):
        """Test load_csv_data with missing file."""
        result = self.data_service.load_csv_data("missing_domain", "missing_file")
        
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
        self.assertIn("size", stats)
        self.assertIn("modified", stats)
        self.assertTrue(stats["exists"])

    def test_get_file_stats_missing_file(self):
        """Test get_file_stats with missing file."""
        stats = self.data_service.get_file_stats("missing_domain", "missing_file", "json")
        
        self.assertIsInstance(stats, dict)
        self.assertFalse(stats["exists"])
        self.assertEqual(stats["size"], 0)

    def test_cache_data(self):
        """Test data caching functionality."""
        test_data = [{"id": 1, "name": "Test"}]
        cache_key = "test_domain:test_data"
        
        self.data_service.cache_data(cache_key, test_data)
        
        self.assertIn(cache_key, self.data_service.cache)
        self.assertEqual(self.data_service.cache[cache_key]["data"], test_data)

    def test_get_cached_data(self):
        """Test retrieving cached data."""
        test_data = [{"id": 1, "name": "Test"}]
        cache_key = "test_domain:test_data"
        
        # Cache the data first
        self.data_service.cache_data(cache_key, test_data)
        
        # Retrieve cached data
        cached_data = self.data_service.get_cached_data(cache_key)
        
        self.assertEqual(cached_data, test_data)

    def test_get_cached_data_expired(self):
        """Test retrieving expired cached data."""
        test_data = [{"id": 1, "name": "Test"}]
        cache_key = "test_domain:test_data"
        
        # Manually create expired cache entry
        self.data_service.cache[cache_key] = {
            "data": test_data,
            "timestamp": datetime.now(timezone.utc).timestamp() - 7200,  # 2 hours ago
            "ttl": 3600  # 1 hour TTL
        }
        
        # Should return None for expired data
        cached_data = self.data_service.get_cached_data(cache_key)
        
        self.assertIsNone(cached_data)

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add some test data to cache
        self.data_service.cache_data("key1", [{"test": 1}])
        self.data_service.cache_data("key2", [{"test": 2}])
        
        self.assertEqual(len(self.data_service.cache), 2)
        
        # Clear cache
        self.data_service.clear_cache()
        
        self.assertEqual(len(self.data_service.cache), 0)


class TestDataLoader(unittest.TestCase):
    """Test DataLoader functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.data_loader = DataLoader(data_root=str(self.test_dir))

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_data_loader_initialization(self):
        """Test DataLoader initialization."""
        self.assertEqual(self.data_loader.data_root, str(self.test_dir))

    def test_load_all_domains(self):
        """Test loading data from all domains."""
        # Create test data for multiple domains
        domains = ["arxiv", "courses", "news"]
        
        for domain in domains:
            domain_dir = self.test_dir / domain
            domain_dir.mkdir()
            
            test_data = [{"id": f"{domain}_1", "title": f"{domain.title()} Item 1"}]
            data_file = domain_dir / f"{domain}_latest.json"
            
            with open(data_file, 'w') as f:
                json.dump(test_data, f)
        
        all_data = self.data_loader.load_all_domains()
        
        self.assertIsInstance(all_data, dict)
        self.assertEqual(len(all_data), len(domains))
        
        for domain in domains:
            self.assertIn(domain, all_data)

    def test_load_domain_data_with_fallback(self):
        """Test loading domain data with fallback to CSV."""
        domain = "test_domain"
        domain_dir = self.test_dir / domain
        domain_dir.mkdir()
        
        # Create only CSV file (no JSON)
        csv_content = "id,title\n1,Test Item"
        csv_file = domain_dir / f"{domain}_latest.csv"
        csv_file.write_text(csv_content)
        
        data = self.data_loader.load_domain_data(domain)
        
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "1")

    def test_get_available_domains(self):
        """Test getting available data domains."""
        # Create test domains
        domains = ["domain1", "domain2", "domain3"]
        
        for domain in domains:
            domain_dir = self.test_dir / domain
            domain_dir.mkdir()
            
            # Create a data file in each domain
            data_file = domain_dir / f"{domain}_latest.json"
            data_file.write_text("[]")
        
        available_domains = self.data_loader.get_available_domains()
        
        self.assertIsInstance(available_domains, list)
        for domain in domains:
            self.assertIn(domain, available_domains)

    def test_get_data_summary(self):
        """Test getting data summary statistics."""
        # Create test data with various counts
        test_data = {
            "arxiv": [{"id": i} for i in range(10)],
            "courses": [{"id": i} for i in range(25)],
            "news": [{"id": i} for i in range(5)]
        }
        
        for domain, data in test_data.items():
            domain_dir = self.test_dir / domain
            domain_dir.mkdir()
            
            data_file = domain_dir / f"{domain}_latest.json"
            with open(data_file, 'w') as f:
                json.dump(data, f)
        
        summary = self.data_loader.get_data_summary()
        
        self.assertIsInstance(summary, dict)
        self.assertEqual(summary["arxiv"]["count"], 10)
        self.assertEqual(summary["courses"]["count"], 25)
        self.assertEqual(summary["news"]["count"], 5)
        self.assertEqual(summary["total"]["count"], 40)


class TestUltraOptimizedDataService(unittest.TestCase):
    """Test UltraOptimizedDataService functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.service = UltraOptimizedDataService(data_root=str(self.test_dir))

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ultra_optimized_service_initialization(self):
        """Test UltraOptimizedDataService initialization."""
        self.assertEqual(self.service.data_root, str(self.test_dir))
        self.assertIsInstance(self.service.memory_cache, dict)
        self.assertIsInstance(self.service.file_cache, dict)

    def test_memory_caching(self):
        """Test memory caching functionality."""
        test_data = [{"id": 1, "name": "Test"}]
        cache_key = "test_key"
        
        self.service.set_memory_cache(cache_key, test_data)
        
        cached_data = self.service.get_memory_cache(cache_key)
        
        self.assertEqual(cached_data, test_data)

    def test_memory_cache_expiration(self):
        """Test memory cache expiration."""
        test_data = [{"id": 1, "name": "Test"}]
        cache_key = "test_key"
        
        # Set cache with very short TTL
        self.service.set_memory_cache(cache_key, test_data, ttl=0.1)
        
        # Wait for expiration
        import time
        time.sleep(0.2)
        
        cached_data = self.service.get_memory_cache(cache_key)
        
        self.assertIsNone(cached_data)

    def test_file_cache_stats(self):
        """Test file cache statistics."""
        # Create test files with different modification times
        domain_dir = self.test_dir / "test_domain"
        domain_dir.mkdir()
        
        files = ["file1.json", "file2.json", "file3.json"]
        
        for file_name in files:
            file_path = domain_dir / file_name
            file_path.write_text("[]")
        
        stats = self.service.get_file_cache_stats("test_domain")
        
        self.assertIsInstance(stats, dict)
        self.assertIn("file_count", stats)
        self.assertIn("total_size", stats)

    @patch('streamlit.cache_data')
    def test_streamlit_cache_integration(self, mock_cache):
        """Test integration with Streamlit caching."""
        # This tests that the service can work with Streamlit's caching
        mock_cache.return_value = lambda x: x
        
        test_data = [{"id": 1, "name": "Test"}]
        
        # The actual implementation would use @st.cache_data
        # Here we just test that the method exists and can be called
        cached_method = self.service.get_cached_domain_data
        
        self.assertTrue(callable(cached_method))

    def test_batch_load_optimization(self):
        """Test batch loading optimization."""
        # Create multiple test domains
        domains = ["domain1", "domain2", "domain3"]
        
        for domain in domains:
            domain_dir = self.test_dir / domain
            domain_dir.mkdir()
            
            test_data = [{"id": f"{domain}_item_{i}"} for i in range(5)]
            data_file = domain_dir / f"{domain}_latest.json"
            
            with open(data_file, 'w') as f:
                json.dump(test_data, f)
        
        # Test batch loading
        batch_data = self.service.batch_load_domains(domains)
        
        self.assertIsInstance(batch_data, dict)
        self.assertEqual(len(batch_data), len(domains))
        
        for domain in domains:
            self.assertIn(domain, batch_data)
            self.assertEqual(len(batch_data[domain]), 5)

    def test_performance_metrics(self):
        """Test performance metrics collection."""
        # Create test data
        domain_dir = self.test_dir / "test_domain"
        domain_dir.mkdir()
        
        test_data = [{"id": i} for i in range(100)]
        data_file = domain_dir / "test_data.json"
        
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Load data and check metrics
        start_time = datetime.now()
        data = self.service.load_json_data("test_domain", "test_data")
        end_time = datetime.now()
        
        metrics = self.service.get_performance_metrics()
        
        self.assertIsInstance(metrics, dict)
        self.assertIn("load_times", metrics)
        self.assertIn("cache_hits", metrics)
        self.assertIn("cache_misses", metrics)

    def test_memory_usage_optimization(self):
        """Test memory usage optimization."""
        # Create large test data
        large_data = [{"id": i, "data": f"item_{i}" * 100} for i in range(1000)]
        
        domain_dir = self.test_dir / "large_domain"
        domain_dir.mkdir()
        data_file = domain_dir / "large_data.json"
        
        with open(data_file, 'w') as f:
            json.dump(large_data, f)
        
        # Load data and check memory usage
        initial_cache_size = len(self.service.memory_cache)
        
        data = self.service.load_json_data("large_domain", "large_data")
        
        # Verify data loaded correctly
        self.assertEqual(len(data), 1000)
        
        # Check that memory cache management is working
        memory_stats = self.service.get_memory_stats()
        
        self.assertIsInstance(memory_stats, dict)
        self.assertIn("cache_size", memory_stats)
        self.assertIn("memory_usage", memory_stats)


class TestDataServiceIntegration(unittest.TestCase):
    """Test integration between different data services."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_service_interoperability(self):
        """Test that different data services can work together."""
        data_service = DataService(data_root=str(self.test_dir))
        data_loader = DataLoader(data_root=str(self.test_dir))
        ultra_service = UltraOptimizedDataService(data_root=str(self.test_dir))
        
        # Create test data
        domain_dir = self.test_dir / "shared_domain"
        domain_dir.mkdir()
        
        test_data = [{"id": 1, "shared": True}]
        data_file = domain_dir / "shared_data.json"
        
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Test that all services can load the same data
        data1 = data_service.load_json_data("shared_domain", "shared_data")
        data2 = data_loader.load_domain_data("shared_domain")
        data3 = ultra_service.load_json_data("shared_domain", "shared_data")
        
        self.assertEqual(data1, test_data)
        self.assertEqual(data2, test_data)
        self.assertEqual(data3, test_data)

    def test_cache_consistency(self):
        """Test cache consistency across services."""
        service1 = DataService(data_root=str(self.test_dir))
        service2 = DataService(data_root=str(self.test_dir))
        
        # Create test data
        domain_dir = self.test_dir / "cache_test"
        domain_dir.mkdir()
        
        test_data = [{"id": 1, "cached": True}]
        data_file = domain_dir / "cache_data.json"
        
        with open(data_file, 'w') as f:
            json.dump(test_data, f)
        
        # Load data with first service (should cache it)
        data1 = service1.load_json_data("cache_test", "cache_data")
        
        # Modify the file
        modified_data = [{"id": 1, "cached": True, "modified": True}]
        with open(data_file, 'w') as f:
            json.dump(modified_data, f)
        
        # Load with second service (should get fresh data)
        data2 = service2.load_json_data("cache_test", "cache_data")
        
        self.assertEqual(data1, test_data)
        self.assertEqual(data2, modified_data)


if __name__ == '__main__':
    unittest.main() 