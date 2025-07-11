"""
Comprehensive unit tests for all utility functions.
Tests file system operations, logging, deduplication, NLP, and more.
"""

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import List, Dict, Any

import pandas as pd
import pytest

from src.utils.file_system import (
    FileSystemManager, ensure_directory, read_json_file, 
    write_json_file, backup_file, get_file_size, 
    clean_filename, batch_process_files
)
from src.utils.logging import (
    setup_logging, get_logger, LogFormatter, StructuredLogger,
    log_execution_time, log_memory_usage
)
from src.utils.course_deduplication import (
    CourseDuplicateDetector, calculate_similarity, 
    normalize_course_title, extract_course_features
)
from src.utils.nlp_classifier import (
    TextClassifier, preprocess_text, extract_keywords,
    classify_technology_category, sentiment_analysis
)
from src.utils.github_utils import (
    GitHubAPIClient, parse_github_url, get_repo_stats,
    fetch_repository_info, get_trending_repositories
)
from src.utils.pwc_utils import (
    PWCDataExtractor, parse_paper_data, extract_benchmarks,
    format_benchmark_results, validate_paper_format
)
from src.utils.recommender import (
    ContentRecommender, calculate_content_similarity,
    generate_recommendations, filter_by_user_preferences,
    update_recommendation_model
)


