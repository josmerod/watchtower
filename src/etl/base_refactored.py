"""Type-safe refactored Base ETL classes for Watchtower.

This refactored version fixes all type safety issues identified by MyPy:
- Constrained type variables with proper bounds
- Protocol-based transformation interfaces
- Proper handling of TimestampedModel vs dict[str, Any]
- Type-safe deduplication and serialization
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable, TYPE_CHECKING

import certifi

# Set SSL certificate file globally for the ETL process
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from src.config.settings import get_settings
from src.data_quality.deduplication import DeduplicationEngine
from src.exceptions.base import handle_exception
from src.exceptions.etl import CheckpointError, ETLError
from src.models.base import TimestampedModel
from src.utils.logging import get_logger, get_performance_logger
from src.etl.circuit_breaker import CircuitBreaker
from src.etl.proxy_manager import ProxyManager

if TYPE_CHECKING:
    from requests import Session


# =============================================================================
# Protocols for Type-Safe ETL Operations
# =============================================================================

@runtime_checkable
class Transformable(Protocol):
    """Protocol for data that can be transformed by ETL.

    Any data type that can be converted to/from dict can be used in ETL pipeline.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transformable:  # type: ignore[misc]
        """Create instance from dictionary."""
        ...


# =============================================================================
# Type Variables with Proper Constraints
# =============================================================================

# Constrained type variables for type-safe ETL operations
InputType = TypeVar("InputType", bound=Transformable)
OutputType = TypeVar("OutputType", bound=TimestampedModel)
ModelType = TypeVar("ModelType", bound=BaseModel)


# =============================================================================
# ETL Metrics and Checkpoint Models
# =============================================================================

class ETLMetrics(BaseModel):
    """Model for ETL execution metrics.

    Enhanced in Epic 1, Story 1.1 to include detailed error tracking
    and checkpoint status.
    """

    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float | None = None
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    error_count: int = 0
    warnings_count: int = 0

    # Story 1.1: Enhanced error tracking
    errors_detail: list[dict[str, Any]] = []

    # Story 1.1: Checkpoint status tracking
    checkpoint_status: str | None = None  # "resumed" | "new_run" | "checkpoint_saved" | "checkpoint_failed"

    # Story 4.1: Deduplication metrics
    duplicates_found: int = 0
    duplicates_removed: int = 0
    deduplication_time_seconds: float = 0.0

    def finish(self) -> None:
        """Mark ETL as finished and calculate duration."""
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_records = self.records_extracted
        if total_records == 0:
            return 100.0 if self.error_count == 0 and self.records_failed == 0 else 0.0
        return (self.records_loaded / total_records) * 100

    @property
    def is_successful(self) -> bool:
        """Check if ETL completed successfully."""
        return self.records_loaded > 0 and self.error_count == 0

    def add_error_detail(
        self,
        error_message: str,
        error_type: str,
        stack_trace: str | None = None,
        context: dict[str, Any] | None = None,
        input_data: Any = None,
    ) -> None:
        """Add detailed error information to metrics.

        Args:
            error_message: Human-readable error message
            error_type: Exception class name
            stack_trace: Full stack trace (optional)
            context: Additional context about the error
            input_data: Input data that caused the error (sanitized)
        """
        error_detail: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": error_message,
            "type": error_type,
        }

        if stack_trace:
            error_detail["stack_trace"] = stack_trace

        if context:
            error_detail["context"] = context

        if input_data is not None:
            # Truncate large input data to prevent massive metrics files
            input_str = str(input_data)
            if len(input_str) > 500:
                input_str = input_str[:500] + "... (truncated)"
            error_detail["input_data"] = input_str

        self.errors_detail.append(error_detail)
        self.error_count += 1


class ETLCheckpoint(BaseModel):
    """Model for ETL checkpointing."""

    etl_name: str
    checkpoint_id: str
    timestamp: datetime
    last_processed_id: str | None = None
    last_processed_timestamp: datetime | None = None
    processed_count: int = 0
    metadata: dict[str, Any] = {}


# =============================================================================
# Base ETL Class (Type-Safe Refactored Version)
# =============================================================================

