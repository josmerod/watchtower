"""Technology Radar Tab — cloud, GenAI, AI, and self-hosting trends.

Aggregates technology news from multiple sources to track the latest trends
and updates across cloud computing, generative AI, artificial intelligence,
and self-hosted applications/tools. Consolidates sources that were previously
scattered across the News tab (Google AI Blog, KDNuggets, Cloud Updates) plus
new dedicated sources (selfh.st for self-hosting).
"""

import json
import logging
import os
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from src.utils.file_system import get_project_root
from src.web.dashboard.search_utils import create_search_input

logger = logging.getLogger(__name__)

# Source definitions: key -> (label, data file path relative to data/, icon)
RADAR_SOURCES: list[dict[str, str]] = [
    {"key": "google_ai", "label": "🧠 Google AI Blog", "file": "news/google_ai_blog_latest.json", "category": "AI"},
    {"key": "kdnuggets", "label": "📊 KDNuggets", "file": "kdnuggets/kdnuggets.json", "category": "Data Science"},
    {"key": "cloud_updates", "label": "☁️ Cloud Updates", "file": "cloud_updates/cloud_updates_latest.json", "category": "Cloud"},
    {"key": "selfhosted", "label": "🏠 Self-Hosted", "file": "selfhosted/selfhosted_latest.json", "category": "Self-Hosting"},
]

MAX_ITEMS_PER_SOURCE = 25


def _load_source_data(file_rel: str) -> list[dict[str, Any]]:
    """Load articles from a data file relative to the project data dir."""
    data_path = os.path.join(get_project_root(), "data", file_rel)
    if not os.path.exists(data_path):
        return []
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _build_article_card(article: dict[str, Any]) -> dbc.Card:
    """Build a card for a single article."""
    title = article.get("title", "Untitled")
    link = article.get("link", article.get("url", "#"))
    summary = article.get("summary", article.get("description", ""))
    published = article.get("published", article.get("fetched_at", ""))
    if summary:
        summary = summary[:200] + "…" if len(summary) > 200 else summary
    return dbc.Card(
        dbc.CardBody(
            [
                html.H6(
                    html.A(title, href=link, target="_blank", className="text-decoration-none"),
                    className="mb-1",
                ),
                html.Small(published[:10] if published else "", className="text-muted") if published else None,
                html.P(summary, className="small text-muted mt-1 mb-0") if summary else None,
            ]
        ),
        className="mb-2 shadow-sm",
    )


def _render_source_section(source: dict[str, str]) -> list:
    """Render one source's articles as a column of cards."""
    articles = _load_source_data(source["file"])[:MAX_ITEMS_PER_SOURCE]
    if not articles:
        return [
            html.H6(source["label"], className="mb-2"),
            dbc.Alert(f"No data yet. Run the ETL for {source['label'].split(' ', 1)[-1]}.", color="light", className="small"),
        ]
    return [
        html.H6(source["label"], className="mb-2"),
        html.Small(f"{len(articles)} articles", className="text-muted mb-2 d-block"),
        *[_build_article_card(a) for a in articles],
    ]


def render_tech_radar_tab() -> html.Div:
    """Render the Technology Radar tab with source columns."""
    search = create_search_input("tech-radar-search", placeholder="Search tech radar…")

    # Build a responsive grid of source sections
    source_cols = []
    for source in RADAR_SOURCES:
        source_cols.append(dbc.Col(_render_source_section(source), width=12, lg=6, xl=3, className="mb-3"))

    return html.Div(
        [
            html.Div(
                [
                    html.H3(
                        [html.I(className="fas fa-satellite-dish me-2 text-primary"), "Technology Radar"],
                        className="mb-1",
                    ),
                    html.P(
                        "Latest trends and updates across Cloud, Generative AI, Artificial Intelligence, and Self-Hosting.",
                        className="text-muted mb-3",
                        style={"fontSize": "0.9rem"},
                    ),
                ]
            ),
            search,
            dbc.Row(source_cols, className="mt-2"),
        ]
    )


def register_tech_radar_callbacks(app):
    """Register callbacks for the Technology Radar tab."""
    # Static tab — data loaded at render time. No dynamic callbacks needed.
    pass
