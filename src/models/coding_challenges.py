"""Pydantic models for Coding Challenge Intelligence."""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel


class ChallengeDifficulty(str, Enum):
    """Difficulty level of the challenge."""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    UNKNOWN = "Unknown"


class ChallengePlatform(str, Enum):
    """Platform where the challenge is hosted."""
    LEETCODE = "LeetCode"
    HACKERRANK = "HackerRank"
    CODEFORCES = "Codeforces"
    OTHER = "Other" # For generic or manually added ones


class CodingChallengeModel(TimestampedModel):
    """Model representing a coding challenge/problem."""

    # Core info
    title: str = Field(description="Title of the challenge")
    slug: str = Field(description="URL-friendly slug (e.g. two-sum)")
    platform: ChallengePlatform = Field(default=ChallengePlatform.LEETCODE, description="Platform source")
    external_id: str | None = Field(default=None, description="Platform specific ID (e.g. Question ID)")
    
    # Details
    description: str | None = Field(default=None, description="Short description or snippet")
    difficulty: ChallengeDifficulty = Field(default=ChallengeDifficulty.UNKNOWN, description="Difficulty level")
    url: HttpUrl | None = Field(default=None, description="Link to the challenge")
    
    # Metadata
    tags: List[str] = Field(default=[], description="Topic tags (e.g. Array, DP)")
    acceptance_rate: float | None = Field(default=None, description="Acceptance rate percentage")
    is_paid_only: bool = Field(default=False, description="Requires premium subscription")
    
    # Status (User context) - This might be better in a separate user-state model if we sync often,
    # but for now, we can store it here if we assume single-user enrichment.
    status: str | None = Field(default=None, description="Status: ac (Accepted), notac (Attempted), null (Todo)")


class UserPerformanceModel(TimestampedModel):
    """Model representing user performance stats on a platform."""
    
    platform: ChallengePlatform = Field(description="Platform")
    username: str = Field(description="Username on the platform")
    
    # Stats
    total_solved: int = Field(default=0, description="Total problems solved")
    easy_solved: int = Field(default=0, description="Easy problems solved")
    medium_solved: int = Field(default=0, description="Medium problems solved")
    hard_solved: int = Field(default=0, description="Hard problems solved")
    
    global_ranking: int | None = Field(default=None, description="Global ranking")
    
    # Metadata
    raw_stats: dict[str, Any] | None = Field(default=None, description="Raw stats payload")
