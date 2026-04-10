import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import html

# Import shared utilities
from src.web.dashboard.utils import get_data_path, parse_date_universal

# Import repository pattern (NEW)
from src.repositories import BaseRepository
from src.services.data_loader import (
    KNOWLEDGE_SOURCES_CONFIG,
    load_data_from_file,
    parse_date,
    get_sortable_date,
    format_article_date as format_article_date_shared,
)

# KNOWLEDGE GARDEN TAB - Reddit, dev communities, and similar sources
# KNOWLEDGE_SOURCES_CONFIG imported from data_loader


# NEW: Repository-based loading (SOLID Pattern)
class KnowledgeGardenRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for knowledge garden data."""

    def __init__(self, data_path: str):
        """Initialize knowledge garden repository.

        Args:
            data_path: Path to knowledge data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of knowledge items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of knowledge item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            # Handle cases where JSON might be a dict with a key containing the list
            if "articles" in raw_data and isinstance(raw_data["articles"], list):
                return raw_data["articles"]
            elif "items" in raw_data and isinstance(raw_data["items"], list):
                return raw_data["items"]
            # Single item
            if all(k in raw_data for k in ["title", "url"]):
                return [raw_data]
            return []
        else:
            return []

# Create singleton instances for each source
opensource_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["opensource"]["path"])
reddit_opensource_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_opensource"]["path"])
gooddevs_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["gooddevs"]["path"])
podcasts_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["podcasts"]["path"])
product_hunt_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["product_hunt"]["path"])
gittrends_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["gittrends"]["path"])
hackernews_ask_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["hackernews_ask"]["path"])
stackoverflow_trends_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["stackoverflow_trends"]["path"])
reddit_unified_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_unified"]["path"])
reddit_ai_ml_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_ai_ml"]["path"])
reddit_programming_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_programming"]["path"])
reddit_tech_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_tech"]["path"])
reddit_devops_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["reddit_devops"]["path"])
devto_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["devto"]["path"])
hypeurls_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["hypeurls"]["path"])
lesswrong_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["lesswrong"]["path"])
substack_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["substack"]["path"])
trendshift_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["trendshift"]["path"])
rss_feeds_repo = KnowledgeGardenRepository(KNOWLEDGE_SOURCES_CONFIG["rss_feeds"]["path"])


# load_knowledge_from_file removed (unused/dead code)


# Load knowledge data dynamically instead of at import time
def get_all_knowledge_data():
    """Load fresh knowledge data from all configured sources using repository pattern (NEW)."""
    # Simple TTL cache to avoid re-reading dozens of files on each tab switch
    # Cache in module state for ~60 seconds
    import time

    global _KNOWLEDGE_CACHE
    now = time.time()
    try:
        if _KNOWLEDGE_CACHE and now - _KNOWLEDGE_CACHE.get("ts", 0) < 60:
            return _KNOWLEDGE_CACHE["data"]
    except NameError:
        pass

    # Use repository pattern instead of manual file loading
    repository_map = {
        "opensource": opensource_repo,
        "reddit_opensource": reddit_opensource_repo,
        "gooddevs": gooddevs_repo,
        "podcasts": podcasts_repo,
        "product_hunt": product_hunt_repo,
        "gittrends": gittrends_repo,
        "hackernews_ask": hackernews_ask_repo,
        "stackoverflow_trends": stackoverflow_trends_repo,
        "reddit_unified": reddit_unified_repo,
        "reddit_ai_ml": reddit_ai_ml_repo,
        "reddit_programming": reddit_programming_repo,
        "reddit_tech": reddit_tech_repo,
        "reddit_devops": reddit_devops_repo,
        "devto": devto_repo,
        "hypeurls": hypeurls_repo,
        "lesswrong": lesswrong_repo,
        "substack": substack_repo,
        "trendshift": trendshift_repo,
        "rss_feeds": rss_feeds_repo,
    }

    data = {}
    for source_key, repo in repository_map.items():
        try:
            data[source_key] = repo.get()
        except Exception:
            # Gracefully handle missing/corrupt data files (e.g. ETL not yet run)
            data[source_key] = []
    _KNOWLEDGE_CACHE = {"ts": now, "data": data}
    return data


# --- Helper function to parse dates ---
# parse_date logic removed (using shared parse_date)


# --- Layout Generation ---

MAX_ARTICLES_PER_SOURCE = 50  # Limit number of articles displayed per source initially


# format_article_date removed (using shared logic)
def format_article_date(article):
    """Wrapper for shared formatting."""
    return format_article_date_shared(article)


