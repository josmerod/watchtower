"""Enhanced watcher system for Watchtower with modern architecture."""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import aiohttp
from pydantic import Field, validator

from src.config.settings import get_settings
from src.exceptions.watcher import (
    WatcherError,
    WatcherTimeoutError,
    WatcherValidationError,
)
from src.models.base import BaseModel as BaseWatchtowerModel
from src.models.base import TimestampedModel
from src.utils.file_system import get_file_system_manager
from src.utils.logging import get_logger, get_performance_logger


class WatcherState(TimestampedModel):
    """Model for watcher state persistence."""

    watcher_name: str = Field(..., description="Name of the watcher")
    last_check: datetime | None = Field(None, description="Last check timestamp")
    last_value: str | None = Field(None, description="Last extracted value")
    check_count: int = Field(default=0, description="Total number of checks performed")
    error_count: int = Field(default=0, description="Number of errors encountered")
    success_rate: float = Field(default=0.0, description="Success rate percentage")

    def calculate_success_rate(self) -> float:
        """Calculate success rate based on check and error counts."""
        if self.check_count == 0:
            return 0.0
        return ((self.check_count - self.error_count) / self.check_count) * 100.0

    def update_success_rate(self) -> None:
        """Update the success rate field."""
        self.success_rate = self.calculate_success_rate()


class WatcherEvent(TimestampedModel):
    """Model for watcher events."""

    watcher_name: str = Field(..., description="Name of the watcher")
    event_type: str = Field(..., description="Type of event")
    old_value: Any | None = Field(None, description="Previous value")
    new_value: Any | None = Field(None, description="Current value")
    url: str | None = Field(None, description="URL being watched")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional event details")

    @validator("event_type")
    def validate_event_type(cls, v):
        """Validate event type."""
        allowed_types = [
            "change_detected",
            "error_occurred",
            "check_started",
            "check_completed",
            "threshold_exceeded",
            "value_invalid",
        ]
        if v not in allowed_types:
            raise ValueError(f"Event type must be one of {allowed_types}")
        return v


