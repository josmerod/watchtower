"""GitHub Trending Tab Component

This module creates a dashboard tab component for displaying GitHub trending repositories
from RSS feeds, organized by time period and programming language.
"""

import json
import dash
from dash import html
import dash_bootstrap_components as dbc
from datetime import datetime, timezone

# Import shared utilities
from src.web.dashboard.utils import get_data_path, parse_date_universal

# --- GitHub Trending Feed Configuration ---

GITHUB_TRENDING_FEEDS = {
    # All Languages
    "daily_all": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_daily_all.json",
        ),
        "name": "Daily - All Languages",
        "description": "Trending repositories today across all languages",
    },
    "weekly_all": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_weekly_all.json",
        ),
        "name": "Weekly - All Languages",
        "description": "Trending repositories this week across all languages",
    },
    "monthly_all": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_monthly_all.json",
        ),
        "name": "Monthly - All Languages",
        "description": "Trending repositories this month across all languages",
    },
    # Python
    "daily_python": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_daily_python.json",
        ),
        "name": "Daily - Python",
        "description": "Trending Python repositories today",
    },
    "weekly_python": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_weekly_python.json",
        ),
        "name": "Weekly - Python",
        "description": "Trending Python repositories this week",
    },
    "monthly_python": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_monthly_python.json",
        ),
        "name": "Monthly - Python",
        "description": "Trending Python repositories this month",
    },
    # Jupyter Notebook
    "weekly_jupyter": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_weekly_jupyter-notebook.json",
        ),
        "name": "Weekly - Jupyter Notebook",
        "description": "Trending Jupyter Notebook repositories this week",
    },
    "monthly_jupyter": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_monthly_jupyter-notebook.json",
        ),
        "name": "Monthly - Jupyter Notebook",
        "description": "Trending Jupyter Notebook repositories this month",
    },
    # CUDA
    "monthly_cuda": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_monthly_cuda.json",
        ),
        "name": "Monthly - CUDA",
        "description": "Trending CUDA repositories this month",
    },
    # Terraform (HCL)
    "monthly_terraform": {
        "path": get_data_path(
            "github_trending_rss/output/github_trending",
            "github_trending_monthly_hcl.json",
        ),
        "name": "Monthly - Terraform (HCL)",
        "description": "Trending Terraform repositories this month",
    },
}


