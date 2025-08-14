"""
YouTube OCR Results Dashboard Tab

This component provides visualization and analysis of YouTube shorts OCR results using Dash.
"""

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback, ctx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.youtube_ocr_converter import load_youtube_ocr_data
except ImportError:
    print(
        "Could not import YouTube OCR converter. Please ensure the utility is properly installed."
    )
    converter = None
else:
    # Load data on module import
    try:
        converter = load_youtube_ocr_data(
            "data/youtube_shorts_ocr/youtube_shorts_ocr_results.json"
        )
    except Exception as e:
        print(f"Error loading YouTube OCR data: {e}")
        converter = None


def render_youtube_ocr_tab():
    """Render the YouTube OCR results dashboard tab."""

    if not converter or not converter.data:
        return html.Div(
            [
                dbc.Alert(
                    "No YouTube OCR data found. Please check if the data file exists.",
                    color="warning",
                    className="mb-4",
                ),
                html.Code(
                    "Expected file: data/youtube_shorts_ocr/youtube_shorts_ocr_results.json"
                ),
            ]
        )

    # Get summary statistics
    summary = converter.get_dashboard_summary()

    return html.Div(
        [
            # Header
            html.H2("🎬 YouTube Shorts OCR Analysis", className="mb-4"),
            # Key Metrics
            html.H4("📊 Key Metrics", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                summary.get("total_videos_analyzed", 0),
                                                className="card-title",
                                            ),
                                            html.P(
                                                "Total Videos Analyzed",
                                                className="card-text",
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                f"{summary.get('successful_processing_rate', 0)}%",
                                                className="card-title",
                                            ),
                                            html.P(
                                                "Success Rate", className="card-text"
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                summary.get("total_urls_extracted", 0),
                                                className="card-title",
                                            ),
                                            html.P(
                                                "URLs Extracted", className="card-text"
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                summary.get("unique_domains", 0),
                                                className="card-title",
                                            ),
                                            html.P(
                                                "Unique Domains", className="card-text"
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        width=3,
                    ),
                ],
                className="mb-4",
            ),
            # Processing Statistics
            html.H4("🔄 Processing Statistics", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                f"{summary.get('avg_confidence_score', 0)}%",
                                                className="card-title",
                                            ),
                                            html.P(
                                                "Avg Confidence Score",
                                                className="card-text",
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                f"{summary.get('avg_video_duration', 0)}s",
                                                className="card-title",
                                            ),
                                            html.P(
                                                "Avg Video Duration",
                                                className="card-text",
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H4(
                                                summary.get("videos_with_urls", 0),
                                                className="card-title",
                                            ),
                                            html.P(
                                                "Videos with URLs",
                                                className="card-text",
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                        width=4,
                    ),
                ],
                className="mb-4",
            ),
            # Data Tables Section
            html.H4("📋 Data Tables", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Select(
                                id="youtube-ocr-table-select",
                                options=[
                                    {
                                        "label": "Basic Video Information",
                                        "value": "basic",
                                    },
                                    {"label": "Extracted URLs", "value": "urls"},
                                    {"label": "Domain Statistics", "value": "domains"},
                                    {"label": "Text Analysis", "value": "text"},
                                    {
                                        "label": "Processing Statistics",
                                        "value": "processing",
                                    },
                                ],
                                value="basic",
                                className="mb-3",
                            )
                        ],
                        width=12,
                    )
                ]
            ),
            # Filters section
            html.Div(id="youtube-ocr-filters"),
            # Content area
            html.Div(id="youtube-ocr-content"),
            # Export section
            html.Hr(),
            html.H4("💾 Export Data", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Export to CSV",
                                id="youtube-ocr-export-btn",
                                color="primary",
                                className="mb-3",
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                "Show Most Common Domains",
                                id="youtube-ocr-domains-btn",
                                color="secondary",
                                className="mb-3",
                            )
                        ],
                        width=6,
                    ),
                ]
            ),
            # Export status
            html.Div(id="youtube-ocr-export-status"),
            # Most common domains display
            html.Div(id="youtube-ocr-domains-display"),
            # Processing date range
            (
                html.Div(
                    [
                        html.H4("📅 Processing Date Range", className="mb-3"),
                        html.P(
                            f"Start: {summary.get('processing_date_range', {}).get('start', 'N/A')}"
                        ),
                        html.P(
                            f"End: {summary.get('processing_date_range', {}).get('end', 'N/A')}"
                        ),
                    ]
                )
                if summary.get("processing_date_range", {}).get("start")
                else html.Div()
            ),
        ]
    )


