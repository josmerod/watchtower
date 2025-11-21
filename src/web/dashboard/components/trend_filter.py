from dash import html, dcc
import dash_bootstrap_components as dbc

def render_trend_filter(filter_id: str = "trend-filter"):
    """
    Renders a switch to toggle trending content.
    
    Args:
        filter_id: ID for the filter component
    """
    return dbc.Row(
        [
            dbc.Col(
                dbc.Switch(
                    id=filter_id,
                    label="🔥 Show Trending Only",
                    value=False,
                    className="d-flex align-items-center gap-2"
                ),
                width="auto"
            )
        ],
        className="mb-3"
    )