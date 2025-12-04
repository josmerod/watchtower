"""Rule form components for alert rule creation and editing.

This module provides specialized form components for creating and editing
alert rule conditions and configurations.
"""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.alerts.models import (
    AlertCondition,
    CategoryMatchCondition,
    KeywordMatchCondition,
    PriceThresholdCondition,
    SourceMatchCondition,
)


def render_add_condition_modal() -> dbc.Modal:
    return dbc.Modal([])


def render_condition_editor(condition: AlertCondition, condition_index: int) -> dbc.Card:
    """Render editor for a single condition.

    Args:
        condition: AlertCondition object to edit
        condition_index: Index of condition in the list

    Returns:
        Dash component with condition editor
    """
    condition_type = condition.condition_type

    if condition_type == "source_match":
        return render_source_condition_editor(condition, condition_index)
    elif condition_type == "keyword_match":
        return render_keyword_condition_editor(condition, condition_index)
    elif condition_type == "category_match":
        return render_category_condition_editor(condition, condition_index)
    elif condition_type == "price_threshold":
        return render_price_condition_editor(condition, condition_index)
    else:
        return dbc.Alert(f"Unknown condition type: {condition_type}", color="warning")


def render_source_condition_editor(condition: SourceMatchCondition, condition_index: int) -> dbc.Card:
    """Render source match condition editor.

    Args:
        condition: SourceMatchCondition object
        condition_index: Index of condition

    Returns:
        Dash component with source condition editor
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6("Source Match", className="mb-0"),
                    dbc.Button(
                        "×",
                        id=f"remove-condition-{condition_index}",
                        color="danger",
                        outline=True,
                        size="sm",
                        className="float-end",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Source *", html_for=f"source-value-{condition_index}"),
                                    dbc.Input(
                                        id=f"source-value-{condition_index}",
                                        placeholder="Enter source name or pattern",
                                        value=condition.value,
                                        type="text",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Operator", html_for=f"source-operator-{condition_index}"),
                                    dbc.Select(
                                        id=f"source-operator-{condition_index}",
                                        options=[
                                            {"label": "Contains", "value": "contains"},
                                            {"label": "Equals", "value": "equals"},
                                            {"label": "Starts with", "value": "starts_with"},
                                            {"label": "Ends with", "value": "ends_with"},
                                        ],
                                        value=condition.operator,
                                    ),
                                ],
                                width=6,
                            ),
                        ]
                    ),
                ]
            ),
        ],
        color="light",
        className="mb-3",
    )


def render_keyword_condition_editor(condition: KeywordMatchCondition, condition_index: int) -> dbc.Card:
    """Render keyword match condition editor.

    Args:
        condition: KeywordMatchCondition object
        condition_index: Index of condition

    Returns:
        Dash component with keyword condition editor
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6("Keyword Match", className="mb-0"),
                    dbc.Button(
                        "×",
                        id=f"remove-condition-{condition_index}",
                        color="danger",
                        outline=True,
                        size="sm",
                        className="float-end",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Keyword *", html_for=f"keyword-value-{condition_index}"),
                                    dbc.Input(
                                        id=f"keyword-value-{condition_index}",
                                        placeholder="Enter keyword or phrase",
                                        value=condition.value,
                                        type="text",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Operator", html_for=f"keyword-operator-{condition_index}"),
                                    dbc.Select(
                                        id=f"keyword-operator-{condition_index}",
                                        options=[
                                            {"label": "Contains", "value": "contains"},
                                            {"label": "Equals", "value": "equals"},
                                            {"label": "Starts with", "value": "starts_with"},
                                            {"label": "Ends with", "value": "ends_with"},
                                        ],
                                        value=condition.operator,
                                    ),
                                ],
                                width=6,
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Checklist(
                                        [
                                            dbc.ChecklistItem(
                                                "Case sensitive",
                                                id=f"keyword-case-sensitive-{condition_index}",
                                                checked=getattr(condition, "case_sensitive", False),
                                            ),
                                        ],
                                        id=f"keyword-case-checklist-{condition_index}",
                                    ),
                                ],
                                width=12,
                                className="mt-3",
                            ),
                        ]
                    ),
                ]
            ),
        ],
        color="light",
        className="mb-3",
    )


