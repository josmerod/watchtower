"""Alert rule engine for evaluating content and triggering notifications.

This module provides the core AlertEngine class that evaluates incoming
content against user-defined alert rules and generates alert events.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

from .models import AlertEvent, AlertRule


class AlertEngine:
    """Core alert rule engine.

    Evaluates incoming content against alert rules and generates
    alert events when rules match. Handles deduplication and
    asynchronous processing to avoid blocking watcher workflows.
    """

    def __init__(self):
        """Initialize the alert engine."""
        self.logger = get_logger("AlertEngine")
        self.settings = get_settings()

        # Initialize paths
        self.project_root = Path(get_project_root())
        self.data_dir = self.project_root / "data" / "alerts"

        # Cache for loaded rules
        self._rules_cache: dict[str, list[AlertRule]] = {}
        self._rules_cache_timestamp: dict[str, datetime] = {}

        # Deduplication cache (content_hash -> timestamp)
        self._dedup_cache: dict[str, datetime] = {}
        self._dedup_window = timedelta(hours=1)  # 1-hour deduplication window

        # Thread lock for thread safety
        self._lock = threading.RLock()

        # Performance metrics
        self._evaluations_count = 0
        self._matches_count = 0
        self._errors_count = 0

        self.logger.info("AlertEngine initialized")

    def evaluate_content(self, content: dict[str, Any], user_id: str) -> list[AlertEvent]:
        """Evaluate content against user's alert rules.

        Args:
            content: Content dictionary with metadata fields
            user_id: User ID to load rules for

        Returns:
            List of alert events generated from matching rules
        """
        try:
            with self._lock:
                self._evaluations_count += 1

                # Generate content hash for deduplication
                content_hash = self._generate_content_hash(content)

                # Check for duplicates within deduplication window
                if self._is_duplicate(content_hash):
                    self.logger.debug("Content duplicate detected, skipping evaluation")
                    return []

                # Load user's alert rules
                rules = self._load_user_rules(user_id)

                if not rules:
                    self.logger.debug(f"No alert rules found for user {user_id}")
                    return []

                # Evaluate against all active rules
                matching_events = []
                for rule in rules:
                    try:
                        if rule.matches_content(content):
                            alert_event = self._create_alert_event(rule, content, content_hash)
                            matching_events.append(alert_event)
                            self._matches_count += 1

                            # Update rule trigger statistics
                            rule.last_triggered = alert_event.triggered_at
                            rule.trigger_count += 1

                    except Exception as e:
                        self.logger.error(f"Error evaluating rule {rule.id}: {e}")
                        self._errors_count += 1

                # Store alert events
                if matching_events:
                    self._store_alert_events(user_id, matching_events)

                return matching_events

        except Exception as e:
            self.logger.error(f"Error in evaluate_content: {e}")
            self._errors_count += 1
            return []

    def _generate_content_hash(self, content: dict[str, Any]) -> str:
        """Generate a unique hash for content deduplication.

        Args:
            content: Content dictionary

        Returns:
            SHA-256 hash of normalized content
        """
        # Create normalized content for hashing
        # Include key fields that make content unique
        hashable_content = {
            "title": content.get("title", ""),
            "url": content.get("url", ""),
            "source": content.get("source", ""),
            "price": content.get("price"),
            "description": content.get("description", ""),
        }

        # Convert to JSON string with sorted keys for consistency
        content_json = json.dumps(hashable_content, sort_keys=True, ensure_ascii=False)

        # Generate SHA-256 hash
        return hashlib.sha256(content_json.encode("utf-8")).hexdigest()

    def _is_duplicate(self, content_hash: str) -> bool:
        """Check if content has already been processed within deduplication window.

        Args:
            content_hash: Hash of the content to check

        Returns:
            True if content is a duplicate, False otherwise
        """
        now = datetime.now()

        # Clean up old entries from deduplication cache
        self._cleanup_dedup_cache(now)

        # Check if content hash exists in cache
        if content_hash in self._dedup_cache:
            last_seen = self._dedup_cache[content_hash]
            if (now - last_seen) < self._dedup_window:
                return True
            else:
                # Entry is too old, remove it
                del self._dedup_cache[content_hash]

        # Add current content hash to cache
        self._dedup_cache[content_hash] = now
        return False

    def _cleanup_dedup_cache(self, now: datetime) -> None:
        """Remove old entries from deduplication cache.

        Args:
            now: Current timestamp
        """
        expired_hashes = [hash_val for hash_val, timestamp in self._dedup_cache.items() if (now - timestamp) >= self._dedup_window]

        for hash_val in expired_hashes:
            del self._dedup_cache[hash_val]

    def _load_user_rules(self, user_id: str) -> list[AlertRule]:
        """Load alert rules for a specific user.

        Args:
            user_id: User ID to load rules for

        Returns:
            List of user's alert rules
        """
        # Check cache first
        cache_key = f"user_{user_id}"
        now = datetime.now()

        if cache_key in self._rules_cache_timestamp:
            cache_age = now - self._rules_cache_timestamp[cache_key]
            if cache_age < timedelta(minutes=5):  # Cache for 5 minutes
                return self._rules_cache.get(cache_key, [])

        try:
            # Load rules from file
            rules_file = self.data_dir / user_id / "rules.json"
            if not rules_file.exists():
                self.logger.debug(f"No rules file found for user {user_id}")
                return []

            with open(rules_file, encoding="utf-8") as f:
                rules_data = json.load(f)

            # Convert to AlertRule objects
            rules = []
            for rule_data in rules_data:
                try:
                    rule = AlertRule(**rule_data)
                    if rule.active:
                        rules.append(rule)
                except Exception as e:
                    self.logger.error(f"Error loading rule {rule_data.get('id', 'unknown')}: {e}")

            # Update cache
            self._rules_cache[cache_key] = rules
            self._rules_cache_timestamp[cache_key] = now

            self.logger.info(f"Loaded {len(rules)} active rules for user {user_id}")
            return rules

        except Exception as e:
            self.logger.error(f"Error loading rules for user {user_id}: {e}")
            return []

    def _create_alert_event(self, rule: AlertRule, content: dict[str, Any], content_hash: str) -> AlertEvent:
        """Create an alert event from a matching rule and content.

        Args:
            rule: The rule that matched
            content: The content that triggered the rule
            content_hash: Hash of the content for deduplication

        Returns:
            AlertEvent object
        """
        # Generate content ID if not present
        content_id = content.get("id", content_hash[:16])

        # Create alert message
        message = f"Alert: {rule.name} - {content.get('title', 'No title')}"
        if content.get("description"):
            message = f"{message}\n{content['description']}"

        # Determine severity based on rule priority or content
        severity = "info"
        if "urgent" in rule.name.lower() or content.get("price") == 0:
            severity = "warning"

        return AlertEvent(
            rule_id=rule.id or str(hash(rule.name + rule.user_id)),
            rule_name=rule.name,
            user_id=rule.user_id,
            content_id=content_id,
            content=content,
            content_hash=content_hash,
            message=message,
            severity=severity,
        )

    def _store_alert_events(self, user_id: str, events: list[AlertEvent]) -> None:
        """Store alert events to file system.

        Args:
            user_id: User ID to store events for
            events: List of alert events to store
        """
        try:
            # Ensure directories exist
            user_events_dir = self.data_dir / user_id / "events"
            ensure_directories([str(user_events_dir)])

            # Store each event in its own file
            for event in events:
                timestamp = event.triggered_at.strftime("%Y%m%d_%H%M%S_%f")
                event_filename = f"{timestamp}_alert.json"
                event_file = user_events_dir / event_filename

                # Write event to file
                with open(event_file, "w", encoding="utf-8") as f:
                    json.dump(event.dict(), f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Stored {len(events)} alert events for user {user_id}")

        except Exception as e:
            self.logger.error(f"Error storing alert events for user {user_id}: {e}")
            raise

    def reload_rules(self, user_id: str = None) -> None:
        """Force reload of alert rules from storage.

        Args:
            user_id: Specific user to reload rules for, or None for all users
        """
        with self._lock:
            if user_id:
                cache_key = f"user_{user_id}"
                if cache_key in self._rules_cache:
                    del self._rules_cache[cache_key]
                if cache_key in self._rules_cache_timestamp:
                    del self._rules_cache_timestamp[cache_key]
                self.logger.info(f"Reloaded rules for user {user_id}")
            else:
                # Clear all cache
                self._rules_cache.clear()
                self._rules_cache_timestamp.clear()
                self.logger.info("Reloaded rules for all users")

    def get_metrics(self) -> dict[str, Any]:
        """Get alert engine performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        with self._lock:
            return {
                "evaluations_count": self._evaluations_count,
                "matches_count": self._matches_count,
                "errors_count": self._errors_count,
                "match_rate": (self._matches_count / max(self._evaluations_count, 1) * 100),
                "cached_users": len(self._rules_cache),
                "dedup_cache_size": len(self._dedup_cache),
                "dedup_window_hours": self._dedup_window.total_seconds() / 3600,
            }

    def clear_dedup_cache(self) -> None:
        """Clear the deduplication cache."""
        with self._lock:
            self._dedup_cache.clear()
            self.logger.info("Deduplication cache cleared")
