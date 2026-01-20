"""Models for Stack Exchange data sources.

Part of Phase 2 ETL implementation for Stack Exchange Network.
Supports 180+ sites including Stack Overflow, Server Fault, Super User, etc.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class StackExchangeSite(str, Enum):
    """Stack Exchange network sites."""

    STACKOVERFLOW = "stackoverflow"
    SERVER_FAULT = "serverfault"
    SUPER_USER = "superuser"
    MATHEMATICS = "mathematics"
    ASK_UBUNTU = "askubuntu"
    UNIX_LINUX = "unix"
    APPLE = "apple"
    ANDROID = "android"
    GAMING = "gaming"
    SCI_FI = "scifi"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    PHILOSOPHY = "philosophy"
    ENGLISH = "english"
    SOFTWARE_ENGINEERING = "softwareengineering"
    COMPUTER_GRAPHICS = "computergraphics"
    CODE_GOLF = "codegolf"
    DATA_SCIENCE = "datascience"
    BLENDER = "blender"


class QuestionType(str, Enum):
    """Question types."""

    QUESTION = "question"
    ANSWER = "answer"
    COMMENT = "comment"


class StackExchangeQuestionModel(TimestampedModel):
    """Model for a Stack Exchange question.

    Represents a question from any Stack Exchange site.
    """

    # Core question fields
    question_id: str = Field(description="Question ID")
    title: str = Field(description="Question title")
    body: str | None = Field(default=None, description="Question body content (HTML)")
    excerpt: str | None = Field(default=None, description="Question excerpt")
    url: str = Field(description="Question URL")

    # Site information
    site: StackExchangeSite = Field(description="Stack Exchange site")
    site_name: str = Field(description="Site display name")
    site_url: str | None = Field(default=None, description="Site base URL")

    # Author information
    author_id: str = Field(description="Author user ID")
    author_name: str = Field(description="Author display name")
    author_reputation: int = Field(default=0, ge=0, description="Author reputation")

    # Statistics
    score: int = Field(default=0, description="Question score (upvotes - downvotes)")
    views_count: int = Field(default=0, ge=0, description="Number of views")
    answers_count: int = Field(default=0, ge=0, description="Number of answers")
    comments_count: int = Field(default=0, ge=0, description="Number of comments")

    # Status
    is_answered: bool = Field(default=False, description="Whether question has accepted answer")
    accepted_answer_id: str | None = Field(default=None, description="Accepted answer ID")

    # Tags and classification
    tags: list[str] = Field(default_factory=list, description="Question tags")

    # Creation timestamps
    api_created_at: datetime | None = Field(default=None, description="Question creation date from API")
    last_activity_at: datetime | None = Field(default=None, description="Last activity date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="API response data")

    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate.

        Returns:
            Engagement rate (answers per 1000 views).
        """
        if self.views_count == 0:
            return 0.0
        return (self.answers_count / self.views_count) * 1000

    @property
    def is_trending(self) -> bool:
        """Check if question is trending.

        Returns:
            True if score > 10 and has 2+ answers.
        """
        return self.score > 10 and self.answers_count >= 2


class StackExchangeAnswerModel(TimestampedModel):
    """Model for a Stack Exchange answer."""

    # Core answer fields
    answer_id: str = Field(description="Answer ID")
    body: str | None = Field(default=None, description="Answer body content (HTML)")
    excerpt: str | None = Field(default=None, description="Answer excerpt")
    url: str = Field(description="Answer URL")

    # Question reference
    question_id: str = Field(description="Parent question ID")
    question_title: str | None = Field(default=None, description="Parent question title")

    # Author information
    author_id: str = Field(description="Author user ID")
    author_name: str = Field(description="Author display name")
    author_reputation: int = Field(default=0, ge=0, description="Author reputation")

    # Statistics
    score: int = Field(default=0, description="Answer score (upvotes - downvotes)")
    comments_count: int = Field(default=0, ge=0, description="Number of comments")

    # Status
    is_accepted: bool = Field(default=False, description="Whether this is the accepted answer")

    # Site information
    site: StackExchangeSite = Field(description="Stack Exchange site")

    # Creation timestamps
    api_created_at: datetime | None = Field(default=None, description="Answer creation date from API")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="API response data")


class StackExchangeTagModel(TimestampedModel):
    """Model for a Stack Exchange tag.

    Represents a topic tag from any Stack Exchange site.
    """

    # Core tag fields
    name: str = Field(description="Tag name")
    site: StackExchangeSite = Field(description="Stack Exchange site")

    # Statistics
    count: int = Field(default=0, ge=0, description="Number of questions with this tag")
    questions_today: int = Field(default=0, ge=0, description="Questions asked today")

    # Popularity
    is_required: bool = Field(default=False, description="Whether tag is required")
    is_moderator_only: bool = Field(default=False, description="Whether tag is moderator-only")

    # Metadata
    excerpt: str | None = Field(default=None, description="Tag description")
    wiki_body: str | None = Field(default=None, description="Tag wiki content")

    # Synonyms
    synonyms: list[str] = Field(default_factory=list, description="Tag synonyms")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional data")


class StackExchangeMetricsModel(TimestampedModel):
    """Model for Stack Exchange ETL metrics."""

    # API request metrics
    successful_requests: int = Field(default=0, description="Successful API requests")
    failed_requests: int = Field(default=0, description="Failed API requests")

    # Discovery metrics
    total_questions_discovered: int = Field(default=0, description="Total questions discovered")
    total_answers_discovered: int = Field(default=0, description="Total answers discovered")
    new_questions_this_run: int = Field(default=0, description="New questions this run")

    # Site breakdown
    site_distribution: dict[str, int] = Field(default_factory=dict, description="Questions by site")

    # Tag metrics
    tag_distribution: dict[str, int] = Field(default_factory=dict, description="Questions by tag")
    total_tags_discovered: int = Field(default=0, description="Total unique tags")

    # Engagement metrics
    avg_score: float | None = Field(default=None, description="Average question score")
    avg_answers: float | None = Field(default=None, description="Average answers per question")
    answered_questions: int = Field(default=0, description="Questions with answers")
    accepted_answers: int = Field(default=0, description="Questions with accepted answer")

    # Trending metrics
    trending_questions: int = Field(default=0, description="Trending questions")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
