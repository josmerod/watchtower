"""Comprehensive tests for refactored BaseETL.

Tests cover:
- Type safety with constrained generics
- Protocol-based transformation
- Checkpoint loading/saving
- Deduplication
- Metrics collection
- Error handling
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel, ValidationError

from src.etl.base_refactored import (
    BaseETL,
    DataFrameETL,
    ETLCheckpoint,
    ETLMetrics,
    SimpleETL,
    Transformable,
)
from src.models.base import TimestampedModel

# =============================================================================
# Test Models
# =============================================================================


class TestInputModel(BaseModel):
    """Test input model conforming to Transformable protocol."""

    name: str
    value: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"name": self.name, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestInputModel:
        """Create from dictionary."""
        return cls(**data)


class TestOutputModel(TimestampedModel):
    """Test output model inheriting from TimestampedModel."""

    title: str
    score: float
    processed_at: datetime


class TestOutputModel2(TimestampedModel):
    """Alternative test output model."""

    name: str
    count: int


# =============================================================================
# Test ETL Implementations
# =============================================================================


class SuccessfulETL(BaseETL[TestInputModel, TestOutputModel]):
    """Test ETL that succeeds."""

    def extract(self) -> list[TestInputModel]:
        """Extract test data."""
        return [
            TestInputModel(name="item1", value=10),
            TestInputModel(name="item2", value=20),
            TestInputModel(name="item3", value=30),
        ]

    def transform(self, data: list[TestInputModel]) -> list[TestOutputModel]:
        """Transform test data."""
        return [
            TestOutputModel(
                title=item.name,
                score=item.value * 1.5,
                processed_at=datetime.now(timezone.utc),
            )
            for item in data
        ]

    def load(self, data: list[TestOutputModel]) -> None:
        """Load test data."""
        output_file = self.output_dir / "test_output.json"
        serializable_data = [self._serialize_to_dict(item) for item in data]
        output_file.write_text(
            json.dumps(serializable_data, indent=2, default=str),
            encoding="utf-8",
        )


class FailingETL(BaseETL[TestInputModel, TestOutputModel]):
    """Test ETL that fails during extraction."""

    def extract(self) -> list[TestInputModel]:
        """Extract raises exception."""
        raise ValueError("Extraction failed")

    def transform(self, data: list[TestInputModel]) -> list[TestOutputModel]:
        """Transform test data."""
        return []

    def load(self, data: list[TestOutputModel]) -> None:
        """Load test data."""
        pass


class EmptyETL(BaseETL[TestInputModel, TestOutputModel]):
    """Test ETL that returns empty data."""

    def extract(self) -> list[TestInputModel]:
        """Extract returns empty."""
        return []

    def transform(self, data: list[TestInputModel]) -> list[TestOutputModel]:
        """Transform test data."""
        return []

    def load(self, data: list[TestOutputModel]) -> None:
        """Load test data."""
        pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create temporary directory for ETL data."""
    data_dir = tmp_path / "data" / "test_etl"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def mock_settings(temp_dir: Path):
    """Create mock settings with temporary directory."""
    settings = MagicMock()
    settings.project_root = str(temp_dir.parent.parent)
    settings.etl.batch_size = 100
    settings.etl.cleanup_old_data_days = 7
    return settings


@pytest.fixture
def successful_etl(mock_settings: MagicMock, temp_dir: Path) -> SuccessfulETL:
    """Create successful test ETL."""
    with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
        etl = SuccessfulETL(
            name="test_etl",
            description="Test ETL for unit testing",
            enable_checkpointing=False,
            enable_deduplication=False,
        )
        yield etl


# =============================================================================
# ETLMetrics Tests
# =============================================================================


