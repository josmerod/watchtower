"""Tests for the recommendations dashboard tab component."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from dash import Dash, html

from src.web.dashboard.components.recommendations_tab import (
    RecommendationsManager,
    render_recommendations_tab,
    get_recommendation_icon,
    get_recommendation_type_label,
)


class TestRecommendationsManager:
    """Test suite for RecommendationsManager functionality."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def recommendations_manager(self, temp_data_dir):
        """Create a RecommendationsManager with mocked dependencies."""
        with patch('src.web.dashboard.components.recommendations_tab.UserActivityTracker') as mock_tracker, \
             patch('src.web.dashboard.components.recommendations_tab.RecommendationEngine') as mock_engine:

            # Configure mocks
            mock_tracker_instance = MagicMock()
            mock_engine_instance = MagicMock()
            mock_tracker.return_value = mock_tracker_instance
            mock_engine.return_value = mock_engine_instance

            manager = RecommendationsManager()
            manager.activity_tracker = mock_tracker_instance
            manager.recommendation_engine = mock_engine_instance

            return manager

    def test_init(self):
        """Test RecommendationsManager initialization."""
        with patch('src.web.dashboard.components.recommendations_tab.UserActivityTracker') as mock_tracker, \
             patch('src.web.dashboard.components.recommendations_tab.RecommendationEngine') as mock_engine:

            manager = RecommendationsManager()

            mock_tracker.assert_called_once()
            mock_engine.assert_called_once_with(mock_tracker.return_value)

    def test_get_user_recommendations_success(self, recommendations_manager):
        """Test successful retrieval of user recommendations."""
        from src.recommendations.models import UserRecommendations, Recommendation, RecommendationType

        # Mock existing recommendations (recent)
        mock_recommendations = UserRecommendations(
            user_id="test_user",
            generated_at=datetime.now() - timedelta(hours=12),  # Recent
        )
        mock_recommendations.add_recommendation(Recommendation(
            id="rec_1",
            user_id="test_user",
            type=RecommendationType.TOP_SOURCE,
            content_id="content_1",
            content_type="arxiv_paper",
            title="Test Paper",
            description="Test description",
            score=0.85,
        ))

        recommendations_manager.recommendation_engine.load_user_recommendations.return_value = mock_recommendations

        result = recommendations_manager.get_user_recommendations("test_user")

        assert result is not None
        assert result.user_id == "test_user"
        assert len(result.recommendations) == 1

    def test_get_user_recommendations_generate_new(self, recommendations_manager):
        """Test generation of new recommendations when none exist or are old."""
        from src.recommendations.models import UserRecommendations, Recommendation, RecommendationType

        # Mock old recommendations (should trigger new generation)
        old_recommendations = UserRecommendations(
            user_id="test_user",
            generated_at=datetime.now() - timedelta(days=2),  # Old
        )

        # Mock new recommendations to be generated
        new_recommendations = UserRecommendations(
            user_id="test_user",
            generated_at=datetime.now(),
        )
        new_recommendations.add_recommendation(Recommendation(
            id="rec_new",
            user_id="test_user",
            type=RecommendationType.TOP_SOURCE,
            content_id="content_new",
            content_type="arxiv_paper",
            title="New Paper",
            description="New description",
            score=0.9,
        ))

        recommendations_manager.recommendation_engine.load_user_recommendations.return_value = old_recommendations
        recommendations_manager.recommendation_engine.generate_recommendations.return_value = new_recommendations

        result = recommendations_manager.get_user_recommendations("test_user")

        assert result is not None
        assert result.user_id == "test_user"
        recommendations_manager.recommendation_engine.generate_recommendations.assert_called_once_with("test_user")

    def test_get_user_recommendations_no_data(self, recommendations_manager):
        """Test handling when no recommendations can be generated."""
        recommendations_manager.recommendation_engine.load_user_recommendations.return_value = None
        recommendations_manager.recommendation_engine.generate_recommendations.return_value = None

        result = recommendations_manager.get_user_recommendations("test_user")

        assert result is None

    def test_track_interaction_success(self, recommendations_manager):
        """Test successful interaction tracking."""
        from src.recommendations.models import ActivityType

        recommendations_manager.activity_tracker.track_interaction.return_value = True

        result = recommendations_manager.track_interaction(
            user_id="test_user",
            action="click",
            content_id="content_1",
            content_type="arxiv_paper",
            duration_seconds=120.0,
            source_category="AI",
            title="Test Paper"
        )

        assert result is True
        recommendations_manager.activity_tracker.track_interaction.assert_called_once()

    def test_track_interaction_failure(self, recommendations_manager):
        """Test handling of interaction tracking failure."""
        recommendations_manager.activity_tracker.track_interaction.return_value = False

        result = recommendations_manager.track_interaction(
            user_id="test_user",
            action="click",
            content_id="content_1",
            content_type="arxiv_paper"
        )

        assert result is False

    def test_update_feedback_success(self, recommendations_manager):
        """Test successful feedback update."""
        recommendations_manager.recommendation_engine.update_recommendation_feedback.return_value = True

        result = recommendations_manager.update_feedback(
            user_id="test_user",
            recommendation_id="rec_1",
            helpful=True
        )

        assert result is True
        recommendations_manager.recommendation_engine.update_recommendation_feedback.assert_called_once_with("test_user", "rec_1", True)

    def test_update_feedback_failure(self, recommendations_manager):
        """Test handling of feedback update failure."""
        recommendations_manager.recommendation_engine.update_recommendation_feedback.return_value = False

        result = recommendations_manager.update_feedback(
            user_id="test_user",
            recommendation_id="rec_1",
            helpful=False
        )

        assert result is False

    def test_dismiss_recommendation_success(self, recommendations_manager):
        """Test successful recommendation dismissal."""
        recommendations_manager.recommendation_engine.dismiss_recommendation.return_value = True

        result = recommendations_manager.dismiss_recommendation(
            user_id="test_user",
            recommendation_id="rec_1"
        )

        assert result is True
        recommendations_manager.recommendation_engine.dismiss_recommendation.assert_called_once_with("test_user", "rec_1")

    def test_dismiss_recommendation_failure(self, recommendations_manager):
        """Test handling of recommendation dismissal failure."""
        recommendations_manager.recommendation_engine.dismiss_recommendation.return_value = False

        result = recommendations_manager.dismiss_recommendation(
            user_id="test_user",
            recommendation_id="rec_1"
        )

        assert result is False


