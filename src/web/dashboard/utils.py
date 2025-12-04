"""Shared utilities for the Dashboard."""

import os
from datetime import datetime, timezone

import pandas as pd


def get_project_root():
    """Get the project root directory from any component file's location.

    Assumes the calling file is in src/web/dashboard/components/
    and needs to go up 4 levels to reach the project root.
    """
    # Get the directory of this utils.py file
    current_file = os.path.abspath(__file__)
    # From src/web/dashboard/utils.py, go up 3 levels to reach project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    return project_root


def get_data_path(*path_parts):
    """Get a path within the data directory.

    Args:
        *path_parts: Path components to join (e.g., 'youtube', 'channel_name')

    Returns:
        str: Absolute path to the data file/directory
    """
    return os.path.join(get_project_root(), "data", *path_parts)


def file_exists(filepath):
    """Check if a file exists and is a file (not a directory)."""
    return os.path.isfile(filepath)


def dir_exists(dirpath):
    """Check if a directory exists and is a directory."""
    return os.path.isdir(dirpath)


def parse_date_universal(date_str, component_name="Unknown"):
    """Universal date parsing function for all dashboard components.

    Args:
        date_str: Date string to parse
        component_name: Name of the component calling this (for logging)

    Returns:
        datetime: Parsed datetime object in UTC, or None if parsing fails
    """
    if pd.isna(date_str) or not date_str or str(date_str).strip() in ("", "N/A", "null", "None", "undefined"):
        return None

    date_str = str(date_str).strip()

    # Try ISO format first
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    # Extended list of common formats including problematic ones from logs
    common_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%d %B %Y %H:%M:%S %Z",
        "%d %B %Y %H:%M:%S %z",
        "%m.%d.%y",
        "%m/%d/%Y",
        "%m/%d/%y",  # Handle formats like "6.14.25"
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%m-%d-%Y",
        # AWS/RSS formats
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S +0000",
        # Additional formats found in logs
        "%d %b %Y %H:%M:%S +0000",
        "%d %b %Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m-%d-%y",
    ]

    for fmt in common_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Try timestamp conversion
    try:
        ts = float(date_str)
        if ts > 10000000000:
            ts /= 1000  # Convert milliseconds to seconds
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError:
        pass

    # Only show debug message for non-trivial date strings to reduce noise
    if len(date_str) > 3 and date_str not in ("N/A", "null", "None", "undefined"):
        print(f"Debug ({component_name}): Could not parse date: '{date_str[:50]}{'...' if len(date_str) > 50 else ''}'")
    return None


def log_missing_file(file_path, component_name, is_optional=True):
    """Log missing file warnings in a consistent, less noisy way.

    Args:
        file_path: Path to the missing file
        component_name: Name of the component
        is_optional: Whether the file is optional (True) or critical (False)
    """
    filename = os.path.basename(file_path)
    log_level = "Info" if is_optional else "Warning"
    status = "Optional data not available" if is_optional else "Required data missing"
    print(f"{log_level} ({component_name}): {status} - {filename}")

    # Only show full path in debug mode or for critical files
    if not is_optional:
        print(f"  Full path: {file_path}")


def handle_data_loading_error(e, component_name, file_path):
    """Handle data loading errors in a consistent way.

    Args:
        e: Exception that occurred
        component_name: Name of the component
        file_path: Path to the file that failed to load
    """
    filename = os.path.basename(file_path)
    print(f"Error ({component_name}): Failed to load {filename} - {str(e)[:100]}")
    # Only show full path and traceback for unexpected errors
    if "FileNotFoundError" not in str(type(e)):
        print(f"  Full path: {file_path}")
        print(f"  Error type: {type(e).__name__}")
