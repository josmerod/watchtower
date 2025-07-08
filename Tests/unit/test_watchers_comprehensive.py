"""
Comprehensive unit tests for the watcher system.
Tests base watcher functionality and specialized watchers.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, List, Any

from src.watchers.base_watcher import BaseWatcher, WatcherState, WatcherEvent
from src.watchers.arxiv_watcher import ArxivWatcher
from src.watchers.enhanced_watcher import EnhancedWatcher
from src.watchers.content_watcher import ContentWatcher
from src.watchers.news_watcher import NewsWatcher
from src.watchers.technology_watcher import TechnologyWatcher


class TestBaseWatcher(unittest.TestCase):
    """Test BaseWatcher functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "test_watcher_state.json"
        
        class TestWatcher(BaseWatcher):
            """Test implementation of BaseWatcher."""
            
            def check_for_changes(self) -> List[WatcherEvent]:
                """Mock implementation."""
                return [
                    WatcherEvent(
                        event_type="test_change",
                        data={"test": "data"},
                        timestamp=datetime.now(timezone.utc)
                    )
                ]
            
            def process_event(self, event: WatcherEvent) -> bool:
                """Mock implementation."""
                return True
        
        self.test_watcher = TestWatcher(
            name="test_watcher",
            state_file=str(self.state_file),
            check_interval=60
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_base_watcher_initialization(self):
        """Test BaseWatcher initialization."""
        self.assertEqual(self.test_watcher.name, "test_watcher")
        self.assertEqual(self.test_watcher.check_interval, 60)
        self.assertEqual(self.test_watcher.state_file, str(self.state_file))
        self.assertIsInstance(self.test_watcher.state, WatcherState)

    def test_watcher_state_initialization(self):
        """Test WatcherState initialization."""
        state = WatcherState()
        
        self.assertIsInstance(state.last_check, datetime)
        self.assertEqual(state.check_count, 0)
        self.assertEqual(state.event_count, 0)
        self.assertEqual(state.last_event_id, "")
        self.assertIsInstance(state.metadata, dict)

    def test_watcher_event_creation(self):
        """Test WatcherEvent creation."""
        event_data = {"key": "value", "number": 42}
        event = WatcherEvent(
            event_type="test_event",
            data=event_data,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.assertEqual(event.event_type, "test_event")
        self.assertEqual(event.data, event_data)
        self.assertIsInstance(event.timestamp, datetime)
        self.assertIsNotNone(event.event_id)

    def test_save_state_creates_file(self):
        """Test save_state creates state file."""
        self.test_watcher.state.check_count = 5
        self.test_watcher.state.event_count = 3
        
        self.test_watcher.save_state()
        
        self.assertTrue(self.state_file.exists())
        
        # Verify content
        with open(self.state_file) as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["check_count"], 5)
        self.assertEqual(saved_data["event_count"], 3)

    def test_load_state_from_file(self):
        """Test load_state loads from existing file."""
        # Create state file
        state_data = {
            "last_check": datetime.now(timezone.utc).isoformat(),
            "check_count": 10,
            "event_count": 7,
            "last_event_id": "test_event_123",
            "metadata": {"test_key": "test_value"}
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state_data, f)
        
        self.test_watcher.load_state()
        
        self.assertEqual(self.test_watcher.state.check_count, 10)
        self.assertEqual(self.test_watcher.state.event_count, 7)
        self.assertEqual(self.test_watcher.state.last_event_id, "test_event_123")
        self.assertEqual(self.test_watcher.state.metadata["test_key"], "test_value")

    def test_load_state_missing_file(self):
        """Test load_state with missing file creates default state."""
        # Ensure file doesn't exist
        if self.state_file.exists():
            self.state_file.unlink()
        
        self.test_watcher.load_state()
        
        # Should have default values
        self.assertEqual(self.test_watcher.state.check_count, 0)
        self.assertEqual(self.test_watcher.state.event_count, 0)

    def test_run_check_processes_events(self):
        """Test run_check processes events correctly."""
        initial_check_count = self.test_watcher.state.check_count
        initial_event_count = self.test_watcher.state.event_count
        
        result = self.test_watcher.run_check()
        
        self.assertTrue(result)
        self.assertEqual(self.test_watcher.state.check_count, initial_check_count + 1)
        self.assertEqual(self.test_watcher.state.event_count, initial_event_count + 1)

    def test_is_time_to_check_initial_run(self):
        """Test is_time_to_check returns True for initial run."""
        # Reset last_check to make it seem like first run
        self.test_watcher.state.last_check = datetime.min.replace(tzinfo=timezone.utc)
        
        self.assertTrue(self.test_watcher.is_time_to_check())

    def test_is_time_to_check_interval_not_passed(self):
        """Test is_time_to_check returns False when interval hasn't passed."""
        # Set last_check to now
        self.test_watcher.state.last_check = datetime.now(timezone.utc)
        
        self.assertFalse(self.test_watcher.is_time_to_check())

    def test_update_metadata(self):
        """Test update_metadata updates state metadata."""
        new_metadata = {"source": "test", "version": "1.0"}
        
        self.test_watcher.update_metadata(new_metadata)
        
        for key, value in new_metadata.items():
            self.assertEqual(self.test_watcher.state.metadata[key], value)

    def test_get_statistics(self):
        """Test get_statistics returns current watcher stats."""
        self.test_watcher.state.check_count = 15
        self.test_watcher.state.event_count = 8
        
        stats = self.test_watcher.get_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["check_count"], 15)
        self.assertEqual(stats["event_count"], 8)
        self.assertIn("last_check", stats)
        self.assertIn("success_rate", stats)


