"""Architecture Intelligence Dashboard Tab."""

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from src.data_quality.user_profile_manager import UserProfileManager
from src.intelligence.architecture_recommender import ArchitectureRecommender
from src.models.architecture_pattern_model import ArchitecturalStyle
from src.utils.logging import get_logger

logger = get_logger("ArchitectureTab")


def render_architecture_intelligence_tab() -> html.Div:
    """Render the Architecture Intelligence tab."""
    recommender = ArchitectureRecommender()
    patterns = recommender.get_all_patterns()

    return html.Div(
        [
            dbc.Container(
                [
                    # Header
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H2("🏗️ Architecture Intelligence", className="mb-3"),
                                    html.P(
                                        "Explore software architecture patterns, best practices, and get personalized recommendations.",
                                        className="text-muted",
                                    ),
                                ]
                            )
                        ],
                        className="mb-4",
                    ),
                    # Recommendations Section (Dynamic)
                    html.Div(id="arch-recommendations-section"),
                    # Pattern Browser
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                html.H4(
                                                                    "📚 Pattern Catalog",
                                                                    className="mb-0",
                                                                ),
                                                                width=8,
                                                            ),
                                                            dbc.Col(
                                                                dbc.Input(
                                                                    id="arch-pattern-search",
                                                                    placeholder="Search patterns...",
                                                                    type="text",
                                                                ),
                                                                width=4,
                                                            ),
                                                        ],
                                                        align="center",
                                                    )
                                                ]
                                            ),
                                            dbc.CardBody(
                                                [
                                                    # Filters
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label("Filter by Style:"),
                                                                    dcc.Dropdown(
                                                                        id="arch-style-filter",
                                                                        options=[
                                                                            {
                                                                                "label": style.value,
                                                                                "value": style.value,
                                                                            }
                                                                            for style in ArchitecturalStyle
                                                                        ],
                                                                        placeholder="All Styles",
                                                                        clearable=True,
                                                                    ),
                                                                ],
                                                                width=4,
                                                            )
                                                        ],
                                                        className="mb-4",
                                                    ),
                                                    # Pattern Grid
                                                    html.Div(id="arch-pattern-grid"),
                                                ]
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ]
                    ),
                    # Pattern Details Modal
                    dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle(id="arch-modal-title")),
                            dbc.ModalBody(id="arch-modal-body"),
                            dbc.ModalFooter(
                                dbc.Button(
                                    "Close",
                                    id="arch-modal-close",
                                    className="ms-auto",
                                    n_clicks=0,
                                )
                            ),
                        ],
                        id="arch-pattern-modal",
                        size="lg",
                        is_open=False,
                    ),
                ],
                fluid=True,
            )
        ]
    )