class BaseETL(ABC, Generic[InputType, OutputType]):
    """Type-safe base class for all ETL processes.

    Generic type parameters:
        InputType: Type of raw data items (must conform to Transformable protocol)
        OutputType: Type of transformed data items (must inherit from TimestampedModel)

    This class provides:
    - Template method pattern for ETL pipeline
    - Built-in metrics collection and error handling
    - Checkpointing support for resumable operations
    - Circuit breaker pattern for failure isolation
    - Proxy rotation for rate limit avoidance
    - Type-safe transformation pipeline
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        batch_size: int | None = None,
        enable_checkpointing: bool = True,
        max_retries: int = 3,
        retry_delay: int = 5,
        enable_deduplication: bool = True,
        title_similarity_threshold: float = 0.8,
        enable_enrichment: bool = False,
    ) -> None:
        """Initialize the ETL process.

        Args:
            name: Unique identifier for this ETL process
            description: Human-readable description
            batch_size: Number of items to process per batch
            enable_checkpointing: Enable resumable checkpoints
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Initial delay between retries (exponential backoff)
            enable_deduplication: Enable deduplication of transformed data
            title_similarity_threshold: Similarity threshold for deduplication (0.0-1.0)
            enable_enrichment: Enable AI content enrichment
        """
        self.name = name
        self.description = description or f"ETL process: {name}"
        self.settings = get_settings()
        self.batch_size = batch_size or self.settings.etl.batch_size
        self.enable_checkpointing = enable_checkpointing
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_deduplication = enable_deduplication
        self.title_similarity_threshold = title_similarity_threshold
        self.enable_enrichment = enable_enrichment
        self.logger = get_logger(f"ETL.{name}")
        self.perf_logger = get_performance_logger(f"ETL.{name}")
        self.metrics = ETLMetrics(start_time=datetime.utcnow())
        self.current_checkpoint: ETLCheckpoint | None = None

        # Type-safe path construction
        project_root = self.settings.project_root
        if not project_root:
            raise ValueError("settings.project_root cannot be None or empty")

        self.data_dir = Path(project_root) / "data" / name
        self.checkpoint_dir = self.data_dir / "checkpoints"
        self.output_dir = self.data_dir / "output"

        # Initialize deduplication engine
        self.deduplication_engine = (
            DeduplicationEngine(title_similarity_threshold=self.title_similarity_threshold)
            if self.enable_deduplication
            else None
        )

        # Story 7.1: Initialize Circuit Breaker
        self.circuit_breaker = CircuitBreaker(etl_name=name, base_path=self.data_dir)

        # Story 7.2: Initialize Proxy Manager
        self.proxy_manager = ProxyManager()

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create necessary directories for data storage."""
        for directory in [self.data_dir, self.checkpoint_dir, self.output_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_checkpoint(self) -> ETLCheckpoint | None:
        """Load checkpoint from disk if available.

        Returns:
            Checkpoint data if found, None otherwise

        Raises:
            CheckpointError: If checkpoint file exists but cannot be loaded
        """
        if not self.enable_checkpointing:
            return None

        checkpoint_file_path = self.checkpoint_dir / "latest.json"
        if not checkpoint_file_path.exists():
            self.logger.info(f"No checkpoint file found at {checkpoint_file_path}.")
            return None

        try:
            self.logger.debug(f"Loading checkpoint from {checkpoint_file_path}")
            checkpoint_data = json.loads(checkpoint_file_path.read_text(encoding="utf-8"))
            return ETLCheckpoint(**checkpoint_data)

        except OSError as e:
            self.logger.error(f"I/O error loading checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(
                f"I/O error loading checkpoint: {e}",
                checkpoint_path=str(checkpoint_file_path),
                operation="load",
                etl_name=self.name,
            ) from e

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error loading checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(
                f"JSON decode error loading checkpoint: {e}",
                checkpoint_path=str(checkpoint_file_path),
                operation="load",
                etl_name=self.name,
            ) from e

        except PydanticValidationError as e:
            self.logger.error(f"Pydantic validation error loading checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(
                f"Pydantic validation error loading checkpoint: {e}",
                checkpoint_path=str(checkpoint_file_path),
                operation="load",
                etl_name=self.name,
            ) from e

        except Exception as e:
            self.logger.error(
                f"Unexpected error loading checkpoint {checkpoint_file_path}: {e}",
                exc_info=True,
            )
            raise CheckpointError(
                f"Unexpected error loading checkpoint: {e}",
                checkpoint_path=str(checkpoint_file_path),
                operation="load",
                etl_name=self.name,
            ) from e

    def _save_checkpoint(self, checkpoint: ETLCheckpoint) -> None:
        """Save checkpoint to disk.

        Args:
            checkpoint: Checkpoint data to save

        Raises:
            CheckpointError: If checkpoint cannot be saved
        """
        if not self.enable_checkpointing:
            return

        checkpoint_file_path = self.checkpoint_dir / "latest.json"
        try:
            self.logger.debug(f"Saving checkpoint to {checkpoint_file_path}")
            checkpoint_json = checkpoint.model_dump_json(indent=2)
            checkpoint_file_path.write_text(checkpoint_json, encoding="utf-8")
            self.logger.info(f"Checkpoint {checkpoint.checkpoint_id} saved successfully to {checkpoint_file_path}")

        except OSError as e:
            self.logger.error(f"I/O error saving checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(
                f"I/O error saving checkpoint: {e}",
                checkpoint_path=str(checkpoint_file_path),
                operation="save",
                etl_name=self.name,
            ) from e

        except TypeError as e:
            self.logger.error(f"Serialization error saving checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(
                f"Serialization error saving checkpoint: {e}",
                checkpoint_path=str(checkpoint_file_path),
                operation="save",
                etl_name=self.name,
            ) from e

        except Exception as e:
            self.logger.error(
                f"Unexpected error saving checkpoint {checkpoint_file_path}: {e}",
                exc_info=True,
            )
            raise CheckpointError(
                f"Unexpected error saving checkpoint: {e}",
                checkpoint_path=str(checkpoint_file_path),
                operation="save",
                etl_name=self.name,
            ) from e

    @property
    def http_session(self) -> Session:
        """Get a configured HTTP session (with proxy rotation).

        Returns:
            Configured requests.Session instance
        """
        return self.proxy_manager.get_session(retries=self.max_retries)

    def _generate_checksum(self, data: Any) -> str:
        """Generate SHA256 checksum for data integrity verification.

        Args:
            data: Data to generate checksum for

        Returns:
            SHA256 hexdigest string
        """
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()

    def _retry_operation(self, operation_name: str, operation_func: Any) -> Any:
        """Execute operation with retry logic.

        Args:
            operation_name: Human-readable operation name for logging
            operation_func: Function to execute

        Returns:
            Result of operation_func

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return operation_func()
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    self.logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"{operation_name} failed after {self.max_retries + 1} attempts: {e}")

        if last_exception:
            raise last_exception
        return None  # Should never reach here

    # =========================================================================
    # Abstract Methods (Must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    def extract(self) -> list[InputType]:
        """Extract data from the source.

        This method should be implemented by subclasses to define the data
        extraction logic from a specific source.

        Returns:
            List of raw data items conforming to Transformable protocol
        """
        pass

    @abstractmethod
    def transform(self, data: list[InputType]) -> list[OutputType]:
        """Transform extracted data into output models.

        This method should be implemented by subclasses to define the
        data transformation logic, converting raw data into structured
        TimestampedModel instances.

        Args:
            data: List of raw data items extracted from the source

        Returns:
            List of validated TimestampedModel instances

        Raises:
            ValidationError: If transformation fails validation
        """
        pass

    @abstractmethod
    def load(self, data: list[OutputType]) -> None:
        """Load transformed data into the destination.

        This method should be implemented by subclasses to define the
        data loading logic, storing the processed data in a target
        system (e.g., database, file).

        Args:
            data: List of transformed TimestampedModel instances to be loaded
        """
        pass

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def validate_data(self, data: list[dict[str, Any]], model_class: type[ModelType]) -> list[ModelType]:
        """Validate data against Pydantic model.

        Args:
            data: List of dictionaries to validate
            model_class: Pydantic model class to validate against

        Returns:
            List of validated model instances
        """
        validated: list[ModelType] = []
        for item in data:
            try:
                validated.append(model_class(**item))
            except PydanticValidationError as e:
                self.logger.warning(f"Data validation failed: {e}")
                self.metrics.records_failed += 1
        return validated

    def process_in_batches(
        self,
        data: list[Any],
        process_func: Any,
    ) -> list[Any]:
        """Process data in batches with checkpoint updates.

        Args:
            data: Data to process
            process_func: Function to apply to each batch

        Returns:
            Processed results
        """
        results: list[Any] = []
        for i in range(0, len(data), self.batch_size):
            batch = data[i : i + self.batch_size]
            try:
                results.extend(process_func(batch))
                if self.current_checkpoint and batch:
                    self.current_checkpoint.processed_count += len(batch)
                    self._save_checkpoint(self.current_checkpoint)
            except Exception as e:
                self.logger.error(f"Batch processing failed: {e}")
                self.metrics.error_count += 1
                if self._should_stop_on_error(e):
                    raise
        return results

    def _should_stop_on_error(self, error: Exception) -> bool:
        """Check if error should stop ETL execution.

        Args:
            error: Exception to evaluate

        Returns:
            True if execution should stop, False otherwise
        """
        return isinstance(error, (KeyboardInterrupt, MemoryError, SystemExit))

    def _purge_old_artifacts(self) -> None:
        """Purge timestamped artifacts older than retention period.

        Keeps `*_latest.*` files always. Applies to files within `self.output_dir`.
        """
        try:
            days = self.settings.etl.cleanup_old_data_days
            if days <= 0:
                return

            cutoff = datetime.utcnow().timestamp() - (days * 86400)
            for file_path in self.output_dir.glob("**/*"):
                if not file_path.is_file():
                    continue

                name = file_path.name
                if "latest" in name:
                    continue

                try:
                    if file_path.stat().st_mtime < cutoff:
                        file_path.unlink(missing_ok=True)
                except Exception as e:
                    self.logger.warning(f"Retention purge skipped for {file_path}: {e}")

        except Exception as e:
            self.logger.warning(f"Retention purge failed: {e}")

    def _serialize_to_dict(self, item: OutputType) -> dict[str, Any]:
        """Serialize TimestampedModel to dictionary.

        Args:
            item: TimestampedModel instance

        Returns:
            Dictionary representation
        """
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")
        elif hasattr(item, "dict"):
            return item.dict()  # type: ignore[attr-defined]
        else:
            return dict(item)  # type: ignore[call-arg]

    def _apply_deduplication(self, data: list[OutputType]) -> list[OutputType]:
        """Apply deduplication to transformed data.

        Args:
            data: List of TimestampedModel instances

        Returns:
            List of deduplicated TimestampedModel instances
        """
        if not self.enable_deduplication or not self.deduplication_engine:
            self.logger.debug("Deduplication disabled, returning original data")
            return data

        if not data:
            self.logger.debug("No data to deduplicate")
            return data

        # All items should be TimestampedModel instances (type constraint)
        deduplication_start = datetime.utcnow()
        try:
            # Convert to dicts for deduplication engine
            data_dicts = [self._serialize_to_dict(item) for item in data]

            result = self.deduplication_engine.find_duplicates(data)

            # Update metrics
            deduplication_time = (datetime.utcnow() - deduplication_start).total_seconds()
            self.metrics.duplicates_found = len(result.duplicate_groups)
            self.metrics.duplicates_removed = result.duplicates_removed
            self.metrics.deduplication_time_seconds = deduplication_time

            self.logger.info(
                f"Deduplication completed: {result.total_items} items -> "
                f"{len(result.unique_items)} unique, {result.duplicates_removed} duplicates removed "
                f"in {deduplication_time:.2f}s"
            )

            # Convert unique items back to TimestampedModel
            unique_items: list[OutputType] = []
            if data and result.unique_items:
                model_class = type(data[0])
                try:
                    unique_items = [model_class(**item) for item in result.unique_items]  # type: ignore[misc]
                except Exception as e:
                    self.logger.warning(
                        f"Failed to convert deduplicated items back to model {model_class.__name__}: {e}"
                    )
                    # Return original data if conversion fails
                    return data

            self.metrics.records_transformed = len(unique_items)
            return unique_items

        except Exception as e:
            self.logger.error(f"Deduplication failed: {e}")
            self.metrics.add_error_detail(
                error_message=f"Deduplication failed: {e!s}",
                error_type=type(e).__name__,
                context={"etl_name": self.name, "item_count": len(data)},
            )
            # Return original data if deduplication fails
            return data

    def run(self) -> ETLMetrics:
        """Execute the complete ETL pipeline.

        This method orchestrates the ETL process by:
        1. Checking circuit breaker state
        2. Loading checkpoint if available
        3. Extracting data from source
        4. Transforming data
        5. Applying deduplication
        6. Optionally applying AI enrichment
        7. Loading data to destination
        8. Recording metrics and cleaning up

        Returns:
            ETLMetrics object containing execution metrics

        Raises:
            ETLError: If the ETL process encounters an unrecoverable error
        """
        self.logger.info(f"Starting ETL process: {self.name}")
        self.perf_logger.start(f"ETL_{self.name}")
        self.metrics = ETLMetrics(start_time=datetime.utcnow())

        # Story 7.1: Check Circuit Breaker
        if not self.circuit_breaker.can_proceed():
            self.logger.warning(f"ETL {self.name} skipped due to open circuit breaker.")
            self.metrics.add_error_detail(
                error_message="Circuit breaker is open. ETL execution skipped.",
                error_type="CircuitBreakerOpen",
                context={"recovery_time": str(self.circuit_breaker.state.recovery_time)}
            )
            self.metrics.finish()
            return self.metrics

        run_threw_exception = False
        try:
            # Story 1.1: Track checkpoint status
            self.current_checkpoint = self._load_checkpoint()
            if self.current_checkpoint:
                self.metrics.checkpoint_status = "resumed"
                self.logger.info(f"Resuming from checkpoint: {self.current_checkpoint.checkpoint_id}")
            else:
                self.metrics.checkpoint_status = "new_run"

            # Extract
            extracted = self._retry_operation("extract", self.extract)
            self.metrics.records_extracted = len(extracted)
            self.logger.info(f"Extracted {self.metrics.records_extracted} records")

            if not extracted:
                self.logger.info("No data extracted. ETL run considered complete.")
                return self.metrics

            # Transform
            transformed = self._retry_operation("transform", lambda: self.transform(extracted))
            self.metrics.records_transformed = len(transformed)
            self.logger.info(f"Transformed {self.metrics.records_transformed} records")

            if not transformed:
                self.logger.info("No data after transformation. Skipping load.")
                return self.metrics

            # Story 4.1: Apply deduplication after transformation
            deduplicated = self._apply_deduplication(transformed)

            # Story 8.x: Apply AI Enrichment (if enabled)
            enriched = deduplicated
            if self.enable_enrichment:
                try:
                    from src.intelligence.enrichment import ContentEnricher
                    enricher = ContentEnricher()
                    # Type: ignore is necessary here because enrich_batch expects specific types
                    enriched = enricher.enrich_batch(deduplicated)  # type: ignore[assignment]
                except Exception as e:
                    self.logger.warning(f"AI Enrichment failed: {e}")
                    enriched = deduplicated  # Fallback to unenriched

            # Load
            self._retry_operation("load", lambda: self.load(enriched))
            self.metrics.records_loaded = len(enriched)
            self.logger.info(f"Loaded {self.metrics.records_loaded} records")

            # Cleanup
            if self.enable_checkpointing and self.metrics.is_successful:
                (self.checkpoint_dir / "latest.json").unlink(missing_ok=True)

            # Retention: purge old timestamped artifacts
            try:
                self._purge_old_artifacts()
            except Exception as e:
                self.logger.warning(f"Retention step failed: {e}")

            # Circuit Breaker: Record success
            if self.metrics.is_successful:
                self.logger.info(
                    f"ETL process completed successfully. Success rate: {self.metrics.success_rate:.1f}%"
                )
                self.circuit_breaker.record_success()
            elif self.metrics.error_count == 0:
                self.logger.info("ETL completed. No records loaded.")
                self.circuit_breaker.record_success()  # Treat no-data as success for stability

        except Exception as e:
            run_threw_exception = True

            # Story 7.1: Record failure
            self.circuit_breaker.record_failure()

            # Story 1.1: Capture detailed error information
            import traceback

            stack_trace = traceback.format_exc()
            err_ctx = {"etl_name": self.name, "metrics": self.metrics.model_dump()}

            self.metrics.add_error_detail(
                error_message=str(e),
                error_type=type(e).__name__,
                stack_trace=stack_trace,
                context=err_ctx,
            )

            wt_err = handle_exception(e, logger=self.logger, reraise=False, add_context=err_ctx)

            # Type-safe error message access
            error_msg = wt_err.message if hasattr(wt_err, 'message') else str(wt_err)

            final_msg = f"ETL process '{self.name}' failed: {error_msg}"
            if isinstance(e, ETLError) and hasattr(e, "context") and e.context.get("original_message_preserved"):
                final_msg = str(e)

            raise ETLError(final_msg, context=err_ctx, cause=e) from e

        finally:
            self.metrics.finish()
            self.perf_logger.end(success=not run_threw_exception and self.metrics.error_count == 0)

            # Persist per-run summary (always attempt; best-effort)
            self._persist_run_summary()

        return self.metrics

    def _persist_run_summary(self) -> None:
        """Persist ETL run summary to disk.

        Saves timestamped and latest run summaries in output directory
        and updates global aggregated metrics.
        """
        try:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            run_summary = {
                "etl_name": self.name,
                "start_time": self.metrics.start_time.isoformat(),
                "end_time": self.metrics.end_time.isoformat() if self.metrics.end_time else None,
                "duration_seconds": self.metrics.duration_seconds,
                "records_extracted": self.metrics.records_extracted,
                "records_transformed": self.metrics.records_transformed,
                "records_loaded": self.metrics.records_loaded,
                "records_failed": self.metrics.records_failed,
                "error_count": self.metrics.error_count,
                "errors_detail": self.metrics.errors_detail,
                "checkpoint_status": self.metrics.checkpoint_status,
                "success": self.metrics.is_successful and self.metrics.error_count == 0,
                "output_dir": str(self.output_dir),
            }

            # Write timestamped and latest summaries in ETL output dir
            (self.output_dir / f"run_summary_{ts}.json").write_text(
                json.dumps(run_summary, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            (self.output_dir / "run_summary_latest.json").write_text(
                json.dumps(run_summary, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            # Update global aggregated metrics
            project_root = self.settings.project_root
            if not project_root:
                self.logger.warning("Cannot persist metrics: project_root is None")
                return

            metrics_dir = Path(project_root) / "data" / "metrics"
            metrics_dir.mkdir(parents=True, exist_ok=True)
            agg_path = metrics_dir / "etl_runs_latest.json"

            try:
                existing = json.loads(agg_path.read_text(encoding="utf-8")) if agg_path.exists() else {}
            except Exception:
                existing = {}

            if not isinstance(existing, dict):
                existing = {}

            runs = existing.get("runs", {})
            if not isinstance(runs, dict):
                runs = {}

            runs[self.name] = run_summary | {"last_updated": datetime.utcnow().isoformat(timespec="seconds")}
            existing["generated_at"] = datetime.utcnow().isoformat(timespec="seconds")
            existing["runs"] = runs
            agg_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

            # Story 1.1: Save per-ETL metrics in data/metrics/{etl_name}/ pattern
            etl_metrics_dir = metrics_dir / self.name
            etl_metrics_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            per_etl_metrics_file = etl_metrics_dir / f"{timestamp}_metrics.json"

            metrics_data = {
                "etl_name": self.name,
                "timestamp": timestamp,
                "start_time": self.metrics.start_time.isoformat(),
                "end_time": self.metrics.end_time.isoformat() if self.metrics.end_time else None,
                "duration_seconds": self.metrics.duration_seconds,
                "records_extracted": self.metrics.records_extracted,
                "records_transformed": self.metrics.records_transformed,
                "records_loaded": self.metrics.records_loaded,
                "records_failed": self.metrics.records_failed,
                "error_count": self.metrics.error_count,
                "warnings_count": self.metrics.warnings_count,
                "success_rate": self.metrics.success_rate,
                "is_successful": self.metrics.is_successful,
                "errors_detail": self.metrics.errors_detail,
                "checkpoint_status": self.metrics.checkpoint_status,
                "output_dir": str(self.output_dir),
                "story_1_1_enhanced": True,
            }

            per_etl_metrics_file.write_text(
                json.dumps(metrics_data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            latest_metrics_file = etl_metrics_dir / "latest_metrics.json"
            latest_metrics_file.write_text(
                json.dumps(metrics_data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            self.logger.debug(f"Per-ETL metrics saved to {per_etl_metrics_file}")

        except Exception as e:
            self.logger.warning(f"Failed to write ETL run summary: {e}")


# =============================================================================
# Simple ETL Implementation
# =============================================================================

class SimpleETL(BaseETL[dict, dict]):
    """Simple ETL for basic dictionary-to-dictionary transformations."""

    def __init__(self, name: str, **kwargs: Any) -> None:
        super().__init__(name, **kwargs)

    def extract(self) -> list[dict[str, Any]]:
        """Extract empty data (override in subclass)."""
        return []

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pass through data without transformation."""
        return data

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load data to JSON file."""
        out_f = self.output_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_f.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        self.logger.info(f"Data saved to {out_f}")


# =============================================================================
# DataFrame ETL Implementation
# =============================================================================

class DataFrameETL(BaseETL[InputType, OutputType], Generic[InputType, OutputType]):
    """ETL base class for Pandas DataFrame operations.

    Provides DataFrame-based extraction and transformation with type-safe
    conversion to TimestampedModel instances.
    """

    def __init__(self, name: str, **kwargs: Any) -> None:
        """Initialize DataFrame ETL.

        Args:
            name: Unique identifier for this ETL process
            **kwargs: Additional arguments passed to BaseETL
        """
        super().__init__(name, **kwargs)
        try:
            import pandas as pd
            self.pd = pd
        except ImportError:
            self.logger.error("Pandas required but not installed.")
            raise

    @abstractmethod
    def extract_to_dataframe(self) -> Any:
        """Extract data and return as Pandas DataFrame.

        Subclasses should implement this method to fetch data from a source
        and structure it into a Pandas DataFrame.

        Returns:
            pandas.DataFrame: The extracted data
        """
        pass

    @abstractmethod
    def transform_dataframe(self, df: Any) -> list[OutputType]:
        """Transform DataFrame into list of TimestampedModel instances.

        Subclasses should implement this method to perform data processing,
        cleaning, and transformation using DataFrame operations, then convert
        the results into TimestampedModel instances.

        Args:
            df: Input DataFrame to transform

        Returns:
            List of TimestampedModel instances
        """
        pass

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from DataFrame.

        Returns:
            List of dictionaries (DataFrame rows)
        """
        self.logger.debug("DataFrameETL.extract() using extract_to_dataframe().")
        df = self.extract_to_dataframe()
        return df.to_dict(orient="records") if df is not None else []

    def transform(self, data: list[dict[str, Any]]) -> list[OutputType]:
        """Transform dictionaries to TimestampedModel instances via DataFrame.

        Args:
            data: List of dictionaries

        Returns:
            List of TimestampedModel instances
        """
        if not data:
            return []

        df = self.pd.DataFrame(data)
        return self.transform_dataframe(df)

    def load(self, data: list[OutputType]) -> None:
        """Load TimestampedModel data to CSV file.

        Args:
            data: List of TimestampedModel instances
        """
        if not data:
            self.logger.info("No data to load.")
            return

        df_to_save = self.pd.DataFrame([self._serialize_to_dict(item) for item in data])
        out_f = self.output_dir / f"{self.name}_output.csv"
        df_to_save.to_csv(out_f, index=False)
        self.logger.info(f"DataFrameETL default load saved to {out_f}")

    def save_as_csv(self, data: list[dict[str, Any]], filename: str | None = None) -> Path:
        """Save data as CSV file.

        Args:
            data: List of dictionaries to save
            filename: Output filename (auto-generated if None)

        Returns:
            Path to saved file
        """
        if not filename:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        out_f = self.output_dir / filename
        self.pd.DataFrame(data).to_csv(out_f, index=False, encoding="utf-8")
        self.logger.info(f"Data saved as CSV to {out_f}")
        return out_f

    def save_as_parquet(self, data: list[dict[str, Any]], filename: str | None = None) -> Path:
        """Save data as Parquet file.

        Args:
            data: List of dictionaries to save
            filename: Output filename (auto-generated if None)

        Returns:
            Path to saved file
        """
        if not filename:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        out_f = self.output_dir / filename
        self.pd.DataFrame(data).to_parquet(out_f, index=False)
        self.logger.info(f"Data saved as Parquet to {out_f}")
        return out_f
