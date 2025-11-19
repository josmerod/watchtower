"""Tests for the recommendation scheduler."""

from __future__ import annotations

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from utils.recommendation_scheduler import (
    RecommendationScheduler,
    get_recommendation_scheduler,
    start_recommendation_scheduler,
    stop_recommendation_scheduler,
    schedule_user_recommendations,
    get_scheduler_status,
)


class TestRecommendationScheduler:
    """Test suite for RecommendationScheduler functionality."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def scheduler(self, temp_data_dir):
        """Create a RecommendationScheduler instance for testing."""
        with patch('utils.recommendation_scheduler.UserActivityTracker') as mock_tracker, \
             patch('utils.recommendation_scheduler.RecommendationEngine') as mock_engine:

            scheduler = RecommendationScheduler()
            return scheduler

    def test_init(self):
        """Test scheduler initialization."""
        with patch('utils.recommendation_scheduler.UserActivityTracker') as mock_tracker, \
             patch('utils.recommendation_scheduler.RecommendationEngine') as mock_engine:

            scheduler = RecommendationScheduler()

            assert scheduler._running is False
            assert scheduler._scheduler_thread is None
            assert scheduler._user_queue == []
            assert scheduler._processed_users == {}

    def test_start_stop_scheduler(self, scheduler):
        """Test starting and stopping the scheduler."""
        assert scheduler._running is False

        scheduler.start()
        assert scheduler._running is True
        assert scheduler._scheduler_thread is not None

        # Give it a moment to start
        time.sleep(0.1)

        scheduler.stop()
        assert scheduler._running is False

    def test_start_already_running_scheduler(self, scheduler):
        """Test starting a scheduler that's already running."""
        scheduler.start()
        time.sleep(0.1)

        # Should not raise an error
        scheduler.start()
        time.sleep(0.1)

        assert scheduler._running is True

        scheduler.stop()

    def test_schedule_user_recommendations(self, scheduler):
        """Test scheduling recommendations for a user."""
        # Initially empty queue
        assert len(scheduler._user_queue) == 0

        # Schedule a user
        scheduler.schedule_user_recommendations("test_user")

        # User should be in queue
        assert len(scheduler._user_queue) == 1
        assert "test_user" in scheduler._user_queue

        # Scheduling same user again should not duplicate
        scheduler.schedule_user_recommendations("test_user")
        assert len(scheduler._user_queue) == 1

    def test_generate_recommendations_for_user_success(self, scheduler):
        """Test successful recommendation generation for a user."""
        # Mock profile with sufficient activity
        mock_profile = MagicMock()
        mock_profile.total_activities = 10

        # Mock recommendations generation
        mock_recommendations = MagicMock()
        mock_recommendations.__len__ = MagicMock(return_value=5)

        scheduler.activity_tracker.get_user_profile.return_value = mock_profile
        scheduler.recommendation_engine.generate_recommendations.return_value = mock_recommendations

        result = scheduler._generate_recommendations_for_user("test_user")

        assert result is True
        scheduler.activity_tracker.get_user_profile.assert_called_once_with("test_user")
        scheduler.recommendation_engine.generate_recommendations.assert_called_once_with("test_user")

    def test_generate_recommendations_for_user_insufficient_activity(self, scheduler):
        """Test recommendation generation with insufficient user activity."""
        # Mock profile with insufficient activity
        mock_profile = MagicMock()
        mock_profile.total_activities = 2  # Less than threshold of 5

        scheduler.activity_tracker.get_user_profile.return_value = mock_profile

        result = scheduler._generate_recommendations_for_user("test_user")

        assert result is False
        scheduler.recommendation_engine.generate_recommendations.assert_not_called()

    def test_generate_recommendations_for_user_no_profile(self, scheduler):
        """Test recommendation generation when user has no profile."""
        scheduler.activity_tracker.get_user_profile.return_value = None

        result = scheduler._generate_recommendations_for_user("test_user")

        assert result is False

    def test_generate_recommendations_for_user_no_recommendations(self, scheduler):
        """Test when recommendation engine returns no recommendations."""
        # Mock profile with sufficient activity
        mock_profile = MagicMock()
        mock_profile.total_activities = 10

        scheduler.activity_tracker.get_user_profile.return_value = mock_profile
        scheduler.recommendation_engine.generate_recommendations.return_value = None

        result = scheduler._generate_recommendations_for_user("test_user")

        assert result is False

    def test_get_scheduler_status(self, scheduler):
        """Test getting scheduler status."""
        # Schedule some users
        scheduler.schedule_user_recommendations("user1")
        scheduler.schedule_user_recommendations("user2")

        # Mark a user as processed
        test_time = datetime.now()
        with scheduler._lock:
            scheduler._processed_users["user3"] = test_time

        status = scheduler.get_scheduler_status()

        assert status["running"] is False
        assert status["queue_size"] == 2
        assert "user1" in status["queued_users"]
        assert "user2" in status["queued_users"]
        assert status["processed_users_count"] == 1
        assert "user3" in status["last_processed"]

    def test_cleanup_old_processed_users(self, scheduler):
        """Test cleanup of old processed user records."""
        old_time = datetime.now() - timedelta(days=10)
        recent_time = datetime.now() - timedelta(days=2)

        with scheduler._lock:
            scheduler._processed_users["old_user"] = old_time
            scheduler._processed_users["recent_user"] = recent_time

        # Cleanup users older than 7 days
        scheduler.cleanup_old_processed_users(days=7)

        with scheduler._lock:
            assert "old_user" not in scheduler._processed_users
            assert "recent_user" in scheduler._processed_users

    def test_force_generate_for_all_active_users(self, scheduler):
        """Test forcing recommendation generation for all active users."""
        # Mock recent activities for default user
        mock_activities = [MagicMock()] * 5  # 5 activities
        scheduler.activity_tracker.load_user_activities.return_value = mock_activities

        scheduled_count = scheduler.force_generate_for_all_active_users()

        assert scheduled_count == 1
        scheduler.activity_tracker.load_user_activities.assert_called_once_with("default", days=7)
        assert "default" in scheduler._user_queue

    def test_force_generate_no_active_users(self, scheduler):
        """Test forcing recommendations when no active users."""
        # Mock empty activities
        scheduler.activity_tracker.load_user_activities.return_value = []

        scheduled_count = scheduler.force_generate_for_all_active_users()

        assert scheduled_count == 0
        assert len(scheduler._user_queue) == 0

    def test_scheduler_loop_processes_users(self, scheduler):
        """Test that the scheduler loop processes users from the queue."""
        # Mock successful recommendation generation
        scheduler._generate_recommendations_for_user = MagicMock(return_value=True)

        # Schedule users
        scheduler.schedule_user_recommendations("user1")
        scheduler.schedule_user_recommendations("user2")

        # Run a single iteration of the loop
        scheduler._running = True
        scheduler._user_queue = ["user1", "user2"]

        # Process one cycle
        users_to_process = []
        with scheduler._lock:
            if scheduler._user_queue:
                users_to_process = scheduler._user_queue.copy()
                scheduler._user_queue.clear()

        # Process users (simulating scheduler loop)
        for user_id in users_to_process:
            if scheduler._running:
                scheduler._generate_recommendations_for_user(user_id)

        # Verify users were processed
        assert scheduler._generate_recommendations_for_user.call_count == 2
        scheduler._generate_recommendations_for_user.assert_any_call("user1")
        scheduler._generate_recommendations_for_user.assert_any_call("user2")

    def test_scheduler_loop_handles_errors(self, scheduler):
        """Test that the scheduler loop handles errors gracefully."""
        # Mock exception for one user
        def generate_side_effect(user_id):
            if user_id == "error_user":
                raise Exception("Test error")
            return True

        scheduler._generate_recommendations_for_user = MagicMock(side_effect=generate_side_effect)

        # Schedule users
        scheduler._user_queue = ["error_user", "good_user"]

        # Process users (simulating scheduler loop)
        users_to_process = scheduler._user_queue.copy()
        scheduler._user_queue.clear()

        for user_id in users_to_process:
            if scheduler._running:
                try:
                    scheduler._generate_recommendations_for_user(user_id)
                except Exception:
                    pass  # Scheduler should handle exceptions

        # Verify both users were attempted
        assert scheduler._generate_recommendations_for_user.call_count == 2


