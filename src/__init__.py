"""Watchtower: A comprehensive data collection and monitoring platform.

Main package for the Watchtower application.

A versatile framework for automated data collection, processing, and monitoring
from diverse online sources.
"""

__version__ = "0.1.0"
__author__ = "Watchtower Team"
__email__ = "team@watchtower.dev"

# Export main classes for easier imports
from utils.file_system import ensure_directories, get_project_root
from utils.logging import get_logger
from watchers.base_watcher import BaseWatcher

__all__ = [
    "BaseWatcher",
    "ensure_directories",
    "get_logger",
    "get_project_root",
]
