"""Minimal Metrics Tab for testing
Simple metrics dashboard to test component integration
"""

import dash_bootstrap_components as dbc
from dash import html


def render_metrics_tab():
    """Render the metrics dashboard tab with simple layout."""

    return html.Div([
        html.H2("📊 System Metrics", className="mb-4"),

        # Simple summary cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("15", className="text-primary mb-0"),
                        html.P("Total ETL Sources", className="text-secondary small mb-0",
                             style={"color": "#6c757d !important", "fontWeight": "500"}),
                    ])
                ], color="light", outline=True)
            ], width=12, md=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("98.5%", className="text-success mb-0"),
                        html.P("Success Rate", className="text-secondary small mb-0",
                             style={"color": "#6c757d !important", "fontWeight": "500"}),
                    ])
                ], color="light", outline=True)
            ], width=12, md=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("2.3s", className="text-info mb-0"),
                        html.P("Avg Duration", className="text-secondary small mb-0",
                             style={"color": "#6c757d !important", "fontWeight": "500"}),
                    ])
                ], color="light", outline=True)
            ], width=12, md=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("1,247", className="text-warning mb-0"),
                        html.P("Items Processed", className="text-secondary small mb-0",
                             style={"color": "#6c757d !important", "fontWeight": "500"}),
                    ])
                ], color="light", outline=True)
            ], width=12, md=3),
        ], className="mb-4"),

        # Placeholder for charts
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("📈 Performance Charts", className="card-title text-primary"),
                        html.P("Interactive charts and visualizations will be displayed here...",
                             className="text-secondary",
                             style={"color": "#6c757d !important"}),
                        html.Div([
                            html.Div(style={"height": "200px",
                                       "backgroundColor": "#f8f9fa",
                                       "border": "2px dashed #dee2e6",
                                       "borderRadius": "8px",
                                       "display": "flex",
                                       "alignItems": "center",
                                       "justifyContent": "center"},
                                   html.P("📊 Chart Area",
                                          className="text-muted mb-0",
                                          style={"color": "#6c757d !important", "fontSize": "18px"}))
                        ], className="mt-3")
                    ])
                ], color="light", outline=True)
            ], width=12),
        ]),
    ])


def register_metrics_callbacks(app):
    """Register callbacks for the metrics tab (minimal version)."""
    # No callbacks for now - just static content
    pass