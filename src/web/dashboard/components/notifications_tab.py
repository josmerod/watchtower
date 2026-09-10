"""Fixed Notifications tab implementation with working callbacks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback_context, html

from src.alerts import rules_store
from src.services.watcher_events import WatcherEventsSummary, build_daily_summary


def _get_rule_id(rule: Any) -> str:
    """Extract a rule ID from rule objects, dicts, or bare ID values.

    Args:
        rule: A rule object with an ``id`` attribute, a rule dict with an ``id``
            key, or a bare rule-ID value.

    Returns:
        The rule ID as a string (empty string when none is available).
    """
    if hasattr(rule, "id"):
        return str(rule.id)
    if isinstance(rule, dict):
        return str(rule.get("id", ""))
    return str(rule)


class NotificationsManager:
    """Manager for alert rules, delegating to the shared :mod:`src.alerts.rules_store`.

    The store path is passed explicitly as a cwd-relative path (production runs
    from the project root) so tests can isolate writes with ``monkeypatch.chdir``.
    """

    def __init__(self):
        self.rules_file = Path("data/alerts/rules.json")
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)

    def load_rules(self) -> list[dict[str, Any]]:
        """Load all alert rules from the shared store (empty when absent)."""
        return rules_store.load_rules(self.rules_file)

    def save_rule(self, rule: dict[str, Any]) -> bool:
        """Insert or update a rule by id via the shared store.

        Args:
            rule: Rule dictionary; an existing rule with the same ``id`` is
                replaced, otherwise the rule is appended.

        Returns:
            ``True`` on success (including a no-op unchanged payload),
            ``False`` if the write failed.
        """
        try:
            rules_store.upsert_rule(rule, rules_file=self.rules_file)
            return True
        except OSError:
            return False

    def delete_rule(self, rule_id: str) -> bool:
        """Remove a rule by id from the shared store.

        Args:
            rule_id: ID of the rule to remove.

        Returns:
            ``True`` if the rule was present and removed, ``False`` otherwise.
        """
        try:
            return rules_store.resolve_rule(rule_id, rules_file=self.rules_file)
        except OSError:
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
            # Daily resumen (T-083): last-24h watcher events, above the rules.
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    html.H5("📅 Últimas 24h", className="mb-0"),
                                                    width="auto",
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        "Actualizar",
                                                        id="daily-summary-refresh-btn",
                                                        color="secondary",
                                                        outline=True,
                                                        size="sm",
                                                        n_clicks=0,
                                                    ),
                                                    width="auto",
                                                    className="ms-auto",
                                                ),
                                            ],
                                            align="center",
                                            justify="between",
                                        )
                                    ),
                                    dbc.CardBody(html.Div(id="daily-summary-container")),
                                ],
                                className="mb-4",
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

        # Watcher-managed rules (e.g. data freshness) carry a severity.
        severity = str(rule.get("severity", "")).lower()
        if severity:
            status_badges = [
                status_badge,
                dbc.Badge(severity.upper(), color="danger" if severity == "high" else "warning", className="ms-1"),
            ]
        else:
            status_badges = [status_badge]

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
                                        *status_badges,
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


def render_daily_summary_section(summary: WatcherEventsSummary) -> html.Div:
    """Render the last-24h watcher-events resumen.

    Shows a headline with the total, one row per ``(watcher, event_type)``
    group (watcher badge, type badge, sample message from the latest event,
    count and relative timestamp) and a per-watcher breakdown footer. A calm
    muted note replaces everything when the window is empty.

    Args:
        summary: Precompiled summary from ``build_daily_summary``.

    Returns:
        Dash layout for the ``daily-summary-container`` body.
    """
    if summary.total == 0:
        return html.Div(
            html.P(
                f"Sin eventos en las últimas {summary.window_hours}h. Los watchers publicarán aquí sus cambios.",
                className="text-muted mb-0",
            )
        )

    plural = "s" if summary.total != 1 else ""
    headline = html.P(
        [
            html.Strong(str(summary.total)),
            f" evento{plural} en las últimas {summary.window_hours}h",
        ],
        className="mb-3",
    )

    rows: list[dbc.ListGroupItem] = []
    for group in summary.groups:
        rows.append(
            dbc.ListGroupItem(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Badge(group.watcher, color="info", pill=True, className="me-2"),
                                dbc.Badge(group.event_type, color="secondary", pill=True),
                                html.Span(group.message, className="d-block mt-1"),
                            ],
                            width=12,
                            lg=8,
                        ),
                        dbc.Col(
                            [
                                dbc.Badge(f"×{group.count}", color="primary", pill=True),
                                html.Small(group.latest_relative, className="text-muted ms-2"),
                            ],
                            width=12,
                            lg=4,
                            className="text-lg-end mt-2 mt-lg-0",
                        ),
                    ],
                    align="start",
                )
            )
        )

    breakdown = " · ".join(f"{watcher}: {count}" for watcher, count in summary.per_watcher.items())
    footer = html.Small(f"Por watcher: {breakdown}", className="text-muted")

    return html.Div([headline, dbc.ListGroup(rows, className="mb-2"), footer])


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

    @app.callback(
        Output("daily-summary-container", "children"),
        [Input("daily-summary-refresh-btn", "n_clicks")],
        prevent_initial_call=False,
    )
    def update_daily_summary(refresh_clicks):
        """Render the last-24h watcher-events resumen.

        Follows the tab's existing reload pattern (cf. ``reload-rules-btn``):
        ``prevent_initial_call=False`` populates the section on page load and
        every click of ``Actualizar`` re-scans the event files. For a
        daily-review view that refresh-on-load is the intended behaviour.
        """
        try:
            return render_daily_summary_section(build_daily_summary())
        except Exception as e:
            return dbc.Alert(
                f"Error loading the daily summary: {e!s}",
                color="danger",
                dismissable=True,
                className="mb-0",
            )

    app.logger.info("Notifications callbacks registered successfully")
