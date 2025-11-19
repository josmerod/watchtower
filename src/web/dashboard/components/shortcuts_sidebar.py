"""
Shortcuts Sidebar Component
Provides a collapsible sidebar for managing personal source shortcuts
"""

import dash
from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
    State,
    clientside_callback,
    ClientsideFunction,
)
import dash_bootstrap_components as dbc
import uuid
from typing import Dict, List, Any


class ShortcutsSidebar:
    """Manages the shortcuts sidebar component"""

    def __init__(self):
        self.sidebar_id = f"shortcuts-sidebar-{uuid.uuid4().hex[:8]}"
        self.shortcuts_container_id = f"shortcuts-container-{uuid.uuid4().hex[:8]}"
        self.toggle_btn_id = f"shortcuts-toggle-{uuid.uuid4().hex[:8]}"
        self.stats_id = f"shortcuts-stats-{uuid.uuid4().hex[:8]}"
        self.domain_prefix = "shortcuts-domain-"

    def create_toggle_button(self):
        """Create the sidebar toggle button for the main layout"""
        return dbc.Button(
            [
                html.I(className="fas fa-star me-2"),
                "Shortcuts",
                html.Span(
                    id=self.stats_id, className="badge bg-secondary ms-2", children="0"
                ),
            ],
            id=self.toggle_btn_id,
            color="outline-primary",
            size="sm",
            className="me-2",
            n_clicks=0,
        )

    def create_sidebar(self):
        """Create the shortcuts sidebar component"""
        return dbc.Offcanvas(
            [
                html.Div(
                    [
                        html.H5(
                            [html.I(className="fas fa-star me-2"), "My Source Shortcuts"],
                            className="offcanvas-title"
                        ),
                        html.Button(
                            type="button",
                            className="btn-close text-reset",
                            **{"data-bs-dismiss": "offcanvas", "aria-label": "Close"}
                        ),
                    ],
                    className="offcanvas-header border-bottom"
                ),
                html.Div(
                    [
                        # Statistics section
                        dbc.Alert(
                            [
                                html.H6("Quick Stats", className="alert-heading mb-2"),
                                html.P(
                                    "Manage your frequently accessed sources with one-click navigation",
                                    className="mb-0 small",
                                ),
                            ],
                            color="info",
                            className="mb-3",
                        ),
                        # Shortcuts container (populated by JavaScript)
                        html.Div(
                            id=self.shortcuts_container_id,
                            children=[
                                # Loading placeholder
                                html.Div(
                                    [
                                        dbc.Spinner(size="sm", spinner_class_name="me-2"),
                                        html.Small("Loading shortcuts..."),
                                    ],
                                    className="text-center text-muted py-3",
                                )
                            ],
                        ),
                        # Add shortcut help
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H6(
                                        "How to Add Shortcuts",
                                        className="card-title mb-2",
                                    ),
                                    html.P(
                                        [
                                            "Look for the ",
                                            html.I(className="fas fa-star me-1"),
                                            " 'Add to Shortcuts' button on any content item across the dashboard.",
                                        ],
                                        className="card-text small text-muted mb-0",
                                    ),
                                ]
                            ),
                            className="mt-3 bg-light",
                        ),
                    ],
                    className="offcanvas-body p-0",
                ),
            ],
            id=self.sidebar_id,
            is_open=False,
            placement="start",
            scrollable=True,
            backdrop=False,
            style={"width": "320px"},
        )

    def create_shortcut_card(self, shortcut_data: Dict[str, Any]) -> dbc.Card:
        """Create a card for a single shortcut"""
        shortcut_id = shortcut_data.get("id", "")
        shortcut_name = shortcut_data.get("name", "Unknown")
        shortcut_domain = shortcut_data.get("domain", "Other")

        # Domain color mapping
        domain_colors = {
            "Papers": "primary",
            "News": "success",
            "Deals": "danger",
            "Courses": "info",
            "Videos": "warning",
            "AI": "dark",
            "Entertainment": "secondary",
            "Other": "light",
        }

        domain_color = domain_colors.get(shortcut_domain, "light")

        return dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                # Domain badge
                                dbc.Badge(
                                    shortcut_domain,
                                    color=domain_color,
                                    className="me-2",
                                ),
                                # Shortcut name (clickable)
                                html.A(
                                    shortcut_name,
                                    href="#",
                                    id=f"shortcut-link-{shortcut_id}",
                                    className="text-decoration-none fw-bold",
                                    **{
                                        "data-shortcut-id": shortcut_id,
                                        "data-domain": shortcut_domain,
                                    },
                                ),
                            ],
                            className="d-flex align-items-center justify-content-between mb-2",
                        ),
                        # Action buttons
                        html.Div(
                            [
                                # Remove button
                                dbc.Button(
                                    html.I(className="fas fa-trash"),
                                    id=f"remove-shortcut-{shortcut_id}",
                                    color="outline-danger",
                                    size="sm",
                                    className="me-1",
                                    **{
                                        "data-shortcut-id": shortcut_id,
                                        "data-shortcut-name": shortcut_name,
                                    },
                                ),
                                # Edit button (future enhancement)
                                dbc.Button(
                                    html.I(className="fas fa-grip-vertical"),
                                    color="outline-secondary",
                                    size="sm",
                                    className="me-1",
                                    disabled=True,
                                    title="Drag to reorder (coming soon)",
                                ),
                            ],
                            className="d-flex justify-content-end",
                        ),
                    ],
                    className="p-3",
                )
            ],
            className="mb-2 shortcut-card",
            id=f"shortcut-card-{shortcut_id}",
            **{
                "data-shortcut-id": shortcut_id,
                "data-domain": shortcut_domain,
                "draggable": "true",
            },
        )

    def create_domain_section(
        self, domain: str, shortcuts: List[Dict[str, Any]]
    ) -> html.Div:
        """Create a section for a specific domain"""
        if not shortcuts:
            return html.Div()

        domain_colors = {
            "Papers": "primary",
            "News": "success",
            "Deals": "danger",
            "Courses": "info",
            "Videos": "warning",
            "AI": "dark",
            "Entertainment": "secondary",
            "Other": "light",
        }

        domain_color = domain_colors.get(domain, "light")
        domain_icons = {
            "Papers": "fa-book",
            "News": "fa-newspaper",
            "Deals": "fa-tags",
            "Courses": "fa-graduation-cap",
            "Videos": "fa-video",
            "AI": "fa-robot",
            "Entertainment": "fa-gamepad",
            "Other": "fa-folder",
        }

        domain_icon = domain_icons.get(domain, "fa-folder")

        return html.Div(
            [
                # Domain header
                html.Div(
                    [
                        html.I(className=f"fas {domain_icon} me-2"),
                        html.H6(f"{domain} ({len(shortcuts)})", className="mb-0 me-2"),
                    ],
                    className="d-flex align-items-center justify-content-between mb-3 border-bottom pb-2",
                ),
                # Shortcuts in this domain
                html.Div(
                    [
                        self.create_shortcut_card(shortcut)
                        for shortcut in sorted(
                            shortcuts, key=lambda x: x.get("order", 0)
                        )
                    ]
                ),
            ],
            className="mb-4",
            id=f"{self.domain_prefix}{domain.lower().replace(' ', '-')}",
        )

    def get_layout(self) -> html.Div:
        """Get the complete shortcuts sidebar layout"""
        return html.Div(
            [
                # Toggle button (placed in main layout)
                self.create_toggle_button(),
                # Sidebar component
                self.create_sidebar(),
                # Store for clientside callbacks
                dcc.Store(id="shortcuts-data-store", data={}),
                # Hidden div for stats updates
                html.Div(id="shortcuts-updates-trigger", style={"display": "none"}),
            ]
        )


