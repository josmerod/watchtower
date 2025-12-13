"""Tests for Developer News ETL."""

import unittest
from unittest.mock import MagicMock, patch

from src.etl.developer_news.developer_news_etl import DeveloperNewsETL
from src.models.developer_news_model import NewsSourceType


class TestDeveloperNewsETL(unittest.TestCase):
    """Test cases for Developer News ETL."""

    def setUp(self):
        self.etl = DeveloperNewsETL()

    @patch("src.etl.developer_news.developer_news_etl.requests.get")
    def test_extract_hacker_news(self, mock_get):
        """Test extraction from Hacker News."""
        # Mock HN Top Stories
        mock_get.side_effect = [
            MagicMock(json=lambda: [12345]), # IDs
            MagicMock(json=lambda: {"id": 12345, "title": "Test Story", "url": "http://example.com/hn", "time": 1600000000}) # Item details
        ]
        
        items = self.etl.extract()
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], NewsSourceType.HACKERNEWS)
        self.assertEqual(items[0]["data"]["title"], "Test Story")

    def test_transform(self):
        """Test transformation logic."""
        raw_data = [{
            "source": NewsSourceType.HACKERNEWS,
            "data": {
                "id": 123,
                "title": "Python 3.12 Released",
                "url": "http://python.org",
                "time": 1600000000,
                "score": 500,
                "descendants": 50
            }
        }]
        
        transformed = self.etl.transform(raw_data)
        
        self.assertEqual(len(transformed), 1)
        item = transformed[0]
        self.assertEqual(item.title, "Python 3.12 Released")
        self.assertEqual(item.source, NewsSourceType.HACKERNEWS)
        self.assertIn("tech", item.tags)
        # Relevance score should be boosted by score > 100
        self.assertTrue(item.relevance_score > 0.1)

    def test_summarizer(self):
        """Test heuristic summarizer."""
        text = "This is sentence one. This is sentence two with more words. Short. This is sentence four."
        summary = self.etl.summarizer.summarize(text, max_sentences=2)
        
        self.assertIn("This is sentence one", summary)
        # Heuristic picks longest sentences usually
        self.assertIn("This is sentence two", summary)

if __name__ == "__main__":
    unittest.main()
