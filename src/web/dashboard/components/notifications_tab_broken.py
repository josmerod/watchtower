"""Notifications tab component for alert rule management.

This module provides the main notifications interface where users can create,
edit, delete, and test alert rules for content monitoring.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback_context, dcc, html

# Import alert system components with fallback
try:
    from src.alerts.engine import AlertEngine
    from src.alerts.models import (
        AlertCondition,
        AlertRule,
        CategoryMatchCondition,
        KeywordMatchCondition,
        NotificationChannel,
        PriceThresholdCondition,
        SourceMatchCondition,
        TimeRange,
    )

    ALERTS_AVAILABLE = True
except ImportError:
    print("Warning: Alert system not available. Using mock classes.")
    AlertRule = None
    AlertCondition = None
    SourceMatchCondition = None
    KeywordMatchCondition = None
    CategoryMatchCondition = None
    PriceThresholdCondition = None
    NotificationChannel = None
    TimeRange = None
    AlertEngine = None
    ALERTS_AVAILABLE = False

# Import utilities with fallback
try:
    from src.utils.file_system import ensure_directories, get_project_root
    from src.utils.logging import get_logger

    UTILS_AVAILABLE = True
except ImportError:
    print("Warning: Utils not available. Using fallback functions.")
    UTILS_AVAILABLE = False

# Import form components with fallback
try:
    from .rule_form import (
        render_category_condition_editor,
        render_condition_editor,
        render_keyword_condition_editor,
        render_price_condition_editor,
        render_source_condition_editor,
        render_test_results,
    )

    RULE_FORM_AVAILABLE = True
except ImportError:
    print("Warning: Rule form components not available.")
    RULE_FORM_AVAILABLE = False


def _get_rule_id(rule: Any) -> str:
    """Helper function to get rule ID from various rule formats."""
    if hasattr(rule, "id"):
        return rule.id
    elif isinstance(rule, dict):
        return rule.get("id", "")
    else:
        return str(rule)


# Fallback functions for when utils are not available
def get_project_root_fallback():
    """Fallback function to get project root."""
    current_file = Path(__file__).resolve()
    # Go up from src/web/dashboard/components/ to project root
    return current_file.parent.parent.parent.parent


def ensure_directories_fallback(directories):
    """Fallback function to ensure directories exist."""
    project_root = get_project_root_fallback()
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)


def get_logger_fallback(name):
    """Fallback logger function."""
    import logging

    return logging.getLogger(name)


class NotificationsManager:
    """Manager class for notifications tab functionality.

    Handles data loading, rule management, and state management following
    the established VideoManager pattern from the dashboard.
    """

    def __init__(self):
        """Initialize the notifications manager."""
        # Use fallbacks if utils are not available
        if UTILS_AVAILABLE:
            self.logger = get_logger("NotificationsManager")
            self.project_root = Path(get_project_root())
        else:
            self.logger = get_logger_fallback("NotificationsManager")
            self.project_root = get_project_root_fallback()

        self.data_dir = self.project_root / "data"

        # Initialize alert engine if available
        self.alert_engine = AlertEngine() if ALERTS_AVAILABLE else None

        # User ID for single-user deployment
        self.user_id = "default_user"

        # Ensure directories exist
        self._ensure_directories()

        self.logger.info("NotificationsManager initialized")

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        try:
            alerts_dir = self.data_dir / "alerts" / self.user_id
            if UTILS_AVAILABLE:
                ensure_directories([str(alerts_dir)])
            else:
                ensure_directories_fallback([str("data/alerts/" + self.user_id)])
        except Exception as e:
            self.logger.error(f"Error ensuring directories: {e}")

    def load_rules(self) -> list[Any]:
        """Load all alert rules for the user.

        Returns:
            List of AlertRule objects or mock rule dictionaries
        """
        try:
            rules_file = self.data_dir / "alerts" / self.user_id / "rules.json"

            if not rules_file.exists():
                self.logger.info("No rules file found, returning empty list")
                return []

            with open(rules_file, encoding="utf-8") as f:
                rules_data = json.load(f)

            rules = []
            for rule_data in rules_data:
                try:
                    if ALERTS_AVAILABLE and AlertRule:
                        rule = AlertRule(**rule_data)
                        rules.append(rule)
                    else:
                        # Use raw dictionary if AlertRule model is not available
                        rules.append(rule_data)
                except Exception as e:
                    self.logger.error(f"Error loading rule {rule_data.get('id', 'unknown')}: {e}")

            self.logger.info(f"Loaded {len(rules)} rules")
            return rules

        except Exception as e:
            self.logger.error(f"Error loading rules: {e}")
            return []

    def save_rule(self, rule: Any) -> bool:
        """Save a rule to storage.

        Args:
            rule: AlertRule object or dictionary to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle both AlertRule objects and dictionaries
            if hasattr(rule, "id"):
                # AlertRule object
                if not rule.id:
                    rule.id = f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                if hasattr(rule, "user_id"):
                    rule.user_id = self.user_id
                if hasattr(rule, "updated_at"):
                    rule.updated_at = datetime.now()

                rule_id = rule.id
                rule_data = rule.dict() if hasattr(rule, "dict") else dict(rule)
            else:
                # Dictionary
                if not rule.get("id"):
                    rule["id"] = f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                rule["user_id"] = self.user_id
                rule["updated_at"] = datetime.now().isoformat()

                rule_id = rule["id"]
                rule_data = rule

            # Load existing rules
            rules = self.load_rules()

            # Find and update or add new rule
            rule_index = None
            for i, existing_rule in enumerate(rules):
                existing_id = getattr(
                    existing_rule,
                    "id",
                    (existing_rule.get("id") if isinstance(existing_rule, dict) else None),
                )
                if existing_id == rule_id:
                    rule_index = i
                    break

            if rule_index is not None:
                rules[rule_index] = rule_data
            else:
                rules.append(rule_data)

            # Save to file
            rules_file = self.data_dir / "alerts" / self.user_id / "rules.json"

            # Convert all rules to dictionaries for JSON storage
            rules_data = []
            for r in rules:
                if hasattr(r, "dict"):
                    rules_data.append(r.dict())
                elif isinstance(r, dict):
                    rules_data.append(r)
                else:
                    # AlertRule-like object
                    rules_data.append(dict(r))

            with open(rules_file, "w", encoding="utf-8") as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False, default=str)

            # Reload alert engine if available
            if self.alert_engine and hasattr(self.alert_engine, "reload_rules"):
                self.alert_engine.reload_rules(self.user_id)

            self.logger.info(f"Saved rule {rule_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving rule: {e}")
            return False

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by ID.

        Args:
            rule_id: ID of rule to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            rules = self.load_rules()
            rules = [rule for rule in rules if self._get_rule_id(rule) != rule_id]

            # Save updated rules
            rules_file = self.data_dir / "alerts" / self.user_id / "rules.json"

            # Convert all rules to dictionaries for JSON storage
            rules_data = []
            for r in rules:
                if hasattr(r, "dict"):
                    rules_data.append(r.dict())
                elif isinstance(r, dict):
                    rules_data.append(r)
                else:
                    rules_data.append(dict(r))

            with open(rules_file, "w", encoding="utf-8") as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False, default=str)

            # Reload alert engine if available
            if self.alert_engine and hasattr(self.alert_engine, "reload_rules"):
                self.alert_engine.reload_rules(self.user_id)

            self.logger.info(f"Deleted rule {rule_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting rule: {e}")
            return False

    def _get_rule_id(self, rule: Any) -> str:
        """Helper method to get rule ID from various rule formats."""
        if hasattr(rule, "id"):
            return rule.id
        elif isinstance(rule, dict):
            return rule.get("id", "")
        else:
            return str(rule)

    def get_available_sources(self) -> list[str]:
        """Get list of available content sources for rule creation.

        Returns:
            List of source names
        """
        sources = []

        # Check data directories for available sources
        data_dirs = [
            "arxiv",
            "news",
            "videos",
            "games",
            "courses",
            "anime",
            "intelligence",
            "deals",
            "giveaways",
        ]

        for source_dir in data_dirs:
            source_path = self.data_dir / source_dir
            if source_path.exists():
                sources.append(source_dir)

        return sorted(sources)

    def get_available_categories(self) -> list[str]:
        """Get list of available content categories.

        Returns:
            List of category names
        """
        # Common categories from NLP classification
        categories = [
            "Technology",
            "Science",
            "Business",
            "Education",
            "Entertainment",
            "Health",
            "Finance",
            "Gaming",
            "Programming",
            "AI",
            "Machine Learning",
            "Data Science",
            "Web Development",
            "Mobile Development",
            "DevOps",
        ]

        return sorted(categories)


