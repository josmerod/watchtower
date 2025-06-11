"""Data models for Watchtower."""

from models.arxiv import (
    ArxivPaperModel,
    CommercialPotential,
    EnhancedArxivPaperModel,
    GitHubRepositoryModel,
    PapersWithCodeModel,
    ResearchCategory,
    TechnologyReadinessLevel,
)
from models.base import (
    BaseModel,
    ErrorModel,
    PaginationModel,
    StatusModel,
    TimestampedModel,
)
from models.events import (
    EventFormat,
    EventRecommendationModel,
    EventStatus,
    EventType,
    SpeakerModel,
    TechEventModel,
    UserEventPreferencesModel,
    VenueModel,
)
from models.security import (
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
from models.technology import (
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

# from models.news import NewsArticleModel, FeedSourceModel  # Temporarily disabled

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
