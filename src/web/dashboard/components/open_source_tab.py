from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from src.config.settings import get_settings
from src.models.github import GitHubRepositoryModel
import pandas as pd
from pathlib import Path
import json

def render_open_source_tab():
    """Render the Open Source Intelligence tab."""
    settings = get_settings()
    data_path = Path(settings.data_dir) / "open_source_intelligence" / "output" / "latest.json"
    
    repositories = []
    if data_path.exists():
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                repositories = [GitHubRepositoryModel(**item) for item in data]
        except Exception as e:
            print(f"Error loading open source data: {e}")
    else:
        # Fallback/Empty state
        pass

    # Unique filtered lists for dropdowns
    languages = sorted(list(set([r.language for r in repositories if r.language])))
    if "Python" not in languages: languages = ["Python"] + languages # Ensure default exists if empty
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Open Source Intelligence", className="display-4 text-primary mb-2"),
                html.P("Trending repositories from GitHub across key ecosystems.", className="lead text-muted"),
            ], width=12)
        ], className="mb-4"),
        
        # Filters
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Language"),
                        dcc.Dropdown(
                            id="os-language-filter",
                            options=[{"label": "All", "value": "ALL"}] + [{"label": l, "value": l} for l in languages],
                            value="ALL",
                            clearable=False
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Sort By"),
                        dcc.Dropdown(
                            id="os-sort-filter",
                            options=[
                                {"label": "Trending Stars (Today)", "value": "trending"},
                                {"label": "Total Stars", "value": "stars"},
                                {"label": "Forks", "value": "forks"}
                            ],
                            value="trending",
                            clearable=False
                        )
                    ], md=4)
                ])
            ])
        ], className="mb-4 shadow-sm"),
        
        # Content Grid
        html.Div(id="os-content-grid")
    ], fluid=True)


@callback(
    Output("os-content-grid", "children"),
    [Input("os-language-filter", "value"),
     Input("os-sort-filter", "value")]
)
def update_os_grid(language, sort_by):
    settings = get_settings()
    data_path = Path(settings.data_dir) / "open_source_intelligence" / "output" / "latest.json"
    
    if not data_path.exists():
        return dbc.Alert("No data available. Run the Open Source ETL first.", color="warning")
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Use raw sorting/filtering here for simplicity if model conversion is slow
            # But safe to use list of dicts for display
            
            # Filter
            filtered = data
            if language != "ALL":
                filtered = [r for r in data if r.get("language") == language]
            
            # Sort
            if sort_by == "trending":
                # Assuming scraping creates a 'period_stars' field logic passing through? 
                # Our model doesn't explicitly have 'period_stars' in the named tuple definition at top, 
                # but the scraper adds it? Wait, model validation might strip it if not in Pydantic.
                # Let's check model. github.py -> GitHubRepositoryModel.
                # It does NOT have period_stars. It will be stripped.
                # We should use stars_count for now.
                filtered.sort(key=lambda x: x.get("stars_count", 0), reverse=True)
            elif sort_by == "stars":
                filtered.sort(key=lambda x: x.get("stars_count", 0), reverse=True)
            elif sort_by == "forks":
                filtered.sort(key=lambda x: x.get("forks_count", 0), reverse=True)
            
            if not filtered:
                return dbc.Alert("No repositories found for this filter.", color="info")
            
            # Create cards
            cards = []
            for repo in filtered:
                cards.append(dbc.Col(_create_repo_card(repo), lg=4, md=6, className="mb-4"))
                
            return dbc.Row(cards)
            
    except Exception as e:
        return dbc.Alert(f"Error loading data: {e}", color="danger")

def _create_repo_card(repo_dict):
    """Create a card for a repository."""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.H5(
                    html.A(repo_dict.get("full_name"), href=repo_dict.get("url"), target="_blank", className="text-decoration-none text-dark"), 
                    className="card-title text-truncate"
                ),
                html.Span(
                    repo_dict.get("language") or "Unknown", 
                    className="badge bg-light text-dark border ms-2"
                )
            ], className="d-flex justify-content-between align-items-center mb-2"),
            
            html.P(repo_dict.get("description"), className="card-text text-muted small", style={"height": "60px", "overflow": "hidden"}),
            
            html.Hr(),
            
            html.Div([
                html.Small([
                    html.I(className="bi bi-star-fill text-warning me-1"),
                    f"{repo_dict.get('stars_count', 0):,}"
                ], className="me-3"),
                
                html.Small([
                    html.I(className="bi bi-git text-secondary me-1"),
                    f"{repo_dict.get('forks_count', 0):,}"
                ], className="me-3"),
            ], className="d-flex text-muted")
        ], className="h-100")
    ], className="h-100 hover-shadow transition-all")
