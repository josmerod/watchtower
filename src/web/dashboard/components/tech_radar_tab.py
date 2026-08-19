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
import re
from typing import Any

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from src.utils.file_system import get_project_root
from src.web.dashboard.search_utils import create_search_input, filter_content

logger = logging.getLogger(__name__)

# Source definitions: key -> (label, data file path relative to data/, icon)
RADAR_SOURCES: list[dict[str, str]] = [
    {"key": "google_ai", "label": "🧠 Google AI Blog", "file": "news/google_ai_blog_latest.json", "category": "AI"},
    {"key": "verge_ai", "label": "⚡ The Verge AI", "file": "news/verge_ai_latest.json", "category": "AI"},
    {"key": "kdnuggets", "label": "📊 KDNuggets", "file": "kdnuggets/kdnuggets.json", "category": "Data Science"},
    {"key": "cloud_updates", "label": "☁️ Cloud Updates", "file": "cloud_updates/cloud_updates_latest.json", "category": "Cloud"},
    {"key": "selfhosted", "label": "🏠 Self-Hosted", "file": "selfhosted/selfhosted_latest.json", "category": "Self-Hosting"},
    {"key": "infoq", "label": "🏗️ InfoQ", "file": "infoq/infoq_news.json", "category": "Engineering"},
    {"key": "thenewstack", "label": "🧱 The New Stack", "file": "thenewstack/thenewstack_news.json", "category": "Cloud-Native"},
    {"key": "changelog", "label": "🔄 Changelog", "file": "changelog/changelog_news.json", "category": "Open Source"},
]

MAX_ITEMS_PER_SOURCE = 25

# Fields checked (with nested metadata fallback) when searching/filtering.
_SEARCHABLE_FIELDS = ["title", "summary", "description"]


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


def _normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested metadata so heterogeneous ETL outputs render uniformly.

    The KDNuggets ETL nests summary/tags inside ``metadata`` and uses
    ``published_at`` instead of ``published``; other ETLs use top-level keys.
    """
    if not isinstance(article, dict):
        return {}
    metadata = article.get("metadata") or {}
    if not article.get("summary"):
        article["summary"] = metadata.get("summary", "") or metadata.get("description", "")
    if not article.get("description"):
        article["description"] = article.get("summary", "")
    if not article.get("published"):
        article["published"] = article.get("published_at", "") or article.get("fetched_at", "")
    if not article.get("link"):
        article["link"] = article.get("url", "")
    return article


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


def _render_source_section(source: dict[str, str], search_term: str | None = None) -> list:
    """Render one source's articles as a column of cards, optionally filtered."""
    articles = [_normalize_article(a) for a in _load_source_data(source["file"])]
    if not articles:
        return [
            html.H6(source["label"], className="mb-2"),
            dbc.Alert(f"No data yet. Run the ETL for {source['label'].split(' ', 1)[-1]}.", color="light", className="small"),
        ]
    if search_term:
        articles = filter_content(search_term, articles, _SEARCHABLE_FIELDS)
        if not articles:
            return [
                html.H6(source["label"], className="mb-2"),
                dbc.Alert(f"No articles matching '{search_term}'.", color="light", className="small"),
            ]
    articles = articles[:MAX_ITEMS_PER_SOURCE]
    return [
        html.H6(source["label"], className="mb-2"),
        html.Small(f"{len(articles)} articles", className="text-muted mb-2 d-block"),
        *[_build_article_card(a) for a in articles],
    ]


