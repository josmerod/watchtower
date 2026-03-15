"""Pydantic models for the Watchtower API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class UnifiedItem(BaseModel):
    """Unified model for news and knowledge items."""

    title: str = Field(..., description="Title of the item")
    url: str | None = Field(None, description="URL of the item")  # Using str to be lenient with faulty URLs
    source: str = Field(..., description="Source name")
    published_at: str | None = Field(None, description="Publication date (ISO 8601 or formatted string)")
    category: Optional[str] = Field(None, description="Category of the item")
    
    # Validation/Cleanup is handled by the data loader transforming raw dicts into this model
    # We allow extra fields to pass through if needed, but for now we stick to the core ones
    
    model_config = {
        "extra": "ignore" 
    }
