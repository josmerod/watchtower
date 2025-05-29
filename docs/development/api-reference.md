# Watchtower API Reference

This document provides detailed API reference for the core Watchtower framework components.

## 📋 Table of Contents

1. [Configuration System](#configuration-system)
2. [ETL Framework](#etl-framework) 
3. [Watcher System](#watcher-system)
4. [Models & Validation](#models--validation)
5. [Utilities & Helpers](#utilities--helpers)
6. [Exception Handling](#exception-handling)

---

## Configuration System

### `Settings` Class

The main configuration management class using Pydantic Settings with environment variable support.

```python
from src.config.settings import get_settings

settings = get_settings()
```

#### Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `app_name` | `str` | Application name (default: "Watchtower") |
| `app_version` | `str` | Application version (default: "0.1.0") |
| `environment` | `Environment` | Current environment (development/testing/staging/production) |
| `debug` | `bool` | Enable debug mode (default: False) |
| `project_root` | `Optional[str]` | Auto-detected project root directory |
| `data_dir` | `str` | Data storage directory (default: "data") |
| `logs_dir` | `str` | Logs storage directory (default: "logs") |
| `config_dir` | `str` | Config storage directory (default: "config") |

#### Component Configurations

- **`database`**: `DatabaseConfig` - Database connection settings
- **`logging`**: `LoggingConfig` - Logging configuration
- **`scraping`**: `ScrapingConfig` - Web scraping settings
- **`api`**: `APIConfig` - API server configuration
- **`streamlit`**: `StreamlitConfig` - Streamlit dashboard settings
- **`security`**: `SecurityConfig` - Security and authentication
- **`monitoring`**: `MonitoringConfig` - Observability settings
- **`notifications`**: `NotificationConfig` - Alert mechanisms
- **`watchers`**: `WatcherConfig` - Watcher monitoring settings
- **`etl`**: `ETLConfig` - ETL pipeline configuration

#### Methods

```python
# Environment checks
settings.is_development() -> bool
settings.is_production() -> bool
settings.is_testing() -> bool

# Path utilities
settings.get_data_path(*paths: str) -> Path
settings.get_logs_path(*paths: str) -> Path
settings.get_config_path(*paths: str) -> Path

# Directory management
settings.create_directories() -> None

# Export settings as environment variables
settings.model_dump_env() -> dict
```

#### Auto-Detection Features

- **Project Root Detection**: Automatically finds project root by looking for markers like `pyproject.toml`, `README.md`, `.git`, `requirements.txt`
- **Path Resolution**: Converts relative paths to absolute paths based on project root
- **Directory Creation**: Automatically creates necessary directories if they don't exist

### Environment Variables

Configuration supports nested environment variables with double underscore delimiter:

```bash
# Database configuration
DATABASE__URL=postgresql://user:pass@localhost/db
DATABASE__ECHO=true

# Logging configuration  
LOGGING__LEVEL=DEBUG
LOGGING__FILE_ENABLED=true

# ETL configuration
ETL__BATCH_SIZE=500
ETL__MAX_WORKERS=8

# Scraping configuration
SCRAPING__TIMEOUT=60
SCRAPING__MAX_RETRIES=5
```

### Testing Configuration

```python
from src.config.settings import get_settings_for_testing

# Get pre-configured testing settings
test_settings = get_settings_for_testing()

# Reload settings (clears cache)
from src.config.settings import reload_settings
new_settings = reload_settings()
```

---

## ETL Framework

### `BaseETL` Class

Abstract base class for all ETL processes with comprehensive error handling and monitoring.

```python
from src.etl.base import BaseETL
from typing import List, Dict, Any

class MyETL(BaseETL):
    def extract(self) -> List[Dict[str, Any]]:
        # Implementation
        pass
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Implementation
        pass
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        # Implementation
        pass
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Unique ETL process name |
| `description` | `Optional[str]` | `None` | ETL process description |
| `batch_size` | `Optional[int]` | `settings.etl.batch_size` | Records per batch |
| `enable_checkpointing` | `bool` | `True` | Enable checkpoint recovery |
| `max_retries` | `int` | `3` | Max retry attempts |
| `retry_delay` | `int` | `5` | Delay between retries (seconds) |

#### Core Methods

```python
# Main execution method
etl.run() -> ETLMetrics

# Abstract methods to implement
etl.extract() -> List[InputType]
etl.transform(data: List[InputType]) -> List[OutputType]
etl.load(data: List[OutputType]) -> None

# Utility methods
etl.validate_data(data: List[Any], model_class: type) -> List[Any]
etl.process_in_batches(data: List[Any], process_func) -> List[Any]
etl.should_stop_on_error(error: Exception) -> bool
```

#### ETL Metrics

The `ETLMetrics` model tracks execution statistics:

```python
from pydantic import BaseModel

class ETLMetrics(BaseModel):
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
        """Mark ETL as finished and calculate duration."""
        pass
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        pass
    
    @property
    def is_successful(self) -> bool:
        """Check if ETL run was successful."""
        pass
```

#### Checkpointing System

ETL processes support automatic checkpointing for recovery:

```python
from pydantic import BaseModel

class ETLCheckpoint(BaseModel):
    etl_name: str
    checkpoint_id: str
    timestamp: datetime
    last_processed_id: Optional[str] = None
    last_processed_timestamp: Optional[datetime] = None
    processed_count: int = 0
    metadata: Dict[str, Any] = {}
```

#### Directory Structure

Each ETL process creates its own directory structure:

```
data/
└── {etl_name}/
    ├── checkpoints/
    │   └── latest.json
    └── output/
        ├── data files...
        └── exports...
```

#### Error Handling & Retries

- **Automatic Retries**: Failed operations are retried with exponential backoff
- **Checksum Validation**: Data integrity verification using MD5 checksums
- **Graceful Error Handling**: Configurable error stopping behavior

### Specialized ETL Classes

#### `SimpleETL`

For basic dictionary-based ETL processes:

```python
from src.etl.base import SimpleETL

class NewsETL(SimpleETL):
    def extract(self) -> List[Dict[str, Any]]:
        # Return list of dictionaries
        pass
    
    # transform and load methods have default implementations
```

#### `DataFrameETL`

For data processing with enhanced export capabilities:

```python
from src.etl.base import DataFrameETL

class AnalyticsETL(DataFrameETL):
    # Includes enhanced export methods
    def save_as_csv(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> Path
    def save_as_parquet(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> Path
    def save_as_json(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> Path
```

---

## Watcher System

### `BaseWatcher` Class

Abstract base class for monitoring web content changes.

```python
from src.watchers.base_watcher import BaseWatcher
from typing import Any

class MyWatcher(BaseWatcher):
    def extract_value(self, html_content: str) -> Any:
        # Extract the value to monitor
        pass
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        # Determine if change should trigger alarm
        pass
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Unique watcher name |
| `url` | `str` | Required | URL to monitor |
| `check_interval` | `int` | `3600` | Check interval (seconds) |

#### Core Methods

```python
# Main monitoring methods
watcher.check() -> None  # Single check
watcher.run(continuous: bool = True, max_runs: Optional[int] = None) -> None

# Abstract methods to implement
watcher.extract_value(html_content: str) -> Any
watcher.has_changed(old_value: Any, new_value: Any) -> bool

# Utility methods
watcher.fetch_page() -> str
watcher.trigger_alarm(old_value: Any, new_value: Any) -> None
```

#### Event Recording

Watchers automatically record events when changes are detected:

```json
{
  "id": "20250123140530_change_detected",
  "type": "change_detected",
  "timestamp": "2025-01-23T14:05:30.123456",
  "watcher": "example_watcher",
  "url": "https://example.com",
  "old_value": "previous_value", 
  "new_value": "current_value",
  "details": {}
}
```

#### State Management

Watchers maintain persistent state in `data/watchers/{name}/state.json`:

```json
{
  "last_check": "2025-01-23T14:05:30.123456",
  "last_value": "monitored_value",
  "first_seen": "2025-01-20T10:00:00.000000"
}
```

#### Directory Structure

Each watcher creates its own directory structure:

```
data/
└── watchers/
    └── {watcher_name}/
        ├── state.json
        └── events/
            └── {timestamp}_{event_type}.json
```

---

## Models & Validation

### `BaseModel` Class

Enhanced base model with additional utility methods:

```python
from src.models.base import BaseModel

class MyModel(BaseModel):
    name: str
    value: int
    
# Available methods:
model.dict_without_none()  # Exclude None values
model.update_from_dict(data)  # Return updated instance
```

### `TimestampedModel` Base Class

Base model for all data objects with automatic timestamps:

```python
from src.models.base import TimestampedModel

class MyModel(TimestampedModel):
    name: str
    value: int
    
# Automatic fields added:
# - id: str (UUID4)
# - created_at: datetime (UTC)
# - updated_at: Optional[datetime] (auto-set on updates)
```

### Standard Models

Additional utility models available:

```python
from src.models.base import (
    StatusModel,     # For status information
    ErrorModel,      # For error details
    PaginationModel, # For pagination data
    PaginatedResponse # For paginated API responses
)
```

### Configuration Models

Pydantic models for component configuration with validation:

```python
from src.config.models import (
    DatabaseConfig,
    LoggingConfig, 
    ScrapingConfig,
    ETLConfig,
    WatcherConfig,
    APIConfig,
    StreamlitConfig,
    SecurityConfig,
    MonitoringConfig,
    NotificationConfig,
)

# Example usage
db_config = DatabaseConfig(
    url="postgresql://localhost/watchtower",
    pool_size=10,
    echo=False
)
```

#### Available Configuration Models

| Model | Key Fields | Validation |
|-------|------------|------------|
| `DatabaseConfig` | `url`, `pool_size`, `max_overflow` | URL scheme validation |
| `LoggingConfig` | `level`, `file_enabled`, `structured` | Log level enum, file size limits |
| `ScrapingConfig` | `timeout`, `max_retries`, `rate_limit` | Range validation, positive values |
| `APIConfig` | `host`, `port`, `cors_origins` | Port range, CORS configuration |
| `StreamlitConfig` | `host`, `port`, `theme_base` | Port range, upload size limits |
| `SecurityConfig` | `secret_key`, `algorithm` | Key length validation |
| `MonitoringConfig` | `metrics_enabled`, `health_check_interval` | Interval bounds |
| `NotificationConfig` | `email_*`, `slack_webhook_url` | Email/URL validation |
| `WatcherConfig` | `default_check_interval`, `max_events_per_watcher` | Range validation |
| `ETLConfig` | `batch_size`, `max_workers` | Worker/batch limits |

---

## Utilities & Helpers

### Enhanced Logging System

Comprehensive logging with structured JSON support and performance monitoring:

```python
from src.utils.logging import get_logger, get_performance_logger

# Standard logger with auto-detected name
logger = get_logger()  # Uses calling module name
logger = get_logger("custom_name")

# Logger with extra fields for structured logging
logger = get_logger("component", extra_fields={"user_id": "123"})

# Performance logger with timing context
perf_logger = get_performance_logger("component")
perf_logger.start("database_query")
# ... operation ...
perf_logger.end(success=True, extra_data={"rows": 100})
```

#### Logging Features

- **Structured JSON Logging**: Optional JSON output for better parsing
- **Rotating File Logs**: Automatic log rotation with configurable size/backup count
- **Performance Tracking**: Built-in operation timing and metrics
- **Auto-Configuration**: Lazy configuration from settings
- **Exception Tracking**: Automatic exception formatting and context

#### Function Logging Decorator

```python
from src.utils.logging import log_function_call

@log_function_call
def my_function(param1, param2):
    return "result"
```

### File System Utilities

Cross-platform file operations with enhanced functionality:

```python
from src.utils.file_system import (
    ensure_directories,
    get_project_root,
    safe_write_json,
    safe_read_json
)

# Ensure directories exist
ensure_directories(["data/output", "logs"])

# Get project root (auto-detected)
root = get_project_root()

# Safe JSON operations with error handling
safe_write_json(data, "output.json")
data = safe_read_json("input.json", default={})
```

---

## Exception Handling

### Exception Hierarchy

Comprehensive exception system with rich context information:

```python
from src.exceptions.base import WatchtowerError
from src.exceptions.etl import ETLError, ExtractionError, TransformationError, LoadError
from src.exceptions.watcher import WatcherError

try:
    # Operation that might fail
    pass
except ETLError as e:
    logger.error(f"ETL failed: {e.error_code} - {e.message}")
    logger.error(f"Context: {e.context}")
    logger.error(f"User message: {e.user_message}")
```

#### Base Exception Features

All Watchtower exceptions inherit from `WatchtowerError` and provide:

```python
class WatchtowerError(Exception):
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None,
    ):
        pass
    
    # Utility methods
    def to_dict(self) -> Dict[str, Any]  # Serialize to dict
    def add_context(self, key: str, value: Any) -> WatchtowerError  # Add context
    def with_user_message(self, message: str) -> WatchtowerError  # Set user message
```

#### Exception Types

| Exception | Use Case | Error Code Prefix |
|-----------|----------|-------------------|
| `WatchtowerError` | Base exception | `WT_` |
| `ConfigurationError` | Configuration issues | `WT_CONFIG_ERROR` |
| `ValidationError` | Data validation problems | `WT_VALIDATION_ERROR` |
| `AuthenticationError` | Authentication failures | `WT_AUTH_ERROR` |
| `AuthorizationError` | Permission denied | `WT_AUTHZ_ERROR` |
| `ResourceNotFoundError` | Missing resources | `WT_NOT_FOUND` |
| `DependencyError` | Missing dependencies | `WT_DEPENDENCY_ERROR` |
| `ETLError` | ETL process failures | `WT_ETL_ERROR` |
| `ExtractionError` | Data extraction issues | `WT_EXTRACTION_ERROR` |
| `TransformationError` | Data transformation problems | `WT_TRANSFORMATION_ERROR` |
| `LoadError` | Data loading failures | `WT_LOAD_ERROR` |
| `WatcherError` | Monitoring failures | `WT_WATCHER_ERROR` |

### Error Handling Utilities

```python
from src.exceptions.base import handle_exception

# Handle exceptions with automatic logging and context
def handle_exception(
    exception: Exception,
    logger=None,
    reraise: bool = True,
    add_context: Optional[Dict[str, Any]] = None,
) -> Optional[WatchtowerError]:
    pass
```

---

## Usage Examples

### Complete ETL Example

```python
from src.etl.base import SimpleETL
from src.config.settings import get_settings
from typing import List, Dict, Any

class NewsETL(SimpleETL):
    def __init__(self, name: str = "news_etl"):
        super().__init__(name, description="Extract and process news articles")
    
    def extract(self) -> List[Dict[str, Any]]:
        # Fetch from RSS feed or API
        articles = []
        # ... fetch logic ...
        self.logger.info(f"Extracted {len(articles)} articles")
        return articles
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Clean and validate data
        transformed = []
        for article in data:
            # ... transformation logic ...
            transformed.append(article)
        return transformed
    
    def load(self, data: List[Dict[str, Any]]) -> None:
        # Save to files
        self.save_as_json(data, "news.json")
        self.save_as_csv(data, "news.csv")
        self.logger.info(f"Loaded {len(data)} articles")

# Run ETL
etl = NewsETL()
metrics = etl.run()
print(f"Success: {metrics.is_successful}")
print(f"Processed {metrics.records_loaded} records in {metrics.duration_seconds:.2f}s")
print(f"Success rate: {metrics.success_rate:.1f}%")
```

### Complete Watcher Example

```python
from src.watchers.base_watcher import BaseWatcher
from bs4 import BeautifulSoup
from typing import Any

class PriceWatcher(BaseWatcher):
    def __init__(self, product_url: str):
        super().__init__(
            name="product_price_watcher",
            url=product_url,
            check_interval=1800  # Check every 30 minutes
        )
    
    def extract_value(self, html_content: str) -> float:
        soup = BeautifulSoup(html_content, 'html.parser')
        price_elem = soup.find('span', class_='price')
        if not price_elem:
            raise ValueError("Price element not found")
        
        price_text = price_elem.text.strip()
        # Remove currency symbol and convert to float
        price = float(price_text.replace('$', '').replace(',', ''))
        return price
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        if old_value is None:
            return False  # Don't trigger on first check
        
        # Trigger if price drops by more than 10%
        percentage_change = abs(old_value - new_value) / old_value
        return percentage_change > 0.10
    
    def trigger_alarm(self, old_value: Any, new_value: Any):
        # Custom alarm logic
        change_pct = ((new_value - old_value) / old_value) * 100
        direction = "dropped" if new_value < old_value else "increased"
        
        self.logger.warning(
            f"Price {direction} significantly: ${old_value:.2f} -> ${new_value:.2f} "
            f"({change_pct:+.1f}%)"
        )
        
        # Call parent to record event
        super().trigger_alarm(old_value, new_value)

# Run watcher
watcher = PriceWatcher("https://store.com/product")
watcher.run(continuous=True)  # Run indefinitely
# OR
watcher.check()  # Single check
```

### Configuration Example

```python
from src.config.settings import get_settings
from src.config.models import LoggingConfig, ETLConfig

# Get current settings
settings = get_settings()

# Check environment
if settings.is_development():
    print("Running in development mode")

# Use path utilities
data_path = settings.get_data_path("processed", "output.json")
log_path = settings.get_logs_path("etl.log")

# Custom configuration
custom_logging = LoggingConfig(
    level="DEBUG",
    structured=True,
    file_enabled=True
)

custom_etl = ETLConfig(
    batch_size=2000,
    max_workers=8,
    checkpoint_enabled=True
)
```

### Advanced Logging Example

```python
from src.utils.logging import get_logger, get_performance_logger, configure_logging
from src.config.models import LoggingConfig

# Configure logging with custom settings
logging_config = LoggingConfig(
    level="DEBUG",
    structured=True,
    console_enabled=True,
    file_enabled=True
)
configure_logging(logging_config)

# Get loggers
logger = get_logger("my_component")
perf_logger = get_performance_logger("my_component")

# Basic logging
logger.info("Processing started")
logger.error("An error occurred", extra={"user_id": "123"})

# Performance logging
perf_logger.start("data_processing")
try:
    # ... processing logic ...
    result = {"processed": 1000}
    perf_logger.end(success=True, extra_data=result)
except Exception as e:
    perf_logger.end(success=False, extra_data={"error": str(e)})
    raise
```

---

For additional examples and use cases, see the [Use Cases](../use-cases/) documentation. 