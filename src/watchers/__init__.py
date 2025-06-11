"""Watchers module for Watchtower."""

# Legacy watchers (backward compatibility)
from watchers.base_watcher import BaseWatcher
from watchers.ms_skills_watcher import MSAppliedSkillsWatcher

# Enhanced watchers (new architecture)
from watchers.enhanced_watcher import (
    EnhancedWatcher,
    WatcherConfig, 
    WatcherState,
    WatcherEvent
)

__all__ = [
    # Legacy
    "BaseWatcher",
    "MSAppliedSkillsWatcher",
    
    # Enhanced
    "EnhancedWatcher", 
    "WatcherConfig",
    "WatcherState",
    "WatcherEvent",
]

# Import any specific watchers here as they're added 