class WatcherConfig(BaseWatchtowerModel):
    """Configuration model for watchers."""

    name: str = Field(..., description="Unique name for the watcher")
    url: str = Field(..., description="URL to watch")
    check_interval: int = Field(default=3600, ge=1, description="Check interval in seconds")
    max_retries: int = Field(default=3, ge=1, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, ge=1, description="Delay between retries in seconds")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    enabled: bool = Field(default=True, description="Whether the watcher is enabled")
    alert_threshold: int | None = Field(None, description="Alert after N consecutive failures")

    @validator("name")
    def validate_name(cls, v):
        """Validate watcher name."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Watcher name must be alphanumeric with underscores/hyphens")
        return v


class EnhancedWatcher(ABC):
    """Enhanced base class for all watchers with modern architecture."""

    def __init__(self, config: WatcherConfig | dict[str, Any]):
        """Initialize the enhanced watcher.

        Args:
            config: Watcher configuration (WatcherConfig object or dict).
        """
        if isinstance(config, dict):
            config = WatcherConfig(**config)

        self.config = config
        self.settings = get_settings()
        self.logger = get_logger(f"Watcher_{config.name}")
        self.perf_logger = get_performance_logger(f"Watcher_{config.name}")
        self.fs_manager = get_file_system_manager()

        # Initialize storage paths
        self._setup_storage()

        # Load or create state
        self.state = self._load_state()

        # Track consecutive failures for alerting
        self.consecutive_failures = 0

    def _setup_storage(self) -> None:
        """Setup storage directories and paths."""
        self.watcher_dir = self.fs_manager.get_absolute_path(f"data/watchers/{self.config.name}")
        self.events_dir = self.watcher_dir / "events"
        self.state_file = self.watcher_dir / "state.json"

        # Ensure directories exist
        self.fs_manager.ensure_directories(
            [
                f"data/watchers/{self.config.name}",
                f"data/watchers/{self.config.name}/events",
            ]
        )

    def _load_state(self) -> WatcherState:
        """Load watcher state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, encoding="utf-8") as f:
                    data = json.load(f)
                return WatcherState(**data)
        except Exception as e:
            self.logger.warning(f"Could not load state file: {e}")

        # Return new state if file doesn't exist or can't be loaded
        return WatcherState(watcher_name=self.config.name)

    def _save_state(self) -> None:
        """Save watcher state to file."""
        try:
            self.state.updated_at = datetime.now()
            self.state.update_success_rate()

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state.dict(), f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Could not save state file: {e}")

    def _record_event(
        self,
        event_type: str,
        old_value: Any = None,
        new_value: Any = None,
        details: dict[str, Any] | None = None,
    ) -> WatcherEvent:
        """Record a watcher event.

        Args:
            event_type: Type of event.
            old_value: Previous value.
            new_value: Current value.
            details: Additional event details.

        Returns:
            WatcherEvent object.
        """
        event = WatcherEvent(
            watcher_name=self.config.name,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
            url=self.config.url,
            details=details or {},
        )

        # Save event to file
        try:
            event_file = self.events_dir / f"{event.id}.json"
            with open(event_file, "w", encoding="utf-8") as f:
                json.dump(event.dict(), f, indent=2, default=str)

            self.logger.info(f"Event recorded: {event.event_type} ({event.id})")
        except Exception as e:
            self.logger.error(f"Could not save event: {e}")

        return event

    async def fetch_page(self) -> str:
        """Fetch page content asynchronously.

        Returns:
            HTML content of the page.

        Raises:
            WatcherError: If the page cannot be fetched.
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                self.logger.debug(f"Fetching {self.config.url}")

                async with session.get(self.config.url) as response:
                    response.raise_for_status()
                    content = await response.text()

                    self.logger.debug(f"Fetched {len(content)} characters from {self.config.url}")
                    return content

        except asyncio.TimeoutError as e:
            raise WatcherTimeoutError(
                message=f"Timeout fetching {self.config.url}",
                url=self.config.url,
                timeout=self.config.timeout,
                context={"watcher": self.config.name},
            ) from e
        except Exception as e:
            raise WatcherError(
                message=f"Failed to fetch {self.config.url}: {e!s}",
                error_code="FETCH_FAILED",
                context={
                    "watcher": self.config.name,
                    "url": self.config.url,
                    "error": str(e),
                },
            ) from e

    @abstractmethod
    async def extract_value(self, html_content: str) -> Any:
        """Extract the value to watch from HTML content.

        Args:
            html_content: HTML content of the page.

        Returns:
            The extracted value.
        """
        pass

    @abstractmethod
    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Determine if the value has changed significantly.

        Args:
            old_value: Previously extracted value.
            new_value: Current extracted value.

        Returns:
            True if change should trigger an alert.
        """
        pass

    def trigger_alert(self, old_value: Any, new_value: Any, details: dict[str, Any] | None = None) -> None:
        """Trigger an alert when a significant change is detected.

        Args:
            old_value: Previous value.
            new_value: Current value.
            details: Additional alert details.
        """
        self.logger.warning(f"CHANGE DETECTED in {self.config.name}: {old_value} -> {new_value}")

        # Record the change event
        self._record_event(
            event_type="change_detected",
            old_value=old_value,
            new_value=new_value,
            details=details,
        )

        # TODO: Integrate with notification system
        # In the future, this could send emails, Slack messages, etc.

    async def check(self) -> bool:
        """Perform a single check.

        Returns:
            True if check was successful, False otherwise.
        """
        if not self.config.enabled:
            self.logger.debug(f"Watcher {self.config.name} is disabled, skipping check")
            return True

        self.perf_logger.start(f"watcher_check_{self.config.name}")

        try:
            # Record check start
            self._record_event("check_started")

            # Fetch and extract value
            html_content = await self.fetch_page()
            current_value = await self.extract_value(html_content)

            # Validate extracted value
            if current_value is None:
                raise WatcherValidationError(
                    message="Extracted value is None",
                    value=current_value,
                    context={"watcher": self.config.name},
                )

            # Update state
            self.state.check_count += 1
            now = datetime.now()

            # Check for changes if we have a previous value
            if self.state.last_value is not None:
                if self.has_changed(self.state.last_value, current_value):
                    self.trigger_alert(
                        old_value=self.state.last_value,
                        new_value=current_value,
                        details={"check_time": now.isoformat()},
                    )
            else:
                self.logger.info(f"First check for {self.config.name}, value: {current_value}")

            # Update state
            self.state.last_check = now
            self.state.last_value = str(current_value)
            self.consecutive_failures = 0

            # Save state
            self._save_state()

            # Record successful completion
            self._record_event(
                "check_completed",
                details={"success": True, "value": str(current_value)},
            )

            self.perf_logger.end(success=True, extra_data={"value": str(current_value)})
            self.logger.debug(f"Check completed successfully for {self.config.name}")

            return True

        except Exception as e:
            self.state.error_count += 1
            self.consecutive_failures += 1

            # Save state even on error
            self._save_state()

            # Record error event
            self._record_event(
                "error_occurred",
                details={"error": str(e), "error_type": type(e).__name__},
            )

            # Check if we should alert on consecutive failures
            if self.config.alert_threshold and self.consecutive_failures >= self.config.alert_threshold:
                self.logger.error(f"Watcher {self.config.name} has failed {self.consecutive_failures} " f"consecutive times (threshold: {self.config.alert_threshold})")
                self._record_event(
                    "threshold_exceeded",
                    details={"consecutive_failures": self.consecutive_failures},
                )

            self.perf_logger.end(success=False, extra_data={"error": str(e)})
            self.logger.error(f"Check failed for {self.config.name}: {e}")

            return False

    async def run_once(self) -> bool:
        """Run a single check with retries.

        Returns:
            True if any attempt succeeded, False if all failed.
        """
        for attempt in range(self.config.max_retries):
            try:
                return await self.check()
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(f"Attempt {attempt + 1}/{self.config.max_retries} failed for " f"{self.config.name}: {e}. Retrying in {self.config.retry_delay}s...")
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    self.logger.error(f"All {self.config.max_retries} attempts failed for {self.config.name}")
                    return False

        return False

    async def run_continuous(self, max_iterations: int | None = None) -> None:
        """Run the watcher continuously.

        Args:
            max_iterations: Maximum number of iterations (None for infinite).
        """
        iteration = 0
        self.logger.info(f"Starting continuous monitoring for {self.config.name}")

        try:
            while max_iterations is None or iteration < max_iterations:
                await self.run_once()

                iteration += 1
                if max_iterations is not None:
                    self.logger.debug(f"Iteration {iteration}/{max_iterations} completed")

                # Wait for next check
                self.logger.debug(f"Waiting {self.config.check_interval} seconds until next check")
                await asyncio.sleep(self.config.check_interval)

        except KeyboardInterrupt:
            self.logger.info(f"Stopping watcher {self.config.name} due to keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Unexpected error in continuous monitoring: {e}")
            raise
        finally:
            self.logger.info(f"Watcher {self.config.name} stopped after {iteration} iterations")

    def get_status(self) -> dict[str, Any]:
        """Get current watcher status.

        Returns:
            Status dictionary.
        """
        return {
            "name": self.config.name,
            "enabled": self.config.enabled,
            "url": self.config.url,
            "last_check": (self.state.last_check.isoformat() if self.state.last_check else None),
            "last_value": self.state.last_value,
            "check_count": self.state.check_count,
            "error_count": self.state.error_count,
            "success_rate": self.state.success_rate,
            "consecutive_failures": self.consecutive_failures,
            "check_interval": self.config.check_interval,
        }