def register_youtube_ocr_callbacks(app):
    """Register callbacks for YouTube OCR tab."""

    @app.callback(
        [
            Output("youtube-ocr-filters", "children"),
            Output("youtube-ocr-content", "children"),
        ],
        [Input("youtube-ocr-table-select", "value")],
    )
    def update_table_content(table_type):
        if not converter or not converter.data:
            return html.Div(), dbc.Alert("No data available", color="warning")

        if table_type == "basic":
            return render_basic_video_filters(), render_basic_video_content()
        elif table_type == "urls":
            return render_urls_filters(), render_urls_content()
        elif table_type == "domains":
            return html.Div(), render_domains_content()
        elif table_type == "text":
            return render_text_filters(), render_text_content()
        elif table_type == "processing":
            return html.Div(), render_processing_content()

        return html.Div(), html.Div()

    @app.callback(
        Output("youtube-ocr-export-status", "children"),
        [Input("youtube-ocr-export-btn", "n_clicks")],
    )
    def export_data(n_clicks):
        if not n_clicks or not converter:
            return html.Div()

        try:
            file_paths = converter.export_to_csv()
            if file_paths:
                return dbc.Alert(
                    [
                        html.H5(
                            "Data exported successfully!", className="alert-heading"
                        ),
                        html.Hr(),
                        html.Div(
                            [
                                html.P(f"✅ {table_name}: {path}")
                                for table_name, path in file_paths.items()
                            ]
                        ),
                    ],
                    color="success",
                )
            else:
                return dbc.Alert(
                    "Export failed. Please check the logs.", color="danger"
                )
        except Exception as e:
            return dbc.Alert(f"Export error: {str(e)}", color="danger")

    @app.callback(
        Output("youtube-ocr-domains-display", "children"),
        [Input("youtube-ocr-domains-btn", "n_clicks")],
    )
    def show_common_domains(n_clicks):
        if not n_clicks or not converter:
            return html.Div()

        summary = converter.get_dashboard_summary()
        most_common = summary.get("most_common_domains", {})

        if most_common:
            return dbc.Alert(
                [
                    html.H5("🏆 Most Common Domains", className="alert-heading"),
                    html.Hr(),
                    html.Div(
                        [
                            html.P(f"• {domain}: {count} mentions")
                            for domain, count in most_common.items()
                        ]
                    ),
                ],
                color="info",
            )
        else:
            return dbc.Alert("No domain data available.", color="info")


def render_basic_video_filters():
    """Render filters for basic video information."""
    if not converter:
        return html.Div()

    basic_df = converter.get_basic_video_table()
    if basic_df.empty:
        return html.Div()

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Label("Processing Status:"),
                    dbc.Select(
                        id="basic-status-filter",
                        options=[{"label": "All", "value": "all"}]
                        + [
                            {"label": status, "value": status}
                            for status in basic_df["processing_status"].unique()
                        ],
                        value="all",
                    ),
                ],
                width=6,
            ),
            dbc.Col(
                [
                    html.Label("URL Presence:"),
                    dbc.Select(
                        id="basic-url-filter",
                        options=[
                            {"label": "All", "value": "all"},
                            {"label": "Has URLs", "value": "has_urls"},
                            {"label": "No URLs", "value": "no_urls"},
                        ],
                        value="all",
                    ),
                ],
                width=6,
            ),
        ],
        className="mb-3",
    )


def render_basic_video_content():
    """Render basic video information content."""
    if not converter:
        return html.Div()

    basic_df = converter.get_basic_video_table()
    if basic_df.empty:
        return dbc.Alert("No basic video data available.", color="warning")

    # Create charts
    fig_duration = px.histogram(
        basic_df,
        x="duration",
        title="Video Duration Distribution",
        labels={"duration": "Duration (seconds)", "count": "Number of Videos"},
    )

    fig_confidence = px.histogram(
        basic_df,
        x="avg_confidence",
        title="OCR Confidence Score Distribution",
        labels={
            "avg_confidence": "Average Confidence (%)",
            "count": "Number of Videos",
        },
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col([dcc.Graph(figure=fig_duration)], width=6),
                    dbc.Col([dcc.Graph(figure=fig_confidence)], width=6),
                ],
                className="mb-4",
            ),
            # Data table
            html.Div([html.H5("Video Data Table"), html.Div(id="basic-video-table")]),
        ]
    )


def render_urls_filters():
    """Render filters for URLs."""
    if not converter:
        return html.Div()

    urls_df = converter.get_extracted_urls_table()
    if urls_df.empty:
        return html.Div()

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Label("Domain Filter:"),
                    dbc.Select(
                        id="urls-domain-filter",
                        options=[{"label": "All", "value": "all"}]
                        + [
                            {"label": domain, "value": domain}
                            for domain in sorted(urls_df["domain"].unique())
                        ],
                        value="all",
                    ),
                ],
                width=6,
            ),
            dbc.Col(
                [
                    html.Label("Minimum Confidence:"),
                    dcc.Slider(
                        id="urls-confidence-slider",
                        min=0,
                        max=100,
                        step=5,
                        value=50,
                        marks={i: f"{i}%" for i in range(0, 101, 25)},
                    ),
                ],
                width=6,
            ),
        ],
        className="mb-3",
    )


