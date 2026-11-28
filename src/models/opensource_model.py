from datetime import datetime

from pydantic import Field

from src.models.base import AIEnhancedModel, TimestampedModel


class OpenSourceProjectItem(TimestampedModel, AIEnhancedModel):
    title: str
    description: str | None = None
    url: str
    source: str = "opensourceprojects.dev"
    tags: list[str] = Field(default_factory=list)
    stars_count: int | None = None
    forks_count: int | None = None
    # In UTC with its zone. A record written before 2026-11-28 has the site's clock (Madrid) without one.
    published_at: datetime | None = None
    # T-204 (2026-11-28): what the feed, the post page and the GitHub API add to a record.
    # The URL of the site's post about the repository
    post_url: str | None = None
    # Primary language and topics, from GitHub
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    last_push_at: datetime | None = None
    # Views of the post on the site
    views_count: int | None = None
    # Whether the opening of the article is already in the record
    detail_fetched: bool = False
    # When GitHub was last asked about the repository
    github_checked_at: datetime | None = None
