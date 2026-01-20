"""Models for Hashnode GraphQL API data sources.

Part of Phase 1 ETL implementation for developer blog aggregation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class HashnodePublicationType(str, Enum):
    """Types of Hashnode publications."""

    BLOG = "blog"
    NEWSLETTER = "newsletter"
    ORGANIZATION = "organization"


class HashnodePostModel(TimestampedModel):
    """Model for a Hashnode blog post.

    Represents a developer blog post from Hashnode's GraphQL API.
    """

    # Core post fields
    post_id: str = Field(description="Hashnode post ID")
    title: str = Field(description="Post title")
    slug: str = Field(description="Post URL slug")
    url: str = Field(description="Full post URL")
    content: str | None = Field(default=None, description="Post content/markdown")
    excerpt: str | None = Field(default=None, description="Post excerpt/summary")

    # Author information
    author_id: str = Field(description="Author ID")
    author_name: str = Field(description="Author display name")
    author_username: str = Field(description="Author username")
    author_bio: str | None = Field(default=None, description="Author biography")
    author_photo: str | None = Field(default=None, description="Author photo URL")

    # Publication/blog information
    publication_id: str | None = Field(default=None, description="Publication ID if part of one")
    publication_name: str | None = Field(default=None, description="Publication name")
    publication_domain: str | None = Field(default=None, description="Publication custom domain")
    publication_type: HashnodePublicationType | None = Field(default=None, description="Publication type")

    # Publication metadata
    published_at: datetime | None = Field(default=None, description="Publication timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When post was scraped")

    # Engagement metrics
    views_count: int = Field(default=0, ge=0, description="Number of views")
    reactions_count: int = Field(default=0, ge=0, description="Number of reactions")
    comments_count: int = Field(default=0, ge=0, description="Number of comments")

    # Cover image
    cover_image: str | None = Field(default=None, description="Cover image URL")

    # Classification
    tags: list[str] = Field(default_factory=list, description="Post tags")
    language: str = Field(default="en", description="Post language code")

    # Identifiers and deduplication
    original_id: str = Field(description="Original unique identifier")

    # Hashnode-specific fields
    brief: str | None = Field(default=None, description="Brief description")
    read_time_in_minutes: int | None = Field(default=None, ge=0, description="Estimated reading time")

    # SEO metadata
    seo_title: str | None = Field(default=None, description="SEO title")
    seo_description: str | None = Field(default=None, description="SEO description")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Full raw API response")

    @property
    def is_part_of_publication(self) -> bool:
        """Check if post is part of a publication.

        Returns:
            True if post belongs to a publication.
        """
        return self.publication_id is not None

    @property
    def engagement_score(self) -> int:
        """Calculate engagement score.

        Returns:
            Engagement score based on views, reactions, and comments.
        """
        return self.views_count + (self.reactions_count * 10) + (self.comments_count * 20)


class HashnodePublicationModel(TimestampedModel):
    """Model for a Hashnode publication (blog/community).

    Represents a developer blog hosted on Hashnode.
    """

    # Core publication fields
    publication_id: str = Field(description="Hashnode publication ID")
    name: str = Field(description="Publication name")
    slug: str = Field(description="Publication URL slug")
    url: str | None = Field(default=None, description="Publication URL")
    description: str | None = Field(default=None, description="Publication description")

    # Author/owner
    author_id: str | None = Field(default=None, description="Publication owner ID")
    author_name: str | None = Field(default=None, description="Publication owner name")

    # Publication metadata
    type: HashnodePublicationType = Field(description="Publication type")
    domain: str | None = Field(default=None, description="Custom domain")

    # Metrics
    followers_count: int = Field(default=0, ge=0, description="Number of followers")
    posts_count: int = Field(default=0, ge=0, description="Total number of posts")

    # Branding
    logo: str | None = Field(default=None, description="Publication logo URL")
    cover_image: str | None = Field(default=None, description="Publication cover image")

    # Classification
    tags: list[str] = Field(default_factory=list, description="Publication tags")

    # Status
    is_active: bool = Field(default=True, description="Whether publication is active")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional publication data")


class HashnodeAuthorModel(TimestampedModel):
    """Model for a Hashnode author.

    Represents a developer/blogger on Hashnode.
    """

    # Core author fields
    author_id: str = Field(description="Hashnode author ID")
    name: str = Field(description="Author display name")
    username: str = Field(description="Author username (handle)")
    url: str | None = Field(default=None, description="Author profile URL")

    # Author metadata
    bio: str | None = Field(default=None, description="Author biography")
    tagline: str | None = Field(default=None, description="Author tagline")
    location: str | None = Field(default=None, description="Author location")

    # Profile
    photo: str | None = Field(default=None, description="Author profile photo URL")

    # Social links
    website: str | None = Field(default=None, description="Personal website URL")
    github_username: str | None = Field(default=None, description="GitHub username")
    twitter_username: str | None = Field(default=None, description="Twitter/X username")

    # Metrics
    followers_count: int = Field(default=0, ge=0, description="Number of followers")
    posts_count: int = Field(default=0, ge=0, description="Total number of posts")

    # Publications
    publications: list[str] = Field(default_factory=list, description="Publication IDs author contributes to")

    # Status
    is_active: bool = Field(default=True, description="Whether author is active")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional author data")


class HashnodeMetricsModel(TimestampedModel):
    """Model for Hashnode ETL metrics."""

    # Discovery metrics
    total_posts_discovered: int = Field(default=0, description="Total posts discovered")
    new_posts_this_run: int = Field(default=0, description="New posts this run")
    total_authors_discovered: int = Field(default=0, description="Total authors discovered")
    total_publications_discovered: int = Field(default=0, description="Total publications discovered")

    # Engagement metrics
    avg_views: float | None = Field(default=None, description="Average views per post")
    total_engagement: int = Field(default=0, description="Total engagement score")

    # Content metrics
    total_read_time_minutes: int = Field(default=0, description="Total read time of all posts")
    avg_read_time: float | None = Field(default=None, description="Average read time")

    # Tag distribution
    popular_tags: dict[str, int] = Field(default_factory=dict, description="Tag frequency")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
