"""Data models for AI platform monitoring."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, HttpUrl

from src.models.base import TimestampedModel


class ModelType(str, Enum):
    """AI model type classification."""
    LANGUAGE_MODEL = "language_model"
    MULTIMODAL = "multimodal"
    CODE_GENERATION = "code_generation"
    IMAGE_GENERATION = "image_generation"
    AUDIO_GENERATION = "audio_generation"
    EMBEDDING = "embedding"
    FINE_TUNED = "fine_tuned"
    OTHER = "other"


class PlatformStatus(str, Enum):
    """Platform operational status."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OUTAGE = "outage"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class AIModelRelease(TimestampedModel):
    """Model for AI model releases and updates."""
    
    platform: str = Field(..., description="Platform name (openai, anthropic, etc.)")
    model_id: str = Field(..., description="Unique model identifier")
    model_name: str = Field(..., description="Human-readable model name")
    version: str = Field(..., description="Model version")
    model_type: ModelType = Field(..., description="Type of AI model")
    release_date: datetime = Field(..., description="Official release date")
    capabilities: List[str] = Field(default_factory=list, description="Model capabilities")
    context_length: Optional[int] = Field(None, description="Maximum context length")
    training_data_cutoff: Optional[datetime] = Field(None, description="Training data cutoff date")
    pricing_input: Optional[float] = Field(None, description="Price per input token")
    pricing_output: Optional[float] = Field(None, description="Price per output token")
    max_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    announcement_url: Optional[HttpUrl] = Field(None, description="Official announcement URL")
    documentation_url: Optional[HttpUrl] = Field(None, description="Documentation URL")
    is_beta: bool = Field(default=False, description="Is this a beta release")
    is_deprecated: bool = Field(default=False, description="Is this model deprecated")
    deprecation_date: Optional[datetime] = Field(None, description="Planned deprecation date")
    replacement_model: Optional[str] = Field(None, description="Replacement model ID")
    performance_benchmarks: Dict[str, float] = Field(default_factory=dict, description="Benchmark scores")
    availability_regions: List[str] = Field(default_factory=list, description="Available regions")


class PlatformUpdate(TimestampedModel):
    """Model for platform updates and announcements."""
    
    platform: str = Field(..., description="Platform name")
    update_type: str = Field(..., description="Type of update (feature, pricing, policy, etc.)")
    title: str = Field(..., description="Update title")
    description: str = Field(..., description="Update description")
    announcement_date: datetime = Field(..., description="Announcement date")
    effective_date: Optional[datetime] = Field(None, description="When update takes effect")
    impact_level: str = Field(..., description="Impact level (low, medium, high, critical)")
    affected_services: List[str] = Field(default_factory=list, description="Affected services")
    breaking_changes: bool = Field(default=False, description="Contains breaking changes")
    migration_required: bool = Field(default=False, description="Requires user migration")
    source_url: Optional[HttpUrl] = Field(None, description="Source announcement URL")
    changelog_url: Optional[HttpUrl] = Field(None, description="Detailed changelog URL")
    tags: List[str] = Field(default_factory=list, description="Update tags")


class APIUsageMetrics(TimestampedModel):
    """Model for API usage and adoption metrics."""
    
    platform: str = Field(..., description="Platform name")
    metric_type: str = Field(..., description="Type of metric (usage, adoption, performance)")
    model_id: Optional[str] = Field(None, description="Specific model if applicable")
    requests_per_second: Optional[float] = Field(None, description="Requests per second")
    active_users: Optional[int] = Field(None, description="Number of active users")
    new_signups: Optional[int] = Field(None, description="New user signups")
    enterprise_adoptions: Optional[int] = Field(None, description="Enterprise customer count")
    api_latency_p95: Optional[float] = Field(None, description="95th percentile API latency")
    error_rate: Optional[float] = Field(None, description="API error rate percentage")
    uptime_percentage: Optional[float] = Field(None, description="Service uptime percentage")
    rate_limit_hits: Optional[int] = Field(None, description="Rate limit violations")
    cost_per_request: Optional[float] = Field(None, description="Average cost per API request")
    geographic_distribution: Dict[str, int] = Field(default_factory=dict, description="Usage by region")


