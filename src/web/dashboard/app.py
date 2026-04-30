from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, clientside_callback

from src.web.dashboard.components.anime_tab import render_anime_tab
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

from src.web.dashboard.components.open_source_tab import render_open_source_tab

from src.web.dashboard.components.scavenging_tab import (
    render_scavenging_tab,
    register_scavenging_callbacks,
)
from src.web.dashboard.components.shortcuts_tab import (
    render_shortcuts_tab,
    register_shortcuts_callbacks,
    get_shortcuts_data,
)

from src.web.dashboard.components.deals_tab import (
    render_deals_tab,
    register_deals_callbacks,
)

from src.web.dashboard.components.benchmarks_tab import (
    render_benchmarks_tab,
    register_benchmarks_callbacks,
)




from src.web.dashboard.components.knowledge_garden_tab import (
    render_knowledge_garden_tab,
)



from src.web.dashboard.components.news_tab import (
    register_news_search_callbacks,
    render_news_tab,
)

# Removed notifications tab import as per UI cleanup

from src.web.dashboard.components.scavenging_tab import (
    register_scavenging_callbacks,
    render_scavenging_tab,
)


from src.web.dashboard.components.spanish_public_aid_tab import (
    register_spanish_aid_callbacks,
    render_spanish_public_aid_tab,
)

from src.web.dashboard.components.valencia_events_new_tab import (
    register_valencia_events_callbacks,
    render_valencia_events_tab,
)
from src.web.dashboard.components.videos_tab import (
    register_video_callbacks,
    render_videos_tab,
)

from src.web.dashboard.health_monitor import HealthMonitor
from src.web.api.routes import api_bp  # Import API Blueprint

# Include localStorage script for filter presets and shortcuts functionality
external_scripts = [
    "/assets/js/localStorage.js",
    "/assets/js/items_per_page.js",
    "/assets/js/mobile_navigation.js",
    "/assets/js/shortcuts.js",
    "/assets/js/dragdrop.js",
    "/assets/js/dragdrop.js",
    "https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js",
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.6/dist/js/bootstrap.bundle.min.js",
]

# Initialize the Dash application with Bootstrap styling
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    external_scripts=external_scripts,
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
        <link rel="stylesheet" href="/assets/css/shortcuts.css">
        <link rel="stylesheet" href="/assets/css/mobile_responsive.css">
        <!-- Font Awesome for mobile navigation icons -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
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
        # Skip to content link removed

        # Header with mobile-responsive layout
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H1(
                                    "Watchtower Dashboard",
                                    className="dashboard-header-title mb-0",
                                ),
                            ],
                            className="dashboard-header d-flex flex-column flex-md-row justify-content-between align-items-center",
                        ),
                    ],
                    width=12,
                ),
            ],
            className="dashboard-header mb-4",
        ),
        # Header buttons container
        html.Div(
            className="d-none",  # Hidden container specifically for keeping mobile nav happy if it looks for header-buttons
            children=[
                 # Removed shortcuts_sidebar and customize_tabs toggles
            ]
        ),
        # Removed shortcuts sidebar
        # Removed customize tabs modal and stores
        # Mobile navigation will be inserted here by JavaScript
        # Dashboard content area
        html.Div(id="dashboard-content", className="dashboard-content"),
        # Navigation tabs
        dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    id="dashboard-tabs",
                    active_tab="tab-news",  # Set a default active tab
                    className="desktop-nav-tabs",
                    children=[


                        dbc.Tab(
                            label="News",
                            tab_id="tab-news",
                            children=[render_news_tab()],
                        ),

                        dbc.Tab(
                            label="Shortcuts",
                            tab_id="tab-shortcuts",
                            children=[render_shortcuts_tab()],
                        ),

                        dbc.Tab(
                            label="🌱 Knowledge Garden",
                            tab_id="tab-knowledge-garden",
                            children=[render_knowledge_garden_tab()],
                        ),
                        # Open Source moved to Knowledge Garden subtab
                        dbc.Tab(
                            label="Videos",
                            tab_id="tab-videos",
                            children=[render_videos_tab()],
                        ),

                        # Removed Intelligence and AI Research tabs as per cleanup


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
                            label="🏛️ Ayudas Públicas",
                            tab_id="tab-spanish-aid",
                            children=[render_spanish_public_aid_tab()],
                        ),
                        dbc.Tab(
                            label="📄 ArXiv Research",
                            tab_id="tab-arxiv-research",
                            children=[render_arxiv_research_tab()],
                        ),
                        dbc.Tab(
                            label="🏷️ Deals",
                            tab_id="tab-deals",
                            children=[render_deals_tab()],
                        ),
                        dbc.Tab(
                            label="🏆 Benchmarks",
                            tab_id="tab-benchmarks",
                            children=[render_benchmarks_tab()],
                        ),
                    ],
                )
            )
        ),
        # Dynamic tab content container
        dbc.Row(dbc.Col(html.Div(id="tab-content", className="mt-3"))),
        # Hidden trigger for dynamic tab generation
        html.Div(
            [
                html.Button(
                    "Refresh Tabs",
                    id="dynamic-tab-trigger-0",
                    n_clicks=0,
                    style={"display": "none"},
                ),
            ],
            id="dynamic-tab-trigger-container",
            style={"display": "none"},
        ),
    ],
    fluid=True,
)

