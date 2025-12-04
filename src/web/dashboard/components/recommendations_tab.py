"""Recommendations tab component for the dashboard.

This module provides the recommendations tab that displays personalized
content recommendations based on user activity patterns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.recommendations.activity_tracker import UserActivityTracker
from src.recommendations.models import UserRecommendations
from src.recommendations.recommendation_engine import RecommendationEngine
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RecommendationsManager:
    """Manager class for handling recommendation data and user interactions."""

    def __init__(self):
        """Initialize the recommendations manager."""
        self.activity_tracker = UserActivityTracker()
        self.recommendation_engine = RecommendationEngine(self.activity_tracker)

    def get_user_recommendations(self, user_id: str = "default") -> UserRecommendations | None:
        """Get recommendations for a user.

        Args:
            user_id: User identifier (defaults to 'default' for single-user mode)

        Returns:
            User recommendations or None if not available
        """
        try:
            # Try to load existing recommendations
            recommendations = self.recommendation_engine.load_user_recommendations(user_id)

            # Generate new recommendations if none exist or they're old (>24h)
            if not recommendations or recommendations.generated_at < datetime.now() - timedelta(hours=24):
                recommendations = self.recommendation_engine.generate_recommendations(user_id)

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get user recommendations: {e}")
            return None

    def track_interaction(self, user_id: str, action: str, content_id: str, content_type: str, **kwargs) -> bool:
        """Track a user interaction for activity logging.

        Args:
            user_id: User identifier
            action: Type of interaction (click, view, etc.)
            content_id: Content identifier
            content_type: Type of content
            **kwargs: Additional interaction metadata

        Returns:
            True if tracking succeeded, False otherwise
        """
        try:
            from src.recommendations.models import ActivityType

            activity_type = ActivityType(action) if action in [t.value for t in ActivityType] else ActivityType.VIEW

            return self.activity_tracker.track_interaction(
                user_id=user_id,
                action=activity_type,
                content_id=content_id,
                content_type=content_type,
                metadata=kwargs.get("metadata", {}),
                duration_seconds=kwargs.get("duration_seconds"),
                source_category=kwargs.get("source_category"),
                title=kwargs.get("title"),
            )

        except Exception as e:
            logger.error(f"Failed to track interaction: {e}")
            return False

    def update_feedback(self, user_id: str, recommendation_id: str, helpful: bool) -> bool:
        """Update user feedback on a recommendation.

        Args:
            user_id: User identifier
            recommendation_id: Recommendation identifier
            helpful: Whether recommendation was helpful

        Returns:
            True if update succeeded, False otherwise
        """
        return self.recommendation_engine.update_recommendation_feedback(user_id, recommendation_id, helpful)

    def dismiss_recommendation(self, user_id: str, recommendation_id: str) -> bool:
        """Dismiss a recommendation for a user.

        Args:
            user_id: User identifier
            recommendation_id: Recommendation identifier

        Returns:
            True if dismissal succeeded, False otherwise
        """
        return self.recommendation_engine.dismiss_recommendation(user_id, recommendation_id)


# Global manager instance
recommendations_manager = RecommendationsManager()


def render_recommendations_tab(user_id: str = "default") -> html.Div:
    """Render the recommendations tab component.

    Args:
        user_id: User identifier (defaults to 'default' for single-user mode)

    Returns:
        Dash HTML component for the recommendations tab
    """
    tab_id = f"recommendations-tab-{str(uuid.uuid4())[:8]}"

    return html.Div(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4(
                                [
                                    html.I(className="bi bi-stars me-2"),
                                    "Recommended for You",
                                ],
                                className="mb-3",
                            ),
                            html.P(
                                [
                                    "Personalized recommendations based on your reading patterns. ",
                                    "Updated daily using your last 30 days of activity.",
                                ],
                                className="text-muted mb-4",
                            ),
                        ]
                    )
                ]
            ),
            # Store for recommendations data
            dcc.Store(id=f"{tab_id}-recommendations-store", data={}),
            dcc.Store(id=f"{tab_id}-user-id", data=user_id),
            # Refresh button
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-arrow-clockwise me-2"),
                                    "Refresh Recommendations",
                                ],
                                id=f"{tab_id}-refresh-btn",
                                color="outline-primary",
                                size="sm",
                                className="mb-3",
                            ),
                        ]
                    )
                ]
            ),
            # Recommendations container
            html.Div(id=f"{tab_id}-recommendations-container"),
            # Loading indicator
            dcc.Loading(
                id=f"{tab_id}-loading",
                type="default",
                children=html.Div(id=f"{tab_id}-loading-placeholder"),
            ),
        ],
        id=tab_id,
        className="tab-content",
    )


def load_recommendations_data(n_clicks: int | None, user_id: str) -> tuple[dict[str, Any], None]:
    """Load recommendations for the user.

    Args:
        n_clicks: Number of times refresh button was clicked
        user_id: User identifier

    Returns:
        Tuple of (recommendations data, None for loading placeholder)
    """
    try:
        # Get recommendations
        recommendations = recommendations_manager.get_user_recommendations(user_id)

        if recommendations:
            # Convert to JSON-serializable format
            data = {
                "user_id": recommendations.user_id,
                "generated_at": recommendations.generated_at.isoformat(),
                "total_activities_analyzed": recommendations.total_activities_analyzed,
                "avg_score": recommendations.avg_score,
                "diversity_score": recommendations.diversity_score,
                "recommendations": [
                    {
                        "id": rec.id,
                        "type": rec.type.value,
                        "content_id": rec.content_id,
                        "content_type": rec.content_type,
                        "title": rec.title,
                        "description": rec.description,
                        "score": rec.score,
                        "dismissed": rec.dismissed,
                        "feedback": rec.feedback,
                        "metadata": rec.metadata,
                    }
                    for rec in recommendations.get_active_recommendations()
                ],
            }
        else:
            data = {"recommendations": []}

        return data, None

    except Exception as e:
        logger.error(f"Failed to load recommendations: {e}")
        return {"recommendations": []}, None


def render_recommendations_container_data(
    recommendations_data: dict[str, Any],
) -> html.Div:
    """Render the recommendations container with recommendations cards.

    Args:
        recommendations_data: Recommendations data from store

    Returns:
        Dash HTML component for recommendations container
    """
    try:
        recommendations = recommendations_data.get("recommendations", [])

        if not recommendations:
            return html.Div(
                [
                    dbc.Alert(
                        [
                            html.I(className="bi bi-info-circle me-2"),
                            "No recommendations available yet. ",
                            "Continue using the dashboard to generate personalized recommendations based on your activity.",
                        ],
                        color="info",
                        className="mt-3",
                    ),
                ]
            )

        # Group recommendations by type
        grouped_recommendations = {}
        for rec in recommendations:
            rec_type = rec["type"]
            if rec_type not in grouped_recommendations:
                grouped_recommendations[rec_type] = []
            grouped_recommendations[rec_type].append(rec)

        # Create recommendation sections
        sections = []

        # Top Sources section
        if "top_source" in grouped_recommendations:
            sections.append(
                create_recommendation_section(
                    "📚 Top Sources",
                    "Sources you frequently read",
                    grouped_recommendations["top_source"][:5],
                    "primary",
                )
            )

        # Top Categories section
        if "top_category" in grouped_recommendations:
            sections.append(
                create_recommendation_section(
                    "🏷️ Top Categories",
                    "Content from categories you engage with",
                    grouped_recommendations["top_category"][:3],
                    "success",
                )
            )

        # Similar Content section
        if "similar_content" in grouped_recommendations:
            sections.append(
                create_recommendation_section(
                    "🔗 Similar Content",
                    "Content similar to what you've recently viewed",
                    grouped_recommendations["similar_content"][:4],
                    "info",
                )
            )

        # Add metadata section
        metadata_section = create_metadata_section(recommendations_data)
        if metadata_section:
            sections.append(metadata_section)

        return html.Div(sections)

    except Exception as e:
        logger.error(f"Failed to render recommendations container: {e}")
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle me-2"),
                "Failed to load recommendations. Please try refreshing.",
            ],
            color="danger",
            className="mt-3",
        )


def create_recommendation_section(title: str, description: str, recommendations: list[dict[str, Any]], color: str) -> html.Div:
    """Create a recommendation section with cards.

    Args:
        title: Section title
        description: Section description
        recommendations: List of recommendations
        color: Bootstrap color for the section

    Returns:
        Dash HTML component for the section
    """
    cards = []
    for rec in recommendations:
        card = create_recommendation_card(rec, color)
        cards.append(dbc.Col(card, md=6, lg=4, className="mb-3"))

    return html.Div(
        [
            html.H5(title, className="mt-4 mb-2"),
            html.P(description, className="text-muted mb-3"),
            (
                dbc.Row(cards)
                if cards
                else html.P(
                    "No recommendations available in this category.",
                    className="text-muted",
                )
            ),
        ]
    )


def create_recommendation_card(recommendation: dict[str, Any], color: str) -> dbc.Card:
    """Create a recommendation card.

    Args:
        recommendation: Recommendation data
        color: Bootstrap color for the card

    Returns:
        Dash Card component
    """
    rec_id = f"rec-{recommendation['id']}"

    card_header = dbc.CardHeader(
        [
            html.Div(
                [
                    html.Span(
                        [
                            html.I(className=f"bi bi-{get_recommendation_icon(recommendation['type'])} me-2"),
                            html.Small(
                                get_recommendation_type_label(recommendation["type"]),
                                className="text-muted",
                            ),
                        ]
                    ),
                    html.Span(
                        [
                            html.Small(
                                f"Score: {recommendation['score']:.2f}",
                                className="text-muted",
                            )
                        ],
                        style={"float": "right"},
                    ),
                ]
            )
        ]
    )

    card_body = dbc.CardBody(
        [
            html.H6(
                recommendation["title"],
                className="card-title text-truncate",
                title=recommendation["title"],
            ),
            html.P(
                recommendation["description"],
                className="card-text text-muted small mb-3",
            ),
            html.Div(
                [
                    # Feedback buttons
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-hand-thumbs-up me-1"),
                                    "Helpful",
                                ],
                                id=f"{rec_id}-helpful",
                                color="outline-success",
                                size="sm",
                            ),
                            dbc.Button(
                                [
                                    html.I(className="bi bi-hand-thumbs-down me-1"),
                                    "Not Helpful",
                                ],
                                id=f"{rec_id}-not-helpful",
                                color="outline-danger",
                                size="sm",
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-x-circle me-1"), "Dismiss"],
                                id=f"{rec_id}-dismiss",
                                color="outline-secondary",
                                size="sm",
                            ),
                        ],
                        size="sm",
                    ),
                ],
                className="d-flex gap-2 justify-content-end",
            ),
        ]
    )

    return dbc.Card([card_header, card_body], color=color, outline=True, className="h-100")


def create_metadata_section(recommendations_data: dict[str, Any]) -> html.Div | None:
    """Create metadata section showing recommendation statistics.

    Args:
        recommendations_data: Recommendations data

    Returns:
        Dash HTML component for metadata section or None
    """
    if not recommendations_data.get("recommendations"):
        return None

    try:
        generated_at = datetime.fromisoformat(recommendations_data["generated_at"])
        total_activities = recommendations_data.get("total_activities_analyzed", 0)
        avg_score = recommendations_data.get("avg_score", 0.0)
        diversity_score = recommendations_data.get("diversity_score", 0.0)

        return html.Div(
            [
                html.Hr(className="my-4"),
                html.H6("Recommendation Details", className="mb-3"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Small(
                                    [
                                        html.Strong("Generated: "),
                                        generated_at.strftime("%Y-%m-%d %H:%M"),
                                    ],
                                    className="text-muted",
                                ),
                            ],
                            md=6,
                            lg=3,
                        ),
                        dbc.Col(
                            [
                                html.Small(
                                    [
                                        html.Strong("Based on: "),
                                        f"{total_activities:,} activities",
                                    ],
                                    className="text-muted",
                                ),
                            ],
                            md=6,
                            lg=3,
                        ),
                        dbc.Col(
                            [
                                html.Small(
                                    [
                                        html.Strong("Avg. Confidence: "),
                                        f"{avg_score:.2f}",
                                    ],
                                    className="text-muted",
                                ),
                            ],
                            md=6,
                            lg=3,
                        ),
                        dbc.Col(
                            [
                                html.Small(
                                    [
                                        html.Strong("Diversity: "),
                                        f"{diversity_score:.2f}",
                                    ],
                                    className="text-muted",
                                ),
                            ],
                            md=6,
                            lg=3,
                        ),
                    ]
                ),
            ],
            className="bg-light p-3 rounded",
        )

    except Exception as e:
        logger.error(f"Failed to create metadata section: {e}")
        return None


def get_recommendation_icon(rec_type: str) -> str:
    """Get icon for recommendation type.

    Args:
        rec_type: Recommendation type

    Returns:
        Bootstrap icon name
    """
    icon_map = {
        "top_source": "bi-journal-text",
        "top_category": "bi-tag",
        "similar_content": "bi-link-45deg",
        "trending": "bi-graph-up",
    }
    return icon_map.get(rec_type, "bi-star")


def get_recommendation_type_label(rec_type: str) -> str:
    """Get human-readable label for recommendation type.

    Args:
        rec_type: Recommendation type

    Returns:
        Human-readable label
    """
    label_map = {
        "top_source": "Top Source",
        "top_category": "Top Category",
        "similar_content": "Similar Content",
        "trending": "Trending",
    }
    return label_map.get(rec_type, "Recommendation")


# Callbacks for recommendation interactions would be implemented in a real Dash app
# For testing purposes, these are defined but not used in the component itself


def handle_recommendation_feedback(n_clicks: int | None, user_id: str, rec_id: str, helpful: bool) -> bool:
    """Handle user feedback on recommendations.

    Args:
        n_clicks: Number of button clicks
        user_id: User identifier
        rec_id: Recommendation ID
        helpful: Whether recommendation was helpful

    Returns:
        True to disable button after feedback
    """
    if n_clicks is None:
        return False

    try:
        # Update feedback
        success = recommendations_manager.update_feedback(user_id, rec_id, helpful)

        if success:
            logger.debug(f"Recorded feedback ({'helpful' if helpful else 'not helpful'}) for recommendation {rec_id}")

        return success

    except Exception as e:
        logger.error(f"Failed to record recommendation feedback: {e}")
        return False


def handle_recommendation_dismissal(n_clicks: int | None, user_id: str, rec_id: str) -> list:
    """Handle recommendation dismissal.

    Args:
        n_clicks: Number of button clicks
        user_id: User identifier
        rec_id: Recommendation ID

    Returns:
        Updated button content (disabled state)
    """
    if n_clicks is None:
        return [html.I(className="bi bi-x-circle me-1"), "Dismiss"]

    try:
        # Dismiss recommendation
        success = recommendations_manager.dismiss_recommendation(user_id, rec_id)

        if success:
            logger.debug(f"Dismissed recommendation {rec_id}")
            return [html.I(className="bi bi-check-circle me-1"), "Dismissed"]

        return [html.I(className="bi bi-x-circle me-1"), "Dismiss"]

    except Exception as e:
        logger.error(f"Failed to dismiss recommendation: {e}")
        return [html.I(className="bi bi-x-circle me-1"), "Dismiss"]
