"""AI Research Intelligence Dashboard Tab."""

from __future__ import annotations

import logging
from typing import Any
from pathlib import Path

import dash_bootstrap_components as dbc
import plotly.express as px
from dash import dash_table, dcc, html

from src.models.ai_research_model import ImplementationComplexity
from src.web.dashboard.utils import get_data_path

# Import repository pattern (NEW)
from src.repositories import BaseRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AI_RESEARCH_DATA_PATH = get_data_path("ai_research", "ai_research_latest.json")
HUGGINGFACE_DATA_PATH = get_data_path("huggingface_platform", "output", "huggingface_latest.json")


# OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
# def load_ai_research_data() -> list[dict[str, Any]]:
#     """Load AI research data from JSON."""
#     try:
#         if not file_exists(AI_RESEARCH_DATA_PATH):
#             logger.info(f"AI Research data file not found: {AI_RESEARCH_DATA_PATH}")
#             return []
#         with open(AI_RESEARCH_DATA_PATH, encoding="utf-8") as f:
#             data = json.load(f)
#         return data
#     except Exception as e:
#         logger.error(f"Error loading AI research data: {e}")
#         return []


# NEW: Repository-based loading (SOLID Pattern)
class AIResearchRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for AI research data."""

    def __init__(self):
        """Initialize AI research repository."""
        super().__init__(
            data_path=Path(AI_RESEARCH_DATA_PATH),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of research papers.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of research paper dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

# Create singleton instance
ai_research_repo = AIResearchRepository()

class HuggingFaceRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for HuggingFace data."""

    def __init__(self):
        super().__init__(
            data_path=Path(HUGGINGFACE_DATA_PATH),
            cache_ttl_seconds=3600,
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        return []

huggingface_repo = HuggingFaceRepository()

def load_ai_research_data() -> list[dict[str, Any]]:
    """Load AI research data using repository pattern (NEW).

    Returns:
        List of AI research papers

    This function now uses the repository pattern with built-in caching.
    """
    try:
        # Repository handles file loading and caching
        data = ai_research_repo.get()
        return data
    except Exception as e:
        logger.error(f"Error loading AI research data: {e}")
        return []


def create_summary_cards(data: list[dict[str, Any]]) -> dbc.Row:
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
                    dbc.CardBody(
                        [
                            html.H4(
                                [html.Span(icon, className="me-2"), value],
                                className=f"text-{color} mb-0",
                            ),
                            html.P(title, className="text-muted small mb-0"),
                        ]
                    ),
                    className="h-100 shadow-sm",
                ),
                md=4,
            )
        )
    return dbc.Row(cols, className="mb-4")


def create_papers_table(data: list[dict[str, Any]]) -> html.Div:
    """Create a table of AI research papers."""
    if not data:
        return dbc.Alert("No AI research papers found.", color="info")

    # Sort by trend score descending
    sorted_data = sorted(data, key=lambda x: x.get("trend_score", 0), reverse=True)

    table_data = []
    for p in sorted_data:
        table_data.append(
            {
                "Title": p.get("title"),
                "Domain": p.get("primary_domain"),
                "Trend": f"{p.get('trend_score', 0):.1f}",
                "Complexity": p.get("complexity"),
                "Link": f"[Open]({p.get('url')})" if p.get("url") else "N/A",
            }
        )

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
            "border": "1px solid #313244",
        },
        style_header={
            "backgroundColor": "#181825",
            "fontWeight": "bold",
            "color": "#cdd6f4",
            "border": "1px solid #313244",
        },
        style_data_conditional=[
            {"if": {"filter_query": '{Complexity} = "Low"'}, "color": "#a6e3a1"},
            {"if": {"filter_query": '{Complexity} = "High"'}, "color": "#f38ba8"},
        ],
    )

def create_huggingface_table(data: list[dict[str, Any]]) -> html.Div:
    """Create a table of HuggingFace models and datasets."""
    if not data:
        return dbc.Alert("No HuggingFace ecosystem data found.", color="info")

    table_data = []
    for d in data:
        name = d.get("model_name") or d.get("dataset_name", "Unknown")
        item_type = d.get("data_type", "unknown").replace("_release", "").title()
        item_id = d.get("model_id") or d.get("dataset_id")
        
        table_data.append(
            {
                "Name": name,
                "Type": item_type,
                "Downloads": d.get("downloads", 0),
                "Likes": d.get("likes", 0),
                "Link": f"[Open](https://huggingface.co/{item_id})" if item_id else "N/A",
            }
        )

    columns = [
        {"name": "Name", "id": "Name", "type": "text"},
        {"name": "Type", "id": "Type", "type": "text"},
        {"name": "Downloads", "id": "Downloads", "type": "numeric"},
        {"name": "Likes", "id": "Likes", "type": "numeric"},
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
            "border": "1px solid #313244",
        },
        style_header={
            "backgroundColor": "#181825",
            "fontWeight": "bold",
            "color": "#cdd6f4",
            "border": "1px solid #313244",
        },
    )


def create_charts(data: list[dict[str, Any]]) -> dbc.Row:
    """Create visualization charts."""
    if not data:
        return html.Div()

    # Domain Distribution
    domains = [p.get("primary_domain", "Other") for p in data]
    fig_domain = px.pie(names=domains, title="Research Domains")
    fig_domain.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#cdd6f4",
    )

    # Trend vs Complexity
    fig_scatter = px.scatter(
        data,
        x="complexity_score",
        y="trend_score",
        color="primary_domain",
        hover_data=["title"],
        title="Trend vs. Complexity",
        labels={"complexity_score": "Complexity", "trend_score": "Trend Momentum"},
    )
    fig_scatter.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#cdd6f4",
    )

    return dbc.Row(
        [
            dbc.Col(dcc.Graph(figure=fig_domain), md=6),
            dbc.Col(dcc.Graph(figure=fig_scatter), md=6),
        ],
        className="mb-4",
    )


def render_ai_research_tab() -> html.Div:
    """Render the AI Research Intelligence tab."""
    data = load_ai_research_data()
    hf_data = []
    try:
        hf_data = huggingface_repo.get()
    except Exception as e:
        logger.error(f"Error loading HuggingFace data: {e}")

    return html.Div(
        [
            html.H2("AI Research Intelligence", className="mb-4 text-primary"),
            html.P(
                "Monitoring latest AI research papers, trends, and implementation opportunities.",
                className="text-muted mb-4",
            ),
            create_summary_cards(data),
            create_charts(data),
            html.H4("Latest Papers", className="mb-3"),
            create_papers_table(data),
            html.Hr(className="my-5"),
            html.H4("Trending Models & Datasets (HuggingFace)", className="mb-3 text-success"),
            create_huggingface_table(hf_data),
        ]
    )
