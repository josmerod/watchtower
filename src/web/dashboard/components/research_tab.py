"""Research Dashboard Tab
Specialized for ADHD research publications and neurodivergent-friendly locations
"""

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, dash_table, dcc, html

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Research sources configuration
RESEARCH_SOURCES_CONFIG = {
    "adhd_publications": {
        "path": get_data_path("adhd_publications", "output", "json", "latest_papers.json"),
        "name": "ADHD Publications",
        "icon": "🧠",
        "category": "Medical Research",
        "color": "primary",
        "description": "Latest ADHD research publications from PubMed and academic sources",
    },
    "adhd_friendly_locations": {
        "path": get_data_path("adhd_friendly_locations", "adhd_locations_latest.json"),
        "name": "ADHD-Friendly Locations",
        "icon": "📍",
        "category": "Accessibility",
        "color": "success",
        "description": "Curated list of ADHD-friendly spaces, services, and accommodations",
    },
}

# NEW: Repository-based loading (SOLID Pattern)
class ResearchRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for research data."""

    def __init__(self, data_path: str):
        """Initialize research repository.

        Args:
            data_path: Path to research data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of research items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of research item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            # Handle structured data
            if "papers" in raw_data:
                return raw_data["papers"]
            return [raw_data]
        else:
            return []

# Create singleton instances for each source
adhd_publications_repo = ResearchRepository(RESEARCH_SOURCES_CONFIG["adhd_publications"]["path"])
adhd_friendly_locations_repo = ResearchRepository(RESEARCH_SOURCES_CONFIG["adhd_friendly_locations"]["path"])


def load_research_data(file_path):
    """Load research data using repository pattern (NEW)."""
    try:
        # Select appropriate repository based on file path
        if "adhd_publications" in file_path or "latest_papers" in file_path:
            data = adhd_publications_repo.get()
        elif "adhd_friendly_locations" in file_path or "adhd_locations" in file_path:
            data = adhd_friendly_locations_repo.get()
        else:
            logger.info(f"Unknown research data source: {file_path}")
            return []

        processed_data = []
        for item in data:
            processed_item = process_research_item(item)
            if processed_item:
                processed_data.append(processed_item)
        return processed_data
    except Exception as e:
        logger.error(f"Error loading research data from {file_path}: {e}")
        return []


def process_research_item(item):
    """Process individual research item with standardized fields"""
    try:
        # Extract common fields
        title = item.get("title", item.get("name", item.get("paper_title", "Unknown Study")))
        abstract = item.get(
            "abstract",
            item.get("description", item.get("summary", "No abstract available")),
        )

        # Handle publication date
        pub_date = None
        for date_field in ["publication_date", "published_date", "date", "created_at"]:
            if date_field in item:
                pub_date = parse_date_universal(item[date_field])
                break

        # Authors processing
        authors = item.get("authors", item.get("author", []))
        if isinstance(authors, str):
            authors = [authors]
        authors_str = ", ".join(authors[:3]) if authors else "Unknown"
        if len(authors) > 3:
            authors_str += f" +{len(authors) - 3} more"

        # Research-specific fields
        journal = item.get("journal", item.get("publication", "Unknown Journal"))
        doi = item.get("doi", "")
        pmid = item.get("pmid", item.get("pubmed_id", ""))

        # Study type and methodology
        study_type = item.get("study_type", item.get("methodology", "Unknown"))
        sample_size = item.get("sample_size", item.get("participants", 0))

        # Location-specific fields (for ADHD-friendly locations)
        location_type = item.get("location_type", item.get("type", "Unknown"))
        address = item.get("address", item.get("location", ""))
        accessibility_features = item.get("accessibility_features", item.get("features", []))
        rating = item.get("rating", item.get("score", 0))

        # Research impact metrics
        citation_count = item.get("citation_count", item.get("citations", 0))
        impact_factor = item.get("impact_factor", 0)

        # Keywords and categories
        keywords = item.get("keywords", item.get("tags", []))
        if isinstance(keywords, str):
            keywords = [keywords]

        return {
            "title": title,
            "abstract": abstract[:300] + "..." if len(abstract) > 300 else abstract,
            "full_abstract": abstract,
            "authors": authors,
            "authors_str": authors_str,
            "publication_date": pub_date,
            "journal": journal,
            "doi": doi,
            "pmid": pmid,
            "study_type": study_type,
            "sample_size": int(sample_size) if sample_size else 0,
            "location_type": location_type,
            "address": address,
            "accessibility_features": (accessibility_features if isinstance(accessibility_features, list) else []),
            "rating": float(rating) if rating else 0,
            "citation_count": int(citation_count) if citation_count else 0,
            "impact_factor": float(impact_factor) if impact_factor else 0,
            "keywords": keywords,
            "url": item.get("url", item.get("link", "#")),
            "source": item.get("source", "unknown"),
            "raw_data": item,
        }
    except Exception as e:
        logger.error(f"Error processing research item: {e}")
        return None


