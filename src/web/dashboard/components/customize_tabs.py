"""
Customize Tabs Component
Provides modal interface for customizing dashboard tab visibility and order
"""

import dash
from dash import html, dcc, callback, Input, Output, State, clientside_callback
import dash_bootstrap_components as dbc
import uuid
from typing import Dict, List, Any


class CustomizeTabs:
    """Manages the customize tabs modal component"""

    def __init__(self):
        self.modal_id = f"customize-tabs-modal-{uuid.uuid4().hex[:8]}"
        self.toggle_button_id = f"customize-tabs-btn-{uuid.uuid4().hex[:8]}"
        self.save_btn_id = f"save-tabs-btn-{uuid.uuid4().hex[:8]}"
        self.reset_btn_id = f"reset-tabs-btn-{uuid.uuid4().hex[:8]}"
        self.cancel_btn_id = f"cancel-tabs-btn-{uuid.uuid4().hex[:8]}"
        self.tabs_container_id = f"tabs-container-{uuid.uuid4().hex[:8]}"
        self.stats_id = f"customize-tabs-stats-{uuid.uuid4().hex[:8]}"
        self.domain_prefix = "customize-tab-"

    def create_toggle_button(self):
        """Create the customize tabs toggle button"""
        return dbc.Button(
            [
                html.I(className="fas fa-sliders-h me-2"),
                "Customize Tabs",
            ],
            id=self.toggle_button_id,
            color="outline-secondary",
            size="sm",
            className="me-2",
            n_clicks=0,
            title="Customize which tabs appear and their order"
        )

    def create_modal(self):
        """Create the customize tabs modal"""
        return dbc.Modal(
            [
                dbc.ModalHeader(
                    [
                        html.I(className="fas fa-sliders-h me-2"),
                        "Customize Dashboard Tabs"
                    ],
                    close_button=True,
                    className="border-bottom"
                ),
                dbc.ModalBody(
                    [
                        # Instructions
                        dbc.Alert(
                            [
                                html.H6("How to customize your dashboard:", className="alert-heading mb-2"),
                                html.Ul(
                                    [
                                        html.Li("Toggle the switch next to each tab to show or hide it"),
                                        html.Li("Drag tabs up or down to reorder them"),
                                        html.Li("Click 'Save' to apply changes immediately"),
                                        html.Li("Use 'Reset' to restore default settings")
                                    ],
                                    className="mb-0"
                                ),
                            ],
                            color="info",
                            className="mb-3"
                        ),

                        # Statistics
                        html.Div(
                            id=self.stats_id,
                            className="text-center text-muted mb-3",
                            children=["Loading tab statistics..."]
                        ),

                        # Tabs container for reordering
                        html.Div(
                            id=self.tabs_container_id,
                            children=[
                                # Loading placeholder
                                dbc.Spinner(size="sm", spinner_class_name="d-block"),
                                html.Small("Loading tab options...")
                            ]
                        ),

                        # Action buttons
                        html.Div(
                            [
                                dbc.Button(
                                    "Reset to Default",
                                    id=self.reset_btn_id,
                                    color="outline-warning",
                                    size="sm",
                                    className="me-2"
                                ),
                                dbc.Button(
                                    "Cancel",
                                    id=self.cancel_btn_id,
                                    color="outline-secondary",
                                    size="sm",
                                    className="me-2"
                                ),
                                dbc.Button(
                                    "Save Changes",
                                    id=self.save_btn_id,
                                    color="primary",
                                    size="sm"
                                )
                            ],
                            className="d-flex justify-content-end mt-4"
                        )
                    ],
                    className="p-0"
                )
            ],
            id=self.modal_id,
            size="lg",  # Large modal for better tab management
            is_open=False,
            scrollable=True,
            backdrop=True,
            keyboard=True
        )

    def create_tab_item(self, tab_info: Dict[str, Any], is_visible: bool, index: int) -> html.Div:
        """Create a single tab item for the customization interface"""
        tab_id = tab_info.get('id', '')
        tab_label = tab_info.get('label', 'Unknown Tab')
        tab_icon = tab_info.get('icon', 'fa-tab')

        return html.Div(
            [
                # Drag handle
                html.Div(
                    [
                        html.I(className="fas fa-grip-vertical me-2 text-muted"),
                        f"{index + 1}."
                    ],
                    className="d-flex align-items-center me-3",
                    style={"cursor": "grab", "userSelect": "none"}
                ),

                # Tab info
                html.Div(
                    [
                        html.I(className=f"fas {tab_icon} me-2 text-muted"),
                        html.Span(tab_label, className="fw-medium")
                    ],
                    className="flex-grow-1"
                ),

                # Visibility toggle
                dbc.Switch(
                    id=f"{self.domain_prefix}{tab_id}-visibility",
                    label="",
                    value=is_visible,
                    className="ms-auto",
                    size="sm"
                )
            ],
            className=[
                "d-flex",
                "align-items-center",
                "p-3",
                "mb-2",
                "bg-light",
                "rounded",
                "border",
                "customize-tab-item"
            ],
            **{
                "data-tab-id": tab_id,
                "data-tab-index": str(index)
            }
        )

    def get_layout(self) -> html.Div:
        """Get the complete customize tabs layout"""
        return html.Div([
            # Toggle button (placed in main layout)
            self.create_toggle_button(),

            # Modal component
            self.create_modal(),

            # Hidden div for triggering updates
            html.Div(id="customize-tabs-trigger", style={"display": "none"}),

            # Store for clientside callbacks
            dcc.Store(id="customize-tabs-data-store", data={}),
        ])


