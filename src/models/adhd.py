from typing import List, Optional

from pydantic import BaseModel


class ADHDPublication(BaseModel):
    title: str
    authors: List[str]
    publication_date: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    source: str
