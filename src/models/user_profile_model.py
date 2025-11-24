"""Data models for User Profiles and Personalized Learning."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field

from src.models.base import TimestampedModel
from src.models.ai_research_model import ResearchDomain


class SkillLevel(str, Enum):
    """User skill levels for personalized content."""
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


class LearningGoal(TimestampedModel):
    """Structured learning goal for a user."""
    
    goal_name: str = Field(description="Name of the learning goal")
    target_domain: ResearchDomain = Field(description="Target AI/ML domain")
    target_skill_level: SkillLevel = Field(description="Desired skill level to achieve")
    deadline: Optional[datetime] = Field(default=None, description="Optional deadline for goal")
    keywords: List[str] = Field(default=[], description="Keywords related to this goal")
    completed: bool = Field(default=False, description="Whether goal has been achieved")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "goal_name": "Master Transformer Architectures",
                    "target_domain": "Natural Language Processing",
                    "target_skill_level": "Advanced",
                    "keywords": ["transformer", "attention", "bert", "gpt"],
                    "completed": False
                }
            ]
        }


class ContentPreferences(TimestampedModel):
    """User preferences for content types and formats."""
    
    prefer_papers: bool = Field(default=True, description="Show research papers")
    prefer_tutorials: bool = Field(default=True, description="Show tutorials")
    prefer_videos: bool = Field(default=False, description="Show video content")
    prefer_code_examples: bool = Field(default=True, description="Show code examples")
    
    # Complexity preferences
    min_complexity: str = Field(default="Low", description="Minimum complexity level")
    max_complexity: str = Field(default="Very High", description="Maximum complexity level")
    
    # Source preferences
    preferred_sources: List[str] = Field(default=["arxiv"], description="Preferred content sources")


class UserProfile(TimestampedModel):
    """User profile for personalized AI content discovery."""
    
    # Identity
    user_id: str = Field(description="Unique user identifier")
    username: str = Field(default="", description="Display name")
    
    # Preferences
    preferred_domains: List[ResearchDomain] = Field(
        default=[],
        description="Preferred AI/ML research domains"
    )
    skill_level: SkillLevel = Field(
        default=SkillLevel.INTERMEDIATE,
        description="Overall skill level"
    )
    
    # Learning goals
    learning_goals: List[LearningGoal] = Field(
        default=[],
        description="Active learning goals"
    )
    
    # Content preferences
    content_preferences: ContentPreferences = Field(
        default_factory=ContentPreferences,
        description="Content type and format preferences"
    )
    
    # Progress tracking
    completed_papers: List[str] = Field(
        default=[],
        description="IDs of papers user has read/completed"
    )
    bookmarked_papers: List[str] = Field(
        default=[],
        description="IDs of papers saved for later"
    )
    
    # Interaction history
    viewed_papers: Dict[str, datetime] = Field(
        default={},
        description="Paper IDs mapped to last viewed timestamp"
    )
    
    # Metadata
    profile_created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When profile was created"
    )
    last_active_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last time user was active"
    )
    
    # Architecture Intelligence
    tech_stack: List[str] = Field(
        default=[],
        description="Technologies used (e.g., Python, React, PostgreSQL, AWS)"
    )
    team_size: Optional[str] = Field(
        default=None,
        description="Team size (Solo, Small 2-5, Medium 6-20, Large 20+)"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "user_id": "user_123",
                    "username": "AI Enthusiast",
                    "preferred_domains": ["Natural Language Processing", "Computer Vision"],
                    "skill_level": "Intermediate",
                    "learning_goals": [
                        {
                            "goal_name": "Learn Vision Transformers",
                            "target_domain": "Computer Vision",
                            "target_skill_level": "Advanced"
                        }
                    ],
                    "completed_papers": ["2010.11929", "1706.03762"],
                    "bookmarked_papers": ["2103.14030"]
                }
            ]
        }
