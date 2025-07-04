
from pydantic import BaseModel


class ADHDPublication(BaseModel):
    title: str
    authors: list[str]
    publication_date: str | None = None
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    source: str
