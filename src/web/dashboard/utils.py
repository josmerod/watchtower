"""Shared utilities for the Dashboard."""

import os
from datetime import datetime, timezone

import dash
import pandas as pd


def get_project_root():
    """Get the project root directory from any component file's location.

    Assumes the calling file is in src/web/dashboard/components/
    and needs to go up 4 levels to reach the project root.
    """
    # Get the directory of this utils.py file
    current_file = os.path.abspath(__file__)
    # From src/web/dashboard/utils.py, go up 4 levels to reach project root
    # (dirname: utils.py -> dashboard -> web -> src -> project_root)
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
        "%Y-%b-%d",
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
        # PubMed-style dates (e.g. "2026-May-21", "2026-05-21")
        "%Y-%b-%d",
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


def _is_click(entry: dict) -> bool:
    prop_id = str(entry.get("prop_id", ""))
    value = entry.get("value")
    return prop_id.endswith(".n_clicks") and isinstance(value, int) and not isinstance(value, bool) and value >= 1


def clicked_prop() -> str | None:
    """The ``id.prop`` of the click that set the running callback going, ``None`` when no button was clicked.

    With an ALL input the argument is the list of every button on screen and cannot tell which one changed; the
    click is in ``dash.ctx.triggered``, whose entries carry ``prop_id`` and ``value`` and nothing else. The id that
    clicked is ``dash.ctx.triggered_prop_ids[prop]`` (a dict for pattern ids).
    """
    return next((entry["prop_id"] for entry in dash.ctx.triggered if _is_click(entry)), None)


def only_inserted() -> bool:
    """Whether this call is Dash showing the callback its freshly inserted buttons, none of them clicked.

    A pattern-matching callback runs again, ``prevent_initial_call=True`` or not, when another callback inserts
    its buttons: ``dash.ctx.triggered`` lists each one with ``value=None``. That is not an action, and nothing
    should change on it. Any other prop in the list, or a click, makes it one.
    """
    changed = dash.ctx.triggered
    return not changed or all(entry.get("value") is None and str(entry.get("prop_id", "")).endswith(".n_clicks") for entry in changed)
