# src/models/home_server.py
from datetime import datetime

from pydantic import BaseModel


class HomeServerTrendItem(BaseModel):
    id: str
    name: str
    description: str
    url: str  # Using str for now as HttpUrl can be strict with relative/internal links if any
    category: str
    source: str = "awesome-selfhosted"
    tags: list[str] | None = None
    added_date: datetime