def register_architecture_callbacks(app):
    """Register callbacks for the Architecture tab."""
    recommender = ArchitectureRecommender()
    profile_manager = UserProfileManager()

    @app.callback(
        Output("arch-pattern-grid", "children"),
        [Input("arch-pattern-search", "value"), Input("arch-style-filter", "value")],
    )
    def update_pattern_grid(search_term, style_filter):
        """Update the grid of patterns based on search and filter."""
        patterns = recommender.get_all_patterns()

        filtered_patterns = patterns

        if style_filter:
            filtered_patterns = [p for p in filtered_patterns if p.style.value == style_filter]

        if search_term:
            term = search_term.lower()
            filtered_patterns = [p for p in filtered_patterns if term in p.name.lower() or term in p.description.lower() or term in p.summary.lower()]

        if not filtered_patterns:
            return html.Div(
                "No patterns found matching your criteria.",
                className="text-center text-muted my-5",
            )

        # Create grid
        cards = []
        for pattern in filtered_patterns:
            card = dbc.Col(
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                dbc.Badge(pattern.style.value, color="info", className="mb-2"),
                                html.H5(pattern.name, className="card-title"),
                                html.P(
                                    pattern.summary,
                                    className="card-text small text-muted",
                                ),
                                dbc.Button(
                                    "View Details",
                                    id={
                                        "type": "arch-pattern-btn",
                                        "index": pattern.pattern_id,
                                    },
                                    color="primary",
                                    size="sm",
                                    outline=True,
                                    className="mt-2",
                                ),
                            ],
                            className="h-100",
                        )
                    ],
                    className="h-100 shadow-sm",
                ),
                width=12,
                md=6,
                lg=4,
                className="mb-4",
            )
            cards.append(card)

        return dbc.Row(cards)

    @app.callback(
        [
            Output("arch-pattern-modal", "is_open"),
            Output("arch-modal-title", "children"),
            Output("arch-modal-body", "children"),
        ],
        [
            Input({"type": "arch-pattern-btn", "index": ALL}, "n_clicks"),
            Input("arch-modal-close", "n_clicks"),
        ],
        [State("arch-pattern-modal", "is_open")],
    )
    def toggle_modal(n_clicks, close_click, is_open):
        """Toggle pattern details modal."""
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "arch-modal-close":
            return False, "", ""

        if "arch-pattern-btn" in trigger_id:
            # Get pattern ID from trigger
            import json

            trigger_obj = json.loads(trigger_id)
            pattern_id = trigger_obj["index"]

            pattern = recommender.get_pattern_by_id(pattern_id)
            if not pattern:
                return is_open, "Error", "Pattern not found"

            # Build modal content
            content = html.Div(
                [
                    dbc.Badge(
                        pattern.complexity.value + " Complexity",
                        color=("warning" if pattern.complexity.value in ["High", "Very High"] else "success"),
                        className="me-2",
                    ),
                    dbc.Badge(
                        pattern.scalability_level + " Scalability",
                        color="info",
                        className="me-2",
                    ),
                    html.Hr(),
                    html.H5("Description"),
                    html.P(pattern.description),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H6("✅ When to Use", className="text-success"),
                                    html.Ul([html.Li(item) for item in pattern.when_to_use]),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.H6("❌ When Not to Use", className="text-danger"),
                                    html.Ul([html.Li(item) for item in pattern.when_not_to_use]),
                                ],
                                width=6,
                            ),
                        ]
                    ),
                    html.H6("Compatible Technologies", className="mt-3"),
                    html.Div(
                        [
                            dbc.Badge(
                                tech,
                                color="light",
                                text_color="dark",
                                className="me-1 border",
                            )
                            for tech in pattern.compatible_technologies
                        ]
                    ),
                    html.H6("Real World Examples", className="mt-3"),
                    html.Div([dbc.Badge(ex, color="secondary", className="me-1") for ex in pattern.real_world_examples]),
                ]
            )

            return True, pattern.name, content

        return is_open, "", ""

    @app.callback(
        Output("arch-recommendations-section", "children"),
        Input("arch-pattern-grid", "children"),  # Trigger on load
    )
    def load_recommendations(_):
        """Load recommendations if user profile exists."""
        # Hardcoded user ID for demo - in real app would come from session/context
        user_id = "demo_user"
        profile = profile_manager.load_profile(user_id)

        if not profile or not profile.tech_stack:
            return html.Div()  # No recommendations if no profile/stack

        recommendations = recommender.recommend_patterns(profile, top_n=3)

        if not recommendations:
            return html.Div()

        cards = []
        for pattern, score, breakdown in recommendations:
            explanation = recommender.explain_recommendation(pattern, breakdown)
            cards.append(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6(
                                        "Recommended for You",
                                        className="text-success small mb-2",
                                    ),
                                    html.H5(pattern.name, className="card-title"),
                                    html.P(explanation, className="small text-muted"),
                                    dbc.Progress(
                                        value=score * 100,
                                        color="success",
                                        className="mb-2",
                                        style={"height": "5px"},
                                    ),
                                    dbc.Button(
                                        "View",
                                        id={
                                            "type": "arch-pattern-btn",
                                            "index": pattern.pattern_id,
                                        },
                                        color="link",
                                        size="sm",
                                        className="p-0",
                                    ),
                                ]
                            )
                        ],
                        className="h-100 border-success",
                    ),
                    width=12,
                    md=4,
                )
            )

        return dbc.Row(
            [
                dbc.Col(html.H4("✨ Recommended Patterns", className="mb-3"), width=12),
                *cards,
            ],
            className="mb-5",
        )
