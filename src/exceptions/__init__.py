"""Exceptions module for Watchtower."""

from src.exceptions.base import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ValidationError,
    WatchtowerError,
)
from src.exceptions.etl import (
    CheckpointError,
    DataSourceError,
    DataValidationError,
    ETLConfigurationError,
    ETLError,
    ETLTimeoutError,
    ExtractionError,
    LoadError,
    TransformationError,
)
from src.exceptions.scraping import (
    ParsingError,
    RateLimitError,
    RequestError,
    ScrapingError,
    TimeoutError,
)
from src.exceptions.watcher import (
    WatcherConfigurationError,
    WatcherConnectionError,
    WatcherError,
    WatcherRuntimeError,
    WatcherTimeoutError,
    WatcherValidationError,
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
