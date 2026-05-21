from pydantic import BaseModel, Field


class ADHDPublication(BaseModel):
    title: str
    authors: list[str]
    publication_date: str | None = None
    published_at: str | None = Field(default=None, description="ISO 8601 publication date (YYYY-MM-DD)")
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    source: str
