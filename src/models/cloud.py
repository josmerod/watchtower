"""Data models for Cloud Computing Intelligence."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from datetime import datetime

from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel


class CloudProvider(str, Enum):
    """Cloud providers."""
    AWS = "AWS"
    AZURE = "Azure"
    GCP = "GCP"
    ORACLE = "Oracle"
    OTHER = "Other"


class UpdateCategory(str, Enum):
    """Category of cloud update."""
    FEATURE = "Feature"
    SECURITY = "Security"
    COST = "Cost"
    REGION = "Region"
    COMPLIANCE = "Compliance"
    GENERAL = "General"


class CloudUpdate(TimestampedModel):
    """Model for a cloud platform update."""
    
    # Identity
    update_id: str = Field(description="Unique update identifier")
    title: str = Field(description="Update title")
    provider: CloudProvider = Field(description="Cloud provider")
    
    # Content
    description: str = Field(description="Update description")
    summary: str = Field(default="", description="AI/Heuristic summary")
    link: HttpUrl = Field(description="Link to official announcement")
    published_at: datetime = Field(description="Publication date")
    
    # Classification
    category: UpdateCategory = Field(default=UpdateCategory.GENERAL, description="Update category")
    services: List[str] = Field(default=[], description="Affected services (e.g., EC2, Lambda)")
    
    # Intelligence
    impact_score: float = Field(default=0.5, description="Estimated impact (0.0-1.0)")
    cost_implication: bool = Field(default=False, description="Does this affect costs?")
    security_implication: bool = Field(default=False, description="Does this affect security?")
    
    tags: List[str] = Field(default=[], description="Additional tags")