# Instantiate component
shortcuts_sidebar = ShortcutsSidebar()


# Clientside callback to toggle sidebar
clientside_callback(
    """
    function(n_clicks, is_open) {
        return !is_open;
    }
    """,
    Output(f"{shortcuts_sidebar.sidebar_id}", "is_open"),
    Input(f"{shortcuts_sidebar.toggle_btn_id}", "n_clicks"),
    State(f"{shortcuts_sidebar.sidebar_id}", "is_open"),
    prevent_initial_call=True,
)


# Clientside callback to load and display shortcuts
clientside_callback(
    """
    function(trigger) {
        try {
            const shortcutsManager = window.shortcutsManager;
            if (!shortcutsManager) {
                console.error('ShortcutsManager not available');
                return [];
            }

            const grouped = shortcutsManager.getShortcutsByDomain();
            const stats = shortcutsManager.getStorageStats();

            // Update stats badge
            const statsElement = document.getElementById('%(stats_id)s');
            if (statsElement) {
                statsElement.textContent = stats.totalShortcuts;
            }

            return grouped;
        } catch (error) {
            console.error('Error loading shortcuts:', error);
            return {};
        }
    }
    """
    % {"stats_id": shortcuts_sidebar.stats_id},
    Output("shortcuts-data-store", "data"),
    Input("shortcuts-updates-trigger", "children"),
    prevent_initial_call=True,
)


