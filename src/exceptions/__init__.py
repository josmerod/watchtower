"""Exception handling for Watchtower."""

from exceptions.base import (
    ConfigurationError,
    ValidationError,
    WatchtowerError,
    WatchtowerWarning,
)
from exceptions.etl import (
    DataSourceError,
    DataValidationError,
    ETLError,
    ExtractionError,
    LoadError,
    TransformationError,
)
from exceptions.scraping import (
    ParsingError,
    RateLimitError,
    RequestError,
    ScrapingError,
    TimeoutError,
)
from exceptions.watcher import (
    WatcherConfigurationError,
    WatcherError,
    WatcherRuntimeError,
)

__all__ = [
    "ConfigurationError",
    "DataSourceError",
    "DataValidationError",
    # ETL exceptions
    "ETLError",
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
    # Watcher exceptions
    "WatcherError",
    "WatcherRuntimeError",
    # Base exceptions
    "WatchtowerError",
    "WatchtowerWarning",
]
