"""Watchtower: A comprehensive data collection and monitoring platform.

Main package for the Watchtower application.

A versatile framework for automated data collection, processing, and monitoring
from diverse online sources.
"""

__version__ = "0.1.0"
__author__ = "Watchtower Team"
__email__ = "team@watchtower.dev"

# Export main classes for easier imports
# Temporarily comment out problematic imports for UV testing
# from src.watchers.base_watcher import BaseWatcher
# from src.utils.logging import get_logger
# from src.utils.file_system import ensure_directories, get_project_root

__all__ = [
    # "BaseWatcher",
    # "get_logger", 
    # "ensure_directories",
    # "get_project_root",
] 