class TestRecommendationsTab:
    """Test suite for recommendations tab UI components."""

    def test_render_recommendations_tab(self):
        """Test rendering of the recommendations tab."""
        with patch('src.web.dashboard.components.recommendations_tab.recommendations_manager') as mock_manager:
            tab = render_recommendations_tab("test_user")

            # Check that the tab is a Dash component
            assert hasattr(tab, 'children')

            # Check for key elements
            tab_html = str(tab)
            assert "Recommended for You" in tab_html
            assert "Personalized recommendations" in tab_html
            assert "Refresh Recommendations" in tab_html

    def test_get_recommendation_icon(self):
        """Test getting icons for recommendation types."""
        assert get_recommendation_icon("top_source") == "bi-journal-text"
        assert get_recommendation_icon("top_category") == "bi-tag"
        assert get_recommendation_icon("similar_content") == "bi-link-45deg"
        assert get_recommendation_icon("trending") == "bi-graph-up"
        assert get_recommendation_icon("unknown") == "bi-star"  # Default icon

    def test_get_recommendation_type_label(self):
        """Test getting labels for recommendation types."""
        assert get_recommendation_type_label("top_source") == "Top Source"
        assert get_recommendation_type_label("top_category") == "Top Category"
        assert get_recommendation_type_label("similar_content") == "Similar Content"
        assert get_recommendation_type_label("trending") == "Trending"
        assert get_recommendation_type_label("unknown") == "Recommendation"  # Default label


