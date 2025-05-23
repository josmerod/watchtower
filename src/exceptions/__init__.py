"""Exception handling for Watchtower."""

from src.exceptions.base import (
    WatchtowerError,
    WatchtowerWarning,
    ConfigurationError,
    ValidationError,
)
from src.exceptions.etl import (
    ETLError,
    ExtractionError,
    TransformationError,
    LoadError,
    DataSourceError,
    DataValidationError,
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