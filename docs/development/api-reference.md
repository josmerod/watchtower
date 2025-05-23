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
| `environment` | `Environment` | Current environment (dev/test/staging/prod) |
| `project_root` | `str` | Auto-detected project root directory |
| `data_dir` | `str` | Data storage directory |
| `logs_dir` | `str` | Logs storage directory |

#### Component Configurations

- **`database`**: `DatabaseConfig` - Database connection settings
- **`logging`**: `LoggingConfig` - Logging configuration
- **`scraping`**: `ScrapingConfig` - Web scraping settings
- **`etl`**: `ETLConfig` - ETL pipeline configuration
- **`watchers`**: `WatcherConfig` - Watcher monitoring settings
- **`api`**: `APIConfig` - API server configuration
- **`streamlit`**: `StreamlitConfig` - Streamlit dashboard settings

#### Methods

```python
# Environment checks
settings.is_development() -> bool
settings.is_production() -> bool
settings.is_testing() -> bool

# Path utilities
settings.get_data_path("subdir", "file.txt") -> Path
settings.get_logs_path("component.log") -> Path
settings.get_config_path("config.json") -> Path

# Directory management
settings.create_directories() -> None
```

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
```

---

## ETL Framework

### `BaseETL` Class

Abstract base class for all ETL processes with comprehensive error handling and monitoring.

```python
from src.etl.base import BaseETL

class MyETL(BaseETL[InputType, OutputType]):
    def extract(self) -> List[InputType]:
        # Implementation
        pass
    
    def transform(self, data: List[InputType]) -> List[OutputType]:
        # Implementation
        pass
    
    def load(self, data: List[OutputType]) -> None:
        # Implementation
        pass
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Unique ETL process name |
| `description` | `str` | `None` | ETL process description |
| `batch_size` | `int` | `1000` | Records per batch |
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
```

#### ETL Metrics

The `ETLMetrics` model tracks execution statistics:

```python
@dataclass
class ETLMetrics:
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    error_count: int = 0
    
    @property
    def success_rate(self) -> float
    
    @property
    def is_successful(self) -> bool
```

#### Checkpointing

ETL processes support automatic checkpointing for recovery:

```python
@dataclass
class ETLCheckpoint:
    etl_name: str
    checkpoint_id: str
    timestamp: datetime
    last_processed_id: Optional[str]
    processed_count: int
    metadata: Dict[str, Any]
```

### Specialized ETL Classes

#### `SimpleETL`

For basic dictionary-based ETL processes:

```python
from src.etl.base import SimpleETL

class NewsETL(SimpleETL):
    def extract(self) -> List[Dict[str, Any]]:
        # Return list of dictionaries
        pass
```

#### `DataFrameETL`

For data processing with DataFrame output:

```python
from src.etl.base import DataFrameETL

class AnalyticsETL(DataFrameETL):
    # Includes CSV and Parquet export methods
    def save_as_csv(self, data: List[Dict], filename: str) -> Path
    def save_as_parquet(self, data: List[Dict], filename: str) -> Path
```

---

## Watcher System

### `BaseWatcher` Class

Abstract base class for monitoring web content changes.

```python
from src.watchers.base_watcher import BaseWatcher

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
watcher.run(continuous=True, max_runs=None) -> None  # Continuous monitoring

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

Watchers maintain persistent state:

```json
{
  "last_check": "2025-01-23T14:05:30.123456",
  "last_value": "monitored_value",
  "first_seen": "2025-01-20T10:00:00.000000"
}
```

---

## Models & Validation

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
# - updated_at: datetime (UTC)
```

### Configuration Models

Pydantic models for component configuration with validation:

```python
from src.config.models import (
    DatabaseConfig,
    LoggingConfig, 
    ScrapingConfig,
    ETLConfig,
    WatcherConfig
)

