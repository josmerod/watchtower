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

# KNOWLEDGE GARDEN TAB - Reddit, dev communities, and similar sources
KNOWLEDGE_SOURCES_CONFIG = {
    # Open Source Projects
    "opensource": {
        "path": get_data_path("open_source_intelligence", "output", "latest.json"),
        "name": "Open Source Projects",
    },
    "gooddevs": {
        "path": get_data_path("gooddevs", "gooddevs_latest.json"),
        "name": "Good Devs",
    },
    "podcasts": {
        "path": get_data_path("podcasts", "podcasts_latest.json"),
        "name": "Podcasts",
    },
    "product_hunt": {
        "path": get_data_path("product_hunt", "product_hunt_latest.json"),
        "name": "Product Hunt",
    },
    # Developer Communities
    "gittrends": {
        "path": get_data_path("github_trends", "github_trends_latest.json"),
        "name": "Git Trends",
    },
    "hackernews_ask": {
        "path": get_data_path("hackernews_ask", "hackernews_ask_latest.json"),
        "name": "HN Ask",
    },
    "stackoverflow_trends": {
        "path": get_data_path("stackoverflow_trends", "stackoverflow_trends_latest.json"),
        "name": "Stack Overflow",
    },
    # Unified Reddit sources by category
    "reddit_unified": {
        "path": get_data_path("reddit_unified", "reddit_unified_latest.json"),
        "name": "Reddit All",
    },
    "reddit_ai_ml": {
        "path": get_data_path("reddit_unified", "reddit_ai_ml_latest.json"),
        "name": "Reddit AI/ML",
    },
    "reddit_programming": {
        "path": get_data_path("reddit_unified", "reddit_programming_latest.json"),
        "name": "Reddit Programming",
    },
    "reddit_tech": {
        "path": get_data_path("reddit_unified", "reddit_tech_latest.json"),
        "name": "Reddit Tech",
    },
    "reddit_devops": {
        "path": get_data_path("reddit_unified", "reddit_devops_latest.json"),
        "name": "Reddit DevOps",
    },
    # Dev.to articles
    "devto": {"path": get_data_path("devto", "devto.json"), "name": "Dev.to"},
    # HypeURLs (via Reddit)
    "hypeurls": {
        "path": get_data_path("reddit_unified", "reddit_news_latest.json"),
        "name": "HypeURLs"
    },
    "lesswrong": {
        "path": get_data_path("lesswrong", "lesswrong_latest.json"),
        "name": "LessWrong",
    },
}


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


def load_knowledge_from_file(file_path):
    """Loads knowledge items from a JSON file."""
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
        print(f"Warning: Knowledge file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {file_path}")
        return []
    except Exception as e:
        print(f"Error loading knowledge from {file_path}: {e}")
        return []


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
    }

    data = {source_key: repository_map[source_key].get() for source_key in repository_map}
    _KNOWLEDGE_CACHE = {"ts": now, "data": data}
    return data


# --- Helper function to parse dates ---
def parse_date(date_str):
    """Parse date string into UTC datetime object."""
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
    return parse_date_universal(s_date, "Knowledge")


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
    def get_sortable_date(article):
        date_str = (
            article.get("published_at") 
            or article.get("published") 
            or article.get("published_date") 
            or article.get("created_at") 
            or article.get("updated_at") 
            or article.get("updated") 
            or article.get("time") 
            or article.get("pubDate")
        )
        parsed = parse_date(date_str)
        return parsed if parsed else datetime.min.replace(tzinfo=timezone.utc)

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
        {"label": "Open Source", "keys": "opensource", "id": "opensource"},
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
