"""ETL-specific exception classes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.exceptions.base import MegalithError


class ETLError(MegalithError):
    """Base exception for ETL-related errors."""
    
    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        stage: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ETL error.
        
        Args:
            message: Error message
            source: Data source that caused the error
            stage: ETL stage where error occurred (extract, transform, load)
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get("context", {})
        if source:
            context["source"] = source
        if stage:
            context["stage"] = stage
            
        super().__init__(
            message,
            error_code="ETL_ERROR",
            context=context,
        )


class ExtractionError(ETLError):
    """Raised when data extraction fails."""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize extraction error.
        
        Args:
            message: Error message
            url: URL that failed to be extracted
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
            
        kwargs["context"] = context
        kwargs["stage"] = "extract"
        super().__init__(message, error_code="EXTRACTION_ERROR", **kwargs)


class TransformationError(ETLError):
    """Raised when data transformation fails."""
    
    def __init__(
        self,
        message: str,
        transformer: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize transformation error.
        
        Args:
            message: Error message
            transformer: Name of transformer that failed
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get("context", {})
        if transformer:
            context["transformer"] = transformer
            
        kwargs["context"] = context
        kwargs["stage"] = "transform"
        super().__init__(message, error_code="TRANSFORMATION_ERROR", **kwargs)


class LoadError(ETLError):
    """Raised when data loading fails."""
    
    def __init__(
        self,
        message: str,
        destination: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize load error.
        
        Args:
            message: Error message
            destination: Destination that failed to load data
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get("context", {})
        if destination:
            context["destination"] = destination
            
        kwargs["context"] = context
        kwargs["stage"] = "load"
        super().__init__(message, error_code="LOAD_ERROR", **kwargs)


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