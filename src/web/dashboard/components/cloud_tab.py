"""Cloud Intelligence Dashboard Tab."""

from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import json
from pathlib import Path
from datetime import datetime
from typing import Any

from src.models.cloud import CloudUpdate, CloudProvider, UpdateCategory
from src.utils.file_system import get_project_root
from src.utils.logging import get_logger

# Import repository pattern (NEW)
from src.repositories import BaseRepository

logger = get_logger("CloudTab")

# NEW: Repository-based loading (SOLID Pattern)
class CloudUpdateRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for cloud update data."""

    def __init__(self):
        """Initialize cloud update repository."""
        project_root = Path(get_project_root())
        data_file = project_root / "data" / "cloud" / "output" / "cloud_updates.json"

        super().__init__(
            data_path=data_file,
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of cloud updates.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of cloud update dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

# Create singleton instance
cloud_update_repo = CloudUpdateRepository()

def render_cloud_tab() -> html.Div:
    """Render the Cloud Intelligence tab.
    
    Returns:
        Dash HTML component
    """
    return html.Div([
        dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("☁️ Cloud Intelligence Hub", className="mb-3"),
                    html.P(
                        "Stay updated with the latest cloud features, security alerts, and cost optimization tips.",
                        className="text-muted"
                    )
                ])
            ], className="mb-4"),
            
            # Filters
            dbc.Row([
                dbc.Col([
                    dbc.Label("Provider:"),
                    dcc.Dropdown(
                        id="cloud-provider-filter",
                        options=[
                            {"label": p.value, "value": p.value}
                            for p in CloudProvider
                        ],
                        placeholder="All Providers",
                        className="mb-3"
                    )
                ], width=4),
                dbc.Col([
                    dbc.Label("Category:"),
                    dcc.Dropdown(
                        id="cloud-category-filter",
                        options=[
                            {"label": c.value, "value": c.value}
                            for c in UpdateCategory
                        ],
                        placeholder="All Categories",
                        className="mb-3"
                    )
                ], width=4),
            ]),
            
            # Content Area
            dbc.Row([
                # Main Feed
                dbc.Col([
                    html.H4("Latest Updates", className="mb-3"),
                    html.Div(id="cloud-updates-container")
                ], width=8),
                
                # Sidebar: Security & Cost
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🛡️ Security Alerts"),
                        dbc.CardBody(id="cloud-security-container")
                    ], className="mb-4 border-danger"),
                    
                    dbc.Card([
                        dbc.CardHeader("💰 Cost Optimization"),
                        dbc.CardBody(id="cloud-cost-container")
                    ], className="mb-4 border-success")
                ], width=4)
            ])
        ], fluid=True)
    ])

def register_cloud_callbacks(app):
    """Register callbacks for the Cloud tab."""
    
    @app.callback(
        [Output("cloud-updates-container", "children"),
         Output("cloud-security-container", "children"),
         Output("cloud-cost-container", "children")],
        [Input("cloud-provider-filter", "value"),
         Input("cloud-category-filter", "value")]
    )
    def update_cloud_content(provider, category):
        """Update cloud content based on filters (NEW - uses repository)."""
        try:
            # OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
            # project_root = Path(get_project_root())
            # data_file = project_root / "data" / "cloud" / "output" / "cloud_updates.json"
            #
            # if not data_file.exists():
            #     return (
            #         dbc.Alert("No cloud data found. Please run the ETL.", color="warning"),
            #         html.P("No data."),
            #         html.P("No data.")
            #     )
            #
            # with open(data_file, 'r', encoding='utf-8') as f:
            #     data = json.load(f)

            # NEW: Repository-based loading with caching
            if not cloud_update_repo.is_available():
                return (
                    dbc.Alert("No cloud data found. Please run the ETL.", color="warning"),
                    html.P("No data."),
                    html.P("No data.")
                )

            data = cloud_update_repo.get()
            updates = [CloudUpdate(**u) for u in data]

            # Filter
            if provider:
                updates = [u for u in updates if u.provider.value == provider]
            if category:
                updates = [u for u in updates if u.category.value == category]

            # Sort by date desc
            updates.sort(key=lambda x: x.published_at, reverse=True)
            
            # Render Main Feed
            feed_cards = []
            for u in updates[:20]: # Limit to 20
                provider_val = getattr(u.provider, 'value', str(u.provider))
                category_val = getattr(u.category, 'value', str(u.category))
                
                badge_color = "primary"
                if provider_val == "AWS": badge_color = "warning"
                elif provider_val == "Azure": badge_color = "info"
                elif provider_val == "GCP": badge_color = "danger"
                
                feed_cards.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                dbc.Badge(provider_val, color=badge_color, className="me-2"),
                                dbc.Badge(category_val, color="secondary", className="me-2"),
                                html.Small(u.published_at.strftime("%Y-%m-%d"), className="text-muted")
                            ], className="mb-2"),
                            html.H5(u.title, className="card-title"),
                            html.P(u.description, className="card-text small"),
                            html.A("Read Announcement", href=str(u.link), target="_blank", className="btn btn-sm btn-outline-primary")
                        ])
                    ], className="mb-3")
                )
                
            if not feed_cards:
                feed_cards = html.P("No updates found.", className="text-muted")
                
            # Render Security Alerts (High priority)
            security_updates = [u for u in updates if u.security_implication][:5]
            sec_cards = []
            for u in security_updates:
                provider_val = getattr(u.provider, 'value', str(u.provider))
                sec_cards.append(
                    html.Div([
                        html.Strong(provider_val, className="text-danger"),
                        html.Span(": "),
                        html.A(u.title, href=str(u.link), target="_blank", className="text-dark"),
                        html.Hr(className="my-2")
                    ])
                )
            if not sec_cards:
                sec_cards = html.P("No immediate security alerts.", className="text-success")
                
            # Render Cost Tips
            cost_updates = [u for u in updates if u.cost_implication][:5]
            cost_cards = []
            for u in cost_updates:
                provider_val = getattr(u.provider, 'value', str(u.provider))
                cost_cards.append(
                    html.Div([
                        html.Strong(provider_val, className="text-success"),
                        html.Span(": "),
                        html.A(u.title, href=str(u.link), target="_blank", className="text-dark"),
                        html.Hr(className="my-2")
                    ])
                )
            if not cost_cards:
                cost_cards = html.P("No specific cost updates.", className="text-muted")
                
            return feed_cards, sec_cards, cost_cards
            
        except Exception as e:
            logger.error(f"Error updating cloud content: {e}")
            return dbc.Alert(f"Error: {e}", color="danger"), html.P("Error"), html.P("Error")
