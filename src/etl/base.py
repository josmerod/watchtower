"""Base ETL classes and patterns for Watchtower."""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Unionfrom pydantic import BaseModel, ValidationError as PydanticValidationErrorfrom src.config.settings import get_settingsfrom src.exceptions.base import handle_exceptionfrom src.exceptions.etl import (    ETLError,    ExtractionError,    LoadError,    TransformationError,)from src.models.base import TimestampedModelfrom src.utils.logging import get_logger, get_performance_loggerclass ETLMetrics(BaseModel):
    """Model for ETL execution metrics."""
    
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    error_count: int = 0
    warnings_count: int = 0
    
    def finish(self) -> None:
        """Mark the ETL run as finished and calculate duration."""
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of the ETL run."""
        total_records = self.records_extracted
        if total_records == 0:
            return 0.0
        return (self.records_loaded / total_records) * 100
    
    @property
    def is_successful(self) -> bool:
        """Check if the ETL run was successful."""
        return self.records_loaded > 0 and self.error_count == 0


class ETLCheckpoint(BaseModel):
    """Model for ETL checkpointing."""
    
    etl_name: str
    checkpoint_id: str
    timestamp: datetime
    last_processed_id: Optional[str] = None
    last_processed_timestamp: Optional[datetime] = None
    processed_count: int = 0
    metadata: Dict[str, Any] = {}


class BaseETL(ABC):
    """Base class for all ETL processes with comprehensive error handling and monitoring."""
    
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        batch_size: Optional[int] = None,
        enable_checkpointing: bool = True,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """Initialize the ETL process.
        
        Args:
            name: Unique name for this ETL process.
            description: Description of what this ETL does.
            batch_size: Number of records to process in each batch.
            enable_checkpointing: Whether to enable checkpointing.
            max_retries: Maximum number of retries for failed operations.
            retry_delay: Delay between retries in seconds.
        """
        self.name = name
        self.description = description or f"ETL process: {name}"
        self.settings = get_settings()
        
        # Configuration
        self.batch_size = batch_size or self.settings.etl.batch_size
        self.enable_checkpointing = enable_checkpointing
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Logging
        self.logger = get_logger(f"ETL.{name}")
        self.perf_logger = get_performance_logger(f"ETL.{name}")
        
        # State
        self.metrics = ETLMetrics(start_time=datetime.utcnow())
        self.current_checkpoint: Optional[ETLCheckpoint] = None
        
        # Paths
        self.data_dir = Path(self.settings.data_dir) / name
        self.checkpoint_dir = self.data_dir / "checkpoints"
        self.output_dir = self.data_dir / "output"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for directory in [self.data_dir, self.checkpoint_dir, self.output_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_checkpoint(self) -> Optional[ETLCheckpoint]:
        """Load the latest checkpoint for this ETL.
        
        Returns:
            Latest checkpoint or None if no checkpoint exists.
        """
        if not self.enable_checkpointing:
            return None
            
        checkpoint_file = self.checkpoint_dir / "latest.json"
        if not checkpoint_file.exists():
            return None
            
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ETLCheckpoint(**data)
        except Exception as e:
            self.logger.warning(f"Failed to load checkpoint: {e}")
            return None
    
    def _save_checkpoint(self, checkpoint: ETLCheckpoint) -> None:
        """Save checkpoint data.
        
        Args:
            checkpoint: Checkpoint to save.
        """
        if not self.enable_checkpointing:
            return
            
        checkpoint_file = self.checkpoint_dir / "latest.json"
        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint.dict(), f, default=str, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
    
    def _generate_checksum(self, data: Any) -> str:
        """Generate checksum for data to detect changes.
        
        Args:
            data: Data to generate checksum for.
            
        Returns:
            MD5 checksum string.
        """
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _retry_operation(self, operation_name: str, operation_func) -> Any:
        """Retry an operation with exponential backoff.
        
        Args:
            operation_name: Name of the operation for logging.
            operation_func: Function to retry.
            
        Returns:
            Result of the operation.
            
        Raises:
            Last exception if all retries fail.
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation_func()
            except Exception as e:
                last_exception = e
                self.metrics.error_count += 1
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"{operation_name} failed after {self.max_retries + 1} attempts: {e}"
                    )
        
        if last_exception:
            raise last_exception
    
    @abstractmethod
    def extract(self) -> List[InputType]:
        """Extract data from the source.
        
        Returns:
            List of extracted raw data items.
            
        Raises:
            ExtractionError: If extraction fails.
        """
        pass
    
    @abstractmethod
    def transform(self, data: List[InputType]) -> List[OutputType]:
        """Transform the extracted data.
        
        Args:
            data: Raw data to transform.
            
        Returns:
            List of transformed data items.
            
        Raises:
            TransformationError: If transformation fails.
        """
        pass
    
    @abstractmethod
    def load(self, data: List[OutputType]) -> None:
        """Load the transformed data to the destination.
        
        Args:
            data: Transformed data to load.
            
        Raises:
            LoadError: If loading fails.
        """
        pass
    
    def validate_data(self, data: List[Any], model_class: type) -> List[Any]:
        """Validate data against a Pydantic model.
        
        Args:
            data: Data to validate.
            model_class: Pydantic model class for validation.
            
        Returns:
            List of validated data items.
        """
        validated_data = []
        
        for item in data:
            try:
                if isinstance(item, dict):
                    validated_item = model_class(**item)
                else:
                    validated_item = model_class.parse_obj(item)
                validated_data.append(validated_item)
            except PydanticValidationError as e:
                self.logger.warning(f"Data validation failed for item: {e}")
                self.metrics.records_failed += 1
        
        return validated_data
    
    def process_in_batches(self, data: List[Any], process_func) -> List[Any]:
        """Process data in batches.
        
        Args:
            data: Data to process.
            process_func: Function to process each batch.
            
        Returns:
            List of processed results.
        """
        results = []
        
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            
            try:
                batch_results = process_func(batch)
                results.extend(batch_results)
                
                # Update checkpoint
                if self.current_checkpoint and batch:
                    self.current_checkpoint.processed_count += len(batch)
                    self._save_checkpoint(self.current_checkpoint)
                    
            except Exception as e:
                self.logger.error(f"Batch processing failed for batch {i // self.batch_size + 1}: {e}")
                self.metrics.error_count += 1
                
                # Decide whether to continue or stop
                if self.should_stop_on_error(e):
                    raise
        
        return results
    
    def should_stop_on_error(self, error: Exception) -> bool:
        """Determine if ETL should stop on this error.
        
        Args:
            error: The error that occurred.
            
        Returns:
            True if ETL should stop, False to continue.
        """
        # Stop on critical errors
        critical_errors = (KeyboardInterrupt, MemoryError, SystemExit)
        return isinstance(error, critical_errors)
    
    def run(self) -> ETLMetrics:
        """Run the complete ETL pipeline.
        
        Returns:
            Metrics from the ETL run.
            
        Raises:
            ETLError: If the ETL process fails.
        """
        self.logger.info(f"Starting ETL process: {self.name}")
        self.perf_logger.start(f"ETL_{self.name}")
        
        try:
            # Load checkpoint
            self.current_checkpoint = self._load_checkpoint()
            if self.current_checkpoint:
                self.logger.info(f"Resuming from checkpoint: {self.current_checkpoint.checkpoint_id}")
            
            # Extract
            self.logger.info("Starting extraction phase")
            extracted_data = self._retry_operation("extract", self.extract)
            self.metrics.records_extracted = len(extracted_data)
            self.logger.info(f"Extracted {self.metrics.records_extracted} records")
            
            if not extracted_data:
                self.logger.warning("No data extracted, skipping transformation and loading")
                return self.metrics
            
            # Transform
            self.logger.info("Starting transformation phase")
            transformed_data = self._retry_operation(
                "transform", 
                lambda: self.transform(extracted_data)
            )
            self.metrics.records_transformed = len(transformed_data)
            self.logger.info(f"Transformed {self.metrics.records_transformed} records")
            
            if not transformed_data:
                self.logger.warning("No data transformed, skipping loading")
                return self.metrics
            
            # Load
            self.logger.info("Starting loading phase")
            self._retry_operation("load", lambda: self.load(transformed_data))
            self.metrics.records_loaded = len(transformed_data)
            self.logger.info(f"Loaded {self.metrics.records_loaded} records")
            
            # Clean up checkpoint on successful completion
            if self.enable_checkpointing:
                checkpoint_file = self.checkpoint_dir / "latest.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
            
            self.logger.info(f"ETL process completed successfully. Success rate: {self.metrics.success_rate:.1f}%")
            
        except Exception as e:
            error_context = {
                "etl_name": self.name,
                "metrics": self.metrics.dict(),
            }
            
            watchtower_error = handle_exception(
                e, 
                logger=self.logger, 
                reraise=False,
                add_context=error_context
            )
            
            self.perf_logger.end(success=False, extra_data=error_context)
            
            # Convert to ETL-specific error
            raise ETLError(
                f"ETL process '{self.name}' failed: {watchtower_error.message}",
                context=error_context,
                cause=e,
            )
        
        finally:
            self.metrics.finish()
            self.perf_logger.end(success=self.metrics.is_successful)
        
        return self.metrics


