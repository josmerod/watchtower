"""Data models for Software Architecture Patterns Intelligence."""

from __future__ import annotations

from enum import Enum

from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel


class ArchitecturalStyle(str, Enum):
    """Architectural style categories."""

    MICROSERVICES = "Microservices"
    EVENT_DRIVEN = "Event-Driven"
    SERVERLESS = "Serverless"
    MONOLITH = "Monolithic"
    LAYERED = "Layered"
    HEXAGONAL = "Hexagonal"
    CQRS = "CQRS"
    SERVICE_ORIENTED = "Service-Oriented"
    PEER_TO_PEER = "Peer-to-Peer"
    SPACE_BASED = "Space-Based"


class TeamSize(str, Enum):
    """Team size categories."""

    SOLO = "Solo"
    SMALL = "Small (2-5)"
    MEDIUM = "Medium (6-20)"
    LARGE = "Large (20+)"


class ComplexityLevel(str, Enum):
    """Pattern complexity levels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class ArchitecturePattern(TimestampedModel):
    """Model for software architecture patterns."""

    # Identity
    pattern_id: str = Field(description="Unique pattern identifier")
    name: str = Field(description="Pattern name")
    style: ArchitecturalStyle = Field(description="Architectural style category")

    # Core Information
    description: str = Field(description="Pattern description")
    summary: str = Field(default="", description="One-line summary")

    # Use Case Guidance
    when_to_use: list[str] = Field(default=[], description="Scenarios where pattern is appropriate")
    when_not_to_use: list[str] = Field(default=[], description="Scenarios where pattern should be avoided")

    # Benefits & Trade-offs
    benefits: list[str] = Field(default=[], description="Key benefits of the pattern")
    trade_offs: list[str] = Field(default=[], description="Trade-offs and challenges")

    # Implementation
    implementation_guidance: list[str] = Field(default=[], description="Step-by-step implementation guidance")
    best_practices: list[str] = Field(default=[], description="Best practices to follow")
    common_pitfalls: list[str] = Field(default=[], description="Common mistakes to avoid")

    # Technology
    compatible_technologies: list[str] = Field(default=[], description="Technologies commonly used with this pattern")
    required_technologies: list[str] = Field(default=[], description="Technologies required for this pattern")

    # Requirements
    recommended_team_size: TeamSize | None = Field(default=None, description="Recommended team size for this pattern")
    complexity: ComplexityLevel = Field(default=ComplexityLevel.MEDIUM, description="Implementation complexity")
    scalability_level: str = Field(
        default="Medium",
        description="Scalability characteristics (Low, Medium, High, Very High)",
    )

    # Examples
    real_world_examples: list[str] = Field(default=[], description="Companies/projects using this pattern")
    example_urls: list[HttpUrl] = Field(default=[], description="Links to example implementations")

    # References
    reference_urls: list[HttpUrl] = Field(default=[], description="Links to detailed articles/documentation")

    # Metadata
    tags: list[str] = Field(default=[], description="Additional tags for categorization")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "pattern_id": "microservices",
                    "name": "Microservices Architecture",
                    "style": "Microservices",
                    "description": "Decompose application into small, independent services",
                    "summary": "Independent, deployable services communicating via APIs",
                    "when_to_use": ["Large teams", "Need independent deployment"],
                    "benefits": ["Independent deployment", "Technology diversity"],
                    "compatible_technologies": ["Docker", "Kubernetes", "REST", "gRPC"],
                    "recommended_team_size": "Medium (6-20)",
                    "complexity": "High",
                    "real_world_examples": ["Netflix", "Amazon", "Uber"],
                }
            ]
        }
