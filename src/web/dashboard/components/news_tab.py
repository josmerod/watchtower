import json
import logging

# Import shared utilities
import sys
from datetime import datetime, timezone
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, html

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.web.dashboard.components.recommendations_tab import recommendations_manager
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
    get_common_searchable_fields,
)
from src.web.dashboard.utils import get_data_path, parse_date_universal

# Configure logging
logger = logging.getLogger(__name__)

# --- Data Loading ---

# NEWS TAB - Actual news sites and aggregators
NEWS_SOURCES_CONFIG = {
    "techcrunch": {
        "path": get_data_path("news", "techcrunch_latest.json"),
        "name": "TechCrunch",
    },
    "venturebeat": {
        "path": get_data_path("news", "venturebeat_latest.json"),
        "name": "VentureBeat",
    },
    "freecodecamp": {
        "path": get_data_path("news", "freecodecamp_latest.json"),
        "name": "freeCodeCamp",
    },
    "google_ai_blog": {
        "path": get_data_path("news", "google_ai_blog_latest.json"),
        "name": "Google AI Blog",
    },
    "lobsters": {
        "path": get_data_path("news", "lobsters_latest.json"),
        "name": "Lobsters",
    },
    "arstechnica": {
        "path": get_data_path("news", "arstechnica_latest.json"),
        "name": "Ars Technica",
    },
    # Added from Knowledge Garden
    "futuretools": {
        "path": get_data_path("futuretools", "futuretoolsnews.json"),
        "name": "FutureTools",
    },
    "bensbites": {
        "path": get_data_path("bensbites", "bensbites_news.json"),
        "name": "Ben's Bites",
    },
    "hackernews": {
        "path": get_data_path("hackernews", "hackernews.json"),
        "name": "Hacker News",
    },
    "medium_genai": {
        "path": get_data_path("medium_genai", "medium_genai.json"),
        "name": "Medium GenAI",
    },
    "kdnuggets": {
        "path": get_data_path("kdnuggets", "kdnuggets.json"),
        "name": "KDnuggets",
    },
    "meneame_general": {
        "path": get_data_path("meneame", "meneame_general_latest.json"),
        "name": "Meneame General",
    },
    "meneame_tecnologia": {
        "path": get_data_path("meneame", "meneame_tecnologia_latest.json"),
        "name": "Meneame Tech",
    },
    "indiehackers": {
        "path": get_data_path("indie_hackers", "posts.json"),
        "name": "Indie Hackers",
    },
    # Kagi RSS sources by category
    "kagi_world": {
        "path": get_data_path("kagi_world", "kagi_world.json"),
        "name": "Kagi World",
    },
    "kagi_usa": {
        "path": get_data_path("kagi_usa", "kagi_usa.json"),
        "name": "Kagi USA",
    },
    "kagi_business": {
        "path": get_data_path("kagi_business", "kagi_business.json"),
        "name": "Kagi Business",
    },
    "kagi_science": {
        "path": get_data_path("kagi_science", "kagi_science.json"),
        "name": "Kagi Science",
    },
    "kagi_gaming": {
        "path": get_data_path("kagi_gaming", "kagi_gaming.json"),
        "name": "Kagi Gaming",
    },
    "kagi_ai": {"path": get_data_path("kagi_ai", "kagi_ai.json"), "name": "Kagi AI"},
    "kagi_europe": {
        "path": get_data_path("kagi_europe", "kagi_europe.json"),
        "name": "Kagi Europe",
    },
    "kagi_spain": {
        "path": get_data_path("kagi_spain", "kagi_spain.json"),
        "name": "Kagi Spain",
    },
}