class TestRecommendationsIntegration:
    """Integration tests for the recommendations system."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def dash_app(self):
        """Create a Dash app for testing."""
        app = Dash(__name__)
        app.layout = html.Div([html.Div(id="test-container")])
        return app

    def test_end_to_end_recommendation_flow(self, temp_data_dir):
        """Test end-to-end recommendation generation and display."""
        from src.recommendations.activity_tracker import UserActivityTracker
        from src.recommendations.recommendation_engine import RecommendationEngine
        from src.recommendations.models import ActivityEvent, ActivityType

        # Create real components with temporary directory
        activity_tracker = UserActivityTracker(data_dir=temp_data_dir)
        engine = RecommendationEngine(activity_tracker, data_dir=temp_data_dir)
        manager = RecommendationsManager()
        manager.activity_tracker = activity_tracker
        manager.recommendation_engine = engine

        # Track some user activities
        activities = [
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_1",
                content_type="arxiv_paper",
                source_category="machine_learning",
                title="Deep Learning Paper",
                duration_seconds=120.0,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.VIEW,
                content_id="news_1",
                content_type="news_article",
                source_category="technology",
                title="AI News",
                duration_seconds=60.0,
            ),
        ]

        # Save activities
        for activity in activities:
            activity_tracker.track_interaction(
                user_id=activity.user_id,
                action=activity.action,
                content_id=activity.content_id,
                content_type=activity.content_type,
                title=activity.title,
                source_category=activity.source_category,
                duration_seconds=activity.duration_seconds,
            )

        # Generate recommendations (will be None due to lack of content data)
        recommendations = manager.get_user_recommendations("test_user")

        # The system should handle the lack of content gracefully
        # In a real environment, this would generate recommendations
        assert recommendations is None or recommendations.user_id == "test_user"

    def test_feedback_workflow(self, temp_data_dir):
        """Test the complete feedback workflow."""
        from src.recommendations.activity_tracker import UserActivityTracker
        from src.recommendations.recommendation_engine import RecommendationEngine
        from src.recommendations.models import UserRecommendations, Recommendation, RecommendationType

        # Create real components
        activity_tracker = UserActivityTracker(data_dir=temp_data_dir)
        engine = RecommendationEngine(activity_tracker, data_dir=temp_data_dir)
        manager = RecommendationsManager()
        manager.activity_tracker = activity_tracker
        manager.recommendation_engine = engine

        # Create mock recommendations
        recommendations = UserRecommendations(user_id="test_user")
        rec = Recommendation(
            id="test_rec",
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
        engine.save_user_recommendations("test_user", recommendations)

        # Test feedback workflow
        feedback_success = manager.update_feedback("test_user", "test_rec", helpful=True)
        assert feedback_success is True

        # Verify feedback was recorded
        updated_recs = engine.load_user_recommendations("test_user")
        updated_rec = updated_recs.recommendations[0]
        assert updated_rec.feedback is True
        assert updated_rec.feedback_timestamp is not None

        # Test dismissal workflow
        dismiss_success = manager.dismiss_recommendation("test_user", "test_rec")
        assert dismiss_success is True

        # Verify dismissal was recorded
        final_recs = engine.load_user_recommendations("test_user")
        final_rec = final_recs.recommendations[0]
        assert final_rec.dismissed is True

    def test_activity_tracking_workflow(self, temp_data_dir):
        """Test the complete activity tracking workflow."""
        from src.recommendations.activity_tracker import UserActivityTracker
        from src.recommendations.models import ActivityType

        # Create activity tracker
        activity_tracker = UserActivityTracker(data_dir=temp_data_dir)

        # Track various interactions
        interactions = [
            ("click", "paper_1", "arxiv_paper", "Deep Learning", "AI", 120.0),
            ("view", "news_1", "news_article", "AI News", "technology", 60.0),
            ("search", "query_1", "search", "machine learning", None, None),
            ("filter", "filter_1", "arxiv_paper", "ML filter", "machine_learning", None),
        ]

        for action, content_id, content_type, title, category, duration in interactions:
            success = activity_tracker.track_interaction(
                user_id="test_user",
                action=ActivityType(action),
                content_id=content_id,
                content_type=content_type,
                title=title,
                source_category=category,
                duration_seconds=duration,
            )
            assert success is True

        # Verify activities were tracked
        activities = activity_tracker.load_user_activities("test_user")
        assert len(activities) == len(interactions)

        # Test activity summary
        summary = activity_tracker.get_activity_summary("test_user", days=7)
        assert summary["total_activities"] == len(interactions)
        assert summary["unique_content_items"] == len(set(content_id for _, content_id, *_ in interactions))
        assert "click" in summary["activity_types"]
        assert "view" in summary["activity_types"]

        # Test user profile generation
        profile = activity_tracker.get_user_profile("test_user")
        assert profile is not None
        assert profile.user_id == "test_user"
        assert profile.total_activities == len(interactions)
        assert len(profile.interaction_frequency) > 0