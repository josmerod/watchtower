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
    # Original formatted date string from the site, or parsed datetime
    published_at: datetime | None = None