# Load all research data
RESEARCH_DATA = {}
for source_id, config in RESEARCH_SOURCES_CONFIG.items():
    data = load_research_data(config["path"])
    RESEARCH_DATA[source_id] = data
    logger.info(f"Loaded {len(data)} items for {config['name']}")

# Combine all data for analytics
ALL_RESEARCH = []
for source_id, data in RESEARCH_DATA.items():
    for item in data:
        item["source_category"] = RESEARCH_SOURCES_CONFIG[source_id]["category"]
        item["source_name"] = RESEARCH_SOURCES_CONFIG[source_id]["name"]
        ALL_RESEARCH.append(item)


def create_study_type_chart():
    """Create a pie chart showing distribution of study types"""
    research_papers = [item for item in ALL_RESEARCH if item["source_category"] == "Medical Research"]

    if not research_papers:
        return html.Div("No research papers available for visualization")

    # Count study types
    study_counts = Counter()
    for paper in research_papers:
        study_type = paper["study_type"] if paper["study_type"] != "Unknown" else "Other"
        study_counts[study_type] += 1

    fig = px.pie(
        values=list(study_counts.values()),
        names=list(study_counts.keys()),
        title="Distribution of Study Types",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CDD6F4",
        title_font_color="#A37FFF",
    )

    return dcc.Graph(figure=fig)


def create_publication_timeline():
    """Create a timeline chart showing publication trends"""
    research_papers = [item for item in ALL_RESEARCH if item["source_category"] == "Medical Research" and item["publication_date"]]

    if not research_papers:
        return html.Div("No publication date data available")

    # Group by month
    monthly_counts = Counter()
    for paper in research_papers:
        month_key = paper["publication_date"].strftime("%Y-%m")
        monthly_counts[month_key] += 1

    months = sorted(monthly_counts.keys())
    counts = [monthly_counts[month] for month in months]

    fig = go.Figure(
        data=go.Scatter(
            x=months,
            y=counts,
            mode="lines+markers",
            name="Publications",
            line=dict(color="#A37FFF", width=3),
            marker=dict(color="#A37FFF", size=8),
        )
    )

    fig.update_layout(
        title="ADHD Research Publications Over Time",
        xaxis_title="Month",
        yaxis_title="Number of Publications",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CDD6F4",
        title_font_color="#A37FFF",
    )

    return dcc.Graph(figure=fig)


def create_research_summary_cards():
    """Create summary cards for each research source"""
    cards = []

    for source_id, config in RESEARCH_SOURCES_CONFIG.items():
        data = RESEARCH_DATA[source_id]
        item_count = len(data)

        # Calculate source-specific metrics
        avg_citation = 0
        avg_sample_size = 0
        avg_rating = 0

        if data:
            if config["category"] == "Medical Research":
                # Research papers metrics
                valid_citations = [item["citation_count"] for item in data if item["citation_count"] > 0]
                if valid_citations:
                    avg_citation = sum(valid_citations) / len(valid_citations)

                valid_samples = [item["sample_size"] for item in data if item["sample_size"] > 0]
                if valid_samples:
                    avg_sample_size = sum(valid_samples) / len(valid_samples)
            else:
                # Location metrics
                valid_ratings = [item["rating"] for item in data if item["rating"] > 0]
                if valid_ratings:
                    avg_rating = sum(valid_ratings) / len(valid_ratings)

        # Get latest update
        latest_update = "No data"
        if data:
            timestamps = [item["publication_date"] for item in data if item["publication_date"]]
            if timestamps:
                latest_update = max(timestamps).strftime("%Y-%m-%d")

        # Status color
        status_color = config["color"] if item_count > 0 else "secondary"

        # Create metrics display based on category
        metrics_content = []
        if config["category"] == "Medical Research":
            metrics_content = [
                html.Div(
                    [
                        html.Strong("Avg Citations: "),
                        html.Span(
                            f"{avg_citation:.1f}" if avg_citation > 0 else "N/A",
                            className="text-info",
                        ),
                    ],
                    className="mb-1",
                ),
                html.Div(
                    [
                        html.Strong("Avg Sample Size: "),
                        html.Span(
                            f"{avg_sample_size:.0f}" if avg_sample_size > 0 else "N/A",
                            className="text-warning",
                        ),
                    ],
                    className="mb-1",
                ),
            ]
        else:
            metrics_content = [
                html.Div(
                    [
                        html.Strong("Avg Rating: "),
                        html.Span(
                            f"{avg_rating:.1f}/5" if avg_rating > 0 else "N/A",
                            className="text-success",
                        ),
                    ],
                    className="mb-1",
                )
            ]

        card = dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H6(
                            [
                                html.Span(config["icon"], className="me-2"),
                                config["name"],
                            ],
                            className="mb-0",
                        ),
                        dbc.Badge(
                            f"{item_count} items",
                            color=status_color,
                            className="float-end",
                        ),
                    ]
                ),
                dbc.CardBody(
                    [
                        html.P(config["description"], className="small text-muted mb-2"),
                        html.Div(
                            [
                                html.Strong("Category: "),
                                dbc.Badge(config["category"], color="info", className="me-2"),
                            ],
                            className="mb-1",
                        ),
                        *metrics_content,
                        html.Div(
                            [
                                html.Strong("Latest: "),
                                html.Span(latest_update, className="text-muted small"),
                            ],
                            className="mb-2",
                        ),
                        dbc.Button(
                            f"View {config['name']}",
                            id=f"btn-research-{source_id}",
                            color="outline-primary",
                            size="sm",
                            className="w-100",
                        ),
                    ]
                ),
            ],
            className="mb-3 h-100",
        )

        cards.append(dbc.Col(card, md=6))

    return cards