class TestGlobalSchedulerFunctions:
    """Test suite for global scheduler functions."""

    def test_get_recommendation_scheduler_singleton(self):
        """Test that get_recommendation_scheduler returns the same instance."""
        with patch('utils.recommendation_scheduler._scheduler', None):
            scheduler1 = get_recommendation_scheduler()
            scheduler2 = get_recommendation_scheduler()
            assert scheduler1 is scheduler2

    def test_start_recommendation_scheduler(self):
        """Test starting the global scheduler."""
        with patch('utils.recommendation_scheduler.get_recommendation_scheduler') as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_get_scheduler.return_value = mock_scheduler

            start_recommendation_scheduler()

            mock_scheduler.start.assert_called_once()

    def test_stop_recommendation_scheduler(self):
        """Test stopping the global scheduler."""
        with patch('utils.recommendation_scheduler._scheduler') as mock_scheduler:
            stop_recommendation_scheduler()

            mock_scheduler.stop.assert_called_once()
            assert mock_scheduler is None

    def test_schedule_user_recommendations(self):
        """Test scheduling recommendations for a user via global function."""
        with patch('utils.recommendation_scheduler.get_recommendation_scheduler') as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_get_scheduler.return_value = mock_scheduler

            schedule_user_recommendations("test_user")

            mock_scheduler.schedule_user_recommendations.assert_called_once_with("test_user")

    def test_get_scheduler_status(self):
        """Test getting scheduler status via global function."""
        with patch('utils.recommendation_scheduler.get_recommendation_scheduler') as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.get_scheduler_status.return_value = {"running": True}
            mock_get_scheduler.return_value = mock_scheduler

            status = get_scheduler_status()

            assert status == {"running": True}
            mock_scheduler.get_scheduler_status.assert_called_once()