class TestFileSystemManager(unittest.TestCase):
    """Test file system utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fs_manager = FileSystemManager(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ensure_directory_creates_new_directory(self):
        """Test ensure_directory creates new directory."""
        new_dir = self.test_dir / "new_directory"
        self.assertFalse(new_dir.exists())
        
        ensure_directory(new_dir)
        
        self.assertTrue(new_dir.exists())
        self.assertTrue(new_dir.is_dir())

    def test_ensure_directory_existing_directory(self):
        """Test ensure_directory with existing directory."""
        existing_dir = self.test_dir / "existing"
        existing_dir.mkdir()
        
        # Should not raise an error
        ensure_directory(existing_dir)
        
        self.assertTrue(existing_dir.exists())

    def test_read_json_file_valid_json(self):
        """Test reading valid JSON file."""
        test_data = {"name": "test", "value": 42}
        json_file = self.test_dir / "test.json"
        
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        result = read_json_file(json_file)
        
        self.assertEqual(result, test_data)

    def test_read_json_file_invalid_json(self):
        """Test reading invalid JSON file."""
        json_file = self.test_dir / "invalid.json"
        
        with open(json_file, 'w') as f:
            f.write("invalid json content")
        
        with self.assertRaises(json.JSONDecodeError):
            read_json_file(json_file)

    def test_read_json_file_missing_file(self):
        """Test reading missing JSON file."""
        missing_file = self.test_dir / "missing.json"
        
        with self.assertRaises(FileNotFoundError):
            read_json_file(missing_file)

    def test_write_json_file_success(self):
        """Test writing JSON file successfully."""
        test_data = {"items": [1, 2, 3], "status": "success"}
        json_file = self.test_dir / "output.json"
        
        write_json_file(json_file, test_data)
        
        self.assertTrue(json_file.exists())
        
        # Verify content
        with open(json_file) as f:
            result = json.load(f)
        
        self.assertEqual(result, test_data)

    def test_write_json_file_pretty_print(self):
        """Test writing JSON file with pretty printing."""
        test_data = {"nested": {"key": "value"}}
        json_file = self.test_dir / "pretty.json"
        
        write_json_file(json_file, test_data, indent=2)
        
        content = json_file.read_text()
        self.assertIn("  ", content)  # Should have indentation

    def test_backup_file_creates_backup(self):
        """Test backup_file creates backup copy."""
        original_file = self.test_dir / "original.txt"
        original_file.write_text("original content")
        
        backup_path = backup_file(original_file)
        
        self.assertTrue(backup_path.exists())
        self.assertEqual(backup_path.read_text(), "original content")
        self.assertIn("backup", str(backup_path))

    def test_get_file_size_existing_file(self):
        """Test get_file_size with existing file."""
        test_file = self.test_dir / "size_test.txt"
        content = "Hello, World!"
        test_file.write_text(content)
        
        size = get_file_size(test_file)
        
        self.assertEqual(size, len(content.encode('utf-8')))

    def test_get_file_size_missing_file(self):
        """Test get_file_size with missing file."""
        missing_file = self.test_dir / "missing.txt"
        
        size = get_file_size(missing_file)
        
        self.assertEqual(size, 0)

    def test_clean_filename_removes_invalid_chars(self):
        """Test clean_filename removes invalid characters."""
        dirty_filename = "file<>:\"/\\|?*name.txt"
        
        clean_name = clean_filename(dirty_filename)
        
        self.assertNotIn("<", clean_name)
        self.assertNotIn(">", clean_name)
        self.assertNotIn(":", clean_name)
        self.assertNotIn("*", clean_name)

    def test_clean_filename_preserves_valid_chars(self):
        """Test clean_filename preserves valid characters."""
        valid_filename = "valid_file-name.123.txt"
        
        clean_name = clean_filename(valid_filename)
        
        self.assertEqual(clean_name, valid_filename)

    def test_batch_process_files_success(self):
        """Test batch_process_files processes multiple files."""
        # Create test files
        for i in range(3):
            (self.test_dir / f"file_{i}.txt").write_text(f"content {i}")
        
        files = list(self.test_dir.glob("*.txt"))
        
        def process_func(file_path):
            return file_path.stat().st_size
        
        results = batch_process_files(files, process_func)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(r, int) for r in results))

    def test_filesystem_manager_data_dir_operations(self):
        """Test FileSystemManager data directory operations."""
        # Test data directory creation
        data_dir = self.fs_manager.get_data_dir("test_domain")
        self.assertTrue(data_dir.exists())
        
        # Test file saving
        test_data = [{"id": 1, "name": "test"}]
        self.fs_manager.save_data("test_domain", "test_file", test_data)
        
        saved_file = data_dir / "test_file.json"
        self.assertTrue(saved_file.exists())
        
        # Test file loading
        loaded_data = self.fs_manager.load_data("test_domain", "test_file")
        self.assertEqual(loaded_data, test_data)


class TestLoggingUtilities(unittest.TestCase):
    """Test logging utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # Clear any handlers that might have been added
        logging.getLogger().handlers.clear()

    def test_setup_logging_creates_logger(self):
        """Test setup_logging creates properly configured logger."""
        log_file = self.test_dir / "test.log"
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO",
            log_to_console=False
        )
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.level, logging.INFO)

    def test_get_logger_returns_configured_logger(self):
        """Test get_logger returns properly configured logger."""
        logger = get_logger("test_module")
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "watchtower.test_module")

    def test_log_formatter_formats_message(self):
        """Test LogFormatter formats log messages correctly."""
        formatter = LogFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        self.assertIn("Test message", formatted)
        self.assertIn("INFO", formatted)

    def test_structured_logger_logs_structured_data(self):
        """Test StructuredLogger logs structured data."""
        logger = StructuredLogger("test_logger")
        
        # Test that log methods exist and are callable
        self.assertTrue(hasattr(logger, 'log_event'))
        self.assertTrue(hasattr(logger, 'log_error'))
        self.assertTrue(hasattr(logger, 'log_performance'))

    @patch('time.time')
    def test_log_execution_time_decorator(self, mock_time):
        """Test log_execution_time decorator."""
        mock_time.side_effect = [0, 1]  # Start and end times
        
        @log_execution_time
        def test_function():
            return "result"
        
        result = test_function()
        
        self.assertEqual(result, "result")

    @patch('psutil.Process')
    def test_log_memory_usage_decorator(self, mock_process):
        """Test log_memory_usage decorator."""
        mock_process_instance = MagicMock()
        mock_process_instance.memory_info.return_value.rss = 1024 * 1024  # 1MB
        mock_process.return_value = mock_process_instance
        
        @log_memory_usage
        def test_function():
            return "result"
        
        result = test_function()
        
        self.assertEqual(result, "result")


