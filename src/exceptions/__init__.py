"""Exceptions module for Watchtower."""
from src.exceptions.base import (
    WatchtowerError,
    ConfigurationError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
)
from src.exceptions.etl import (
    ETLError,
    CheckpointError,
    ExtractionError,
    TransformationError,
    LoadError,
    DataSourceError,
    DataValidationError,
    ETLTimeoutError,
    ETLConfigurationError,
)
from src.exceptions.scraping import (
    ScrapingError,
    RequestError,
    ParsingError,
    RateLimitError,
    TimeoutError,
)
from src.exceptions.watcher import (
    WatcherError,
    WatcherConfigurationError,
    WatcherRuntimeError,
    WatcherTimeoutError,
    WatcherValidationError,
    WatcherConnectionError,
)

__all__ = [
    # Base exceptions
    "WatchtowerError",
    "ConfigurationError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    # ETL exceptions
    "ETLError",
    "CheckpointError",
    "ExtractionError",
    "TransformationError",
    "LoadError",
    "DataSourceError",
    "DataValidationError",
    "ETLTimeoutError",
    "ETLConfigurationError",
    # Scraping exceptions
    "ScrapingError",
    "RequestError",
    "ParsingError",
    "RateLimitError",
    "TimeoutError",
    # Watcher exceptions
    "WatcherError",
    "WatcherConfigurationError",
    "WatcherRuntimeError",
    "WatcherTimeoutError",
    "WatcherValidationError",
    "WatcherConnectionError",
]
