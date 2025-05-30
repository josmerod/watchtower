"""Data models for Watchtower."""

from src.models.arxiv import (
    ArxivPaperModel,
    CommercialPotential,
    EnhancedArxivPaperModel,
    GitHubRepositoryModel,
    PapersWithCodeModel,
    ResearchCategory,
    TechnologyReadinessLevel,
)
from src.models.base import (
    BaseModel,
    ErrorModel,
    PaginationModel,
    StatusModel,
    TimestampedModel,
)
from src.models.events import (
    EventFormat,
    EventRecommendationModel,
    EventStatus,
    EventType,
    SpeakerModel,
    TechEventModel,
    UserEventPreferencesModel,
    VenueModel,
)
from src.models.security import (
    AttackComplexity,
    AttackVector,
    PrivilegesRequired,
    RiskLevel,
    ThreatIntelligenceModel,
    UserInteraction,
    VulnerabilityModel,
    VulnerabilitySourceModel,
    VulnerabilityStatus,
)
from src.models.technology import (
    AdoptionLevel,
    FrameworkBattleModel,
    MaturityLevel,
    TechnologyCategory,
    TechnologyComparisonModel,
    TechnologyMetrics,
    TechnologyModel,
    TechnologyPredictionModel,
    TrendDirection,
)

# from src.models.news import NewsArticleModel, FeedSourceModel  # Temporarily disabled

__all__ = [
    # Base models
    "BaseModel",
    "TimestampedModel",
    "StatusModel",
    "ErrorModel",
    "PaginationModel",
    # Security models
    "VulnerabilityModel",
    "VulnerabilitySourceModel",
    "ThreatIntelligenceModel",
    "RiskLevel",
    "VulnerabilityStatus",
    "AttackVector",
    "AttackComplexity",
    "PrivilegesRequired",
    "UserInteraction",
    # Technology models
    "TechnologyModel",
    "TechnologyComparisonModel",
    "TechnologyPredictionModel",
    "FrameworkBattleModel",
    "TechnologyMetrics",
    "TechnologyCategory",
    "TrendDirection",
    "MaturityLevel",
    "AdoptionLevel",
    # ArXiv models
    "ArxivPaperModel",
    "EnhancedArxivPaperModel",
    "GitHubRepositoryModel",
    "PapersWithCodeModel",
    "TechnologyReadinessLevel",
    "ResearchCategory",
    "CommercialPotential",
    # Events models
    "TechEventModel",
    "SpeakerModel",
    "VenueModel",
    "EventRecommendationModel",
    "UserEventPreferencesModel",
    "EventType",
    "EventFormat",
    "EventStatus",
    # News models (temporarily disabled)
    # "NewsArticleModel",
    # "FeedSourceModel",
]