class DeveloperTool(TimestampedModel):
    """Model for AI-powered developer tools."""
    
    tool_name: str = Field(..., description="Tool name")
    platform: str = Field(..., description="Platform or company")
    tool_type: str = Field(..., description="Type of tool (ide, code_completion, etc.)")
    supported_languages: List[str] = Field(default_factory=list, description="Supported programming languages")
    integration_type: str = Field(..., description="Integration type (plugin, native, web)")
    adoption_metrics: Dict[str, Any] = Field(default_factory=dict, description="Usage metrics")
    feature_updates: List[str] = Field(default_factory=list, description="Recent feature updates")
    pricing_model: str = Field(..., description="Pricing model (free, subscription, usage)")
    pricing_details: Dict[str, Any] = Field(default_factory=dict, description="Pricing information")
    user_reviews: Dict[str, float] = Field(default_factory=dict, description="User review scores")
    competitor_analysis: Dict[str, Any] = Field(default_factory=dict, description="Competitive positioning")


class ResearchPublication(TimestampedModel):
    """Model for AI research publications and papers."""
    
    platform: str = Field(..., description="Platform or organization")
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="Paper authors")
    publication_date: datetime = Field(..., description="Publication date")
    abstract: str = Field(..., description="Paper abstract")
    paper_url: Optional[HttpUrl] = Field(None, description="Paper URL")
    arxiv_id: Optional[str] = Field(None, description="ArXiv ID if applicable")
    research_areas: List[str] = Field(default_factory=list, description="Research areas/tags")
    methodology: Optional[str] = Field(None, description="Research methodology")
    key_findings: List[str] = Field(default_factory=list, description="Key research findings")
    benchmark_results: Dict[str, float] = Field(default_factory=dict, description="Benchmark performance")
    code_availability: bool = Field(default=False, description="Is code available")
    dataset_used: Optional[str] = Field(None, description="Dataset used in research")
    citations_count: Optional[int] = Field(None, description="Number of citations")
    impact_score: Optional[float] = Field(None, description="Research impact score")


class ComplianceAlert(TimestampedModel):
    """Model for AI platform compliance and regulatory alerts."""
    
    platform: str = Field(..., description="Platform name")
    alert_type: str = Field(..., description="Type of alert (privacy, safety, regulatory)")
    severity: str = Field(..., description="Alert severity (low, medium, high, critical)")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    regulatory_body: Optional[str] = Field(None, description="Regulatory body involved")
    affected_regions: List[str] = Field(default_factory=list, description="Affected geographic regions")
    compliance_deadline: Optional[datetime] = Field(None, description="Compliance deadline")
    required_actions: List[str] = Field(default_factory=list, description="Required actions")
    financial_impact: Optional[float] = Field(None, description="Potential financial impact")
    source_url: Optional[HttpUrl] = Field(None, description="Source URL")
    status: str = Field(default="active", description="Alert status")


class PlatformStatus(TimestampedModel):
    """Model for AI platform operational status."""
    
    platform: str = Field(..., description="Platform name")
    service_name: str = Field(..., description="Specific service name")
    status: PlatformStatus = Field(..., description="Current operational status")
    last_incident: Optional[datetime] = Field(None, description="Last incident timestamp")
    uptime_percentage: float = Field(..., description="Current uptime percentage")
    response_time_ms: Optional[float] = Field(None, description="Average response time")
    incident_count_24h: int = Field(default=0, description="Incidents in last 24 hours")
    maintenance_scheduled: Optional[datetime] = Field(None, description="Next scheduled maintenance")
    status_page_url: Optional[HttpUrl] = Field(None, description="Status page URL")
    monitoring_source: str = Field(..., description="Source of status information")


class AIMarketIntelligence(TimestampedModel):
    """Model for AI market intelligence and trends."""
    
    report_type: str = Field(..., description="Type of intelligence report")
    market_segment: str = Field(..., description="Market segment (enterprise, consumer, developer)")
    growth_rate: Optional[float] = Field(None, description="Market growth rate percentage")
    market_size_usd: Optional[float] = Field(None, description="Market size in USD")
    key_trends: List[str] = Field(default_factory=list, description="Key market trends")
    top_players: List[str] = Field(default_factory=list, description="Top market players")
    emerging_technologies: List[str] = Field(default_factory=list, description="Emerging technologies")
    investment_activity: Dict[str, Any] = Field(default_factory=dict, description="Investment and funding data")
    regulatory_landscape: Dict[str, Any] = Field(default_factory=dict, description="Regulatory environment")
    consumer_sentiment: Dict[str, float] = Field(default_factory=dict, description="Consumer sentiment metrics")
    enterprise_adoption: Dict[str, Any] = Field(default_factory=dict, description="Enterprise adoption metrics")
    geographic_distribution: Dict[str, Any] = Field(default_factory=dict, description="Geographic market data")
    forecast_data: Dict[str, Any] = Field(default_factory=dict, description="Market forecasts")
    source_reports: List[str] = Field(default_factory=list, description="Source reports and studies") 