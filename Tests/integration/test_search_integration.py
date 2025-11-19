"""
Integration tests for search functionality across dashboard tabs
"""

import pytest
import json
from src.web.dashboard.utils.search_utils import (
    filter_content,
    get_common_searchable_fields,
    highlight_matches
)


class TestNewsSearchIntegration:
    """Test search functionality integration with news data"""

    def create_sample_news_data(self):
        """Create sample news data for testing"""
        return [
            {
                "title": "New AI Model Breakthrough",
                "description": "Researchers announce major advances in artificial intelligence",
                "source": "TechCrunch",
                "summary": "AI research breakthrough announced",
                "source_display_name": "TechCrunch",
                "published_at": "2025-01-16"
            },
            {
                "title": "Python 3.12 Released",
                "description": "Latest version of Python brings performance improvements",
                "source": "Ars Technica",
                "summary": "Python 3.12 features enhanced performance",
                "source_display_name": "Ars Technica",
                "published_at": "2025-01-15"
            },
            {
                "title": "Cloud Computing Trends",
                "description": "Analysis of current cloud computing adoption patterns",
                "source": "VentureBeat",
                "summary": "Cloud computing continues to grow",
                "source_display_name": "VentureBeat",
                "published_at": "2025-01-14"
            }
        ]

    def test_news_title_search(self):
        """Test searching news by title"""
        news_data = self.create_sample_news_data()
        searchable_fields = get_common_searchable_fields('news')

        result = filter_content("python", news_data, searchable_fields)

        assert len(result) == 1
        assert "Python 3.12" in result[0]["title"]
        assert result[0]["source_display_name"] == "Ars Technica"

    def test_news_description_search(self):
        """Test searching news by description"""
        news_data = self.create_sample_news_data()
        searchable_fields = get_common_searchable_fields('news')

        result = filter_content("artificial intelligence", news_data, searchable_fields)

        assert len(result) == 1
        assert "AI Model" in result[0]["title"]

    def test_news_source_search(self):
        """Test searching news by source"""
        news_data = self.create_sample_news_data()
        searchable_fields = get_common_searchable_fields('news')

        result = filter_content("TechCrunch", news_data, searchable_fields)

        assert len(result) == 1
        assert result[0]["source_display_name"] == "TechCrunch"

    def test_news_multiple_field_search(self):
        """Test searching across multiple news fields"""
        news_data = self.create_sample_news_data()
        searchable_fields = get_common_searchable_fields('news')

        result = filter_content("computing", news_data, searchable_fields)

        # Should find matches in both title and description
        assert len(result) >= 1
        titles = [item["title"] for item in result]
        assert any("Computing" in title for title in titles)


