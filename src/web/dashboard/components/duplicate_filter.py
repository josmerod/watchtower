"""Duplicate filter component for dashboard tabs.

Reusable component for filtering and showing duplicate content across all tabs.
"""

import dash
from dash import Input, Output, State, dcc, html

from ..deduplication_utils import create_show_duplicates_button, get_duplicate_summary


def create_duplicate_filter_component(component_id: str, data_store_id: str, data_name: str = "items"):
    """Create a duplicate filter component for a tab.

    Args:
        component_id: Base ID for the component (e.g., "arxiv", "news").
        data_store_id: ID of the dcc.Store that holds the tab data.
        data_name: Name of the data for display purposes (e.g., "papers", "articles").

    Returns:
        List of Dash components for the duplicate filter.
    """
    return [
        html.Div(
            [
                html.Div(
                    [
                        # Duplicate filter controls
                        html.Div(
                            [
                                html.Div(
                                    id=f"{component_id}-duplicate-controls",
                                    children=[
                                        # Button will be populated by callback
                                    ],
                                    className="d-flex align-items-center",
                                ),
                                html.Div(id=f"{component_id}-duplicate-summary", className="text-muted small ms-3"),
                            ],
                            className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom",
                        )
                    ]
                ),
            ]
        ),
        # Hidden div to store current show_duplicates state
        dcc.Store(id=f"{component_id}-show-duplicates", data=False),
        # Store for duplicate statistics
        dcc.Store(id=f"{component_id}-duplicate-stats"),
    ]


def register_duplicate_filter_callback(component_id: str, data_store_id: str, data_name: str = "items"):
    """Register callbacks for the duplicate filter component.

    Args:
        component_id: Base ID for the component.
        data_store_id: ID of the dcc.Store that holds the tab data.
        data_name: Name of the data for display purposes.
    """
    app = dash.get_app()

    # Callback to update duplicate controls and summary
    @app.callback(
        [Output(f"{component_id}-duplicate-controls", "children"), Output(f"{component_id}-duplicate-summary", "children"), Output(f"{component_id}-duplicate-stats", "data")],
        [Input(data_store_id, "data"), Input(f"{component_id}-show-duplicates", "data")],
        prevent_initial_call=False,
    )
    def update_duplicate_controls(data, show_duplicates):
        """Update duplicate controls and summary based on current data."""
        if not data:
            return [], "", None

        try:
            # Get duplicate summary
            summary = get_duplicate_summary(data)

            # Create show/hide duplicates button
            button = create_show_duplicates_button(button_id=f"{component_id}-toggle-duplicates", data=data, current_show_duplicates=show_duplicates)

            # Create summary text
            if summary["duplicate_items"] > 0:
                summary_text = f"Showing {summary['unique_items']} {data_name} ({summary['duplicate_items']} duplicates hidden in {summary['duplicate_groups']} groups)"
            else:
                summary_text = f"Showing {summary['unique_items']} {data_name} (no duplicates)"

            return [button], summary_text, summary

        except Exception:
            return [], "Error loading duplicate information", None

    # Callback to toggle show/hide duplicates
    @app.callback(Output(f"{component_id}-show-duplicates", "data"), Input(f"{component_id}-toggle-duplicates", "n_clicks"), State(f"{component_id}-show-duplicates", "data"), prevent_initial_call=True)
    def toggle_duplicates(n_clicks, current_show_duplicates):
        """Toggle the show duplicates state."""
        if n_clicks:
            return not current_show_duplicates
        return current_show_duplicates


def get_filtered_data_callback_id(component_id: str) -> str:
    """Get the callback ID for filtered data.

    Args:
        component_id: Base ID for the component.

    Returns:
        String callback ID for the filtered data output.
    """
    return f"{component_id}-filtered-data"


def register_filtered_data_callback(component_id: str, data_store_id: str, target_output: tuple):
    """Register callback to provide filtered data to tab components.

    Args:
        component_id: Base ID for the component.
        data_store_id: ID of the dcc.Store that holds the tab data.
        target_output: Tuple of (output_id, output_property) for the filtered data.
    """
    app = dash.get_app()

    @app.callback(target_output, [Input(data_store_id, "data"), Input(f"{component_id}-show-duplicates", "data")], prevent_initial_call=False)
    def provide_filtered_data(data, show_duplicates):
        """Provide filtered data based on duplicate settings."""
        from ..deduplication_utils import filter_duplicates

        if not data:
            return []

        try:
            filtered_data = filter_duplicates(data, show_duplicates or False)
            return filtered_data
        except Exception:
            return []


# Example usage in a tab component:
# Example usage in a tab component:
# from .duplicate_filter import (
#     create_duplicate_filter_component,
#     register_duplicate_filter_callback,
#     register_filtered_data_callback,
#     get_filtered_data_callback_id
# )
#
# def create_layout():
#     return html.Div([
#         # Add duplicate filter component
#         *create_duplicate_filter_component("arxiv", "arxiv-data-store", "papers"),

#         # Other tab content...
#     ])


# def register_callbacks():
#     # Register duplicate filter callbacks
#     register_duplicate_filter_callback("arxiv", "arxiv-data-store", "papers")
#
#     # Register filtered data callback for your display component
#     register_filtered_data_callback(
#         "arxiv",
#         "arxiv-data-store",
#         (get_filtered_data_callback_id("arxiv"), "data")
#     )
#
#     # Use the filtered data in your display callbacks
#     @app.callback(
#         Output("arxiv-content", "children"),
#         Input(get_filtered_data_callback_id("arxiv"), "data")
#     )
#     def update_content(filtered_data):
#         # Display the filtered data
#         return create_content_cards(filtered_data)
# """
