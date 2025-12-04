"""Background scheduler for daily recommendation generation.

This module provides utilities for scheduling and running daily
recommendation generation jobs without blocking dashboard performance.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from src.recommendations.activity_tracker import UserActivityTracker
from src.recommendations.recommendation_engine import RecommendationEngine
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RecommendationScheduler:
    """Scheduler for daily recommendation generation.

    Runs in background thread to avoid blocking dashboard operations.
    Maintains a schedule of user IDs that need recommendations updated.
    """

    def __init__(self):
        """Initialize the recommendation scheduler."""
        self.activity_tracker = UserActivityTracker()
        self.recommendation_engine = RecommendationEngine(self.activity_tracker)
        self._running = False
        self._scheduler_thread: threading.Thread | None = None
        self._user_queue: list[str] = []
        self._processed_users: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the background scheduler."""
        if self._running:
            logger.warning("Recommendation scheduler is already running")
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("Recommendation scheduler started")

    def stop(self) -> None:
        """Stop the background scheduler."""
        if not self._running:
            return

        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5.0)

        logger.info("Recommendation scheduler stopped")

    def schedule_user_recommendations(self, user_id: str) -> None:
        """Schedule recommendation generation for a user.

        Args:
            user_id: User identifier
        """
        with self._lock:
            if user_id not in self._user_queue:
                self._user_queue.append(user_id)
                logger.debug(f"Scheduled recommendations for user {user_id}")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop running in background thread."""
        logger.info("Recommendation scheduler loop started")

        while self._running:
            try:
                # Process user queue
                users_to_process = []

                with self._lock:
                    if self._user_queue:
                        users_to_process = self._user_queue.copy()
                        self._user_queue.clear()

                # Generate recommendations for queued users
                for user_id in users_to_process:
                    if not self._running:
                        break

                    try:
                        self._generate_recommendations_for_user(user_id)
                    except Exception as e:
                        logger.error(f"Failed to generate recommendations for user {user_id}: {e}")

                # Sleep for a short interval to avoid CPU spinning
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait longer on error

    def _generate_recommendations_for_user(self, user_id: str) -> bool:
        """Generate recommendations for a specific user.

        Args:
            user_id: User identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Generating recommendations for user {user_id}")

            # Check if user has sufficient activity
            profile = self.activity_tracker.get_user_profile(user_id)
            if not profile or profile.total_activities < 5:
                logger.debug(f"Insufficient activity for user {user_id}, skipping")
                return False

            # Generate recommendations
            recommendations = self.recommendation_engine.generate_recommendations(user_id)

            if recommendations:
                with self._lock:
                    self._processed_users[user_id] = datetime.now()

                logger.info(f"Generated {len(recommendations.recommendations)} recommendations for user {user_id}")
                return True
            else:
                logger.debug(f"No recommendations generated for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
            return False

    def get_scheduler_status(self) -> dict[str, any]:
        """Get the current status of the scheduler.

        Returns:
            Dictionary with scheduler status information
        """
        with self._lock:
            return {
                "running": self._running,
                "queue_size": len(self._user_queue),
                "queued_users": self._user_queue.copy(),
                "processed_users_count": len(self._processed_users),
                "last_processed": (dict(list(self._processed_users.items())[-10:]) if self._processed_users else {}),
            }

    def cleanup_old_processed_users(self, days: int = 7) -> None:
        """Clean up old processed user records.

        Args:
            days: Number of days to keep records
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with self._lock:
                old_users = [user_id for user_id, processed_date in self._processed_users.items() if processed_date < cutoff_date]

                for user_id in old_users:
                    del self._processed_users[user_id]

                if old_users:
                    logger.debug(f"Cleaned up {len(old_users)} old user records from scheduler")

        except Exception as e:
            logger.error(f"Failed to cleanup old processed users: {e}")

    def force_generate_for_all_active_users(self) -> int:
        """Force generate recommendations for all users with recent activity.

        Returns:
            Number of users scheduled for recommendation generation
        """
        try:
            # This is a simplified implementation
            # In a real system, you'd query your user database for active users
            active_users = ["default"]  # Single-user mode

            scheduled_count = 0
            for user_id in active_users:
                # Check if user has recent activity
                recent_activities = self.activity_tracker.load_user_activities(user_id, days=7)
                if recent_activities:
                    self.schedule_user_recommendations(user_id)
                    scheduled_count += 1

            logger.info(f"Scheduled recommendations for {scheduled_count} active users")
            return scheduled_count

        except Exception as e:
            logger.error(f"Failed to schedule recommendations for active users: {e}")
            return 0


# Global scheduler instance
_scheduler: RecommendationScheduler | None = None


def get_recommendation_scheduler() -> RecommendationScheduler:
    """Get the global recommendation scheduler instance.

    Returns:
        RecommendationScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = RecommendationScheduler()
    return _scheduler


def start_recommendation_scheduler() -> None:
    """Start the global recommendation scheduler."""
    scheduler = get_recommendation_scheduler()
    scheduler.start()


def stop_recommendation_scheduler() -> None:
    """Stop the global recommendation scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


def schedule_user_recommendations(user_id: str) -> None:
    """Schedule recommendation generation for a user.

    Args:
        user_id: User identifier
    """
    scheduler = get_recommendation_scheduler()
    scheduler.schedule_user_recommendations(user_id)


def get_scheduler_status() -> dict[str, any]:
    """Get the current status of the recommendation scheduler.

    Returns:
        Dictionary with scheduler status information
    """
    scheduler = get_recommendation_scheduler()
    return scheduler.get_scheduler_status()