# Instantiate component
customize_tabs = CustomizeTabs()


# Clientside callback to toggle modal and trigger data loading
clientside_callback(
    """
    function(n_clicks, is_open) {
        // If opening the modal, trigger data loading
        if (!is_open && n_clicks > 0) {
            setTimeout(() => {
                const trigger = document.getElementById('customize-tabs-trigger');
                if (trigger) {
                    trigger.innerHTML = Date.now().toString();
                }
            }, 100);
        }
        return !is_open;
    }
    """,
    Output(f"{customize_tabs.modal_id}", "is_open", allow_duplicate=True),
    Input(f"{customize_tabs.toggle_button_id}", "n_clicks"),
    State(f"{customize_tabs.modal_id}", "is_open"),
    prevent_initial_call=True
)


# Clientside callback to load tabs into customization modal
clientside_callback(
    """
    function(trigger) {
        try {
            const tabManager = window.tabPreferencesManager;
            if (!tabManager) {
                console.error('TabPreferencesManager not available');
                return [];
            }

            const allTabs = tabManager.defaultTabs;
            const visibility = tabManager.getVisibility();
            const order = tabManager.getOrder();

            // Update stats
            const statsDiv = document.getElementById('%(stats_id)s');
            if (statsDiv) {
                const totalTabs = allTabs.length;
                const visibleCount = tabManager.getVisibleTabCount();
                statsDiv.innerHTML = `
                    <strong>${visibleCount}</strong> of ${totalTabs} tabs visible
                `;
            }

            // Generate tab items in order
            const tabItems = allTabs.map((tab, index) => {
                const isVisible = visibility[tab.id] || false;
                const orderIndex = order.indexOf(tab.id);
                return {
                    tab_id: tab.id,
                    tab_label: tab.label,
                    tab_icon: tab.icon,
                    is_visible: isVisible,
                    index: orderIndex >= 0 ? orderIndex : 999
                };
            }).sort((a, b) => a.index - b.index);

            return tabItems;

        } catch (error) {
            console.error('Error loading tabs for customization:', error);
            return [];
        }
    }
    """ % {"stats_id": customize_tabs.stats_id},
    Output("customize-tabs-data-store", "data"),
    Input("customize-tabs-trigger", "children"),
    prevent_initial_call=True
)


# Callback to render tabs in modal
@dash.callback(
    Output(f"{customize_tabs.tabs_container_id}", "children"),
    Input("customize-tabs-data-store", "data"),
    prevent_initial_call=True,
)
def render_customize_tabs(tab_data: List[Dict[str, Any]]):
    """Render customization tabs from data"""
    if not tab_data:
        return html.Div([
            dbc.Spinner(size="sm", spinner_class_name="d-block mx-auto"),
            html.Small("No tab data available")
        ])

    return [
        customize_tabs.create_tab_item(
            tab_info=item,
            is_visible=item.get('is_visible', False),
            index=item.get('index', 0)
        )
        for item in tab_data
    ]


