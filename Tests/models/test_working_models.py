"""Working unit tests for Pydantic models that actually exist.
Tests validation, serialization, and model behavior.
"""

import unittest
import uuid
from datetime import datetime

from pydantic import ValidationError

from src.models.base import (
    BaseModel,
    ErrorModel,
    PaginatedResponse,
    PaginationModel,
    StatusModel,
    TimestampedModel,
)


class TestBaseModels(unittest.TestCase):
    """Test base model classes that actually exist."""

    def test_base_model_functionality(self):
        """Test BaseModel basic functionality."""

        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)

        self.assertEqual(model.name, "test")
        self.assertEqual(model.value, 42)

    def test_base_model_dict_without_none(self):
        """Test dict_without_none method."""

        class TestModel(BaseModel):
            name: str
            optional: str | None = None

        model = TestModel(name="test")
        result = model.dict_without_none()

        self.assertIn("name", result)
        self.assertNotIn("optional", result)

    def test_base_model_update_from_dict(self):
        """Test update_from_dict method."""

        class TestModel(BaseModel):
            name: str
            value: int = 0

        original = TestModel(name="original", value=1)
        updated = original.update_from_dict({"name": "updated", "value": 2})

        self.assertEqual(updated.name, "updated")
        self.assertEqual(updated.value, 2)
        # Original should be unchanged
        self.assertEqual(original.name, "original")

    def test_timestamped_model_auto_timestamps(self):
        """Test TimestampedModel automatically sets timestamps."""

        class TestModel(TimestampedModel):
            name: str

        model = TestModel(name="test")

        self.assertIsInstance(model.id, str)
        self.assertIsInstance(model.created_at, datetime)
        # updated_at might be None by default, but created_at should exist
        if model.updated_at is not None:
            self.assertIsInstance(model.updated_at, datetime)

    def test_timestamped_model_uuid_generation(self):
        """Test TimestampedModel generates unique IDs."""

        class TestModel(TimestampedModel):
            name: str

        model1 = TestModel(name="test1")
        model2 = TestModel(name="test2")

        self.assertNotEqual(model1.id, model2.id)
        # Should be valid UUIDs
        uuid.UUID(model1.id)  # Should not raise
        uuid.UUID(model2.id)  # Should not raise

    def test_status_model_creation(self):
        """Test StatusModel creation and validation."""
        status = StatusModel(
            status="success",
            message="Operation completed successfully",
            details={"count": 10, "duration": 5.2},
        )

        self.assertEqual(status.status, "success")
        self.assertEqual(status.message, "Operation completed successfully")
        self.assertEqual(status.details["count"], 10)
        self.assertIsInstance(status.timestamp, datetime)

    def test_error_model_creation(self):
        """Test ErrorModel creation and validation."""
        error = ErrorModel(
            error_code="VALIDATION_ERROR",
            error_message="Invalid input provided",
            error_type="ValidationError",
            context={"field": "email", "value": "invalid-email"},
        )

        self.assertEqual(error.error_code, "VALIDATION_ERROR")
        self.assertEqual(error.error_message, "Invalid input provided")
        self.assertEqual(error.error_type, "ValidationError")
        self.assertEqual(error.context["field"], "email")
        self.assertIsInstance(error.timestamp, datetime)

    def test_pagination_model_calculation(self):
        """Test PaginationModel with all required fields."""
        pagination = PaginationModel(
            page=2,
            page_size=10,
            total_items=95,
            total_pages=10,
            has_next=True,
            has_previous=True,
        )

        self.assertEqual(pagination.page, 2)
        self.assertEqual(pagination.page_size, 10)
        self.assertEqual(pagination.total_items, 95)
        self.assertEqual(pagination.total_pages, 10)
        self.assertTrue(pagination.has_previous)
        self.assertTrue(pagination.has_next)

    def test_pagination_model_edge_cases(self):
        """Test PaginationModel edge cases."""
        # First page
        first_page = PaginationModel(
            page=1,
            page_size=20,
            total_items=15,
            total_pages=1,
            has_next=False,
            has_previous=False,
        )

        self.assertFalse(first_page.has_previous)
        self.assertFalse(first_page.has_next)
        self.assertEqual(first_page.total_pages, 1)

    def test_paginated_response_creation(self):
        """Test PaginatedResponse creation."""
        items = [{"id": i, "name": f"item_{i}"} for i in range(1, 6)]
        pagination = PaginationModel(
            page=1,
            page_size=5,
            total_items=25,
            total_pages=5,
            has_next=True,
            has_previous=False,
        )

        response = PaginatedResponse(
            items=items,
            pagination=pagination,
            metadata={"query_time": 0.05, "source": "database"},
        )

        self.assertEqual(len(response.items), 5)
        self.assertEqual(response.pagination.total_items, 25)
        self.assertEqual(response.metadata["query_time"], 0.05)