def load_news_from_file(file_path):
    """Loads news items from a JSON file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            # Ensure data is a list of records
            if isinstance(data, dict):  # Handle cases where JSON might be a dict with a key containing the list
                if "articles" in data and isinstance(data["articles"], list):
                    return data["articles"]
                elif "items" in data and isinstance(data["items"], list):
                    return data["items"]
                # Add more checks if other common patterns are found
                else:  # If it's a dictionary but not a recognized pattern, wrap it in a list if it looks like a single item
                    if all(k in data for k in ["title", "url"]):  # Heuristic for a single item
                        return [data]
                    print(f"Warning: Data in {file_path} is a dict but not a recognized list structure. Returning empty.")
                    return []
            elif isinstance(data, list):
                return data
            else:
                print(f"Warning: Data in {file_path} is not a list or recognized dict structure. Type: {type(data)}. Returning empty.")
                return []
    except FileNotFoundError:
        print(f"Warning: News file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {file_path}")
        return []
    except Exception as e:
        print(f"Error loading news from {file_path}: {e}")
        return []


# Load news data dynamically instead of at import time
def get_all_news_data():
    """Load fresh news data from all configured sources."""
    # Simple TTL cache to avoid re-reading dozens of files on each tab switch
    # Cache in module state for ~60 seconds
    import time

    global _NEWS_CACHE  # type: ignore
    now = time.time()
    try:
        if _NEWS_CACHE and now - _NEWS_CACHE.get("ts", 0) < 60:
            return _NEWS_CACHE["data"]
    except NameError:
        pass

    data = {source_key: load_news_from_file(config["path"]) for source_key, config in NEWS_SOURCES_CONFIG.items()}
    _NEWS_CACHE = {"ts": now, "data": data}
    return data


# --- Helper function to parse dates ---
def parse_date(date_str):
    if date_str is None or str(date_str).strip() == "":
        return None

    s_date = str(date_str)

    # List of datetime formats to try for string parsing
    # Ordered from more specific/complex to more general
    datetime_formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO 8601 with microseconds and timezone
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 without microseconds, with timezone
        "%Y-%m-%d %H:%M:%S%z",  # Common format with timezone
        "%Y-%m-%dT%H:%M:%S",  # ISO 8601, no timezone (assumed UTC later)
        "%Y-%m-%d %H:%M:%S",  # Common format, no timezone (assumed UTC later)
        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822/1123 (e.g., "Mon, 01 Jan 2024 12:00:00 GMT")
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 822/1123 with numeric timezone
        "%Y-%m-%d",  # Date only
        "%m/%d/%Y %I:%M:%S %p",  # e.g., 01/20/2024 10:00:00 AM
        "%d/%m/%Y %H:%M:%S",  # e.g., 20/01/2024 10:00:00
    ]

    # Attempt 1: ISO 8601 format (handles 'Z' correctly if present, or timezone offsets)
    # fromisoformat is quite flexible for true ISO strings.
    try:
        # Ensure 'Z' is converted to +00:00 for fromisoformat
        dt = datetime.fromisoformat(s_date.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass  # Continue to other formats

    # Attempt 2: Try common string formats using strptime
    for fmt in datetime_formats:
        try:
            dt = datetime.strptime(s_date, fmt)
            # If parsing succeeds but dt is naive, assume UTC. If tz-aware, convert to UTC.
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue  # Try next format

    # Attempt 3: Epoch timestamp (integer or float string)
    # Check if it's likely an epoch timestamp (e.g. all digits, possibly with a decimal point)
    # Common epoch lengths are 10 (seconds) or 13 (milliseconds) or more with fractions.
    if s_date.replace(".", "", 1).isdigit() and len(s_date) >= 10:
        try:
            timestamp = float(s_date)
            # Heuristic: if timestamp is very large (e.g. > 3e9), it might be milliseconds
            if timestamp > 3 * (10**9):  # Roughly year 2065 in seconds
                timestamp /= 1000.0
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError):
            pass  # Not a valid float or timestamp

    # Use the shared date parsing function as fallback
    return parse_date_universal(s_date, "News")


# --- Layout Generation ---

MAX_ARTICLES_PER_SOURCE = 50  # Limit number of articles displayed per source initially


def format_article_date(article):
    """Extracts and parses date from an article, returns formatted string or 'Date N/A'."""
    # Common date fields in order of preference
    date_fields = [
        "published_at",
        "published",
        "published_date",
        "created_at",
        "updated_at",
        "updated",
        "time",
        "pubDate",
    ]
    date_str = None
    for field in date_fields:
        date_str = article.get(field)
        if date_str:
            break

    parsed_dt = parse_date(date_str)
    return parsed_dt.strftime("%Y-%m-%d %H:%M UTC") if parsed_dt else "Date N/A"


# Removed create_article_card function as it's no longer needed for table view


def create_news_source_tab_content(source_keys, combined_name=None):
    """Creates the content for a news tab as a table with search functionality, potentially combining multiple sources.

    Sorts articles by date before limiting.
    """
    all_articles_for_tab = []
    if isinstance(source_keys, str):  # Single source key
        source_keys = [source_keys]
        source_display_name = NEWS_SOURCES_CONFIG[source_keys[0]]["name"]
        tab_search_id = f"news-search-{source_keys[0]}"
    else:  # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined News"
        tab_search_id = f"news-search-{'-'.join(source_keys)}"

    # Load fresh data each time
    all_news_data = get_all_news_data()

    for key in source_keys:
        articles_from_source = all_news_data.get(key, [])
        # Add source name to each article for display in the table
        for article in articles_from_source:
            # Use 'source_display' to ensure we have a consistent field for the table
            article["source_display_name"] = article.get("source", NEWS_SOURCES_CONFIG[key]["name"])
        all_articles_for_tab.extend(articles_from_source)

    # Sort all articles by date (descending)
    def get_sortable_date(article):
        date_str = (
            article.get("published_at") or article.get("published_date") or article.get("created_at") or article.get("updated_at") or article.get("updated") or article.get("time") or article.get("pubDate")
        )
        parsed = parse_date(date_str)
        return parsed if parsed else datetime.min.replace(tzinfo=timezone.utc)

    all_articles_for_tab.sort(key=get_sortable_date, reverse=True)

    # Store all articles in a hidden div for search filtering
    articles_data = html.Div(
        all_articles_for_tab[:MAX_ARTICLES_PER_SOURCE],
        id=f"{tab_search_id}-data",
        style={"display": "none"},
    )

    if not all_articles_for_tab:
        return dbc.Alert(f"No news items available for {source_display_name}.", color="info")

    # Create table header
    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Source"),
                    html.Th("Date"),
                    html.Th("Actions"),
                ]
            )
        )
    ]

    # Load trend data
    from src.web.dashboard.trend_utils import (
        get_trending_items_map,
        is_item_trending,
        render_trend_badge,
    )

    trending_map = get_trending_items_map()

    # Create table body with robust field fallbacks for heterogeneous sources
    table_body_rows = []
    for i, article in enumerate(all_articles_for_tab[:MAX_ARTICLES_PER_SOURCE]):
        # Check trend status
        is_trending = is_item_trending(article, trending_map)
        trend_badge = render_trend_badge(trending_map.get(f"category:{article.get('source')}") or trending_map.get(article.get("id"))) if is_trending else None

        # Title fallbacks: common across Product Hunt/GitHub Trends/others
        title = article.get("title") or article.get("name") or article.get("full_name") or "No Title"
        # URL fallbacks
        url = article.get("url") or article.get("link") or article.get("html_url") or article.get("website")
        # Use the 'source_display_name' we added earlier
        source_for_display = article.get("source_display_name", source_display_name)
        date_display = format_article_date(article)

        # Add trending class for filtering
        row_class = "trending-item" if is_trending else ""

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.A(title, href=url, target="_blank") if url else title,
                            trend_badge,
                        ]
                    ),
                    html.Td(source_for_display),
                    html.Td(date_display),
                    html.Td(
                        dbc.Button(
                            "Related",
                            id={
                                "type": "related-btn",
                                "tab_id": tab_search_id,
                                "index": i,
                            },
                            color="link",
                            size="sm",
                            className="p-0 text-decoration-none",
                        )
                    ),
                    # Hidden cell for trend filtering
                    html.Td(
                        str(is_trending).lower(),
                        style={"display": "none"},
                        className="is-trending-data",
                    ),
                ],
                className=row_class,
            )
        )

    table_body = [html.Tbody(table_body_rows)]

    # Combine header and body into a dbc.Table
    table = dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,  # Makes table scroll horizontally on small screens
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mb-0",  # Remove default bottom margin if wrapped in Div with padding
    )

    from src.web.dashboard.components.trend_filter import render_trend_filter

    # Return search input and table container
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        # Search input
                        create_search_input(
                            input_id=tab_search_id,
                            placeholder=f"Search {source_display_name}...",
                            clear_button=True,
                        ),
                        width=True,
                    ),
                    dbc.Col(
                        render_trend_filter(f"{tab_search_id}-trend-filter"),
                        width="auto",
                    ),
                ],
                className="mb-3 align-items-center",
            ),
            # Hidden data storage for search filtering
            articles_data,
            # Container for filtered results
            html.Div(
                table,
                id=f"{tab_search_id}-results",
                style={
                    "maxHeight": "800px",
                    "overflowY": "auto",
                    "paddingRight": "15px",
                },
            ),
            # Modal for related content
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Related Content")),
                    dbc.ModalBody(id=f"{tab_search_id}-related-content"),
                    dbc.ModalFooter(
                        dbc.Button(
                            "Close",
                            id=f"{tab_search_id}-related-close",
                            className="ms-auto",
                            n_clicks=0,
                        )
                    ),
                ],
                id=f"{tab_search_id}-related-modal",
                size="lg",
                is_open=False,
            ),
        ]
    )


def register_news_search_callbacks(app):
    """Register search callbacks for all news tabs."""
    # Get all unique search IDs from the tab definitions
    search_ids = [
        "news-search-techcrunch",
        "news-search-venturebeat",
        "news-search-freecodecamp",
        "news-search-google_ai_blog",
        "news-search-lobsters",
        "news-search-arstechnica",
        "news-search-futuretools-bensbites",
        "news-search-hackernews",
        "news-search-medium_genai",
        "news-search-kdnuggets",
        "news-search-meneame_general",
        "news-search-meneame_tecnologia",
        "news-search-indiehackers",
        "news-search-kagi_world",
        "news-search-kagi_usa",
        "news-search-kagi_business",
        "news-search-kagi_science",
        "news-search-kagi_gaming",
        "news-search-kagi_ai",
        "news-search-kagi_europe",
        "news-search-kagi_spain",
    ]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value"), Input(f"{search_id}-trend-filter", "value")],
            State(f"{search_id}-data", "children"),
            prevent_initial_call=True,
        )
        def update_news_search(search_term, show_trending, articles_data, current_search_id=search_id):
            """Update news display based on search term and trend filter."""
            try:
                # Convert articles data back to list if needed
                if articles_data is None:
                    return html.Div("No data available")

                # Get searchable fields for news content
                searchable_fields = get_common_searchable_fields("news")

                # Filter articles based on search term
                filtered_articles = filter_content(search_term, articles_data, searchable_fields)

                # Filter by trending if enabled
                if show_trending:
                    # We need to re-check trending status or use the hidden data
                    # Since we don't have the hidden data easily accessible here without parsing HTML,
                    # we'll re-use the utility. Ideally, we should store this in the data store.
                    from src.web.dashboard.trend_utils import (
                        get_trending_items_map,
                        is_item_trending,
                    )

                    trending_map = get_trending_items_map()
                    filtered_articles = [a for a in filtered_articles if is_item_trending(a, trending_map)]

                if not filtered_articles:
                    msg = f"No articles found matching '{search_term}'" if search_term else "No articles found"
                    if show_trending:
                        msg += " (filtered by trending)"
                    return dbc.Alert(msg, color="info")

                # Create table for filtered results
                table_header = [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Title"),
                                html.Th("Source"),
                                html.Th("Date"),
                                html.Th("Actions"),
                            ]
                        )
                    )
                ]

                # Load trend data for rendering badges
                from src.web.dashboard.trend_utils import (
                    get_trending_items_map,
                    is_item_trending,
                    render_trend_badge,
                )

                trending_map = get_trending_items_map()

                table_body_rows = []
                for i, article in enumerate(filtered_articles):
                    # Check trend status
                    is_trending = is_item_trending(article, trending_map)
                    trend_badge = render_trend_badge(trending_map.get(f"category:{article.get('source')}") or trending_map.get(article.get("id"))) if is_trending else None

                    # Title fallbacks: common across news sources
                    title = article.get("title") or article.get("name") or article.get("full_name") or "No Title"
                    # URL fallbacks
                    url = article.get("url") or article.get("link") or article.get("html_url") or article.get("website")
                    # Use the 'source_display_name' if available
                    source_for_display = article.get("source_display_name", "Unknown")
                    date_display = format_article_date(article)

                    # Add trending class
                    row_class = "trending-item" if is_trending else ""

                    table_body_rows.append(
                        html.Tr(
                            [
                                html.Td(
                                    [
                                        (html.A(title, href=url, target="_blank") if url else title),
                                        trend_badge,
                                    ]
                                ),
                                html.Td(source_for_display),
                                html.Td(date_display),
                                html.Td(
                                    dbc.Button(
                                        "Related",
                                        id={
                                            "type": "related-btn",
                                            "tab_id": current_search_id,
                                            "index": i,
                                        },
                                        color="link",
                                        size="sm",
                                        className="p-0 text-decoration-none",
                                    )
                                ),
                            ],
                            className=row_class,
                        )
                    )

                table_body = [html.Tbody(table_body_rows)]

                # Combine header and body into a dbc.Table
                table = dbc.Table(
                    table_header + table_body,
                    bordered=True,
                    hover=True,
                    responsive=True,
                    striped=True,
                    size="sm",
                    color="dark",
                    className="table-responsive mb-0",
                )

                return html.Div(
                    [
                        dbc.Alert(
                            f"📰 Found {len(filtered_articles)} articles matching '{search_term}'" + (" (Trending)" if show_trending else ""),
                            color="success",
                            className="mb-3",
                        ),
                        table,
                    ],
                    style={
                        "maxHeight": "800px",
                        "overflowY": "auto",
                        "paddingRight": "15px",
                    },
                )

            except Exception as e:
                logger.error(f"Error in news search callback for {current_search_id}: {e}")
                return dbc.Alert(f"Error searching articles: {e}", color="danger")

        # Clear search callback
        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_news_search(n_clicks):
            """Clear search input."""
            if n_clicks:
                return ""
            return dash.no_update

        # Callback for related content modal
        @app.callback(
            [
                Output(f"{search_id}-related-modal", "is_open"),
                Output(f"{search_id}-related-content", "children"),
            ],
            [
                Input(
                    {"type": "related-btn", "tab_id": search_id, "index": ALL},
                    "n_clicks",
                ),
                Input(f"{search_id}-related-close", "n_clicks"),
            ],
            [
                State(f"{search_id}-related-modal", "is_open"),
                State(f"{search_id}-data", "children"),
            ],
            prevent_initial_call=True,
        )
        def toggle_related_modal(n_clicks_related, n_clicks_close, is_open, articles_data):
            ctx = dash.callback_context
            if not ctx.triggered:
                return is_open, dash.no_update

            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

            if "related-close" in trigger_id:
                return False, dash.no_update

            if "related-btn" in trigger_id:
                # Extract index from trigger_id which is a JSON string
                try:
                    # Get the item index directly from the structured ID
                    list_index = ctx.triggered_id["index"]

                    if isinstance(articles_data, list) and 0 <= list_index < len(articles_data):
                        target_article = articles_data[list_index]
                    else:
                        logger.warning(f"Invalid article index: {list_index}")
                        target_article = None

                    if target_article:
                        title = target_article.get("title")
                        content_type = target_article.get("type", "news_article")  # Default to news_article

                        related_items = recommendations_manager.recommendation_engine.get_related_content(title, content_type)

                        if not related_items:
                            return True, html.P("No related content found.")

                        # Render related items
                        items_list = []
                        for item in related_items:
                            items_list.append(
                                dbc.ListGroupItem(
                                    [
                                        html.Div(
                                            [
                                                html.H6(item.get("title"), className="mb-1"),
                                                html.Small(
                                                    f"Similarity: {item.get('similarity_score', 0):.2f}",
                                                    className="text-muted",
                                                ),
                                            ],
                                            className="d-flex w-100 justify-content-between",
                                        ),
                                        html.P(
                                            item.get("description", ""),
                                            className="mb-1",
                                        ),
                                        html.Small(
                                            html.A(
                                                "Read more",
                                                href=item.get("url", "#"),
                                                target="_blank",
                                            )
                                        ),
                                    ]
                                )
                            )

                        return True, dbc.ListGroup(items_list)

                    return True, html.P("Article details not found.")

                except Exception as e:
                    logger.error(f"Error in related content callback: {e}")
                    return True, html.P(f"Error loading related content: {e}")

            return is_open, dash.no_update


# Main function to render the news tab
def render_news_tab():
    """Render the complete news tab with all sub-tabs."""
    tab_definitions = [
        {"label": "TechCrunch", "keys": "techcrunch", "id": "tc"},
        {"label": "VentureBeat", "keys": "venturebeat", "id": "vb"},
        {"label": "freeCodeCamp", "keys": "freecodecamp", "id": "fcc"},
        {"label": "Google AI Blog", "keys": "google_ai_blog", "id": "gaib"},
        {"label": "Lobsters", "keys": "lobsters", "id": "lobsters"},
        {"label": "Ars Technica", "keys": "arstechnica", "id": "ars"},
        {
            "label": "FutureTools & Ben's Bites",
            "keys": ["futuretools", "bensbites"],
            "id": "ft-bb",
        },
        {"label": "Hacker News", "keys": "hackernews", "id": "hn"},
        {"label": "Medium GenAI", "keys": "medium_genai", "id": "med_genai"},
        {"label": "KDnuggets", "keys": "kdnuggets", "id": "kdn"},
        {"label": "Meneame General", "keys": "meneame_general", "id": "men_gen"},
        {"label": "Meneame Tech", "keys": "meneame_tecnologia", "id": "men_tec"},
        {"label": "Indie Hackers", "keys": "indiehackers", "id": "ih"},
        # Kagi RSS feeds as individual tabs
        {"label": "Kagi World", "keys": "kagi_world", "id": "kagi_world"},
        {"label": "Kagi USA", "keys": "kagi_usa", "id": "kagi_usa"},
        {"label": "Kagi Business", "keys": "kagi_business", "id": "kagi_business"},
        {"label": "Kagi Science", "keys": "kagi_science", "id": "kagi_science"},
        {"label": "Kagi Gaming", "keys": "kagi_gaming", "id": "kagi_gaming"},
        {"label": "Kagi AI", "keys": "kagi_ai", "id": "kagi_ai"},
        {"label": "Kagi Europe", "keys": "kagi_europe", "id": "kagi_europe"},
        {"label": "Kagi Spain", "keys": "kagi_spain", "id": "kagi_spain"},
    ]

    tabs_children = []
    for tab_def in tab_definitions:
        tab_id = f"news-tab-{tab_def['id']}"
        content = create_news_source_tab_content(tab_def["keys"], combined_name=tab_def["label"])
        tabs_children.append(
            dbc.Tab(
                label=tab_def["label"],
                tab_id=tab_id,
                children=content,
                id=tab_id + "-container",
            )  # Added id to tab for potential future targeting
        )

    return html.Div(
        [
            html.H3("News Feed", className="mb-3"),
            dbc.Tabs(
                id="news-source-tabs-main",
                children=tabs_children,
                active_tab="news-tab-ft-bb",
            ),  # Default active tab
        ]
    )


if __name__ == "__main__":
    # For testing this component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # The render_news_tab now produces the full tabbed layout
    app_test.layout = dbc.Container(
        [
            html.H1("News Tab Test (Standalone)"),
            render_news_tab(),  # This will include the tabs and initial content
        ],
        fluid=True,
        className="py-4",
    )

    print("Running standalone test for news_tab.py...")
    print(f"Displaying max {MAX_ARTICLES_PER_SOURCE} articles per tab, sorted by date.")
    print("Expected news JSON files relative to project root, e.g., data/futuretools/futuretoolsnews.json")
    print("Check console for warnings about missing files or parsing errors, especially date parsing.")
    app_test.run(debug=True, port=8052)
