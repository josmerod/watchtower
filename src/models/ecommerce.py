# src/models/ecommerce.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class ShoppyProduct(BaseModel):
    """
    Data model for a product listed on Shoppy.gg or similar platforms.
    """

    product_id: str
    name: str
    price: str  # Keeping as string for now, can be parsed to float/decimal later if needed and currency is consistent
    seller: Optional[str] = None
    description: Optional[str] = None
    url: HttpUrl

    # Timestamps for tracking when data was fetched and parsed
    fetched_at: datetime
    parsed_at: datetime

    # Optional fields that might be useful
    category: Optional[str] = None
    stock_status: Optional[str] = None  # e.g., "In Stock", "Out of Stock"
    rating: Optional[float] = None  # e.g., 4.5
    num_reviews: Optional[int] = None

    # To store any other relevant data not fitting the predefined fields
    additional_info: Optional[dict] = None


class ShoppyRawData(BaseModel):
    """
    Model for the raw data fetched before parsing.
    """

    product_id: str
    raw_content: str  # Could be HTML, JSON string, etc.
    fetched_at: datetime


class GumroadProduct(BaseModel):
    """
    Data model for a free product listed on Gumroad.
    """

    product_id: str
    name: str
    price: str  # Should be "Free" or "$0.00" for free products
    seller: Optional[str] = None
    description: Optional[str] = None
    url: HttpUrl

    # Timestamps for tracking when data was fetched and parsed
    fetched_at: datetime
    parsed_at: datetime

    # Gumroad-specific fields
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    rating: Optional[float] = None
    num_ratings: Optional[int] = None
    thumbnail_url: Optional[str] = None

    # Additional metadata
    is_free: bool = True  # Should always be True for our scraper
    file_size: Optional[str] = None
    file_type: Optional[str] = None

    # To store any other relevant data not fitting the predefined fields
    additional_info: Optional[dict] = None


class GumroadRawData(BaseModel):
    """
    Model for the raw data fetched from Gumroad before parsing.
    """

    product_id: str
    raw_content: str  # HTML content from the product page
    fetched_at: datetime
    page_number: int  # Which page this product was found on
    position: int  # Position on the page (for tracking)


class TravelDeal(BaseModel):
    """
    Data model for a travel deal from Viajeros Piratas or similar travel deal sites.
    """

    deal_id: str
    title: str
    description: Optional[str] = None
    price: float = 0.0  # Numeric price for sorting/filtering
    currency: str = "EUR"
    raw_price: str = ""  # Original price text as scraped
    category: str = "other"  # hotel, flight, vacation, attraction, other
    url: Optional[str] = None

    # Timestamps
    published_at: datetime
    fetched_at: datetime
    parsed_at: datetime

    # Scraping metadata
    page_number: int
    position: int
    source: str = "viajeros_piratas"

    # Optional fields for travel-specific data
    destination: Optional[str] = None
    duration: Optional[str] = None  # e.g., "3 nights", "1 week"
    deal_type: Optional[str] = None  # e.g., "all_inclusive", "flight_only"

    # Additional metadata
    additional_info: Optional[dict] = None


class TravelDealRawData(BaseModel):
    """
    Model for raw travel deal data before parsing.
    """

    deal_id: str
    raw_content: str  # HTML content of the deal
    text_content: str  # Plain text content
    title: str
    price_text: str
    time_text: str
    link: str
    page_number: int
    position: int
    fetched_at: datetime


if __name__ == "__main__":
    # Example Usage:
    product_example = ShoppyProduct(
        product_id="example123",
        name="Example Product",
        price="10.99 USD",
        seller="TrustedSeller",
        description="This is a fantastic example product.",
        url="https://shoppy.gg/product/example123",
        fetched_at=datetime.now(),
        parsed_at=datetime.now(),
        category="Digital Goods",
        stock_status="In Stock",
    )
    print(product_example.model_dump_json(indent=2))

    raw_data_example = ShoppyRawData(
        product_id="example123",
        raw_content="<html>...</html>",
        fetched_at=datetime.now(),
    )
    print(raw_data_example.model_dump_json(indent=2))
