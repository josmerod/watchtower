"""Data models for technology adoption analysis and intelligence."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field, field_validator

from src.models.base import TimestampedModel


class TrendDirection(str, Enum):
    """Technology trend direction enumeration."""

    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    EXPLOSIVE = "explosive"
    STAGNANT = "stagnant"


class TechnologyCategory(str, Enum):
    """Technology category enumeration."""

    FRONTEND = "frontend"
    BACKEND = "backend"
    MOBILE = "mobile"
    ML = "ml"
    DATABASE = "database"
    DEVOPS = "devops"
    SECURITY = "security"
    CLOUD = "cloud"
    TESTING = "testing"
    GENERAL = "general"


class MaturityLevel(str, Enum):
    """Technology maturity level enumeration."""

    EXPERIMENTAL = "experimental"
    EMERGING = "emerging"
    MATURE = "mature"
    ESTABLISHED = "established"
    LEGACY = "legacy"


class AdoptionLevel(str, Enum):
    """Technology adoption level enumeration."""

    NICHE = "niche"
    GROWING = "growing"
    MAINSTREAM = "mainstream"
    DOMINANT = "dominant"
    DECLINING = "declining"


class TechnologyMetrics(BaseModel):
    """Model for technology metrics from various sources."""

    github_stars: int | None = Field(
        default=None, ge=0, description="GitHub stars count"
    )
    github_forks: int | None = Field(
        default=None, ge=0, description="GitHub forks count"
    )
    github_issues: int | None = Field(
        default=None, ge=0, description="GitHub open issues"
    )
    stackoverflow_questions: int | None = Field(
        default=None, ge=0, description="StackOverflow questions"
    )
    npm_downloads: int | None = Field(
        default=None, ge=0, description="NPM weekly downloads"
    )
    pypi_downloads: int | None = Field(
        default=None, ge=0, description="PyPI monthly downloads"
    )
    job_postings: int | None = Field(
        default=None, ge=0, description="Job postings count"
    )
    dev_mentions: int | None = Field(
        default=None, ge=0, description="DEV community mentions"
    )
    conference_mentions: int | None = Field(
        default=None, ge=0, description="Conference mentions"
    )
    tutorial_count: int | None = Field(
        default=None, ge=0, description="Tutorial/course count"
    )

    @computed_field
    @property
    def total_activity_score(self) -> float:
        """Calculate total activity score from all metrics."""
        score = 0.0
        weights = {
            "github_stars": 0.3,
            "stackoverflow_questions": 0.2,
            "job_postings": 0.25,
            "dev_mentions": 0.15,
            "npm_downloads": 0.1,
        }

        for metric, weight in weights.items():
            value = getattr(self, metric)
            if value is not None:
                # Normalize large numbers
                normalized_value = (
                    min(value / 10000, 1.0)
                    if metric in ["npm_downloads", "github_stars"]
                    else min(value / 1000, 1.0)
                )
                score += normalized_value * weight

        return round(score * 100, 2)


class TechnologyModel(TimestampedModel):
    """Model for technology information and analytics."""

    # Core information
    name: str = Field(..., description="Technology name")
    display_name: str | None = Field(default=None, description="Display name")
    description: str | None = Field(default=None, description="Technology description")
    official_website: str | None = Field(
        default=None, description="Official website URL"
    )
    documentation_url: str | None = Field(default=None, description="Documentation URL")

    # Classification
    category: TechnologyCategory = Field(description="Technology category")
    subcategory: str | None = Field(default=None, description="Technology subcategory")
    tags: list[str] = Field(default=[], description="Technology tags")

    # Release information
    first_release_date: datetime | None = Field(
        default=None, description="First release date"
    )
    latest_version: str | None = Field(default=None, description="Latest version")
    license: str | None = Field(default=None, description="License type")

    # Metrics
    metrics: TechnologyMetrics = Field(
        default_factory=TechnologyMetrics, description="Technology metrics"
    )

    # Analysis results
    popularity_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Popularity score (0-100)"
    )
    growth_rate: float = Field(default=0.0, description="Growth rate (-1.0 to +∞)")
    maturity_level: MaturityLevel = Field(
        default=MaturityLevel.EMERGING, description="Maturity level"
    )
    adoption_level: AdoptionLevel = Field(
        default=AdoptionLevel.NICHE, description="Adoption level"
    )
    trend_direction: TrendDirection = Field(
        default=TrendDirection.STABLE, description="Trend direction"
    )

    # Competitive analysis
    competitors: list[str] = Field(default=[], description="Competitor technologies")
    alternatives: list[str] = Field(default=[], description="Alternative technologies")

    # Learning and adoption
    learning_curve: str = Field(
        default="medium", description="Learning curve difficulty"
    )
    ecosystem_size: int = Field(default=0, ge=0, description="Ecosystem size score")
    community_health: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Community health score"
    )

    # Market intelligence
    job_market_demand: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Job market demand score"
    )
    salary_premium: float | None = Field(
        default=None, description="Salary premium percentage"
    )

    # Metadata
    last_analyzed: datetime = Field(
        default_factory=datetime.utcnow, description="Last analysis timestamp"
    )
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Analysis confidence score"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate technology name format."""
        if not v or not v.strip():
            raise ValueError("Technology name cannot be empty")
        return v.strip().lower()

    @computed_field
    @property
    def display_name_formatted(self) -> str:
        """Get formatted display name."""
        return self.display_name or self.name.title()

    @computed_field
    @property
    def age_in_years(self) -> float | None:
        """Calculate technology age in years."""
        if self.first_release_date:
            delta = datetime.utcnow() - self.first_release_date
            return round(delta.days / 365.25, 1)
        return None

    @computed_field
    @property
    def is_emerging(self) -> bool:
        """Check if technology is emerging (less than 3 years old)."""
        if self.age_in_years:
            return self.age_in_years < 3.0
        return False

    @computed_field
    @property
    def overall_score(self) -> float:
        """Calculate overall technology score."""
        weights = {
            "popularity_score": 0.3,
            "community_health": 0.2,
            "job_market_demand": 0.25,
            "ecosystem_size": 0.15,
            "growth_rate": 0.1,
        }

        score = 0.0
        normalized_growth = (
            max(0, min(self.growth_rate + 1, 2)) / 2 * 100
        )  # Normalize growth rate to 0-100
        normalized_ecosystem = (
            min(self.ecosystem_size / 100, 1) * 100
        )  # Normalize ecosystem size

        score += self.popularity_score * weights["popularity_score"]
        score += self.community_health * weights["community_health"]
        score += self.job_market_demand * weights["job_market_demand"]
        score += normalized_ecosystem * weights["ecosystem_size"]
        score += normalized_growth * weights["growth_rate"]

        return round(score, 2)


