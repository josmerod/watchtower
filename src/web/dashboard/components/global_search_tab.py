"""Global Search Dashboard Tab
Unified search across all intelligence domains.
"""

import logging
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html, dcc, ALL

from src.web.dashboard.meta_search import meta_search_engine

logger = logging.getLogger(__name__)

def create_global_search_layout():
    """Create the layout for Global Search tab."""
    return html.Div(
        [
            # Search Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [html.I(className="fas fa-search me-2"), "Global Intelligence Search"],
                                className="text-center text-primary mb-4"
                            ),
                            # Search Bar
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="global-search-input",
                                        placeholder="Search across Videos, News, Research Papers...",
                                        type="text",
                                        size="lg",
                                        className="rounded-pill p-3",
                                        style={"fontSize": "1.2rem"}
                                    ),
                                    dbc.Button(
                                        [html.I(className="fas fa-search me-2"), "Search"],
                                        id="global-search-btn",
                                        color="primary",
                                        className="rounded-pill px-4 ms-2",
                                    ),
                                ],
                                className="mb-4",
                                style={"maxWidth": "800px", "margin": "0 auto"}
                            ),
                            # Filter Toggles (Visual only for now, could act as real filters)
                            html.Div(
                                [
                                    dbc.RadioItems(
                                        id="global-search-type",
                                        options=[
                                            {"label": "All", "value": "all"},
                                            {"label": "Videos", "value": "video"},
                                            {"label": "News", "value": "news"},
                                            {"label": "Research", "value": "paper"},
                                        ],
                                        value="all",
                                        inline=True,
                                        className="mb-3 justify-content-center d-flex gap-3",
                                        inputClassName="btn-check",
                                        labelClassName="btn btn-outline-secondary rounded-pill",
                                        labelCheckedClassName="active",
                                    )
                                ],
                                className="text-center"
                            )
                        ],
                        width=12,
                        className="py-5"
                    )
                ]
            ),
            
            # Results Container
            html.Div(
                id="global-search-results",
                className="mt-4"
            )
        ]
    )

def render_result_card(item):
    """Render a single search result as a card."""
    
    # Icon and Color based on type
    type_config = {
        "video": {"icon": "fas fa-video", "color": "danger"},
        "news": {"icon": "fas fa-newspaper", "color": "success"},
        "paper": {"icon": "fas fa-graduation-cap", "color": "info"},
    }
    
    config = type_config.get(item["type"], {"icon": "fas fa-file", "color": "secondary"})
    
    return dbc.Col(
        dbc.Card(
            [
                # Image for videos
                dbc.CardImg(src=item["image"], top=True) if item.get("image") else None,
                
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                dbc.Badge(
                                    [html.I(className=f"{config['icon']} me-1"), item["type"].title()],
                                    color=config["color"],
                                    className="me-2 mb-2"
                                ),
                                html.Small(item.get("date_display", ""), className="text-muted")
                            ]
                        ),
                        html.H5(
                            html.A(
                                item["title"], 
                                href=item["url"], 
                                target="_blank",
                                className="text-decoration-none"
                            ),
                            className="card-title"
                        ),
                        html.H6(item["source"], className="card-subtitle mb-2 text-muted small"),
                        html.P(
                            item["summary"],
                            className="card-text small text-muted",
                            style={
                                "display": "-webkit-box",
                                "-webkitLineClamp": "3",
                                "-webkitBoxOrient": "vertical",
                                "overflow": "hidden"
                            }
                        ),
                    ]
                ),
                dbc.CardFooter(
                    html.A(
                        "Open Link",
                        href=item["url"],
                        target="_blank",
                        className="btn btn-sm btn-outline-primary w-100"
                    )
                )
            ],
            className="h-100 shadow-sm hover-shadow"
        ),
        xs=12, sm=6, md=4, lg=3,
        className="mb-4"
    )

def register_global_search_callbacks(app):
    """Register callbacks for Global Search."""
    
    @app.callback(
        Output("global-search-results", "children"),
        [Input("global-search-btn", "n_clicks"),
         Input("global-search-input", "n_submit")],
        [State("global-search-input", "value"),
         State("global-search-type", "value")],
        prevent_initial_call=True
    )
    def update_results(n_clicks, n_submit, query, filter_type):
        if not query:
            return html.Div(
                dbc.Alert("Please enter a search term.", color="warning"),
                className="text-center"
            )
            
        try:
            results = meta_search_engine.search(query)
            
            # Client-side filtering if 'filter_type' is not 'all'
            # (Ideally MetaSearchEngine could take this arg, but this works for now)
            if filter_type != "all":
                results = [r for r in results if r["type"] == filter_type]
            
            if not results:
                return html.Div(
                    [
                        html.I(className="fas fa-search-minus fa-3x text-muted mb-3"),
                        html.H4("No results found", className="text-muted"),
                        html.P(f"We couldn't find anything matching '{query}'", className="text-muted")
                    ],
                    className="text-center py-5"
                )
                
            # Render grid
            return dbc.Row(
                [render_result_card(item) for item in results]
            )
            
        except Exception as e:
            logger.error(f"Global search error: {e}")
            return dbc.Alert(f"An error occurred while searching: {e}", color="danger")
