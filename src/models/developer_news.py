from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NewsCategory(str, Enum):
    AI_ML = "AI & Machine Learning"
    WEB_DEV = "Web Development"
    DEVOPS = "DevOps & Cloud"
    MOBILE = "Mobile Development"
    SECURITY = "Cybersecurity"
    CAREER = "Career & Productivity"
    STARTUPS = "Startups & Business"
    GENERAL = "General Tech"


class ExpertComment(BaseModel):
    author: str
    content: str
    source: str
    sentiment: str | None = None


class SmartNewsItem(BaseModel):
    id: str
    title: str
    url: str
    source: str
    published_at: datetime
    category: NewsCategory

    # Intelligence Fields
    summary: str = Field(..., description="AI-generated summary of the content")
    key_points: list[str] = Field(default_factory=list, description="Extracted key points")
    trend_score: float = Field(0.0, ge=0.0, le=1.0, description="Calculated trend score")
    expert_commentary: ExpertComment | None = None

    # Metadata
    original_data: dict = Field(default_factory=dict, description="Original raw data")
