"""Course-related data models for Watchtower."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from .base import TimestampedModel


class CourseModel(TimestampedModel):
    """Model for course information from various platforms."""

    title: str = Field(description="Course title")
    url: str = Field(description="Course URL")
    provider: str = Field(description="Course provider (e.g., Pluralsight, Coursera)")
    description: str | None = Field(default=None, description="Course description")
    instructor: str | None = Field(default=None, description="Course instructor")
    duration: str | None = Field(default=None, description="Course duration")
    level: str | None = Field(default=None, description="Course level (Beginner, Intermediate, Advanced)")
    subject: str | None = Field(default=None, description="Course subject/category")
    rating: float | None = Field(default=None, description="Course rating")
    rating_count: int | None = Field(default=None, description="Number of ratings")
    is_free: bool = Field(default=False, description="Whether the course is free")
    published_date: datetime | None = Field(default=None, description="Course publication date")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When the course was scraped")
    language: str | None = Field(default=None, description="Course language")
    category: str | None = Field(default=None, description="Course category")
    subcategory: str | None = Field(default=None, description="Course subcategory")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: float | None) -> float | None:
        """Validate rating is within valid range."""
        if v is not None and (v < 0 or v > 5):
            return None
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL starts with http/https."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class PluralsightCourseModel(CourseModel):
    """Specific model for Pluralsight courses."""

    provider: str = Field(default="Pluralsight", description="Always Pluralsight")
    skill_paths: list[str] | None = Field(default=None, description="Associated skill paths")
    course_id: str | None = Field(default=None, description="Pluralsight course ID")


class MsAppliedSkillModel(CourseModel):
    """Specific model for Microsoft Applied Skills and certifications."""

    provider: str = Field(default="Microsoft Learn", description="Always Microsoft Learn")
    roles: list[str] | None = Field(default=None, description="Roles the skill is applicable to")
    products: list[str] | None = Field(default=None, description="Microsoft products covered by the skill")
    first_detected_at: datetime | None = Field(default=None, description="When the skill was first detected by Watchtower")


class AwsSkillBuilderModel(CourseModel):
    """Specific model for AWS Skill Builder courses."""

    provider: str = Field(default="AWS Skill Builder", description="Always AWS Skill Builder")
    first_detected_at: datetime | None = Field(default=None, description="When the course was first detected by Watchtower")


class GcpSkillsBoostModel(CourseModel):
    """Specific model for GCP Skills Boost courses and labs."""

    provider: str = Field(default="GCP Skills Boost", description="Always GCP Skills Boost")
    course_type: str | None = Field(default=None, description="Type of content (e.g., lab, course, quest)")
    first_detected_at: datetime | None = Field(default=None, description="When the course was first detected by Watchtower")
