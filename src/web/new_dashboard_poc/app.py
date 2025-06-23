import dash
import dash_bootstrap_components as dbc
from dash import html

from dash import dcc, Input, Output # Added Input, Output, dcc for Tabs and callback
from src.web.new_dashboard_poc.components.shortcuts_tab import render_shortcuts_tab, ALL_SHORTCUTS_DATA, render_shortcuts_tab_layout

from src.web.new_dashboard_poc.components.news_tab import render_news_tab

from src.web.new_dashboard_poc.components.videos_tab import render_videos_tab, register_video_callbacks

from src.web.new_dashboard_poc.components.google_cloud_blog_tab import render_gcp_blog_tab

from src.web.new_dashboard_poc.components.aws_training_tab import render_aws_training_tab

from src.web.new_dashboard_poc.components.azure_training_tab import render_azure_training_tab

from src.web.new_dashboard_poc.components.games_tab import render_games_tab

from src.web.new_dashboard_poc.components.allkeyshop_tab import render_allkeyshop_tab, register_allkeyshop_callbacks

from src.web.new_dashboard_poc.components.courses_tab import render_courses_tab, register_courses_callbacks

from src.web.new_dashboard_poc.components.tech_events_tab import render_tech_events_tab, register_tech_events_callbacks

from src.web.new_dashboard_poc.components.dev_communities_tab import render_dev_communities_tab, register_dev_communities_callbacks

from src.web.new_dashboard_poc.components.security_tab import render_security_tab, register_security_callbacks

from src.web.new_dashboard_poc.components.innovation_tab import render_innovation_tab, register_innovation_callbacks

from src.web.new_dashboard_poc.components.ai_platforms_tab import render_ai_platforms_tab, register_ai_platforms_callbacks

from src.web.new_dashboard_poc.components.home_server_tab import render_home_server_tab, register_home_server_callbacks

# Initialize the Dash application with Bootstrap styling
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Main layout with Tabs
app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(html.H1("New Dashboard POC", className="text-center my-4"))
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
                        dbc.Tab(label="Google Cloud Blog", tab_id="tab-gcp-blog", children=[
                            render_gcp_blog_tab()
                        ]),
                        dbc.Tab(label="AWS Training", tab_id="tab-aws-training", children=[
                            render_aws_training_tab()
                        ]),
                        dbc.Tab(label="Azure Training", tab_id="tab-azure-training", children=[
                            render_azure_training_tab()
                        ]),
                        dbc.Tab(label="Juegos", tab_id="tab-games", children=[
                            render_games_tab()
                        ]),
                        dbc.Tab(label="AllKeyShop Deals", tab_id="tab-aks", children=[
                            render_allkeyshop_tab()
                        ]),
                        dbc.Tab(label="Cursos", tab_id="tab-courses", children=[
                            render_courses_tab()
                        ]),
                        dbc.Tab(label="Eventos Tech", tab_id="tab-tech-events", children=[
                            render_tech_events_tab()
                        ]),
                        dbc.Tab(label="Comunidades Dev", tab_id="tab-dev-communities", children=[
                            render_dev_communities_tab()
                        ]),
                        dbc.Tab(label="Seguridad", tab_id="tab-security", children=[
                            render_security_tab()
                        ]),
                        dbc.Tab(label="Innovación", tab_id="tab-innovation", children=[
                            render_innovation_tab()
                        ]),
                        dbc.Tab(label="Plataformas IA", tab_id="tab-ai-platforms", children=[
                            render_ai_platforms_tab()
                        ]),
                        dbc.Tab(label="Home Server", tab_id="tab-home-server", children=[
                            render_home_server_tab() # Content from home_server_tab.py
                        ]),
                        dbc.Tab(label="Other Tab (Placeholder)", tab_id="tab-other", children=[
                            html.P("This is content for another future tab.")
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
register_allkeyshop_callbacks(app)
register_courses_callbacks(app)
register_tech_events_callbacks(app)
register_dev_communities_callbacks(app)
register_security_callbacks(app)
register_innovation_callbacks(app)
register_ai_platforms_callbacks(app)
register_home_server_callbacks(app) # Register Home Server tab callbacks

if __name__ == "__main__":
    # Note on data loading:
    # - Shortcuts data (ALL_SHORTCUTS_DATA) is loaded when shortcuts_tab.py is imported.
    # - News data (ALL_NEWS_DATA) is loaded when news_tab.py is imported.
    # - Videos data (ALL_VIDEOS_DATA) is loaded when videos_tab.py is imported.
    # These imports happen when app.py itself is imported (e.g., by run_new_dashboard_poc.py).
    # The relative paths within each component (e.g., '../../../data/...') are resolved
    # based on the Current Working Directory (CWD) when the Python interpreter loads those modules.
    # If run_new_dashboard_poc.py is at project root, CWD is project root, so paths should be correct.

    print("Verifying data loaded for main app context (run from app.py directly):")
    # Simple check, more detailed checks are in individual tab's __main__ blocks
    if ALL_SHORTCUTS_DATA:
        print("  Shortcuts data seems loaded.")
    else:
        print("  Warning: Shortcuts data might be missing.")

    # Accessing ALL_NEWS_DATA and ALL_VIDEOS_DATA directly here would require importing them into app.py
    # For now, we assume their respective tabs handle their data loading messages.
    # If this script (app.py) is run directly, ensure CWD allows components to find their data.
    # Typically, one would run `run_new_dashboard_poc.py` from the project root.

    app.run_server(debug=True, port=8050) # Default Dash port for direct app run