def render_category_condition_editor(condition: CategoryMatchCondition, condition_index: int) -> dbc.Card:
    """Render category match condition editor.

    Args:
        condition: CategoryMatchCondition object
        condition_index: Index of condition

    Returns:
        Dash component with category condition editor
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6("Category Match", className="mb-0"),
                    dbc.Button(
                        "×",
                        id=f"remove-condition-{condition_index}",
                        color="danger",
                        outline=True,
                        size="sm",
                        className="float-end",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Category *", html_for=f"category-value-{condition_index}"),
                                    dbc.Select(
                                        id=f"category-value-{condition_index}",
                                        options=[
                                            {"label": "Technology", "value": "Technology"},
                                            {"label": "Science", "value": "Science"},
                                            {"label": "Business", "value": "Business"},
                                            {"label": "Education", "value": "Education"},
                                            {"label": "Entertainment", "value": "Entertainment"},
                                            {"label": "Health", "value": "Health"},
                                            {"label": "Finance", "value": "Finance"},
                                            {"label": "Gaming", "value": "Gaming"},
                                            {"label": "Programming", "value": "Programming"},
                                            {"label": "AI", "value": "AI"},
                                            {"label": "Machine Learning", "value": "Machine Learning"},
                                            {"label": "Data Science", "value": "Data Science"},
                                        ],
                                        value=condition.value,
                                    ),
                                ],
                                width=12,
                            ),
                        ]
                    ),
                ]
            ),
        ],
        color="light",
        className="mb-3",
    )


def render_price_condition_editor(condition: PriceThresholdCondition, condition_index: int) -> dbc.Card:
    """Render price threshold condition editor.

    Args:
        condition: PriceThresholdCondition object
        condition_index: Index of condition

    Returns:
        Dash component with price condition editor
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H6("Price Threshold", className="mb-0"),
                    dbc.Button(
                        "×",
                        id=f"remove-condition-{condition_index}",
                        color="danger",
                        outline=True,
                        size="sm",
                        className="float-end",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Price Value *", html_for=f"price-value-{condition_index}"),
                                    dbc.Input(
                                        id=f"price-value-{condition_index}",
                                        placeholder="Enter price value",
                                        value=str(condition.value),
                                        type="number",
                                        step="0.01",
                                        min="0",
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Operator", html_for=f"price-operator-{condition_index}"),
                                    dbc.Select(
                                        id=f"price-operator-{condition_index}",
                                        options=[
                                            {"label": "Less than", "value": "less_than"},
                                            {"label": "Less than or equal", "value": "less_equal"},
                                            {"label": "Equals", "value": "equals"},
                                            {"label": "Greater than", "value": "greater_than"},
                                            {"label": "Greater than or equal", "value": "greater_equal"},
                                        ],
                                        value=condition.operator,
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Currency", html_for=f"price-currency-{condition_index}"),
                                    dbc.Select(
                                        id=f"price-currency-{condition_index}",
                                        options=[
                                            {"label": "USD", "value": "USD"},
                                            {"label": "EUR", "value": "EUR"},
                                            {"label": "GBP", "value": "GBP"},
                                            {"label": "JPY", "value": "JPY"},
                                        ],
                                        value=condition.currency,
                                    ),
                                ],
                                width=4,
                            ),
                        ]
                    ),
                ]
            ),
        ],
        color="light",
        className="mb-3",
    )


def render_quiet_hours_config() -> dbc.Container:
    return dbc.Container(
        [
            html.P(
                "Configure times when notifications should be suppressed.",
                className="text-muted mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Start Time", html_for="quiet-hours-start"),
                            dbc.Input(
                                id="quiet-hours-start",
                                type="time",
                                value="22:00",
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("End Time", html_for="quiet-hours-end"),
                            dbc.Input(
                                id="quiet-hours-end",
                                type="time",
                                value="08:00",
                            ),
                        ],
                        width=6,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Label("Days of Week", html_for="quiet-hours-days"),
            dcc.Checklist(
                id="quiet-hours-days",
                options=[
                    {"label": "Monday", "value": 0},
                    {"label": "Tuesday", "value": 1},
                    {"label": "Wednesday", "value": 2},
                    {"label": "Thursday", "value": 3},
                    {"label": "Friday", "value": 4},
                    {"label": "Saturday", "value": 5},
                    {"label": "Sunday", "value": 6},
                ],
                value=[0, 1, 2, 3, 4, 5, 6],  # All days selected by default
                inline=True,
                className="mb-3",
            ),
            dbc.Alert(
                html.Small(["Note: Time ranges that cross midnight (e.g., 22:00 to 08:00) are handled correctly."]),
                color="info",
            ),
        ],
        fluid=True,
    )


def render_test_results(results: dict[str, Any]) -> dbc.Container:
    """Render rule test results.

    Args:
        results: Test results dictionary

    Returns:
        Dash component with test results
    """
    if not results.get("matches", []):
        return dbc.Container(
            [
                dbc.Alert(
                    "No matches found in recent content. Try adjusting your rule conditions.",
                    color="info",
                    className="mt-3",
                ),
            ],
            fluid=True,
        )

    matches = results["matches"]
    return dbc.Container(
        [
            dbc.Alert(
                f"Found {len(matches)} matching items in recent content!",
                color="success",
                className="mb-3",
            ),
            dbc.ListGroup(
                [
                    dbc.ListGroupItem(
                        [
                            html.H6(match.get("title", "No title"), className="mb-1"),
                            html.P(match.get("description", "No description")[:100] + "...", className="mb-1"),
                            html.Small(
                                [
                                    html.Strong("Source: "),
                                    match.get("source", "Unknown"),
                                    " | ",
                                    html.Strong("Matched at: "),
                                    "Now",
                                ]
                            ),
                        ]
                    )
                    for match in matches[:10]  # Show first 10 matches
                ]
            ),
        ],
        fluid=True,
    )