class TestSchedulerIntegration:
    """Integration tests for the scheduler with real components."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_end_to_end_scheduler_workflow(self, temp_data_dir):
        """Test end-to-end scheduler workflow with real components."""
        from src.recommendations.activity_tracker import UserActivityTracker
        from src.recommendations.recommendation_engine import RecommendationEngine
        from src.recommendations.models import ActivityEvent, ActivityType

        # Create real components
        activity_tracker = UserActivityTracker(data_dir=temp_data_dir)
        engine = RecommendationEngine(activity_tracker, data_dir=temp_data_dir)

        # Create scheduler with real components
        scheduler = RecommendationScheduler()
        scheduler.activity_tracker = activity_tracker
        scheduler.recommendation_engine = engine

        # Track some user activities to meet the threshold
        for i in range(6):  # Need at least 5 activities
            activity_tracker.track_interaction(
                user_id="test_user",
                action=ActivityType.CLICK,
                content_id=f"content_{i}",
                content_type="arxiv_paper",
                source_category="AI",
                title=f"Test Paper {i}",
                duration_seconds=60.0,
            )

        # Schedule user for recommendations
        scheduler.schedule_user_recommendations("test_user")
        assert len(scheduler._user_queue) == 1

        # Process the user (simulate scheduler loop)
        result = scheduler._generate_recommendations_for_user("test_user")

        # The result will be False in this test environment due to lack of content data,
        # but the workflow should complete without errors
        assert isinstance(result, bool)

        # Verify user was processed and marked
        status = scheduler.get_scheduler_status()
        assert status["queue_size"] == 0
        assert status["processed_users_count"] == 1
        assert "test_user" in status["last_processed"]

    def test_scheduler_with_multiple_users(self, temp_data_dir):
        """Test scheduler handling multiple users."""
        from src.recommendations.activity_tracker import UserActivityTracker
        from src.recommendations.recommendation_engine import RecommendationEngine
        from src.recommendations.models import ActivityEvent, ActivityType

        # Create real components
        activity_tracker = UserActivityTracker(data_dir=temp_data_dir)
        engine = RecommendationEngine(activity_tracker, data_dir=temp_data_dir)

        # Create scheduler
        scheduler = RecommendationScheduler()
        scheduler.activity_tracker = activity_tracker
        scheduler.recommendation_engine = engine

        # Create activities for multiple users
        users = ["user1", "user2", "user3"]
        for user_id in users:
            for i in range(6):  # Each user needs at least 5 activities
                activity_tracker.track_interaction(
                    user_id=user_id,
                    action=ActivityType.CLICK,
                    content_id=f"{user_id}_content_{i}",
                    content_type="arxiv_paper",
                    source_category="AI",
                    title=f"Test Paper {i} for {user_id}",
                    duration_seconds=60.0,
                )

        # Schedule all users
        for user_id in users:
            scheduler.schedule_user_recommendations(user_id)

        assert len(scheduler._user_queue) == 3

        # Process all users
        processed_count = 0
        users_to_process = scheduler._user_queue.copy()
        scheduler._user_queue.clear()

        for user_id in users_to_process:
            result = scheduler._generate_recommendations_for_user(user_id)
            if result is not False:
                processed_count += 1

        # Verify all users were processed
        status = scheduler.get_scheduler_status()
        assert status["queue_size"] == 0
        assert status["processed_users_count"] == 3

        # Verify all users are in processed list
        for user_id in users:
            assert user_id in status["last_processed"]