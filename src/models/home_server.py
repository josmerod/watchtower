# src/models/home_server.py
from typing import List, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class HomeServerTrendItem(BaseModel):
    id: str
    name: str
    description: str
    url: str  # Using str for now as HttpUrl can be strict with relative/internal links if any
    category: str
    source: str = "awesome-selfhosted"
    tags: Optional[List[str]] = None
    added_date: datetime