class TestModelSerialization(unittest.TestCase):
    """Test model serialization and deserialization."""

    def test_model_to_dict(self):
        """Test model serialization to dictionary."""

        class TestModel(TimestampedModel):
            name: str
            tags: list[str] = []

        model = TestModel(name="test", tags=["tag1", "tag2"])

        model_dict = model.model_dump()

        self.assertIsInstance(model_dict, dict)
        self.assertEqual(model_dict["name"], "test")
        self.assertEqual(model_dict["tags"], ["tag1", "tag2"])
        self.assertIn("id", model_dict)
        self.assertIn("created_at", model_dict)

    def test_model_to_json(self):
        """Test model serialization to JSON."""
        status = StatusModel(status="active", message="System is running")

        json_string = status.model_dump_json()

        self.assertIsInstance(json_string, str)
        self.assertIn("active", json_string)
        self.assertIn("System is running", json_string)

    def test_model_from_dict(self):
        """Test model deserialization from dictionary."""
        data = {
            "error_code": "NOT_FOUND",
            "error_message": "Resource not found",
            "error_type": "NotFoundError",
        }

        error = ErrorModel(**data)

        self.assertEqual(error.error_code, "NOT_FOUND")
        self.assertEqual(error.error_message, "Resource not found")
        self.assertEqual(error.error_type, "NotFoundError")


class TestModelValidation(unittest.TestCase):
    """Test model validation behavior."""

    def test_required_field_validation(self):
        """Test validation of required fields."""

        class TestModel(BaseModel):
            name: str
            value: int

        # Should work with all required fields
        model = TestModel(name="test", value=42)
        self.assertEqual(model.name, "test")

        # Should fail without required field
        with self.assertRaises(ValidationError):
            TestModel(name="test")  # Missing value

    def test_type_validation(self):
        """Test type validation."""

        class TestModel(BaseModel):
            name: str
            value: int

        # Should work with correct types
        model = TestModel(name="test", value=42)
        self.assertEqual(model.value, 42)

        # Should convert string to int if possible
        model2 = TestModel(name="test", value="123")
        self.assertEqual(model2.value, 123)
        self.assertIsInstance(model2.value, int)

    def test_pagination_validation(self):
        """Test pagination model validation."""
        # Valid pagination
        pagination = PaginationModel(
            page=1,
            page_size=10,
            total_items=50,
            total_pages=5,
            has_next=True,
            has_previous=False,
        )
        self.assertEqual(pagination.page, 1)

        # Invalid page (must be >= 1)
        with self.assertRaises(ValidationError):
            PaginationModel(
                page=0,
                page_size=10,
                total_items=50,
                total_pages=5,
                has_next=True,
                has_previous=False,
            )

        # Invalid page_size (must be >= 1)
        with self.assertRaises(ValidationError):
            PaginationModel(
                page=1,
                page_size=0,
                total_items=50,
                total_pages=5,
                has_next=True,
                has_previous=False,
            )


if __name__ == "__main__":
    unittest.main()
