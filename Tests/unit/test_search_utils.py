"""Unit tests for search utility functions"""

import sys
from pathlib import Path

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.web.dashboard.search_utils import (
    cached_filter_content,
    create_search_input,
    filter_content,
    get_common_searchable_fields,
    highlight_matches,
    validate_search_performance,
)


class TestHighlightMatches:
    """Test the highlight_matches function"""

    def test_basic_highlight(self):
        """Test basic highlighting functionality"""
        text = "This is a test string"
        query = "test"
        result = highlight_matches(text, query)
        assert "<mark>test</mark>" in result

    def test_case_insensitive_highlight(self):
        """Test case-insensitive highlighting"""
        text = "This is a Test String"
        query = "test"
        result = highlight_matches(text, query)
        assert "<mark>test</mark>" in result

    def test_no_query(self):
        """Test that empty query returns original text"""
        text = "This is a test string"
        query = ""
        result = highlight_matches(text, query)
        assert result == text

    def test_no_match(self):
        """Test that non-matching query returns original text"""
        text = "This is a test string"
        query = "nomatch"
        result = highlight_matches(text, query)
        assert result == text

    def test_multiple_matches(self):
        """Test highlighting multiple occurrences"""
        text = "test and test again"
        query = "test"
        result = highlight_matches(text, query)
        # Should highlight both occurrences
        assert result.count("<mark>test</mark>") == 2

    def test_html_escaping(self):
        """Test that HTML is properly escaped before highlighting"""
        text = '<script>alert("xss")</script>'
        query = "script"
        result = highlight_matches(text, query)
        assert "&lt;<mark>script</mark>&gt;" in result
        assert "<mark>script</mark>" in result


class TestFilterContent:
    """Test the filter_content function"""

    def test_basic_filtering(self):
        """Test basic content filtering"""
        content = [
            {"title": "Test Article", "description": "A test description"},
            {"title": "Other Article", "description": "Something else"},
        ]
        query = "test"
        result = filter_content(query, content)
        assert len(result) == 1
        # filter_content adds highlighting by default
        assert result[0]["title"] == "<mark>test</mark> Article"

    def test_case_insensitive_filtering(self):
        """Test case-insensitive content filtering"""
        content = [
            {"title": "Test Article", "description": "A test description"},
            {"title": "test article", "description": "Something else"},
        ]
        query = "TEST"
        result = filter_content(query, content)
        assert len(result) == 2

    def test_filter_with_custom_fields(self):
        """Test filtering with custom searchable fields"""
        content = [
            {"title": "Test Article", "category": "tech"},
            {"title": "Other Article", "category": "test"},
        ]
        query = "test"
        searchable_fields = ["title", "category"]
        result = filter_content(query, content, searchable_fields)
        assert len(result) == 2

    def test_empty_content(self):
        """Test filtering empty content"""
        content = []
        query = "test"
        result = filter_content(query, content)
        assert result == []

    def test_empty_query(self):
        """Test empty query returns all content"""
        content = [{"title": "Test Article"}]
        query = ""
        result = filter_content(query, content)
        assert result == content

    def test_missing_fields(self):
        """Test filtering with missing fields"""
        content = [
            {"title": "Test Article"},  # missing description
            {"description": "Test description"},  # missing title
        ]
        query = "test"
        result = filter_content(query, content)
        assert len(result) == 2

    def test_no_matches(self):
        """Test filtering with no matches"""
        content = [{"title": "Other Article", "description": "Something else"}]
        query = "test"
        result = filter_content(query, content)
        assert len(result) == 0


class TestGetCommonSearchableFields:
    """Test the get_common_searchable_fields function"""

    def test_videos_fields(self):
        """Test videos content type fields"""
        fields = get_common_searchable_fields("videos")
        expected = ["title", "description", "channel", "published_at"]
        assert fields == expected

    def test_news_fields(self):
        """Test news content type fields"""
        fields = get_common_searchable_fields("news")
        expected = ["title", "description", "source", "summary", "source_display_name"]
        assert fields == expected

    def test_deals_fields(self):
        """Test deals content type fields"""
        fields = get_common_searchable_fields("deals")
        expected = [
            "title",
            "description",
            "platform",
            "source_category",
            "source_name",
        ]
        assert fields == expected

    def test_arxiv_fields(self):
        """Test arxiv content type fields"""
        fields = get_common_searchable_fields("arxiv")
        expected = ["title", "summary", "authors_display", "primary_category_display"]
        assert fields == expected

    def test_default_fields(self):
        """Test default content type fields"""
        fields = get_common_searchable_fields("unknown")
        expected = ["title", "description", "summary", "content", "source", "name"]
        assert fields == expected


class TestCreateSearchInput:
    """Test the create_search_input function"""

    def test_basic_search_input(self):
        """Test basic search input creation"""
        search_input = create_search_input("test-input", "Test placeholder")
        # Should return a Dash component
        assert search_input is not None

    def test_search_input_without_clear_button(self):
        """Test search input without clear button"""
        search_input = create_search_input("test-input", clear_button=False)
        # Should return a simple input component
        assert search_input is not None


class TestValidateSearchPerformance:
    """Test the validate_search_performance function"""

    def test_acceptable_performance(self):
        """Test acceptable content size"""
        result = validate_search_performance(5000)
        assert result is True

    def test_large_content_warning(self):
        """Test warning for large content size"""
        result = validate_search_performance(15000)
        assert result is False

    def test_custom_max_items(self):
        """Test custom max items threshold"""
        result = validate_search_performance(1000, max_items=500)
        assert result is False


class TestCachedFilterContent:
    """Test the cached_filter_content function"""

    def test_caching_functionality(self):
        """Test that caching works"""
        content = [{"title": "Test Article", "description": "A test description"}]

        # First call should compute result
        result1 = cached_filter_content("test", content, "hash1")

        # Second call with same parameters should return cached result
        result2 = cached_filter_content("test", content, "hash1")

        assert result1 == result2
        assert len(result1) == 1

    def test_different_content_hashes(self):
        """Test that different content hashes produce different results"""
        content1 = [{"title": "Test Article"}]
        content2 = [{"title": "Other Article"}]

        result1 = cached_filter_content("test", content1, "hash1")
        result2 = cached_filter_content("test", content2, "hash2")

        # Should have different results due to different content
        assert len(result1) == 1
        assert len(result2) == 0


if __name__ == "__main__":
    pytest.main([__file__])
