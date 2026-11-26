"""Tests for the Shoppy models in ``src/models/ecommerce.py``.

Each test asserts directly: a failing construction must fail the test, never
be swallowed by a ``try`` block that returns a boolean.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.ecommerce import ShoppyProduct, ShoppyRawData

NOW = datetime(2026, 11, 24, 12, 0, 0)


def product_payload(**overrides):
    """Return a valid ``ShoppyProduct`` payload with ``overrides`` applied."""
    return {
        "product_id": "test_prod_001",
        "name": "Test Product",
        "price": "1.00",
        "url": "https://shoppy.gg/products/test",
        "fetched_at": NOW,
        "parsed_at": NOW,
        "rating": 4.5,
    } | overrides


def test_shoppy_product_valid_creation():
    product = ShoppyProduct(**product_payload())

    assert product.product_id == "test_prod_001"
    assert product.name == "Test Product"
    assert product.price == "1.00"
    assert product.rating == 4.5
    assert product.seller is None


def test_shoppy_product_rejects_missing_required_fields():
    with pytest.raises(ValidationError) as excinfo:
        ShoppyProduct(product_id="incomplete")

    missing = {error["loc"][0] for error in excinfo.value.errors() if error["type"] == "missing"}
    assert missing == {"name", "price", "url", "fetched_at", "parsed_at"}


def test_shoppy_product_rejects_invalid_url():
    with pytest.raises(ValidationError):
        ShoppyProduct(**product_payload(product_id="badurl", url="not-a-url"))


def test_shoppy_product_rejects_non_numeric_rating():
    with pytest.raises(ValidationError):
        ShoppyProduct(**product_payload(product_id="badrating", rating="not-a-float"))


def test_shoppy_raw_data_creation():
    raw_data = ShoppyRawData(product_id="raw_001", raw_content="<p>HTML content</p>", fetched_at=NOW)

    assert raw_data.product_id == "raw_001"
    assert "HTML content" in raw_data.raw_content
