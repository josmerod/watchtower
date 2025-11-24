"""AI Research Intelligence Dashboard Tab."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import dash_bootstrap_components as dbc
import plotly.express as px
from dash import Input, Output, callback, dash_table, dcc, html

from src.web.dashboard.utils import file_exists, get_data_path
from src.models.ai_research_model import AIResearchPaper, ResearchDomain, ImplementationComplexity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AI_RESEARCH_DATA_PATH = get_data_path("ai_research", "ai_research_latest.json")

def load_ai_research_data() -> List[Dict[str, Any]]:
    """Load AI research data from JSON."""
    try:
        if not file_exists(AI_RESEARCH_DATA_PATH):
            logger.info(f"AI Research data file not found: {AI_RESEARCH_DATA_PATH}")
            return []
        with open(AI_RESEARCH_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading AI research data: {e}")
        return []

def create_summary_cards(data: List[Dict[str, Any]]) -> dbc.Row:
    """Create summary cards for AI research metrics."""
    total_papers = len(data)
    high_trend = len([p for p in data if p.get("trend_score", 0) > 75])
    low_complexity = len([p for p in data if p.get("complexity") == ImplementationComplexity.LOW])
    
    cards = [
        ("Total Papers", total_papers, "primary", "📚"),
        ("High Trend", high_trend, "success", "🔥"),
        ("Easy Implementation", low_complexity, "info", "⚡"),
    ]
    
    cols = []
    for title, value, color, icon in cards:
        cols.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H4([html.Span(icon, className="me-2"), value], className=f"text-{color} mb-0"),
                        html.P(title, className="text-muted small mb-0"),
                    ]),
                    className="h-100 shadow-sm"
                ),
                md=4
            )
        )
    return dbc.Row(cols, className="mb-4")

def create_papers_table(data: List[Dict[str, Any]]) -> html.Div:
    """Create a table of AI research papers."""
    if not data:
        return dbc.Alert("No AI research papers found.", color="info")
        
    # Sort by trend score descending
    sorted_data = sorted(data, key=lambda x: x.get("trend_score", 0), reverse=True)
    
    table_data = []
    for p in sorted_data:
        table_data.append({
            "Title": p.get("title"),
            "Domain": p.get("primary_domain"),
            "Trend": f"{p.get('trend_score', 0):.1f}",
            "Complexity": p.get("complexity"),
            "Link": f"[Open]({p.get('url')})" if p.get("url") else "N/A"
        })
        
    columns = [
        {"name": "Title", "id": "Title", "type": "text"},
        {"name": "Domain", "id": "Domain", "type": "text"},
        {"name": "Trend", "id": "Trend", "type": "numeric"},
        {"name": "Complexity", "id": "Complexity", "type": "text"},
        {"name": "Link", "id": "Link", "type": "text", "presentation": "markdown"},
    ]
    
    return dash_table.DataTable(
        data=table_data,
        columns=columns,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "padding": "10px",
            "fontFamily": "Inter, sans-serif",
            "backgroundColor": "#1e1e2e",
            "color": "#cdd6f4",
            "border": "1px solid #313244"
        },
        style_header={
            "backgroundColor": "#181825",
            "fontWeight": "bold",
            "color": "#cdd6f4",
            "border": "1px solid #313244"
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{Complexity} = "Low"'},
                'color': '#a6e3a1'
            },
            {
                'if': {'filter_query': '{Complexity} = "High"'},
                'color': '#f38ba8'
            }
        ]
    )

def create_charts(data: List[Dict[str, Any]]) -> dbc.Row:
    """Create visualization charts."""
    if not data:
        return html.Div()
        
    # Domain Distribution
    domains = [p.get("primary_domain", "Other") for p in data]
    fig_domain = px.pie(names=domains, title="Research Domains")
    fig_domain.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#cdd6f4"
    )
    
    # Trend vs Complexity
    fig_scatter = px.scatter(
        data, 
        x="complexity_score", 
        y="trend_score", 
        color="primary_domain",
        hover_data=["title"],
        title="Trend vs. Complexity",
        labels={"complexity_score": "Complexity", "trend_score": "Trend Momentum"}
    )
    fig_scatter.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#cdd6f4"
    )
    
    return dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_domain), md=6),
        dbc.Col(dcc.Graph(figure=fig_scatter), md=6),
    ], className="mb-4")

def render_ai_research_tab() -> html.Div:
    """Render the AI Research Intelligence tab."""
    data = load_ai_research_data()
    
    return html.Div([
        html.H2("AI Research Intelligence", className="mb-4 text-primary"),
        html.P("Monitoring latest AI research papers, trends, and implementation opportunities.", className="text-muted mb-4"),
        
        create_summary_cards(data),
        create_charts(data),
        
        html.H4("Latest Papers", className="mb-3"),
        create_papers_table(data)
    ])
