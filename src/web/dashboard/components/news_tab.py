import json
from datetime import datetime, timezone

import dash
import dash_bootstrap_components as dbc
from dash import html

# Import shared utilities
from src.web.dashboard.utils import get_data_path, parse_date_universal

# --- Data Loading ---

NEWS_SOURCES_CONFIG = {
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
    "gooddevs": {
        "path": get_data_path("gooddevs", "gooddevs_latest.json"),
        "name": "Good Devs",
    },
    "meneame_general": {
        "path": get_data_path("meneame", "meneame_general_latest.json"),
        "name": "Meneame General",
    },
    "meneame_tecnologia": {
        "path": get_data_path("meneame", "meneame_tecnologia_latest.json"),
        "name": "Meneame Tech",
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
    "indiehackers": {
        "path": get_data_path("indie_hackers", "posts.json"),
        "name": "Indie Hackers",
    },
    "gittrends": {
        "path": get_data_path("github_trends", "github_trends_latest.json"),
        "name": "Git Trends",
    },
    "hackernews_ask": {
        "path": get_data_path("hackernews_ask", "hackernews_ask_latest.json"),
        "name": "HN Ask",
    },
    "stackoverflow_trends": {
        "path": get_data_path(
            "stackoverflow_trends", "stackoverflow_trends_latest.json"
        ),
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
    # Dev.to articles
    "devto": {"path": get_data_path("devto", "devto.json"), "name": "Dev.to"},
}


def load_news_from_file(file_path):
    """Loads news items from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure data is a list of records
            if isinstance(
                data, dict
            ):  # Handle cases where JSON might be a dict with a key containing the list
                if "articles" in data and isinstance(data["articles"], list):
                    return data["articles"]
                elif "items" in data and isinstance(data["items"], list):
                    return data["items"]
                # Add more checks if other common patterns are found
                else:  # If it's a dictionary but not a recognized pattern, wrap it in a list if it looks like a single item
                    if all(
                        k in data for k in ["title", "url"]
                    ):  # Heuristic for a single item
                        return [data]
                    print(
                        f"Warning: Data in {file_path} is a dict but not a recognized list structure. Returning empty."
                    )
                    return []
            elif isinstance(data, list):
                return data
            else:
                print(
                    f"Warning: Data in {file_path} is not a list or recognized dict structure. Type: {type(data)}. Returning empty."
                )
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

    data = {
        source_key: load_news_from_file(config["path"])
        for source_key, config in NEWS_SOURCES_CONFIG.items()
    }
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
        return (
            dt.astimezone(timezone.utc)
            if dt.tzinfo
            else dt.replace(tzinfo=timezone.utc)
        )
    except (ValueError, TypeError):
        pass  # Continue to other formats

    # Attempt 2: Try common string formats using strptime
    for fmt in datetime_formats:
        try:
            dt = datetime.strptime(s_date, fmt)
            # If parsing succeeds but dt is naive, assume UTC. If tz-aware, convert to UTC.
            return (
                dt.astimezone(timezone.utc)
                if dt.tzinfo
                else dt.replace(tzinfo=timezone.utc)
            )
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
    """
    Creates the content for a news tab as a table, potentially combining multiple sources.
    Sorts articles by date before limiting.
    """
    all_articles_for_tab = []
    if isinstance(source_keys, str):  # Single source key
        source_keys = [source_keys]
        source_display_name = NEWS_SOURCES_CONFIG[source_keys[0]]["name"]
    else:  # List of source keys (for combined tabs)
        source_display_name = combined_name or "Combined News"

    # Load fresh data each time
    all_news_data = get_all_news_data()

    for key in source_keys:
        articles_from_source = all_news_data.get(key, [])
        # Add source name to each article for display in the table
        for article in articles_from_source:
            # Use 'source_display' to ensure we have a consistent field for the table
            article["source_display_name"] = article.get(
                "source", NEWS_SOURCES_CONFIG[key]["name"]
            )
        all_articles_for_tab.extend(articles_from_source)

    # Sort all articles by date (descending)
    def get_sortable_date(article):
        date_str = (
            article.get("published_at")
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
        return dbc.Alert(
            f"No news items available for {source_display_name}.", color="info"
        )

    # Create table header
    table_header = [
        html.Thead(html.Tr([html.Th("Title"), html.Th("Source"), html.Th("Date")]))
    ]

    # Create table body with robust field fallbacks for heterogeneous sources
    table_body_rows = []
    for article in articles_to_display:
        # Title fallbacks: common across Product Hunt/GitHub Trends/others
        title = (
            article.get("title")
            or article.get("name")
            or article.get("full_name")
            or "No Title"
        )
        # URL fallbacks
        url = (
            article.get("url")
            or article.get("link")
            or article.get("html_url")
            or article.get("website")
        )
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
    return html.Div(
        table, style={"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"}
    )


# Main function to render the news tab
def render_news_tab():
    tab_definitions = [
        {
            "label": "FutureTools & Ben's Bites",
            "keys": ["futuretools", "bensbites"],
            "id": "ft-bb",
        },
        {"label": "Hacker News", "keys": "hackernews", "id": "hn"},
        {"label": "Medium GenAI", "keys": "medium_genai", "id": "med_genai"},
        {"label": "KDnuggets", "keys": "kdnuggets", "id": "kdn"},
        {"label": "Good Devs", "keys": "gooddevs", "id": "gd"},
        {"label": "Meneame General", "keys": "meneame_general", "id": "men_gen"},
        {"label": "Meneame Tech", "keys": "meneame_tecnologia", "id": "men_tec"},
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
        {"label": "Indie Hackers", "keys": "indiehackers", "id": "ih"},
        {"label": "Git Trends", "keys": "gittrends", "id": "gt"},
        {"label": "HN Ask", "keys": "hackernews_ask", "id": "hn_ask"},
        {"label": "Stack Overflow", "keys": "stackoverflow_trends", "id": "so"},
        # Kagi RSS feeds as individual tabs
        {"label": "Kagi World", "keys": "kagi_world", "id": "kagi_world"},
        {"label": "Kagi USA", "keys": "kagi_usa", "id": "kagi_usa"},
        {"label": "Kagi Business", "keys": "kagi_business", "id": "kagi_business"},
        {"label": "Kagi Science", "keys": "kagi_science", "id": "kagi_science"},
        {"label": "Kagi Gaming", "keys": "kagi_gaming", "id": "kagi_gaming"},
        {"label": "Kagi AI", "keys": "kagi_ai", "id": "kagi_ai"},
        {"label": "Kagi Europe", "keys": "kagi_europe", "id": "kagi_europe"},
        {"label": "Kagi Spain", "keys": "kagi_spain", "id": "kagi_spain"},
        # Developer community tab
        {"label": "Dev.to", "keys": "devto", "id": "devto"},
    ]

    tabs_children = []
    for i, tab_def in enumerate(tab_definitions):
        tab_id = f"news-tab-{tab_def['id']}"
        content = create_news_source_tab_content(
            tab_def["keys"], combined_name=tab_def["label"]
        )
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
    print(
        "Expected news JSON files relative to project root, e.g., data/futuretools/futuretoolsnews.json"
    )
    print(
        "Check console for warnings about missing files or parsing errors, especially date parsing."
    )
    app_test.run(debug=True, port=8052)
