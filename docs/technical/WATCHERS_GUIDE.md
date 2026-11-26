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

    def __init__(
        self,
        name: str,
        url: str,
        check_interval: int = 3600,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        Initialize the base watcher.

        Args:
            name: Unique name for this watcher
            url: URL to watch for changes
            check_interval: Time in seconds between checks (default: 1 hour)
            max_retries: Maximum number of retry attempts for network operations
            retry_delay: Initial delay in seconds between retries (exponential backoff)
        """
        self.name = name
        self.url = url
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = get_logger(f"Watcher_{name}")

        self.project_root = Path(get_project_root())
        self.data_dir = self.project_root / "data" / "watchers" / self.name
        ensure_directories([f"data/watchers/{self.name}"])

        # Path to store the state file
        self.state_file = self.data_dir / "state.json"

        # Path to store events
        self.events_dir = self.data_dir / "events"
        ensure_directories([f"data/watchers/{self.name}/events"])

        self.proxy_manager = ProxyManager()

        # Load previous state if exists
        self.previous_state = self._load_state()
```

### Required Methods

Every watcher must implement these two abstract methods. `check()` drives them in order: it fetches the page with `fetch_page()`, passes the HTML to `extract_value()`, and from the second run on compares the result with the stored value through `has_changed()`. When `has_changed()` returns `True`, `check()` calls `trigger_alarm(old_value, new_value)`, which logs a warning and records a `change_detected` event. On the first run `check()` only stores the extracted value, so `has_changed()` is not called and no event is recorded.

#### 1. extract_value()

Extract the current value to monitor from the fetched page.

```python
@abstractmethod
def extract_value(self, html_content: str) -> Any:
    """
    Extract the value to watch from the HTML content.

    Args:
        html_content: HTML content of the page

    Returns:
        The extracted value
    """
    pass
```

#### 2. has_changed()

Determine if a significant change has occurred.

```python
@abstractmethod
def has_changed(self, old_value: Any, new_value: Any) -> bool:
    """
    Determine if the value has changed enough to trigger an alarm.

    Args:
        old_value: Previously extracted value
        new_value: Current extracted value

    Returns:
        True if the change should trigger an alarm, False otherwise
    """
    pass
```

### State Management

The watcher automatically manages state in JSON format, in `data/watchers/{name}/state.json`:

```json
{
  "last_check": "2025-01-10T15:30:00.123456",
  "last_value": "monitored_value",
  "first_seen": "2025-01-10T14:30:00.123456"
}
```

`last_value` is the value returned by the last `extract_value()` call, `last_check` the time of that check and `first_seen` the time the state was created.

### Event Logging

Change events are logged with full context, one JSON file per event in `data/watchers/{name}/events/`:

```json
{
  "id": "20250110153000_change_detected",
  "type": "change_detected",
  "timestamp": "2025-01-10T15:30:00.123456",
  "watcher": "simple_content_watcher",
  "url": "https://example.com/updates",
  "old_value": "previous_value",
  "new_value": "current_value",
  "details": {
    "additional": "context"
  }
}
```

## Creating Custom Watchers

### Simple Content Watcher

Monitor a web page for text changes:

```python
from bs4 import BeautifulSoup
from src.watchers.base_watcher import BaseWatcher

class SimpleContentWatcher(BaseWatcher):
    """Watch a web page for content changes."""

    def __init__(self, url: str, selector: str):
        super().__init__(name="simple_content_watcher", url=url)
        self.selector = selector

    def extract_value(self, html_content: str) -> str:
        """Extract text content from CSS selector."""
        soup = BeautifulSoup(html_content, 'html.parser')
        element = soup.select_one(self.selector)

        if not element:
            raise ValueError(f"Selector '{self.selector}' not found")

        return element.get_text(strip=True)

    def has_changed(self, old_value: str, new_value: str) -> bool:
        """Detect any text content change."""
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
from typing import Any
from src.watchers.base_watcher import BaseWatcher

class ListMonitorWatcher(BaseWatcher):
    """Monitor a list of items for additions and removals."""

    def __init__(self, name: str, url: str, fetch_function):
        super().__init__(name=name, url=url)
        self.fetch_function = fetch_function

    def extract_value(self, html_content: str) -> list[str]:
        """Fetch current list of items."""
        items = self.fetch_function()
        return sorted(items)  # Sort for consistent comparison

    def has_changed(
        self,
        old_value: list[str],
        new_value: list[str]
    ) -> bool:
        """Detect additions or removals."""
        old_set = set(old_value)
        new_set = set(new_value)

        added = new_set - old_set
        removed = old_set - new_set

        return bool(added or removed)

    def trigger_alarm(self, old_value: Any, new_value: Any) -> None:
        """Record what was added and removed with the change event."""
        added = sorted(set(new_value) - set(old_value))
        removed = sorted(set(old_value) - set(new_value))

        super()._record_event(
            event_type="change_detected",
            old_value=old_value,
            new_value=new_value,
            details={
                "added": added,
                "removed": removed,
                "added_count": len(added),
                "removed_count": len(removed)
            }
        )
```

### Threshold-Based Watcher

Only alert when changes exceed a threshold:

```python
class ThresholdWatcher(BaseWatcher):
    """Alert only when value changes exceed threshold."""

    def __init__(self, name: str, url: str, threshold: float = 0.1):
        super().__init__(name=name, url=url)
        self.threshold = threshold

    def extract_value(self, html_content: str) -> float:
        """Extract numeric value to monitor."""
        # Implementation to parse the value out of html_content
        pass

    def has_changed(
        self,
        old_value: float,
        new_value: float
    ) -> bool:
        """Alert only if change exceeds threshold percentage."""
        if not old_value:
            return False

        change_percent = abs((new_value - old_value) / old_value)
        return change_percent >= self.threshold

    def trigger_alarm(self, old_value: float, new_value: float) -> None:
        """Record the size of the change with the change event."""
        change_percent = abs((new_value - old_value) / old_value)

        super()._record_event(
            event_type="change_detected",
            old_value=old_value,
            new_value=new_value,
            details={
                "change_percent": change_percent,
                "threshold": self.threshold
            }
        )
```

## Advanced Watcher Patterns

### Enhanced Watcher with Notifications

```python
from typing import Any
from src.watchers.base_watcher import BaseWatcher

class NotifyingWatcher(BaseWatcher):
    """Watcher with email notifications on changes."""

    def __init__(self, name: str, url: str, email_config: dict[str, Any]):
        super().__init__(name=name, url=url)
        self.email_config = email_config

    def trigger_alarm(self, old_value: Any, new_value: Any) -> None:
        """Record the event, then send a notification when a change is detected."""
        super().trigger_alarm(old_value, new_value)

        subject = f"Change Detected: {self.name}"
        body = f"""
        Change detected in {self.name}

        Previous value: {old_value}
        New value: {new_value}
        """

        self.send_email(subject, body)

    def send_email(self, subject: str, body: str):
        """Send email notification."""
        # Email sending implementation
        pass
```

### Multi-Source Aggregation Watcher

```python
from collections.abc import Callable
from typing import Any

class AggregationWatcher(BaseWatcher):
    """Monitor multiple sources and aggregate results."""

    def __init__(self, name: str, url: str, sources: list[Callable[[], Any]]):
        super().__init__(name=name, url=url)
        self.sources = sources

    def extract_value(self, html_content: str) -> dict[str, Any]:
        """Aggregate data from multiple sources."""
        results = {}

        for i, source_func in enumerate(self.sources):
            try:
                results[f"source_{i}"] = source_func()
            except Exception as e:
                self.logger.error(f"Source {i} failed: {e}")
                results[f"source_{i}"] = None

        return results

    def has_changed(
        self,
        old_value: dict[str, Any],
        new_value: dict[str, Any]
    ) -> bool:
        """Check if any source has changed."""
        for key in new_value:
            if old_value.get(key) != new_value.get(key):
                return True

        return False

    def trigger_alarm(self, old_value: Any, new_value: Any) -> None:
        """Record which sources changed with the change event."""
        changed_sources = [
            key for key in new_value
            if old_value.get(key) != new_value.get(key)
        ]

        super()._record_event(
            event_type="change_detected",
            old_value=old_value,
            new_value=new_value,
            details={"changed_sources": changed_sources}
        )
```

## Deployment and Scheduling

### Running Watchers

#### Single Execution

```bash
# With UV (recommended)
uv run python src/watchers/run_watcher.py ms_applied_skills --once

# Traditional method
python src/watchers/run_watcher.py ms_applied_skills --once
```

#### Continuous Monitoring

```bash
# Run continuously with automatic interval management
uv run python src/watchers/run_watcher.py ms_applied_skills

# Run all registered watchers
uv run python src/watchers/run_watcher.py
```

#### List Available Watchers

```bash
uv run python src/watchers/run_watcher.py --list
```

`run_watcher.py` is the manual runner. `list_available_watchers()` returns only `ms_applied_skills`, so that is the only watcher it can launch; `--interval` sets the seconds between checks (default: 3600) and `--num-runs` limits a continuous run.

The runner is not how the repository's watchers run in production. There is no watchers service: `deployment/supervisord.conf` starts three programs, `dashboard`, `api` and `etl_scheduler`, and the scheduler (`deployment/etl_scheduler.py`) runs `./run_all_etl.sh` when it starts and then every 2 hours. That cycle is the list `ETL_SCRIPTS` in `run_all_etl_orchestrator.py`, which includes `src/watchers/ms_skills_watcher.py`, `src/watchers/courses_watcher.py` and `src/watchers/data_freshness_watcher.py`: `MSAppliedSkillsWatcher`, `CoursesWatcher` and `DataFreshnessWatcher` each run once per invocation and exit. `ArxivWatcher` is not run on its own; `src/etl/arxiv/arxiv_etl.py` creates it and calls `watcher.run(continuous=False, max_runs=1)`.

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

Use the command-line runner with Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily or On startup
4. Action: Start a program
5. Program: `uv`, with the arguments `run python src/watchers/run_watcher.py --once` and *Start in* set to the repository root

### Docker Deployment

```yaml
# docker-compose.yml
services:
  watchers:
    build: .
    command: ["uv", "run", "python", "src/watchers/run_watcher.py", "--interval", "3600"]
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

## Best Practices

### 1. Error Handling

Always implement robust error handling. `fetch_page()` already retries the request (`max_retries` attempts with exponential backoff) and raises when all of them fail, so the parsing of the fetched page is what belongs in `extract_value()`:

```python
def extract_value(self, html_content: str) -> Any:
    """Extract the value with proper error handling."""
    try:
        return self.parse_response(html_content)
    except ValueError as e:
        self.logger.error(f"Parsing error: {e}")
        raise
```

`check()` catches the exception, logs it and leaves the stored value untouched, so the next run compares against the last good value.

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
    def fetch_page(self) -> str:
        """Fetch the page with automatic rate limiting."""
        return super().fetch_page()
```

### 3. Caching

Implement intelligent caching for expensive operations:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedWatcher(BaseWatcher):
    def __init__(self, name: str, url: str, cache_duration: int = 300):
        super().__init__(name=name, url=url)
        self.cache_duration = cache_duration
        self._cache = None
        self._cache_time = None

    def extract_value(self, html_content: str) -> Any:
        """Get value with caching."""
        now = datetime.utcnow()

        if (self._cache is not None and
            self._cache_time is not None and
            now - self._cache_time < timedelta(seconds=self.cache_duration)):
            return self._cache

        value = self.parse_response(html_content)
        self._cache = value
        self._cache_time = now
        return value
```

### 4. Testing

Write comprehensive tests for your watchers:

```python
# Tests/unit/test_my_watcher.py
import pytest
from src.watchers.my_watcher import MyWatcher

class TestMyWatcher:
    @pytest.fixture
    def watcher(self, tmp_path, monkeypatch):
        """Create watcher with temporary directory."""
        monkeypatch.setattr("src.watchers.base_watcher.get_project_root", lambda: str(tmp_path))
        monkeypatch.setattr("src.watchers.base_watcher.ensure_directories", lambda dirs: None)
        watcher = MyWatcher(name="test_watcher", url="https://example.com")
        watcher.data_dir = tmp_path / "state"
        watcher.events_dir = tmp_path / "events"
        watcher.state_file = watcher.data_dir / "state.json"
        watcher.data_dir.mkdir(parents=True)
        watcher.events_dir.mkdir(parents=True)
        watcher.previous_state = watcher._load_state()
        return watcher

    def test_extract_value(self, watcher):
        """Test value extraction."""
        value = watcher.extract_value('<html><body>Test</body></html>')
        assert value == "Test"

    def test_has_changed(self, watcher):
        """Test change detection."""
        assert watcher.has_changed("old", "new") == True
        assert watcher.has_changed("same", "same") == False
```

### 5. Logging

Use structured logging with appropriate levels:

```python
import logging

class ProperlyLoggedWatcher(BaseWatcher):
    def extract_value(self, html_content: str) -> Any:
        """Extract with comprehensive logging."""
        self.logger.info(f"Fetching data from {self.url}")

        try:
            data = self.parse_response(html_content)
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
        filter_criteria: dict[str, Any] | None = None
    ):
        """
        Initialize watcher with source configuration.

        Args:
            source_url: URL to monitor for changes
            filter_criteria: Optional filtering parameters
        """
        super().__init__(name="well_documented_watcher", url=source_url)
        self.source_url = source_url
        self.filter_criteria = filter_criteria or {}
```

## Additional Resources

- **Base Watcher Source**: `src/watchers/base_watcher.py`
- **ArXiv Watcher**: `src/watchers/arxiv_watcher.py`
- **MS Skills Watcher**: `src/watchers/ms_skills_watcher.py`
- **Courses Watcher**: `src/watchers/courses_watcher.py`
- **Data Freshness Watcher**: `src/watchers/data_freshness_watcher.py`
- **Runner**: `src/watchers/run_watcher.py`

## Troubleshooting

### Common Issues

1. **State file corruption**: Delete `data/watchers/{name}/state.json` to reset
2. **Permission errors**: Ensure write access to `data/watchers/` directory
3. **Network timeouts**: Increase timeout values or implement retry logic
4. **Memory leaks**: Ensure proper cleanup in long-running watchers

This guide provides a comprehensive foundation for developing robust, production-ready watchers for the Watchtower platform.
