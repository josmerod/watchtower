from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, html  # Added Input, Output for Tabs and callback
from flask import jsonify

from src.web.dashboard.components.anime_tab import (
    register_anime_callbacks,
    render_anime_tab,
)
from src.web.dashboard.components.arxiv_research_tab import (
    register_arxiv_callbacks,
    render_arxiv_research_tab,
)
from src.web.dashboard.components.courses_tab import (
    register_courses_callbacks,
    render_courses_tab,
)
from src.web.dashboard.components.fourchan_tab import (
    register_fourchan_callbacks,
    render_fourchan_tab,
)
from src.web.dashboard.components.games_tab import render_games_tab
from src.web.dashboard.components.github_trending_tab import render_github_trending_tab
from src.web.dashboard.components.giveaways_tab import create_giveaways_tab
from src.web.dashboard.components.intelligence_tab import (
    register_intelligence_callbacks,
    render_intelligence_tab,
)
from src.web.dashboard.components.news_tab import render_news_tab
from src.web.dashboard.components.scavenging_tab import (
    register_scavenging_callbacks,
    render_scavenging_tab,
)
from src.web.dashboard.components.shortcuts_tab import (
    get_shortcuts_data,
    render_shortcuts_tab,
    render_shortcuts_tab_layout,
)
from src.web.dashboard.components.spanish_public_aid_tab import (
    register_spanish_aid_callbacks,
    render_spanish_public_aid_tab,
)
from src.web.dashboard.components.valencia_events_tab import (
    register_valencia_events_callbacks,
    render_valencia_events_tab,
)
from src.web.dashboard.components.videos_tab import (
    register_video_callbacks,
    render_videos_tab,
)

# Initialize the Dash application with Bootstrap styling
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Set app title for browser tab and configure metadata
app.title = "Watchtower Dashboard"

# Add meta tags for better branding
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Watchtower Dashboard</title>
        <meta name="description" content="Watchtower - Real-time Intelligence & Monitoring Platform">
        <link rel="icon" type="image/svg+xml" href="/assets/watchtower_icon.svg">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# Main layout with Tabs
app.layout = dbc.Container(
    [
        dbc.Row(dbc.Col(html.H1("Watchtower Dashboard", className="text-center my-4"))),
        dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    id="dashboard-tabs",
                    active_tab="tab-shortcuts",  # Set a default active tab
                    children=[
                        dbc.Tab(
                            label="Shortcuts",
                            tab_id="tab-shortcuts",
                            children=[render_shortcuts_tab()],
                        ),
                        dbc.Tab(
                            label="News",
                            tab_id="tab-news",
                            children=[render_news_tab()],
                        ),
                        dbc.Tab(
                            label="GitHub Trending",
                            tab_id="tab-github-trending",
                            children=[render_github_trending_tab()],
                        ),
                        dbc.Tab(
                            label="Videos",
                            tab_id="tab-videos",
                            children=[render_videos_tab()],
                        ),
                        dbc.Tab(
                            label="Games",
                            tab_id="tab-games",
                            children=[render_games_tab()],
                        ),
                        dbc.Tab(
                            label="Intelligence",
                            tab_id="tab-intelligence",
                            children=[render_intelligence_tab()],
                        ),
                        dbc.Tab(
                            label="Courses",
                            tab_id="tab-courses",
                            children=[render_courses_tab()],
                        ),
                        dbc.Tab(
                            label="Anime",
                            tab_id="tab-anime",
                            children=[render_anime_tab()],
                        ),
                        dbc.Tab(
                            label="4chan Generals",
                            tab_id="tab-4chan",
                            children=[render_fourchan_tab()],
                        ),
                        dbc.Tab(
                            label="Scavenging",
                            tab_id="tab-scavenging",
                            children=[render_scavenging_tab()],
                        ),
                        dbc.Tab(
                            label="Valencia Events",
                            tab_id="tab-valencia",
                            children=[render_valencia_events_tab()],
                        ),
                        dbc.Tab(
                            label="🎁 Giveaways",
                            tab_id="tab-giveaways",
                            children=[create_giveaways_tab()],
                        ),
                        dbc.Tab(
                            label="🏛️ Ayudas Públicas",
                            tab_id="tab-spanish-aid",
                            children=[render_spanish_public_aid_tab()],
                        ),
                        dbc.Tab(
                            label="📄 ArXiv Research",
                            tab_id="tab-arxiv-research",
                            children=[render_arxiv_research_tab()],
                        ),
                    ],
                )
            )
        ),
        # Dynamic tab content container
        dbc.Row(dbc.Col(html.Div(id="tab-content", className="mt-3"))),
    ],
    fluid=True,
)

