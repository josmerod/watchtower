"""Deduplication utilities for dashboard components.

Provides functions to filter and display duplicate content in the dashboard.
"""

import hashlib
import json
import logging
import re
from collections.abc import Callable
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


def normalize_story_key(text: str) -> str:
    """Normalize a title into a story-matching key.

    Lowercases, replaces non-alphanumeric runs with single spaces and trims,
    so "OpenAI launches GPT-5!" and "openai launches gpt 5" collapse to the
    same key (cross-source duplicates usually differ in punctuation/casing
    but share the headline).

    Args:
        text: Raw title text.

    Returns:
        Normalized key (empty string for blank input).
    """
    return " ".join(re.sub(r"[^0-9a-záéíóúüñçäößàèìòùâêîôûåøæ]+", " ", text.lower()).split())


def get_story_group_key(item: dict[str, Any]) -> str | None:
    """Derive the duplicate-group key for an item from its title fields.

    Falls back through the common title field names (title/name/full_name);
    items without any title get no key and are never grouped.

    Args:
        item: Data item to key.

    Returns:
        Normalized story key, or None if the item has no title.
    """
    title = item.get("title") or item.get("name") or item.get("full_name")
    if not title:
        return None
    return normalize_story_key(str(title))


def annotate_duplicate_groups(
    data: list[dict[str, Any]],
    key_func: Callable[[dict[str, Any]], str | None] = get_story_group_key,
) -> list[dict[str, Any]]:
    """Annotate items with ``is_duplicate``/``duplicate_group_id`` flags.

    This is the missing front-end half of the dedup pipeline: raw feed items
    carry no duplicate metadata (the load-time dedup in ``data_loader``
    silently drops exact matches instead), so cross-source duplicates must be
    flagged here before ``filter_duplicates``/``get_duplicate_summary`` can
    act on them. Items are returned as shallow copies — the input list (often
    a cached dataset) is never mutated. The first item of each group in list
    order (callers pass date-descending lists, so the newest) stays the
    original; the rest are flagged as duplicates.

    Args:
        data: Items to annotate, ideally sorted newest-first.
        key_func: Returns the group key for an item (None = never grouped).

    Returns:
        Copies of the items annotated with ``is_duplicate`` and
        ``duplicate_group_id`` (group members only; the original of each
        group gets the id too so ``get_duplicate_groups`` keeps working).
    """
    annotated = [dict(item) for item in data]

    groups: dict[str, list[int]] = {}
    for index, item in enumerate(annotated):
        key = key_func(item)
        if key:
            groups.setdefault(key, []).append(index)

    for key, indexes in groups.items():
        if len(indexes) < 2:
            continue
        group_id = f"grp-{hashlib.md5(key.encode('utf-8')).hexdigest()[:12]}"
        for position, index in enumerate(indexes):
            annotated[index]["duplicate_group_id"] = group_id
            annotated[index]["is_duplicate"] = position > 0

    return annotated


def format_duplicate_summary(summary: dict[str, int]) -> str:
    """Render the duplicate summary as the Spanish one-liner from spec 01 M5.

    Args:
        summary: Statistics dict as returned by ``get_duplicate_summary``.

    Returns:
        e.g. "2 ocultos en 1 grupo", "1 oculto en 1 grupo" or "sin duplicados".
    """
    hidden = summary.get("duplicate_items", 0)
    groups = summary.get("duplicate_groups", 0)
    if hidden <= 0:
        return "sin duplicados"
    hidden_text = f"{hidden} oculto" if hidden == 1 else f"{hidden} ocultos"
    groups_text = f"{groups} grupo" if groups == 1 else f"{groups} grupos"
    return f"{hidden_text} en {groups_text}"


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
