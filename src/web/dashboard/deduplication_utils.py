"""Deduplication utilities for dashboard components.

Provides functions to filter and display duplicate content in the dashboard.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def filter_duplicates(data: list[dict[str, Any]], show_duplicates: bool = False) -> list[dict[str, Any]]:
    """Filter duplicate items from dashboard data.

    Args:
        data: List of data items to filter.
        show_duplicates: If True, include duplicate items. If False, only show unique items.

    Returns:
        Filtered list of data items.
    """
    if not data:
        return data

    if show_duplicates:
        # Return all items (unique + duplicates)
        return data
    else:
        # Filter out duplicate items (is_duplicate = True)
        filtered_data = []
        duplicate_count = 0

        for item in data:
            is_duplicate = item.get("is_duplicate", False)
            if not is_duplicate:
                filtered_data.append(item)
            else:
                duplicate_count += 1

        logger.debug(f"Filtered {duplicate_count} duplicates from {len(data)} items")
        return filtered_data


def get_duplicate_groups(data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group items by duplicate_group_id.

    Args:
        data: List of data items to group.

    Returns:
        Dictionary mapping group_id to list of items in that group.
    """
    groups = {}

    for item in data:
        group_id = item.get("duplicate_group_id")
        if group_id:
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(item)

    return groups


def get_duplicate_summary(data: list[dict[str, Any]]) -> dict[str, int]:
    """Get summary statistics about duplicates in the data.

    Args:
        data: List of data items to analyze.

    Returns:
        Dictionary with duplicate statistics.
    """
    total_items = len(data)
    duplicate_items = [item for item in data if item.get("is_duplicate", False)]
    duplicate_count = len(duplicate_items)
    unique_items = total_items - duplicate_count

    # Count duplicate groups
    duplicate_groups = set()
    for item in duplicate_items:
        group_id = item.get("duplicate_group_id")
        if group_id:
            duplicate_groups.add(group_id)

    return {
        "total_items": total_items,
        "unique_items": unique_items,
        "duplicate_items": duplicate_count,
        "duplicate_groups": len(duplicate_groups),
    }


def create_show_duplicates_button(
    button_id: str,
    data: list[dict[str, Any]],
    current_show_duplicates: bool = False,
    button_text: str | None = None,
) -> Any:
    """Create a button to show/hide duplicates.

    Args:
        button_id: ID for the button component.
        data: Data to analyze for duplicate statistics.
        current_show_duplicates: Current state of show duplicates toggle.
        button_text: Custom button text (auto-generated if not provided).

    Returns:
        Dash button component.
    """
    import dash_bootstrap_components as dbc

    summary = get_duplicate_summary(data)

    if button_text is None:
        if current_show_duplicates:
            button_text = f"Hide {summary['duplicate_items']} duplicates"
        else:
            if summary["duplicate_items"] > 0:
                button_text = f"Show {summary['duplicate_items']} duplicates"
            else:
                button_text = "No duplicates found"

    # Disable button if no duplicates exist
    disabled = summary["duplicate_items"] == 0

    button = dbc.Button(
        button_text,
        id=button_id,
        color="outline-secondary" if not current_show_duplicates else "secondary",
        size="sm",
        disabled=disabled,
        className="mb-3",
    )

    return button


def load_and_filter_data(file_path: str, show_duplicates: bool = False, max_items: int | None = None) -> list[dict[str, Any]]:
    """Load data from file and apply duplicate filtering.

    Args:
        file_path: Path to the JSON data file.
        show_duplicates: Whether to include duplicate items.
        max_items: Maximum number of items to return (most recent first).

    Returns:
        Filtered list of data items.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle single object case
        if isinstance(data, dict):
            data = [data]

        # Filter duplicates
        filtered_data = filter_duplicates(data, show_duplicates)

        # Sort by created_at if available (most recent first)
        filtered_data.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Apply max_items limit if specified
        if max_items:
            filtered_data = filtered_data[:max_items]

        return filtered_data

    except FileNotFoundError:
        logger.warning(f"Data file not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {e}")
        return []


def enhance_item_with_duplicate_info(item: dict[str, Any]) -> dict[str, Any]:
    """Add duplicate-related information to an item for display.

    Args:
        item: Original data item.

    Returns:
        Enhanced item with duplicate display information.
    """
    enhanced = item.copy()

    # Add duplicate status badge info
    if enhanced.get("is_duplicate", False):
        enhanced["duplicate_badge"] = "Duplicate"
        enhanced["duplicate_color"] = "warning"
    else:
        enhanced["duplicate_badge"] = "Original"
        enhanced["duplicate_color"] = "success"

    # Add quality score display
    quality_score = enhanced.get("quality_score")
    if quality_score is not None:
        enhanced["quality_display"] = f"Quality: {quality_score:.1f}/100"

    return enhanced