def render_notifications_tab() -> dbc.Container:
    """Render the main notifications tab content.

    Returns:
        Dash component with notifications interface
    """
    return dbc.Container(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3("🔔 Alert Rules", className="mb-3"),
                            html.P(
                                "Create and manage notification rules to get alerts for content you care about.",
                                className="text-muted mb-4",
                            ),
                        ],
                        width=12,
                    ),
                ]
            ),
            # Action buttons
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Create Alert Rule",
                                id="create-rule-btn",
                                color="primary",
                                className="me-2",
                                n_clicks=0,
                            ),
                            dbc.Button(
                                "Reload Rules",
                                id="reload-rules-btn",
                                color="secondary",
                                outline=True,
                                n_clicks=0,
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-4",
            ),
            # Rules list
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(id="rules-list-container"),
                        ],
                        width=12,
                    ),
                ]
            ),
            # Rule creation/editing modal
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Create Alert Rule"), id="rule-modal-header"),
                    dbc.ModalBody(id="rule-modal-body"),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="rule-modal-cancel",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button("Save Rule", id="rule-modal-save", color="primary"),
                            dbc.Button(
                                "Test Rule",
                                id="rule-modal-test",
                                color="success",
                                outline=True,
                                className="me-2",
                            ),
                        ]
                    ),
                ],
                id="rule-modal",
                is_open=False,
                size="lg",
            ),
            # Store for form data
            dcc.Store(id="rule-form-store", data={}),
        ],
        fluid=True,
    )


