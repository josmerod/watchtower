# Watchers Development Guide

This guide provides comprehensive instructions for developing and deploying watchers in the Watchtower platform.

## Table of Contents

- [Overview](#overview)
- [BaseWatcher Framework](#basewatcher-framework)
- [Creating Custom Watchers](#creating-custom-watchers)
- [Advanced Watcher Patterns](#advanced-watcher-patterns)
- [Deployment and Scheduling](#deployment-and-scheduling)
- [Best Practices](#best-practices)

## Overview

Watchers are continuous monitoring components that detect changes in web content and trigger actions based on those changes. The Watchtower platform provides a robust `BaseWatcher` framework that handles state management, event logging, and change detection.

### Key Features

- **State Persistence**: JSON-based checkpoint system for resumable monitoring
- **Event Logging**: Timestamped change events with detailed context
- **Configurable Intervals**: Flexible polling frequencies (default: 1 hour)
- **Error Resilience**: Continues operation despite individual failures
- **Extensible Design**: Abstract interface for custom implementations

### Watcher Architecture

```
┌─────────────────────┐
│   External Source   │
└──────────┬──────────┘
           │
    ┌──────▼───────┐
    │   Extract    │
    │    Value     │
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │   Compare    │
    │ with Previous│
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │  Has Changed?│
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │  Log Event   │
    │ Update State │
    └──────────────┘
```

## BaseWatcher Framework

The `BaseWatcher` class (`src/watchers/base_watcher.py`) provides the foundation for all watchers.

### Core Components

```python
class BaseWatcher(ABC):
    """
    Abstract base class for content monitoring and change detection.

    Provides automatic:
    - State persistence in data/watchers/{name}/state.json
    - Event logging in data/watchers/{name}/events/
    - Change detection and comparison
    - Error handling and resilience
    """

    def __init__(self, name: str, check_interval: int = 3600):
        """
        Initialize watcher with name and check interval.

        Args:
            name: Unique identifier for this watcher
            check_interval: Seconds between checks (default: 3600 = 1 hour)
        """
        self.name = name
        self.check_interval = check_interval
        self.state_dir = Path(f"data/watchers/{name}")
        self.events_dir = self.state_dir / "events"

        # Create directories
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)
```

### Required Methods

Every watcher must implement these abstract methods:

#### 1. get_current_value()

Extract the current value to monitor from the source.

```python
@abstractmethod
def get_current_value(self) -> Any:
    """
    Fetch and extract the current value to monitor.

    Returns:
        The extracted value (can be any JSON-serializable type)

    Raises:
        Exception: If extraction fails (will be logged and handled)
    """
    pass
```

#### 2. check_for_changes()

Determine if a significant change has occurred.

```python
@abstractmethod
def check_for_changes(self, old_value: Any, new_value: Any) -> bool:
    """
    Compare old and new values to determine if change is significant.

    Args:
        old_value: Previously stored value (None on first run)
        new_value: Newly extracted value

    Returns:
        True if change should be logged, False otherwise
    """
    pass
```

### State Management

The watcher automatically manages state in JSON format:

```json
{
  "last_check": "2025-01-10T15:30:00Z",
  "last_value": "monitored_value",
  "check_count": 42,
  "change_count": 5
}
```

### Event Logging

Change events are logged with full context:

```json
{
  "timestamp": "2025-01-10T15:30:00Z",
  "watcher": "arxiv_watcher",
  "old_value": "previous_value",
  "new_value": "current_value",
  "change_type": "content_update",
  "details": {
    "additional": "context"
  }
}
```

## Creating Custom Watchers

### Simple Content Watcher

Monitor a web page for text changes:

```python
import requests
from bs4 import BeautifulSoup
from src.watchers.base_watcher import BaseWatcher

class SimpleContentWatcher(BaseWatcher):
    """Watch a web page for content changes."""

    def __init__(self, url: str, selector: str):
        super().__init__(name="simple_content_watcher")
        self.url = url
        self.selector = selector

    def get_current_value(self) -> str:
        """Extract text content from CSS selector."""
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        element = soup.select_one(self.selector)

        if not element:
            raise ValueError(f"Selector '{self.selector}' not found")

        return element.get_text(strip=True)

    def check_for_changes(self, old_value: str, new_value: str) -> bool:
        """Detect any text content change."""
        if old_value is None:
            return False  # Don't log on first run

        return old_value != new_value

# Usage
watcher = SimpleContentWatcher(
    url="https://example.com/updates",
    selector="#main-content"
)
watcher.run()
```

### Advanced List Monitoring

Track additions and removals in a list:

```python
from typing import List, Dict, Any
from src.watchers.base_watcher import BaseWatcher

class ListMonitorWatcher(BaseWatcher):
    """Monitor a list of items for additions and removals."""

    def __init__(self, name: str, fetch_function):
        super().__init__(name=name)
        self.fetch_function = fetch_function

    def get_current_value(self) -> List[str]:
        """Fetch current list of items."""
        items = self.fetch_function()
        return sorted(items)  # Sort for consistent comparison

    def check_for_changes(
        self,
        old_value: List[str],
        new_value: List[str]
    ) -> bool:
        """Detect additions or removals."""
        if old_value is None:
            return False

        old_set = set(old_value)
        new_set = set(new_value)

        added = new_set - old_set
        removed = old_set - new_set

        if added or removed:
            # Log detailed change information
            self.log_event({
                "added": list(added),
                "removed": list(removed),
                "added_count": len(added),
                "removed_count": len(removed)
            })
            return True

        return False
```

### Threshold-Based Watcher

Only alert when changes exceed a threshold:

```python
class ThresholdWatcher(BaseWatcher):
    """Alert only when value changes exceed threshold."""

    def __init__(self, name: str, threshold: float = 0.1):
        super().__init__(name=name)
        self.threshold = threshold

    def get_current_value(self) -> float:
        """Fetch numeric value to monitor."""
        # Implementation to fetch value
        pass

    def check_for_changes(
        self,
        old_value: float,
        new_value: float
    ) -> bool:
        """Alert only if change exceeds threshold percentage."""
        if old_value is None or old_value == 0:
            return False

        change_percent = abs((new_value - old_value) / old_value)

        if change_percent >= self.threshold:
            self.log_event({
                "old_value": old_value,
                "new_value": new_value,
                "change_percent": change_percent,
                "threshold": self.threshold
            })
            return True

        return False
```

## Advanced Watcher Patterns

### Enhanced Watcher with Notifications

```python
from src.watchers.enhanced_watcher import EnhancedWatcher

class NotifyingWatcher(EnhancedWatcher):
    """Watcher with email notifications on changes."""

    def __init__(self, name: str, email_config: Dict[str, Any]):
        super().__init__(name=name)
        self.email_config = email_config

    def on_change_detected(
        self,
        old_value: Any,
        new_value: Any,
        event_data: Dict[str, Any]
    ):
        """Send notification when change is detected."""
        subject = f"Change Detected: {self.name}"
        body = f"""
        Change detected in {self.name}

        Previous value: {old_value}
        New value: {new_value}

        Details: {event_data}
        """

        self.send_email(subject, body)

    def send_email(self, subject: str, body: str):
        """Send email notification."""
        # Email sending implementation
        pass
```

### Multi-Source Aggregation Watcher

```python
class AggregationWatcher(BaseWatcher):
    """Monitor multiple sources and aggregate results."""

    def __init__(self, name: str, sources: List[callable]):
        super().__init__(name=name)
        self.sources = sources

    def get_current_value(self) -> Dict[str, Any]:
        """Aggregate data from multiple sources."""
        results = {}

        for i, source_func in enumerate(self.sources):
            try:
                results[f"source_{i}"] = source_func()
            except Exception as e:
                self.logger.error(f"Source {i} failed: {e}")
                results[f"source_{i}"] = None

        return results

    def check_for_changes(
        self,
        old_value: Dict[str, Any],
        new_value: Dict[str, Any]
    ) -> bool:
        """Check if any source has changed."""
        if old_value is None:
            return False

        for key in new_value:
            if old_value.get(key) != new_value.get(key):
                self.log_event({
                    "changed_source": key,
                    "old_value": old_value.get(key),
                    "new_value": new_value.get(key)
                })
                return True

        return False
```

## Deployment and Scheduling

### Running Watchers

#### Single Execution

```bash
# With UV (recommended)
uv run python src/watchers/run_watcher.py arxiv_watcher --once

# Traditional method
python src/watchers/run_watcher.py arxiv_watcher --once
```

#### Continuous Monitoring

```bash
# Run continuously with automatic interval management
uv run python src/watchers/run_watcher.py arxiv_watcher

# Run all registered watchers
uv run python src/watchers/run_watcher.py
```

#### List Available Watchers

```bash
uv run python src/watchers/run_watcher.py --list
```

### Systemd Service (Linux)

Create `/etc/systemd/system/watchtower-watchers.service`:

```ini
[Unit]
Description=Watchtower Watchers Service
After=network.target

[Service]
Type=simple
User=watchtower
Group=watchtower
WorkingDirectory=/opt/watchtower
Environment=PATH=/opt/watchtower/.venv/bin
ExecStart=/opt/watchtower/.venv/bin/python src/watchers/run_watcher.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable watchtower-watchers
sudo systemctl start watchtower-watchers
```

### Windows Task Scheduler

Use the provided batch script with Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily or On startup
4. Action: Start a program
5. Program: `C:\path\to\watchtower\run_watcher.bat`

### Docker Deployment

```yaml
# docker-compose.yml
services:
  watchers:
    build: .
    command: ["uv", "run", "python", "src/watchers/run_watcher.py"]
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - CHECK_INTERVAL=3600
    restart: unless-stopped
```

## Best Practices

### 1. Error Handling

Always implement robust error handling:

```python
def get_current_value(self) -> Any:
    """Fetch current value with proper error handling."""
    try:
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()
        return self.parse_response(response)
    except requests.RequestException as e:
        self.logger.error(f"Network error: {e}")
        raise
    except ValueError as e:
        self.logger.error(f"Parsing error: {e}")
        raise
```

### 2. Rate Limiting

Respect source rate limits:

```python
import time
from functools import wraps

def rate_limit(calls_per_minute: int):
    """Decorator to limit API calls."""
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait_time = min_interval - elapsed

            if wait_time > 0:
                time.sleep(wait_time)

            last_called[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

class RateLimitedWatcher(BaseWatcher):
    @rate_limit(calls_per_minute=10)
    def get_current_value(self) -> Any:
        """Fetch with automatic rate limiting."""
        return self.fetch_data()
```

### 3. Caching

Implement intelligent caching for expensive operations:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedWatcher(BaseWatcher):
    def __init__(self, name: str, cache_duration: int = 300):
        super().__init__(name=name)
        self.cache_duration = cache_duration
        self._cache = None
        self._cache_time = None

    def get_current_value(self) -> Any:
        """Get value with caching."""
        now = datetime.utcnow()

        if (self._cache is not None and
            self._cache_time is not None and
            now - self._cache_time < timedelta(seconds=self.cache_duration)):
            return self._cache

        value = self.fetch_fresh_data()
        self._cache = value
        self._cache_time = now
        return value
```

### 4. Testing

Write comprehensive tests for your watchers:

```python
# tests/watchers/test_my_watcher.py
import pytest
from unittest.mock import Mock, patch
from src.watchers.my_watcher import MyWatcher

class TestMyWatcher:
    @pytest.fixture
    def watcher(self, tmp_path):
        """Create watcher with temporary directory."""
        watcher = MyWatcher(name="test_watcher")
        watcher.state_dir = tmp_path / "state"
        watcher.events_dir = tmp_path / "events"
        watcher.state_dir.mkdir(parents=True)
        watcher.events_dir.mkdir(parents=True)
        return watcher

    @patch('requests.get')
    def test_get_current_value(self, mock_get, watcher):
        """Test value extraction."""
        mock_response = Mock()
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        value = watcher.get_current_value()
        assert value == "Test"

    def test_check_for_changes(self, watcher):
        """Test change detection."""
        assert watcher.check_for_changes("old", "new") == True
        assert watcher.check_for_changes("same", "same") == False
        assert watcher.check_for_changes(None, "first") == False
```

### 5. Logging

Use structured logging with appropriate levels:

```python
import logging

class ProperlyLoggedWatcher(BaseWatcher):
    def get_current_value(self) -> Any:
        """Fetch with comprehensive logging."""
        self.logger.info(f"Fetching data from {self.url}")

        try:
            data = self.fetch_data()
            self.logger.info(f"Successfully fetched {len(data)} items")
            return data
        except Exception as e:
            self.logger.error(
                f"Failed to fetch data: {e}",
                exc_info=True,
                extra={"url": self.url}
            )
            raise
```

### 6. Documentation

Document your watchers thoroughly:

```python
class WellDocumentedWatcher(BaseWatcher):
    """
    Monitor XYZ source for updates.

    This watcher checks for new items every hour and logs
    changes to the event system.

    Attributes:
        source_url: URL of the source to monitor
        filter_criteria: Optional criteria for filtering items

    Example:
        >>> watcher = WellDocumentedWatcher(
        ...     source_url="https://example.com/feed",
        ...     filter_criteria={"category": "tech"}
        ... )
        >>> watcher.run()
    """

    def __init__(
        self,
        source_url: str,
        filter_criteria: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize watcher with source configuration.

        Args:
            source_url: URL to monitor for changes
            filter_criteria: Optional filtering parameters
        """
        super().__init__(name="well_documented_watcher")
        self.source_url = source_url
        self.filter_criteria = filter_criteria or {}
```

## Additional Resources

- **Base Watcher Source**: `src/watchers/base_watcher.py`
- **Example Watchers**: `src/watchers/example_enhanced_watcher.py`
- **ArXiv Watcher**: `src/watchers/arxiv_watcher.py`
- **Enhanced Watcher**: `src/watchers/enhanced_watcher.py`
- **MS Skills Watcher**: `src/watchers/ms_skills_watcher.py`

## Troubleshooting

### Common Issues

1. **State file corruption**: Delete `data/watchers/{name}/state.json` to reset
2. **Permission errors**: Ensure write access to `data/watchers/` directory
3. **Network timeouts**: Increase timeout values or implement retry logic
4. **Memory leaks**: Ensure proper cleanup in long-running watchers

This guide provides a comprehensive foundation for developing robust, production-ready watchers for the Watchtower platform.
