"""
Performance tests for search functionality
Tests sub-second response times as required by Story 1.3
"""

import pytest
import time
from src.web.dashboard.utils.search_utils import (
    filter_content,
    get_common_searchable_fields,
    validate_search_performance
)


class TestSearchPerformance:
    """Test search performance meets the <1 second requirement"""

    def generate_large_dataset(self, size: int):
        """Generate a large dataset for performance testing"""
        dataset = []
        for i in range(size):
            dataset.append({
                "title": f"Test Article {i}",
                "description": f"This is a test description for article number {i}",
                "source": f"Source {i % 10}",
                "summary": f"Summary for article {i} with some content"
            })
        return dataset

    def test_small_dataset_performance(self):
        """Test search performance with small dataset (1,000 items)"""
        dataset = self.generate_large_dataset(1000)
        searchable_fields = get_common_searchable_fields('news')

        start_time = time.time()
        result = filter_content("test", dataset, searchable_fields)
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 0.5, f"Search took {response_time:.3f}s, should be <0.5s for 1K items"

    def test_medium_dataset_performance(self):
        """Test search performance with medium dataset (5,000 items)"""
        dataset = self.generate_large_dataset(5000)
        searchable_fields = get_common_searchable_fields('news')

        start_time = time.time()
        result = filter_content("test", dataset, searchable_fields)
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 0.8, f"Search took {response_time:.3f}s, should be <0.8s for 5K items"

    def test_large_dataset_performance(self):
        """Test search performance with large dataset (10,000 items)"""
        dataset = self.generate_large_dataset(10000)
        searchable_fields = get_common_searchable_fields('news')

        start_time = time.time()
        result = filter_content("test", dataset, searchable_fields)
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 1.0, f"Search took {response_time:.3f}s, should be <1.0s for 10K items"

    def test_empty_search_performance(self):
        """Test search performance with empty query"""
        dataset = self.generate_large_dataset(10000)
        searchable_fields = get_common_searchable_fields('news')

        start_time = time.time()
        result = filter_content("", dataset, searchable_fields)
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 0.1, f"Empty search took {response_time:.3f}s, should be <0.1s"
        assert result == dataset  # Should return all items

    def test_long_query_performance(self):
        """Test search performance with long query"""
        dataset = self.generate_large_dataset(5000)
        searchable_fields = get_common_searchable_fields('news')
        long_query = "this is a very long search query that might affect performance"

        start_time = time.time()
        result = filter_content(long_query, dataset, searchable_fields)
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 1.0, f"Long query search took {response_time:.3f}s, should be <1.0s"

    def test_partial_match_performance(self):
        """Test search performance with partial matches"""
        dataset = self.generate_large_dataset(8000)
        searchable_fields = get_common_searchable_fields('news')

        start_time = time.time()
        result = filter_content("Article 123", dataset, searchable_fields)
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 1.0, f"Partial match search took {response_time:.3f}s, should be <1.0s"
        assert len(result) > 0  # Should find some matches

    def test_case_insensitive_performance(self):
        """Test performance with case-insensitive search"""
        dataset = self.generate_large_dataset(7000)
        searchable_fields = get_common_searchable_fields('news')

        start_time = time.time()
        result = filter_content("TEST ARTICLE", dataset, searchable_fields)
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 1.0, f"Case-insensitive search took {response_time:.3f}s, should be <1.0s"

    def test_multiple_search_calls_performance(self):
        """Test performance of multiple consecutive searches"""
        dataset = self.generate_large_dataset(3000)
        searchable_fields = get_common_searchable_fields('news')
        queries = ["test", "article", "source", "summary", "description"]

        total_time = 0
        for query in queries:
            start_time = time.time()
            result = filter_content(query, dataset, searchable_fields)
            end_time = time.time()
            total_time += (end_time - start_time)

        average_time = total_time / len(queries)
        assert average_time < 0.5, f"Average search time was {average_time:.3f}s, should be <0.5s"

    def test_memory_usage_with_large_dataset(self):
        """Test that memory usage doesn't grow excessively"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create a large dataset and perform search
        dataset = self.generate_large_dataset(15000)
        searchable_fields = get_common_searchable_fields('news')

        # Perform multiple searches
        for i in range(5):
            result = filter_content(f"test {i}", dataset, searchable_fields)

        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

        # Memory increase should be reasonable (<50MB for this test)
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB, should be <50MB"


if __name__ == "__main__":
    pytest.main([__file__])