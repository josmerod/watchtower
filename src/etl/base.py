"""Base ETL classes and patterns for Watchtower."""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import (  # Added Type, ensured Generic, List, Any, TypeVar
    Any,
    Generic,
    TypeVar,
)

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from config.settings import get_settings
from exceptions.base import handle_exception
from exceptions.etl import CheckpointError, ETLError
from utils.logging import get_logger, get_performance_logger

# Type variables for generic ETL
InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class ETLMetrics(BaseModel):
    """Model for ETL execution metrics."""

    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float | None = None
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    error_count: int = 0
    warnings_count: int = 0

    def finish(self) -> None:
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        total_records = self.records_extracted
        if total_records == 0:
            return 100.0 if self.error_count == 0 and self.records_failed == 0 else 0.0
        return (self.records_loaded / total_records) * 100

    @property
    def is_successful(self) -> bool:
        return self.records_loaded > 0 and self.error_count == 0


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
    ):
        self.name = name
        self.description = description or f"ETL process: {name}"
        self.settings = get_settings()
        self.batch_size = batch_size or self.settings.etl.batch_size
        self.enable_checkpointing = enable_checkpointing
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = get_logger(f"ETL.{name}")
        self.perf_logger = get_performance_logger(f"ETL.{name}")
        self.metrics = ETLMetrics(start_time=datetime.utcnow())
        self.current_checkpoint: ETLCheckpoint | None = None
        self.data_dir = Path(self.settings.project_root) / "data" / name
        self.checkpoint_dir = self.data_dir / "checkpoints"
        self.output_dir = self.data_dir / "output"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        for directory in [self.data_dir, self.checkpoint_dir, self.output_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_checkpoint(self) -> ETLCheckpoint | None:
        if not self.enable_checkpointing: return None
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
            raise CheckpointError(f"I/O error loading checkpoint: {e}", checkpoint_path=str(checkpoint_file_path), operation="load", etl_name=self.name) from e
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error loading checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(f"JSON decode error loading checkpoint: {e}", checkpoint_path=str(checkpoint_file_path), operation="load", etl_name=self.name) from e
        except PydanticValidationError as e:
            self.logger.error(f"Pydantic validation error loading checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(f"Pydantic validation error loading checkpoint: {e}", checkpoint_path=str(checkpoint_file_path), operation="load", etl_name=self.name) from e
        except Exception as e:
            self.logger.error(f"Unexpected error loading checkpoint {checkpoint_file_path}: {e}", exc_info=True)
            raise CheckpointError(f"Unexpected error loading checkpoint: {e}", checkpoint_path=str(checkpoint_file_path), operation="load", etl_name=self.name) from e

    def _save_checkpoint(self, checkpoint: ETLCheckpoint) -> None:
        if not self.enable_checkpointing: return
        checkpoint_file_path = self.checkpoint_dir / "latest.json"
        try:
            self.logger.debug(f"Saving checkpoint to {checkpoint_file_path}")
            checkpoint_json = checkpoint.model_dump_json(indent=2)
            checkpoint_file_path.write_text(checkpoint_json, encoding="utf-8")
            self.logger.info(f"Checkpoint {checkpoint.checkpoint_id} saved successfully to {checkpoint_file_path}")
        except OSError as e:
            self.logger.error(f"I/O error saving checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(f"I/O error saving checkpoint: {e}", checkpoint_path=str(checkpoint_file_path), operation="save", etl_name=self.name) from e
        except TypeError as e: # Pydantic model_dump_json can raise TypeError
            self.logger.error(f"Serialization error saving checkpoint {checkpoint_file_path}: {e}")
            raise CheckpointError(f"Serialization error saving checkpoint: {e}", checkpoint_path=str(checkpoint_file_path), operation="save", etl_name=self.name) from e
        except Exception as e:
            self.logger.error(f"Unexpected error saving checkpoint {checkpoint_file_path}: {e}", exc_info=True)
            raise CheckpointError(f"Unexpected error saving checkpoint: {e}", checkpoint_path=str(checkpoint_file_path), operation="save", etl_name=self.name) from e

    def _generate_checksum(self, data: Any) -> str:
        return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def _retry_operation(self, operation_name: str, operation_func) -> Any:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try: return operation_func()
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    self.logger.warning(f"{operation_name} failed (attempt {attempt+1}/{self.max_retries+1}): {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else: self.logger.error(f"{operation_name} failed after {self.max_retries+1} attempts: {e}")
        if last_exception: raise last_exception

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

    def validate_data(self, data: list[Any], model_class: type[BaseModel]) -> list[BaseModel]: # Use Type
        validated = []
        for item in data:
            try:
                validated.append(model_class(**item) if isinstance(item, dict) else model_class.parse_obj(item))
            except PydanticValidationError as e:
                self.logger.warning(f"Data validation failed: {e}"); self.metrics.records_failed+=1
        return validated

    def process_in_batches(self, data: list[Any], process_func) -> list[Any]:
        results = []
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i+self.batch_size]
            try:
                results.extend(process_func(batch))
                if self.current_checkpoint and batch:
                    self.current_checkpoint.processed_count += len(batch)
                    self._save_checkpoint(self.current_checkpoint)
            except Exception as e:
                self.logger.error(f"Batch processing failed: {e}"); self.metrics.error_count+=1
                if self.should_stop_on_error(e): raise
        return results

    def should_stop_on_error(self, error: Exception) -> bool:
        return isinstance(error, KeyboardInterrupt | MemoryError | SystemExit)

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
        run_threw_exception = False
        try:
            self.current_checkpoint = self._load_checkpoint()
            if self.current_checkpoint: self.logger.info(f"Resuming from checkpoint: {self.current_checkpoint.checkpoint_id}")

            extracted = self._retry_operation("extract", self.extract)
            self.metrics.records_extracted = len(extracted)
            self.logger.info(f"Extracted {self.metrics.records_extracted} records")

            if not extracted:
                self.logger.info("No data extracted. ETL run considered complete."); return self.metrics

            transformed = self._retry_operation("transform", lambda: self.transform(extracted))
            self.metrics.records_transformed = len(transformed)
            self.logger.info(f"Transformed {self.metrics.records_transformed} records")

            if not transformed:
                self.logger.info("No data after transformation. Skipping load."); return self.metrics

            self._retry_operation("load", lambda: self.load(transformed))
            self.metrics.records_loaded = len(transformed)
            self.logger.info(f"Loaded {self.metrics.records_loaded} records")

            if self.enable_checkpointing and self.metrics.is_successful:
                (self.checkpoint_dir/"latest.json").unlink(missing_ok=True)

            if self.metrics.is_successful: self.logger.info(f"ETL process completed successfully. Success rate: {self.metrics.success_rate:.1f}%")
            elif self.metrics.error_count==0: self.logger.info("ETL completed. No records loaded.")
            # else: errors occurred and were handled by _retry_operation, ETLError will be raised

        except Exception as e:
            run_threw_exception = True
            self.metrics.error_count +=1
            err_ctx = {"etl_name":self.name, "metrics":self.metrics.model_dump()}
            wt_err = handle_exception(e, logger=self.logger, reraise=False, add_context=err_ctx)
            final_msg = f"ETL process '{self.name}' failed: {wt_err.message}"
            if isinstance(e, ETLError) and hasattr(e, 'context') and e.context.get("original_message_preserved"): final_msg=str(e)
            raise ETLError(final_msg, context=err_ctx, cause=e) from e
        finally:
            self.metrics.finish()
            self.perf_logger.end(success=not run_threw_exception and self.metrics.error_count == 0)
        return self.metrics

class SimpleETL(BaseETL[dict, dict]):
    def __init__(self, name: str, **kwargs): super().__init__(name, **kwargs)
    def extract(self) -> list[dict[str, Any]]: return []
    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]: return data
    def load(self, data: list[dict[str, Any]]) -> None:
        out_f = self.output_dir/f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_f.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        self.logger.info(f"Data saved to {out_f}")

class DataFrameETL(BaseETL[InputType, OutputType], Generic[InputType, OutputType]): # Explicitly Generic again
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        try: import pandas as pd; self.pd = pd
        except ImportError: self.logger.error("Pandas required but not installed."); raise

    @abstractmethod
    def extract_to_dataframe(self) -> Any: # pd.DataFrame
        """Extracts data and returns it as a Pandas DataFrame.

        Subclasses should implement this method to fetch data from a source
        and structure it into a Pandas DataFrame.

        Returns:
            pandas.DataFrame: The extracted data as a DataFrame.
        """
        pass

    @abstractmethod
    def transform_dataframe(self, df: Any) -> list[OutputType]: # df: pd.DataFrame
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
        return df.to_dict(orient='records') if df is not None else []

    def transform(self, data: list[InputType]) -> list[OutputType]:
        if not data: return []
        df = self.pd.DataFrame(data)
        return self.transform_dataframe(df)

    def load(self, data: list[OutputType]) -> None:
        if not data: self.logger.info("No data to load."); return
        df_to_save = self.pd.DataFrame([i.model_dump() if isinstance(i,BaseModel) else i for i in data])
        out_f = self.output_dir/f"{self.name}_output.csv"
        df_to_save.to_csv(out_f, index=False)
        self.logger.info(f"DataFrameETL default load saved to {out_f}")

    def save_as_csv(self, data: list[dict[str,Any]], filename:str|None=None) -> Path:
        if not filename: filename=f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        out_f = self.output_dir/filename
        self.pd.DataFrame(data).to_csv(out_f,index=False,encoding="utf-8")
        self.logger.info(f"Data saved as CSV to {out_f}"); return out_f

    def save_as_parquet(self, data:list[dict[str,Any]], filename:str|None=None) -> Path:
        if not filename: filename=f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        out_f = self.output_dir/filename
        self.pd.DataFrame(data).to_parquet(out_f,index=False)
        self.logger.info(f"Data saved as Parquet to {out_f}"); return out_f
