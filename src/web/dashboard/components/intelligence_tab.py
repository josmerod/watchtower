"""Content Insights Dashboard Tab

Aggregates internal insights (recommendations, trends) and external intelligence feeds.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
import plotly.express as px
from dash import Input, Output, dash_table, dcc, html

from src.web.dashboard.components.recommendations_tab import recommendations_manager
from src.web.dashboard.trend_utils import load_latest_trends
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# Import repository pattern (NEW)
from src.repositories import BaseRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Import centralized configuration
from src.services.data_loader import INTEL_SOURCES_CONFIG

# NEW: Repository-based loading (SOLID Pattern)
class IntelligenceRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for intelligence data."""

    def __init__(self, data_path: str):
        """Initialize intelligence repository.

        Args:
            data_path: Path to intelligence data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of intelligence items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of intelligence item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

# Create singleton instances for each source
sec_edgar_repo = IntelligenceRepository(INTEL_SOURCES_CONFIG["sec_edgar"]["path"])
who_outbreaks_repo = IntelligenceRepository(INTEL_SOURCES_CONFIG["who_outbreaks"]["path"])
nvd_cve_repo = IntelligenceRepository(INTEL_SOURCES_CONFIG["nvd_cve"]["path"])


# OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
# def load_intel_data(file_path: str) -> list[dict[str, Any]]:
#     try:
#         if not file_exists(file_path):
#             logger.info(f"Intelligence data file not found: {file_path}")
#             return []
#         with open(file_path, encoding="utf-8") as f:
#             data = json.load(f)
#         if isinstance(data, list):
#             return [process_intel_item(item) for item in data if process_intel_item(item)]
#         return []
#     except Exception as e:
#         logger.error(f"Error loading intelligence data from {file_path}: {e}")
#         return []


def load_intel_data(file_path: str) -> list[dict[str, Any]]:
    """Load intelligence data using repository pattern (NEW).

    Args:
        file_path: Path to intelligence data file

    Returns:
        List of processed intelligence items
    """
    try:
        # Select appropriate repository based on file path
        if "sec_edgar" in file_path:
            data = sec_edgar_repo.get()
        elif "who_outbreaks" in file_path:
            data = who_outbreaks_repo.get()
        elif "nvd_cve" in file_path:
            data = nvd_cve_repo.get()
        else:
            logger.info(f"Unknown intelligence data source: {file_path}")
            return []

        if isinstance(data, list):
            return [process_intel_item(item) for item in data if process_intel_item(item)]
        return []
    except Exception as e:
        logger.error(f"Error loading intelligence data from {file_path}: {e}")
        return []


def process_intel_item(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        title = item.get("title", item.get("name", "Untitled"))
        url = item.get("url", item.get("link", "#"))
        published = item.get("published") or item.get("date") or item.get("created_at")
        published_dt = parse_date_universal(published, "Intelligence")
        content_type = item.get("content_type", item.get("type", "item"))
        source = item.get("source", "unknown")
        summary = item.get("summary", item.get("abstract", ""))
        region = item.get("region", "global")
        return {
            "title": title,
            "url": url,
            "published": published_dt,
            "content_type": content_type,
            "source": source,
            "summary": summary[:200] + ("..." if len(summary) > 200 else ""),
            "region": region,
        }
    except Exception as e:
        logger.error(f"Error processing intelligence item: {e}")
        return None


# Load data for all sources
INTEL_DATA: dict[str, list[dict[str, Any]]] = {}
for source_id, cfg in INTEL_SOURCES_CONFIG.items():
    data = load_intel_data(cfg["path"])
    INTEL_DATA[source_id] = data
    logger.info(f"Loaded {len(data)} items for {cfg['name']}")


def create_recommendations_section() -> html.Div:
    """Creates the Top Recommendations section."""
    try:
        recs = recommendations_manager.get_user_recommendations()
        if not recs or not recs.recommendations:
            return html.Div(
                dbc.Alert(
                    "No personalized recommendations available yet. Interact with content to generate insights!",
                    color="info",
                ),
                className="mb-4",
            )

        # Take top 3 recommendations
        top_recs = recs.recommendations[:3]

        cards = []
        for rec in top_recs:
            cards.append(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6(rec.title, className="card-title text-truncate"),
                                    html.P(
                                        rec.description,
                                        className="card-text small text-muted",
                                        style={"height": "40px", "overflow": "hidden"},
                                    ),
                                    dbc.Badge(
                                        f"{rec.score:.0%} Match",
                                        color="success" if rec.score > 0.7 else "info",
                                        className="mb-2",
                                    ),
                                    html.Div(
                                        dbc.Button(
                                            "View Content",
                                            href="#",
                                            color="primary",
                                            size="sm",
                                            className="w-100",
                                        ),  # Placeholder link
                                    ),
                                ]
                            )
                        ],
                        className="h-100 shadow-sm",
                    ),
                    md=4,
                    className="mb-3",
                )
            )

        return html.Div(
            [
                html.H4("🎯 Top Picks for You", className="text-primary mb-3"),
                dbc.Row(cards),
            ],
            className="mb-5",
        )
    except Exception as e:
        logger.error(f"Error creating recommendations section: {e}")
        return html.Div()


def create_trending_section() -> html.Div:
    """Creates the Trending Topics section."""
    try:
        trends = load_latest_trends()
        if not trends:
            return html.Div()

        # Filter for high trending score
        top_trends = sorted(trends, key=lambda x: x.get("trend_score", 0), reverse=True)[:10]

        badges = []
        for trend in top_trends:
            badges.append(
                dbc.Badge(
                    [
                        trend.get("title", "Unknown"),
                        dbc.Badge(
                            f"{trend.get('trend_score', 0):.1f}",
                            color="light",
                            text_color="dark",
                            className="ms-2",
                        ),
                    ],
                    color="danger",
                    className="me-2 mb-2 p-2",
                    pill=True,
                    href="#",  # Placeholder
                )
            )

        return html.Div(
            [
                html.H4("🔥 Trending Now", className="text-danger mb-3"),
                html.Div(badges, className="d-flex flex-wrap"),
            ],
            className="mb-5",
        )
    except Exception as e:
        logger.error(f"Error creating trending section: {e}")
        return html.Div()


def create_intel_summary_cards() -> list[html.Div]:
    cards: list[html.Div] = []
    for source_id, cfg in INTEL_SOURCES_CONFIG.items():
        data = INTEL_DATA[source_id]
        count = len(data)
        latest = max((d["published"] for d in data if d.get("published")), default=None) if data else None
        status_color = cfg["color"] if count > 0 else "secondary"
        cards.append(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            [
                                html.H6(
                                    [
                                        html.Span(cfg["icon"], className="me-2"),
                                        cfg["name"],
                                    ],
                                    className="mb-0",
                                ),
                                dbc.Badge(
                                    f"{count} items",
                                    color=status_color,
                                    className="float-end",
                                ),
                            ]
                        ),
                        dbc.CardBody(
                            [
                                html.P(
                                    cfg["description"],
                                    className="small text-muted mb-2",
                                ),
                                html.Div(
                                    [
                                        html.Strong("Category: "),
                                        dbc.Badge(
                                            cfg["category"],
                                            color="info",
                                            className="ms-1",
                                        ),
                                    ]
                                ),
                                html.Div(
                                    [
                                        html.Strong("Latest: "),
                                        html.Span(
                                            (latest.strftime("%Y-%m-%d %H:%M UTC") if latest else "N/A"),
                                            className="text-muted small",
                                        ),
                                    ],
                                    className="mt-1",
                                ),
                                dbc.Button(
                                    f"View {cfg['name']}",
                                    id=f"btn-intel-{source_id}",
                                    color="outline-primary",
                                    size="sm",
                                    className="w-100 mt-2",
                                ),
                            ]
                        ),
                    ],
                    className="mb-3 h-100",
                ),
                md=6,
            )
        )
    return cards


def create_intel_table(source_id: str, items: list[dict[str, Any]]) -> html.Div:
    if not items:
        return dbc.Alert("No intelligence items available for this source.", color="info")

    # Sort by published desc
    sorted_items = sorted(
        items,
        key=lambda x: x.get("published") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    df_rows = []
    for it in sorted_items:
        date_str = it["published"].strftime("%Y-%m-%d %H:%M") if it.get("published") else "N/A"
        df_rows.append(
            {
                "Title": it.get("title", "Untitled")[:100] + ("..." if len(it.get("title", "")) > 100 else ""),
                "Date": date_str,
                "Type": it.get("content_type", "item"),
                "Region": it.get("region", "global"),
                "URL": it.get("url", "#"),
            }
        )

    columns = [
        {"name": "Title", "id": "Title", "type": "text"},
        {"name": "Date", "id": "Date", "type": "text"},
        {"name": "Type", "id": "Type", "type": "text"},
        {"name": "Region", "id": "Region", "type": "text"},
        {"name": "Link", "id": "URL", "type": "text", "presentation": "markdown"},
    ]

    # Links to markdown
    for row in df_rows:
        row["URL"] = f"[Open]({row['URL']})" if row["URL"] and row["URL"] != "#" else "N/A"

    return dash_table.DataTable(
        data=df_rows,
        columns=columns,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Poppins, sans-serif",
            "maxWidth": "220px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_header={
            "backgroundColor": "#3C3970",
            "color": "#E2E8F0",
            "fontWeight": "bold",
        },
        style_data={
            "backgroundColor": "#2D2B55",
            "color": "#CDD6F4",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#252343"}],
    )


def create_timeline_chart(items: list[dict[str, Any]]) -> html.Div:
    dates = [it["published"].strftime("%Y-%m-%d") for it in items if it.get("published")]
    if not dates:
        return html.Div("No date data available for timeline")
    counts = Counter(dates)
    x = sorted(counts.keys())
    y = [counts[d] for d in x]
    fig = px.line(x=x, y=y, title="Items Over Time", labels={"x": "Date", "y": "Items"})
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CDD6F4",
        title_font_color="#A37FFF",
    )
    return dcc.Graph(figure=fig)


def render_intelligence_tab() -> html.Div:
    total_items = sum(len(v) for v in INTEL_DATA.values())
    return html.Div(
        [
            html.H2("Content Insights Dashboard", className="mb-4 text-center"),
            # Row 1: Recommendations
            create_recommendations_section(),
            # Row 2: Trending
            create_trending_section(),
            html.Hr(className="my-5"),
            html.H3("External Intelligence Feeds", className="mb-3"),
            # Summary stats
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H4(total_items, className="text-primary mb-0"),
                                    html.P(
                                        "Total Intelligence Items",
                                        className="text-muted small mb-0",
                                    ),
                                ]
                            )
                        ),
                        md=3,
                    ),
                ],
                className="mb-4",
            ),
            # Source cards
            html.H4("Sources", className="text-primary mb-3"),
            dbc.Row(create_intel_summary_cards(), className="mb-4"),
            # Timeline for all items
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.H5("Timeline", className="mb-0")),
                                    dbc.CardBody([create_timeline_chart([it for items in INTEL_DATA.values() for it in items])]),
                                ]
                            )
                        ],
                        md=12,
                    )
                ],
                className="mb-4",
            ),
            # Data display area
            html.Div(id="intelligence-data-display"),
            dcc.Store(id="selected-intel-source"),
        ]
    )


def register_intelligence_callbacks(app):
    # Single callback for all source buttons using app.callback
    input_list = [Input(f"btn-intel-{source_id}", "n_clicks") for source_id in INTEL_SOURCES_CONFIG]

    @app.callback(
        Output("intelligence-data-display", "children"),
        Output("selected-intel-source", "data"),
        input_list,
        prevent_initial_call=True,
    )
    def display_intel_data(*n_clicks_list):
        from dash import callback_context

        ctx = callback_context
        if not ctx.triggered:
            return html.Div(), None

        # Find which button was triggered
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        source_id = triggered_id.replace("btn-intel-", "")

        if source_id in INTEL_SOURCES_CONFIG:
            cfg = INTEL_SOURCES_CONFIG[source_id]
            items = INTEL_DATA[source_id]
            return (
                html.Div(
                    [
                        html.Hr(),
                        html.H4(
                            [
                                html.Span(cfg["icon"], className="me-2"),
                                f"{cfg['name']} Items",
                            ],
                            className="text-primary mb-3",
                        ),
                        create_intel_table(source_id, items),
                    ]
                ),
                source_id,
            )
        return html.Div(), None
