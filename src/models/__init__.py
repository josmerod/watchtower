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
    "AdoptionLevel",
    # ArXiv models
    "ArxivPaperModel",
    "AttackComplexity",
    "AttackVector",
    # Base models
    "BaseModel",
    "CommercialPotential",
    "EnhancedArxivPaperModel",
    "ErrorModel",
    "EventFormat",
    "EventRecommendationModel",
    "EventStatus",
    "EventType",
    "FrameworkBattleModel",
    "GitHubRepositoryModel",
    "MaturityLevel",
    "PaginationModel",
    "PapersWithCodeModel",
    "PrivilegesRequired",
    "ResearchCategory",
    "RiskLevel",
    "SpeakerModel",
    "StatusModel",
    # Events models
    "TechEventModel",
    "TechnologyCategory",
    "TechnologyComparisonModel",
    "TechnologyMetrics",
    # Technology models
    "TechnologyModel",
    "TechnologyPredictionModel",
    "TechnologyReadinessLevel",
    "ThreatIntelligenceModel",
    "TimestampedModel",
    "TrendDirection",
    "UserEventPreferencesModel",
    "UserInteraction",
    "VenueModel",
    # Security models
    "VulnerabilityModel",
    "VulnerabilitySourceModel",
    "VulnerabilityStatus",
    # News models (temporarily disabled)
    # "NewsArticleModel",
    # "FeedSourceModel",
]