class TestCourseDuplication(unittest.TestCase):
    """Test course deduplication utilities."""

    def setUp(self):
        """Set up test data."""
        self.detector = CourseDuplicateDetector()
        
        self.sample_courses = [
            {
                "title": "Python Programming for Beginners",
                "description": "Learn Python programming from scratch",
                "instructor": "John Doe",
                "duration": "10 hours",
                "price": 49.99
            },
            {
                "title": "Python Programming - Beginner Course",
                "description": "Master Python programming basics",
                "instructor": "John Doe",
                "duration": "12 hours", 
                "price": 59.99
            },
            {
                "title": "Advanced JavaScript Concepts",
                "description": "Deep dive into JavaScript",
                "instructor": "Jane Smith",
                "duration": "15 hours",
                "price": 99.99
            }
        ]

    def test_calculate_similarity_identical_strings(self):
        """Test calculate_similarity with identical strings."""
        similarity = calculate_similarity("hello world", "hello world")
        self.assertEqual(similarity, 1.0)

    def test_calculate_similarity_different_strings(self):
        """Test calculate_similarity with different strings."""
        similarity = calculate_similarity("hello", "world")
        self.assertLess(similarity, 0.5)

    def test_calculate_similarity_similar_strings(self):
        """Test calculate_similarity with similar strings."""
        similarity = calculate_similarity(
            "Python Programming Basics",
            "Python Programming Fundamentals"
        )
        self.assertGreater(similarity, 0.5)

    def test_normalize_course_title_removes_common_words(self):
        """Test normalize_course_title removes common words."""
        title = "The Complete Python Programming Course for Beginners"
        normalized = normalize_course_title(title)
        
        self.assertNotIn("the", normalized.lower())
        self.assertNotIn("complete", normalized.lower())
        self.assertNotIn("course", normalized.lower())
        self.assertIn("python", normalized.lower())

    def test_normalize_course_title_handles_special_chars(self):
        """Test normalize_course_title handles special characters."""
        title = "Python Programming: From Zero to Hero!"
        normalized = normalize_course_title(title)
        
        self.assertNotIn(":", normalized)
        self.assertNotIn("!", normalized)

    def test_extract_course_features_extracts_keywords(self):
        """Test extract_course_features extracts relevant keywords."""
        course = self.sample_courses[0]
        features = extract_course_features(course)
        
        self.assertIsInstance(features, dict)
        self.assertIn("keywords", features)
        self.assertIn("python", " ".join(features["keywords"]).lower())

    def test_course_duplicate_detector_finds_duplicates(self):
        """Test CourseDuplicateDetector finds duplicate courses."""
        duplicates = self.detector.find_duplicates(self.sample_courses)
        
        self.assertIsInstance(duplicates, list)
        # Should find the two similar Python courses
        self.assertGreater(len(duplicates), 0)

    def test_course_duplicate_detector_similarity_threshold(self):
        """Test CourseDuplicateDetector respects similarity threshold."""
        # High threshold should find fewer duplicates
        high_threshold_detector = CourseDuplicateDetector(similarity_threshold=0.9)
        high_duplicates = high_threshold_detector.find_duplicates(self.sample_courses)
        
        # Low threshold should find more duplicates
        low_threshold_detector = CourseDuplicateDetector(similarity_threshold=0.3)
        low_duplicates = low_threshold_detector.find_duplicates(self.sample_courses)
        
        self.assertLessEqual(len(high_duplicates), len(low_duplicates))


