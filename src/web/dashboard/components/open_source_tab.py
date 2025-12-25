from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from src.config.settings import get_settings
from src.models.opensource_model import OpenSourceProjectItem
from datetime import datetime
from pathlib import Path
import json

def render_open_source_tab():
    """Render the Open Source Intelligence tab."""
    settings = get_settings()
    data_path = Path(settings.data_dir) / "open_source_intelligence" / "output" / "latest.json"
    
    projects = []
    if data_path.exists():
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                projects = [OpenSourceProjectItem(**item) for item in data]
        except Exception as e:
            print(f"Error loading open source data: {e}")
    
    # Collect all unique tags for filtering
    all_tags = set()
    for p in projects:
        for tag in p.tags:
            all_tags.add(tag)
    
    sorted_tags = sorted(list(all_tags))
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Open Source Intelligence", className="display-4 text-primary mb-2"),
                html.P("Latest open source projects from opensourceprojects.dev.", className="lead text-muted"),
            ], width=12)
        ], className="mb-4"),
        
        # Filters
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Filter by Tag"),
                        dcc.Dropdown(
                            id="os-tag-filter",
                            options=[{"label": "All Tags", "value": "ALL"}] + [{"label": t, "value": t} for t in sorted_tags],
                            value="ALL",
                            clearable=False
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("Sort By"),
                        dcc.Dropdown(
                            id="os-sort-filter",
                            options=[
                                {"label": "Newest First", "value": "newest"},
                                {"label": "Oldest First", "value": "oldest"}
                            ],
                            value="newest",
                            clearable=False
                        )
                    ], md=6)
                ])
            ])
        ], className="mb-4 shadow-sm"),
        
        # Content Grid
        html.Div(id="os-content-grid")
    ], fluid=True)


@callback(
    Output("os-content-grid", "children"),
    [Input("os-tag-filter", "value"),
     Input("os-sort-filter", "value")]
)
def update_os_grid(tag_filter, sort_by):
    settings = get_settings()
    data_path = Path(settings.data_dir) / "open_source_intelligence" / "output" / "latest.json"
    
    if not data_path.exists():
        return dbc.Alert("No data available. Run the Open Source ETL first.", color="warning")
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Validation optional to speed up, but good for consistency
            projects = [OpenSourceProjectItem(**item) for item in data]
            
            # Filter
            if tag_filter != "ALL":
                projects = [p for p in projects if tag_filter in p.tags]
            
            # Sort
            if sort_by == "newest":
                projects.sort(key=lambda x: x.published_at or x.created_at, reverse=True)
            elif sort_by == "oldest":
                projects.sort(key=lambda x: x.published_at or x.created_at, reverse=False)
            
            if not projects:
                return dbc.Alert("No projects found for this filter.", color="info")
            
            # Create cards
            cards = []
            for project in projects:
                cards.append(dbc.Col(_create_project_card(project), lg=4, md=6, className="mb-4"))
                
            return dbc.Row(cards)
            
    except Exception as e:
        return dbc.Alert(f"Error loading data: {e}", color="danger")

def _create_project_card(item: OpenSourceProjectItem):
    """Create a card for a project."""
    
    tags_badges = [
        html.Span(tag, className="badge bg-light text-dark border me-1 mb-1") 
        for tag in item.tags[:5] # Limit tags
    ]
    
    date_str = item.published_at.strftime("%Y-%m-%d") if item.published_at else "Unknown Date"
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.H5(
                    html.A(item.title, href=item.url, target="_blank", className="text-decoration-none text-dark"), 
                    className="card-title text-truncate"
                ),
            ], className="mb-2"),
            
            html.Div(tags_badges, className="mb-2"),
            
            html.P(item.description, className="card-text text-muted small", style={"height": "60px", "overflow": "hidden"}),
            
            html.Hr(),
            
            html.Div([
                html.Small([
                    html.I(className="bi bi-calendar-event text-secondary me-1"),
                    date_str
                ], className="me-3"),
                
                # Check for AI summary if available (using AIEnhancedModel fields)
                # item.ai_summary...
            ], className="d-flex text-muted justify-content-between align-items-center"),
            
            html.Div([
                 html.A("View Project", href=item.url, target="_blank", className="btn btn-sm btn-outline-primary mt-2 w-100")
            ])
            
        ], className="h-100 d-flex flex-column")
    ], className="h-100 hover-shadow transition-all")