# Callback to render shortcuts from data store
@dash.callback(
    Output(f"{shortcuts_sidebar.shortcuts_container_id}", "children"),
    Input("shortcuts-data-store", "data"),
    prevent_initial_call=True,
)
def render_shortcuts(grouped_data: Dict[str, List[Dict[str, Any]]]):
    """Render shortcuts from grouped data"""
    if not grouped_data:
        return html.Div(
            [
                html.P("No shortcuts yet", className="text-center text-muted py-3"),
                html.P(
                    "Add shortcuts using the star button on content items",
                    className="text-center small text-muted",
                ),
            ]
        )

    # Define domain order for consistent display
    domain_order = [
        "Papers",
        "News",
        "Deals",
        "Courses",
        "Videos",
        "AI",
        "Entertainment",
        "Other",
    ]

    sections = []

    # Add domains in order, only if they have shortcuts
    for domain in domain_order:
        shortcuts = grouped_data.get(domain, [])
        if shortcuts:
            sections.append(shortcuts_sidebar.create_domain_section(domain, shortcuts))

    return sections


# Clientside callback for shortcut navigation
clientside_callback(
    """
    function(clicks) {
        if (clicks && clicks > 0) {
            // This will be handled by the clientside click handler
            return window.dash_clientside.no_update;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output(f"{shortcuts_sidebar.shortcuts_container_id}", "data-dummy"),  # Dummy output
    Input({"type": "shortcut-link", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)


# Clientside callback for removing shortcuts
clientside_callback(
    """
    function(clicks) {
        if (clicks && clicks > 0) {
            // This will be handled by the clientside click handler
            return window.dash_clientside.no_update;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output(
        f"{shortcuts_sidebar.shortcuts_container_id}", "data-dummy2"
    ),  # Dummy output
    Input({"type": "remove-shortcut", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)


# JavaScript to inject for handling shortcut interactions
def get_shortcuts_clientside_script():
    """Return JavaScript code for handling shortcut interactions"""
    return """
    // Handle shortcut navigation
    document.addEventListener('click', function(e) {
        const target = e.target.closest('a[id^="shortcut-link-"]');
        if (target) {
            e.preventDefault();
            const shortcutId = target.getAttribute('data-shortcut-id');
            const domain = target.getAttribute('data-domain');

            if (shortcutId) {
                navigateWithShortcut(shortcutId, domain);
            }
        }

        // Handle remove shortcut
        const removeBtn = e.target.closest('button[id^="remove-shortcut-"]');
        if (removeBtn) {
            e.preventDefault();
            const shortcutId = removeBtn.getAttribute('data-shortcut-id');
            const shortcutName = removeBtn.getAttribute('data-shortcut-name');

            if (shortcutId && confirm(`Remove shortcut "${shortcutName}"?`)) {
                removeShortcut(shortcutId);
            }
        }
    });

    function navigateWithShortcut(shortcutId, domain) {
        try {
            const shortcutsManager = window.shortcutsManager;
            const shortcut = shortcutsManager.getShortcut(shortcutId);

            if (!shortcut) {
                console.error('Shortcut not found:', shortcutId);
                return;
            }

            // Apply source filter and navigate to appropriate tab
            const sourceFilter = shortcut.source_filter;

            // Trigger navigation based on domain
            let targetTab = '';
            switch (domain) {
                case 'Papers':
                    targetTab = 'arxiv';
                    break;
                case 'News':
                    targetTab = 'news';
                    break;
                case 'Deals':
                    targetTab = 'deals';
                    break;
                case 'Videos':
                    targetTab = 'videos';
                    break;
                default:
                    targetTab = 'news'; // Default fallback
            }

            // Navigate to tab and apply filter
            // This would need to be integrated with the specific tab callbacks
            console.log('Navigating to tab:', targetTab, 'with filter:', sourceFilter);

            // Close sidebar
            const sidebar = document.getElementById('%(sidebar_id)s');
            if (sidebar && sidebar.classList) {
                const offcanvas = bootstrap.Offcanvas.getInstance(sidebar);
                if (offcanvas) {
                    offcanvas.hide();
                }
            }

        } catch (error) {
            console.error('Error navigating with shortcut:', error);
        }
    }

    function removeShortcut(shortcutId) {
        try {
            const shortcutsManager = window.shortcutsManager;
            const success = shortcutsManager.removeShortcut(shortcutId);

            if (success) {
                // Trigger shortcuts refresh
                const trigger = document.getElementById('shortcuts-updates-trigger');
                if (trigger) {
                    trigger.innerHTML = Date.now(); // Trigger change
                }

                // Show success message (optional)
                console.log('Shortcut removed successfully');
            } else {
                alert('Failed to remove shortcut');
            }
        } catch (error) {
            console.error('Error removing shortcut:', error);
            alert('Error removing shortcut: ' + error.message);
        }
    }

    // Initialize drag and drop for shortcuts (future enhancement)
    function initializeDragDrop() {
        // TODO: Implement drag and drop functionality
        console.log('Drag and drop not yet implemented');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeDragDrop);
    } else {
        initializeDragDrop();
    }
    """ % {"sidebar_id": shortcuts_sidebar.sidebar_id}
