"""Developer News Intelligence Dashboard Tab."""

from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import json
from pathlib import Path
from datetime import datetime

from src.models.developer_news import SmartNewsItem, NewsCategory
from src.utils.file_system import get_project_root
from src.utils.logging import get_logger

logger = get_logger("DeveloperNewsTab")

def render_developer_news_tab() -> html.Div:
    """Render the Developer News Intelligence tab.
    
    Returns:
        Dash HTML component
    """
    return html.Div([
        dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("📰 Developer News & Tips", className="mb-3"),
                    html.P(
                        "AI-curated news feed with summaries, trend analysis, and expert commentary.",
                        className="text-muted"
                    )
                ])
            ], className="mb-4"),
            
            # Filters
            dbc.Row([
                dbc.Col([
                    dbc.Label("Category:"),
                    dcc.Dropdown(
                        id="dev-news-category-filter",
                        options=[
                            {"label": c.value, "value": c.value}
                            for c in NewsCategory
                        ],
                        placeholder="All Categories",
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([
                    dbc.Label("Sort By:"),
                    dcc.Dropdown(
                        id="dev-news-sort-filter",
                        options=[
                            {"label": "Trending Score", "value": "trend"},
                            {"label": "Newest First", "value": "date"}
                        ],
                        value="trend",
                        clearable=False,
                        className="mb-3"
                    )
                ], width=4),
            ]),
            
            # Content Area
            dbc.Row([
                # Main Feed
                dbc.Col([
                    html.H4("Smart Feed", className="mb-3"),
                    html.Div(id="dev-news-feed-container")
                ], width=8),
                
                # Sidebar: Trends & Expert Picks
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📈 Trending Topics"),
                        dbc.CardBody(id="dev-news-trends-container")
                    ], className="mb-4 border-info"),
                    
                    dbc.Card([
                        dbc.CardHeader("💡 Expert Commentary"),
                        dbc.CardBody(id="dev-news-expert-container")
                    ], className="mb-4 border-warning")
                ], width=4)
            ])
        ], fluid=True)
    ])

def register_developer_news_callbacks(app):
    """Register callbacks for the Developer News tab."""
    
    @app.callback(
        [Output("dev-news-feed-container", "children"),
         Output("dev-news-trends-container", "children"),
         Output("dev-news-expert-container", "children")],
        [Input("dev-news-category-filter", "value"),
         Input("dev-news-sort-filter", "value")]
    )
    def update_news_content(category, sort_by):
        """Update news content based on filters."""
        try:
            # Load data
            project_root = Path(get_project_root())
            data_file = project_root / "data" / "developer_news" / "output" / "smart_news.json"
            
            if not data_file.exists():
                return (
                    dbc.Alert("No news data found. Please run the ETL.", color="warning"),
                    html.P("No data."),
                    html.P("No data.")
                )
                
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            items = [SmartNewsItem(**item) for item in data]
            
            # Filter
            if category:
                items = [i for i in items if i.category.value == category]
                
            # Sort
            if sort_by == "date":
                items.sort(key=lambda x: x.published_at, reverse=True)
            else: # trend
                items.sort(key=lambda x: x.trend_score, reverse=True)
            
            # Render Main Feed
            feed_cards = []
            for item in items[:20]: # Limit to 20
                
                # Badges
                badges = [
                    dbc.Badge(getattr(item.category, 'value', str(item.category)), color="primary", className="me-2"),
                    dbc.Badge(f"Trend: {int(item.trend_score * 100)}%", color="info" if item.trend_score > 0.7 else "secondary", className="me-2")
                ]
                
                # Key Points
                key_points_html = []
                if item.key_points:
                    key_points_html = [html.Ul([html.Li(kp) for kp in item.key_points], className="small text-muted mt-2")]
                
                feed_cards.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(badges, className="mb-2"),
                            html.H5(item.title, className="card-title"),
                            html.P(item.summary, className="card-text"),
                            *key_points_html,
                            html.Div([
                                html.Small(item.source, className="text-muted me-3"),
                                html.Small(item.published_at.strftime("%Y-%m-%d"), className="text-muted"),
                                html.A("Read Full Article", href=item.url, target="_blank", className="btn btn-sm btn-outline-primary float-end")
                            ], className="mt-3")
                        ])
                    ], className="mb-3")
                )
                
            if not feed_cards:
                feed_cards = html.P("No news found.", className="text-muted")
                
            # Render Trends (Top 5 by score)
            top_trends = sorted(items, key=lambda x: x.trend_score, reverse=True)[:5]
            trend_list = []
            for item in top_trends:
                trend_list.append(
                    html.Div([
                        html.Strong(item.title, className="d-block"),
                        dbc.Progress(value=item.trend_score * 100, color="info", className="mb-2", style={"height": "5px"}),
                        html.Small(f"Score: {int(item.trend_score * 100)}", className="text-muted"),
                        html.Hr(className="my-2")
                    ])
                )
            if not trend_list:
                trend_list = html.P("No trends detected.", className="text-muted")
                
            # Render Expert Commentary
            expert_items = [i for i in items if i.expert_commentary][:5]
            expert_cards = []
            for item in expert_items:
                comment = item.expert_commentary
                expert_cards.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.H6(f"On: {item.title}", className="card-subtitle mb-2 text-muted"),
                            html.P(f"\"{comment.content}\"", className="fst-italic small"),
                            html.Div([
                                html.Small(f"— {comment.author}", className="fw-bold"),
                                dbc.Badge(comment.sentiment, color="success" if comment.sentiment == "Positive" else "warning", className="ms-2")
                            ])
                        ])
                    ], className="mb-2 bg-light")
                )
            if not expert_cards:
                expert_cards = html.P("No expert commentary available.", className="text-muted")
                
            return feed_cards, trend_list, expert_cards
            
        except Exception as e:
            logger.error(f"Error updating developer news content: {e}")
            return dbc.Alert(f"Error: {e}", color="danger"), html.P("Error"), html.P("Error")