class TestDealsSearchIntegration:
    """Test search functionality integration with deals data"""

    def create_sample_deals_data(self):
        """Create sample deals data for testing"""
        return [
            {
                "title": "50% Off Software Bundle",
                "description": "Get 50% discount on premium software development tools",
                "platform": "StackSocial",
                "source_category": "Software",
                "source_name": "StackSocial Deals",
                "original_price": 299.99,
                "current_price": 149.99,
                "discount_percentage": 50.0,
                "savings": 150.00,
                "deal_rating": 4.5
            },
            {
                "title": "Gaming Laptop Deal",
                "description": "High-performance gaming laptop with 30% discount",
                "platform": "Amazon",
                "source_category": "Hardware",
                "source_name": "Amazon Deals",
                "original_price": 1299.99,
                "current_price": 909.99,
                "discount_percentage": 30.0,
                "savings": 390.00,
                "deal_rating": 4.2
            },
            {
                "title": "Online Course Bundle",
                "description": "Complete programming course bundle with lifetime access",
                "platform": "Udemy",
                "source_category": "Education",
                "source_name": "Udemy Deals",
                "original_price": 199.99,
                "current_price": 19.99,
                "discount_percentage": 90.0,
                "savings": 180.00,
                "deal_rating": 4.8
            }
        ]

    def test_deals_title_search(self):
        """Test searching deals by title"""
        deals_data = self.create_sample_deals_data()
        searchable_fields = get_common_searchable_fields('deals')

        result = filter_content("software", deals_data, searchable_fields)

        assert len(result) == 1
        assert "Software Bundle" in result[0]["title"]
        assert result[0]["platform"] == "StackSocial"

    def test_deals_platform_search(self):
        """Test searching deals by platform"""
        deals_data = self.create_sample_deals_data()
        searchable_fields = get_common_searchable_fields('deals')

        result = filter_content("Udemy", deals_data, searchable_fields)

        assert len(result) == 1
        assert result[0]["platform"] == "Udemy"

    def test_deals_category_search(self):
        """Test searching deals by category"""
        deals_data = self.create_sample_deals_data()
        searchable_fields = get_common_searchable_fields('deals')

        result = filter_content("hardware", deals_data, searchable_fields)

        assert len(result) == 1
        assert result[0]["source_category"] == "Hardware"

    def test_deals_description_search(self):
        """Test searching deals by description"""
        deals_data = self.create_sample_deals_data()
        searchable_fields = get_common_searchable_fields('deals')

        result = filter_content("programming", deals_data, searchable_fields)

        assert len(result) == 1
        assert "Course" in result[0]["title"]


class TestSearchHighlightingIntegration:
    """Test search highlighting in realistic scenarios"""

    def test_news_highlighting(self):
        """Test highlighting in news content"""
        news_item = {
            "title": "Breaking AI News Today",
            "description": "Latest developments in artificial intelligence",
            "source": "Tech News"
        }

        # Apply highlighting
        highlighted_title = highlight_matches(news_item["title"], "AI")
        highlighted_description = highlight_matches(news_item["description"], "artificial")

        assert "<mark>AI</mark>" in highlighted_title
        assert "<mark>artificial</mark>" in highlighted_description

    def test_deals_highlighting(self):
        """Test highlighting in deals content"""
        deal_item = {
            "title": "Software Development Bundle Deal",
            "description": "Complete development toolkit for programmers"
        }

        highlighted_title = highlight_matches(deal_item["title"], "software")
        highlighted_description = highlight_matches(deal_item["description"], "programmers")

        assert "<mark>software</mark>" in highlighted_title
        assert "<mark>programmers</mark>" in highlighted_description

    def test_multiple_highlights(self):
        """Test multiple highlights in the same text"""
        text = "Python software development bundle with programming tutorials"
        query = "python"

        highlighted = highlight_matches(text, query)

        # Should highlight both Python occurrences (case-insensitive)
        assert highlighted.count("<mark>python</mark>") == 2


class TestSearchFieldMappingIntegration:
    """Test that field mappings work correctly for different content types"""

    def test_news_fields_mapping(self):
        """Test news field mapping covers all necessary fields"""
        news_fields = get_common_searchable_fields('news')
        expected_fields = ['title', 'description', 'source', 'summary', 'source_display_name']

        for field in expected_fields:
            assert field in news_fields, f"Missing field '{field}' in news searchable fields"

    def test_deals_fields_mapping(self):
        """Test deals field mapping covers all necessary fields"""
        deals_fields = get_common_searchable_fields('deals')
        expected_fields = ['title', 'description', 'platform', 'source_category', 'source_name']

        for field in expected_fields:
            assert field in deals_fields, f"Missing field '{field}' in deals searchable fields"

    def test_field_mapping_with_missing_data(self):
        """Test that missing fields don't cause errors"""
        incomplete_news = [
            {"title": "News Article"},  # Missing description, source, etc.
            {"description": "Article description"}  # Missing title, source, etc.
        ]

        searchable_fields = get_common_searchable_fields('news')
        result = filter_content("article", incomplete_news, searchable_fields)

        # Should find both articles despite missing fields
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__])