def load_github_trending_data(file_path):
    """Load GitHub trending data from JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure data is a list
            if isinstance(data, dict):
                # Handle different JSON structures
                if "repositories" in data and isinstance(data["repositories"], list):
                    return data["repositories"]
                elif "items" in data and isinstance(data["items"], list):
                    return data["items"]
                else:
                    # If it's a single repo object, wrap in list
                    if "full_name" in data and "url" in data:
                        return [data]
                    return []
            elif isinstance(data, list):
                return data
            else:
                print(f"Warning: Unexpected data format in {file_path}")
                return []
    except FileNotFoundError:
        print(f"Warning: GitHub trending file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {file_path}")
        return []
    except Exception as e:
        print(f"Error loading GitHub trending data from {file_path}: {e}")
        return []


_GITHUB_TRENDING_ALL_CACHE = {"ts": 0, "data": {}}


def get_all_github_trending_data():
    """Load fresh GitHub trending data from all configured feeds with TTL cache."""
    import time
    now = time.time()
    if _GITHUB_TRENDING_ALL_CACHE.get("data") and (now - _GITHUB_TRENDING_ALL_CACHE.get("ts", 0) < 60):
        return _GITHUB_TRENDING_ALL_CACHE["data"]

    result = {
        feed_key: load_github_trending_data(config["path"]) for feed_key, config in GITHUB_TRENDING_FEEDS.items()
    }
    _GITHUB_TRENDING_ALL_CACHE["ts"] = now
    _GITHUB_TRENDING_ALL_CACHE["data"] = result
    return result


def parse_github_date(date_str):
    """Parse GitHub repository date fields."""
    if date_str is None or str(date_str).strip() == "":
        return None

    s_date = str(date_str)

    # Try ISO format first (GitHub API standard)
    try:
        dt = datetime.fromisoformat(s_date.replace("Z", "+00:00"))
        return (
            dt.astimezone(timezone.utc)
            if dt.tzinfo
            else dt.replace(tzinfo=timezone.utc)
        )
    except (ValueError, TypeError):
        pass

    # Fallback to universal parser
    return parse_date_universal(s_date, "GitHub")


def format_repo_date(repo):
    """Extract and format date from repository data."""
    # Try different date fields in order of preference
    date_fields = ["rss_published", "updated_at", "created_at", "fetched_at"]
    date_str = None

    for field in date_fields:
        date_str = repo.get(field)
        if date_str:
            break

    parsed_dt = parse_github_date(date_str)
    return parsed_dt.strftime("%Y-%m-%d %H:%M UTC") if parsed_dt else "Date N/A"


def format_number(num):
    """Format numbers with K/M suffixes for better readability."""
    if num is None:
        return "0"

    num = int(num) if isinstance(num, (int, float, str)) and str(num).isdigit() else 0

    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    else:
        return str(num)


def create_github_trending_tab_content(feed_keys, combined_name=None):
    """Create content for GitHub trending tab as a table."""
    all_repos_for_tab = []

    if isinstance(feed_keys, str):
        feed_keys = [feed_keys]
        source_display_name = GITHUB_TRENDING_FEEDS[feed_keys[0]]["name"]
    else:
        source_display_name = combined_name or "Combined GitHub Trending"

    # Load fresh data
    all_trending_data = get_all_github_trending_data()

    for key in feed_keys:
        repos_from_feed = all_trending_data.get(key, [])
        # Add feed info to each repo
        for repo in repos_from_feed:
            repo["feed_display_name"] = repo.get(
                "trending_category", GITHUB_TRENDING_FEEDS[key]["name"]
            )
        all_repos_for_tab.extend(repos_from_feed)

    # Sort by stars (descending), then by date
    def get_sort_key(repo):
        stars = int(repo.get("stars", 0)) if repo.get("stars") else 0
        date_str = (
            repo.get("rss_published")
            or repo.get("updated_at")
            or repo.get("fetched_at")
        )
        parsed_date = parse_github_date(date_str)
        date_val = (
            parsed_date if parsed_date else datetime.min.replace(tzinfo=timezone.utc)
        )
        return (-stars, -date_val.timestamp())  # Negative for descending order

    all_repos_for_tab.sort(key=get_sort_key)

    # Limit results
    MAX_REPOS_PER_TAB = 100
    repos_to_display = all_repos_for_tab[:MAX_REPOS_PER_TAB]

    if not repos_to_display:
        return dbc.Alert(
            f"No repositories available for {source_display_name}.", color="info"
        )

    # Create table header
    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Repository"),
                    html.Th("Description"),
                    html.Th("Language"),
                    html.Th("Stars"),
                    html.Th("Forks"),
                    html.Th("Owner"),
                    html.Th("Category"),
                    html.Th("Date"),
                ]
            )
        )
    ]

    # Create table body
    table_body_rows = []
    for repo in repos_to_display:
        # Extract repository data
        full_name = repo.get("full_name", repo.get("name", "Unknown"))
        url = repo.get("url", repo.get("html_url", "#"))
        description = repo.get("description", "No description available")
        language = repo.get("language", "Unknown")
        stars = format_number(repo.get("stars", 0))
        forks = format_number(repo.get("forks", 0))
        owner = repo.get("owner", "Unknown")
        category = repo.get("feed_display_name", source_display_name)
        date_display = format_repo_date(repo)

        # Truncate long descriptions
        if len(description) > 100:
            description = description[:97] + "..."

        # Create language badge
        language_color = {
            "Python": "primary",
            "JavaScript": "warning",
            "TypeScript": "info",
            "Java": "danger",
            "C++": "secondary",
            "C": "dark",
            "Go": "success",
            "Rust": "warning",
            "Jupyter Notebook": "primary",
            "CUDA": "success",
            "HCL": "info",
        }.get(language, "light")

        language_badge = (
            dbc.Badge(
                language,
                color=language_color,
                className="me-1",
                style={"fontSize": "0.75em"},
            )
            if language != "Unknown"
            else language
        )

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            (
                                html.A(
                                    full_name,
                                    href=url,
                                    target="_blank",
                                    style={
                                        "fontWeight": "bold",
                                        "textDecoration": "none",
                                    },
                                )
                                if url != "#"
                                else full_name
                            )
                        ]
                    ),
                    html.Td(description, style={"fontSize": "0.9em", "color": "#666"}),
                    html.Td(language_badge),
                    html.Td(
                        [
                            html.I(
                                className="fas fa-star",
                                style={"color": "#ffd700", "marginRight": "5px"},
                            ),
                            stars,
                        ],
                        style={"whiteSpace": "nowrap"},
                    ),
                    html.Td(
                        [
                            html.I(
                                className="fas fa-code-branch",
                                style={"color": "#666", "marginRight": "5px"},
                            ),
                            forks,
                        ],
                        style={"whiteSpace": "nowrap"},
                    ),
                    html.Td(owner, style={"fontSize": "0.9em"}),
                    html.Td(
                        dbc.Badge(
                            category, color="secondary", style={"fontSize": "0.7em"}
                        ),
                        style={"whiteSpace": "nowrap"},
                    ),
                    html.Td(
                        date_display,
                        style={"fontSize": "0.8em", "whiteSpace": "nowrap"},
                    ),
                ]
            )
        )

    table_body = [html.Tbody(table_body_rows)]

    # Create table
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

    # Add summary info
    total_stars = sum(
        int(repo.get("stars", 0)) for repo in repos_to_display if repo.get("stars")
    )
    summary_info = html.Div(
        [
            dbc.Badge(
                f"{len(repos_to_display)} repositories", color="info", className="me-2"
            ),
            dbc.Badge(
                f"{format_number(total_stars)} total stars",
                color="warning",
                className="me-2",
            ),
        ],
        className="mb-3",
    )

    return html.Div(
        [
            summary_info,
            html.Div(
                table,
                style={
                    "maxHeight": "800px",
                    "overflowY": "auto",
                    "paddingRight": "15px",
                },
            ),
        ]
    )


def render_github_trending_tab():
    """Main function to render the GitHub trending tab with subtabs."""

    tab_definitions = [
        # All Languages by Period
        {"label": "Daily - All", "keys": "daily_all", "id": "daily-all"},
        {"label": "Weekly - All", "keys": "weekly_all", "id": "weekly-all"},
        {"label": "Monthly - All", "keys": "monthly_all", "id": "monthly-all"},
        # Python by Period
        {"label": "Daily - Python", "keys": "daily_python", "id": "daily-python"},
        {"label": "Weekly - Python", "keys": "weekly_python", "id": "weekly-python"},
        {"label": "Monthly - Python", "keys": "monthly_python", "id": "monthly-python"},
        # Specialized Languages
        {"label": "Weekly - Jupyter", "keys": "weekly_jupyter", "id": "weekly-jupyter"},
        {
            "label": "Monthly - Jupyter",
            "keys": "monthly_jupyter",
            "id": "monthly-jupyter",
        },
        {"label": "Monthly - CUDA", "keys": "monthly_cuda", "id": "monthly-cuda"},
        {
            "label": "Monthly - Terraform",
            "keys": "monthly_terraform",
            "id": "monthly-terraform",
        },
    ]

    tabs_children = []
    for tab_def in tab_definitions:
        tab_id = f"github-trending-tab-{tab_def['id']}"
        content = create_github_trending_tab_content(
            tab_def["keys"], combined_name=tab_def["label"]
        )
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
            html.H3("GitHub Trending Repositories", className="mb-3"),
            html.P(
                "Trending GitHub repositories from RSS feeds, organized by time period and programming language.",
                className="text-muted mb-4",
            ),
            dbc.Tabs(
                id="github-trending-tabs-main",
                children=tabs_children,
                active_tab="github-trending-tab-daily-all",
            ),
        ]
    )


if __name__ == "__main__":
    # For testing this component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    app_test.layout = dbc.Container(
        [
            html.H1("GitHub Trending Tab Test (Standalone)"),
            render_github_trending_tab(),
        ],
        fluid=True,
    )

    app_test.run(debug=True, port=8052)
