import json

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, html

# Import shared utilities
from src.web.dashboard.utils import get_data_path


def create_shortcut_button(shortcut_info):
    """Creates a Bootstrap button for a shortcut."""
    return dbc.Col(
        html.A(
            shortcut_info["name"],
            href=shortcut_info["url"],
            target="_blank",  # Open in new tab
            className="btn btn-outline-primary m-1",  # Bootstrap button styling
        ),
        width="auto",  # Adjust column width to content
    )


def create_category_card(category_name, shortcuts_list, search_term=""):
    """Creates a Bootstrap Card for a category of shortcuts."""
    if search_term:
        shortcuts_list = [
            s for s in shortcuts_list if search_term.lower() in s["name"].lower() or search_term.lower() in s["url"].lower() or (s.get("description") and search_term.lower() in s["description"].lower())
        ]

    if not shortcuts_list:  # If no shortcuts match search, don't render the card for this category
        return None

    return dbc.Card(
        [
            dbc.CardHeader(html.H5(category_name, className="mb-0")),  # Use H5 for category titles
            dbc.CardBody(
                dbc.Row(
                    [create_shortcut_button(s) for s in shortcuts_list],
                    className="g-2",  # Add gutters between columns
                )
            ),
        ],
        className="mb-3",  # Margin bottom for spacing between cards
    )


def render_shortcuts_tab_layout(shortcuts_data, search_term=""):
    """Renders the full layout for the shortcuts tab based on data and search term."""
    if not shortcuts_data:
        return html.Div(dbc.Alert("No shortcut data loaded or available.", color="warning"))

    cards = []
    for category, shortcut_items in shortcuts_data.items():
        card = create_category_card(category, shortcut_items, search_term)
        if card:
            cards.append(card)

    if not cards and search_term:  # If search yielded no results in any category
        return html.Div(dbc.Alert(f"No shortcuts found matching '{search_term}'.", color="info"))

    return html.Div(cards)


def render_shortcuts_tab():
    """Main function to create the shortcuts tab layout.
    This is what will be imported by the main app.
    It sets up the static parts of the layout and the container for dynamic content.
    """
    return html.Div(
        [
            # Search Input
            dbc.Input(
                id="search-shortcuts-input",
                placeholder="Search shortcuts by name, URL, or description...",
                type="text",
                className="mb-3",
                value="",  # Initial value
            ),
            # Container for dynamically filtered shortcuts
            html.Div(
                id="shortcuts-cards-container",
                children=render_shortcuts_tab_layout(get_shortcuts_data()),
            ),
        ]
    )


# Callback to update shortcuts based on search
# This needs the 'app' instance, so it will be defined in app.py or a dedicated callbacks file
# For now, the structure is prepared here.

# def register_shortcuts_callbacks(app):
#     @app.callback(
#         Output("shortcuts-cards-container", "children"),
#         [Input("search-shortcuts-input", "value")]
#     )
#     def update_filtered_shortcuts(search_value):
#         return render_shortcuts_tab_layout(ALL_SHORTCUTS_DATA, search_value)


