"""Recommendation engine for personalized content discovery.

This module provides the RecommendationEngine class that generates
content recommendations based on user activity patterns using simple
heuristic algorithms.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.recommendations.activity_tracker import UserActivityTracker
from src.recommendations.models import (
    ActivityEvent,
    ActivityType,
    Recommendation,
    RecommendationType,
    UserActivityProfile,
    UserRecommendations,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RecommendationEngine:
    """Engine for generating personalized content recommendations.

    Uses simple heuristic algorithms based on user activity patterns:
    1. Top 5 sources by click count
    2. Top 3 categories by engagement
    3. Content similar to recently clicked items (title matching)
    """

    def __init__(
        self,
        activity_tracker: UserActivityTracker | None = None,
        data_dir: Path | None = None,
    ):
        """Initialize the recommendation engine.

        Args:
            activity_tracker: Activity tracker instance (creates one if None)
            data_dir: Directory to store recommendation data
        """
        self.settings = get_settings()
        self.activity_tracker = activity_tracker or UserActivityTracker(data_dir)
        self.data_dir = data_dir or Path(self.settings.project_root) / "data" / "users"
        self.recommendation_window_days = 7  # Recommendations stay fresh for 7 days

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_user_recommendations_file(self, user_id: str) -> Path:
        """Get the path to a user's recommendations file."""
        user_dir = self.data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "recommendations.json"

    def generate_recommendations(self, user_id: str) -> UserRecommendations | None:
        """Generate recommendations for a user based on their activity.

        Args:
            user_id: User identifier

        Returns:
            User recommendations object or None if failed
        """
        try:
            logger.info(f"Generating recommendations for user {user_id}")

            # Load user activity profile
            profile = self.activity_tracker.get_user_profile(user_id)
            if not profile or profile.total_activities < 5:
                logger.info(f"Insufficient activity data for user {user_id}")
                return None

            # Load recent activities (last 30 days)
            activities = self.activity_tracker.load_user_activities(user_id, days=30)
            if not activities:
                logger.info(f"No recent activities found for user {user_id}")
                return None

            # Create recommendations container
            recommendations = UserRecommendations(
                user_id=user_id,
                activity_window_days=30,
                total_activities_analyzed=len(activities),
            )

            # Generate different types of recommendations
            self._generate_top_source_recommendations(user_id, profile, recommendations)
            self._generate_top_category_recommendations(user_id, profile, recommendations)
            self._generate_similar_content_recommendations(user_id, activities, recommendations)

            # Sort by confidence score and limit to top 20
            recommendations.recommendations.sort(key=lambda r: r.score, reverse=True)
            recommendations.recommendations = recommendations.recommendations[:20]

            # Save recommendations
            self.save_user_recommendations(user_id, recommendations)

            logger.info(f"Generated {len(recommendations.recommendations)} recommendations for user {user_id}")
            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
            return None

    def _generate_top_source_recommendations(
        self,
        user_id: str,
        profile: UserActivityProfile,
        recommendations: UserRecommendations,
    ) -> None:
        """Generate recommendations based on user's top sources.

        Args:
            user_id: User identifier
            profile: User activity profile
            recommendations: Container to add recommendations to
        """
        try:
            # Get top 5 sources from user profile
            top_sources = profile.top_sources[:5]

            for i, source_type in enumerate(top_sources):
                # Find recent content from this source type
                recent_content = self._find_recent_content_by_type(source_type, limit=3)

                for content in recent_content:
                    # Generate recommendation with decreasing confidence based on source rank
                    confidence = 0.8 - (i * 0.1)  # 0.8, 0.7, 0.6, 0.5, 0.4

                    recommendation = Recommendation(
                        id=self._generate_recommendation_id(user_id, "top_source", content["id"]),
                        user_id=user_id,
                        type=RecommendationType.TOP_SOURCE,
                        content_id=content["id"],
                        content_type=content["type"],
                        title=content["title"],
                        description=f"Because you frequently read {source_type} content",
                        score=confidence,
                        metadata={
                            "source_rank": i + 1,
                            "source_type": source_type,
                            "recent_count": content.get("recent_count", 0),
                        },
                    )

                    recommendations.add_recommendation(recommendation)

            logger.debug(f"Generated {len(top_sources)} top source recommendations for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to generate top source recommendations: {e}")

    def _generate_top_category_recommendations(
        self,
        user_id: str,
        profile: UserActivityProfile,
        recommendations: UserRecommendations,
    ) -> None:
        """Generate recommendations based on user's top categories.

        Args:
            user_id: User identifier
            profile: User activity profile
            recommendations: Container to add recommendations to
        """
        try:
            # Get top 3 categories from user profile
            top_categories = profile.top_categories[:3]

            for i, category in enumerate(top_categories):
                # Find recent content in this category
                recent_content = self._find_recent_content_by_category(category, limit=2)

                for content in recent_content:
                    # Generate recommendation with confidence based on category rank
                    confidence = 0.7 - (i * 0.15)  # 0.7, 0.55, 0.4

                    recommendation = Recommendation(
                        id=self._generate_recommendation_id(user_id, "top_category", content["id"]),
                        user_id=user_id,
                        type=RecommendationType.TOP_CATEGORY,
                        content_id=content["id"],
                        content_type=content["type"],
                        title=content["title"],
                        description=f"Popular in {category} - a category you engage with frequently",
                        score=confidence,
                        metadata={
                            "category_rank": i + 1,
                            "category": category,
                            "trending_score": content.get("trending_score", 0.0),
                        },
                    )

                    recommendations.add_recommendation(recommendation)

            logger.debug(f"Generated category recommendations for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to generate category recommendations: {e}")

    def _generate_similar_content_recommendations(
        self,
        user_id: str,
        activities: list[ActivityEvent],
        recommendations: UserRecommendations,
    ) -> None:
        """Generate recommendations based on content similarity to recently viewed items.

        Args:
            user_id: User identifier
            activities: User's recent activities
            recommendations: Container to add recommendations to
        """
        try:
            # Get recently clicked/viewed content (last 14 days)
            recent_interactions = [a for a in activities if a.action in [ActivityType.CLICK, ActivityType.VIEW] and a.timestamp > datetime.now() - timedelta(days=14) and a.title][
                :10
            ]  # Limit to 10 recent items

            for _i, activity in enumerate(recent_interactions):
                # Find similar content based on title
                similar_content = self._find_similar_content(activity.title, activity.content_type)

                for content in similar_content:
                    # Skip if it's the same content the user already interacted with
                    if content["id"] == activity.content_id:
                        continue

                    # Calculate similarity score
                    similarity = self._calculate_title_similarity(activity.title, content["title"])
                    confidence = similarity * 0.6  # Scale down for similarity-based recommendations

                    if confidence > 0.3:  # Only include if reasonably similar
                        recommendation = Recommendation(
                            id=self._generate_recommendation_id(user_id, "similar", content["id"]),
                            user_id=user_id,
                            type=RecommendationType.SIMILAR_CONTENT,
                            content_id=content["id"],
                            content_type=content["type"],
                            title=content["title"],
                            description=f'Similar to "{activity.title}" which you recently viewed',
                            score=confidence,
                            metadata={
                                "similarity_score": similarity,
                                "source_title": activity.title,
                                "source_content_id": activity.content_id,
                            },
                        )

                        recommendations.add_recommendation(recommendation)

            logger.debug(f"Generated similar content recommendations for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to generate similar content recommendations: {e}")

    def _find_recent_content_by_type(self, content_type: str, limit: int = 5) -> list[dict[str, Any]]:
        """Find recent content of a specific type.

        Args:
            content_type: Type of content to search for
            limit: Maximum number of items to return

        Returns:
            List of content items with metadata
        """
        # This is a simplified implementation - in a real system, you'd query your content database
        # For now, we'll simulate by looking at available data files

        content_items = []
        data_dir = Path(self.settings.project_root) / "data"

        # Try different data sources based on content type
        if content_type == "arxiv_paper":
            arxiv_file = data_dir / "arxiv" / "latest.json"
            if arxiv_file.exists():
                try:
                    with open(arxiv_file, encoding="utf-8") as f:
                        data = json.load(f)
                        for item in data[:limit]:
                            content_items.append(
                                {
                                    "id": item.get("id", ""),
                                    "title": item.get("title", ""),
                                    "type": "arxiv_paper",
                                    "recent_count": 1,  # Placeholder
                                }
                            )
                except Exception as e:
                    logger.warning(f"Failed to load ArXiv data: {e}")

        elif content_type == "news_article":
            # Try multiple news sources
            news_dirs = ["news", "hackernews", "reddit"]
            for news_dir in news_dirs:
                news_file = data_dir / news_dir / "latest.json"
                if news_file.exists():
                    try:
                        with open(news_file, encoding="utf-8") as f:
                            data = json.load(f)
                            for item in data[:limit]:
                                content_items.append(
                                    {
                                        "id": item.get("id", ""),
                                        "title": item.get("title", ""),
                                        "type": "news_article",
                                        "recent_count": 1,
                                    }
                                )
                            break  # Use first successful source
                    except Exception as e:
                        logger.warning(f"Failed to load {news_dir} data: {e}")

        return content_items[:limit]

    def _find_recent_content_by_category(self, category: str, limit: int = 5) -> list[dict[str, Any]]:
        """Find recent content in a specific category.

        Args:
            category: Category to search for
            limit: Maximum number of items to return

        Returns:
            List of content items with metadata
        """
        # Simplified implementation - map categories to content types
        category_mapping = {
            "research": "arxiv_paper",
            "technology": "news_article",
            "ai": "arxiv_paper",
            "machine learning": "arxiv_paper",
            "news": "news_article",
            "deals": "game_deal",
            "gaming": "game_deal",
        }

        content_type = category_mapping.get(category.lower(), "news_article")
        return self._find_recent_content_by_type(content_type, limit)

    def _find_similar_content(self, title: str, content_type: str, limit: int = 3) -> list[dict[str, Any]]:
        """Find content similar to the given title.

        Args:
            title: Title to find similar content for
            content_type: Type of the original content
            limit: Maximum number of items to return

        Returns:
            List of similar content items
        """
        # Find recent content of the same type
        all_content = self._find_recent_content_by_type(content_type, limit=20)

        # Calculate similarity scores and sort
        similar_content = []
        for content in all_content:
            similarity = self._calculate_title_similarity(title, content["title"])
            if similarity > 0.3:  # Only include reasonably similar items
                content["similarity_score"] = similarity
                similar_content.append(content)

        # Sort by similarity and return top matches
        similar_content.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_content[:limit]

    def get_related_content(self, title: str, content_type: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get content related to a specific title.

        Args:
            title: Title to find related content for
            content_type: Type of the original content
            limit: Maximum number of items to return

        Returns:
            List of related content items
        """
        return self._find_similar_content(title, content_type, limit)

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity score between two titles.

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple word-based similarity calculation
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _generate_recommendation_id(self, user_id: str, type_prefix: str, content_id: str) -> str:
        """Generate a unique recommendation ID.

        Args:
            user_id: User identifier
            type_prefix: Type prefix for the ID
            content_id: Content identifier

        Returns:
            Unique recommendation ID
        """
        hash_input = f"{user_id}_{type_prefix}_{content_id}_{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    def save_user_recommendations(self, user_id: str, recommendations: UserRecommendations) -> bool:
        """Save recommendations for a user.

        Args:
            user_id: User identifier
            recommendations: Recommendations to save

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            recommendations_file = self.get_user_recommendations_file(user_id)

            # Convert to JSON-serializable format
            data = recommendations.dict()

            # Convert datetime fields to ISO strings
            if isinstance(data.get("generated_at"), datetime):
                data["generated_at"] = recommendations.generated_at.isoformat()

            for rec in data["recommendations"]:
                if isinstance(rec.get("generated_at"), datetime):
                    rec["generated_at"] = rec["generated_at"].isoformat()
                if isinstance(rec.get("expires_at"), datetime):
                    rec["expires_at"] = rec["expires_at"].isoformat()
                if isinstance(rec.get("feedback_timestamp"), datetime):
                    rec["feedback_timestamp"] = rec["feedback_timestamp"].isoformat()

            with open(recommendations_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(recommendations.recommendations)} recommendations for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save recommendations for user {user_id}: {e}")
            return False

    def load_user_recommendations(self, user_id: str) -> UserRecommendations | None:
        """Load recommendations for a user.

        Args:
            user_id: User identifier

        Returns:
            User recommendations or None if not found/failed
        """
        try:
            recommendations_file = self.get_user_recommendations_file(user_id)

            if not recommendations_file.exists():
                return None

            with open(recommendations_file, encoding="utf-8") as f:
                data = json.load(f)

            # Parse datetime fields
            if isinstance(data.get("generated_at"), str):
                data["generated_at"] = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))

            for rec in data.get("recommendations", []):
                if isinstance(rec.get("generated_at"), str):
                    rec["generated_at"] = datetime.fromisoformat(rec["generated_at"].replace("Z", "+00:00"))
                if isinstance(rec.get("expires_at"), str):
                    rec["expires_at"] = datetime.fromisoformat(rec["expires_at"].replace("Z", "+00:00"))
                if rec.get("feedback_timestamp"):
                    rec["feedback_timestamp"] = datetime.fromisoformat(rec["feedback_timestamp"].replace("Z", "+00:00"))

            return UserRecommendations(**data)

        except Exception as e:
            logger.error(f"Failed to load recommendations for user {user_id}: {e}")
            return None

    def update_recommendation_feedback(self, user_id: str, recommendation_id: str, helpful: bool) -> bool:
        """Update user feedback on a recommendation.

        Args:
            user_id: User identifier
            recommendation_id: Recommendation identifier
            helpful: Whether user found recommendation helpful

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            recommendations = self.load_user_recommendations(user_id)
            if not recommendations:
                return False

            # Find and update the recommendation
            updated = False
            for rec in recommendations.recommendations:
                if rec.id == recommendation_id:
                    rec.feedback = helpful
                    rec.feedback_timestamp = datetime.now()
                    updated = True
                    break

            if updated:
                # Update user profile feedback metrics
                profile = self.activity_tracker.get_user_profile(user_id)
                if profile:
                    # Recalculate feedback ratios
                    feedback_positive = sum(1 for r in recommendations.recommendations if r.feedback is True)
                    feedback_total = sum(1 for r in recommendations.recommendations if r.feedback is not None)
                    profile.feedback_ratio = feedback_positive / feedback_total if feedback_total > 0 else 0.0
                    self.activity_tracker.save_user_profile(user_id, profile)

                # Save updated recommendations
                self.save_user_recommendations(user_id, recommendations)
                logger.debug(f"Updated feedback for recommendation {recommendation_id} for user {user_id}")

            return updated

        except Exception as e:
            logger.error(f"Failed to update recommendation feedback: {e}")
            return False

    def dismiss_recommendation(self, user_id: str, recommendation_id: str) -> bool:
        """Mark a recommendation as dismissed by the user.

        Args:
            user_id: User identifier
            recommendation_id: Recommendation identifier

        Returns:
            True if dismissal succeeded, False otherwise
        """
        try:
            recommendations = self.load_user_recommendations(user_id)
            if not recommendations:
                return False

            # Find and dismiss the recommendation
            dismissed = False
            for rec in recommendations.recommendations:
                if rec.id == recommendation_id:
                    rec.dismissed = True
                    dismissed = True
                    break

            if dismissed:
                # Update user profile dismissal rate
                profile = self.activity_tracker.get_user_profile(user_id)
                if profile:
                    dismissed_count = sum(1 for r in recommendations.recommendations if r.dismissed)
                    profile.dismissal_rate = dismissed_count / len(recommendations.recommendations)
                    self.activity_tracker.save_user_profile(user_id, profile)

                # Save updated recommendations
                self.save_user_recommendations(user_id, recommendations)
                logger.debug(f"Dismissed recommendation {recommendation_id} for user {user_id}")

            return dismissed

        except Exception as e:
            logger.error(f"Failed to dismiss recommendation: {e}")
            return False
