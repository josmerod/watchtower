"""Pydantic models for Job Market Intelligence."""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel


class JobSource(str, Enum):
    """Source of the job posting."""
    REMOTEOK = "RemoteOK"
    HACKERNEWS = "Hacker News"
    REMOTIVE = "Remotive"
    JOBICY = "Jobicy"
    OTHER = "Other"


class JobPostingModel(TimestampedModel):
    """Model representing a job posting."""

    # Core info
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    description: str | None = Field(default=None, description="Job description")
    url: HttpUrl | None = Field(default=None, description="Link to the job posting")
    source: JobSource = Field(default=JobSource.OTHER, description="Data source")
    external_id: str | None = Field(default=None, description="External ID (e.g. HN item ID)")
    
    # Details
    location: str | None = Field(default=None, description="Job location (e.g. Remote, City)")
    is_remote: bool = Field(default=False, description="Is remote position")
    role: str | None = Field(default="Unknown", description="Categorized role (e.g. Backend, Frontend)")
    
    # Intelligence (Parsed/Enriched)
    salary_min: float | None = Field(default=None, description="Minimum salary")
    salary_max: float | None = Field(default=None, description="Maximum salary")
    currency: str = Field(default="USD", description="Currency code")
    
    technologies: List[str] = Field(default=[], description="Tech stack tags")
    
    posted_date: datetime | None = Field(default=None, description="Date posted")


class JobMarketTrendsModel(TimestampedModel):
    """Model for aggregated job market trends."""
    
    period: str = Field(description="Time period (e.g. 2025-01)")
    
    # Tech Popularity: {"Python": 150, "React": 120}
    tech_popularity: dict[str, int] = Field(default={}, description="Technology mention counts")
    
    # Average Salary by Role/Tech (simplified)
    # {"Python": 150000, "Junior": 80000}
    salary_stats: dict[str, float] = Field(default={}, description="Average salary stats")
    
    total_jobs: int = Field(default=0, description="Total jobs analyzed in this period")
