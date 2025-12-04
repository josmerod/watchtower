"""User Profile Manager for CRUD operations on user profiles."""

import json
from pathlib import Path

from src.config.settings import get_settings
from src.models.user_profile_model import LearningGoal, SkillLevel, UserProfile
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger


class UserProfileManager:
    """Manages user profile storage and retrieval."""

    def __init__(self):
        """Initialize the user profile manager."""
        self.logger = get_logger("UserProfileManager")
        self.settings = get_settings()

        # Setup profile storage directory
        self.project_root = Path(get_project_root())
        self.profiles_dir = self.project_root / "data" / "user_profiles"
        ensure_directories([str(self.profiles_dir)])

        self.logger.info(f"UserProfileManager initialized with storage: {self.profiles_dir}")

    def load_profile(self, user_id: str) -> UserProfile | None:
        """Load a user profile from storage.

        Args:
            user_id: User identifier

        Returns:
            UserProfile if found, None otherwise
        """
        profile_file = self.profiles_dir / user_id / "profile.json"

        if not profile_file.exists():
            self.logger.debug(f"No profile found for user {user_id}")
            return None

        try:
            with open(profile_file, encoding="utf-8") as f:
                profile_data = json.load(f)

            profile = UserProfile(**profile_data)
            self.logger.info(f"Loaded profile for user {user_id}")
            return profile

        except Exception as e:
            self.logger.error(f"Error loading profile for user {user_id}: {e}")
            return None

    def save_profile(self, profile: UserProfile) -> bool:
        """Save a user profile to storage.

        Args:
            profile: UserProfile to save

        Returns:
            True if successful, False otherwise
        """
        user_dir = self.profiles_dir / profile.user_id
        ensure_directories([str(user_dir)])

        profile_file = user_dir / "profile.json"

        try:
            profile_data = profile.model_dump(mode="json")

            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Saved profile for user {profile.user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving profile for user {profile.user_id}: {e}")
            return False

    def create_default_profile(self, user_id: str, username: str = "") -> UserProfile:
        """Create a default user profile.

        Args:
            user_id: User identifier
            username: Optional display name

        Returns:
            New UserProfile with defaults
        """
        profile = UserProfile(
            user_id=user_id,
            username=username or user_id,
            preferred_domains=[],
            skill_level=SkillLevel.INTERMEDIATE,
        )

        self.save_profile(profile)
        self.logger.info(f"Created default profile for user {user_id}")
        return profile

    def update_preferences(
        self,
        user_id: str,
        preferred_domains: list | None = None,
        skill_level: SkillLevel | None = None,
    ) -> bool:
        """Update user preferences.

        Args:
            user_id: User identifier
            preferred_domains: Optional new domain preferences
            skill_level: Optional new skill level

        Returns:
            True if successful, False otherwise
        """
        profile = self.load_profile(user_id)

        if not profile:
            self.logger.warning(f"Cannot update preferences: user {user_id} not found")
            return False

        if preferred_domains is not None:
            profile.preferred_domains = preferred_domains

        if skill_level is not None:
            profile.skill_level = skill_level

        return self.save_profile(profile)

    def mark_paper_completed(self, user_id: str, paper_id: str) -> bool:
        """Mark a paper as completed for a user.

        Args:
            user_id: User identifier
            paper_id: Paper ID to mark as completed

        Returns:
            True if successful, False otherwise
        """
        profile = self.load_profile(user_id)

        if not profile:
            self.logger.warning(f"Cannot mark paper completed: user {user_id} not found")
            return False

        if paper_id not in profile.completed_papers:
            profile.completed_papers.append(paper_id)
            self.logger.info(f"User {user_id} completed paper {paper_id}")

        return self.save_profile(profile)

    def bookmark_paper(self, user_id: str, paper_id: str) -> bool:
        """Bookmark a paper for later reading.

        Args:
            user_id: User identifier
            paper_id: Paper ID to bookmark

        Returns:
            True if successful, False otherwise
        """
        profile = self.load_profile(user_id)

        if not profile:
            self.logger.warning(f"Cannot bookmark paper: user {user_id} not found")
            return False

        if paper_id not in profile.bookmarked_papers:
            profile.bookmarked_papers.append(paper_id)
            self.logger.info(f"User {user_id} bookmarked paper {paper_id}")

        return self.save_profile(profile)

    def add_learning_goal(self, user_id: str, goal: LearningGoal) -> bool:
        """Add a learning goal to user profile.

        Args:
            user_id: User identifier
            goal: LearningGoal to add

        Returns:
            True if successful, False otherwise
        """
        profile = self.load_profile(user_id)

        if not profile:
            self.logger.warning(f"Cannot add learning goal: user {user_id} not found")
            return False

        profile.learning_goals.append(goal)
        self.logger.info(f"Added learning goal '{goal.goal_name}' for user {user_id}")

        return self.save_profile(profile)

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create a new one.

        Args:
            user_id: User identifier

        Returns:
            UserProfile (existing or new)
        """
        profile = self.load_profile(user_id)

        if profile is None:
            profile = self.create_default_profile(user_id)

        return profile