def load_shortcuts_from_file(file_path):
    """Loads shortcuts from a JSON file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Shortcut file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {file_path}")
        return []
    except UnicodeDecodeError:
        print(f"Warning: Could not decode file encoding from {file_path}")
        return []


def get_all_shortcuts():
    """Loads shortcuts from predefined and custom files."""
    predefined_path = get_data_path("shortcuts", "predefined_shortcuts.json")
    custom_path = get_data_path("shortcuts", "custom_shortcuts.json")

    predefined_shortcuts = load_shortcuts_from_file(predefined_path)
    custom_shortcuts = load_shortcuts_from_file(custom_path)

    # Initialize the final shortcuts dictionary
    shortcuts_by_category = {}

    # Process predefined shortcuts
    if isinstance(predefined_shortcuts, dict):
        if "categories" in predefined_shortcuts:
            # Old format: {"categories": [{"category": "name", "items": [...]}]}
            for category_data in predefined_shortcuts["categories"]:
                category_name = category_data.get("category", "Uncategorized")
                items = category_data.get("items", [])
                if category_name not in shortcuts_by_category:
                    shortcuts_by_category[category_name] = []
                shortcuts_by_category[category_name].extend(items)
        else:
            # New format: {"Category Name": [{"name": "...", "url": "..."}]}
            for category_name, items in predefined_shortcuts.items():
                if category_name not in shortcuts_by_category:
                    shortcuts_by_category[category_name] = []
                shortcuts_by_category[category_name].extend(items)
    elif isinstance(predefined_shortcuts, list):
        # List of category objects
        for category_data in predefined_shortcuts:
            category_name = category_data.get("category", "Uncategorized")
            items = category_data.get("items", [])
            if category_name not in shortcuts_by_category:
                shortcuts_by_category[category_name] = []
            shortcuts_by_category[category_name].extend(items)

    # Process custom shortcuts (same logic)
    if isinstance(custom_shortcuts, dict):
        if "categories" in custom_shortcuts:
            # Old format: {"categories": [{"category": "name", "items": [...]}]}
            for category_data in custom_shortcuts["categories"]:
                category_name = category_data.get("category", "Uncategorized")
                items = category_data.get("items", [])
                if category_name not in shortcuts_by_category:
                    shortcuts_by_category[category_name] = []
                shortcuts_by_category[category_name].extend(items)
        else:
            # New format: {"Category Name": [{"name": "...", "url": "..."}]}
            for category_name, items in custom_shortcuts.items():
                if category_name not in shortcuts_by_category:
                    shortcuts_by_category[category_name] = []
                shortcuts_by_category[category_name].extend(items)
    elif isinstance(custom_shortcuts, list):
        # List of category objects
        for category_data in custom_shortcuts:
            category_name = category_data.get("category", "Uncategorized")
            items = category_data.get("items", [])
            if category_name not in shortcuts_by_category:
                shortcuts_by_category[category_name] = []
            shortcuts_by_category[category_name].extend(items)

    return shortcuts_by_category


# Load data dynamically instead of at import time
def get_shortcuts_data():
    """Get fresh shortcuts data."""
    return get_all_shortcuts()


# Test data loading (can be removed or commented out later)
# if __name__ == '__main__':
#     all_shortcuts_data = get_all_shortcuts()
#     if all_shortcuts_data:
#         print(f"Successfully loaded {sum(len(items) for items in all_shortcuts_data.values())} shortcuts in {len(all_shortcuts_data)} categories.")
#         # print(json.dumps(all_shortcuts_data, indent=2))
#     else:
#         print("No shortcut data loaded.")

if __name__ == "__main__":
    # This part is for testing the component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    ALL_SHORTCUTS_DATA = get_all_shortcuts()

    # The render_shortcuts_tab now produces the full initial layout including the search bar
    app_test.layout = dbc.Container(
        [
            html.H1("Shortcuts Tab Test (Standalone)"),
            render_shortcuts_tab(),  # This will include the search input and initial full list
        ]
    )

    # Define the callback for the standalone test app_test
    @app_test.callback(
        Output("shortcuts-cards-container", "children"),  # Target the container within the rendered layout
        [Input("search-shortcuts-input", "value")],  # Source from the input within the rendered layout
    )
    def update_shortcuts_for_test(search_value):
        # ALL_SHORTCUTS_DATA is loaded when the module is imported
        return render_shortcuts_tab_layout(ALL_SHORTCUTS_DATA, search_value)

    print("Running standalone test for shortcuts_tab.py...")
    print("Expected predefined: ../../../data/shortcuts/predefined_shortcuts.json")
    print("Expected custom: ../../../data/shortcuts/custom_shortcuts.json (optional)")
    print("If paths are incorrect, data loading will fail and be reported in console/layout.")
    app_test.run_server(debug=True, port=8051)