class SimpleETL(BaseETL[Dict[str, Any], Dict[str, Any]]):
    """Simple ETL class for basic dictionary-based transformations."""
    
    def __init__(self, name: str, **kwargs):
        """Initialize simple ETL.
        
        Args:
            name: ETL name.
            **kwargs: Additional arguments for base class.
        """
        super().__init__(name, **kwargs)
    
    def extract(self) -> List[Dict[str, Any]]:
        """Default extract implementation - override in subclasses."""
        return []
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Default transform implementation - pass through data."""
        return data
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        """Default load implementation - save as JSON."""
        output_file = self.output_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"Data saved to {output_file}")


class DataFrameETL(BaseETL[Dict[str, Any], Dict[str, Any]]):
    """ETL class with Pandas DataFrame support."""
    
    def __init__(self, name: str, **kwargs):
        """Initialize DataFrame ETL.
        
        Args:
            name: ETL name.
            **kwargs: Additional arguments for base class.
        """
        super().__init__(name, **kwargs)
        
        try:
            import pandas as pd
            self.pd = pd
        except ImportError:
            raise ImportError("pandas is required for DataFrameETL")
    
    def save_as_csv(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> Path:
        """Save data as CSV file.
        
        Args:
            data: Data to save.
            filename: Optional filename.
            
        Returns:
            Path to saved file.
        """
        if not filename:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        output_file = self.output_dir / filename
        df = self.pd.DataFrame(data)
        df.to_csv(output_file, index=False, encoding="utf-8")
        
        self.logger.info(f"Data saved as CSV to {output_file}")
        return output_file
    
    def save_as_parquet(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> Path:
        """Save data as Parquet file.
        
        Args:
            data: Data to save.
            filename: Optional filename.
            
        Returns:
            Path to saved file.
        """
        if not filename:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        output_file = self.output_dir / filename
        df = self.pd.DataFrame(data)
        df.to_parquet(output_file, index=False)
        
        self.logger.info(f"Data saved as Parquet to {output_file}")
        return output_file 