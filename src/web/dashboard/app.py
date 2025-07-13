import dash
import dash_bootstrap_components as dbc
from dash import html

from dash import dcc, Input, Output # Added Input, Output, dcc for Tabs and callback
from src.web.dashboard.components.shortcuts_tab import render_shortcuts_tab, ALL_SHORTCUTS_DATA, render_shortcuts_tab_layout

from src.web.dashboard.components.news_tab import render_news_tab

from src.web.dashboard.components.videos_tab import render_videos_tab, register_video_callbacks

from src.web.dashboard.components.games_tab import render_games_tab

from src.web.dashboard.components.courses_tab import render_courses_tab, register_courses_callbacks

from src.web.dashboard.components.anime_tab import render_anime_tab, register_anime_callbacks

from src.web.dashboard.components.fourchan_tab import render_fourchan_tab, register_fourchan_callbacks

from src.web.dashboard.components.scavenging_tab import render_scavenging_tab, register_scavenging_callbacks

from src.web.dashboard.components.valencia_events_tab import render_valencia_events_tab, register_valencia_events_callbacks

from src.web.dashboard.components.youtube_ocr_tab import render_youtube_ocr_tab, register_youtube_ocr_callbacks

# Initialize the Dash application with Bootstrap styling
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Set app title for browser tab and configure metadata
app.title = "Watchtower Dashboard"

# Add meta tags for better branding
app.index_string = '''
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
'''

# Main layout with Tabs
app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(html.H1("Watchtower Dashboard", className="text-center my-4"))
        ),
        dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    id="dashboard-tabs",
                    active_tab="tab-shortcuts", # Set a default active tab
                    children=[
                        dbc.Tab(label="Shortcuts", tab_id="tab-shortcuts", children=[
                            render_shortcuts_tab()
                        ]),
                        dbc.Tab(label="News", tab_id="tab-news", children=[
                            render_news_tab()
                        ]),
                        dbc.Tab(label="Videos", tab_id="tab-videos", children=[
                            render_videos_tab()
                        ]),
                        dbc.Tab(label="Games", tab_id="tab-games", children=[
                            render_games_tab()
                        ]),
                        dbc.Tab(label="Courses", tab_id="tab-courses", children=[
                            render_courses_tab()
                        ]),
                        dbc.Tab(label="Anime", tab_id="tab-anime", children=[
                            render_anime_tab()
                        ]),
                        dbc.Tab(label="4chan Generals", tab_id="tab-4chan", children=[
                            render_fourchan_tab()
                        ]),
                        dbc.Tab(label="Scavenging", tab_id="tab-scavenging", children=[
                            render_scavenging_tab()
                        ]),
                        dbc.Tab(label="Valencia Events", tab_id="tab-valencia", children=[
                            render_valencia_events_tab()
                        ]),
                        dbc.Tab(label="YouTube OCR", tab_id="tab-youtube-ocr", children=[
                            render_youtube_ocr_tab()
                        ]),
                    ],
                )
            )
        ),
    ],
    fluid=True,
)

# Register callbacks for the main app
# Callback for updating shortcuts in the Shortcuts Tab
@app.callback(
    Output("shortcuts-cards-container", "children"), # This ID is in shortcuts_tab.py
    [Input("search-shortcuts-input", "value")]    # This ID is in shortcuts_tab.py
)
def update_main_app_shortcuts(search_value):
    # Reuse the layout rendering function from shortcuts_tab.py
    # ALL_SHORTCUTS_DATA is imported from shortcuts_tab.py
    return render_shortcuts_tab_layout(ALL_SHORTCUTS_DATA, search_value)

# Register callbacks from other modules
register_video_callbacks(app)
register_courses_callbacks(app)
register_anime_callbacks(app)
register_fourchan_callbacks(app)
register_scavenging_callbacks(app)
register_valencia_events_callbacks(app)
register_youtube_ocr_callbacks(app)

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
    if ALL_SHORTCUTS_DATA:
        print("  Shortcuts data loaded successfully.")
    else:
        print("  Warning: Shortcuts data might be missing.")

    # Accessing ALL_NEWS_DATA and ALL_VIDEOS_DATA directly here would require importing them into app.py
    # For now, we assume their respective tabs handle their data loading messages.
    # If this script (app.py) is run directly, ensure CWD allows components to find their data.
    # Typically, one would run `run_watchtower_dashboard.py` from the project root.

    app.run_server(debug=False, port=8050) # Default Dash port for direct app run
