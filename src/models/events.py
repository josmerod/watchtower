"""Data models for tech events and conference intelligence."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import Field, HttpUrl, computed_field, field_validator

from models.base import TimestampedModel


class EventType(str, Enum):
    """Technology event type enumeration."""

    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    MEETUP = "meetup"
    WEBINAR = "webinar"
    HACKATHON = "hackathon"
    BOOTCAMP = "bootcamp"
    SUMMIT = "summit"
    FESTIVAL = "festival"


class EventFormat(str, Enum):
    """Event format enumeration."""

    IN_PERSON = "in_person"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class EventStatus(str, Enum):
    """Event status enumeration."""

    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class SpeakerModel(TimestampedModel):
    """Model for event speakers."""

    name: str = Field(description="Speaker name")
    title: str | None = Field(default=None, description="Speaker title/position")
    company: str | None = Field(default=None, description="Speaker company")
    bio: str | None = Field(default=None, description="Speaker biography")

    # Social media and links
    twitter_handle: str | None = Field(default=None, description="Twitter handle")
    linkedin_url: HttpUrl | None = Field(default=None, description="LinkedIn profile")
    website_url: HttpUrl | None = Field(default=None, description="Personal website")
    github_handle: str | None = Field(default=None, description="GitHub handle")

    # Speaker metrics
    influence_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Speaker influence score"
    )
    expertise_areas: list[str] = Field(default=[], description="Areas of expertise")
    speaking_experience: int | None = Field(
        default=None, ge=0, description="Years of speaking experience"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate speaker name."""
        if not v or not v.strip():
            raise ValueError("Speaker name cannot be empty")
        return v.strip()


class VenueModel(TimestampedModel):
    """Model for event venues."""

    name: str = Field(description="Venue name")
    address: str | None = Field(default=None, description="Venue address")
    city: str | None = Field(default=None, description="City")
    country: str | None = Field(default=None, description="Country")
    venue_type: str | None = Field(default=None, description="Type of venue")

    # Venue details
    capacity: int | None = Field(default=None, ge=0, description="Venue capacity")
    accessibility_features: list[str] = Field(
        default=[], description="Accessibility features"
    )
    amenities: list[str] = Field(default=[], description="Venue amenities")

    # Location coordinates
    latitude: float | None = Field(default=None, description="Latitude")
    longitude: float | None = Field(default=None, description="Longitude")

    # Links
    website_url: HttpUrl | None = Field(default=None, description="Venue website")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate venue name."""
        if not v or not v.strip():
            raise ValueError("Venue name cannot be empty")
        return v.strip()


class TechEventModel(TimestampedModel):
    """Model for technology events and conferences."""

    # Core event information
    name: str = Field(description="Event name")
    description: str | None = Field(default=None, description="Event description")
    event_type: EventType = Field(description="Type of event")
    format: EventFormat = Field(description="Event format")
    status: EventStatus = Field(
        default=EventStatus.UPCOMING, description="Event status"
    )

    # Date and time information
    start_date: datetime = Field(description="Event start date")
    end_date: datetime | None = Field(default=None, description="Event end date")
    timezone: str | None = Field(default=None, description="Event timezone")
    duration_hours: float | None = Field(
        default=None, ge=0, description="Event duration in hours"
    )

    # Location information
    venue: VenueModel | None = Field(default=None, description="Event venue")
    location: str | None = Field(
        default=None, description="Event location (if different from venue)"
    )
    is_virtual: bool = Field(default=False, description="Whether event is virtual")
    virtual_platform: str | None = Field(
        default=None, description="Virtual platform used"
    )

    # Event content
    topics: list[str] = Field(default=[], description="Event topics")
    technologies: list[str] = Field(default=[], description="Technologies covered")
    target_audience: list[str] = Field(default=[], description="Target audience")
    difficulty_level: str | None = Field(default=None, description="Difficulty level")

    # Speakers and organizers
    speakers: list[SpeakerModel] = Field(default=[], description="Event speakers")
    organizer: str | None = Field(default=None, description="Event organizer")
    organizer_website: HttpUrl | None = Field(
        default=None, description="Organizer website"
    )

    # Registration and costs
    registration_url: HttpUrl | None = Field(
        default=None, description="Registration URL"
    )
    registration_deadline: datetime | None = Field(
        default=None, description="Registration deadline"
    )
    registration_required: bool = Field(
        default=True, description="Whether registration is required"
    )
    estimated_cost: float | None = Field(
        default=None, ge=0, description="Estimated cost in USD"
    )
    is_free: bool = Field(default=False, description="Whether event is free")

    # Event intelligence scores
    speaker_influence_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Overall speaker influence"
    )
    relevance_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Topic relevance score"
    )
    networking_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Networking potential score"
    )
    roi_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Return on investment score"
    )
    quality_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Overall quality score"
    )

    # Social and engagement
    attendee_count: int | None = Field(
        default=None, ge=0, description="Expected/actual attendee count"
    )
    social_media_buzz: float | None = Field(
        default=None, ge=0, description="Social media buzz score"
    )
    hashtags: list[str] = Field(default=[], description="Event hashtags")

    # Links and resources
    website_url: HttpUrl | None = Field(default=None, description="Event website")
    agenda_url: HttpUrl | None = Field(default=None, description="Event agenda URL")
    live_stream_url: HttpUrl | None = Field(default=None, description="Live stream URL")
    recording_url: HttpUrl | None = Field(
        default=None, description="Recording URL (post-event)"
    )

    # Data source information
    source_name: str = Field(description="Data source name")
    source_url: HttpUrl | None = Field(default=None, description="Source URL")
    source_id: str | None = Field(default=None, description="Source-specific ID")

    # Additional metadata
    tags: list[str] = Field(default=[], description="Event tags")
    categories: list[str] = Field(default=[], description="Event categories")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate event name."""
        if not v or not v.strip():
            raise ValueError("Event name cannot be empty")
        return v.strip()

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: datetime | None, info) -> datetime | None:
        """Validate end date is after start date."""
        if v and hasattr(info, "data") and "start_date" in info.data:
            start_date = info.data["start_date"]
            if v < start_date:
                raise ValueError("End date must be after start date")
        return v

    @computed_field
    @property
    def is_upcoming(self) -> bool:
        """Check if event is upcoming."""
        return self.start_date > datetime.utcnow()

    @computed_field
    @property
    def is_ongoing(self) -> bool:
        """Check if event is currently ongoing."""
        now = datetime.utcnow()
        if self.end_date:
            return self.start_date <= now <= self.end_date
        else:
            # If no end date, consider ongoing for 24 hours
            return self.start_date <= now <= (self.start_date + timedelta(hours=24))

    @computed_field
    @property
    def days_until_event(self) -> int:
        """Calculate days until event starts."""
        if self.is_upcoming:
            delta = self.start_date - datetime.utcnow()
            return delta.days
        return 0

    @computed_field
    @property
    def is_high_quality(self) -> bool:
        """Check if event is considered high quality."""
        return (
            self.quality_score >= 75.0
            and self.speaker_influence_score >= 60.0
            and len(self.speakers) > 0
        )

    @computed_field
    @property
    def registration_status(self) -> str:
        """Get registration status."""
        if not self.registration_required:
            return "no_registration_required"
        if not self.registration_deadline:
            return "open"

        now = datetime.utcnow()
        if now > self.registration_deadline:
            return "closed"
        elif (self.registration_deadline - now).days <= 7:
            return "closing_soon"
        else:
            return "open"


