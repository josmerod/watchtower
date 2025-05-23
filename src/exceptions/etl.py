"""ETL-specific exception classes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.exceptions.base import WatchtowerError


class ETLError(WatchtowerError):
    """Base exception for ETL-related errors."""
    
    def __init__(
        self,
        message: str,
        etl_name: Optional[str] = None,
        phase: Optional[str] = None,
        **kwargs,
    ):
        """Initialize ETL error.
        
        Args:
            message: Error message.
            etl_name: Name of the ETL process.
            phase: ETL phase where error occurred (extract, transform, load).
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if etl_name:
            context["etl_name"] = etl_name
        if phase:
            context["phase"] = phase
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_ETL_ERROR")
        
        super().__init__(message, **kwargs)


class ExtractionError(ETLError):
    """Exception raised during data extraction phase."""
    
    def __init__(
        self,
        message: str,
        source_url: Optional[str] = None,
        source_type: Optional[str] = None,
        **kwargs,
    ):
        """Initialize extraction error.
        
        Args:
            message: Error message.
            source_url: URL of the data source.
            source_type: Type of data source (api, rss, html, etc.).
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if source_url:
            context["source_url"] = source_url
        if source_type:
            context["source_type"] = source_type
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_EXTRACTION_ERROR")
        kwargs["phase"] = "extract"
        
        super().__init__(message, **kwargs)


class TransformationError(ETLError):
    """Exception raised during data transformation phase."""
    
    def __init__(
        self,
        message: str,
        transformation_step: Optional[str] = None,
        invalid_data: Optional[Any] = None,
        **kwargs,
    ):
        """Initialize transformation error.
        
        Args:
            message: Error message.
            transformation_step: Specific transformation step that failed.
            invalid_data: Sample of invalid data that caused the error.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if transformation_step:
            context["transformation_step"] = transformation_step
        if invalid_data is not None:
            context["invalid_data_sample"] = str(invalid_data)[:500]  # Limit size
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_TRANSFORMATION_ERROR")
        kwargs["phase"] = "transform"
        
        super().__init__(message, **kwargs)


class LoadError(ETLError):
    """Exception raised during data loading phase."""
    
    def __init__(
        self,
        message: str,
        destination: Optional[str] = None,
        destination_type: Optional[str] = None,
        records_failed: Optional[int] = None,
        **kwargs,
    ):
        """Initialize load error.
        
        Args:
            message: Error message.
            destination: Destination where data was being loaded.
            destination_type: Type of destination (file, database, api, etc.).
            records_failed: Number of records that failed to load.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if destination:
            context["destination"] = destination
        if destination_type:
            context["destination_type"] = destination_type
        if records_failed is not None:
            context["records_failed"] = records_failed
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_LOAD_ERROR")
        kwargs["phase"] = "load"
        
        super().__init__(message, **kwargs)


class DataSourceError(ETLError):
    """Exception raised when data source is unavailable or inaccessible."""
    
    def __init__(
        self,
        message: str,
        source_url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        """Initialize data source error.
        
        Args:
            message: Error message.
            source_url: URL of the data source.
            status_code: HTTP status code if applicable.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if source_url:
            context["source_url"] = source_url
        if status_code:
            context["status_code"] = status_code
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_DATA_SOURCE_ERROR")
        kwargs["user_message"] = "Data source is currently unavailable. Please try again later."
        
        super().__init__(message, **kwargs)


class DataValidationError(ETLError):
    """Exception raised when data fails validation."""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        record_count: Optional[int] = None,
        **kwargs,
    ):
        """Initialize data validation error.
        
        Args:
            message: Error message.
            validation_errors: List of validation error details.
            record_count: Number of records that failed validation.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if validation_errors:
            context["validation_errors"] = validation_errors[:10]  # Limit to first 10
        if record_count is not None:
            context["failed_record_count"] = record_count
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_DATA_VALIDATION_ERROR")
        
        super().__init__(message, **kwargs)


class ETLTimeoutError(ETLError):
    """Exception raised when ETL process times out."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        **kwargs,
    ):
        """Initialize ETL timeout error.
        
        Args:
            message: Error message.
            timeout_seconds: Timeout value in seconds.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_ETL_TIMEOUT")
        kwargs["user_message"] = "Operation timed out. Please try again with a longer timeout."
        
        super().__init__(message, **kwargs)


class ETLConfigurationError(ETLError):
    """Exception raised for ETL configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_parameter: Optional[str] = None,
        **kwargs,
    ):
        """Initialize ETL configuration error.
        
        Args:
            message: Error message.
            config_parameter: Configuration parameter that caused the error.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if config_parameter:
            context["config_parameter"] = config_parameter
            
        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_ETL_CONFIG_ERROR")
        
        super().__init__(message, **kwargs) 