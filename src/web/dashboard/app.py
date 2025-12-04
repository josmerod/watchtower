from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import (  # Added Input, Output, dcc, clientside_callback, ALL for Tabs and callback
    Input,
    Output,
    clientside_callback,
    dcc,
    html,
)
from flask import jsonify

from src.web.dashboard.components.ai_research_tab import render_ai_research_tab
from src.web.dashboard.components.anime_tab import (
    register_anime_callbacks,
    render_anime_tab,
)
from src.web.dashboard.components.architecture_intelligence_tab import (
    register_architecture_callbacks,
    render_architecture_intelligence_tab,
)
from src.web.dashboard.components.arxiv_research_tab import (
    register_arxiv_callbacks,
    render_arxiv_research_tab,
)
from src.web.dashboard.components.cloud_tab import (
    register_cloud_callbacks,
    render_cloud_tab,
)
from src.web.dashboard.components.courses_tab import (
    register_courses_callbacks,
    render_courses_tab,
)
from src.web.dashboard.components.customize_tabs import customize_tabs
from src.web.dashboard.components.deals_tab import (
    register_deals_search_callbacks,
    render_deals_tab,
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
from src.web.dashboard.components.knowledge_garden_tab import (
    render_knowledge_garden_tab,
)
from src.web.dashboard.components.metrics_tab import (
    register_metrics_callbacks,
    render_metrics_tab,
)
from src.web.dashboard.components.news_tab import (
    register_news_search_callbacks,
    render_news_tab,
)
from src.web.dashboard.components.notifications_tab import (
    register_notifications_callbacks,
    render_notifications_tab,
)
from src.web.dashboard.components.personalization_tab import (
    register_personalization_callbacks,
    render_personalization_tab,
)
from src.web.dashboard.components.scavenging_tab import (
    register_scavenging_callbacks,
    render_scavenging_tab,
)
from src.web.dashboard.components.shortcuts_sidebar import shortcuts_sidebar
from src.web.dashboard.components.shortcuts_tab import (
    get_shortcuts_data,
    render_shortcuts_tab,
    render_shortcuts_tab_layout,
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

# Include localStorage script for filter presets and shortcuts functionality
external_scripts = [
    "/assets/js/localStorage.js",
    "/assets/js/items_per_page.js",
    "/assets/js/mobile_navigation.js",
    "/assets/js/shortcuts.js",
    "/assets/js/dragdrop.js",
    "/assets/js/tab_preferences.js",
    "/assets/js/customize_tabs_dragdrop.js",
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

# Register callbacks for components that need them
register_personalization_callbacks(app)
register_architecture_callbacks(app)
register_cloud_callbacks(app)

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
        # Skip to content link for accessibility
        html.A(
            "Skip to main content",
            href="#dashboard-content",
            className="skip-to-content",
        ),
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
            [
                shortcuts_sidebar.create_toggle_button(),
                customize_tabs.create_toggle_button(),
            ],
            className="header-buttons d-flex justify-content-end gap-2 mb-3 desktop-only",
        ),
        # Add shortcuts sidebar (hidden by default)
        shortcuts_sidebar.create_sidebar(),
        # Add customize tabs modal with required components (hidden by default)
        customize_tabs.create_modal(),
        # Hidden components required for customize tabs functionality
        html.Div(id="customize-tabs-trigger", style={"display": "none"}),
        dcc.Store(id="customize-tabs-data-store", data={}),
        # Mobile navigation will be inserted here by JavaScript
        # Dashboard content area
        html.Div(id="dashboard-content", className="dashboard-content"),
        # Navigation tabs
        dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    id="dashboard-tabs",
                    active_tab="tab-shortcuts",  # Set a default active tab
                    className="desktop-nav-tabs",
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
                            label="🔔 Notifications",
                            tab_id="tab-notifications",
                            children=[render_notifications_tab()],
                        ),
                        dbc.Tab(
                            label="🌱 Knowledge Garden",
                            tab_id="tab-knowledge-garden",
                            children=[render_knowledge_garden_tab()],
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
                            label="Content Insights",
                            tab_id="tab-intelligence",
                            children=[render_intelligence_tab()],
                        ),
                        dbc.Tab(
                            label="AI Research Intelligence",
                            tab_id="tab-ai-research",
                            children=[render_ai_research_tab()],
                        ),
                        dbc.Tab(
                            label="🎯 My AI Learning",
                            tab_id="tab-personalization",
                            children=[render_personalization_tab()],
                        ),
                        dbc.Tab(
                            label="🏗️ Architecture",
                            tab_id="tab-architecture",
                            children=[render_architecture_intelligence_tab()],
                        ),
                        dbc.Tab(
                            label="☁️ Cloud",
                            tab_id="tab-cloud",
                            children=[render_cloud_tab()],
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
                        dbc.Tab(
                            label="💰 Deals & Offers",
                            tab_id="tab-deals",
                            children=[render_deals_tab()],
                        ),
                        dbc.Tab(
                            label="📊 Metrics",
                            tab_id="tab-metrics",
                            children=[render_metrics_tab()],
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
register_news_search_callbacks(app)
register_deals_search_callbacks(app)
register_metrics_callbacks(app)
register_notifications_callbacks(app)


# Clientside callback to dynamically generate tabs based on user preferences

clientside_callback(
    """
    function(n_clicks) {
        try {
            // Wait for the page to fully load and tab preferences to be available
            setTimeout(() => {
                applyTabPreferences();
            }, 1000);

            return window.dash_clientside.no_update;
        } catch (error) {
            console.error('Error in dynamic tab generation callback:', error);
            return window.dash_clientside.no_update;
        }
    }

    function applyTabPreferences() {
        try {
            // Initialize tab preferences if not available
            if (!window.tabPreferencesManager) {
                console.warn('TabPreferencesManager not available, will retry...');
                setTimeout(applyTabPreferences, 1000);
                return;
            }

            // Get visible tabs based on user preferences
            const visibleTabs = window.tabPreferencesManager.getVisibleTabs();

            if (!visibleTabs || visibleTabs.length === 0) {
                console.warn('No visible tabs found, using default configuration');
                return;
            }

            // Hide tabs that are not in the visible list
            const allTabElements = document.querySelectorAll('#dashboard-tabs [tab_id]');
            const visibleTabIds = new Set(visibleTabs.map(tab => tab.id));

            allTabElements.forEach(tabElement => {
                const tabId = tabElement.getAttribute('tab_id');
                if (!visibleTabIds.has(tabId)) {
                    tabElement.style.display = 'none';
                } else {
                    tabElement.style.display = '';
                }
            });

            // Reorder tabs to match user preferences
            const tabsContainer = document.querySelector('#dashboard-tabs .nav-tabs');
            if (tabsContainer) {
                const tabItems = Array.from(tabsContainer.children);

                // Sort tab items according to user preference order
                tabItems.sort((a, b) => {
                    const aTabId = a.getAttribute('tab_id');
                    const bTabId = b.getAttribute('tab_id');

                    const aIndex = visibleTabs.findIndex(tab => tab.id === aTabId);
                    const bIndex = visibleTabs.findIndex(tab => tab.id === bTabId);

                    return aIndex - bIndex;
                });

                // Re-append sorted items to maintain order
                tabItems.forEach(tabItem => {
                    tabsContainer.appendChild(tabItem);
                });
            }

            console.log('Tabs dynamically generated based on preferences:', visibleTabs.map(t => t.id));

        } catch (error) {
            console.error('Error applying tab preferences:', error);
        }
    }
    """,
    Output("dynamic-tab-trigger-container", "children"),  # Dummy output
    Input("dynamic-tab-trigger-0", "n_clicks"),
    prevent_initial_call=False,  # Run on page load to apply saved preferences
)


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
