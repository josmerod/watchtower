"""Items Per Page Selector Component
Reusable component for selecting items per page in dashboard tabs
"""

import dash_bootstrap_components as dbc
from dash import Input, Output, clientside_callback, dcc, html


def create_items_per_page_selector(tab_name, default_value=48):
    """Create an items-per-page selector component for a specific tab

    Args:
        tab_name (str): The name of the tab (e.g., 'videos', 'arxiv')
        default_value (int): Default items per page value

    Returns:
        dbc.Col: A Bootstrap column containing the selector
    """
    selector_id = f"{tab_name}-items-per-page-select"

    # Options for items per page
    options = [
        {"label": "12 items", "value": 12},
        {"label": "24 items", "value": 24},
        {"label": "48 items", "value": 48},
        {"label": "96 items", "value": 96},
    ]

    return dbc.Col(
        [
            html.Label("Items per page:", className="form-label small"),
            dcc.Dropdown(
                id=selector_id,
                options=options,
                value=default_value,
                clearable=False,
                className="mb-3 form-select form-select-sm",
                style={"minWidth": "120px"},
            ),
        ],
        width=12,
        md=2,
        lg=2,
    )


def register_items_per_page_callback(tab_name):
    """Register a clientside callback for items-per-page preference saving

    Args:
        tab_name (str): The name of the tab
    """
    selector_id = f"{tab_name}-items-per-page-select"

    # Client-side callback to save preference to localStorage
    clientside_callback(
        """
        function(itemsPerPage) {
            // Save preference to localStorage using ItemsPerPageManager
            if (typeof window.itemsPerPageManager !== 'undefined') {
                window.itemsPerPageManager.applyPreference(
                    '%(tab_name)s',
                    itemsPerPage,
                    function(tab, value) {
                        console.log(`Items per page updated for ${tab}: ${value}`);
                        // Trigger a content refresh if needed
                        if (typeof window.refreshTabContent === 'function') {
                            window.refreshTabContent(tab, value);
                        }
                    }
                );
            }
            return itemsPerPage;
        }
        """
        % {"tab_name": tab_name},
        Output(selector_id, "value"),
        Input(selector_id, "value"),
        prevent_initial_call=True,
    )


def load_initial_preference(tab_name):
    """Generate JavaScript to load initial preference from localStorage

    Args:
        tab_name (str): The name of the tab

    Returns:
        str: JavaScript code snippet
    """
    return f"""
        // Load initial items-per-page preference for {tab_name}
        if (typeof window.itemsPerPageManager !== 'undefined') {{
            const initialPreference = window.itemsPerPageManager.getPreference('{tab_name}');
            const selector = document.getElementById('{tab_name}-items-per-page-select');
            if (selector && selector.querySelector('select')) {{
                selector.querySelector('select').value = initialPreference;
            }}
            console.log(`Loaded initial preference for {tab_name}: ${{initialPreference}}`);
        }}
    """


def create_items_per_page_script(tab_names):
    """Create a script to initialize all items-per-page selectors

    Args:
        tab_names (list): List of tab names to initialize

    Returns:
        html.Script: Script element for initialization
    """
    init_code = """
        // Initialize items-per-page selectors for all tabs
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                %s
            }, 100); // Small delay to ensure Dash components are rendered
        });
    """

    tab_initializations = []
    for tab_name in tab_names:
        tab_initializations.append(load_initial_preference(tab_name))

    return html.Script(init_code % "\n                ".join(tab_initializations))