class TestNLPClassifier(unittest.TestCase):
    """Test NLP classification utilities."""

    def setUp(self):
        """Set up test environment."""
        self.classifier = TextClassifier()

    def test_preprocess_text_cleans_text(self):
        """Test preprocess_text cleans and normalizes text."""
        dirty_text = "  Hello, World! This is a TEST.  "
        cleaned = preprocess_text(dirty_text)
        
        self.assertEqual(cleaned.strip(), cleaned)  # No leading/trailing spaces
        self.assertNotIn(",", cleaned)
        self.assertNotIn("!", cleaned)
        self.assertEqual(cleaned, cleaned.lower())  # Should be lowercase

    def test_preprocess_text_handles_empty_string(self):
        """Test preprocess_text handles empty input."""
        result = preprocess_text("")
        self.assertEqual(result, "")

    def test_preprocess_text_handles_none(self):
        """Test preprocess_text handles None input."""
        result = preprocess_text(None)
        self.assertEqual(result, "")

    def test_extract_keywords_finds_important_words(self):
        """Test extract_keywords identifies important words."""
        text = "Machine learning and artificial intelligence are transforming technology"
        keywords = extract_keywords(text, max_keywords=3)
        
        self.assertIsInstance(keywords, list)
        self.assertLessEqual(len(keywords), 3)
        self.assertTrue(any("machine" in kw.lower() or "learning" in kw.lower() for kw in keywords))

    def test_extract_keywords_handles_short_text(self):
        """Test extract_keywords handles short text."""
        text = "Hello world"
        keywords = extract_keywords(text)
        
        self.assertIsInstance(keywords, list)

    def test_classify_technology_category_programming_language(self):
        """Test classify_technology_category identifies programming languages."""
        text = "Python is a high-level programming language with dynamic semantics"
        category = classify_technology_category(text)
        
        self.assertIn("programming", category.lower())

    def test_classify_technology_category_framework(self):
        """Test classify_technology_category identifies frameworks."""
        text = "React is a JavaScript framework for building user interfaces"
        category = classify_technology_category(text)
        
        self.assertIn("framework", category.lower())

    def test_sentiment_analysis_positive(self):
        """Test sentiment_analysis identifies positive sentiment."""
        positive_text = "This is an excellent and amazing product that I love"
        sentiment = sentiment_analysis(positive_text)
        
        self.assertIn("positive", sentiment.lower())

    def test_sentiment_analysis_negative(self):
        """Test sentiment_analysis identifies negative sentiment."""
        negative_text = "This is terrible and awful, I hate it completely"
        sentiment = sentiment_analysis(negative_text)
        
        self.assertIn("negative", sentiment.lower())

    def test_sentiment_analysis_neutral(self):
        """Test sentiment_analysis identifies neutral sentiment."""
        neutral_text = "This is a product with various features and specifications"
        sentiment = sentiment_analysis(neutral_text)
        
        self.assertIn("neutral", sentiment.lower())


class TestGitHubUtils(unittest.TestCase):
    """Test GitHub utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.github_client = GitHubAPIClient(token="fake_token")

    def test_parse_github_url_valid_url(self):
        """Test parse_github_url with valid GitHub URL."""
        url = "https://github.com/owner/repo"
        owner, repo = parse_github_url(url)
        
        self.assertEqual(owner, "owner")
        self.assertEqual(repo, "repo")

    def test_parse_github_url_with_git_extension(self):
        """Test parse_github_url with .git extension."""
        url = "https://github.com/owner/repo.git"
        owner, repo = parse_github_url(url)
        
        self.assertEqual(owner, "owner")
        self.assertEqual(repo, "repo")

    def test_parse_github_url_invalid_url(self):
        """Test parse_github_url with invalid URL."""
        url = "https://example.com/not/github"
        
        with self.assertRaises(ValueError):
            parse_github_url(url)

    @patch('requests.get')
    def test_get_repo_stats_success(self, mock_get):
        """Test get_repo_stats with successful API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "stars": 1000,
            "forks": 200,
            "open_issues": 50,
            "watchers": 800
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        stats = get_repo_stats("owner", "repo")
        
        self.assertEqual(stats["stars"], 1000)
        self.assertEqual(stats["forks"], 200)

    @patch('requests.get')
    def test_get_repo_stats_api_error(self, mock_get):
        """Test get_repo_stats with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        stats = get_repo_stats("owner", "repo")
        
        self.assertIsNone(stats)


class TestPWCUtils(unittest.TestCase):
    """Test Papers with Code utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.extractor = PWCDataExtractor()

    def test_parse_paper_data_valid_format(self):
        """Test parse_paper_data with valid paper data."""
        paper_data = {
            "title": "Test Paper",
            "abstract": "Test abstract",
            "authors": ["Author 1", "Author 2"],
            "url": "https://arxiv.org/abs/2301.00001",
            "benchmarks": [
                {"dataset": "ImageNet", "metric": "Accuracy", "value": 95.2}
            ]
        }
        
        parsed = parse_paper_data(paper_data)
        
        self.assertEqual(parsed["title"], "Test Paper")
        self.assertEqual(len(parsed["authors"]), 2)
        self.assertEqual(len(parsed["benchmarks"]), 1)

    def test_extract_benchmarks_from_paper(self):
        """Test extract_benchmarks extracts benchmark data."""
        paper_text = """
        Our model achieves 95.2% accuracy on ImageNet.
        We also report 88.5% F1 score on GLUE benchmark.
        """
        
        benchmarks = extract_benchmarks(paper_text)
        
        self.assertIsInstance(benchmarks, list)
        self.assertGreater(len(benchmarks), 0)

    def test_format_benchmark_results_creates_table(self):
        """Test format_benchmark_results creates formatted table."""
        benchmarks = [
            {"dataset": "ImageNet", "metric": "Accuracy", "value": 95.2},
            {"dataset": "CIFAR-10", "metric": "Accuracy", "value": 98.1}
        ]
        
        formatted = format_benchmark_results(benchmarks)
        
        self.assertIsInstance(formatted, str)
        self.assertIn("ImageNet", formatted)
        self.assertIn("95.2", formatted)

    def test_validate_paper_format_valid_paper(self):
        """Test validate_paper_format with valid paper."""
        paper = {
            "title": "Valid Paper",
            "abstract": "Valid abstract",
            "authors": ["Author 1"],
            "url": "https://arxiv.org/abs/2301.00001"
        }
        
        is_valid = validate_paper_format(paper)
        
        self.assertTrue(is_valid)

    def test_validate_paper_format_invalid_paper(self):
        """Test validate_paper_format with invalid paper."""
        paper = {
            "title": "",  # Empty title
            "authors": []  # No authors
        }
        
        is_valid = validate_paper_format(paper)
        
        self.assertFalse(is_valid)


