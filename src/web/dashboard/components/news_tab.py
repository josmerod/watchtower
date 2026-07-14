import logging

# Import shared utilities
import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, html

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.services.data_loader import (
    CLOUD_UPDATES_SOURCES_CONFIG,
    NEWS_SOURCES_CONFIG,
    VALENCIA_LOCAL_SOURCES_CONFIG,
    get_sortable_date,
    load_data_from_file,
)
from src.services.data_loader import (
    format_article_date as format_article_date_shared,
)

# Merge the extra source configs so the news tab can render them as subtabs
_ALL_NEWS_SOURCES = {
    **NEWS_SOURCES_CONFIG,
    **CLOUD_UPDATES_SOURCES_CONFIG,
    **VALENCIA_LOCAL_SOURCES_CONFIG,
}
from src.web.dashboard.components.recommendations_tab import recommendations_manager
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
    get_common_searchable_fields,
)

# Configure logging
logger = logging.getLogger(__name__)

# --- Data Loading ---

# NEWS TAB - Actual news sites and aggregators
# NEWS_SOURCES_CONFIG imported from data_loader

# load_news_from_file removed (using shared load_data_from_file)


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

    data = {source_key: load_data_from_file(config["path"]) for source_key, config in _ALL_NEWS_SOURCES.items()}
    _NEWS_CACHE = {"ts": now, "data": data}
    return data


# --- Helper function to parse dates ---
# parse_date logic removed (using shared parse_date)


# --- Layout Generation ---

MAX_ARTICLES_PER_SOURCE = 50  # Limit number of articles displayed per source initially


# format_article_date removed (using shared logic)
def format_article_date(article):
    """Wrapper for shared formatting."""
    return format_article_date_shared(article)


# Removed create_article_card function as it's no longer needed for table view


def create_news_source_tab_content(source_keys, combined_name=None):
    """Creates the content for a news tab as a table with search functionality, potentially combining multiple sources.

    Sorts articles by date before limiting.
    """
    all_articles_for_tab = []
    if isinstance(source_keys, str):  # Single source key
        source_keys = [source_keys]
        source_display_name = _ALL_NEWS_SOURCES[source_keys[0]]["name"]
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
            article["source_display_name"] = article.get("source", _ALL_NEWS_SOURCES[key]["name"])
        all_articles_for_tab.extend(articles_from_source)

    # Sort all articles by date (descending)
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
    for _i, article in enumerate(all_articles_for_tab[:MAX_ARTICLES_PER_SOURCE]):
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

    # Return search input and table container
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        # Search input
                        create_search_input(
                            input_id=tab_search_id,
                            placeholder=f"Filter {source_display_name} by term...",
                            clear_button=True,
                        ),
                        width=True,
                    ),
                    # Trend filter button removed
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
        "news-search-techcrunch-venturebeat-arstechnica-kagi_ai",
        "news-search-freecodecamp",
        "news-search-google_ai_blog",
        "news-search-lobsters",
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
        "news-search-kagi_europe",
        "news-search-kagi_spain",
        "news-search-microsiervos",
    ]

    for search_id in search_ids:

        @app.callback(
            Output(f"{search_id}-results", "children"),
            [Input(search_id, "value")],
            State(f"{search_id}-data", "children"),
            # prevent_initial_call=False (default), so it runs on load
        )
        def update_news_search(search_term, _unused_state_data, current_search_id=search_id):
            """Update news display based on search term. Fetches fresh data on execution."""
            try:
                # 1. Determine Source Keys from Search ID
                # Format: news-search-{key} or news-search-{key1}-{key2}
                id_suffix = current_search_id.replace("news-search-", "")
                if id_suffix == "futuretools-bensbites":
                    source_keys = ["futuretools", "bensbites"]
                else:
                    source_keys = id_suffix.split("-")

                # 2. Fetch Fresh Data (CACHE HIT usually, unless cleared)
                all_news_data = get_all_news_data()

                # 3. Aggregate Data for this Tab
                articles_data = []
                for key in source_keys:
                    # Robust key matching (try exact, then maybe underscore/dash swap if needed)
                    # Keys in config use underscores. ID uses dashes?
                    # Let's attempt to access direct key first, then try replace
                    if key in all_news_data:
                        source_articles = all_news_data[key]
                        # Enrich with source display name
                        for art in source_articles:
                            art["source_display_name"] = _ALL_NEWS_SOURCES[key]["name"]
                        articles_data.extend(source_articles)
                    else:
                        # Try swapping dash to underscore just in case
                        alt_key = key.replace("-", "_")
                        if alt_key in all_news_data:
                            source_articles = all_news_data[alt_key]
                            # Enrich with source display name
                            for art in source_articles:
                                art["source_display_name"] = _ALL_NEWS_SOURCES[alt_key]["name"]
                            articles_data.extend(source_articles)

                if not articles_data:
                    return dbc.Alert("No data available (fetch returned empty)", color="warning")

                # 4. Sort
                articles_data.sort(key=get_sortable_date, reverse=True)

                articles_data.sort(key=get_sortable_date, reverse=True)

                # 5. Filter (Search)
                if search_term:
                    searchable_fields = get_common_searchable_fields("news")
                    filtered_articles = filter_content(search_term, articles_data, searchable_fields)
                else:
                    filtered_articles = articles_data[:MAX_ARTICLES_PER_SOURCE]  # Limit initial view

                # Legacy filtering block removed

                # Create table for filtered results
                table_header = [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Title"),
                                html.Th("Source"),
                                html.Th("Date"),
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
                for _i, article in enumerate(filtered_articles):
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

                # Only show alert if a search term is active
                if search_term:
                    alert = dbc.Alert(
                        f"📰 Found {len(filtered_articles)} articles matching '{search_term}'",
                        color="success",
                        className="mb-3",
                    )
                else:
                    alert = None

                return html.Div(
                    [
                        alert,
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
        {
            "label": "Top Tech",
            "keys": ["techcrunch", "venturebeat", "arstechnica", "kagi_ai"],
            "id": "top_tech",
        },
        {"label": "freeCodeCamp", "keys": "freecodecamp", "id": "fcc"},
        {"label": "Google AI Blog", "keys": "google_ai_blog", "id": "gaib"},
        {"label": "Lobsters", "keys": "lobsters", "id": "lobsters"},
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
        {"label": "Kagi Europe", "keys": "kagi_europe", "id": "kagi_europe"},
        {"label": "Kagi Spain", "keys": "kagi_spain", "id": "kagi_spain"},
        {"label": "Microsiervos", "keys": "microsiervos", "id": "microsiervos"},
        {"label": "🇪🇸 Spanish Tech", "keys": "spanish_tech", "id": "spanish_tech"},
        {"label": "☁️ Cloud Updates", "keys": "cloud_updates", "id": "cloud_updates"},
        {"label": "📍 Valencia Local", "keys": "valencia_local", "id": "valencia_local"},
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
            ),
        ]
    )