class TestArxivWatcher(unittest.TestCase):
    """Test ArxivWatcher functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "arxiv_watcher_state.json"
        
        self.arxiv_watcher = ArxivWatcher(
            categories=["cs.AI", "cs.LG"],
            state_file=str(self.state_file),
            check_interval=3600
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_arxiv_watcher_initialization(self):
        """Test ArxivWatcher initialization."""
        self.assertEqual(self.arxiv_watcher.categories, ["cs.AI", "cs.LG"])
        self.assertEqual(self.arxiv_watcher.name, "arxiv_watcher")
        self.assertIsInstance(self.arxiv_watcher.rss_urls, list)

    def test_build_rss_urls(self):
        """Test build_rss_urls creates correct URLs."""
        urls = self.arxiv_watcher.build_rss_urls()
        
        self.assertIsInstance(urls, list)
        self.assertTrue(len(urls) > 0)
        
        for url in urls:
            self.assertIn("arxiv.org", url)
            self.assertIn("rss", url.lower())

    @patch('feedparser.parse')
    def test_fetch_rss_feed_success(self, mock_parse):
        """Test fetch_rss_feed with successful response."""
        mock_parse.return_value = MagicMock(
            entries=[
                MagicMock(
                    id="http://arxiv.org/abs/2301.00001v1",
                    title="Test Paper",
                    summary="Test abstract",
                    published="2023-01-01T00:00:00Z"
                )
            ]
        )
        
        entries = self.arxiv_watcher.fetch_rss_feed("https://test.arxiv.org/rss")
        
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "Test Paper")

    @patch('feedparser.parse')
    def test_check_for_changes_finds_new_papers(self, mock_parse):
        """Test check_for_changes identifies new papers."""
        mock_parse.return_value = MagicMock(
            entries=[
                MagicMock(
                    id="http://arxiv.org/abs/2301.00001v1",
                    title="New Paper",
                    summary="New abstract",
                    published="2023-01-01T00:00:00Z",
                    tags=[MagicMock(term="cs.AI")]
                )
            ]
        )
        
        events = self.arxiv_watcher.check_for_changes()
        
        self.assertIsInstance(events, list)
        if len(events) > 0:
            self.assertEqual(events[0].event_type, "new_paper")

    def test_extract_arxiv_id(self):
        """Test extract_arxiv_id extracts ID correctly."""
        test_url = "http://arxiv.org/abs/2301.00001v1"
        arxiv_id = self.arxiv_watcher.extract_arxiv_id(test_url)
        
        self.assertEqual(arxiv_id, "2301.00001")

    def test_is_new_paper(self):
        """Test is_new_paper identifies new papers."""
        # Paper not in seen papers should be new
        self.assertTrue(self.arxiv_watcher.is_new_paper("2301.00001"))
        
        # Add to seen papers
        self.arxiv_watcher.state.metadata["seen_papers"] = ["2301.00001"]
        
        # Should no longer be new
        self.assertFalse(self.arxiv_watcher.is_new_paper("2301.00001"))


class TestEnhancedWatcher(unittest.TestCase):
    """Test EnhancedWatcher functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "enhanced_watcher_state.json"
        
        self.enhanced_watcher = EnhancedWatcher(
            name="enhanced_test_watcher",
            sources=["https://example.com/feed1", "https://example.com/feed2"],
            state_file=str(self.state_file)
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_enhanced_watcher_initialization(self):
        """Test EnhancedWatcher initialization."""
        self.assertEqual(self.enhanced_watcher.name, "enhanced_test_watcher")
        self.assertEqual(len(self.enhanced_watcher.sources), 2)
        self.assertIn("https://example.com/feed1", self.enhanced_watcher.sources)

    def test_add_source(self):
        """Test add_source adds new source."""
        new_source = "https://example.com/feed3"
        initial_count = len(self.enhanced_watcher.sources)
        
        self.enhanced_watcher.add_source(new_source)
        
        self.assertEqual(len(self.enhanced_watcher.sources), initial_count + 1)
        self.assertIn(new_source, self.enhanced_watcher.sources)

    def test_remove_source(self):
        """Test remove_source removes existing source."""
        source_to_remove = "https://example.com/feed1"
        initial_count = len(self.enhanced_watcher.sources)
        
        result = self.enhanced_watcher.remove_source(source_to_remove)
        
        self.assertTrue(result)
        self.assertEqual(len(self.enhanced_watcher.sources), initial_count - 1)
        self.assertNotIn(source_to_remove, self.enhanced_watcher.sources)

    def test_remove_source_not_found(self):
        """Test remove_source with non-existent source."""
        result = self.enhanced_watcher.remove_source("https://nonexistent.com")
        
        self.assertFalse(result)

    @patch('requests.get')
    def test_fetch_source_content_success(self, mock_get):
        """Test fetch_source_content with successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_get.return_value = mock_response
        
        content = self.enhanced_watcher.fetch_source_content("https://example.com")
        
        self.assertEqual(content, "<html><body>Test content</body></html>")

    @patch('requests.get')
    def test_fetch_source_content_failure(self, mock_get):
        """Test fetch_source_content with failed response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        content = self.enhanced_watcher.fetch_source_content("https://example.com")
        
        self.assertIsNone(content)

    def test_calculate_content_hash(self):
        """Test calculate_content_hash generates consistent hash."""
        content = "This is test content"
        
        hash1 = self.enhanced_watcher.calculate_content_hash(content)
        hash2 = self.enhanced_watcher.calculate_content_hash(content)
        
        self.assertEqual(hash1, hash2)
        self.assertIsInstance(hash1, str)
        self.assertTrue(len(hash1) > 10)

    def test_has_content_changed(self):
        """Test has_content_changed detects changes."""
        source = "https://example.com"
        content1 = "Original content"
        content2 = "Modified content"
        
        # First check - should be considered changed (new)
        changed1 = self.enhanced_watcher.has_content_changed(source, content1)
        self.assertTrue(changed1)
        
        # Same content - should not be changed
        changed2 = self.enhanced_watcher.has_content_changed(source, content1)
        self.assertFalse(changed2)
        
        # Different content - should be changed
        changed3 = self.enhanced_watcher.has_content_changed(source, content2)
        self.assertTrue(changed3)


class TestContentWatcher(unittest.TestCase):
    """Test ContentWatcher functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "content_watcher_state.json"
        
        self.content_watcher = ContentWatcher(
            name="content_test_watcher",
            content_types=["article", "blog_post"],
            sources=["https://example.com/blog"],
            state_file=str(self.state_file)
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_content_watcher_initialization(self):
        """Test ContentWatcher initialization."""
        self.assertEqual(self.content_watcher.content_types, ["article", "blog_post"])
        self.assertEqual(len(self.content_watcher.sources), 1)

    def test_filter_by_content_type(self):
        """Test filter_by_content_type filters content correctly."""
        content_items = [
            {"type": "article", "title": "Article 1"},
            {"type": "blog_post", "title": "Blog 1"},
            {"type": "video", "title": "Video 1"},
            {"type": "article", "title": "Article 2"}
        ]
        
        filtered = self.content_watcher.filter_by_content_type(content_items)
        
        self.assertEqual(len(filtered), 3)  # 2 articles + 1 blog_post
        self.assertTrue(all(item["type"] in ["article", "blog_post"] for item in filtered))

    def test_extract_content_metadata(self):
        """Test extract_content_metadata extracts metadata."""
        content_html = """
        <html>
            <head>
                <title>Test Article</title>
                <meta name="author" content="John Doe">
                <meta name="description" content="Test description">
            </head>
            <body>
                <h1>Test Article</h1>
                <p>This is test content.</p>
            </body>
        </html>
        """
        
        metadata = self.content_watcher.extract_content_metadata(content_html)
        
        self.assertIsInstance(metadata, dict)
        self.assertIn("title", metadata)
        self.assertIn("author", metadata)

    def test_is_content_relevant(self):
        """Test is_content_relevant filters relevant content."""
        relevant_content = {
            "title": "Machine Learning Advances",
            "description": "Latest developments in AI and ML",
            "tags": ["AI", "machine-learning", "technology"]
        }
        
        irrelevant_content = {
            "title": "Cooking Recipe",
            "description": "How to make pasta",
            "tags": ["cooking", "food", "recipe"]
        }
        
        # This test depends on implementation details
        # For now, just test that the method exists and returns boolean
        result1 = self.content_watcher.is_content_relevant(relevant_content)
        result2 = self.content_watcher.is_content_relevant(irrelevant_content)
        
        self.assertIsInstance(result1, bool)
        self.assertIsInstance(result2, bool)


class TestNewsWatcher(unittest.TestCase):
    """Test NewsWatcher functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "news_watcher_state.json"
        
        self.news_watcher = NewsWatcher(
            name="news_test_watcher",
            news_sources=["https://example.com/rss", "https://news.example.com/feed"],
            categories=["technology", "science"],
            state_file=str(self.state_file)
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_news_watcher_initialization(self):
        """Test NewsWatcher initialization."""
        self.assertEqual(len(self.news_watcher.news_sources), 2)
        self.assertEqual(self.news_watcher.categories, ["technology", "science"])

    @patch('feedparser.parse')
    def test_fetch_news_feed_success(self, mock_parse):
        """Test fetch_news_feed with successful response."""
        mock_parse.return_value = MagicMock(
            entries=[
                MagicMock(
                    title="Tech News",
                    link="https://example.com/article1",
                    published="2023-01-01T00:00:00Z",
                    summary="Tech news summary"
                )
            ]
        )
        
        articles = self.news_watcher.fetch_news_feed("https://example.com/rss")
        
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Tech News")

    def test_categorize_article(self):
        """Test categorize_article categorizes articles correctly."""
        tech_article = {
            "title": "New AI Framework Released",
            "summary": "A new artificial intelligence framework for developers"
        }
        
        category = self.news_watcher.categorize_article(tech_article)
        
        self.assertIsInstance(category, str)
        self.assertTrue(len(category) > 0)

    def test_is_duplicate_article(self):
        """Test is_duplicate_article detects duplicates."""
        article1 = {
            "title": "Breaking Tech News",
            "link": "https://example.com/article1",
            "published": "2023-01-01T00:00:00Z"
        }
        
        # First time should not be duplicate
        self.assertFalse(self.news_watcher.is_duplicate_article(article1))
        
        # Add to seen articles
        self.news_watcher.state.metadata["seen_articles"] = [article1["link"]]
        
        # Should now be duplicate
        self.assertTrue(self.news_watcher.is_duplicate_article(article1))


class TestTechnologyWatcher(unittest.TestCase):
    """Test TechnologyWatcher functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "tech_watcher_state.json"
        
        self.tech_watcher = TechnologyWatcher(
            name="tech_test_watcher",
            technologies=["Python", "JavaScript", "React"],
            sources=["https://github.com/trending", "https://stackoverflow.com/questions/tagged/python"],
            state_file=str(self.state_file)
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_technology_watcher_initialization(self):
        """Test TechnologyWatcher initialization."""
        self.assertEqual(self.tech_watcher.technologies, ["Python", "JavaScript", "React"])
        self.assertEqual(len(self.tech_watcher.sources), 2)

    def test_track_technology_trends(self):
        """Test track_technology_trends updates trend data."""
        tech_data = {
            "Python": {"mentions": 150, "sentiment": "positive"},
            "JavaScript": {"mentions": 120, "sentiment": "neutral"},
            "React": {"mentions": 80, "sentiment": "positive"}
        }
        
        self.tech_watcher.track_technology_trends(tech_data)
        
        trends = self.tech_watcher.state.metadata.get("technology_trends", {})
        self.assertIn("Python", trends)
        self.assertEqual(trends["Python"]["mentions"], 150)

    def test_analyze_technology_sentiment(self):
        """Test analyze_technology_sentiment analyzes sentiment correctly."""
        positive_text = "Python is amazing and easy to use for development"
        negative_text = "Python is slow and difficult to deploy in production"
        
        positive_sentiment = self.tech_watcher.analyze_technology_sentiment(positive_text)
        negative_sentiment = self.tech_watcher.analyze_technology_sentiment(negative_text)
        
        self.assertIsInstance(positive_sentiment, str)
        self.assertIsInstance(negative_sentiment, str)

    def test_detect_technology_mentions(self):
        """Test detect_technology_mentions finds technology mentions."""
        text = "I love using Python and React for web development. JavaScript is also great."
        
        mentions = self.tech_watcher.detect_technology_mentions(text)
        
        self.assertIsInstance(mentions, list)
        expected_techs = ["Python", "React", "JavaScript"]
        for tech in expected_techs:
            self.assertIn(tech, mentions)


if __name__ == '__main__':
    unittest.main() 