# Expose enhanced health/metrics endpoints
server = app.server

# Initialize health monitor
health_monitor = HealthMonitor()


@server.route("/health")
def health():
    """Enhanced health endpoint with status calculation and caching."""
    try:
        # Try to get cached response first
        cached_response = health_monitor.get_cached_response("health")
        if cached_response:
            return jsonify(cached_response)

        # Calculate health status
        health_status = health_monitor.calculate_overall_health()

        # Convert to dict for JSON response
        response_data = health_status.model_dump()

        # Cache for 5 minutes
        health_monitor.set_cached_response("health", response_data, ttl_minutes=5)

        return jsonify(response_data)

    except Exception as e:
        # Fallback response on error
        return (
            jsonify(
                {
                    "status": "down",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0.0",
                    "error": str(e),
                }
            ),
            500,
        )


@server.route("/metrics")
def metrics():
    """Enhanced metrics endpoint with comprehensive ETL metrics and caching."""
    try:
        # Try to get cached response first
        cached_response = health_monitor.get_cached_response("metrics")
        if cached_response:
            return jsonify(cached_response)

        # Generate comprehensive metrics summary
        metrics_summary = health_monitor.generate_metrics_summary()

        # Convert to dict for JSON response
        response_data = metrics_summary.model_dump()

        # Cache for 5 minutes
        health_monitor.set_cached_response("metrics", response_data, ttl_minutes=5)

        return jsonify(response_data)

    except Exception as e:
        # Fallback response on error
        return (
            jsonify(
                {
                    "generated_at": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "total_sources": 0,
                    "total_items": 0,
                    "last_etl_run_times": {},
                    "error_rates_per_source": {},
                }
            ),
            500,
        )


# Register callbacks for the main app
# Callback for updating shortcuts in the Shortcuts Tab





# Callback for dynamic tab content loading
# Remove legacy dynamic loader with dead branches to avoid confusion
# (Tabs are rendered directly above per component.)


# Register callbacks from other modules
register_video_callbacks(app)
register_courses_callbacks(app)
register_spanish_aid_callbacks(app)
register_arxiv_callbacks(app)

register_news_search_callbacks(app)
register_scavenging_callbacks(app)
register_valencia_events_callbacks(app)
register_shortcuts_callbacks(app)
register_deals_callbacks(app)
register_benchmarks_callbacks(app)









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

    app.run(debug=False, port=8050)  # Default Dash port for direct app run
