"""Search Utilities for Dashboard Tabs
Reusable search functionality for all dashboard components
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def filter_duplicates(content: list[dict[str, Any]], show_duplicates: bool = False) -> list[dict[str, Any]]:
    """Filter out duplicate content items (Story 4.1: Content Deduplication Engine).

    Args:
        content: List of content items (dictionaries)
        show_duplicates: Whether to show duplicate items or filter them out

    Returns:
        Content with duplicates filtered out (unless show_duplicates=True)
    """
    if show_duplicates or not content:
        return content

    # Filter out items marked as duplicates
    filtered_content = [item for item in content if not item.get("is_duplicate", False)]

    logger.info(f"Filtered {len(content) - len(filtered_content)} duplicates from {len(content)} items")
    return filtered_content


def highlight_matches(text: str, query: str) -> str:
    """Highlight matching terms in text using HTML <mark> tags.

    Args:
        text: Text to highlight
        query: Search query string

    Returns:
        Text with highlighted matches
    """
    if not query or not text:
        return text

    try:
        # Escape HTML special characters first
        escaped_text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Create regex pattern for case-insensitive matching
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        # Use <mark> tags for highlighting
        highlighted = pattern.sub(f"<mark>{query}</mark>", escaped_text)

        return highlighted
    except Exception as e:
        logger.warning(f"Error highlighting matches: {e}")
        return str(text)


def filter_content(
    search_query: str,
    content: list[dict[str, Any]],
    searchable_fields: list[str] = None,
) -> list[dict[str, Any]]:
    """Filter content based on search query using case-insensitive substring matching.

    Args:
        search_query: Search query string
        content: List of content items (dictionaries)
        searchable_fields: List of fields to search in (default: common fields)

    Returns:
        Filtered content with highlighted matches
    """
    if not search_query or not content:
        return content

    # Default searchable fields if not specified
    if searchable_fields is None:
        searchable_fields = [
            "title",
            "description",
            "summary",
            "content",
            "source",
            "name",
            "channel",
        ]

    query_lower = search_query.lower()
    filtered_content = []

    for item in content:
        # Build searchable text from specified fields
        searchable_text_parts = []

        for field in searchable_fields:
            field_value = item.get(field, "")
            if field_value:
                searchable_text_parts.append(str(field_value))

        searchable_text = " ".join(searchable_text_parts).lower()

        # Check if query matches any part of searchable text
        if query_lower in searchable_text:
            # Create a copy with highlighted fields
            item_copy = item.copy()

            # Highlight matching fields
            for field in searchable_fields:
                if item_copy.get(field):
                    item_copy[field] = highlight_matches(str(item_copy[field]), search_query)

            filtered_content.append(item_copy)

    return filtered_content


def create_search_input(input_id: str, placeholder: str = "Search...", clear_button: bool = True):
    """Create a search input component with Bootstrap styling.

    Args:
        input_id: Dash component ID
        placeholder: Placeholder text
        clear_button: Whether to include a clear button

    Returns:
        Dash Bootstrap Components input group
    """
    import dash_bootstrap_components as dbc
    from dash import html

    input_component = dbc.Input(
        id=input_id,
        placeholder=placeholder,
        type="text",
        className="mb-3",
    )

    if clear_button:
        return dbc.InputGroup(
            [
                input_component,
                dbc.InputGroupText(
                    html.I(className="fas fa-times"),
                    id=f"{input_id}-clear",
                    style={"cursor": "pointer"},
                ),
            ],
            className="mb-3",
        )

    return input_component


def get_common_searchable_fields(content_type: str) -> list[str]:
    """Get commonly searchable fields for different content types.

    Args:
        content_type: Type of content (videos, news, deals, papers, etc.)

    Returns:
        List of field names to search in
    """
    field_mappings = {
        "videos": ["title", "description", "channel", "published_at"],
        "news": ["title", "description", "source", "summary", "source_display_name"],
        "deals": ["title", "description", "platform", "source_category", "source_name"],
        "papers": [
            "title",
            "summary",
            "authors",
            "categories",
            "primary_category_display",
        ],
        "courses": ["title", "description", "instructor", "category"],
        "arxiv": ["title", "summary", "authors_display", "primary_category_display"],
        "default": ["title", "description", "summary", "content", "source", "name"],
    }

    return field_mappings.get(content_type, field_mappings["default"])


def validate_search_performance(content_size: int, max_items: int = 10000) -> bool:
    """Validate that search performance will meet requirements.

    Args:
        content_size: Number of items to search through
        max_items: Maximum recommended items for client-side search

    Returns:
        True if performance is acceptable
    """
    if content_size > max_items:
        logger.warning(f"Search performance may be slow with {content_size} items (recommended: <{max_items})")
        return False
    return True


# Cache for search results to improve performance
_search_cache = {}


def cached_filter_content(
    search_query: str,
    content: list[dict],
    content_hash: str,
    searchable_fields: list[str] = None,
) -> list[dict]:
    """Cached version of filter_content for better performance.

    Args:
        search_query: Search query string
        content: List of content items
        content_hash: Hash of the content for cache key
        searchable_fields: List of fields to search in

    Returns:
        Filtered content
    """
    cache_key = f"{search_query}_{content_hash}_{hash(tuple(searchable_fields or []))}"

    if cache_key in _search_cache:
        return _search_cache[cache_key]

    result = filter_content(search_query, content, searchable_fields)

    # Limit cache size to prevent memory issues
    if len(_search_cache) > 100:
        _search_cache.clear()

    _search_cache[cache_key] = result
    return result