# Save preferences functionality
clientside_callback(
    """
    function(save_clicks, cancel_clicks, reset_clicks, is_open, trigger) {
        const ctx = window.dash_clientside.callback_context;

        if (!ctx || !ctx.triggered) {
            return window.dash_clientside.no_update;
        }

        const trigger_id = ctx.triggered[0]['prop_id'].split('.')[0];

        if (trigger_id === '%(save_btn_id)s') {
            // Collect visibility settings
            const visibility = {};
            const tabItems = document.querySelectorAll('[id^="%(domain_prefix)s"]');

            tabItems.forEach(item => {
                const tabId = item.getAttribute('data-tab-id');
                const switchElement = item.querySelector('input[type="checkbox"]');
                const isVisible = switchElement ? switchElement.checked : false;
                visibility[tabId] = isVisible;
            });

            // Get current order
            const order = Array.from(document.querySelectorAll('[id^="%(domain_prefix)s"]'))
                .map(item => item.getAttribute('data-tab-id'));

            // Save preferences
            try {
                const tabManager = window.tabPreferencesManager;
                const success = tabManager.savePreferences(visibility, order);

                if (success) {
                    // Show success message
                    const successAlert = document.createElement('div');
                    successAlert.className = 'alert alert-success alert-dismissible fade show position-fixed';
                    successAlert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
                    successAlert.innerHTML = `
                        <i class="fas fa-check-circle me-2"></i>
                        <strong>Success!</strong> Tab preferences saved.
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.body.appendChild(successAlert);

                    // Auto-remove after 3 seconds
                    setTimeout(() => {
                        if (successAlert.parentNode) {
                            successAlert.parentNode.removeChild(successAlert);
                        }
                    }, 3000);

                    // Close modal
                    return false;
                } else {
                    throw new Error('Failed to save tab preferences');
                }
            } catch (error) {
                console.error('Error saving tab preferences:', error);

                // Show error message
                const errorAlert = document.createElement('div');
                errorAlert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
                errorAlert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
                errorAlert.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Error:</strong> ${error.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                document.body.appendChild(errorAlert);

                setTimeout(() => {
                    if (errorAlert.parentNode) {
                        errorAlert.parentNode.removeChild(errorAlert);
                    }
                }, 5000);

                return is_open; // Keep modal open on error
            }

        } else if (trigger_id === '%(reset_btn_id)s') {
            // Confirm reset
            const confirmed = confirm('Are you sure you want to reset all tabs to their default configuration?');

            if (confirmed) {
                try {
                    const tabManager = window.tabPreferencesManager;
                    const success = tabManager.resetToDefault();

                    if (success) {
                        // Reload tab display
                        const trigger = document.getElementById('customize-tabs-trigger');
                        if (trigger) {
                            trigger.innerHTML = Date.now();
                        }

                        // Show success message
                        const successAlert = document.createElement('div');
                        successAlert.className = 'alert alert-warning alert-dismissible fade show position-fixed';
                        successAlert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
                        successAlert.innerHTML = `
                            <i class="fas fa-undo me-2"></i>
                            <strong>Reset!</strong> Tab preferences reset to defaults.
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        `;
                        document.body.appendChild(successAlert);

                        setTimeout(() => {
                            if (successAlert.parentNode) {
                                successAlert.parentNode.removeChild(successAlert);
                            }
                        }, 3000);

                        return false; // Keep modal open to see changes
                    } else {
                        throw new Error('Failed to reset tab preferences');
                    }
                } catch (error) {
                    console.error('Error resetting tab preferences:', error);

                    const errorAlert = document.createElement('div');
                    errorAlert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
                    errorAlert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
                    errorAlert.innerHTML = `
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>Error:</strong> ${error.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.body.appendChild(errorAlert);

                    setTimeout(() => {
                        if (errorAlert.parentNode) {
                            errorAlert.parentNode.removeChild(errorAlert);
                        }
                    }, 5000);

                    return is_open;
                }
            } else {
                return is_open; // User cancelled, keep modal open
            }
        } else if (trigger_id === '%(cancel_btn_id)s') {
            return false; // Close modal
        }

        return is_open;
    }
    """ % {
        "save_btn_id": customize_tabs.save_btn_id,
        "reset_btn_id": customize_tabs.reset_btn_id,
        "cancel_btn_id": customize_tabs.cancel_btn_id,
        "domain_prefix": customize_tabs.domain_prefix
    },
    Output(f"{customize_tabs.modal_id}", "is_open"),
    [
        Input(f"{customize_tabs.save_btn_id}", "n_clicks"),
        Input(f"{customize_tabs.reset_btn_id}", "n_clicks"),
        Input(f"{customize_tabs.cancel_btn_id}", "n_clicks"),
    ],
    [
        State(f"{customize_tabs.modal_id}", "is_open")
    ],
    prevent_initial_call=True
)