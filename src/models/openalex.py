"""Models for OpenAlex (Open Academic and Scholarly Works).

Part of Phase 2 ETL implementation for academic research aggregation.
Includes 200M+ works, 50M+ authors, 80K+ venues, 50K+ concepts.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.models.base import TimestampedModel


class WorkType(str, Enum):
    """Types of academic works."""

    JOURNAL_ARTICLE = "journal-article"
    BOOK = "book"
    BOOK_CHAPTER = "book-chapter"
    DISSERTATION = "dissertation"
    PREPRINT = "preprint"
    REPORT = "report"
    PATENT = "patent"
    DATASET = "dataset"
    OTHER = "other"


class OpenAlexWorkModel(TimestampedModel):
    """Model for an OpenAlex work (academic paper/publication).

    Represents one of 200M+ scholarly works from OpenAlex.
    """

    # Core work fields
    work_id: str = Field(description="OpenAlex work ID")
    title: str = Field(description="Work title")
    type: WorkType = Field(description="Work type")
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    url: str | None = Field(default=None, description="Work URL")

    # Publication venue
    venue_id: str | None = Field(default=None, description="Venue ID")
    venue_name: str | None = Field(default=None, description="Venue/journal name")
    venue_issn: str | None = Field(default=None, description="Venue ISSN")
    publisher: str | None = Field(default=None, description="Publisher name")

    # Authors
    author_ids: list[str] = Field(default_factory=list, description="Author institution IDs")
    authors_count: int = Field(default=0, ge=0, description="Number of authors")

    # Citations and metrics
    citations_count: int = Field(default=0, ge=0, description="Number of citations")
    h_index: int | None = Field(default=None, ge=0, description="H-index")
    impact_factor: float | None = Field(default=None, description="Impact factor")

    # Year and date
    publication_year: int | None = Field(default=None, ge=1900, le=2100, description="Publication year")
    publication_date: datetime | None = Field(default=None, description="Publication date")

    # Abstract and concepts
    abstract: str | None = Field(default=None, description="Abstract text")
    concepts: list[str] = Field(default_factory=list, description="Research concepts/tags")

    # Open Access
    is_oa: bool = Field(default=False, description="Is open access")
    oa_url: str | None = Field(default=None, description="Open access URL")

    # Language
    language: str | None = Field(default=None, description="Work language (ISO 639-1)")

    # Scrape timestamp
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Source database
    source: str = Field(default="openalex", description="Source database")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Full API data")

    @property
    def age_years(self) -> int | None:
        """Calculate work age in years.

        Returns:
            Age in years or None.
        """
        if self.publication_year:
            return datetime.utcnow().year - self.publication_year
        return None

    @property
    def is_highly_cited(self) -> bool:
        """Check if work is highly cited.

        Returns:
            True if citations > 100.
        """
        return self.citations_count > 100

    @property
    def citations_per_year(self) -> float | None:
        """Calculate citations per year.

        Returns:
            Citations per year or None.
        """
        if self.publication_year and self.citations_count > 0:
            age = max(1, datetime.utcnow().year - self.publication_year)
            return self.citations_count / age
        return None


class OpenAlexAuthorModel(TimestampedModel):
    """Model for an OpenAlex author (researcher).

    Represents one of 50M+ academic authors.
    """

    # Core author fields
    author_id: str = Field(description="OpenAlex author ID")
    name: str = Field(description="Author name")
    orcid: str | None = Field(default=None, description="ORCID identifier")
    url: str | None = Field(default=None, description="Author URL")

    # Institution
    institution_id: str | None = Field(default=None, description="Primary institution ID")
    institution_name: str | None = Field(default=None, description="Primary institution name")

    # Metrics
    works_count: int = Field(default=0, ge=0, description="Number of works")
    citations_count: int = Field(default=0, ge=0, description="Total citations")
    h_index: int | None = Field(default=None, ge=0, description="H-index")

    # Research interests
    concepts: list[str] = Field(default_factory=list, description="Research concepts")

    # Last known work
    last_work_id: str | None = Field(default=None, description="Last known work ID")
    last_work_year: int | None = Field(default=None, description="Last publication year")

    # Scrape timestamp
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional data")


class OpenAlexVenueModel(TimestampedModel):
    """Model for an OpenAlex venue (journal/conference).

    Represents one of 80K+ academic venues.
    """

    # Core venue fields
    venue_id: str = Field(description="OpenAlex venue ID")
    name: str = Field(description="Venue name")
    type: str | None = Field(default=None, description="Venue type (journal, conference, etc.)")
    url: str | None = Field(default=None, description="Venue URL")

    # Identifiers
    issn: str | None = Field(default=None, description="ISSN (print)")
    issn_l: str | None = Field(default=None, description="ISSN (online)")

    # Metrics
    works_count: int = Field(default=0, ge=0, description="Number of works")
    citations_count: int = Field(default=0, ge=0, description="Total citations")
    h_index: int | None = Field(default=None, ge=0, description="H-index")
    impact_factor: float | None = Field(default=None, description="Impact factor")

    # Publisher
    publisher_id: str | None = Field(default=None, description="Publisher ID")
    publisher_name: str | None = Field(default=None, description="Publisher name")

    # Subject areas
    subjects: list[str] = Field(default_factory=list, description="Subject areas")

    # Scrape timestamp
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")

    # Identifiers
    original_id: str = Field(description="Original unique identifier")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional data")


class OpenAlexMetricsModel(TimestampedModel):
    """Model for OpenAlex ETL metrics."""

    # API request metrics
    successful_requests: int = Field(default=0, description="Successful API requests")
    failed_requests: int = Field(default=0, description="Failed API requests")

    # Discovery metrics
    total_works_discovered: int = Field(default=0, description="Total works discovered")
    total_authors_discovered: int = Field(default=0, description="Total authors discovered")
    total_venues_discovered: int = Field(default=0, description="Total venues discovered")

    # Type distribution
    work_type_distribution: dict[str, int] = Field(default_factory=dict, description="Works by type")

    # Subject metrics
    subject_distribution: dict[str, int] = Field(default_factory=dict, description="Works by subject")

    # Citation metrics
    total_citations: int = Field(default=0, description="Total citations across all works")
    avg_citations_per_work: float | None = Field(default=None, description="Average citations")
    highly_cited_works: int = Field(default=0, description="Works with >100 citations")

    # Open Access metrics
    oa_works: int = Field(default=0, description="Open access works")

    # Year distribution
    year_distribution: dict[str, int] = Field(default_factory=dict, description="Works by year")

    # Extended metadata
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metrics")
