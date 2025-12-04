"""Fixed Notifications tab implementation with working callbacks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback_context, html

from src.alerts.engine import AlertEngine


class NotificationsManager:
    """Manager for alert rules with file-based persistence."""

    def __init__(self):
        self.alert_engine = AlertEngine()
        self.user_id = "default_user"
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure necessary directories exist."""
        from pathlib import Path

        data_dir = Path("data")
        alerts_dir = data_dir / "alerts"
        alerts_dir.mkdir(parents=True, exist_ok=True)

    def load_rules(self) -> list[dict[str, Any]]:
        """Load alert rules from file."""
        try:
            import json
            from pathlib import Path

            rules_file = Path("data/alerts/rules.json")
            if rules_file.exists():
                with open(rules_file) as f:
                    return json.load(f)
            return []
        except Exception:
            return []

    def save_rule(self, rule: dict[str, Any]) -> bool:
        """Save a rule to file."""
        try:
            import json
            from pathlib import Path

            rules = self.load_rules()

            # Update existing rule or add new one
            for i, existing_rule in enumerate(rules):
                if existing_rule.get("id") == rule.get("id"):
                    rules[i] = rule
                    break
            else:
                rules.append(rule)

            rules_file = Path("data/alerts/rules.json")
            with open(rules_file, "w") as f:
                json.dump(rules, f, indent=2, default=str)

            return True
        except Exception:
            return False

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by ID."""
        try:
            import json
            from pathlib import Path

            rules = self.load_rules()
            rules = [rule for rule in rules if rule.get("id") != rule_id]

            rules_file = Path("data/alerts/rules.json")
            with open(rules_file, "w") as f:
                json.dump(rules, f, indent=2, default=str)

            return True
        except Exception:
            return False


def render_notifications_tab() -> dbc.Container:
    """Render the main notifications tab content."""
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
            # Status message
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(id="rule-save-status"),
                        ],
                        width=12,
                    ),
                ]
            ),
            # Rule creation modal
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
                                className="me-2",
                            ),
                            dbc.Button("Save Rule", id="rule-modal-save", color="primary"),
                        ]
                    ),
                ],
                id="rule-modal",
                is_open=False,
                size="lg",
            ),
        ],
        fluid=True,
    )


def render_rules_list(rules: list[Any]) -> dbc.Container:
    """Render the list of alert rules."""
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
        rule_id = rule.get("id", "unknown")
        rule_name = rule.get("name", "Unnamed Rule")
        rule_description = rule.get("description", "")
        is_active = rule.get("active", True)
        created_at = rule.get("created_at", "")

        status_badge = dbc.Badge(
            "Active" if is_active else "Inactive",
            color="success" if is_active else "secondary",
            className="me-2",
        )

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
                                html.Small(
                                    [
                                        html.Strong("Created: "),
                                        created_at[:19] if created_at else "Unknown",
                                    ],
                                    className="text-muted",
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    "Delete",
                                    id=f"delete-rule-{rule_id}",
                                    color="danger",
                                    outline=True,
                                    size="sm",
                                    n_clicks=0,
                                ),
                                dbc.Button(
                                    "Enable" if not is_active else "Disable",
                                    id=f"toggle-rule-{rule_id}",
                                    color="success" if not is_active else "warning",
                                    outline=True,
                                    size="sm",
                                    n_clicks=0,
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


def render_rule_form() -> dbc.Container:
    """Render the rule creation/editing form."""
    return dbc.Container(
        [
            html.H4("Rule Details", className="mb-4"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Rule Name *"),
                            dbc.Input(
                                id="rule-name-input",
                                placeholder="Enter rule name",
                                type="text",
                                className="mb-3",
                            ),
                        ],
                        width=12,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Description"),
                            dbc.Textarea(
                                id="rule-description-input",
                                placeholder="Describe what this rule monitors for",
                                className="mb-3",
                                rows=3,
                            ),
                        ],
                        width=12,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Checklist(
                                id="rule-is-active",
                                options=[
                                    {"label": "Enable this rule", "value": True},
                                ],
                                value=[True],
                                className="mb-3",
                            ),
                        ],
                        width=12,
                    ),
                ]
            ),
            html.Hr(),
            html.H5("Basic Configuration", className="mb-3"),
            html.P(
                "This is a simplified form. The full implementation would include condition editors, notification channels, and quiet hours.",
                className="text-muted mb-3",
            ),
        ],
        fluid=True,
    )


def register_notifications_callbacks(app):
    """Register all callbacks for the notifications tab."""

    @app.callback(
        Output("rules-list-container", "children"),
        [
            Input("reload-rules-btn", "n_clicks"),
            Input("create-rule-btn", "n_clicks"),
            Input("rule-modal-save", "n_clicks"),
            Input("rule-modal-cancel", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def update_rules_list(reload_clicks, create_clicks, save_clicks, cancel_clicks):
        """Update the rules list display."""
        manager = NotificationsManager()
        return render_rules_list(manager.load_rules())

    @app.callback(
        Output("rule-modal", "is_open"),
        [Input("create-rule-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def toggle_rule_modal(create_clicks):
        """Toggle rule modal visibility."""
        ctx = callback_context
        if not ctx.triggered:
            return False
        return ctx.triggered[0]["prop_id"].split(".")[0] == "create-rule-btn"

    @app.callback(
        Output("rule-modal-header", "children"),
        [Input("create-rule-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def update_modal_header(create_clicks):
        """Update modal header."""
        return dbc.ModalTitle("Create Alert Rule")

    @app.callback(
        Output("rule-modal-body", "children"),
        [Input("rule-modal", "is_open")],
        prevent_initial_call=False,
    )
    def update_modal_body(is_open):
        """Update modal body content."""
        if not is_open:
            return ""
        return render_rule_form()

    @app.callback(
        Output("rule-save-status", "children"),
        [Input("rule-modal-save", "n_clicks")],
        [
            State("rule-name-input", "value"),
            State("rule-description-input", "value"),
            State("rule-is-active", "value"),
        ],
        prevent_initial_call=True,
    )
    def save_rule(n_clicks, name, description, is_active):
        """Save rule from modal form."""
        if n_clicks == 0:
            return ""

        try:
            manager = NotificationsManager()

            new_rule = {
                "id": f"rule_{int(datetime.utcnow().timestamp())}",
                "name": name or "New Alert Rule",
                "description": description or "",
                "active": bool(is_active and is_active),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "conditions": [],
                "notification_channels": [{"type": "browser", "value": True}],
            }

            if manager.save_rule(new_rule):
                return dbc.Alert(
                    "Rule saved successfully!",
                    color="success",
                    dismissable=True,
                    duration=3000,
                    className="mt-3",
                )
            else:
                return dbc.Alert(
                    "Error saving rule",
                    color="danger",
                    dismissable=True,
                    duration=5000,
                    className="mt-3",
                )
        except Exception as e:
            return dbc.Alert(
                f"Error saving rule: {e!s}",
                color="danger",
                dismissable=True,
                duration=5000,
                className="mt-3",
            )

    app.logger.info("Notifications callbacks registered successfully")
