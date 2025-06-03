"""Exception handling for Watchtower."""

from src.exceptions.base import (
    ConfigurationError,
    ValidationError,
    WatchtowerError,
    WatchtowerWarning,
)
from src.exceptions.etl import (
    DataSourceError,
    DataValidationError,
    ETLError,
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
    WatcherError,
    WatcherRuntimeError,
)

__all__ = [
    # Base exceptions
    "WatchtowerError",
    "WatchtowerWarning",
    "ConfigurationError",
    "ValidationError",
    # ETL exceptions
    "ETLError",
    "ExtractionError",
    "TransformationError",
    "LoadError",
    "DataSourceError",
    "DataValidationError",
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
]
