"""Filter Presets Component - Reusable filter preset functionality for dashboard tabs
Provides localStorage-based filter preset management with Dash integration
"""

import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html
from dash.development.base_component import Component

logger = logging.getLogger(__name__)


class FilterPresetsComponent:
    """Reusable component for filter preset management in dashboard tabs"""

    def __init__(self, tab_name: str, filter_inputs: dict[str, str]):
        """Initialize filter presets component.

        Args:
            tab_name: Name of the tab (used for localStorage key)
            filter_inputs: Dict mapping filter names to their component IDs
        """
        self.tab_name = tab_name
        self.filter_inputs = filter_inputs
        self.storage_prefix = f"filter_presets_{tab_name}"

    def create_preset_controls(self) -> list[Component]:
        """Create preset control components (dropdown, buttons, modal).

        Returns:
            List of Dash components for preset management
        """
        # Preset selector dropdown
        preset_selector = dbc.Select(
            id=f"{self.storage_prefix}_preset_selector",
            placeholder="Select saved preset...",
            className="mb-2",
        )

        # Preset action buttons
        preset_buttons = html.Div(
            [
                dbc.Button(
                    "Save Current Filters",
                    id=f"{self.storage_prefix}_save_preset_btn",
                    color="primary",
                    size="sm",
                    className="me-2",
                ),
                dbc.Button(
                    "Update Preset",
                    id=f"{self.storage_prefix}_update_preset_btn",
                    color="warning",
                    size="sm",
                    className="me-2",
                    style={"display": "none"},
                ),
                dbc.Button(
                    "Delete Preset",
                    id=f"{self.storage_prefix}_delete_preset_btn",
                    color="danger",
                    size="sm",
                    style={"display": "none"},
                ),
            ],
            className="d-flex gap-2 mb-2",
        )

        # Preset save modal
        save_modal = dbc.Modal(
            [
                dbc.ModalHeader("Save Filter Preset"),
                dbc.ModalBody(
                    [
                        dbc.Label("Preset Name:"),
                        dbc.Input(
                            id=f"{self.storage_prefix}_preset_name_input",
                            placeholder="Enter preset name...",
                            maxLength=50,
                        ),
                        html.Div(
                            id=f"{self.storage_prefix}_preset_error",
                            className="text-danger mt-2",
                            style={"display": "none"},
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            "Cancel",
                            id=f"{self.storage_prefix}_cancel_save_btn",
                            color="secondary",
                        ),
                        dbc.Button(
                            "Save",
                            id=f"{self.storage_prefix}_confirm_save_btn",
                            color="primary",
                        ),
                    ]
                ),
            ],
            id=f"{self.storage_prefix}_save_modal",
            is_open=False,
        )

        # Hidden storage for current filters
        filters_store = dcc.Store(id=f"{self.storage_prefix}_current_filters", data={})

        # Hidden storage for selected preset
        selected_preset_store = dcc.Store(id=f"{self.storage_prefix}_selected_preset", data={})

        return [
            preset_selector,
            preset_buttons,
            save_modal,
            filters_store,
            selected_preset_store,
        ]

    def create_callbacks(self, app: dash.Dash) -> None:
        """Create Dash callbacks for preset functionality.

        Args:
            app: Dash application instance
        """

        # Save current filters to store
        @app.callback(
            Output(f"{self.storage_prefix}_current_filters", "data"),
            [Input(filter_id, "value") for filter_id in self.filter_inputs.values()],
        )
        def update_current_filters(*filter_values):
            """Update stored current filter values"""
            current_filters = {}

            for filter_name, filter_id in self.filter_inputs.items():
                filter_index = list(self.filter_inputs.values()).index(filter_id)
                if filter_index < len(filter_values):
                    current_filters[filter_name] = filter_values[filter_index]

            return current_filters

        # Open save modal
        @app.callback(
            Output(f"{self.storage_prefix}_save_modal", "is_open"),
            [
                Input(f"{self.storage_prefix}_save_preset_btn", "n_clicks"),
                Input(f"{self.storage_prefix}_cancel_save_btn", "n_clicks"),
                Input(f"{self.storage_prefix}_confirm_save_btn", "n_clicks"),
            ],
            [
                State(f"{self.storage_prefix}_save_modal", "is_open"),
                State(f"{self.storage_prefix}_preset_name_input", "value"),
                State(f"{self.storage_prefix}_current_filters", "data"),
            ],
        )
        def handle_save_modal(
            save_clicks,
            cancel_clicks,
            confirm_clicks,
            is_open,
            preset_name,
            current_filters,
        ):
            """Handle preset save modal"""
            ctx = dash.callback_context
            if not ctx.triggered:
                return False

            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

            if trigger_id == f"{self.storage_prefix}_save_preset_btn":
                # Open modal
                return True

            if trigger_id == f"{self.storage_prefix}_cancel_save_btn":
                # Close modal
                return False

            if trigger_id == f"{self.storage_prefix}_confirm_save_btn":
                # Save preset (this would be handled by clientside callback)
                return False

            return is_open

        # Apply selected preset
        @app.callback(
            [Output(filter_id, "value") for filter_id in self.filter_inputs.values()],
            [Input(f"{self.storage_prefix}_preset_selector", "value")],
            [State(f"{self.storage_prefix}_selected_preset", "data")],
        )
        def apply_preset(selected_preset_name, selected_preset_data):
            """Apply selected preset to filter inputs"""
            if not selected_preset_name or not selected_preset_data:
                # Return list of None values (no change to filters)
                return [None] * len(self.filter_inputs)

            # Extract filter values from preset data
            filter_values = []
            for filter_name in self.filter_inputs:
                filter_values.append(selected_preset_data.get("filters", {}).get(filter_name))

            return filter_values

        # Delete preset
        @app.callback(
            Output(f"{self.storage_prefix}_preset_selector", "value", allow_duplicate=True),
            [Input(f"{self.storage_prefix}_delete_preset_btn", "n_clicks")],
            prevent_initial_call=True,
        )
        def delete_preset(n_clicks):
            """Delete selected preset"""
            if n_clicks:
                return None
            return dash.no_update

        # Update preset
        @app.callback(
            Output(f"{self.storage_prefix}_save_modal", "is_open", allow_duplicate=True),
            [Input(f"{self.storage_prefix}_update_preset_btn", "n_clicks")],
            prevent_initial_call=True,
        )
        def update_preset(n_clicks):
            """Open modal for updating preset"""
            if n_clicks:
                return True
            return dash.no_update

    def get_clientside_callbacks(self) -> dict[str, str]:
        """Generate clientside callbacks for localStorage operations.

        Returns:
            Dict mapping callback names to JavaScript code
        """
        callbacks = {}

        # Load presets callback
        callbacks["load_presets"] = f"""
            function() {{
                try {{
                    const storageKey = 'watchtower_filter_presets';
                    const stored = localStorage.getItem(storageKey);
                    const presets = stored ? JSON.parse(stored) : {{}};
                    const tabPresets = presets['{self.tab_name}'] || [];

                    return tabPresets.map(preset => ({{
                        label: preset.name,
                        value: preset.name
                    }}));
                }} catch (error) {{
                    console.error('Error loading presets:', error);
                    return [];
                }}
            }}
        """

        # Save preset callback
        callbacks["save_preset"] = f"""
            function(presetName, currentFilters) {{
                try {{
                    const storageKey = 'watchtower_filter_presets';
                    const stored = localStorage.getItem(storageKey);
                    const presets = stored ? JSON.parse(stored) : {{}};

                    // Initialize tab if not exists
                    if (!presets['{self.tab_name}']) {{
                        presets['{self.tab_name}'] = [];
                    }}

                    // Check maximum presets limit
                    if (presets['{self.tab_name}'].length >= 10) {{
                        return {{success: false, message: 'Maximum 10 presets allowed per tab'}};
                    }}

                    // Check for duplicate names
                    const existingIndex = presets['{self.tab_name}'].findIndex(p => p.name === presetName);
                    if (existingIndex !== -1) {{
                        return {{success: false, message: 'Preset name already exists'}};
                    }}

                    // Add new preset
                    const newPreset = {{
                        name: presetName,
                        filters: currentFilters,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    }};

                    presets['{self.tab_name}'].push(newPreset);
                    localStorage.setItem(storageKey, JSON.stringify(presets));

                    return {{success: true, message: 'Preset saved successfully'}};
                }} catch (error) {{
                    return {{success: false, message: error.message}};
                }}
            }}
        """

        # Delete preset callback
        callbacks["delete_preset"] = f"""
            function(presetName) {{
                try {{
                    const storageKey = 'watchtower_filter_presets';
                    const stored = localStorage.getItem(storageKey);
                    const presets = stored ? JSON.parse(stored) : {{}};

                    if (!presets['{self.tab_name}']) {{
                        return {{success: false, message: 'No presets found for this tab'}};
                    }}

                    const originalLength = presets['{self.tab_name}'].length;
                    presets['{self.tab_name}'] = presets['{self.tab_name}'].filter(p => p.name !== presetName);

                    if (presets['{self.tab_name}'].length === originalLength) {{
                        return {{success: false, message: 'Preset not found'}};
                    }}

                    localStorage.setItem(storageKey, JSON.stringify(presets));
                    return {{success: true, message: 'Preset deleted successfully'}};
                }} catch (error) {{
                    return {{success: false, message: error.message}};
                }}
            }}
        """

        return callbacks
