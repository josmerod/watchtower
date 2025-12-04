"""Data models for AI/ML Research Intelligence."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel


class ResearchDomain(str, Enum):
    """AI Research Domains."""

    NLP = "Natural Language Processing"
    CV = "Computer Vision"
    RL = "Reinforcement Learning"
    ML_THEORY = "Machine Learning Theory"
    ROBOTICS = "Robotics"
    AUDIO = "Audio & Speech"
    GENERATIVE = "Generative AI"
    OTHER = "Other"


class ImplementationComplexity(str, Enum):
    """Implementation complexity levels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class AIResearchPaper(TimestampedModel):
    """Model for AI Research Papers."""

    # Core Metadata
    title: str = Field(description="Paper title")
    authors: list[str] = Field(default=[], description="List of authors")
    published_at: datetime = Field(description="Publication date")
    url: HttpUrl = Field(description="Link to the paper (e.g., arXiv)")
    pdf_url: HttpUrl | None = Field(default=None, description="Link to PDF")
    source: str = Field(description="Source name (e.g., arXiv, PapersWithCode)")

    # Content
    abstract: str = Field(description="Paper abstract")
    summary: str | None = Field(default=None, description="AI-generated summary")
    key_takeaways: list[str] = Field(default=[], description="Key takeaways")

    # Classification
    primary_domain: ResearchDomain = Field(default=ResearchDomain.OTHER, description="Primary AI domain")
    tags: list[str] = Field(default=[], description="Research tags")

    # Intelligence Metrics
    trend_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Trend momentum score")
    complexity: ImplementationComplexity = Field(default=ImplementationComplexity.MEDIUM, description="Implementation complexity")
    complexity_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Numeric complexity score")
    industry_impact: str = Field(default="Pending Analysis", description="Qualitative industry impact assessment")
    industry_impact_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Potential industry impact")
    implementation_probability: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Implementation probability percentage",
    )

    # Implementation details
    code_url: HttpUrl | None = Field(default=None, description="Link to code repository")
    frameworks: list[str] = Field(default=[], description="Frameworks used (PyTorch, TensorFlow, etc.)")

    # Opportunities
    implementation_opportunities: list[str] = Field(default=[], description="Identified implementation opportunities")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "title": "Attention Is All You Need",
                    "authors": ["Vaswani et al."],
                    "published_at": "2017-06-12T00:00:00Z",
                    "url": "https://arxiv.org/abs/1706.03762",
                    "source": "arXiv",
                    "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                    "primary_domain": "Natural Language Processing",
                    "trend_score": 98.5,
                    "complexity": "High",
                }
            ]
        }