# Curated technology dictionary (spec 13 TR-F1 v1): canonical name -> quadrant.
# Quadrants follow the ThoughtWorks vocabulary: Techniques / Tools / Platforms / Languages & Frameworks.
TECH_DICTIONARY: dict[str, str] = {
    # Languages & frameworks
    "python": "Languages & Frameworks",
    "rust": "Languages & Frameworks",
    "golang": "Languages & Frameworks",
    "typescript": "Languages & Frameworks",
    "javascript": "Languages & Frameworks",
    "java": "Languages & Frameworks",
    "react": "Languages & Frameworks",
    "vue": "Languages & Frameworks",
    "svelte": "Languages & Frameworks",
    "next.js": "Languages & Frameworks",
    "django": "Languages & Frameworks",
    "flask": "Languages & Frameworks",
    "fastapi": "Languages & Frameworks",
    "spring": "Languages & Frameworks",
    "tailwind": "Languages & Frameworks",
    "flutter": "Languages & Frameworks",
    "swift": "Languages & Frameworks",
    "kotlin": "Languages & Frameworks",
    # Platforms
    "kubernetes": "Platforms",
    "k8s": "Platforms",
    "docker": "Platforms",
    "aws": "Platforms",
    "gcp": "Platforms",
    "azure": "Platforms",
    "cloudflare": "Platforms",
    "vercel": "Platforms",
    "github": "Platforms",
    "gitlab": "Platforms",
    "linux": "Platforms",
    "nginx": "Platforms",
    "home assistant": "Platforms",
    "raspberry pi": "Platforms",
    "unraid": "Platforms",
    "proxmox": "Platforms",
    "steam": "Platforms",
    # Tools
    "terraform": "Tools",
    "ansible": "Tools",
    "postgres": "Tools",
    "postgresql": "Tools",
    "mysql": "Tools",
    "redis": "Tools",
    "sqlite": "Tools",
    "mongodb": "Tools",
    "grafana": "Tools",
    "prometheus": "Tools",
    "n8n": "Tools",
    "hugging face": "Tools",
    "ollama": "Tools",
    "vscode": "Tools",
    "neovim": "Tools",
    "obsidian": "Tools",
    "docker compose": "Tools",
    "traefik": "Tools",
    # Techniques
    "rag": "Techniques",
    "fine-tuning": "Techniques",
    "rlhf": "Techniques",
    "distillation": "Techniques",
    "quantization": "Techniques",
    "mlops": "Techniques",
    "ci/cd": "Techniques",
    "tdd": "Techniques",
    "microservices": "Techniques",
    "serverless": "Techniques",
    "edge computing": "Techniques",
    "vector database": "Techniques",
    "agent": "Techniques",
    "agents": "Techniques",
    # AI models treated as Tools (bubbles sized by mentions)
    "llama": "Tools",
    "gpt": "Tools",
    "claude": "Tools",
    "gemini": "Tools",
    "mistral": "Tools",
    "deepseek": "Tools",
    "qwen": "Tools",
}

_QUADRANT_ORDER = ["Techniques", "Tools", "Platforms", "Languages & Frameworks"]
_RING_ORDER = ["Adopt", "Trial", "Assess", "Hold"]


