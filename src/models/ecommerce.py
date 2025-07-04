# src/models/ecommerce.py
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ShoppyProduct(BaseModel):
    """Data model for a product listed on Shoppy.gg or similar platforms."""

    product_id: str
    name: str
    price: str  # Keeping as string for now, can be parsed to float/decimal later if needed and currency is consistent
    seller: str | None = None
    description: str | None = None
    url: HttpUrl

    # Timestamps for tracking when data was fetched and parsed
    fetched_at: datetime
    parsed_at: datetime

    # Optional fields that might be useful
    category: str | None = None
    stock_status: str | None = None  # e.g., "In Stock", "Out of Stock"
    rating: float | None = None  # e.g., 4.5
    num_reviews: int | None = None

    # To store any other relevant data not fitting the predefined fields
    additional_info: dict | None = None


class ShoppyRawData(BaseModel):
    """Model for the raw data fetched before parsing."""

    product_id: str
    raw_content: str  # Could be HTML, JSON string, etc.
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
