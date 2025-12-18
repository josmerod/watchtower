import json
from pathlib import Path
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html, dcc, Output, Input, State
import pandas as pd

from src.config.settings import get_settings

settings = get_settings()

# Define the data path
DATA_DIR = Path(settings.data_dir) / "startup_intelligence/output"
LATEST_DATA_FILE = DATA_DIR / "startup_intelligence_latest.json"

def get_startup_data():
    """Load startup data from the latest JSON file."""
    if not LATEST_DATA_FILE.exists():
        return []
    
    try:
        data = json.loads(LATEST_DATA_FILE.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        print(f"Error loading startup data: {e}")
        return []

def render_startup_intelligence_tab():
    """Render the Startup Intelligence tab layout."""
    return html.Div(
        [
            dcc.Interval(id="startup-interval", interval=600 * 1000, n_intervals=0), # Refresh every 10 mins
            html.Div(id="startup-content"),
        ],
        className="p-4",
    )

def register_startup_callbacks(app):
    """Register callbacks for the Startup Intelligence tab."""
    
    @app.callback(
        Output("startup-content", "children"),
        [Input("startup-interval", "n_intervals")]
    )
    def update_startup_content(n):
        data = get_startup_data()
        
        if not data:
            return dbc.Alert("No startup data found. Please run the ETL pipeline.", color="warning")
            
        # Segregate data
        ph_items = [d for d in data if d.get('source') == 'product_hunt']
        tc_items = [d for d in data if d.get('source') == 'techcrunch']
        
        # Sort by relevance/date
        # PH: votes
        ph_items.sort(key=lambda x: x.get('votes', 0), reverse=True)
        # TC: date
        tc_items.sort(key=lambda x: x.get('published_at', ''), reverse=True)

        return html.Div([
            # Hero Section: Top Product Hunt Launches
            html.H3("🚀 Top Product Hunt Launches", className="mb-4 text-primary"),
            dbc.Row(
                [
                    dbc.Col(_render_ph_card(item), width=12, md=6, lg=4)
                    for item in ph_items[:6] # Top 6
                ],
                className="g-4 mb-5"
            ),
            
            # News Section
            html.H3("📰 TechCrunch Startup News", className="mb-4 text-success"),
            dbc.Row(
                [
                     dbc.Col(_render_news_list(tc_items), width=12, lg=8),
                     dbc.Col(_render_trending_companies(data), width=12, lg=4)
                ]
            )
        ])

def _render_ph_card(item):
    """Render a Product Hunt item card."""
    return dbc.Card(
        [
            dbc.CardImg(src=item.get("thumbnail_url"), top=True, style={"height": "200px", "object-fit": "cover"}) if item.get("thumbnail_url") else None,
            dbc.CardBody(
                [
                    html.H5(
                        html.A(item.get("title"), href=item.get("url"), target="_blank", className="text-decoration-none text-dark"),
                        className="card-title"
                    ),
                    html.P(item.get("summary") or item.get("tagline"), className="card-text text-muted small"),
                    html.Div(
                        [
                            html.Span(f"🔼 {item.get('votes', 0)}", className="badge bg-primary me-2"),
                            html.Span(f"💬 {item.get('comments', 0)}", className="badge bg-secondary"),
                        ],
                        className="d-flex align-items-center"
                    )
                ]
            )
        ],
        className="h-100 shadow-sm hover-shadow transition-all"
    )

def _render_news_list(items):
    """Render a list of news items."""
    return dbc.ListGroup(
        [
            dbc.ListGroupItem(
                [
                    html.Div(
                        [
                            html.H6(html.A(item.get("title"), href=item.get("url"), target="_blank", className="text-decoration-none")),
                            html.Small(item.get("published_at")[:10], className="text-muted")
                        ],
                        className="d-flex justify-content-between align-items-center mb-1"
                    ),
                    html.P(item.get("summary")[:200] + "..." if item.get("summary") else "", className="mb-1 small text-muted"),
                    html.Div(
                        [
                             html.Span(tag, className="badge bg-light text-dark me-1 border")
                             for tag in item.get("tags", [])[:3]
                        ]
                    )
                ],
                className="py-3"
            )
            for item in items[:15]
        ],
        flush=True
    )

def _render_trending_companies(data):
    """Render a list of trending companies based on mentions."""
    # Count company mentions
    mentions = {}
    for item in data:
        for company in item.get("company_mentioned", []):
            mentions[company] = mentions.get(company, 0) + 1
            
    sorted_mentions = sorted(mentions.items(), key=lambda x: x[1], reverse=True)
    
    if not sorted_mentions:
        return html.Div()
        
    return dbc.Card(
        [
            dbc.CardHeader("🔥 Trending Companies"),
            dbc.ListGroup(
                [
                    dbc.ListGroupItem(
                        [
                            html.Span(company, className="fw-bold"),
                            html.Span(f"{count} mentions", className="badge bg-danger rounded-pill")
                        ],
                        className="d-flex justify-content-between align-items-center"
                    )
                    for company, count in sorted_mentions[:10]
                ],
                flush=True
            )
        ]
    )