def _extract_tech_mentions() -> list[dict[str, Any]]:
    """Scan every radar source for dictionary-tech mentions.

    Returns one record per detected technology with mention counts, the
    sources that mentioned it and example articles for the hover.
    """
    combined: dict[str, dict[str, Any]] = {}
    for source in RADAR_SOURCES:
        for raw in _load_source_data(source["file"]):
            article = _normalize_article(raw)
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            for tech, quadrant in TECH_DICTIONARY.items():
                if re.search(rf"\b{re.escape(tech)}\b", text):
                    entry = combined.setdefault(
                        tech,
                        {"tech": tech, "quadrant": quadrant, "mentions": 0, "sources": set(), "examples": []},
                    )
                    entry["mentions"] += 1
                    entry["sources"].add(source["label"])
                    if len(entry["examples"]) < 3:
                        entry["examples"].append(article.get("title", "")[:80])

    records = []
    for entry in combined.values():
        if entry["mentions"] >= 2:  # noise floor: single mentions skipped
            ring = _RING_ORDER[min(3, entry["mentions"] // 3)]  # 2-2 Assess, 3-5 Trial, 6-8 Adopt, 9+ Hold cap
            if entry["mentions"] >= 6:
                ring = "Adopt"
            elif entry["mentions"] >= 3:
                ring = "Trial"
            else:
                ring = "Assess"
            records.append({**entry, "sources": sorted(entry["sources"]), "ring": ring})
    records.sort(key=lambda r: r["mentions"], reverse=True)
    return records[:40]


def _build_radar_figure(records: list[dict[str, Any]]) -> go.Figure:
    """Plotly scatter: quadrant columns x ring rows, bubble size by mentions."""
    if not records:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="No tech mentions detected yet — run the radar ETLs", showarrow=False)
        return fig

    fig = go.Figure()
    for quadrant in _QUADRANT_ORDER:
        subset = [r for r in records if r["quadrant"] == quadrant]
        if not subset:
            continue
        fig.add_trace(
            go.Scatter(
                x=[quadrant] * len(subset),
                y=[r["ring"] for r in subset],
                text=[r["tech"] for r in subset],
                customdata=list(subset),
                mode="markers+text",
                textposition="bottom center",
                marker={
                    "size": [min(60, 10 + r["mentions"] * 4) for r in subset],
                    "sizemode": "diameter",
                    "opacity": 0.75,
                    "color": [len(r["sources"]) for r in subset],
                    "colorscale": "Viridis",
                    "showscale": quadrant == _QUADRANT_ORDER[-1],
                    "colorbar": {"title": "Fuentes"} if quadrant == _QUADRANT_ORDER[-1] else None,
                },
                name=quadrant,
                hovertemplate="<b>%{text}</b><br>Ring: %{y}<br>Quadrant: %{x}<br>Menciones: %{customdata[2]}<br>Fuentes: %{customdata[4]}<extra></extra>",
            )
        )

    fig.update_layout(
        title="📡 Radar tecnológico — menciones cruzadas por cuadrante y madurez",
        xaxis_title="Cuadrante",
        yaxis_title="Anillo (madurez estimada por menciones)",
        xaxis={"categoryorder": "array", "categoryarray": _QUADRANT_ORDER},
        yaxis={"categoryorder": "array", "categoryarray": list(reversed(_RING_ORDER))},
        height=560,
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom"},
        margin={"l": 60, "r": 30, "t": 60, "b": 40},
    )
    return fig


def _render_radar_plot() -> dbc.Card:
    """Radar visualization card (spec 13 TR-F1)."""
    records = _extract_tech_mentions()
    return dbc.Card(
        [
            dbc.CardHeader(html.H6("📡 Radar — Tecnologías detectadas en las últimas publicaciones", className="mb-0")),
            dbc.CardBody(dcc.Graph(id="tech-radar-plot", figure=_build_radar_figure(records), style={"height": "560px"})),
            dbc.CardFooter(
                html.Small(
                    f"{len(records)} tecnologías detectadas (diccionario curado v1, ≥2 menciones). Tamaño = menciones; color = numero de fuentes.",
                    className="text-muted",
                )
            ),
        ],
        className="mb-3",
    )


def render_tech_radar_tab() -> html.Div:
    """Render the Technology Radar tab with source columns."""
    search = create_search_input("tech-radar-search", placeholder="Search tech radar…", clear_button=True)

    # Build a responsive grid of source sections
    source_cols = [dbc.Col(_render_source_section(source), id=f"tech-radar-col-{source['key']}", width=12, lg=6, xl=3, className="mb-3") for source in RADAR_SOURCES]

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
            _render_radar_plot(),
            dbc.Row(source_cols, className="mt-2"),
        ]
    )


def register_tech_radar_callbacks(app):
    """Register callbacks for the Technology Radar tab."""

    @app.callback(
        [Output(f"tech-radar-col-{source['key']}", "children") for source in RADAR_SOURCES],
        Input("tech-radar-search", "value"),
        prevent_initial_call=True,
    )
    def update_radar_search(search_term):
        """Filter every source column by the search term."""
        try:
            term = (search_term or "").strip() or None
            return [_render_source_section(source, search_term=term) for source in RADAR_SOURCES]
        except Exception as e:
            logger.error(f"Error in tech radar search: {e}")
            return [[dbc.Alert(f"Error searching: {e}", color="danger")] for _ in RADAR_SOURCES]

    @app.callback(
        Output("tech-radar-search", "value", allow_duplicate=True),
        Input("tech-radar-search-clear", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_radar_search(n_clicks):
        """Clear the search input."""
        if n_clicks:
            return ""
        return dash.no_update
