#!/usr/bin/env python3
"""Test script for the recommendation system."""

from datetime import datetime, timedelta
from pathlib import Path
from src.recommendations.activity_tracker import UserActivityTracker
from src.recommendations.recommendation_engine import RecommendationEngine
from src.recommendations.models import ActivityType


def create_sample_content_data():
    """Create sample content data for testing recommendations."""

    # Create some mock content data in the expected format
    content_data = {
        "arxiv_papers": [
            {"id": "arxiv-1", "title": "Machine Learning Advances", "type": "arxiv_paper", "category": "ai"},
            {"id": "arxiv-2", "title": "Deep Learning Fundamentals", "type": "arxiv_paper", "category": "ai"},
            {"id": "arxiv-3", "title": "Python Data Science", "type": "arxiv_paper", "category": "data-science"},
        ],
        "news_articles": [
            {"id": "news-1", "title": "Tech Industry Trends", "type": "news_article", "category": "technology"},
            {"id": "news-2", "title": "AI News Today", "type": "news_article", "category": "ai"},
        ],
        "courses": [
            {"id": "course-1", "title": "Python Programming", "type": "course", "category": "programming"},
            {"id": "course-2", "title": "Web Development", "type": "course", "category": "web-dev"},
        ]
    }

    return content_data


def track_user_activity(tracker, user_id):
    """Track sample user activities for testing."""

    print(f"Tracking activities for user {user_id}...")

    # Track various user interactions over the past few days
    activities = [
        # User likes AI and machine learning content
        (datetime.now() - timedelta(days=1), ActivityType.CLICK, "arxiv-1", "arxiv_paper", "ai", "Machine Learning Advances", 120.0),
        (datetime.now() - timedelta(days=2), ActivityType.VIEW, "arxiv-2", "arxiv_paper", "ai", "Deep Learning Fundamentals", 90.0),
        (datetime.now() - timedelta(days=3), ActivityType.CLICK, "news-2", "news_article", "ai", "AI News Today", 60.0),

        # User also interested in Python programming
        (datetime.now() - timedelta(days=4), ActivityType.CLICK, "course-1", "course", "programming", "Python Programming", 180.0),
        (datetime.now() - timedelta(days=5), ActivityType.VIEW, "arxiv-3", "arxiv_paper", "data-science", "Python Data Science", 150.0),

        # Some general browsing
        (datetime.now() - timedelta(days=6), ActivityType.VIEW, "news-1", "news_article", "technology", "Tech Industry Trends", 45.0),
        (datetime.now() - timedelta(days=7), ActivityType.CLICK, "course-2", "course", "web-dev", "Web Development", 30.0),

        # Recent activity (important for recommendations)
        (datetime.now() - timedelta(hours=2), ActivityType.SEARCH, "search-python", "search", "programming", "Python Search Query", 5.0),
        (datetime.now() - timedelta(hours=1), ActivityType.VIEW, "arxiv-1", "arxiv_paper", "ai", "Machine Learning Advances", 200.0),
    ]

    for timestamp, action, content_id, content_type, category, title, duration in activities:
        success = tracker.track_interaction(
            user_id=user_id,
            action=action,
            content_id=content_id,
            content_type=content_type,
            source_category=category,
            title=title,
            duration_seconds=duration,
            metadata={"tracked_at": timestamp.isoformat()}
        )

        if not success:
            print(f"Failed to track activity: {action} on {content_id}")

    print(f"Tracked {len(activities)} activities for user {user_id}")


def test_activity_tracker():
    """Test the user activity tracker functionality."""

    print("Testing User Activity Tracker...")
    print("=" * 50)

    # Initialize tracker
    tracker = UserActivityTracker()
    user_id = "test-user"

    # Track sample activities
    track_user_activity(tracker, user_id)

    # Load and verify activities
    activities = tracker.load_user_activities(user_id, days=30)
    print(f"Loaded {len(activities)} activities for user {user_id}")

    # Get user profile
    profile = tracker.get_user_profile(user_id)
    if profile:
        print(f"User Profile Generated:")
        print(f"  Total Activities: {profile.total_activities}")
        print(f"  Top Sources: {profile.top_sources}")
        print(f"  Top Categories: {profile.top_categories}")
        print(f"  Favorite Content Types: {profile.favorite_content_types}")
        print(f"  Avg Session Duration: {profile.avg_session_duration:.1f}s")
        print(f"  Interaction Frequency: {dict(profile.interaction_frequency)}")
    else:
        print("No user profile generated")
        return False

    # Verify expected behavior
    assert len(activities) >= 9, f"Expected at least 9 activities, got {len(activities)}"
    assert profile.total_activities >= 9, f"Expected at least 9 total activities in profile"
    assert "ai" in profile.top_categories, f"Expected 'ai' in top categories, got {profile.top_categories}"
    assert "arxiv_paper" in profile.top_sources, f"Expected 'arxiv_paper' in top sources, got {profile.top_sources}"

    print("[SUCCESS] Activity tracker tests passed!")
    return True


def test_recommendation_engine():
    """Test the recommendation engine functionality."""

    print("\nTesting Recommendation Engine...")
    print("=" * 50)

    # Initialize components
    data_dir = Path("data/test-users")
    tracker = UserActivityTracker(data_dir)
    engine = RecommendationEngine(tracker, data_dir)
    user_id = "test-user-2"

    # Track user activities
    track_user_activity(tracker, user_id)

    # Generate recommendations
    recommendations = engine.generate_recommendations(user_id)

    if recommendations:
        print(f"Generated {len(recommendations.recommendations)} recommendations:")
        print(f"  Activity Window: {recommendations.activity_window_days} days")
        print(f"  Activities Analyzed: {recommendations.total_activities_analyzed}")
        print(f"  Average Score: {recommendations.avg_score:.3f}")
        print(f"  Diversity Score: {recommendations.diversity_score:.3f}")

        for i, rec in enumerate(recommendations.recommendations[:5], 1):
            print(f"\n  Recommendation {i}:")
            print(f"    Type: {rec.type}")
            print(f"    Title: {rec.title}")
            print(f"    Score: {rec.score:.3f}")
            print(f"    Reason: {rec.description}")
    else:
        print("No recommendations generated")
        return False

    # Test saving and loading recommendations
    saved_recommendations = engine.load_user_recommendations(user_id)
    if saved_recommendations:
        print(f"\nLoaded {len(saved_recommendations.recommendations)} saved recommendations")
    else:
        print("Failed to load saved recommendations")
        return False

    # Verify expected behavior
    assert len(recommendations.recommendations) > 0, "Expected some recommendations to be generated"
    assert recommendations.avg_score > 0.0, "Expected positive average score"
    assert recommendations.total_activities_analyzed >= 9, "Expected activities to be analyzed"

    print("[SUCCESS] Recommendation engine tests passed!")
    return True


def test_recommendations_system():
    """Test the complete recommendations system."""

    print("Testing Complete Recommendations System")
    print("=" * 60)

    # Test individual components
    tracker_success = test_activity_tracker()
    engine_success = test_recommendation_engine()

    if tracker_success and engine_success:
        print("\n[SUCCESS] All recommendations system tests passed!")
        return True
    else:
        print("\n[FAILED] Some tests failed")
        return False


if __name__ == "__main__":
    test_recommendations_system()