class TestRecommender(unittest.TestCase):
    """Test content recommendation utilities."""

    def setUp(self):
        """Set up test environment."""
        self.recommender = ContentRecommender()
        
        self.sample_content = [
            {
                "id": 1,
                "title": "Python Programming",
                "description": "Learn Python programming",
                "tags": ["python", "programming", "beginner"],
                "category": "programming"
            },
            {
                "id": 2,
                "title": "Machine Learning Basics",
                "description": "Introduction to machine learning",
                "tags": ["ml", "python", "data-science"],
                "category": "data-science"
            },
            {
                "id": 3,
                "title": "Web Development",
                "description": "Build web applications",
                "tags": ["web", "javascript", "html"],
                "category": "web-development"
            }
        ]

    def test_calculate_content_similarity_identical_content(self):
        """Test calculate_content_similarity with identical content."""
        content1 = self.sample_content[0]
        similarity = calculate_content_similarity(content1, content1)
        
        self.assertEqual(similarity, 1.0)

    def test_calculate_content_similarity_related_content(self):
        """Test calculate_content_similarity with related content."""
        content1 = self.sample_content[0]  # Python programming
        content2 = self.sample_content[1]  # Machine learning (also Python)
        
        similarity = calculate_content_similarity(content1, content2)
        
        self.assertGreater(similarity, 0.0)
        self.assertLess(similarity, 1.0)

    def test_generate_recommendations_returns_similar_content(self):
        """Test generate_recommendations returns similar content."""
        target_content = self.sample_content[0]
        
        recommendations = generate_recommendations(
            target_content, 
            self.sample_content,
            max_recommendations=2
        )
        
        self.assertIsInstance(recommendations, list)
        self.assertLessEqual(len(recommendations), 2)
        # Should not include the target content itself
        self.assertNotIn(target_content["id"], [r["id"] for r in recommendations])

    def test_filter_by_user_preferences_filters_content(self):
        """Test filter_by_user_preferences filters content correctly."""
        user_preferences = {
            "categories": ["programming", "data-science"],
            "tags": ["python"],
            "exclude_categories": ["web-development"]
        }
        
        filtered = filter_by_user_preferences(self.sample_content, user_preferences)
        
        self.assertIsInstance(filtered, list)
        self.assertLess(len(filtered), len(self.sample_content))
        # Should not include web development content
        self.assertTrue(all(c["category"] != "web-development" for c in filtered))

    def test_update_recommendation_model_processes_feedback(self):
        """Test update_recommendation_model processes user feedback."""
        feedback = [
            {"content_id": 1, "rating": 5, "user_action": "liked"},
            {"content_id": 2, "rating": 3, "user_action": "viewed"},
            {"content_id": 3, "rating": 1, "user_action": "disliked"}
        ]
        
        # Should not raise an exception
        try:
            update_recommendation_model(feedback)
            success = True
        except Exception:
            success = False
        
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main() 