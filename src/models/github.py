"""GitHub repository and trending data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from .base import BaseModel, TimestampedModel


class TrendingPeriod(str, Enum):
    """Enum for GitHub trending periods."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class RepositoryLanguage(str, Enum):
    """Enum for supported programming languages."""
    
    ALL = "all"
    PYTHON = "python"
    JUPYTER_NOTEBOOK = "jupyter-notebook"
    CUDA = "cuda"
    HCL = "hcl"  # Terraform


class GitHubRepositoryOwner(BaseModel):
    """Model for GitHub repository owner information."""
    
    login: str = Field(description="Owner username")
    type: str = Field(description="Owner type (User/Organization)")
    html_url: str | None = Field(default=None, description="Owner profile URL")
    avatar_url: str | None = Field(default=None, description="Owner avatar URL")


class GitHubRepositoryModel(TimestampedModel):
    """Model for GitHub repository data from RSS feeds."""
    
    # Core repository info
    repository_id: int | None = Field(default=None, description="GitHub repository ID")
    name: str = Field(description="Repository name")
    full_name: str = Field(description="Full repository name (owner/repo)")
    description: str | None = Field(default=None, description="Repository description")
    html_url: str = Field(description="Repository URL")
    
    # Repository metadata
    language: str | None = Field(default=None, description="Primary programming language")
    stars_count: int = Field(default=0, description="Number of stars")
    forks_count: int = Field(default=0, description="Number of forks")
    watchers_count: int = Field(default=0, description="Number of watchers")
    open_issues_count: int = Field(default=0, description="Number of open issues")
    
    # Repository settings
    default_branch: str | None = Field(default=None, description="Default branch name")
    topics: list[str] = Field(default_factory=list, description="Repository topics/tags")
    license_name: str | None = Field(default=None, description="License name")
    size: int = Field(default=0, description="Repository size in KB")
    
    # Repository status
    archived: bool = Field(default=False, description="Whether repository is archived")
    disabled: bool = Field(default=False, description="Whether repository is disabled")
    has_wiki: bool = Field(default=False, description="Whether repository has wiki")
    has_pages: bool = Field(default=False, description="Whether repository has GitHub Pages")
    has_downloads: bool = Field(default=False, description="Whether repository has downloads")
    
    # Owner information
    owner: GitHubRepositoryOwner | None = Field(default=None, description="Repository owner")
    
    # Timestamps
    repository_created_at: datetime | None = Field(default=None, description="Repository creation date")
    repository_updated_at: datetime | None = Field(default=None, description="Repository last update date")
    pushed_at: datetime | None = Field(default=None, description="Last push date")
    
    # Trending context
    trending_period: TrendingPeriod = Field(description="Trending period (daily/weekly/monthly)")
    trending_language: RepositoryLanguage = Field(description="Language filter applied")
    
    # RSS feed metadata
    rss_title: str | None = Field(default=None, description="RSS feed entry title")
    rss_link: str | None = Field(default=None, description="RSS feed entry link")
    rss_published: datetime | None = Field(default=None, description="RSS entry publication date")
    rss_summary: str | None = Field(default=None, description="RSS entry summary/description")
    
    # Source tracking
    source: str = Field(default="github_trending_rss", description="Data source identifier")
    source_url: str | None = Field(default=None, description="Original RSS feed URL")
    
    @field_validator("topics", mode="before")
    @classmethod
    def parse_topics(cls, v: Any) -> list[str]:
        """Parse topics from various formats."""
        if isinstance(v, str):
            # Handle comma-separated topics
            return [topic.strip() for topic in v.split(",") if topic.strip()]
        elif isinstance(v, list):
            return [str(topic).strip() for topic in v if str(topic).strip()]
        return []
    
    @field_validator("repository_created_at", "repository_updated_at", "pushed_at", "rss_published", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime | None:
        """Parse datetime fields from various formats."""
        if v is None:
            return None
        
        if isinstance(v, datetime):
            return v
        
        if isinstance(v, str):
            # Try to parse ISO format datetime
            try:
                # Remove timezone suffix if present and parse
                if v.endswith('Z'):
                    v = v[:-1] + '+00:00'
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                # Try other common formats
                try:
                    return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    try:
                        return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        return None
        
        return None
    
    def get_trending_display_name(self) -> str:
        """Get display name for trending category."""
        period_map = {
            TrendingPeriod.DAILY: "Daily",
            TrendingPeriod.WEEKLY: "Weekly", 
            TrendingPeriod.MONTHLY: "Monthly"
        }
        
        language_map = {
            RepositoryLanguage.ALL: "All Languages",
            RepositoryLanguage.PYTHON: "Python",
            RepositoryLanguage.JUPYTER_NOTEBOOK: "Jupyter Notebook",
            RepositoryLanguage.CUDA: "CUDA",
            RepositoryLanguage.HCL: "Terraform (HCL)"
        }
        
        period_name = period_map.get(self.trending_period, self.trending_period)
        language_name = language_map.get(self.trending_language, self.trending_language)
        
        return f"{period_name} - {language_name}"
    
    def to_dashboard_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for dashboard display."""
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description or "No description available",
            "url": self.html_url,
            "language": self.language or "Unknown",
            "stars": self.stars_count,
            "forks": self.forks_count,
            "owner": self.owner.login if self.owner else "Unknown",
            "owner_type": self.owner.type if self.owner else "Unknown",
            "topics": self.topics,
            "license": self.license_name,
            "trending_category": self.get_trending_display_name(),
            "trending_period": self.trending_period,
            "trending_language": self.trending_language,
            "created_at": self.repository_created_at.isoformat() if self.repository_created_at else None,
            "updated_at": self.repository_updated_at.isoformat() if self.repository_updated_at else None,
            "fetched_at": self.created_at.isoformat(),
            "rss_published": self.rss_published.isoformat() if self.rss_published else None,
        }


class GitHubTrendingFeed(BaseModel):
    """Model for GitHub trending RSS feed configuration."""
    
    name: str = Field(description="Feed display name")
    url: str = Field(description="RSS feed URL")
    period: TrendingPeriod = Field(description="Trending period")
    language: RepositoryLanguage = Field(description="Programming language filter")
    description: str | None = Field(default=None, description="Feed description")
    
    def get_output_filename(self) -> str:
        """Get standardized output filename for this feed."""
        lang_part = self.language.replace("-", "_")
        return f"github_trending_{self.period}_{lang_part}.json"