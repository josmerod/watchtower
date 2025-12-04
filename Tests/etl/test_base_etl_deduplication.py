"""Tests for BaseETL deduplication integration."""

import json

import pytest

from src.data_quality.deduplication import DeduplicationEngine
from src.etl.base import BaseETL, ETLMetrics
from src.models.base import TimestampedModel


class TestContentModel(TimestampedModel):
    """Test content model for ETL integration tests."""

    title: str
    description: str | None = None
    source: str | None = None
    url: str | None = None


class TestDeduplicationETL(BaseETL[dict, TestContentModel]):
    """Test ETL class for deduplication integration."""

    def __init__(self, test_data: list[dict], **kwargs):
        super().__init__("test_deduplication_etl", **kwargs)
        self.test_data = test_data

    def extract(self) -> list[dict]:
        """Extract test data."""
        return self.test_data

    def transform(self, data: list[dict]) -> list[TestContentModel]:
        """Transform data into models."""
        return [TestContentModel(**item) for item in data]

    def load(self, data: list[TestContentModel]) -> None:
        """Load data to file (mock)."""
        # Convert to dict format for saving
        data_dict = [item.model_dump() for item in data]
        output_file = self.output_dir / f"{self.name}_output.json"

        # Add metadata about deduplication
        output_data = {
            "metadata": {
                "total_items": len(data),
                "deduplication_enabled": self.enable_deduplication,
                "etl_name": self.name,
            },
            "items": data_dict,
        }

        output_file.write_text(json.dumps(output_data, indent=2, default=str), encoding="utf-8")