# Expose basic health/metrics endpoints
server = app.server


@server.route("/health")
def health() -> str:
    """Health endpoint for uptime checks."""
    return jsonify(
        {"status": "ok", "time_utc": datetime.utcnow().isoformat(timespec="seconds")}
    )


@server.route("/metrics")
def metrics() -> str:
    """Lightweight metrics summary for latest datasets used by the dashboard."""
    import json
    import os
    from pathlib import Path

    base = Path("data")
    files = {
        "product_hunt": base / "product_hunt" / "product_hunt_latest.json",
        "github_trends": base / "github_trends" / "github_trends_latest.json",
        "arxiv_papers": base / "arxiv" / "arxiv_papers_latest.json",
        "free_games": base / "giveaways" / "free_games_latest.json",
    }

    summary = {"generated_at": datetime.utcnow().isoformat(timespec="seconds")}
    for key, path in files.items():
        try:
            count = 0
            mtime = None
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        count = len(data)
                    elif isinstance(data, dict):
                        # Fallback: try common list fields
                        for field in ("items", "articles", "results"):
                            if field in data and isinstance(data[field], list):
                                count = len(data[field])
                                break
                except Exception:
                    count = -1  # denote read error
                try:
                    mtime = datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat(
                        timespec="seconds"
                    )
                except Exception:
                    mtime = None
            summary[key] = {"exists": path.exists(), "count": count, "modified": mtime}
        except Exception:
            summary[key] = {"exists": False, "count": -1, "modified": None}

    return jsonify(summary)


# Register callbacks for the main app
# Callback for updating shortcuts in the Shortcuts Tab


@app.callback(
    Output("shortcuts-cards-container", "children"),  # This ID is in shortcuts_tab.py
    [Input("search-shortcuts-input", "value")],  # This ID is in shortcuts_tab.py
)
def update_main_app_shortcuts(search_value):
    """Filter shortcuts by the search input and return updated cards."""
    return render_shortcuts_tab_layout(get_shortcuts_data(), search_value)


# Callback for dynamic tab content loading
# Remove legacy dynamic loader with dead branches to avoid confusion
# (Tabs are rendered directly above per component.)


# Register callbacks from other modules
register_video_callbacks(app)
register_courses_callbacks(app)
register_anime_callbacks(app)
register_fourchan_callbacks(app)
register_scavenging_callbacks(app)
register_valencia_events_callbacks(app)
register_spanish_aid_callbacks(app)
register_arxiv_callbacks(app)
register_intelligence_callbacks(app)


if __name__ == "__main__":
    # Note on data loading:
    # - Shortcuts data (ALL_SHORTCUTS_DATA) is loaded when shortcuts_tab.py is imported.
    # - News data (ALL_NEWS_DATA) is loaded when news_tab.py is imported.
    # - Videos data (ALL_VIDEOS_DATA) is loaded when videos_tab.py is imported.
    # These imports happen when app.py itself is imported (e.g., by run_watchtower_dashboard.py).
    # The relative paths within each component (e.g., '../../../data/...') are resolved
    # based on the Current Working Directory (CWD) when the Python interpreter loads those modules.
    # If run_watchtower_dashboard.py is at project root, CWD is project root, so paths should be correct.

    print("Verifying data loaded for Watchtower Dashboard:")
    # Simple check, more detailed checks are in individual tab's __main__ blocks
    if get_shortcuts_data():
        print("  Shortcuts data loaded successfully.")
    else:
        print("  Warning: Shortcuts data might be missing.")

    # Accessing ALL_NEWS_DATA and ALL_VIDEOS_DATA directly here would require importing them into app.py
    # For now, we assume their respective tabs handle their data loading messages.
    # If this script (app.py) is run directly, ensure CWD allows components to find their data.
    # Typically, one would run `run_watchtower_dashboard.py` from the project root.

    app.run_server(debug=False, port=8050)  # Default Dash port for direct app run
