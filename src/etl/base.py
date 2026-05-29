"""Base ETL classes and patterns for Watchtower."""

from __future__ import annotations
import urllib.error
import hashlib
import json
import logging
import os
import time
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

import certifi

# Set SSL certificate file globally for the ETL process
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Module-level logger for tenacity retry callbacks (runs before instance exists)
_retry_logger = logging.getLogger("ETL.retry")

# Retryable exception types for HTTP requests
_RETRYABLE_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.HTTPError,
    TimeoutError,
    ConnectionError,
    urllib.error.URLError,
)


def _before_sleep_log_retry(retry_state: Any) -> None:
    """Log before sleeping on a retry, showing URL and attempt count."""
    # retry_state.args[0] is self (bound method), args[1] is url
    url = retry_state.args[1] if len(retry_state.args) > 1 else "?"
    attempt = retry_state.attempt_number
    sleep_time = getattr(retry_state.next_action, "sleep", 0)
    _retry_logger.warning(
        "Retrying %s (attempt %d/3), waiting %.1fs…",
        url,
        attempt,
        sleep_time,
    )

# Added Type, ensured Generic, List, Any, TypeVar
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

# Type variables for generic ETL
InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class ETLMetrics(BaseModel):
    """Model for ETL execution metrics.

    Enhanced in Epic 1, Story 1.1 to include detailed error tracking and checkpoint status.
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
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        # For ETLs with deduplication, records_transformed may be reduced to
        # the final unique item count before load. Treat successful loading of
        # that post-transform/post-dedupe set as 100%, rather than penalizing
        # duplicate removal as if records failed.
        total_records = self.records_transformed or self.records_extracted
        if total_records == 0:
            return 100.0 if self.error_count == 0 and self.records_failed == 0 else 0.0
        return (self.records_loaded / total_records) * 100

    @property
    def is_successful(self) -> bool:
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
        error_detail = {
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


class BaseETL(ABC, Generic[InputType, OutputType]):
    """Base class for all ETL processes with comprehensive error handling and monitoring."""

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
    ):
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
        self.data_dir = Path(self.settings.project_root) / "data" / name
        self.checkpoint_dir = self.data_dir / "checkpoints"
        self.output_dir = self.data_dir / "output"

        # Initialize deduplication engine
        self.deduplication_engine = DeduplicationEngine(title_similarity_threshold=self.title_similarity_threshold) if self.enable_deduplication else None

        # Story 7.1: Initialize Circuit Breaker
        self.circuit_breaker = CircuitBreaker(etl_name=name, base_path=self.data_dir)

        # Story 7.2: Initialize Proxy Manager
        self.proxy_manager = ProxyManager()

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        for directory in [self.data_dir, self.checkpoint_dir, self.output_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_checkpoint(self) -> ETLCheckpoint | None:
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
        except TypeError as e:  # Pydantic model_dump_json can raise TypeError
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
    def http_session(self) -> Any: # requests.Session
        """Get a configured HTTP session (with proxy rotation)."""
        return self.proxy_manager.get_session(retries=self.max_retries)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        before_sleep=_before_sleep_log_retry,
        reraise=True,
    )
    def fetch_url(self, url: str, **kwargs: Any) -> requests.Response:
        """Fetch a URL with tenacity retry logic and a 30-second timeout.

        This is the recommended method for all HTTP GET requests in ETL
        subclasses.  It applies exponential-backoff retries for transient
        network / timeout errors and enforces a 30-second connection timeout.

        Args:
            url: The URL to fetch.
            **kwargs: Additional keyword arguments forwarded to
                ``requests.Session.get()`` (e.g. *headers*, *params*).

        Returns:
            A ``requests.Response`` object.

        Raises:
            requests.exceptions.RetryError: After all retry attempts are
                exhausted.
        """
        # Ensure a 30-second timeout unless the caller explicitly overrides it
        kwargs.setdefault("timeout", 30)
        session = self.http_session
        response = session.get(url, **kwargs)
        response.raise_for_status()
        return response

    def fetch_json(self, url: str, **kwargs: Any) -> Any:
        """Fetch a URL and return the parsed JSON response.

        Convenience wrapper around :meth:`fetch_url` that parses the
        response body as JSON.

        Args:
            url: The URL to fetch.
            **kwargs: Additional keyword arguments forwarded to
                ``requests.Session.get()``.

        Returns:
            Parsed JSON data (typically ``dict`` or ``list``).
        """
        response = self.fetch_url(url, **kwargs)
        return response.json()

    def _generate_checksum(self, data: Any) -> str:
        """Generate SHA256 checksum for data integrity verification.

        Args:
            data: Data to generate checksum for.

        Returns:
            SHA256 hexdigest string.
        """
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def _retry_operation(self, operation_name: str, operation_func) -> Any:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return operation_func()
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    self.logger.warning(f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"{operation_name} failed after {self.max_retries + 1} attempts: {e}")
        if last_exception:
            raise last_exception

    @abstractmethod
    def extract(self) -> list[InputType]:
        """Extracts data from the source.

        This method should be implemented by subclasses to define the data
        extraction logic from a specific source.

        Returns:
            List[InputType]: A list of raw data items.
        """
        pass

    @abstractmethod
    def transform(self, data: list[InputType]) -> list[OutputType]:
        """Transforms the extracted data.

        This method should be implemented by subclasses to define the
        data transformation logic, converting raw data into a structured
        or processed format.

        Args:
            data: A list of raw data items extracted from the source.

        Returns:
            List[OutputType]: A list of transformed data items.
        """
        pass

    @abstractmethod
    def load(self, data: list[OutputType]) -> None:
        """Loads the transformed data into the destination.

        This method should be implemented by subclasses to define the
        data loading logic, storing the processed data in a target
        system (e.g., database, file).

        Args:
            data: A list of transformed data items to be loaded.
        """
        pass

    def validate_data(self, data: list[Any], model_class: type[BaseModel]) -> list[BaseModel]:  # Use Type
        validated = []
        for item in data:
            try:
                validated.append(model_class(**item) if isinstance(item, dict) else model_class.parse_obj(item))
            except PydanticValidationError as e:
                self.logger.warning(f"Data validation failed: {e}")
                self.metrics.records_failed += 1
        return validated

    def process_in_batches(self, data: list[Any], process_func) -> list[Any]:
        results = []
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
                if self.should_stop_on_error(e):
                    raise
        return results

    def should_stop_on_error(self, error: Exception) -> bool:
        return isinstance(error, (KeyboardInterrupt, MemoryError, SystemExit))

    def _purge_old_artifacts(self) -> None:
        """Purge timestamped artifacts older than settings.etl.cleanup_old_data_days.

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

    def _apply_deduplication(self, data: list[OutputType]) -> list[OutputType]:
        """Apply deduplication to transformed data.

        Args:
            data: List of transformed data items.

        Returns:
            List of deduplicated data items.
        """
        if not self.enable_deduplication or not self.deduplication_engine:
            self.logger.debug("Deduplication disabled, returning original data")
            return data

        if not data:
            self.logger.debug("No data to deduplicate")
            return data

        # Filter for items that inherit from TimestampedModel
        timestamped_data = []
        for item in data:
            if isinstance(item, TimestampedModel):
                timestamped_data.append(item)
            else:
                # For non-TimestampedModel items, just add them back without deduplication
                timestamped_data.append(item)

        # Only deduplicate TimestampedModel items
        deduplicable_items = [item for item in timestamped_data if isinstance(item, TimestampedModel)]
        non_deduplicable_items = [item for item in timestamped_data if not isinstance(item, TimestampedModel)]

        if not deduplicable_items:
            self.logger.debug("No deduplicable items found")
            return data

        # Apply deduplication
        deduplication_start = datetime.utcnow()
        try:
            result = self.deduplication_engine.find_duplicates(deduplicable_items)

            # Update metrics
            deduplication_time = (datetime.utcnow() - deduplication_start).total_seconds()
            self.metrics.duplicates_found = len(result.duplicate_groups)
            self.metrics.duplicates_removed = result.duplicates_removed
            self.metrics.deduplication_time_seconds = deduplication_time

            self.logger.info(f"Deduplication completed: {result.total_items} items -> " f"{len(result.unique_items)} unique, {result.duplicates_removed} duplicates removed " f"in {deduplication_time:.2f}s")

            # Return unique items + non-deduplicable items
            unique_items = result.unique_items

            # Convert unique_items back to models if they are dicts and we have a model class
            # DeduplicationEngine returns dicts, but we need to maintain the original model type
            if deduplicable_items and unique_items and isinstance(unique_items[0], dict):
                model_class = type(deduplicable_items[0])
                try:
                    unique_items = [model_class(**item) for item in unique_items]
                except Exception as e:
                    self.logger.warning(f"Failed to convert deduplicated items back to model {model_class.__name__}: {e}")
                    # Fallback to returning dicts if conversion fails, though this might cause downstream issues

            final_items = unique_items + non_deduplicable_items

            # Update record count for transformed items
            self.metrics.records_transformed = len(final_items)

            return final_items

        except Exception as e:
            self.logger.error(f"Deduplication failed: {e}")
            self.metrics.add_error_detail(
                error_message=f"Deduplication failed: {e!s}",
                error_type=type(e).__name__,
                context={"etl_name": self.name, "item_count": len(deduplicable_items)},
            )
            # Return original data if deduplication fails
            return data

    def run(self) -> ETLMetrics:
        """Executes the complete ETL pipeline.

        This method orchestrates the ETL process by:
        1. Initializing metrics and performance logging.
        2. Attempting to load a checkpoint if enabled.
        3. Calling the `extract` method to get data.
        4. Calling the `transform` method to process the extracted data.
        5. Calling the `load` method to store the transformed data.
        6. Handling retries for each stage (extract, transform, load).
        7. Managing checkpoint saving and deletion.
        8. Capturing metrics, logging results, and handling exceptions.

        Returns:
            ETLMetrics: An object containing metrics about the ETL run.

        Raises:
            ETLError: If the ETL process encounters an unrecoverable error.
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

            extracted = self._retry_operation("extract", self.extract)
            self.metrics.records_extracted = len(extracted)
            self.logger.info(f"Extracted {self.metrics.records_extracted} records")

            if not extracted:
                self.logger.info("No data extracted. ETL run considered complete.")
                return self.metrics

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
                   enriched = enricher.enrich_batch(deduplicated)
                except Exception as e:
                    self.logger.warning(f"AI Enrichment failed: {e}")
                    enriched = deduplicated # Fallback to unenriched

            self._retry_operation("load", lambda: self.load(enriched))
            self.metrics.records_loaded = len(enriched)
            self.logger.info(f"Loaded {self.metrics.records_loaded} records")

            if self.enable_checkpointing and self.metrics.is_successful:
                (self.checkpoint_dir / "latest.json").unlink(missing_ok=True)

            # Retention: purge old timestamped artifacts
            try:
                self._purge_old_artifacts()
            except Exception as e:
                self.logger.warning(f"Retention step failed: {e}")

            if self.metrics.is_successful:
                self.logger.info(f"ETL process completed successfully. Success rate: {self.metrics.success_rate:.1f}%")
                # Story 7.1: Record success
                self.circuit_breaker.record_success()
            elif self.metrics.error_count == 0:
                self.logger.info("ETL completed. No records loaded.")
                self.circuit_breaker.record_success() # Treat no-data as success for stability
            # else: errors occurred and were handled by _retry_operation, ETLError will be raised
            
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
            final_msg = f"ETL process '{self.name}' failed: {wt_err.message}"
            if isinstance(e, ETLError) and hasattr(e, "context") and e.context.get("original_message_preserved"):
                final_msg = str(e)
            raise ETLError(final_msg, context=err_ctx, cause=e) from e
        finally:
            self.metrics.finish()
            self.perf_logger.end(success=not run_threw_exception and self.metrics.error_count == 0)

            # Persist per-run summary (always attempt; best-effort)
            try:
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                run_summary = {
                    "etl_name": self.name,
                    "start_time": self.metrics.start_time.isoformat(),
                    "end_time": (self.metrics.end_time.isoformat() if self.metrics.end_time else None),
                    "duration_seconds": self.metrics.duration_seconds,
                    "records_extracted": self.metrics.records_extracted,
                    "records_transformed": self.metrics.records_transformed,
                    "records_loaded": self.metrics.records_loaded,
                    "records_failed": self.metrics.records_failed,
                    "error_count": self.metrics.error_count,
                    # Story 1.1: Include enhanced metrics
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
                metrics_dir = Path(self.settings.project_root) / "data" / "metrics"
                metrics_dir.mkdir(parents=True, exist_ok=True)
                agg_path = metrics_dir / "etl_runs_latest.json"
                try:
                    existing = json.loads(agg_path.read_text(encoding="utf-8")) if agg_path.exists() else {}
                except Exception:
                    existing = {}
                if not isinstance(existing, dict):
                    existing = {}
                runs = existing.get("runs") or {}
                if not isinstance(runs, dict):
                    runs = {}
                runs[self.name] = run_summary | {"last_updated": datetime.utcnow().isoformat(timespec="seconds")}
                existing["generated_at"] = datetime.utcnow().isoformat(timespec="seconds")
                existing["runs"] = runs
                agg_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

                # Story 1.1: Save per-ETL metrics in data/metrics/{etl_name}/ pattern
                etl_metrics_dir = metrics_dir / self.name
                etl_metrics_dir.mkdir(parents=True, exist_ok=True)

                # Create timestamped metrics file as specified in AC2
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                per_etl_metrics_file = etl_metrics_dir / f"{timestamp}_metrics.json"

                # Store full metrics object with enhanced details
                metrics_data = {
                    "etl_name": self.name,
                    "timestamp": timestamp,
                    "start_time": self.metrics.start_time.isoformat(),
                    "end_time": (self.metrics.end_time.isoformat() if self.metrics.end_time else None),
                    "duration_seconds": self.metrics.duration_seconds,
                    "records_extracted": self.metrics.records_extracted,
                    "records_transformed": self.metrics.records_transformed,
                    "records_loaded": self.metrics.records_loaded,
                    "records_failed": self.metrics.records_failed,
                    "error_count": self.metrics.error_count,
                    "warnings_count": self.metrics.warnings_count,
                    "success_rate": self.metrics.success_rate,
                    "is_successful": self.metrics.is_successful,
                    # Enhanced tracking from Story 1.1
                    "errors_detail": self.metrics.errors_detail,
                    "checkpoint_status": self.metrics.checkpoint_status,
                    "output_dir": str(self.output_dir),
                    "story_1_1_enhanced": True,
                }

                per_etl_metrics_file.write_text(
                    json.dumps(metrics_data, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )

                # Also update latest file for this ETL
                latest_metrics_file = etl_metrics_dir / "latest_metrics.json"
                latest_metrics_file.write_text(
                    json.dumps(metrics_data, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )

                self.logger.debug(f"Per-ETL metrics saved to {per_etl_metrics_file}")
            except Exception as e:
                self.logger.warning(f"Failed to write ETL run summary: {e}")

        return self.metrics


class SimpleETL(BaseETL[dict, dict]):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

    def extract(self) -> list[dict[str, Any]]:
        return []

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data

    def load(self, data: list[dict[str, Any]]) -> None:
        out_f = self.output_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_f.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        self.logger.info(f"Data saved to {out_f}")


class DataFrameETL(BaseETL[InputType, OutputType], Generic[InputType, OutputType]):  # Explicitly Generic again
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        try:
            import pandas as pd

            self.pd = pd
        except ImportError:
            self.logger.error("Pandas required but not installed.")
            raise

    @abstractmethod
    def extract_to_dataframe(self) -> Any:  # pd.DataFrame
        """Extracts data and returns it as a Pandas DataFrame.

        Subclasses should implement this method to fetch data from a source
        and structure it into a Pandas DataFrame.

        Returns:
            pandas.DataFrame: The extracted data as a DataFrame.
        """
        pass

    @abstractmethod
    def transform_dataframe(self, df: Any) -> list[OutputType]:  # df: pd.DataFrame
        """Transforms data from a Pandas DataFrame into a list of OutputType objects.

        Subclasses should implement this method to perform data processing,
        cleaning, and transformation using DataFrame operations, then convert
        the results into the desired output format.

        Args:
            df (pandas.DataFrame): The input DataFrame to be transformed.

        Returns:
            List[OutputType]: A list of transformed data objects.
        """
        pass

    def extract(self) -> list[InputType]:
        self.logger.debug("DataFrameETL.extract() using extract_to_dataframe().")
        df = self.extract_to_dataframe()
        return df.to_dict(orient="records") if df is not None else []

    def transform(self, data: list[InputType]) -> list[OutputType]:
        if not data:
            return []
        df = self.pd.DataFrame(data)
        return self.transform_dataframe(df)

    def load(self, data: list[OutputType]) -> None:
        if not data:
            self.logger.info("No data to load.")
            return
        df_to_save = self.pd.DataFrame([i.model_dump() if isinstance(i, BaseModel) else i for i in data])
        out_f = self.output_dir / f"{self.name}_output.csv"
        df_to_save.to_csv(out_f, index=False)
        self.logger.info(f"DataFrameETL default load saved to {out_f}")

    def save_as_csv(self, data: list[dict[str, Any]], filename: str | None = None) -> Path:
        if not filename:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        out_f = self.output_dir / filename
        self.pd.DataFrame(data).to_csv(out_f, index=False, encoding="utf-8")
        self.logger.info(f"Data saved as CSV to {out_f}")
        return out_f

    def save_as_parquet(self, data: list[dict[str, Any]], filename: str | None = None) -> Path:
        if not filename:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        out_f = self.output_dir / filename
        self.pd.DataFrame(data).to_parquet(out_f, index=False)
        self.logger.info(f"Data saved as Parquet to {out_f}")
        return out_f
