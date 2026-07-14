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
    "AuthenticationError",
    "AuthorizationError",
    "CheckpointError",
    "ConfigurationError",
    "DataSourceError",
    "DataValidationError",
    "ETLConfigurationError",
    # ETL exceptions
    "ETLError",
    "ETLTimeoutError",
    "ExtractionError",
    "LoadError",
    "ParsingError",
    "RateLimitError",
    "RequestError",
    # Scraping exceptions
    "ScrapingError",
    "TimeoutError",
    "TransformationError",
    "ValidationError",
    "WatcherConfigurationError",
    "WatcherConnectionError",
    # Watcher exceptions
    "WatcherError",
    "WatcherRuntimeError",
    "WatcherTimeoutError",
    "WatcherValidationError",
    # Base exceptions
    "WatchtowerError",
]