def create_research_table(source_id, items):
    """Create a detailed table for research items"""
    if not items:
        return dbc.Alert(
            "No research data available for this category.",
            color="info",
            className="text-center",
        )

    config = RESEARCH_SOURCES_CONFIG[source_id]

    # Sort items by date or relevance
    if config["category"] == "Medical Research":
        sorted_items = sorted(
            items,
            key=lambda x: (
                x["citation_count"],
                x["publication_date"] or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
    else:
        sorted_items = sorted(items, key=lambda x: x["rating"], reverse=True)

    # Convert to DataFrame
    df_data = []
    for item in sorted_items:
        if config["category"] == "Medical Research":
            # Research paper format
            date_str = item["publication_date"].strftime("%Y-%m-%d") if item["publication_date"] else "N/A"

            row = {
                "Title": (item["title"][:80] + "..." if len(item["title"]) > 80 else item["title"]),
                "Authors": item["authors_str"],
                "Journal": item["journal"],
                "Study Type": item["study_type"],
                "Sample Size": (f"{item['sample_size']:,}" if item["sample_size"] > 0 else "N/A"),
                "Citations": (f"{item['citation_count']:,}" if item["citation_count"] > 0 else "N/A"),
                "Publication Date": date_str,
                "DOI": item["doi"] if item["doi"] else "N/A",
                "Abstract": item["abstract"],
                "URL": item["url"],
            }
        else:
            # Location format
            features_str = ", ".join(item["accessibility_features"][:3]) if item["accessibility_features"] else "None listed"
            if len(item["accessibility_features"]) > 3:
                features_str += f" +{len(item['accessibility_features']) - 3} more"

            row = {
                "Name": item["title"],
                "Type": item["location_type"],
                "Address": item["address"] if item["address"] else "N/A",
                "Rating": f"{item['rating']:.1f}/5" if item["rating"] > 0 else "N/A",
                "Accessibility Features": features_str,
                "Description": item["abstract"],
                "URL": item["url"],
            }

        df_data.append(row)

    df = pd.DataFrame(df_data)

    # Create columns based on data type
    if config["category"] == "Medical Research":
        columns = [
            {"name": "Title", "id": "Title", "type": "text"},
            {"name": "Authors", "id": "Authors", "type": "text"},
            {"name": "Journal", "id": "Journal", "type": "text"},
            {"name": "Study Type", "id": "Study Type", "type": "text"},
            {"name": "Sample Size", "id": "Sample Size", "type": "text"},
            {"name": "Citations", "id": "Citations", "type": "text"},
            {"name": "Publication Date", "id": "Publication Date", "type": "text"},
            {"name": "DOI", "id": "DOI", "type": "text"},
            {"name": "Abstract", "id": "Abstract", "type": "text"},
            {"name": "Link", "id": "URL", "type": "text", "presentation": "markdown"},
        ]
    else:
        columns = [
            {"name": "Name", "id": "Name", "type": "text"},
            {"name": "Type", "id": "Type", "type": "text"},
            {"name": "Address", "id": "Address", "type": "text"},
            {"name": "Rating", "id": "Rating", "type": "text"},
            {
                "name": "Accessibility Features",
                "id": "Accessibility Features",
                "type": "text",
            },
            {"name": "Description", "id": "Description", "type": "text"},
            {"name": "Link", "id": "URL", "type": "text", "presentation": "markdown"},
        ]

    # Convert URLs to markdown links
    df["URL"] = df.apply(lambda row: f"[🔗 View]({row['URL']})" if row["URL"] != "#" else "N/A", axis=1)

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=columns,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Poppins, sans-serif",
            "maxWidth": "200px",
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
        tooltip_data=[{col: {"value": str(row[col]), "type": "markdown"} for col in ["Abstract", "Description"] if col in row} for row in df.to_dict("records")],
        tooltip_duration=None,
    )


def render_research_tab():
    """Main render function for the Research dashboard tab"""
    total_items = len(ALL_RESEARCH)
    research_papers = [item for item in ALL_RESEARCH if item["source_category"] == "Medical Research"]
    locations = [item for item in ALL_RESEARCH if item["source_category"] == "Accessibility"]

    # Calculate metrics
    total_citations = sum(item["citation_count"] for item in research_papers)
    avg_sample_size = 0
    if research_papers:
        valid_samples = [item["sample_size"] for item in research_papers if item["sample_size"] > 0]
        if valid_samples:
            avg_sample_size = sum(valid_samples) / len(valid_samples)

    return html.Div(
        [
            # Header with statistics
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-brain me-2"),
                                    "ADHD Research Dashboard",
                                ],
                                className="text-primary mb-3",
                            ),
                            # Summary statistics
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                len(research_papers),
                                                                className="text-primary mb-0",
                                                            ),
                                                            html.P(
                                                                "Research Papers",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                f"{total_citations:,}",
                                                                className="text-success mb-0",
                                                            ),
                                                            html.P(
                                                                "Total Citations",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                (f"{avg_sample_size:.0f}" if avg_sample_size > 0 else "N/A"),
                                                                className="text-info mb-0",
                                                            ),
                                                            html.P(
                                                                "Avg Sample Size",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                len(locations),
                                                                className="text-warning mb-0",
                                                            ),
                                                            html.P(
                                                                "ADHD-Friendly Locations",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        md=3,
                                    ),
                                ],
                                className="mb-4",
                            ),
                        ]
                    )
                ]
            ),
            # Analytics charts
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.H5("Study Types Distribution", className="mb-0")),
                                    dbc.CardBody([create_study_type_chart()]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.H5("Publication Timeline", className="mb-0")),
                                    dbc.CardBody([create_publication_timeline()]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            # Research categories
            html.H4("Research Categories", className="text-primary mb-3"),
            dbc.Row(create_research_summary_cards(), className="mb-4"),
            # Data display area
            html.Div(id="research-data-display"),
            # Storage for selected source
            dcc.Store(id="selected-research-source"),
        ]
    )