def register_notifications_callbacks(app):
    """Register all callbacks for the notifications tab.

    Args:
        app: Dash application instance
    """
    manager = NotificationsManager()

    # Build input list dynamically
    rules = manager.load_rules()
    rule_inputs = []
    for rule in rules:
        rule_id = _get_rule_id(rule)
        rule_inputs.extend(
            [
                Input(f"delete-rule-{rule_id}", "n_clicks"),
                Input(f"toggle-rule-{rule_id}", "n_clicks"),
            ]
        )

    @app.callback(
        Output("rules-list-container", "children"),
        [
            Input("reload-rules-btn", "n_clicks"),
            Input("create-rule-btn", "n_clicks"),
            Input("rule-modal-save", "n_clicks"),
            Input("rule-modal-cancel", "n_clicks"),
        ]
        + rule_inputs,
        prevent_initial_call=False,
    )
    def update_rules_list(*args):
        """Update the rules list display."""
        # Get the triggered input to determine the action
        ctx = callback_context
        if not ctx.triggered:
            return render_rules_list([])

        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Handle delete action
        if triggered_id.startswith("delete-rule-"):
            rule_id = triggered_id.replace("delete-rule-", "")
            if manager.delete_rule(rule_id):
                return render_rules_list(manager.load_rules())
            else:
                return dbc.Alert("Error deleting rule", color="danger")

        # Handle toggle action
        if triggered_id.startswith("toggle-rule-"):
            rule_id = triggered_id.replace("toggle-rule-", "")
            rules = manager.load_rules()
            for rule in rules:
                if rule.id == rule_id:
                    rule.active = not rule.active
                    manager.save_rule(rule)
                    break
            return render_rules_list(manager.load_rules())

        # Handle reload or other actions
        return render_rules_list(manager.load_rules())

    # Build edit inputs dynamically
    edit_inputs = [Input(f"edit-rule-{_get_rule_id(rule)}", "n_clicks") for rule in rules]

    @app.callback(
        Output("rule-modal", "is_open"),
        [Input("create-rule-btn", "n_clicks")] + edit_inputs,
        prevent_initial_call=True,
    )
    def toggle_rule_modal(*args):
        """Toggle rule modal visibility."""
        ctx = callback_context
        if not ctx.triggered:
            return False

        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        return bool(triggered_id == "create-rule-btn" or triggered_id.startswith("edit-rule-"))

    @app.callback(
        Output("rule-modal-header", "children"),
        [Input("create-rule-btn", "n_clicks")] + edit_inputs,
    )
    def update_modal_header(*args):
        """Update modal header based on action."""
        ctx = callback_context
        if not ctx.triggered:
            return dbc.ModalTitle("Create Alert Rule")

        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered_id.startswith("edit-rule-"):
            return dbc.ModalTitle("Edit Alert Rule")
        return dbc.ModalTitle("Create Alert Rule")

    # Build state inputs dynamically
    state_inputs = [State(f"edit-rule-{_get_rule_id(rule)}", "n_clicks") for rule in rules]

    @app.callback(
        Output("rule-modal-body", "children"),
        [Input("rule-modal", "is_open")],
        state_inputs,
    )
    def update_modal_body(is_open, *args):
        """Update modal body content."""
        if not is_open:
            return ""

        ctx = callback_context
        triggered_input = None

        # Find the triggered edit input
        for input_id in ctx.states:
            if input_id.startswith("edit-rule-") and ctx.states[input_id] > 0:
                triggered_input = input_id
                break

        # If editing an existing rule
        if triggered_input:
            rule_id = triggered_input.replace("edit-rule-", "")
            rules = manager.load_rules()
            for rule in rules:
                if rule.id == rule_id:
                    return render_rule_form(rule)

        # Default: create new rule form
        return render_rule_form()

    # Add more callbacks for form handling, etc.
    # This is a simplified version - in a full implementation,
    # we'd add callbacks for saving rules, testing, conditions management, etc.

    app.logger.info("Notifications callbacks registered")


