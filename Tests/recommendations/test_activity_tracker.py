"""Tests for the UserActivityTracker class."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.recommendations.activity_tracker import UserActivityTracker
from src.recommendations.models import ActivityEvent, ActivityType


class TestUserActivityTracker:
    """Test suite for UserActivityTracker functionality."""

    @pytest.fixture()
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture()
    def activity_tracker(self, temp_data_dir):
        """Create a UserActivityTracker instance with temporary data directory."""
        return UserActivityTracker(data_dir=temp_data_dir)

    @pytest.fixture()
    def sample_activities(self):
        """Create sample activity events for testing."""
        return [
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_1",
                content_type="arxiv_paper",
                source_category="machine_learning",
                title="Deep Learning Advances",
                duration_seconds=120.5,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.VIEW,
                content_id="news_1",
                content_type="news_article",
                source_category="technology",
                title="AI Breakthrough News",
                duration_seconds=45.0,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.SEARCH,
                content_id="search_query",
                content_type="search",
                metadata={"query": "machine learning"},
            ),
        ]

    def test_init_with_default_directory(self):
        """Test UserActivityTracker initialization with default directory."""
        tracker = UserActivityTracker()
        assert tracker.data_dir.name == "users"
        assert tracker.activity_window_days == 30

    def test_init_with_custom_directory(self, temp_data_dir):
        """Test UserActivityTracker initialization with custom directory."""
        tracker = UserActivityTracker(data_dir=temp_data_dir)
        assert tracker.data_dir == temp_data_dir
        assert temp_data_dir.exists()

    def test_track_interaction_success(self, activity_tracker):
        """Test successful activity tracking."""
        success = activity_tracker.track_interaction(
            user_id="test_user",
            action=ActivityType.CLICK,
            content_id="content_1",
            content_type="arxiv_paper",
            source_category="AI",
            title="Test Paper",
        )

        assert success is True
        assert activity_tracker.get_user_activity_file("test_user").exists()

    def test_track_interaction_with_metadata(self, activity_tracker):
        """Test activity tracking with metadata."""
        metadata = {"source": "dashboard", "device": "desktop"}
        success = activity_tracker.track_interaction(
            user_id="test_user",
            action=ActivityType.VIEW,
            content_id="content_1",
            content_type="news_article",
            metadata=metadata,
        )

        assert success is True

        # Verify metadata is saved
        activities = activity_tracker.load_user_activities("test_user")
        assert len(activities) == 1
        assert activities[0].metadata == metadata

    def test_track_interaction_with_duration(self, activity_tracker):
        """Test activity tracking with duration."""
        success = activity_tracker.track_interaction(
            user_id="test_user",
            action=ActivityType.VIEW,
            content_id="content_1",
            content_type="arxiv_paper",
            duration_seconds=180.5,
        )

        assert success is True

        activities = activity_tracker.load_user_activities("test_user")
        assert len(activities) == 1
        assert activities[0].duration_seconds == 180.5

    def test_track_interaction_failure(self, activity_tracker):
        """Test activity tracking failure handling."""
        # Mock Path operations to raise an exception
        with patch.object(
            activity_tracker.get_user_activity_file("test_user"),
            "exists",
            side_effect=Exception("Test error"),
        ):
            success = activity_tracker.track_interaction(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="content_1",
                content_type="arxiv_paper",
            )

            assert success is False

    def test_load_user_activities_empty(self, activity_tracker):
        """Test loading activities for user with no activities."""
        activities = activity_tracker.load_user_activities("nonexistent_user")
        assert activities == []

    def test_load_user_activities_with_data(self, activity_tracker, sample_activities):
        """Test loading activities for user with existing data."""
        # Save sample activities
        activity_tracker.save_user_activities("test_user", sample_activities)

        loaded_activities = activity_tracker.load_user_activities("test_user")
        assert len(loaded_activities) == len(sample_activities)

        # Verify activity data integrity
        for i, activity in enumerate(loaded_activities):
            assert activity.user_id == sample_activities[i].user_id
            assert activity.action == sample_activities[i].action
            assert activity.content_id == sample_activities[i].content_id
            assert activity.content_type == sample_activities[i].content_type

    def test_load_user_activities_with_date_filter(self, activity_tracker):
        """Test loading activities with date filtering."""
        # Create activities with different timestamps
        old_activity = ActivityEvent(
            user_id="test_user",
            action=ActivityType.CLICK,
            content_id="old_content",
            content_type="arxiv_paper",
            timestamp=datetime.now() - timedelta(days=10),
        )
        recent_activity = ActivityEvent(
            user_id="test_user",
            action=ActivityType.CLICK,
            content_id="recent_content",
            content_type="news_article",
            timestamp=datetime.now() - timedelta(days=1),
        )

        activity_tracker.save_user_activities("test_user", [old_activity, recent_activity])

        # Load last 5 days - should only get recent activity
        filtered_activities = activity_tracker.load_user_activities("test_user", days=5)
        assert len(filtered_activities) == 1
        assert filtered_activities[0].content_id == "recent_content"

    def test_save_user_activities_success(self, activity_tracker, sample_activities):
        """Test successful saving of user activities."""
        success = activity_tracker.save_user_activities("test_user", sample_activities)
        assert success is True

        # Verify file was created and contains data
        activity_file = activity_tracker.get_user_activity_file("test_user")
        assert activity_file.exists()

        with open(activity_file, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == len(sample_activities)

    def test_save_user_activities_cleanup_old_activities(self, activity_tracker):
        """Test that old activities are cleaned up when saving."""
        # Create old activity (outside 30-day window)
        old_activity = ActivityEvent(
            user_id="test_user",
            action=ActivityType.CLICK,
            content_id="old_content",
            content_type="arxiv_paper",
            timestamp=datetime.now() - timedelta(days=35),
        )

        # Create recent activity
        recent_activity = ActivityEvent(
            user_id="test_user",
            action=ActivityType.CLICK,
            content_id="recent_content",
            content_type="news_article",
            timestamp=datetime.now() - timedelta(days=1),
        )

        # Save both activities
        activity_tracker.save_user_activities("test_user", [old_activity, recent_activity])

        # Load activities - should only have recent one
        loaded_activities = activity_tracker.load_user_activities("test_user")
        assert len(loaded_activities) == 1
        assert loaded_activities[0].content_id == "recent_content"

    def test_get_user_profile_new_user(self, activity_tracker):
        """Test getting profile for new user."""
        profile = activity_tracker.get_user_profile("new_user")

        assert profile is not None
        assert profile.user_id == "new_user"
        assert profile.total_activities == 0
        assert profile.top_sources == []
        assert profile.top_categories == []

    def test_get_user_profile_with_activities(self, activity_tracker):
        """Test getting profile for user with activities."""
        # Create activities with different sources and categories
        activities = [
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_1",
                content_type="arxiv_paper",
                source_category="machine_learning",
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="paper_2",
                content_type="arxiv_paper",
                source_category="machine_learning",
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.VIEW,
                content_id="news_1",
                content_type="news_article",
                source_category="technology",
            ),
        ]

        activity_tracker.save_user_activities("test_user", activities)
        profile = activity_tracker.get_user_profile("test_user")

        assert profile is not None
        assert profile.user_id == "test_user"
        assert profile.total_activities == 3
        assert "arxiv_paper" in profile.top_sources
        assert "machine_learning" in profile.top_categories

    def test_get_activity_summary(self, activity_tracker):
        """Test getting activity summary for user."""
        activities = [
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id="content_1",
                content_type="arxiv_paper",
                duration_seconds=60.0,
            ),
            ActivityEvent(
                user_id="test_user",
                action=ActivityType.VIEW,
                content_id="content_2",
                content_type="news_article",
                duration_seconds=30.0,
            ),
        ]

        activity_tracker.save_user_activities("test_user", activities)
        summary = activity_tracker.get_activity_summary("test_user", days=7)

        assert summary["total_activities"] == 2
        assert summary["unique_content_items"] == 2
        assert summary["activity_types"]["click"] == 1
        assert summary["activity_types"]["view"] == 1
        assert summary["content_types"]["arxiv_paper"] == 1
        assert summary["content_types"]["news_article"] == 1
        assert summary["avg_duration"] == 45.0

    def test_get_activity_summary_empty_user(self, activity_tracker):
        """Test getting activity summary for user with no activities."""
        summary = activity_tracker.get_activity_summary("empty_user", days=7)

        assert summary["total_activities"] == 0
        assert summary["unique_content_items"] == 0
        assert summary["activity_types"] == {}
        assert summary["content_types"] == {}
        assert summary["avg_duration"] == 0.0

    def test_cleanup_old_activities(self, activity_tracker):
        """Test cleanup of old activities."""
        # Create old activity
        old_activity = ActivityEvent(
            user_id="test_user",
            action=ActivityType.CLICK,
            content_id="old_content",
            content_type="arxiv_paper",
            timestamp=datetime.now() - timedelta(days=35),
        )

        # Save old activity
        activity_tracker.save_user_activities("test_user", [old_activity])

        # Verify it exists
        activities_before = activity_tracker.load_user_activities("test_user")
        assert len(activities_before) == 1

        # Run cleanup
        removed_count = activity_tracker.cleanup_old_activities("test_user")

        # Verify it was removed
        activities_after = activity_tracker.load_user_activities("test_user")
        assert len(activities_after) == 0
        assert removed_count == 1

    def test_cleanup_old_activities_all_users(self, activity_tracker):
        """Test cleanup of old activities for all users."""
        # Create activities for multiple users
        for user_id in ["user1", "user2"]:
            old_activity = ActivityEvent(
                user_id=user_id,
                action=ActivityType.CLICK,
                content_id="old_content",
                content_type="arxiv_paper",
                timestamp=datetime.now() - timedelta(days=35),
            )
            activity_tracker.save_user_activities(user_id, [old_activity])

        # Run cleanup for all users
        removed_count = activity_tracker.cleanup_old_activities()

        # Verify all old activities were removed
        assert removed_count == 2

        activities1 = activity_tracker.load_user_activities("user1")
        activities2 = activity_tracker.load_user_activities("user2")
        assert len(activities1) == 0
        assert len(activities2) == 0

    def test_save_and_load_user_profile(self, activity_tracker):
        """Test saving and loading user profile."""
        from src.recommendations.models import UserActivityProfile

        profile = UserActivityProfile(
            user_id="test_user",
            total_activities=100,
            top_sources=["arxiv_paper", "news_article"],
            top_categories=["machine_learning", "AI"],
            avg_session_duration=45.5,
        )

        success = activity_tracker.save_user_profile("test_user", profile)
        assert success is True

        loaded_profile = activity_tracker.get_user_profile("test_user")
        assert loaded_profile is not None
        assert loaded_profile.user_id == profile.user_id
        assert loaded_profile.total_activities == profile.total_activities
        assert loaded_profile.top_sources == profile.top_sources
        assert loaded_profile.top_categories == profile.top_categories
        assert loaded_profile.avg_session_duration == profile.avg_session_duration
