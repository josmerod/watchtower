import os
import json
import time
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root


class BaseWatcher(ABC):
    """
    Base class for all watchers.
    
    Watchers are processes that periodically check if a web page has changed
    with respect to some specific value or content. If a change is detected,
    they trigger an alarm.
    """
    
    def __init__(self, name: str, url: str, check_interval: int = 3600):
        """
        Initialize the base watcher.
        
        Args:
            name (str): Unique name for this watcher
            url (str): URL to watch for changes
            check_interval (int): Time in seconds between checks (default: 1 hour)
        """
        self.name = name
        self.url = url
        self.check_interval = check_interval
        self.logger = get_logger(f"Watcher_{name}")
        
        # Ensure storage directories exist
        self.project_root = get_project_root()
        self.data_dir = os.path.join(self.project_root, f"data/watchers/{self.name}")
        ensure_directories([f"data/watchers/{self.name}"])
        
        # Path to store the state file
        self.state_file = os.path.join(self.data_dir, "state.json")
        
        # Path to store events
        self.events_dir = os.path.join(self.data_dir, "events")
        ensure_directories([f"data/watchers/{self.name}/events"])
        
        # Load previous state if exists
        self.previous_state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load the previous state from the state file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading state file: {str(e)}")
        
        # Return empty state if file doesn't exist or can't be loaded
        return {
            "last_check": None,
            "last_value": None,
            "first_seen": datetime.now().isoformat()
        }
    
    def _save_state(self, state: Dict[str, Any]):
        """Save the current state to the state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state file: {str(e)}")
    
    def _record_event(self, event_type: str, old_value: Any, new_value: Any, details: Optional[Dict[str, Any]] = None):
        """
        Record a change event.
        
        Args:
            event_type (str): Type of event (e.g., 'change_detected')
            old_value: Previous value
            new_value: Current value
            details: Additional details about the event
        """
        timestamp = datetime.now()
        event_id = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{event_type}"
        
        event = {
            "id": event_id,
            "type": event_type,
            "timestamp": timestamp.isoformat(),
            "watcher": self.name,
            "url": self.url,
            "old_value": old_value,
            "new_value": new_value,
            "details": details or {}
        }
        
        # Save event to file
        event_file = os.path.join(self.events_dir, f"{event_id}.json")
        try:
            with open(event_file, 'w') as f:
                json.dump(event, f, indent=2)
            self.logger.info(f"Event recorded: {event_id}")
        except Exception as e:
            self.logger.error(f"Error recording event: {str(e)}")
        
        return event
    
    def fetch_page(self) -> str:
        """
        Fetch the page content.
        
        Returns:
            str: HTML content of the page
        
        Raises:
            Exception: If the page cannot be fetched
        """
        try:
            self.logger.info(f"Fetching {self.url}")
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching URL {self.url}: {str(e)}")
            raise
    
    @abstractmethod
    def extract_value(self, html_content: str) -> Any:
        """
        Extract the value to watch from the HTML content.
        Must be implemented by subclasses.
        
        Args:
            html_content (str): HTML content of the page
            
        Returns:
            Any: The extracted value
        """
        pass
    
    @abstractmethod
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """
        Determine if the value has changed enough to trigger an alarm.
        Must be implemented by subclasses.
        
        Args:
            old_value: Previously extracted value
            new_value: Current extracted value
            
        Returns:
            bool: True if the change should trigger an alarm, False otherwise
        """
        pass
    
    def trigger_alarm(self, old_value: Any, new_value: Any):
        """
        Trigger an alarm when a change is detected.
        
        Args:
            old_value: Previous value
            new_value: Current value
        """
        self.logger.warning(f"CHANGE DETECTED in {self.name}: {old_value} -> {new_value}")
        
        # Record the event
        event = self._record_event(
            event_type="change_detected",
            old_value=old_value,
            new_value=new_value
        )
        
        # TODO: In the future, implement notification mechanisms here
        # For now, we just log the event
    
    def check(self):
        """
        Check if the watched value has changed.
        """
        try:
            # Fetch the page
            html_content = self.fetch_page()
            
            # Extract the value
            current_value = self.extract_value(html_content)
            
            # Get current time
            now = datetime.now().isoformat()
            
            # Initialize state if first run
            if self.previous_state["last_value"] is None:
                self.logger.info(f"First check for {self.name}, value: {current_value}")
                new_state = {
                    "last_check": now,
                    "last_value": current_value,
                    "first_seen": self.previous_state["first_seen"]
                }
                self._save_state(new_state)
                # return # MODIFIED FOR TESTING: Allow flow through to has_changed
            
            # Check if value has changed
            old_value = self.previous_state["last_value"] # This will be None if it was the first check and we didn't return
            if self.has_changed(old_value, current_value):
                self.trigger_alarm(old_value, current_value)
            
            # Update state
            new_state = {
                "last_check": now,
                "last_value": current_value,
                "first_seen": self.previous_state["first_seen"]
            }
            self._save_state(new_state)
            
        except Exception as e:
            self.logger.error(f"Error checking watcher {self.name}: {str(e)}")
    
    def run(self, continuous: bool = True, max_runs: int = None):
        """
        Run the watcher, either continuously or for a specified number of runs.
        
        Args:
            continuous (bool): Whether to run continuously
            max_runs (int, optional): Maximum number of runs if not continuous
        """
        self.logger.info(f"Starting watcher for {self.name} ({self.url})")
        
        run_count = 0
        
        try:
            while True:
                self.check()
                
                run_count += 1
                if not continuous or (max_runs is not None and run_count >= max_runs):
                    break
                
                self.logger.info(f"Sleeping for {self.check_interval} seconds")
                time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            self.logger.info("Watcher stopped by user")
        except Exception as e:
            self.logger.error(f"Watcher failed: {str(e)}")
        
        self.logger.info(f"Watcher {self.name} finished after {run_count} runs") 