def render_urls_content():
    """Render URLs content."""
    if not converter:
        return html.Div()

    urls_df = converter.get_extracted_urls_table()
    if urls_df.empty:
        return dbc.Alert("No extracted URLs data available.", color="warning")

    # Create confidence chart
    fig_confidence = px.box(
        urls_df, x="domain", y="confidence", title="URL Confidence Scores by Domain"
    )
    fig_confidence.update_xaxes(tickangle=45)

    return html.Div(
        [
            dcc.Graph(figure=fig_confidence, className="mb-4"),
            html.Div([html.H5("URLs Data Table"), html.Div(id="urls-table")]),
        ]
    )


def render_domains_content():
    """Render domain statistics content."""
    if not converter:
        return html.Div()

    domain_stats = converter.get_domain_statistics()
    if domain_stats.empty:
        return dbc.Alert("No domain statistics available.", color="warning")

    # Create charts
    top_domains = domain_stats.head(10)
    fig_domains = px.bar(
        top_domains, x="domain", y="total_mentions", title="Top Domains by Mentions"
    )
    fig_domains.update_xaxes(tickangle=45)

    fig_scatter = px.scatter(
        domain_stats,
        x="avg_confidence",
        y="total_mentions",
        hover_data=["domain"],
        title="Domain Confidence vs Mentions",
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col([dcc.Graph(figure=fig_domains)], width=6),
                    dbc.Col([dcc.Graph(figure=fig_scatter)], width=6),
                ],
                className="mb-4",
            ),
            # Data table
            html.Div(
                [
                    html.H5("Domain Statistics Table"),
                    html.Div(domain_stats.to_dict("records")),
                ]
            ),
        ]
    )


def render_text_filters():
    """Render text analysis filters."""
    if not converter:
        return html.Div()

    text_df = converter.get_text_analysis_table()
    if text_df.empty:
        return html.Div()

    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Label("Minimum Text Length:"),
                    dcc.Slider(
                        id="text-length-slider",
                        min=0,
                        max=int(text_df["text_length"].max()),
                        step=100,
                        value=0,
                        marks={
                            i: str(i)
                            for i in range(
                                0, int(text_df["text_length"].max()) + 1, 500
                            )
                        },
                    ),
                ],
                width=6,
            ),
            dbc.Col(
                [
                    html.Label("Keyword Filter:"),
                    dbc.Select(
                        id="text-keyword-filter",
                        options=[
                            {"label": "All", "value": "all"},
                            {"label": "Website Keywords", "value": "website"},
                            {"label": "Productivity Keywords", "value": "productivity"},
                            {"label": "Design Keywords", "value": "design"},
                        ],
                        value="all",
                    ),
                ],
                width=6,
            ),
        ],
        className="mb-3",
    )


def render_text_content():
    """Render text analysis content."""
    if not converter:
        return html.Div()

    text_df = converter.get_text_analysis_table()
    if text_df.empty:
        return dbc.Alert("No text analysis data available.", color="warning")

    # Create charts
    fig_length = px.histogram(
        text_df,
        x="text_length",
        title="OCR Text Length Distribution",
        labels={"text_length": "Text Length (characters)", "count": "Number of Videos"},
    )

    # Keyword analysis
    keyword_counts = {
        "Website Keywords": text_df["contains_website_keywords"].sum(),
        "Productivity Keywords": text_df["contains_productivity_keywords"].sum(),
        "Design Keywords": text_df["contains_design_keywords"].sum(),
    }

    fig_keywords = px.bar(
        x=list(keyword_counts.keys()),
        y=list(keyword_counts.values()),
        title="Videos by Keyword Category",
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col([dcc.Graph(figure=fig_length)], width=6),
                    dbc.Col([dcc.Graph(figure=fig_keywords)], width=6),
                ],
                className="mb-4",
            ),
            # Data table
            html.Div(
                [html.H5("Text Analysis Table"), html.Div(id="text-analysis-table")]
            ),
        ]
    )


def render_processing_content():
    """Render processing statistics content."""
    if not converter:
        return html.Div()

    proc_stats = converter.get_processing_statistics()
    if proc_stats.empty:
        return dbc.Alert("No processing statistics available.", color="warning")

    # Convert to a more readable format
    stats_dict = proc_stats.iloc[0].to_dict()

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5("Processing Statistics", className="card-title"),
                    html.Div(
                        [
                            html.P(f"{key.replace('_', ' ').title()}: {value}")
                            for key, value in stats_dict.items()
                        ]
                    ),
                ]
            )
        ]
    )


if __name__ == "__main__":
    print("YouTube OCR Tab Component")
    if converter and converter.data:
        print(f"✅ Loaded {len(converter.data)} YouTube OCR records")
        summary = converter.get_dashboard_summary()
        print(f"📊 Summary: {summary}")
    else:
        print("❌ No YouTube OCR data loaded")
