"""Pydantic models for Language and GenAI Trends."""

from enum import Enum

from pydantic import Field, HttpUrl

from src.models.base import TimestampedModel


class TrendType(str, Enum):
    """Type of trend item."""

    PYTHON_PACKAGE = "Python Package"
    HF_MODEL = "Hugging Face Model"


class PackageTrendModel(TimestampedModel):
    """Model for Python package stats (PyPI)."""

    name: str = Field(description="Package name (e.g. pandas)")
    total_downloads: int = Field(default=0, description="Total downloads (recent period)")
    recent_downloads: int = Field(default=0, description="Recent downloads (e.g. last week)")
    previous_downloads: int = Field(default=0, description="Previous period downloads")
    growth_rate: float = Field(default=0.0, description="Growth rate percentage")

    category: str | None = Field(default=None, description="Category (e.g. Data, Web, AI)")

    # History for charts
    history_dates: list[str] = Field(default=[], description="List of dates")
    history_downloads: list[int] = Field(default=[], description="List of download counts")


class ModelTrendModel(TimestampedModel):
    """Model for Hugging Face Model stats."""

    model_id: str = Field(description="Model ID (e.g. meta-llama/Llama-2-7b)")
    author: str = Field(description="Model author/org")
    name: str = Field(description="Model name")

    downloads: int = Field(default=0, description="Downloads (last 30 days)")
    likes: int = Field(default=0, description="Total likes")

    tags: list[str] = Field(default=[], description="Model tags (e.g. text-generation)")
    pipeline_tag: str | None = Field(default=None, description="Pipeline task")

    url: HttpUrl | None = Field(default=None, description="Link to model")