def create_knowledge_source_tab_content(source_keys, combined_name=None):
    """Creates the content for a knowledge tab as a table, potentially combining multiple sources.

    Sorts articles by date before limiting.
    """
    all_articles_for_tab = []
    if isinstance(source_keys, str):  # Single source key
        source_keys = [source_keys]
        source_display_name = KNOWLEDGE_SOURCES_CONFIG[source_keys[0]]["name"]
    else:  # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined Knowledge"

    # Load fresh data each time
    all_knowledge_data = get_all_knowledge_data()

    for key in source_keys:
        articles_from_source = all_knowledge_data.get(key, [])
        # Add source name to each article for display in the table
        for article in articles_from_source:
            # Use 'source_display' to ensure we have a consistent field for the table
            article["source_display_name"] = article.get("source", KNOWLEDGE_SOURCES_CONFIG[key]["name"])
        all_articles_for_tab.extend(articles_from_source)

    # Sort all articles by date (descending)
    all_articles_for_tab.sort(key=get_sortable_date, reverse=True)

    articles_to_display = all_articles_for_tab[:MAX_ARTICLES_PER_SOURCE]

    if not articles_to_display:
        return dbc.Alert(f"No knowledge items available for {source_display_name}.", color="info")

    # Create table header
    table_header = [html.Thead(html.Tr([html.Th("Title"), html.Th("Source"), html.Th("Date")]))]

    # Create table body with robust field fallbacks for heterogeneous sources
    table_body_rows = []
    for article in articles_to_display:
        # Title fallbacks: common across Product Hunt/GitHub Trends/others
        title = article.get("title") or article.get("name") or article.get("full_name") or "No Title"
        # URL fallbacks
        url = article.get("url") or article.get("link") or article.get("html_url") or article.get("website")
        # Use the 'source_display_name' we added earlier
        source_for_display = article.get("source_display_name", source_display_name)
        date_display = format_article_date(article)

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(html.A(title, href=url, target="_blank") if url else title),
                    html.Td(source_for_display),
                    html.Td(date_display),
                ]
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

    # Return the table wrapped in a Div for consistent styling (e.g. maxHeight, overflow)
    return html.Div(table, style={"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"})


# Main function to render the knowledge garden tab
def render_knowledge_garden_tab():
    """Render the complete knowledge garden tab with all sub-tabs."""
    tab_definitions = [
        {"label": "LessWrong", "keys": "lesswrong", "id": "lw"},
        {"label": "Good Devs", "keys": "gooddevs", "id": "gd"},
        {"label": "Podcasts", "keys": "podcasts", "id": "pod"},
        {"label": "Reddit AI/ML", "keys": "reddit_ai_ml", "id": "reddit_ai_ml"},
        {
            "label": "Reddit Programming",
            "keys": "reddit_programming",
            "id": "reddit_prog",
        },
        {"label": "Reddit Tech", "keys": "reddit_tech", "id": "reddit_tech"},
        {"label": "Reddit DevOps", "keys": "reddit_devops", "id": "reddit_devops"},
        {"label": "Reddit All", "keys": "reddit_unified", "id": "reddit_all"},
        {"label": "Git Trends", "keys": "gittrends", "id": "gt"},
        {"label": "HN Ask", "keys": "hackernews_ask", "id": "hn_ask"},
        {"label": "Stack Overflow", "keys": "stackoverflow_trends", "id": "so"},
        {"label": "Product Hunt", "keys": "product_hunt", "id": "ph"},
        # Developer community tab
        {"label": "Dev.to", "keys": "devto", "id": "devto"},
        {"label": "HypeURLs", "keys": "hypeurls", "id": "hypeurls"},
        {"label": "Open Source", "keys": ["opensource", "reddit_opensource"], "id": "opensource"},
        {"label": "Substack", "keys": "substack", "id": "substack"},
        {"label": "TrendShift", "keys": "trendshift", "id": "trendshift"},
        {"label": "RSS Feeds", "keys": "rss_feeds", "id": "rss_feeds"},
    ]

    tabs_children = []
    
    # 2. Standard Knowledge Sources (Table Layout)
    for tab_def in tab_definitions:
        tab_id = f"knowledge-tab-{tab_def['id']}"
        content = create_knowledge_source_tab_content(tab_def["keys"], combined_name=tab_def["label"])
        tabs_children.append(
            dbc.Tab(
                label=tab_def["label"],
                tab_id=tab_id,
                children=content,
                id=tab_id + "-container",
            )
        )

    return html.Div(
        [
            html.H3("Knowledge Garden", className="mb-3"),
            dbc.Tabs(
                id="knowledge-source-tabs-main",
                children=tabs_children,
                active_tab="knowledge-tab-opensource",
            ),
        ]
    )


if __name__ == "__main__":
    # For testing this component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # The render_knowledge_garden_tab now produces the full tabbed layout
    app_test.layout = dbc.Container(
        [
            html.H1("Knowledge Garden Tab Test (Standalone)"),
            render_knowledge_garden_tab(),  # This will include the tabs and initial content
        ],
        fluid=True,
        className="py-4",
    )

    print("Running standalone test for knowledge_garden_tab.py...")
    print(f"Displaying max {MAX_ARTICLES_PER_SOURCE} articles per tab, sorted by date.")
    print("Expected knowledge JSON files relative to project root, e.g., data/futuretools/futuretoolsnews.json")
    print("Check console for warnings about missing files or parsing errors, especially date parsing.")
    app_test.run(debug=True, port=8053)
