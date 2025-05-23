"""Watchers module for Watchtower."""

# Legacy watchers (backward compatibility)
from src.watchers.base_watcher import BaseWatcher
from src.watchers.ms_skills_watcher import MSAppliedSkillsWatcher

# Enhanced watchers (new architecture)
from src.watchers.enhanced_watcher import (
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