class TestETLMetrics:
    """Test ETLMetrics model."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ETLMetrics(start_time=datetime.now(timezone.utc))
        assert metrics.records_extracted == 0
        assert metrics.records_transformed == 0
        assert metrics.records_loaded == 0
        assert metrics.error_count == 0
        assert metrics.errors_detail == []

    def test_metrics_finish(self):
        """Test metrics finish calculation."""
        start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        metrics = ETLMetrics(start_time=start)
        metrics.finish()

        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None
        assert metrics.duration_seconds > 0

    def test_metrics_success_rate(self):
        """Test success rate calculation."""
        metrics = ETLMetrics(start_time=datetime.now(timezone.utc))
        metrics.records_extracted = 100
        metrics.records_loaded = 80

        success_rate = metrics.success_rate
        assert success_rate == 80.0

    def test_metrics_success_rate_no_records(self):
        """Test success rate with no records extracted."""
        metrics = ETLMetrics(start_time=datetime.now(timezone.utc))
        metrics.records_extracted = 0

        # No records, no errors = 100% success
        assert metrics.success_rate == 100.0

    def test_metrics_is_successful(self):
        """Test is_successful property."""
        metrics = ETLMetrics(start_time=datetime.now(timezone.utc))
        metrics.records_loaded = 10

        assert metrics.is_successful is True

        metrics.error_count = 1
        assert metrics.is_successful is False

    def test_metrics_add_error_detail(self):
        """Test adding error details."""
        metrics = ETLMetrics(start_time=datetime.now(timezone.utc))
        metrics.add_error_detail(
            error_message="Test error",
            error_type="ValueError",
            stack_trace="Traceback...",
            context={"key": "value"},
            input_data={"test": "data"},
        )

        assert metrics.error_count == 1
        assert len(metrics.errors_detail) == 1
        assert metrics.errors_detail[0]["message"] == "Test error"
        assert metrics.errors_detail[0]["type"] == "ValueError"
        assert "stack_trace" in metrics.errors_detail[0]
        assert "context" in metrics.errors_detail[0]
        assert "input_data" in metrics.errors_detail[0]

    def test_metrics_add_error_detail_truncates_input(self):
        """Test that large input data is truncated."""
        metrics = ETLMetrics(start_time=datetime.now(timezone.utc))

        # Create input data larger than 500 characters
        large_input = "x" * 1000
        metrics.add_error_detail(
            error_message="Test",
            error_type="Error",
            input_data=large_input,
        )

        # Should be truncated
        stored_input = metrics.errors_detail[0]["input_data"]
        assert len(stored_input) == 508  # 500 + "... (truncated)"
        assert stored_input.endswith("... (truncated)")


# =============================================================================
# BaseETL Tests
# =============================================================================


class TestBaseETL:
    """Test BaseETL functionality."""

    def test_etl_initialization(self, mock_settings: MagicMock):
        """Test ETL initialization."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SuccessfulETL(
                name="test_etl",
                description="Test ETL",
            )

            assert etl.name == "test_etl"
            assert etl.description == "Test ETL"
            assert etl.batch_size == 100
            assert etl.max_retries == 3
            assert etl.enable_checkpointing is True
            assert etl.logger is not None
            assert etl.metrics is not None
            assert etl.data_dir.exists()
            assert etl.checkpoint_dir.exists()
            assert etl.output_dir.exists()

    def test_etl_initialization_with_none_project_root(self):
        """Test ETL initialization fails with None project_root."""
        settings = MagicMock()
        settings.project_root = None

        with patch("src.etl.base_refactored.get_settings", return_value=settings):
            with pytest.raises(ValueError, match="project_root cannot be None"):
                SuccessfulETL(name="test_etl")

    def test_etl_extract_transform_load(self, successful_etl: SuccessfulETL):
        """Test complete ETL pipeline."""
        # Extract
        extracted = successful_etl.extract()
        assert len(extracted) == 3
        assert isinstance(extracted[0], TestInputModel)
        assert extracted[0].name == "item1"

        # Transform
        transformed = successful_etl.transform(extracted)
        assert len(transformed) == 3
        assert isinstance(transformed[0], TestOutputModel)
        assert transformed[0].title == "item1"
        assert transformed[0].score == 15.0  # 10 * 1.5

        # Load
        successful_etl.load(transformed)
        output_file = successful_etl.output_dir / "test_output.json"
        assert output_file.exists()

        # Verify output
        data = json.loads(output_file.read_text())
        assert len(data) == 3
        assert data[0]["title"] == "item1"

    def test_etl_run_success(self, successful_etl: SuccessfulETL):
        """Test successful ETL run."""
        metrics = successful_etl.run()

        assert metrics.is_successful is True
        assert metrics.records_extracted == 3
        assert metrics.records_transformed == 3
        assert metrics.records_loaded == 3
        assert metrics.error_count == 0
        assert metrics.end_time is not None
        assert metrics.duration_seconds > 0

    def test_etl_run_with_empty_data(self, mock_settings: MagicMock):
        """Test ETL run with empty data."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = EmptyETL(name="empty_etl")
            metrics = etl.run()

            # Should complete without errors
            assert metrics.records_extracted == 0
            assert metrics.records_transformed == 0

    def test_etl_run_with_extraction_failure(self, mock_settings: MagicMock):
        """Test ETL run with extraction failure."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = FailingETL(name="failing_etl", max_retries=1)
            metrics = etl.run()

            assert metrics.is_successful is False
            assert metrics.error_count > 0
            assert len(metrics.errors_detail) > 0
            assert metrics.errors_detail[0]["type"] == "ValueError"

    def test_etl_validate_data(self, successful_etl: SuccessfulETL):
        """Test data validation."""
        valid_data = [
            {"title": "Test1", "score": 1.5, "processed_at": "2024-01-01T00:00:00Z"},
            {"title": "Test2", "score": 2.5, "processed_at": "2024-01-01T00:00:00Z"},
        ]

        validated = successful_etl.validate_data(valid_data, TestOutputModel)

        assert len(validated) == 2
        assert all(isinstance(item, TestOutputModel) for item in validated)

    def test_etl_validate_data_with_invalid_data(self, successful_etl: SuccessfulETL):
        """Test data validation with invalid data."""
        invalid_data = [
            {"title": "Valid", "score": 1.0, "processed_at": "2024-01-01T00:00:00Z"},
            {"title": "Invalid"},  # Missing required fields
        ]

        validated = successful_etl.validate_data(invalid_data, TestOutputModel)

        # Should only validate the first item
        assert len(validated) == 1
        assert successful_etl.metrics.records_failed == 1

    def test_etl_serialize_to_dict(self, successful_etl: SuccessfulETL):
        """Test serialization to dictionary."""
        model = TestOutputModel(
            title="Test",
            score=1.5,
            processed_at=datetime.now(timezone.utc),
        )

        result = successful_etl._serialize_to_dict(model)

        assert isinstance(result, dict)
        assert result["title"] == "Test"
        assert result["score"] == 1.5
        assert "processed_at" in result

    def test_etl_generate_checksum(self, successful_etl: SuccessfulETL):
        """Test checksum generation."""
        data = {"key": "value", "number": 42}
        checksum1 = successful_etl._generate_checksum(data)
        checksum2 = successful_etl._generate_checksum(data)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA256 hex length

    def test_etl_retry_operation_success(self, successful_etl: SuccessfulETL):
        """Test retry operation with success on first try."""
        call_count = [0]

        def operation():
            call_count[0] += 1
            return "success"

        result = successful_etl._retry_operation("test_operation", operation)

        assert result == "success"
        assert call_count[0] == 1

    def test_etl_retry_operation_with_retries(self, mock_settings: MagicMock):
        """Test retry operation with retries."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SuccessfulETL(name="test", max_retries=2, retry_delay=0)

            call_count = [0]

            def failing_operation():
                call_count[0] += 1
                if call_count[0] < 3:
                    raise ValueError("Temporary failure")
                return "success"

            result = etl._retry_operation("test_operation", failing_operation)

            assert result == "success"
            assert call_count[0] == 3  # Failed twice, succeeded on third try

    def test_etl_retry_operation_exhausted(self, mock_settings: MagicMock):
        """Test retry operation with exhausted retries."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SuccessfulETL(name="test", max_retries=1, retry_delay=0)

            def always_failing_operation():
                raise ValueError("Persistent failure")

            with pytest.raises(ValueError, match="Persistent failure"):
                etl._retry_operation("test_operation", always_failing_operation)

    def test_etl_should_stop_on_error(self, successful_etl: SuccessfulETL):
        """Test _should_stop_on_error logic."""
        assert successful_etl._should_stop_on_error(KeyboardInterrupt()) is True
        assert successful_etl._should_stop_on_error(MemoryError()) is True
        assert successful_etl._should_stop_on_error(SystemExit()) is True
        assert successful_etl._should_stop_on_error(ValueError()) is False

    def test_etl_checkpoint_save_load(self, successful_etl: SuccessfulETL, tmp_path: Path):
        """Test checkpoint saving and loading."""
        # Create checkpoint
        checkpoint = ETLCheckpoint(
            etl_name="test_etl",
            checkpoint_id="test_checkpoint_1",
            timestamp=datetime.now(timezone.utc),
            last_processed_id="id123",
            processed_count=100,
            metadata={"key": "value"},
        )

        # Save checkpoint
        successful_etl._save_checkpoint(checkpoint)

        checkpoint_file = successful_etl.checkpoint_dir / "latest.json"
        assert checkpoint_file.exists()

        # Load checkpoint
        loaded_checkpoint = successful_etl._load_checkpoint()

        assert loaded_checkpoint is not None
        assert loaded_checkpoint.etl_name == "test_etl"
        assert loaded_checkpoint.checkpoint_id == "test_checkpoint_1"
        assert loaded_checkpoint.last_processed_id == "id123"
        assert loaded_checkpoint.processed_count == 100
        assert loaded_checkpoint.metadata == {"key": "value"}

    def test_etl_checkpoint_load_not_found(self, successful_etl: SuccessfulETL):
        """Test checkpoint loading when file doesn't exist."""
        checkpoint = successful_etl._load_checkpoint()
        assert checkpoint is None

    def test_etl_checkpoint_disabled(self, mock_settings: MagicMock):
        """Test ETL with checkpointing disabled."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SuccessfulETL(name="test", enable_checkpointing=False)

            checkpoint = etl._load_checkpoint()
            assert checkpoint is None

            # Saving should be a no-op
            checkpoint = ETLCheckpoint(
                etl_name="test",
                checkpoint_id="test",
                timestamp=datetime.now(timezone.utc),
            )
            etl._save_checkpoint(checkpoint)  # Should not raise

            checkpoint_file = etl.checkpoint_dir / "latest.json"
            assert not checkpoint_file.exists()


# =============================================================================
# SimpleETL Tests
# =============================================================================


class TestSimpleETL:
    """Test SimpleETL implementation."""

    def test_simple_etl_run(self, mock_settings: MagicMock):
        """Test SimpleETL execution."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SimpleETL(name="simple_test")

            # Extract returns empty list
            extracted = etl.extract()
            assert extracted == []

            # Transform is passthrough
            data = [{"key": "value"}]
            transformed = etl.transform(data)
            assert transformed == data

            # Load saves to file
            etl.load(data)
            output_files = list(etl.output_dir.glob("*.json"))
            assert len(output_files) > 0


