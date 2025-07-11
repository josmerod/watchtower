"""Base models for Watchtower with common functionality."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, field_validator


class BaseModel(PydanticBaseModel):
    """Base model with common configuration and methods."""

    model_config = {
        # Allow field population by name and alias
        "populate_by_name": True,
        # Validate assignment (validate on attribute assignment)
        "validate_assignment": True,
        # Use enum values instead of enum names
        "use_enum_values": True,
        # Generate schema with examples
        "json_schema_extra": {"examples": []},
    }

    def dict_without_none(self, **kwargs) -> dict[str, Any]:
        """Return dictionary representation excluding None values.

        Args:
            **kwargs: Additional arguments for model_dump().

        Returns:
            Dictionary without None values.
        """
        return {k: v for k, v in self.model_dump(**kwargs).items() if v is not None}

    def update_from_dict(self, data: dict[str, Any]) -> BaseModel:
        """Update model from dictionary, returning new instance.

        Args:
            data: Dictionary with updated values.

        Returns:
            New model instance with updated values.
        """
        current_data = self.model_dump()
        current_data.update(data)
        return self.__class__(**current_data)


class TimestampedModel(BaseModel):
    """Base model with automatic timestamp fields."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique identifier"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    @field_validator("updated_at", mode="before")
    @classmethod
    def set_updated_at(cls, v: datetime | None) -> datetime:
        """Auto-set updated_at to current time if not provided.

        Args:
            v: Current value of updated_at.

        Returns:
            Current datetime or provided value.
        """
        return v or datetime.utcnow()


class StatusModel(BaseModel):
    """Model for status information."""

    status: str = Field(description="Status value")
    message: str | None = Field(default=None, description="Status message")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional status details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Status timestamp"
    )


class ErrorModel(BaseModel):
    """Model for error information."""

    error_code: str = Field(description="Error code")
    error_message: str = Field(description="Error message")
    error_type: str = Field(description="Error type/class")
    traceback: str | None = Field(default=None, description="Error traceback")
    context: dict[str, Any] | None = Field(
        default=None, description="Additional error context"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )


class PaginationModel(BaseModel):
    """Model for pagination information."""

    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=1000, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether next page exists")
    has_previous: bool = Field(description="Whether previous page exists")

    @field_validator("total_pages", mode="before")
    @classmethod
    def calculate_total_pages(cls, v: int, info) -> int:
        """Calculate total pages from total items and page size.

        Args:
            v: Current total_pages value.
            info: Validation info with other field values.

        Returns:
            Calculated total pages.
        """
        data = info.data if hasattr(info, "data") else {}
        if "total_items" in data and "page_size" in data:
            total_items = data["total_items"]
            page_size = data["page_size"]
            return (total_items + page_size - 1) // page_size
        return v

    @field_validator("has_next", mode="before")
    @classmethod
    def calculate_has_next(cls, v: bool, info) -> bool:
        """Calculate if next page exists.

        Args:
            v: Current has_next value.
            info: Validation info with other field values.

        Returns:
            Whether next page exists.
        """
        data = info.data if hasattr(info, "data") else {}
        if "page" in data and "total_pages" in data:
            return data["page"] < data["total_pages"]
        return v

    @field_validator("has_previous", mode="before")
    @classmethod
    def calculate_has_previous(cls, v: bool, info) -> bool:
        """Calculate if previous page exists.

        Args:
            v: Current has_previous value.
            info: Validation info with other field values.

        Returns:
            Whether previous page exists.
        """
        data = info.data if hasattr(info, "data") else {}
        if "page" in data:
            return data["page"] > 1
        return v


class PaginatedResponse(BaseModel):
    """Generic paginated response model."""

    items: list = Field(description="List of items")
    pagination: PaginationModel = Field(description="Pagination information")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional response metadata"
    )
