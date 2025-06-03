"""Data models for ArXiv papers and research intelligence."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, HttpUrl, computed_field, field_validator

from src.models.base import TimestampedModel


class TechnologyReadinessLevel(int, Enum):
    """Technology Readiness Level (TRL) enumeration."""

    TRL_1 = 1  # Basic principles observed
    TRL_2 = 2  # Technology concept formulated
    TRL_3 = 3  # Experimental proof of concept
    TRL_4 = 4  # Technology validated in lab
    TRL_5 = 5  # Technology validated in relevant environment
    TRL_6 = 6  # Technology demonstrated in relevant environment
    TRL_7 = 7  # System prototype demonstration in operational environment
    TRL_8 = 8  # System complete and qualified
    TRL_9 = 9  # Actual system proven in operational environment


class ResearchCategory(str, Enum):
    """Research category classification."""

    # AI and Machine Learning
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    NEURAL_NETWORKS = "neural_networks"
    NATURAL_LANGUAGE_PROCESSING = "natural_language_processing"
    COMPUTER_VISION = "computer_vision"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    GENERATIVE_AI = "generative_ai"

    # Software Engineering
    SOFTWARE_ENGINEERING = "software_engineering"
    SOFTWARE_ARCHITECTURE = "software_architecture"
    SOFTWARE_TESTING = "software_testing"
    DEVOPS = "devops"
    MICROSERVICES = "microservices"
    API_DESIGN = "api_design"

    # Data Engineering
    DATA_ENGINEERING = "data_engineering"
    BIG_DATA = "big_data"
    DATA_PIPELINES = "data_pipelines"
    DATA_WAREHOUSING = "data_warehousing"
    STREAM_PROCESSING = "stream_processing"

    # Architecture
    SOLUTION_ARCHITECTURE = "solution_architecture"
    ENTERPRISE_ARCHITECTURE = "enterprise_architecture"
    CLOUD_ARCHITECTURE = "cloud_architecture"
    DISTRIBUTED_SYSTEMS = "distributed_systems"
    SYSTEM_DESIGN = "system_design"

    # Other Tech Areas
    CYBERSECURITY = "cybersecurity"
    BLOCKCHAIN = "blockchain"
    QUANTUM_COMPUTING = "quantum_computing"
    IOT = "internet_of_things"
    EDGE_COMPUTING = "edge_computing"

    # Research Types
    THEORETICAL = "theoretical"
    EMPIRICAL = "empirical"
    SURVEY = "survey"
    BENCHMARK = "benchmark"


class CommercialPotential(str, Enum):
    """Commercial potential assessment."""

    HIGH = "high"  # Ready for commercialization or high market demand
    MEDIUM = "medium"  # Moderate commercial potential
    LOW = "low"  # Limited commercial applicability
    RESEARCH = "research"  # Pure research, no immediate commercial value


class GitHubRepositoryModel(TimestampedModel):
    """Model for GitHub repository information."""

    html_url: HttpUrl | None = Field(default=None, description="GitHub repository URL")
    description: str | None = Field(default=None, description="Repository description")
    stars: int | None = Field(default=None, ge=0, description="Number of stars")
    forks: int | None = Field(default=None, ge=0, description="Number of forks")
    watchers: int | None = Field(default=None, ge=0, description="Number of watchers")
    open_issues: int | None = Field(
        default=None, ge=0, description="Number of open issues"
    )
    last_updated: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    created_at: datetime | None = Field(
        default=None, description="Repository creation timestamp"
    )
    language: str | None = Field(default=None, description="Primary language")
    languages: dict[str, int] | None = Field(
        default=None, description="Language breakdown"
    )
    topics: list[str] = Field(default=[], description="Repository topics")
    has_issues: bool | None = Field(default=None, description="Has issues enabled")
    has_projects: bool | None = Field(default=None, description="Has projects enabled")
    has_wiki: bool | None = Field(default=None, description="Has wiki enabled")
    has_pages: bool | None = Field(default=None, description="Has GitHub Pages enabled")
    default_branch: str | None = Field(default=None, description="Default branch name")


class PapersWithCodeModel(TimestampedModel):
    """Model for Papers With Code integration data."""

    pwc_id: str | None = Field(default=None, description="Papers With Code ID")
    pwc_url: HttpUrl | None = Field(default=None, description="Papers With Code URL")
    pwc_title: str | None = Field(default=None, description="Papers With Code title")
    proceeding: str | None = Field(default=None, description="Conference or journal")
    repositories: list[dict[str, str]] = Field(
        default=[], description="Associated repositories"
    )
    datasets: list[dict[str, str]] = Field(
        default=[], description="Associated datasets"
    )
    tasks_and_metrics: list[dict[str, str]] = Field(
        default=[], description="Tasks and performance metrics"
    )
    methods: list[str] = Field(default=[], description="Methods used in the paper")


class ArxivPaperModel(TimestampedModel):
    """Base model for ArXiv papers."""

    # Core paper information
    arxiv_id: str = Field(description="ArXiv paper ID")
    title: str = Field(description="Paper title")
    authors: list[str] = Field(description="List of authors")
    categories: list[str] = Field(description="ArXiv categories")
    summary: str = Field(description="Paper abstract/summary")

    # Publication information
    published: datetime = Field(description="Publication date")
    updated: datetime = Field(description="Last update date")
    link: HttpUrl = Field(description="ArXiv link")
    pdf_url: HttpUrl | None = Field(default=None, description="PDF download URL")
    comment: str | None = Field(default=None, description="Author comments")

    # Processing metadata
    processed_date: datetime = Field(
        default_factory=datetime.utcnow, description="When this paper was processed"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate and clean title."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """Validate and clean summary."""
        if not v or not v.strip():
            raise ValueError("Summary cannot be empty")
        return v.strip()


class EnhancedArxivPaperModel(ArxivPaperModel):
    """Enhanced ArXiv paper model with intelligence features."""

    # Classification and clustering
    cluster_id: int | None = Field(default=None, description="Cluster assignment ID")
    cluster_label: str | None = Field(
        default=None, description="Human-readable cluster label"
    )
    cluster_keywords: list[str] = Field(
        default=[], description="Keywords from cluster analysis"
    )
    extracted_keywords: list[str] = Field(
        default=[], description="Keywords extracted from paper"
    )
    research_categories: list[ResearchCategory] = Field(
        default=[], description="Research category classifications"
    )

    # Intelligence scoring
    industry_impact_score: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Calculated industry impact score (0-10)",
    )
    technology_readiness_level: TechnologyReadinessLevel | None = Field(
        default=None, description="Technology readiness level assessment"
    )
    commercial_potential: CommercialPotential = Field(
        default=CommercialPotential.RESEARCH,
        description="Commercial viability assessment",
    )
    innovation_score: float = Field(
        default=0.0, ge=0.0, le=10.0, description="Innovation potential score (0-10)"
    )

    # Technology and application analysis
    related_technologies: list[str] = Field(
        default=[], description="Related technologies mentioned"
    )
    potential_applications: list[str] = Field(
        default=[], description="Potential real-world applications"
    )
    technical_concepts: list[str] = Field(
        default=[], description="Key technical concepts"
    )
    methodologies: list[str] = Field(
        default=[], description="Research methodologies used"
    )

    # External integrations
    github_info: GitHubRepositoryModel | None = Field(
        default=None, description="GitHub repository information"
    )
    papers_with_code_info: PapersWithCodeModel | None = Field(
        default=None, description="Papers With Code information"
    )

    # Metrics and analytics
    citation_potential: float = Field(
        default=0.0, ge=0.0, le=10.0, description="Predicted citation potential (0-10)"
    )
    reproducibility_score: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Reproducibility assessment score (0-10)",
    )

    # Additional metadata
    quality_indicators: dict[str, float] = Field(
        default={}, description="Various quality indicators and their scores"
    )
    trends_alignment: dict[str, float] = Field(
        default={}, description="Alignment with current technology trends"
    )

    @computed_field
    @property
    def overall_significance_score(self) -> float:
        """Calculate overall significance score based on multiple factors."""
        weights = {
            "industry_impact": 0.3,
            "innovation": 0.25,
            "citation_potential": 0.2,
            "commercial_potential": 0.15,
            "reproducibility": 0.1,
        }

        commercial_score_map = {
            CommercialPotential.HIGH: 8.0,
            CommercialPotential.MEDIUM: 5.0,
            CommercialPotential.LOW: 2.0,
            CommercialPotential.RESEARCH: 0.0,
        }

        commercial_score = commercial_score_map.get(self.commercial_potential, 0.0)

        overall_score = (
            self.industry_impact_score * weights["industry_impact"]
            + self.innovation_score * weights["innovation"]
            + self.citation_potential * weights["citation_potential"]
            + commercial_score * weights["commercial_potential"]
            + self.reproducibility_score * weights["reproducibility"]
        )

        return round(overall_score, 2)

    @computed_field
    @property
    def is_breakthrough(self) -> bool:
        """Determine if this paper represents a potential breakthrough."""
        return (
            self.industry_impact_score >= 8.0
            or self.innovation_score >= 8.0
            or self.overall_significance_score >= 7.5
        )

    @computed_field
    @property
    def implementation_feasibility(self) -> str:
        """Assess implementation feasibility based on TRL and other factors."""
        if not self.technology_readiness_level:
            return "unknown"

        # Handle both enum and int values
        if isinstance(self.technology_readiness_level, TechnologyReadinessLevel):
            trl = self.technology_readiness_level.value
        else:
            trl = int(self.technology_readiness_level)

        if trl >= 7:
            return "ready_for_deployment"
        elif trl >= 5:
            return "prototype_ready"
        elif trl >= 3:
            return "experimental_stage"
        else:
            return "conceptual_stage"

    class Config:
        """Pydantic configuration."""

        json_encoders = {HttpUrl: lambda v: str(v), datetime: lambda v: v.isoformat()}

        json_schema_extra = {
            "examples": [
                {
                    "arxiv_id": "2403.12345",
                    "title": "Advanced Neural Architecture Search for Enterprise Applications",
                    "authors": ["John Doe", "Jane Smith"],
                    "categories": ["cs.LG", "cs.AI"],
                    "summary": "We present a novel neural architecture search method...",
                    "published": "2024-03-15T10:00:00Z",
                    "updated": "2024-03-15T10:00:00Z",
                    "link": "http://arxiv.org/abs/2403.12345",
                    "cluster_label": "Neural Architecture Search",
                    "industry_impact_score": 8.5,
                    "technology_readiness_level": 5,
                    "commercial_potential": "high",
                    "innovation_score": 7.8,
                    "related_technologies": [
                        "AutoML",
                        "Neural Networks",
                        "Deep Learning",
                    ],
                    "potential_applications": [
                        "Enterprise ML",
                        "Automated Model Design",
                    ],
                    "research_categories": [
                        "machine_learning",
                        "artificial_intelligence",
                    ],
                }
            ]
        }
