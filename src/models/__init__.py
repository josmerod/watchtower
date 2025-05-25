"""Data models for Watchtower."""

from src.models.base import BaseModel, TimestampedModel, StatusModel, ErrorModel, PaginationModel
from src.models.security import (
    VulnerabilityModel, VulnerabilitySourceModel, ThreatIntelligenceModel,
    RiskLevel, VulnerabilityStatus, AttackVector, AttackComplexity, 
    PrivilegesRequired, UserInteraction
)
from src.models.technology import (
    TechnologyModel, TechnologyComparisonModel, TechnologyPredictionModel,
    FrameworkBattleModel, TechnologyMetrics, TechnologyCategory,
    TrendDirection, MaturityLevel, AdoptionLevel
)
from src.models.arxiv import (
    ArxivPaperModel, EnhancedArxivPaperModel, GitHubRepositoryModel, PapersWithCodeModel,
    TechnologyReadinessLevel, ResearchCategory, CommercialPotential
)
from src.models.events import (
    TechEventModel, SpeakerModel, VenueModel, EventRecommendationModel, 
    UserEventPreferencesModel, EventType, EventFormat, EventStatus
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