class EventRecommendationModel(TimestampedModel):
    """Model for event recommendations."""

    event: TechEventModel = Field(description="Recommended event")
    recommendation_score: float = Field(
        ge=0.0, le=100.0, description="Recommendation score"
    )
    recommendation_reason: str = Field(description="Why this event is recommended")

    # Matching factors
    interest_match: float = Field(ge=0.0, le=1.0, description="Interest match score")
    location_convenience: float = Field(
        ge=0.0, le=1.0, description="Location convenience score"
    )
    budget_fit: float = Field(ge=0.0, le=1.0, description="Budget fit score")
    schedule_compatibility: float = Field(
        ge=0.0, le=1.0, description="Schedule compatibility score"
    )

    # Additional insights
    key_benefits: list[str] = Field(default=[], description="Key benefits of attending")
    potential_connections: list[str] = Field(
        default=[], description="Potential networking connections"
    )
    learning_outcomes: list[str] = Field(
        default=[], description="Expected learning outcomes"
    )

    @computed_field
    @property
    def is_highly_recommended(self) -> bool:
        """Check if event is highly recommended."""
        return self.recommendation_score >= 80.0


class UserEventPreferencesModel(TimestampedModel):
    """Model for user event preferences."""

    user_id: str = Field(description="User identifier")

    # Interest preferences
    preferred_topics: list[str] = Field(default=[], description="Preferred topics")
    preferred_technologies: list[str] = Field(
        default=[], description="Preferred technologies"
    )
    preferred_event_types: list[EventType] = Field(
        default=[], description="Preferred event types"
    )
    preferred_formats: list[EventFormat] = Field(
        default=[], description="Preferred formats"
    )

    # Location and travel preferences
    preferred_locations: list[str] = Field(
        default=[], description="Preferred locations"
    )
    max_travel_distance: int | None = Field(
        default=None, ge=0, description="Max travel distance in km"
    )
    willing_to_travel: bool = Field(
        default=True, description="Willing to travel for events"
    )

    # Budget and time preferences
    max_budget: float | None = Field(
        default=None, ge=0, description="Maximum budget per event"
    )
    preferred_duration_min: int | None = Field(
        default=None, ge=0, description="Minimum event duration in hours"
    )
    preferred_duration_max: int | None = Field(
        default=None, ge=0, description="Maximum event duration in hours"
    )

    # Experience level and goals
    experience_level: str | None = Field(default=None, description="Experience level")
    learning_goals: list[str] = Field(default=[], description="Learning goals")
    networking_interests: list[str] = Field(
        default=[], description="Networking interests"
    )

    # Scheduling preferences
    preferred_days_of_week: list[str] = Field(
        default=[], description="Preferred days of week"
    )
    preferred_times: list[str] = Field(default=[], description="Preferred times of day")
    exclude_holidays: bool = Field(default=True, description="Exclude holidays")

    # Notification preferences
    notification_lead_time: int = Field(
        default=30, ge=1, description="Notification lead time in days"
    )
    enable_recommendations: bool = Field(
        default=True, description="Enable event recommendations"
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user ID."""
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v.strip()