def register_research_callbacks(app):
    """Register callbacks for the Research dashboard tab"""
    # Create callbacks for each source button
    for source_id in RESEARCH_SOURCES_CONFIG:

        @callback(
            Output("research-data-display", "children"),
            Output("selected-research-source", "data"),
            Input(f"btn-research-{source_id}", "n_clicks"),
            prevent_initial_call=True,
        )
        def display_research_data(n_clicks, source_id=source_id):
            if n_clicks:
                config = RESEARCH_SOURCES_CONFIG[source_id]
                items = RESEARCH_DATA[source_id]

                return (
                    html.Div(
                        [
                            html.Hr(),
                            html.H4(
                                [
                                    html.Span(config["icon"], className="me-2"),
                                    f"{config['name']} Data",
                                ],
                                className="text-primary mb-3",
                            ),
                            create_research_table(source_id, items),
                        ]
                    ),
                    source_id,
                )

            return html.Div(), None


if __name__ == "__main__":
    print("Research Dashboard Tab - Data Summary:")
    for source_id, config in RESEARCH_SOURCES_CONFIG.items():
        item_count = len(RESEARCH_DATA[source_id])
        print(f"  {config['name']}: {item_count} items")

    total = len(ALL_RESEARCH)
    print(f"  Total: {total} research items across {len(RESEARCH_SOURCES_CONFIG)} sources")