def render_rules_list(rules: list[Any]) -> dbc.Container:
    """Render the list of alert rules.

    Args:
        rules: List of AlertRule objects or dictionaries

    Returns:
        Dash component with rules list
    """
    if not rules:
        return dbc.Container(
            [
                dbc.Alert(
                    "No alert rules configured yet. Click 'Create Alert Rule' to get started.",
                    color="info",
                    className="mt-3",
                ),
            ],
            fluid=True,
        )

    rules_cards = []
    for rule in rules:
        # Handle both AlertRule objects and dictionaries
        rule_data = rule.dict() if hasattr(rule, "dict") else rule if isinstance(rule, dict) else {}

        rule_id = _get_rule_id(rule)
        rule_name = rule_data.get("name", getattr(rule, "name", "Unnamed Rule"))
        rule_description = rule_data.get("description", getattr(rule, "description", ""))
        is_active = rule_data.get("active", getattr(rule, "active", True))
        last_triggered = rule_data.get("last_triggered", getattr(rule, "last_triggered", None))
        trigger_count = rule_data.get("trigger_count", getattr(rule, "trigger_count", 0))

        status_badge = dbc.Badge(
            "Active" if is_active else "Inactive",
            color="success" if is_active else "secondary",
            className="me-2",
        )

        # Format last triggered
        if last_triggered:
            try:
                if isinstance(last_triggered, str):
                    dt = datetime.fromisoformat(last_triggered.replace("Z", "+00:00"))
                    last_triggered_str = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    last_triggered_str = last_triggered.strftime("%Y-%m-%d %H:%M")
            except:
                last_triggered_str = "Unknown"
        else:
            last_triggered_str = "Never"

        trigger_count_str = f"({trigger_count} triggers)"

        # Build condition summary
        condition_summary = []
        conditions = rule_data.get("conditions", getattr(rule, "conditions", []))
        for condition in conditions[:2]:  # Show first 2 conditions
            if isinstance(condition, dict):
                condition_type = condition.get("condition_type", "")
                condition_value = condition.get("value", "")
                condition_operator = condition.get("operator", "")
            else:
                condition_type = getattr(condition, "condition_type", "")
                condition_value = getattr(condition, "value", "")
                condition_operator = getattr(condition, "operator", "")

            if condition_type == "source_match":
                condition_summary.append(f"Source: {condition_value}")
            elif condition_type == "keyword_match":
                condition_summary.append(f"Keyword: {condition_value}")
            elif condition_type == "category_match":
                condition_summary.append(f"Category: {condition_value}")
            elif condition_type == "price_threshold":
                condition_summary.append(f"Price: {condition_operator} {condition_value}")

        if len(conditions) > 2:
            condition_summary.append(f"... and {len(conditions) - 2} more")

        # Build channels summary
        notification_channels = rule_data.get("notification_channels", getattr(rule, "notification_channels", []))
        if notification_channels:
            channels = []
            for ch in notification_channels:
                if isinstance(ch, dict):
                    channels.append(ch.get("value", ""))
                elif hasattr(ch, "value"):
                    channels.append(ch.value)
                else:
                    channels.append(str(ch))
            channels_text = ", ".join(filter(None, channels))
        else:
            channels_text = "None"

        card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H5(rule_name, className="mb-2"),
                                        html.P(
                                            rule_description or "No description",
                                            className="text-muted mb-3",
                                        ),
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        status_badge,
                                    ],
                                    width=4,
                                    className="text-end",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.H6("Conditions:", className="mb-2"),
                                html.P(
                                    (", ".join(condition_summary) if condition_summary else "No conditions defined"),
                                    className="mb-3",
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Small(
                                            [
                                                html.Strong("Last Triggered: "),
                                                f"{last_triggered_str} {trigger_count_str}",
                                            ],
                                            className="text-muted",
                                        ),
                                    ],
                                    width=6,
                                ),
                                dbc.Col(
                                    [
                                        html.Small(
                                            [html.Strong("Channels: "), channels_text],
                                            className="text-muted",
                                        ),
                                    ],
                                    width=6,
                                ),
                            ]
                        ),
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    "Edit",
                                    id=f"edit-rule-{rule_id}",
                                    color="primary",
                                    outline=True,
                                    size="sm",
                                ),
                                dbc.Button(
                                    "Delete",
                                    id=f"delete-rule-{rule_id}",
                                    color="danger",
                                    outline=True,
                                    size="sm",
                                ),
                                dbc.Button(
                                    "Enable" if not is_active else "Disable",
                                    id=f"toggle-rule-{rule_id}",
                                    color="success" if not is_active else "warning",
                                    outline=True,
                                    size="sm",
                                ),
                            ],
                            className="mt-3",
                        ),
                    ]
                ),
            ],
            className="mb-3",
        )

        rules_cards.append(card)

    return dbc.Container(rules_cards, fluid=True)


