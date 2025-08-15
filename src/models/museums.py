import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field, HttpUrl

# Assuming TimestampedModel is defined in src.models.base
from src.models.base import TimestampedModel


class VirtualMuseumModel(
    TimestampedModel
):  # Ensure this class correctly inherits from the imported TimestampedModel
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4
    )  # Redefined as per instruction, though TimestampedModel might provide it
    name: str
    description: Optional[str] = None
    website_url: Optional[HttpUrl] = None
    virtual_tour_url: Optional[HttpUrl] = None
    country_label: Optional[str] = None  # Label for the country
    city_label: Optional[str] = None  # Label for the city
    main_subject_label: Optional[str] = None  # Label for the main subject
    image_url: Optional[HttpUrl] = None
    wikidata_url: Optional[HttpUrl] = None  # Link to the Wikidata item
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data_source: str = "Wikidata"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        collection_name = "virtual_museums"

    def __hash__(self):
        # Using a combination of fields that are likely to be unique
        # and immutable or less frequently changed.
        # id should be sufficient if always present and unique.
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, VirtualMuseumModel):
            return NotImplemented
        return self.id == other.id

    @classmethod
    async def get_by_name(cls, name: str):
        # This is a placeholder for a database query.
        # In a real application, this would interact with a database.
        # For now, it will return None, as there's no database connected.
        print(f"Attempting to retrieve museum by name: {name}")
        return None

    @classmethod
    async def get_random_museum(cls):
        # Placeholder for fetching a random museum
        print("Attempting to retrieve a random museum.")
        return None
