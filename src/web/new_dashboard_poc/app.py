import dash
import dash_bootstrap_components as dbc
from dash import (  # Added Input, Output, dcc for Tabs and callback
    Input,
    Output,
    html,
)

from src.web.new_dashboard_poc.components.news_tab import render_news_tab
from src.web.new_dashboard_poc.components.shortcuts_tab import (
    ALL_SHORTCUTS_DATA,
    render_shortcuts_tab,
    render_shortcuts_tab_layout,
)

# Initialize the Dash application with Bootstrap styling
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Main layout with Tabs
app.layout = dbc.Container(
    [
        dbc.Row(dbc.Col(html.H1("New Dashboard POC", className="text-center my-4"))),
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
                            children=[
                                render_news_tab()  # Content from news_tab.py
                            ],
                        ),
                        dbc.Tab(
                            label="Other Tab (Placeholder)",
                            tab_id="tab-other",
                            children=[
                                html.P("This is content for another future tab.")
                            ],
                        ),
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
    Output("shortcuts-cards-container", "children"),  # This ID is in shortcuts_tab.py
    [Input("search-shortcuts-input", "value")],  # This ID is in shortcuts_tab.py
)
def update_main_app_shortcuts(search_value):
    # Reuse the layout rendering function from shortcuts_tab.py
    # ALL_SHORTCUTS_DATA is imported from shortcuts_tab.py
    return render_shortcuts_tab_layout(ALL_SHORTCUTS_DATA, search_value)


if __name__ == "__main__":
    # Note: The `get_all_shortcuts` function in `shortcuts_tab.py` uses relative paths
    # like '../../../data/shortcuts/predefined_shortcuts.json'.
    # This assumes that `app.py` (or wherever the main app is run from) is located
    # such that these relative paths correctly point to the data files.
    # If app.py is in src/web/new_dashboard_poc/, then ../../../data/ is correct.
    # Project Root
    # |- data/
    #    |- shortcuts/
    #       |- predefined_shortcuts.json
    # |- src/
    #    |- web/
    #       |- new_dashboard_poc/
    #          |- app.py  <-- Running this
    #          |- components/
    #             |- shortcuts_tab.py (contains the relative path logic)
    print("Verifying ALL_SHORTCUTS_DATA in app.py context:")
    if ALL_SHORTCUTS_DATA:
        print(
            f"  Successfully loaded {sum(len(items) for items in ALL_SHORTCUTS_DATA.values())} shortcuts in {len(ALL_SHORTCUTS_DATA)} categories."
        )
    else:
        print(
            "  Warning: No shortcut data loaded in app.py context. Check paths in shortcuts_tab.py relative to project root."
        )
    app.run(debug=True)
