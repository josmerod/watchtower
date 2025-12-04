"""Tests for the RecommendationEngine class."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.recommendations.activity_tracker import UserActivityTracker
from src.recommendations.models import (
    ActivityEvent,
    ActivityType,
    RecommendationType,
    UserActivityProfile,
)
from src.recommendations.recommendation_engine import RecommendationEngine


class TestRecommendationEngine:
    """Test suite for RecommendationEngine functionality."""

    @pytest.fixture()
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture()
    def activity_tracker(self, temp_data_dir):
        """Create a UserActivityTracker instance for testing."""
        return UserActivityTracker(data_dir=temp_data_dir)

    @pytest.fixture()
    def recommendation_engine(self, activity_tracker, temp_data_dir):
        """Create a RecommendationEngine instance for testing."""
        return RecommendationEngine(activity_tracker=activity_tracker, data_dir=temp_data_dir)

    @pytest.fixture()
    def sample_activities(self):
        """Create sample activity events for testing."""
        base_time = datetime.now() - timedelta(days=1)
        return [
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_1",
                content_type="arxiv_paper",
                source_category="machine_learning",
                title="Deep Learning Advances",
                timestamp=base_time,
                duration_seconds=120.0,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_2",
                content_type="arxiv_paper",
                source_category="AI",
                title="Neural Networks Explained",
                timestamp=base_time + timedelta(hours=2),
                duration_seconds=90.0,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.VIEW,
                content_id="news_1",
                content_type="news_article",
                source_category="technology",
                title="AI Breakthrough News",
                timestamp=base_time + timedelta(hours=4),
                duration_seconds=45.0,
            ),
        ]

    @pytest.fixture()
    def mock_content_data(self):
        """Create mock content data for testing content finding functions."""
        return [
            {
                "id": "paper_3",
                "title": "Machine Learning Trends",
                "type": "arxiv_paper",
                "recent_count": 5,
            },
            {
                "id": "paper_4",
                "title": "Deep Learning Fundamentals",
                "type": "arxiv_paper",
                "recent_count": 3,
            },
            {
                "id": "news_2",
                "title": "Technology News Today",
                "type": "news_article",
                "recent_count": 10,
            },
        ]

    def test_init_with_default_tracker(self, temp_data_dir):
        """Test RecommendationEngine initialization with default tracker."""
        engine = RecommendationEngine(data_dir=temp_data_dir)
        assert engine.activity_tracker is not None
        assert engine.data_dir == temp_data_dir
        assert engine.recommendation_window_days == 7

    def test_init_with_custom_tracker(self, activity_tracker, temp_data_dir):
        """Test RecommendationEngine initialization with custom tracker."""
        engine = RecommendationEngine(activity_tracker=activity_tracker, data_dir=temp_data_dir)
        assert engine.activity_tracker == activity_tracker

    def test_generate_recommendations_insufficient_data(self, recommendation_engine):
        """Test recommendation generation with insufficient user data."""
        recommendations = recommendation_engine.generate_recommendations("new_user")
        assert recommendations is None

    def test_generate_recommendations_no_activities(self, recommendation_engine):
        """Test recommendation generation when user has no activities."""
        # Mock profile to return insufficient activities
        with patch.object(recommendation_engine.activity_tracker, "get_user_profile") as mock_profile:
            mock_profile.return_value = None
            recommendations = recommendation_engine.generate_recommendations("test_user")
            assert recommendations is None

    def test_generate_recommendations_success(self, recommendation_engine, sample_activities, mock_content_data):
        """Test successful recommendation generation."""
        # Setup user profile
        profile = UserActivityProfile(
            user_id="test_user",
            total_activities=10,
            top_sources=["arxiv_paper", "news_article"],
            top_categories=["machine_learning", "technology"],
        )

        # Setup mocks
        with (
            patch.object(
                recommendation_engine.activity_tracker,
                "get_user_profile",
                return_value=profile,
            ),
            patch.object(
                recommendation_engine.activity_tracker,
                "load_user_activities",
                return_value=sample_activities,
            ),
            patch.object(
                recommendation_engine,
                "_find_recent_content_by_type",
                return_value=mock_content_data,
            ),
            patch.object(
                recommendation_engine,
                "_find_recent_content_by_category",
                return_value=mock_content_data,
            ),
            patch.object(
                recommendation_engine,
                "_find_similar_content",
                return_value=mock_content_data,
            ),
        ):
            recommendations = recommendation_engine.generate_recommendations("test_user")

            assert recommendations is not None
            assert recommendations.user_id == "test_user"
            assert len(recommendations.recommendations) > 0
            assert recommendations.total_activities_analyzed == len(sample_activities)

    def test_generate_top_source_recommendations(self, recommendation_engine):
        """Test generation of top source recommendations."""
        profile = UserActivityProfile(
            user_id="test_user",
            top_sources=["arxiv_paper", "news_article"],
        )

        from src.recommendations.models import UserRecommendations

        recommendations = UserRecommendations(user_id="test_user")

        mock_content = [
            {"id": "paper_1", "title": "ML Paper", "type": "arxiv_paper"},
            {"id": "paper_2", "title": "AI Paper", "type": "arxiv_paper"},
        ]

        with patch.object(
            recommendation_engine,
            "_find_recent_content_by_type",
            return_value=mock_content,
        ):
            recommendation_engine._generate_top_source_recommendations("test_user", profile, recommendations)

            # Should have recommendations for top sources
            source_recs = [r for r in recommendations.recommendations if r.type == RecommendationType.TOP_SOURCE]
            assert len(source_recs) > 0

            # Verify recommendation structure
            rec = source_recs[0]
            assert rec.user_id == "test_user"
            assert rec.type == RecommendationType.TOP_SOURCE
            assert rec.content_id in ["paper_1", "paper_2"]

    def test_generate_top_category_recommendations(self, recommendation_engine):
        """Test generation of top category recommendations."""
        profile = UserActivityProfile(
            user_id="test_user",
            top_categories=["machine_learning", "technology"],
        )

        from src.recommendations.models import UserRecommendations

        recommendations = UserRecommendations(user_id="test_user")

        mock_content = [
            {"id": "content_1", "title": "ML Content", "type": "arxiv_paper"},
            {"id": "content_2", "title": "Tech Content", "type": "news_article"},
        ]

        with patch.object(
            recommendation_engine,
            "_find_recent_content_by_category",
            return_value=mock_content,
        ):
            recommendation_engine._generate_top_category_recommendations("test_user", profile, recommendations)

            # Should have recommendations for top categories
            category_recs = [r for r in recommendations.recommendations if r.type == RecommendationType.TOP_CATEGORY]
            assert len(category_recs) > 0

            # Verify recommendation structure
            rec = category_recs[0]
            assert rec.user_id == "test_user"
            assert rec.type == RecommendationType.TOP_CATEGORY

    def test_generate_similar_content_recommendations(self, recommendation_engine, sample_activities):
        """Test generation of similar content recommendations."""
        from src.recommendations.models import UserRecommendations

        recommendations = UserRecommendations(user_id="test_user")

        mock_similar_content = [
            {
                "id": "similar_1",
                "title": "Deep Learning Advances Guide",
                "type": "arxiv_paper",
                "similarity_score": 0.8,
            },
            {
                "id": "similar_2",
                "title": "ML Tutorial",
                "type": "arxiv_paper",
                "similarity_score": 0.6,
            },
        ]

        with patch.object(
            recommendation_engine,
            "_find_similar_content",
            return_value=mock_similar_content,
        ):
            recommendation_engine._generate_similar_content_recommendations("test_user", sample_activities, recommendations)

            # Should have similar content recommendations
            similar_recs = [r for r in recommendations.recommendations if r.type == RecommendationType.SIMILAR_CONTENT]
            assert len(similar_recs) > 0

            # Verify recommendation structure
            rec = similar_recs[0]
            assert rec.user_id == "test_user"
            assert rec.type == RecommendationType.SIMILAR_CONTENT
            assert "Similar to" in rec.description

    def test_find_recent_content_by_type_arxiv(self, recommendation_engine, temp_data_dir):
        """Test finding recent ArXiv content."""
        # Create mock ArXiv data file
        arxiv_dir = temp_data_dir / "data" / "arxiv"
        arxiv_dir.mkdir(parents=True)
        arxiv_file = arxiv_dir / "latest.json"

        mock_data = [
            {
                "id": "paper_1",
                "title": "Machine Learning Paper",
                "abstract": "Test abstract",
            },
            {
                "id": "paper_2",
                "title": "Deep Learning Paper",
                "abstract": "Another test",
            },
        ]

        with open(arxiv_file, "w") as f:
            json.dump(mock_data, f)

        # Mock settings to point to our temp directory
        with patch.object(recommendation_engine.settings, "project_root", str(temp_data_dir)):
            content = recommendation_engine._find_recent_content_by_type("arxiv_paper", limit=2)

            assert len(content) == 2
            assert content[0]["id"] == "paper_1"
            assert content[0]["title"] == "Machine Learning Paper"
            assert content[0]["type"] == "arxiv_paper"

    def test_find_recent_content_by_type_news(self, recommendation_engine, temp_data_dir):
        """Test finding recent news content."""
        # Create mock news data file
        news_dir = temp_data_dir / "data" / "news"
        news_dir.mkdir(parents=True)
        news_file = news_dir / "latest.json"

        mock_data = [
            {"id": "news_1", "title": "Tech News Today", "url": "http://example.com"},
            {"id": "news_2", "title": "AI News Update", "url": "http://example2.com"},
        ]

        with open(news_file, "w") as f:
            json.dump(mock_data, f)

        # Mock settings to point to our temp directory
        with patch.object(recommendation_engine.settings, "project_root", str(temp_data_dir)):
            content = recommendation_engine._find_recent_content_by_type("news_article", limit=2)

            assert len(content) == 2
            assert content[0]["id"] == "news_1"
            assert content[0]["title"] == "Tech News Today"
            assert content[0]["type"] == "news_article"

    def test_calculate_title_similarity(self, recommendation_engine):
        """Test title similarity calculation."""
        # Test identical titles
        similarity = recommendation_engine._calculate_title_similarity("Machine Learning", "Machine Learning")
        assert similarity == 1.0

        # Test similar titles
        similarity = recommendation_engine._calculate_title_similarity("Machine Learning", "Machine Learning Advances")
        assert similarity > 0.5

        # Test different titles
        similarity = recommendation_engine._calculate_title_similarity("Machine Learning", "Cooking Recipes")
        assert similarity == 0.0

        # Test partial overlap
        similarity = recommendation_engine._calculate_title_similarity("Deep Learning in Practice", "Learning Deep Networks")
        assert similarity > 0.0 and similarity < 1.0

    def test_find_similar_content(self, recommendation_engine):
        """Test finding similar content based on title."""
        mock_content = [
            {
                "id": "content_1",
                "title": "Machine Learning Fundamentals",
                "type": "arxiv_paper",
            },
            {
                "id": "content_2",
                "title": "Deep Learning Advances",
                "type": "arxiv_paper",
            },
            {"id": "content_3", "title": "Cooking Recipe Book", "type": "book"},
        ]

        with patch.object(
            recommendation_engine,
            "_find_recent_content_by_type",
            return_value=mock_content,
        ):
            similar = recommendation_engine._find_similar_content("Machine Learning Tutorial", "arxiv_paper")

            # Should return content with similar titles
            assert len(similar) > 0
            # Should prioritize titles with "Learning" in them
            learning_content = [c for c in similar if "Learning" in c["title"]]
            assert len(learning_content) > 0

    def test_generate_recommendation_id(self, recommendation_engine):
        """Test generation of unique recommendation IDs."""
        id1 = recommendation_engine._generate_recommendation_id("user1", "type1", "content1")
        id2 = recommendation_engine._generate_recommendation_id("user1", "type1", "content1")
        id3 = recommendation_engine._generate_recommendation_id("user2", "type1", "content1")

        # IDs should be unique due to timestamp
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

        # IDs should be valid hex strings
        assert all(c in "0123456789abcdef" for c in id1)
        assert len(id1) == 16

    def test_save_and_load_user_recommendations(self, recommendation_engine):
        """Test saving and loading user recommendations."""
        from src.recommendations.models import Recommendation, UserRecommendations

        # Create test recommendations
        recommendations = UserRecommendations(
            user_id="test_user",
            total_activities_analyzed=50,
        )

        rec = Recommendation(
            id="test_rec_1",
            user_id="test_user",
            type=RecommendationType.TOP_SOURCE,
            content_id="content_1",
            content_type="arxiv_paper",
            title="Test Paper",
            description="Test description",
            score=0.85,
        )

        recommendations.add_recommendation(rec)

        # Save recommendations
        success = recommendation_engine.save_user_recommendations("test_user", recommendations)
        assert success is True

        # Load recommendations
        loaded_recommendations = recommendation_engine.load_user_recommendations("test_user")
        assert loaded_recommendations is not None
        assert loaded_recommendations.user_id == "test_user"
        assert len(loaded_recommendations.recommendations) == 1
        assert loaded_recommendations.recommendations[0].id == "test_rec_1"
        assert loaded_recommendations.recommendations[0].score == 0.85

    def test_update_recommendation_feedback(self, recommendation_engine):
        """Test updating recommendation feedback."""
        from src.recommendations.models import Recommendation, UserRecommendations

        # Create test recommendations
        recommendations = UserRecommendations(user_id="test_user")
        rec = Recommendation(
            id="test_rec_1",
            user_id="test_user",
            type=RecommendationType.TOP_SOURCE,
            content_id="content_1",
            content_type="arxiv_paper",
            title="Test Paper",
            description="Test description",
            score=0.85,
        )
        recommendations.add_recommendation(rec)

        # Save recommendations
        recommendation_engine.save_user_recommendations("test_user", recommendations)

        # Update feedback
        success = recommendation_engine.update_recommendation_feedback("test_user", "test_rec_1", helpful=True)
        assert success is True

        # Verify feedback was updated
        updated_recommendations = recommendation_engine.load_user_recommendations("test_user")
        updated_rec = updated_recommendations.recommendations[0]
        assert updated_rec.feedback is True
        assert updated_rec.feedback_timestamp is not None

    def test_dismiss_recommendation(self, recommendation_engine):
        """Test dismissing a recommendation."""
        from src.recommendations.models import Recommendation, UserRecommendations

        # Create test recommendations
        recommendations = UserRecommendations(user_id="test_user")
        rec = Recommendation(
            id="test_rec_1",
            user_id="test_user",
            type=RecommendationType.TOP_SOURCE,
            content_id="content_1",
            content_type="arxiv_paper",
            title="Test Paper",
            description="Test description",
            score=0.85,
        )
        recommendations.add_recommendation(rec)

        # Save recommendations
        recommendation_engine.save_user_recommendations("test_user", recommendations)

        # Dismiss recommendation
        success = recommendation_engine.dismiss_recommendation("test_user", "test_rec_1")
        assert success is True

        # Verify recommendation was dismissed
        updated_recommendations = recommendation_engine.load_user_recommendations("test_user")
        updated_rec = updated_recommendations.recommendations[0]
        assert updated_rec.dismissed is True

    def test_update_feedback_nonexistent_recommendation(self, recommendation_engine):
        """Test updating feedback for non-existent recommendation."""
        success = recommendation_engine.update_recommendation_feedback("test_user", "nonexistent", helpful=True)
        assert success is False

    def test_dismiss_nonexistent_recommendation(self, recommendation_engine):
        """Test dismissing non-existent recommendation."""
        success = recommendation_engine.dismiss_recommendation("test_user", "nonexistent")
        assert success is False

    def test_get_related_content(self, recommendation_engine):
        """Test getting related content."""
        mock_similar_content = [
            {
                "id": "similar_1",
                "title": "Deep Learning Guide",
                "type": "arxiv_paper",
                "similarity_score": 0.8,
            },
            {
                "id": "similar_2",
                "title": "ML Tutorial",
                "type": "arxiv_paper",
                "similarity_score": 0.6,
            },
        ]

        with patch.object(
            recommendation_engine,
            "_find_similar_content",
            return_value=mock_similar_content,
        ):
            related = recommendation_engine.get_related_content("Deep Learning", "arxiv_paper")

            assert len(related) == 2
            assert related[0]["id"] == "similar_1"
            assert related[1]["id"] == "similar_2"