class TechnologyComparisonModel(BaseModel):
    """Model for technology comparison results."""

    technology_name: str = Field(..., description="Technology name")
    category: TechnologyCategory = Field(..., description="Technology category")

    # Comparison metrics
    popularity_score: float = Field(ge=0.0, le=100.0, description="Popularity score")
    growth_rate: float = Field(description="Growth rate")
    community_health: float = Field(
        ge=0.0, le=100.0, description="Community health score"
    )
    job_market_demand: float = Field(ge=0.0, le=100.0, description="Job market demand")
    learning_curve: str = Field(description="Learning curve difficulty")
    maturity_level: MaturityLevel = Field(description="Maturity level")
    ecosystem_size: int = Field(ge=0, description="Ecosystem size")
    performance_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Performance benchmark score"
    )

    # Ranking
    overall_rank: int = Field(ge=1, description="Overall ranking in category")

    # Strengths and weaknesses
    strengths: list[str] = Field(default=[], description="Technology strengths")
    weaknesses: list[str] = Field(default=[], description="Technology weaknesses")

    # Recommendation
    recommendation_score: float = Field(
        ge=0.0, le=100.0, description="Recommendation score"
    )
    use_cases: list[str] = Field(default=[], description="Recommended use cases")


class TechnologyPredictionModel(BaseModel):
    """Model for technology adoption predictions."""

    technology_name: str = Field(..., description="Technology name")

    # Current state
    current_score: float = Field(ge=0.0, le=100.0, description="Current adoption score")
    current_adoption_level: AdoptionLevel = Field(description="Current adoption level")

    # Predictions
    predicted_score: float = Field(
        ge=0.0, le=100.0, description="Predicted adoption score"
    )
    predicted_adoption_level: AdoptionLevel = Field(
        description="Predicted adoption level"
    )
    growth_rate: float = Field(description="Predicted growth rate")
    trend_direction: TrendDirection = Field(description="Predicted trend direction")

    # Timeline
    prediction_timeframe_months: int = Field(
        ge=1, le=36, description="Prediction timeframe in months"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Prediction confidence")

    # Analysis
    key_drivers: list[str] = Field(default=[], description="Key growth drivers")
    risk_factors: list[str] = Field(default=[], description="Risk factors")
    recommendation: str = Field(description="Adoption recommendation")

    # Market intelligence
    early_adoption_indicators: list[str] = Field(
        default=[], description="Early adoption indicators"
    )
    competitive_threats: list[str] = Field(
        default=[], description="Competitive threats"
    )

    @computed_field
    @property
    def expected_growth_percentage(self) -> float:
        """Calculate expected growth percentage."""
        if self.current_score > 0:
            return round(
                ((self.predicted_score - self.current_score) / self.current_score)
                * 100,
                1,
            )
        return 0.0

    @computed_field
    @property
    def investment_recommendation(self) -> str:
        """Generate investment recommendation based on prediction."""
        if self.confidence < 0.6:
            return "Monitor - Low confidence prediction"
        elif self.growth_rate > 0.5 and self.confidence > 0.8:
            return "Strong Buy - High growth potential with good confidence"
        elif self.growth_rate > 0.2 and self.confidence > 0.7:
            return "Buy - Moderate growth with good confidence"
        elif self.growth_rate > 0.0:
            return "Hold - Stable growth expected"
        else:
            return "Sell - Declining trend predicted"


class FrameworkBattleModel(BaseModel):
    """Model for framework battle results."""

    category: TechnologyCategory = Field(..., description="Framework category")
    battle_date: datetime = Field(
        default_factory=datetime.utcnow, description="Battle analysis date"
    )

    # Battle participants
    frameworks: list[TechnologyComparisonModel] = Field(
        ..., description="Frameworks in battle"
    )

    # Battle results
    winner: str = Field(..., description="Current battle winner")
    runner_up: str = Field(..., description="Runner-up framework")
    rising_star: str | None = Field(
        default=None, description="Fastest growing framework"
    )

    # Market insights
    market_share_leader: str = Field(..., description="Market share leader")
    developer_preference: str = Field(..., description="Developer preference leader")
    enterprise_adoption: str = Field(..., description="Enterprise adoption leader")

    # Predictions
    predicted_winner_6m: str = Field(..., description="Predicted winner in 6 months")
    predicted_winner_12m: str = Field(..., description="Predicted winner in 12 months")

    # Analysis metadata
    confidence_score: float = Field(ge=0.0, le=1.0, description="Analysis confidence")
    data_quality_score: float = Field(ge=0.0, le=1.0, description="Data quality score")

    @computed_field
    @property
    def total_frameworks(self) -> int:
        """Get total number of frameworks in battle."""
        return len(self.frameworks)

    @computed_field
    @property
    def battle_summary(self) -> str:
        """Generate battle summary."""
        return f"{self.category.value.title()} Battle: {self.winner} leads with {self.runner_up} as runner-up"
