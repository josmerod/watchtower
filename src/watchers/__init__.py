"""Watchers module for Watchtower."""

# Legacy watchers (backward compatibility)
from watchers.base_watcher import BaseWatcher

# Enhanced watchers (new architecture)
from watchers.enhanced_watcher import (
    EnhancedWatcher,
    WatcherConfig,
    WatcherEvent,
    WatcherState,
)
from watchers.ms_skills_watcher import MSAppliedSkillsWatcher

__all__ = [
    # Legacy
    "BaseWatcher",
    # Enhanced
    "EnhancedWatcher",
    "MSAppliedSkillsWatcher",
    "WatcherConfig",
    "WatcherEvent",
    "WatcherState",
]

# Import any specific watchers here as they're added
