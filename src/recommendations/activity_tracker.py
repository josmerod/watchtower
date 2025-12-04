"""User activity tracking service for the recommendation system.

This module provides the UserActivityTracker class that monitors and logs
user interactions across the dashboard for recommendation generation.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.recommendations.models import ActivityEvent, ActivityType, UserActivityProfile
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UserActivityTracker:
    """Service for tracking and storing user activity data.

    Follows BaseETL patterns for JSON file storage and error handling.
    Maintains a 30-day rolling window of activity data for each user.
    """

    def __init__(self, data_dir: Path | None = None):
        """Initialize the activity tracker.

        Args:
            data_dir: Directory to store activity data. Defaults to project data/users/
        """
        self.settings = get_settings()
        self.data_dir = data_dir or Path(self.settings.project_root) / "data" / "users"
        self.activity_window_days = 30

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_user_activity_file(self, user_id: str) -> Path:
        """Get the path to a user's activity log file."""
        user_dir = self.data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "activity_log.json"

    def get_user_profile_file(self, user_id: str) -> Path:
        """Get the path to a user's profile file."""
        user_dir = self.data_dir / user_id
        return user_dir / "profile.json"

    def track_interaction(
        self,
        user_id: str,
        action: ActivityType,
        content_id: str,
        content_type: str,
        metadata: dict[str, Any] | None = None,
        duration_seconds: float | None = None,
        source_category: str | None = None,
        title: str | None = None,
    ) -> bool:
        """Track a user interaction event.

        Args:
            user_id: Unique identifier for the user
            action: Type of activity performed
            content_id: Identifier of the content interacted with
            content_type: Type of content (e.g., 'arxiv_paper', 'news_article')
            metadata: Additional context about the activity
            duration_seconds: Time spent on content if applicable
            source_category: Category of the content source
            title: Title of the content for similarity matching

        Returns:
            True if tracking succeeded, False otherwise
        """
        try:
            # Create activity event
            event = ActivityEvent(
                user_id=user_id,
                action=action,
                content_id=content_id,
                content_type=content_type,
                metadata=metadata or {},
                duration_seconds=duration_seconds,
                source_category=source_category,
                title=title,
            )

            # Load existing activities
            activities = self.load_user_activities(user_id)

            # Add new event
            activities.append(event)

            # Clean old activities (maintain 30-day window)
            cutoff_date = datetime.now() - timedelta(days=self.activity_window_days)
            activities = [a for a in activities if a.timestamp > cutoff_date]

            # Save updated activities
            self.save_user_activities(user_id, activities)

            logger.debug(f"Tracked {action.value} activity for user {user_id}: {content_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to track activity for user {user_id}: {e}")
            return False

    def load_user_activities(self, user_id: str, days: int | None = None) -> list[ActivityEvent]:
        """Load activity events for a user.

        Args:
            user_id: User identifier
            days: Number of days to load (None for all available)

        Returns:
            List of activity events
        """
        try:
            activity_file = self.get_user_activity_file(user_id)

            if not activity_file.exists():
                return []

            with open(activity_file, encoding="utf-8") as f:
                data = json.load(f)

            # Parse JSON to ActivityEvent objects
            activities = []
            cutoff_date = None

            if days:
                cutoff_date = datetime.now() - timedelta(days=days)

            for event_data in data:
                try:
                    # Parse timestamp
                    if isinstance(event_data.get("timestamp"), str):
                        event_data["timestamp"] = datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00"))

                    # Parse activity type
                    if isinstance(event_data.get("action"), str):
                        event_data["action"] = ActivityType(event_data["action"])

                    # Apply date filter if specified
                    if cutoff_date and event_data["timestamp"] < cutoff_date:
                        continue

                    activities.append(ActivityEvent(**event_data))

                except Exception as e:
                    logger.warning(f"Failed to parse activity event: {e}")
                    continue

            return activities

        except Exception as e:
            logger.error(f"Failed to load activities for user {user_id}: {e}")
            return []

    def save_user_activities(self, user_id: str, activities: list[ActivityEvent]) -> bool:
        """Save activity events for a user.

        Args:
            user_id: User identifier
            activities: List of activity events to save

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            activity_file = self.get_user_activity_file(user_id)

            # Convert to JSON-serializable format
            data = []
            for activity in activities:
                event_data = activity.dict()
                # Convert datetime to ISO string
                if isinstance(event_data.get("timestamp"), datetime):
                    event_data["timestamp"] = activity.timestamp.isoformat()
                data.append(event_data)

            # Sort by timestamp (newest first) for easier analysis
            data.sort(key=lambda x: x["timestamp"], reverse=True)

            with open(activity_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(activities)} activities for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save activities for user {user_id}: {e}")
            return False

    def get_user_profile(self, user_id: str) -> UserActivityProfile | None:
        """Load or generate a user's activity profile.

        Args:
            user_id: User identifier

        Returns:
            User activity profile or None if failed
        """
        try:
            profile_file = self.get_user_profile_file(user_id)

            # Load existing profile if available
            if profile_file.exists():
                try:
                    with open(profile_file, encoding="utf-8") as f:
                        data = json.load(f)

                    # Parse last_updated timestamp
                    if isinstance(data.get("last_updated"), str):
                        data["last_updated"] = datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))

                    return UserActivityProfile(**data)

                except Exception as e:
                    logger.warning(f"Failed to parse existing profile for {user_id}: {e}")

            # Generate new profile from activities
            activities = self.load_user_activities(user_id, days=self.activity_window_days)
            profile = UserActivityProfile(user_id=user_id)
            profile.update_from_activities(activities)

            # Save generated profile
            self.save_user_profile(user_id, profile)

            return profile

        except Exception as e:
            logger.error(f"Failed to get profile for user {user_id}: {e}")
            return None

    def save_user_profile(self, user_id: str, profile: UserActivityProfile) -> bool:
        """Save a user's activity profile.

        Args:
            user_id: User identifier
            profile: Profile to save

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            profile_file = self.get_user_profile_file(user_id)

            # Convert to JSON-serializable format
            data = profile.dict()
            if isinstance(data.get("last_updated"), datetime):
                data["last_updated"] = profile.last_updated.isoformat()

            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved profile for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save profile for user {user_id}: {e}")
            return False

    def get_activity_summary(self, user_id: str, days: int = 7) -> dict[str, Any]:
        """Get a summary of user activity for the specified period.

        Args:
            user_id: User identifier
            days: Number of days to analyze

        Returns:
            Dictionary with activity summary statistics
        """
        try:
            activities = self.load_user_activities(user_id, days=days)

            if not activities:
                return {
                    "total_activities": 0,
                    "unique_content_items": 0,
                    "activity_types": {},
                    "content_types": {},
                    "avg_duration": 0.0,
                }

            # Calculate statistics
            unique_content = {a.content_id for a in activities}
            activity_types = {}
            content_types = {}
            durations = [a.duration_seconds for a in activities if a.duration_seconds]

            for activity in activities:
                # Count activity types
                activity_type = activity.action.value
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1

                # Count content types
                content_type = activity.content_type
                content_types[content_type] = content_types.get(content_type, 0) + 1

            summary = {
                "total_activities": len(activities),
                "unique_content_items": len(unique_content),
                "activity_types": activity_types,
                "content_types": content_types,
                "avg_duration": sum(durations) / len(durations) if durations else 0.0,
                "period_days": days,
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to get activity summary for user {user_id}: {e}")
            return {}

    def cleanup_old_activities(self, user_id: str | None = None) -> int:
        """Clean up activities older than the retention window.

        Args:
            user_id: Specific user to clean (None for all users)

        Returns:
            Number of activities removed
        """
        try:
            total_removed = 0
            cutoff_date = datetime.now() - timedelta(days=self.activity_window_days)

            if user_id:
                users = [user_id]
            else:
                # Get all user directories
                users = [d.name for d in self.data_dir.iterdir() if d.is_dir()]

            for uid in users:
                activities = self.load_user_activities(uid)
                original_count = len(activities)

                # Remove old activities
                activities = [a for a in activities if a.timestamp > cutoff_date]

                if len(activities) != original_count:
                    self.save_user_activities(uid, activities)
                    total_removed += original_count - len(activities)

                    logger.debug(f"Cleaned {original_count - len(activities)} old activities for user {uid}")

            logger.info(f"Cleaned up {total_removed} old activities total")
            return total_removed

        except Exception as e:
            logger.error(f"Failed to cleanup old activities: {e}")
            return 0