def render_rule_form(rule: AlertRule | None = None) -> dbc.Container:
    """Render the rule creation/editing form.

    Args:
        rule: Existing rule to edit, or None for new rule

    Returns:
        Dash component with rule form
    """

    return dbc.Container(
        [
            # Basic information
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Rule Name *", html_for="rule-name-input"),
                            dbc.Input(
                                id="rule-name-input",
                                placeholder="Enter a descriptive name for this rule",
                                value=rule.name if rule else "",
                                type="text",
                                required=True,
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Description", html_for="rule-description-input"),
                            dbc.Textarea(
                                id="rule-description-input",
                                placeholder="Optional description of what this rule does",
                                value=rule.description if rule else "",
                                rows=2,
                            ),
                        ],
                        width=6,
                    ),
                ],
                className="mb-3",
            ),
            # Active status
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Checklist(
                                [
                                    dbc.ChecklistItem(
                                        "Enable this rule",
                                        id="rule-active-checkbox",
                                        checked=rule.active if rule else True,
                                    ),
                                ],
                                id="rule-active-checklist",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            # Conditions section
            html.H5("Conditions", className="mb-3"),
            html.Div(id="rule-conditions-container"),
            # Add condition button
            dbc.Button(
                "Add Condition",
                id="add-condition-btn",
                color="outline-primary",
                size="sm",
                className="mb-4",
            ),
            # Notification channels
            html.H5("Notification Channels", className="mb-3"),
            dbc.Checklist(
                [
                    dbc.ChecklistItem(
                        "Browser notifications",
                        id="channel-browser-checkbox",
                        checked=("browser" in [ch.value for ch in rule.notification_channels] if rule else True),
                    ),
                    dbc.ChecklistItem(
                        "Email notifications",
                        id="channel-email-checkbox",
                        checked=("email" in [ch.value for ch in rule.notification_channels] if rule else False),
                    ),
                ],
                id="notification-channels-checklist",
            ),
            # Quiet hours
            html.H5("Quiet Hours", className="mb-3 mt-4"),
            dbc.Checklist(
                [
                    dbc.ChecklistItem(
                        "Enable quiet hours",
                        id="quiet-hours-enabled-checkbox",
                        checked=rule.quiet_hours is not None,
                    ),
                ],
                id="quiet-hours-checklist",
            ),
            # Quiet hours configuration (shown when enabled)
            html.Div(
                id="quiet-hours-config",
                style={"display": "block" if rule and rule.quiet_hours else "none"},
            ),
        ],
        fluid=True,
    )