class TestBaseETLDeduplication:
    """Test suite for BaseETL deduplication integration."""

    def test_etl_init_with_deduplication_enabled(self):
        """Test ETL initialization with deduplication enabled."""
        etl = TestDeduplicationETL(test_data=[])

        assert etl.enable_deduplication is True
        assert etl.deduplication_engine is not None
        assert isinstance(etl.deduplication_engine, DeduplicationEngine)
        assert etl.title_similarity_threshold == 0.8

    def test_etl_init_with_deduplication_disabled(self):
        """Test ETL initialization with deduplication disabled."""
        etl = TestDeduplicationETL(test_data=[], enable_deduplication=False)

        assert etl.enable_deduplication is False
        assert etl.deduplication_engine is None

    def test_etl_init_with_custom_similarity_threshold(self):
        """Test ETL initialization with custom similarity threshold."""
        etl = TestDeduplicationETL(test_data=[], title_similarity_threshold=0.9)

        assert etl.title_similarity_threshold == 0.9
        assert etl.deduplication_engine.title_similarity_threshold == 0.9

    def test_apply_deduplication_disabled(self):
        """Test that deduplication is skipped when disabled."""
        etl = TestDeduplicationETL(test_data=[], enable_deduplication=False)

        data = [
            TestContentModel(title="Item 1"),
            TestContentModel(title="Item 1"),  # Duplicate
        ]

        result = etl._apply_deduplication(data)

        # Should return original data unchanged
        assert len(result) == len(data)
        assert result == data

    def test_apply_deduplication_no_engine(self):
        """Test that deduplication is skipped when no engine is available."""
        etl = TestDeduplicationETL(test_data=[], enable_deduplication=False)
        etl.deduplication_engine = None  # Explicitly set to None

        data = [TestContentModel(title="Item 1")]
        result = etl._apply_deduplication(data)

        # Should return original data unchanged
        assert result == data

    def test_apply_deduplication_empty_data(self):
        """Test deduplication with empty data."""
        etl = TestDeduplicationETL(test_data=[])

        result = etl._apply_deduplication([])
        assert result == []

    def test_apply_deduplication_with_duplicates(self):
        """Test deduplication with duplicate data."""
        # Create test data with duplicates
        test_data = [
            {"title": "Similar Title 1", "source": "arxiv"},
            {"title": "Similar Title 2", "source": "github"},  # Similar
            {"title": "Unique Title", "source": "techcrunch"},
            {
                "title": "Same Content",
                "description": "Same description",
                "url": "https://example.com",
            },
            {
                "title": "Same Content 2",
                "description": "Same description",
                "url": "https://example.com/different",
            },
        ]

        etl = TestDeduplicationETL(test_data=test_data)

        # Transform data first
        transformed = etl.transform(test_data)
        assert len(transformed) == 5

        # Apply deduplication
        deduplicated = etl._apply_deduplication(transformed)

        # Should have fewer items due to deduplication
        assert len(deduplicated) < len(transformed)

        # Check that metrics were updated
        assert etl.metrics.duplicates_found >= 0
        assert etl.metrics.duplicates_removed >= 0
        assert etl.metrics.deduplication_time_seconds >= 0

    def test_apply_deduplication_mixed_model_types(self):
        """Test deduplication with mixed model types (some not TimestampedModel)."""
        etl = TestDeduplicationETL(test_data=[])

        # Mix of TimestampedModel and regular dict items
        mixed_data = [
            TestContentModel(title="Model Item 1"),
            {"title": "Dict Item 1"},  # Not TimestampedModel
            TestContentModel(title="Model Item 2"),
        ]

        result = etl._apply_deduplication(mixed_data)

        # Should process all items, including non-TimestampedModel
        assert len(result) == len(mixed_data)

        # Check that TimestampedModel items were processed
        model_items = [item for item in result if isinstance(item, TestContentModel)]
        dict_items = [item for item in result if isinstance(item, dict)]

        assert len(model_items) == 2
        assert len(dict_items) == 1

    def test_run_full_etl_with_deduplication(self):
        """Test full ETL run with deduplication enabled."""
        # Create test data with known duplicates
        test_data = [
            {"title": "Machine Learning in Healthcare", "source": "arxiv"},
            {"title": "Machine Learning for Healthcare", "source": "github"},  # Similar
            {"title": "Quantum Computing Basics", "source": "techcrunch"},
            {
                "title": "AI Research",
                "description": "Research content",
                "url": "https://example.com",
            },
            {
                "title": "AI Study",
                "description": "Research content",
                "url": "https://example.com",
            },
        ]

        etl = TestDeduplicationETL(test_data=test_data, enable_deduplication=True)

        # Run the full ETL process
        metrics = etl.run()

        # Check that ETL completed successfully
        assert isinstance(metrics, ETLMetrics)
        assert metrics.is_successful

        # Check deduplication metrics
        assert metrics.duplicates_found >= 0
        assert metrics.duplicates_removed >= 0
        assert metrics.deduplication_time_seconds >= 0

        # Check that output file was created
        output_file = etl.output_dir / f"{etl.name}_output.json"
        assert output_file.exists()

        # Check output content
        output_content = json.loads(output_file.read_text())
        assert "metadata" in output_content
        assert "items" in output_content

        # Should have fewer items than input due to deduplication
        output_items = output_content["items"]
        assert len(output_items) <= len(test_data)

        # Check that deduplication metadata is present
        metadata = output_content["metadata"]
        assert metadata["deduplication_enabled"] is True

    def test_run_full_etl_without_deduplication(self):
        """Test full ETL run with deduplication disabled."""
        test_data = [
            {"title": "Item 1"},
            {"title": "Item 1"},  # Would be duplicate if deduplication was enabled
        ]

        etl = TestDeduplicationETL(test_data=test_data, enable_deduplication=False)

        # Run the full ETL process
        metrics = etl.run()

        # Check that ETL completed successfully
        assert metrics.is_successful

        # Check that no deduplication metrics were recorded
        assert metrics.duplicates_found == 0
        assert metrics.duplicates_removed == 0
        assert metrics.deduplication_time_seconds == 0.0

        # Check that all items were loaded
        output_file = etl.output_dir / f"{etl.name}_output.json"
        output_content = json.loads(output_file.read_text())
        output_items = output_content["items"]
        assert len(output_items) == len(test_data)

    def test_deduplication_error_handling(self):
        """Test error handling during deduplication."""
        etl = TestDeduplicationETL(test_data=[], enable_deduplication=True)

        # Create data that might cause deduplication issues
        problematic_data = [
            TestContentModel(title="Normal Item"),
            TestContentModel(title=None),  # None title might cause issues
        ]

        # Should not raise exceptions
        result = etl._apply_deduplication(problematic_data)

        # Should return some result (even if deduplication fails)
        assert isinstance(result, list)

    def test_metrics_updates_after_deduplication(self):
        """Test that metrics are properly updated after deduplication."""
        test_data = [
            {"title": "Similar Title 1"},
            {"title": "Similar Title 2"},  # Similar
            {"title": "Unique Title"},
        ]

        etl = TestDeduplicationETL(test_data=test_data)

        # Transform first to get initial transformed count
        transformed = etl.transform(test_data)
        initial_transformed_count = len(transformed)
        etl.metrics.records_transformed = initial_transformed_count

        # Apply deduplication
        deduplicated = etl._apply_deduplication(transformed)

        # Check that records_transformed was updated
        assert etl.metrics.records_transformed == len(deduplicated)
        assert len(deduplicated) <= initial_transformed_count

    def test_deduplication_performance_metrics(self):
        """Test that deduplication performance is tracked."""
        # Create enough data to measure meaningful performance
        test_data = [{"title": f"Item {i}"} for i in range(100)]
        # Add some duplicates
        test_data.extend(
            [
                {"title": "Duplicate Item"},
                {"title": "Duplicate Item Variant"},
            ]
            * 10
        )

        etl = TestDeduplicationETL(test_data=test_data)

        # Run ETL with performance tracking
        metrics = etl.run()

        # Check that performance metrics are recorded
        assert metrics.deduplication_time_seconds >= 0
        assert metrics.duration_seconds >= metrics.deduplication_time_seconds

        # Deduplication should not take more than the total ETL time
        assert metrics.deduplication_time_seconds <= metrics.duration_seconds

    def test_checkpoint_compatibility(self):
        """Test that deduplication doesn't break checkpoint functionality."""
        test_data = [
            {"title": "Item 1"},
            {"title": "Item 1"},  # Duplicate
        ]

        etl = TestDeduplicationETL(test_data=test_data, enable_checkpointing=True)

        # Run with checkpointing enabled
        metrics = etl.run()

        # Should still work with checkpoints
        assert metrics.is_successful

        # Check that checkpoint directory exists
        assert etl.checkpoint_dir.exists()

        # Should create output file
        output_file = etl.output_dir / f"{etl.name}_output.json"
        assert output_file.exists()


if __name__ == "__main__":
    pytest.main([__file__])