# =============================================================================
# DataFrameETL Tests
# =============================================================================


class TestDataFrameETL:
    """Test DataFrameETL implementation."""

    def test_dataframe_etl_requires_pandas(self, mock_settings: MagicMock):
        """Test that DataFrameETL requires pandas."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            # Should raise ImportError if pandas not available
            with patch.dict("sys.modules", {"pandas": None}):
                with pytest.raises(ImportError):
                    from src.etl.base_refactored import DataFrameETL

                    DataFrameETL(name="test")

    def test_dataframe_etl_extract_transform(self, mock_settings: MagicMock):
        """Test DataFrameETL extract and transform."""
        import pandas as pd

        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):

            class TestDataFrameETL(DataFrameETL[dict, TestOutputModel]):
                def extract_to_dataframe(self) -> Any:
                    return pd.DataFrame(
                        [
                            {"title": "Test1", "score": 1.5},
                            {"title": "Test2", "score": 2.5},
                        ]
                    )

                def transform_dataframe(self, df: Any) -> list[TestOutputModel]:
                    return [
                        TestOutputModel(
                            title=row["title"],
                            score=row["score"],
                            processed_at=datetime.now(timezone.utc),
                        )
                        for _, row in df.iterrows()
                    ]

            etl = TestDataFrameETL(name="df_test")

            # Extract should convert DataFrame to list of dicts
            extracted = etl.extract()
            assert len(extracted) == 2
            assert isinstance(extracted[0], dict)
            assert extracted[0]["title"] == "Test1"

            # Transform should convert dicts to DataFrame then to models
            transformed = etl.transform(extracted)
            assert len(transformed) == 2
            assert isinstance(transformed[0], TestOutputModel)
            assert transformed[0].title == "Test1"

    def test_dataframe_etl_save_as_csv(self, mock_settings: MagicMock):
        """Test DataFrameETL CSV export."""
        import pandas as pd

        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):

            class TestDataFrameETL(DataFrameETL[dict, TestOutputModel]):
                def extract_to_dataframe(self) -> Any:
                    return pd.DataFrame()

                def transform_dataframe(self, df: Any) -> list[TestOutputModel]:
                    return []

            etl = TestDataFrameETL(name="df_test")

            data = [{"title": "Test1", "score": 1.5}]
            output_path = etl.save_as_csv(data, filename="test.csv")

            assert output_path.exists()
            assert output_path.name == "test.csv"

            # Verify CSV content
            df = pd.read_csv(output_path)
            assert len(df) == 1
            assert df["title"][0] == "Test1"


# =============================================================================
# Integration Tests
# =============================================================================


class TestETLIntegration:
    """Integration tests for complete ETL workflows."""

    def test_etl_run_with_checkpointing(self, mock_settings: MagicMock, tmp_path: Path):
        """Test ETL run with checkpointing enabled."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SuccessfulETL(
                name="checkpoint_test",
                enable_checkpointing=True,
            )

            metrics = etl.run()

            # Checkpoint should be deleted after successful run
            checkpoint_file = etl.checkpoint_dir / "latest.json"
            assert not checkpoint_file.exists()

            # Run summary should be saved
            run_summary_files = list(etl.output_dir.glob("run_summary_*.json"))
            assert len(run_summary_files) > 0

            # Latest run summary should exist
            latest_summary = etl.output_dir / "run_summary_latest.json"
            assert latest_summary.exists()

    def test_etl_run_persists_metrics(self, mock_settings: MagicMock):
        """Test that ETL run persists metrics correctly."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SuccessfulETL(name="metrics_test")
            metrics = etl.run()

            # Check per-ETL metrics file
            project_root = Path(mock_settings.project_root)
            metrics_dir = project_root / "data" / "metrics" / "metrics_test"

            latest_metrics = metrics_dir / "latest_metrics.json"
            assert latest_metrics.exists()

            # Verify metrics content
            metrics_data = json.loads(latest_metrics.read_text())
            assert metrics_data["etl_name"] == "metrics_test"
            assert metrics_data["records_extracted"] == 3
            assert metrics_data["records_loaded"] == 3
            assert metrics_data["is_successful"] is True

    def test_etl_type_safety(self, successful_etl: SuccessfulETL):
        """Test that ETL maintains type safety throughout pipeline."""
        # Extract returns TestInputModel
        extracted = successful_etl.extract()
        assert all(isinstance(item, TestInputModel) for item in extracted)

        # Transform returns TestOutputModel
        transformed = successful_etl.transform(extracted)
        assert all(isinstance(item, TestOutputModel) for item in transformed)

        # Load handles TestOutputModel
        successful_etl.load(transformed)

    def test_etl_deduplication_disabled(self, mock_settings: MagicMock):
        """Test ETL with deduplication disabled."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):
            etl = SuccessfulETL(
                name="no_dedupe_test",
                enable_deduplication=False,
            )

            # Create duplicate data
            data = [
                TestInputModel(name="duplicate", value=10),
                TestInputModel(name="duplicate", value=10),  # Exact duplicate
                TestInputModel(name="unique", value=20),
            ]

            # Apply deduplication (should be disabled)
            result = etl._apply_deduplication(data)

            # All items should pass through
            assert len(result) == 3


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestETLErrorHandling:
    """Test ETL error handling."""

    def test_etl_handles_extract_error(self, mock_settings: MagicMock):
        """Test that extract errors are handled gracefully."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):

            class FailingExtractETL(BaseETL[TestInputModel, TestOutputModel]):
                def extract(self) -> list[TestInputModel]:
                    raise ValueError("Extract failed")

                def transform(self, data: list[TestInputModel]) -> list[TestOutputModel]:
                    return []

                def load(self, data: list[TestOutputModel]) -> None:
                    pass

            etl = FailingExtractETL(name="failing_extract", max_retries=1)
            metrics = etl.run()

            assert metrics.is_successful is False
            assert metrics.error_count > 0

    def test_etl_handles_transform_error(self, mock_settings: MagicMock):
        """Test that transform errors are handled gracefully."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):

            class FailingTransformETL(BaseETL[TestInputModel, TestOutputModel]):
                def extract(self) -> list[TestInputModel]:
                    return [TestInputModel(name="test", value=10)]

                def transform(self, data: list[TestInputModel]) -> list[TestOutputModel]:
                    raise ValueError("Transform failed")

                def load(self, data: list[TestOutputModel]) -> None:
                    pass

            etl = FailingTransformETL(name="failing_transform", max_retries=1)
            metrics = etl.run()

            assert metrics.is_successful is False
            assert metrics.error_count > 0

    def test_etl_handles_load_error(self, mock_settings: MagicMock):
        """Test that load errors are handled gracefully."""
        with patch("src.etl.base_refactored.get_settings", return_value=mock_settings):

            class FailingLoadETL(BaseETL[TestInputModel, TestOutputModel]):
                def extract(self) -> list[TestInputModel]:
                    return [TestInputModel(name="test", value=10)]

                def transform(self, data: list[TestInputModel]) -> list[TestOutputModel]:
                    return [
                        TestOutputModel(
                            title="test",
                            score=1.5,
                            processed_at=datetime.now(timezone.utc),
                        )
                    ]

                def load(self, data: list[TestOutputModel]) -> None:
                    raise ValueError("Load failed")

            etl = FailingLoadETL(name="failing_load", max_retries=1)
            metrics = etl.run()

            assert metrics.is_successful is False
            assert metrics.error_count > 0
