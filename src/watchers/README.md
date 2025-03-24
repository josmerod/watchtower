# Watchers Module

## Overview

The Watchers module provides a system for monitoring web pages for changes to specific content. When changes are detected, the system triggers alarms and records events for later analysis or notification.

## Components

- **BaseWatcher**: Abstract base class that defines the common structure for all watchers.
- **MSAppliedSkillsWatcher**: A specific watcher implementation that monitors the number of Microsoft Applied Skills credentials.

## How It Works

1. Each watcher periodically fetches a web page
2. The watcher extracts specific values from the content
3. The extracted values are compared with previous values
4. If changes are detected, an alarm is triggered and an event is recorded

## Event Structure

Events are recorded as JSON files with the following structure:

```json
{
  "id": "[timestamp]_[event_type]",
  "type": "[event_type]",
  "timestamp": "[ISO timestamp]",
  "watcher": "[watcher_name]",
  "url": "[monitored_url]",
  "old_value": "[previous_value]",
  "new_value": "[current_value]",
  "details": {
    // Additional event-specific details
  }
}
```

## Running Watchers

Watchers can be run from the command line using the `run_watcher.py` script or the `run_watcher.bat` batch file:

```
# Run all watchers continuously
python src/watchers/run_watcher.py

# Run a specific watcher once
python src/watchers/run_watcher.py ms_applied_skills --once

# Run a specific watcher with a custom interval (in seconds)
python src/watchers/run_watcher.py ms_applied_skills --interval 1800

# List available watchers
python src/watchers/run_watcher.py --list
```

## Creating New Watchers

To create a new watcher:

1. Create a new Python file in the `src/watchers` directory
2. Subclass `BaseWatcher` and implement the required methods:
   - `extract_value`: Extract the value to watch from the HTML content
   - `has_changed`: Determine if the value has changed enough to trigger an alarm
3. Optionally override `trigger_alarm` to customize the alarm behavior
4. Add the new watcher to `__init__.py` and `run_watcher.py`

Example implementation:

```python
from src.watchers.base_watcher import BaseWatcher

class MyCustomWatcher(BaseWatcher):
    def __init__(self, name: str = "custom_watcher", check_interval: int = 3600):
        url = "https://example.com/page-to-watch"
        super().__init__(name, url, check_interval)
    
    def extract_value(self, html_content: str) -> Any:
        # Extract and return the value to watch
        return extracted_value
    
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        # Return True if the value has changed enough to trigger an alarm
        return old_value != new_value
``` 