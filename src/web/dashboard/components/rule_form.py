"""Simple rule form components for alert rule creation and editing."""

from __future__ import annotations

from typing import Any, Dict

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.alerts.models import (
    AlertCondition,
    SourceMatchCondition,
    KeywordMatchCondition,
    CategoryMatchCondition,
    PriceThresholdCondition,
)


def render_condition_editor(condition: AlertCondition, condition_index: int) -> dbc.Card:
    """Render editor for a single condition."""
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
    """Render source match condition editor."""
    return dbc.Card([
        dbc.CardHeader(html.H6("Source Match", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Source *"),
                    dbc.Input(
                        id=f"source-value-{condition_index}",
                        placeholder="Enter source name or pattern",
                        value=condition.value,
                        type="text",
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Operator"),
                    dbc.Select(
                        id=f"source-operator-{condition_index}",
                        options=[
                            {"label": "Contains", "value": "contains"},
                            {"label": "Equals", "value": "equals"},
                        ],
                        value=condition.operator,
                    ),
                ], width=6),
            ]),
        ]),
    ], color="light", className="mb-3")


def render_keyword_condition_editor(condition: KeywordMatchCondition, condition_index: int) -> dbc.Card:
    """Render keyword match condition editor."""
    return dbc.Card([
        dbc.CardHeader(html.H6("Keyword Match", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Keyword *"),
                    dbc.Input(
                        id=f"keyword-value-{condition_index}",
                        placeholder="Enter keyword or phrase",
                        value=condition.value,
                        type="text",
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Operator"),
                    dbc.Select(
                        id=f"keyword-operator-{condition_index}",
                        options=[
                            {"label": "Contains", "value": "contains"},
                            {"label": "Equals", "value": "equals"},
                        ],
                        value=condition.operator,
                    ),
                ], width=6),
            ]),
        ]),
    ], color="light", className="mb-3")


def render_category_condition_editor(condition: CategoryMatchCondition, condition_index: int) -> dbc.Card:
    """Render category match condition editor."""
    return dbc.Card([
        dbc.CardHeader(html.H6("Category Match", className="mb-0")),
        dbc.CardBody([
            dbc.Label("Category *"),
            dbc.Select(
                id=f"category-value-{condition_index}",
                options=[
                    {"label": "Technology", "value": "Technology"},
                    {"label": "Science", "value": "Science"},
                    {"label": "Business", "value": "Business"},
                    {"label": "Education", "value": "Education"},
                ],
                value=condition.value,
            ),
        ]),
    ], color="light", className="mb-3")


def render_price_condition_editor(condition: PriceThresholdCondition, condition_index: int) -> dbc.Card:
    """Render price threshold condition editor."""
    return dbc.Card([
        dbc.CardHeader(html.H6("Price Threshold", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Price Value *"),
                    dbc.Input(
                        id=f"price-value-{condition_index}",
                        placeholder="Enter price value",
                        value=str(condition.value),
                        type="number",
                        step="0.01",
                        min="0",
                    ),
                ], width=4),
                dbc.Col([
                    dbc.Label("Operator"),
                    dbc.Select(
                        id=f"price-operator-{condition_index}",
                        options=[
                            {"label": "Less than", "value": "less_than"},
                            {"label": "Equals", "value": "equals"},
                            {"label": "Greater than", "value": "greater_than"},
                        ],
                        value=condition.operator,
                    ),
                ], width=4),
                dbc.Col([
                    dbc.Label("Currency"),
                    dbc.Select(
                        id=f"price-currency-{condition_index}",
                        options=[
                            {"label": "USD", "value": "USD"},
                            {"label": "EUR", "value": "EUR"},
                            {"label": "GBP", "value": "GBP"},
                        ],
                        value=condition.currency,
                    ),
                ], width=4),
            ]),
        ]),
    ], color="light", className="mb-3")


def render_test_results(results: Dict[str, Any]) -> dbc.Container:
    """Render rule test results."""
    if not results.get("matches", []):
        return dbc.Container([
            dbc.Alert(
                "No matches found in recent content. Try adjusting your rule conditions.",
                color="info",
                className="mt-3",
            ),
        ])

    matches = results["matches"]
    return dbc.Container([
        dbc.Alert(
            f"Found {len(matches)} matching items in recent content!",
            color="success",
            className="mb-3",
        ),
        dbc.ListGroup([
            dbc.ListGroupItem([
                html.H6(match.get("title", "No title"), className="mb-1"),
                html.P(match.get("description", "No description")[:100] + "...", className="mb-1"),
                html.Small([
                    html.Strong("Source: "),
                    match.get("source", "Unknown"),
                    " | ",
                    html.Strong("Matched at: "),
                    "Now",
                ]),
            ]) for match in matches[:10]  # Show first 10 matches
        ]),
    ])