# Example usage
db_config = DatabaseConfig(
    url="postgresql://localhost/watchtower",
    pool_size=10
)
```

#### Available Models

| Model | Purpose |
|-------|---------|
| `DatabaseConfig` | Database connection settings |
| `LoggingConfig` | Logging configuration |
| `ScrapingConfig` | Web scraping parameters |
| `APIConfig` | API server settings |
| `StreamlitConfig` | Dashboard configuration |
| `SecurityConfig` | Security and authentication |
| `MonitoringConfig` | Observability settings |
| `NotificationConfig` | Alert mechanisms |
| `WatcherConfig` | Monitoring parameters |
| `ETLConfig` | Pipeline configuration |

---

## Utilities & Helpers

### Logging System

Enhanced logging with performance monitoring:

```python
from src.utils.logging import get_logger, get_performance_logger

# Standard logger
logger = get_logger("component_name")
logger.info("Message")

# Performance logger with timing
perf_logger = get_performance_logger("component_name")
with perf_logger.timer("operation_name"):
    # Timed operation
    pass
```

### File System Utilities

Cross-platform file operations:

```python
from src.utils.file_system import (
    ensure_directories,
    get_project_root,
    safe_write_json,
    safe_read_json
)

# Ensure directories exist
ensure_directories(["data/output", "logs"])

# Get project root
root = get_project_root()

# Safe JSON operations
safe_write_json(data, "output.json")
data = safe_read_json("input.json")
```

---

## Exception Handling

### Exception Hierarchy

Comprehensive exception system with error codes:

```python
from src.exceptions.base import WatchtowerError
from src.exceptions.etl import ETLError, ExtractionError
from src.exceptions.watcher import WatcherError

try:
    # Operation that might fail
    pass
except ETLError as e:
    logger.error(f"ETL failed: {e.error_code} - {e.message}")
    logger.error(f"Context: {e.context}")
```

#### Exception Types

| Exception | Use Case |
|-----------|----------|
| `WatchtowerError` | Base exception |
| `ETLError` | ETL process failures |
| `ExtractionError` | Data extraction issues |
| `TransformationError` | Data transformation problems |
| `LoadError` | Data loading failures |
| `WatcherError` | Monitoring failures |
| `ConfigurationError` | Configuration issues |

### Error Handling Decorator

Automatic exception handling with context preservation:

```python
from src.exceptions.base import handle_exception

@handle_exception(
    error_type=ETLError,
    error_code="EXTRACTION_FAILED",
    reraise=True
)
def extract_data():
    # Function implementation
    pass
```

---

## Usage Examples

### Complete ETL Example

```python
from src.etl.base import SimpleETL
from src.config.settings import get_settings

class NewsETL(SimpleETL):
    def extract(self) -> List[Dict[str, Any]]:
        # Fetch from RSS feed
        return feed_data
    
    def transform(self, data: List[Dict]) -> List[Dict]:
        # Clean and validate data
        return transformed_data
    
    def load(self, data: List[Dict]) -> None:
        # Save to files
        self.save_as_json(data, "news.json")
        self.save_as_csv(data, "news.csv")

# Run ETL
etl = NewsETL("news_pipeline")
metrics = etl.run()
print(f"Processed {metrics.records_loaded} records in {metrics.duration_seconds}s")
```

### Complete Watcher Example

```python
from src.watchers.base_watcher import BaseWatcher
from bs4 import BeautifulSoup

class PriceWatcher(BaseWatcher):
    def extract_value(self, html_content: str) -> float:
        soup = BeautifulSoup(html_content, 'html.parser')
        price_elem = soup.find('span', class_='price')
        return float(price_elem.text.replace('$', ''))
    
    def has_changed(self, old_value: float, new_value: float) -> bool:
        # Trigger if price drops by more than 10%
        if old_value is None:
            return False
        return (old_value - new_value) / old_value > 0.1

# Run watcher
watcher = PriceWatcher("product_price", "https://store.com/product")
watcher.run(continuous=True)
```

---

For additional examples and use cases, see the [Use Cases](../use-cases/) documentation. 