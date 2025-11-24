"""
Metrics Dashboard Tab - ETL Performance and System Health Visualization
Displays ETL metrics, performance charts, and error tracking
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Input, Output, State, dcc, html

# Import shared utilities
from src.web.dashboard.utils import get_data_path
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
    get_common_searchable_fields,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
# Constants
DATA_DIR = get_data_path("")  # Root data directory


class MetricsManager:
    """
    Manages metrics data loading and processing for the dashboard.
    Follows the VideoManager pattern for consistency.
    """

    def __init__(self):
        """Initialize the MetricsManager."""
        self.metrics_data = []
        self.loaded = False
        self.last_updated = None

    def load_data(self):
        """Load metrics data from the metrics directory."""
        logger.info("Loading metrics data...")
        self.metrics_data = []

        try:
            # Find all run summary JSON files in any output directory
            # Pattern: data/*/output/run_summary_*.json
            root_path = Path(DATA_DIR)
            logger.info(f"Searching for metrics in: {root_path}")
            files = list(root_path.glob("**/output/run_summary_*.json"))
            logger.info(f"Found {len(files)} metrics files")
            
            for metrics_file in files:
                try:
                    with open(metrics_file, encoding="utf-8") as f:
                        data = json.load(f)

                    if isinstance(data, list) and data:
                        # Ensure each metric record has required fields
                        for metric in data:
                            processed_metric = self._process_metric_record(metric)
                            if processed_metric:
                                self.metrics_data.append(processed_metric)
                    elif isinstance(data, dict):
                        # Handle single metric record (new format)
                        processed_metric = self._process_metric_record(data)
                        if processed_metric:
                            self.metrics_data.append(processed_metric)

                        logger.info(f"Loaded metric from {metrics_file.name}")

                except Exception as e:
                    logger.error(f"Error loading metrics from {metrics_file}: {e}")
                    continue

            # Sort by last run time (newest first)
            self.metrics_data.sort(
                key=lambda x: x.get("last_run_time", datetime.min.replace(tzinfo=timezone.utc)),
                reverse=True
            )

            self.last_updated = datetime.now(timezone.utc)
            logger.info(f"Total metrics loaded: {len(self.metrics_data)}")

        except Exception as e:
            logger.error(f"Error loading metrics data: {e}")

        self.loaded = True

    def _process_metric_record(self, metric):
        """Process and validate a single metric record."""
        try:
            # Ensure required fields exist
            if not isinstance(metric, dict):
                return None

            # Required fields for display
            processed = {
                "name": metric.get("etl_name", metric.get("name", "Unknown ETL")),
                "last_run_time": self._parse_datetime(metric.get("end_time", metric.get("last_run_time"))),
                "items_processed": metric.get("records_loaded", metric.get("items_processed", 0)),
                "success_count": metric.get("success_count", 0),
                "error_count": metric.get("error_count", 0),
                "avg_duration": metric.get("duration_seconds", metric.get("avg_duration", 0.0)),
                "total_duration": metric.get("duration_seconds", metric.get("total_duration", 0.0)),
                "error_details": metric.get("errors_detail", metric.get("error_details", [])),
                "status": metric.get("status", "unknown"),
                "start_time": self._parse_datetime(metric.get("start_time")),
                "end_time": self._parse_datetime(metric.get("end_time")),
            }

            # Calculate success rate
            total_runs = processed["success_count"] + processed["error_count"]
            if total_runs > 0:
                processed["success_rate"] = (processed["success_count"] / total_runs) * 100
            else:
                processed["success_rate"] = 0.0

            return processed

        except Exception as e:
            logger.warning(f"Error processing metric record: {e}")
            return None
    def _parse_datetime(self, date_str):
        """Parse datetime string with multiple format support."""
        if not date_str:
            return None

        try:
            dt = None
            # Try parsing ISO format first
            if isinstance(date_str, str) and 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Try other formats or timestamp
                if isinstance(date_str, (int, float)):
                    dt = datetime.fromtimestamp(date_str, tz=timezone.utc)
                else:
                    dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
            
            # Ensure timezone awareness
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
            
        except Exception as e:
            logger.warning(f"Error parsing datetime '{date_str}': {e}")
            return None

    def get_metrics_summary(self):
        """Get summary statistics of all metrics."""
        if not self.loaded:
            self.load_data()

        if not self.metrics_data:
            return {
                "total_sources": 0,
                "avg_success_rate": 0,
                "total_items_processed": 0,
                "total_errors": 0,
                "last_24h_errors": 0
            }

        total_sources = len(self.metrics_data)

        # Calculate averages
        success_rates = [m["success_rate"] for m in self.metrics_data if m["success_rate"] > 0]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

        total_items = sum(m["items_processed"] for m in self.metrics_data)
        total_errors = sum(m["error_count"] for m in self.metrics_data)

        # Calculate last 24h errors
        now = datetime.now(timezone.utc)
        last_24h_errors = 0
        for metric in self.metrics_data:
            if metric["last_run_time"] and (now - metric["last_run_time"]).total_seconds() <= 86400:
                last_24h_errors += metric["error_count"]

        return {
            "total_sources": total_sources,
            "avg_success_rate": round(avg_success_rate, 1),
            "total_items_processed": total_items,
            "total_errors": total_errors,
            "last_24h_errors": last_24h_errors,
            "last_updated": self.last_updated
        }

    def get_error_counts(self):
        """Get error counts per source for the last 24 hours."""
        if not self.loaded:
            self.load_data()

        error_counts = {}
        now = datetime.now(timezone.utc)

        for metric in self.metrics_data:
            if metric["error_count"] > 0:
                # Check if error is recent (within last 24 hours)
                if metric["last_run_time"] and (now - metric["last_run_time"]).total_seconds() <= 86400:
                    error_counts[metric["name"]] = metric["error_count"]

        return error_counts

    def get_time_series_data(self, days=7):
        """Get time series data for the specified number of days."""
        if not self.loaded:
            self.load_data()

        # Filter for data within the specified time range
        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=days)

        recent_data = [
            metric for metric in self.metrics_data
            if metric["last_run_time"] and metric["last_run_time"] >= cutoff_date
        ]

        # Create time series data for charts
        time_series = []
        for metric in recent_data:
            if metric["last_run_time"]:
                time_series.append({
                    "timestamp": metric["last_run_time"],
                    "name": metric["name"],
                    "duration": metric["avg_duration"],
                    "success_rate": metric["success_rate"],
                    "status": metric["status"]
                })

        # Sort by timestamp
        time_series.sort(key=lambda x: x["timestamp"])
        return time_series

    def get_source_by_name(self, name):
        """Get metrics data for a specific source by name."""
        if not self.loaded:
            self.load_data()

        for metric in self.metrics_data:
            if metric["name"] == name:
                return metric
        return None


# Global metrics manager instance
metrics_manager = MetricsManager()


def render_metrics_tab():
    """Main render function for the Metrics dashboard tab."""
    # Load metrics data
    metrics_manager.load_data()

    summary = metrics_manager.get_metrics_summary()

    return html.Div([
        # Header with summary statistics
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-chart-line me-2"),
                    "ETL Metrics Dashboard",
                ], className="text-primary mb-3"),
                # Summary cards
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(
                                    summary["total_sources"],
                                    className="text-primary mb-0",
                                ),
                                html.P(
                                    "Total ETL Sources",
                                    className="text-muted small mb-0",
                                ),
                            ])
                        ])
                    ], xs=12, sm=6, md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(
                                    f"{summary['avg_success_rate']:.1f}%",
                                    className="text-success mb-0",
                                ),
                                html.P(
                                    "Avg Success Rate",
                                    className="text-muted small mb-0",
                                ),
                            ])
                        ])
                    ], xs=12, sm=6, md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(
                                    summary["total_items_processed"],
                                    className="text-info mb-0",
                                ),
                                html.P(
                                    "Items Processed",
                                    className="text-muted small mb-0",
                                ),
                            ])
                        ])
                    ], xs=12, sm=6, md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(
                                    summary["last_24h_errors"],
                                    className="text-danger mb-0",
                                    style={"color": "red" if summary["last_24h_errors"] > 0 else "inherit"}
                                ),
                                html.P(
                                    "Last 24h Errors",
                                    className="text-muted small mb-0",
                                ),
                            ])
                        ])
                    ], xs=12, sm=6, md=3),
                ], className="mb-4"),
            ])
        ]),

        # Charts and tables
        dbc.Row([
            # Time Series Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("ETL Performance Trends (Last 7 Days)", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="metrics-time-series-chart",
                            style={"height": "400px"}
                        ),
                    ]),
                ]),
            ], xs=12, md=8),

            # Error Distribution Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("Error Distribution", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dcc.Graph(
                            id="metrics-error-chart",
                            style={"height": "400px"}
                        ),
                    ]),
                ]),
            ], xs=12, md=4),
        ], className="mb-4"),

        # Metrics Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("ETL Sources Details", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(id="metrics-table-container"),
                    ]),
                ]),
            ], width=12),
        ], className="mb-4"),

        # Error Details Section (hidden by default)
        dbc.Row([
            dbc.Col([
                html.Div(id="error-details-container", style={"display": "none"}),
            ], width=12),
        ]),
    ])


def register_metrics_callbacks(app):
    """Register callbacks for metrics tab functionality."""

    @app.callback(
        [Output("metrics-time-series-chart", "figure"),
         Output("metrics-error-chart", "figure"),
         Output("metrics-table-container", "children")],
        [Input("metrics-update-interval", "n_intervals")]
    )
    def update_metrics_data(n_intervals):
        """Update metrics charts and table."""
        try:
            # Reload data to get latest metrics
            metrics_manager.load_data()

            # Get time series data for charts
            time_series_data = metrics_manager.get_time_series_data(days=7)

            # Create time series chart
            time_series_fig = create_time_series_chart(time_series_data)

            # Get error counts for error chart
            error_counts = metrics_manager.get_error_counts()
            error_fig = create_error_chart(error_counts)

            # Create metrics table
            metrics_table = create_metrics_table(metrics_manager.metrics_data)

            return time_series_fig, error_fig, metrics_table

        except Exception as e:
            logger.error(f"Error updating metrics data: {e}")
            # Return empty components on error
            empty_fig = go.Figure()
            return empty_fig, empty_fig, dbc.Alert(
                f"Error loading metrics data: {e}", color="danger"
            )

    @app.callback(
        Output("error-details", "children", allow_duplicate=True),
        Input("metrics-table", "active_cell"),
        [State("metrics-table", "data")],
        prevent_initial_call=True
    )
    def show_error_details(active_cell, table_data):
        """Show detailed error logs for selected ETL source."""
        try:
            if not active_cell or not table_data:
                return html.Div()

            # Get row and column from active_cell
            row = active_cell["row"]
            col = active_cell["column"]

            # Get source name from the first column (name)
            if col == 0 and row < len(table_data):
                source_name = table_data[row][0]

                # Find metrics data for this source
                source_metric = metrics_manager.get_source_by_name(source_name)

                if source_metric and source_metric.get("error_details"):
                    return create_error_details_section(source_name, source_metric["error_details"])

            return html.Div()

        except Exception as e:
            logger.error(f"Error showing error details: {e}")
            return html.Div()


def create_time_series_chart(time_series_data):
    """Create time series chart for ETL performance trends."""
    if not time_series_data:
        return go.Figure().add_annotation(
            x=0.5, y=0.5,
            text="No time series data available",
            xref="paper", yref="paper",
            showarrow=False
        )

    # Create DataFrame for easier plotting
    df = pd.DataFrame(time_series_data)

    # Group by date for daily aggregates
    df["date"] = df["timestamp"].dt.date()
    daily_data = df.groupby(["date", "name"]).agg({
        "duration": "mean",
        "success_rate": "mean"
    }).reset_index()

    # Create scatter plot for each ETL source
    fig = go.Figure()

    # Add trace for each ETL source
    for source_name in daily_data["name"].unique():
        source_data = daily_data[daily_data["name"] == source_name]
        if not source_data.empty:
            fig.add_tracego(go.Scatter(
                x=source_data["date"],
                y=source_data["duration"],
                mode="lines+markers",
                name=source_name,
                line=dict(width=2),
                marker=dict(size=8)
            ))

    fig.update_layout(
        title="ETL Performance Trends (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Duration (seconds)",
        hovermode="x unified",
        template="plotly_white",
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom"
        )
    )

    return fig


def create_error_chart(error_counts):
    """Create bar chart showing error counts per source."""
    if not error_counts:
        return go.Figure().add_annotation(
            x=0.5, y=0.5,
            text="No errors in last 24 hours",
            xref="paper", yref="paper",
            showarrow=False
        )

    # Create DataFrame from error counts
    df = pd.DataFrame(list(error_counts.items()), columns=["source", "error_count"])

    # Create bar chart
    fig = px.bar(
        df,
        x="source",
        y="error_count",
        title="Error Count by Source (Last 24 Hours)",
        labels={"error_count": "Error Count", "source": "ETL Source"},
        color="error_count",
        color_continuous_scale="Reds"
    )

    fig.update_layout(
        xaxis_title="ETL Source",
        yaxis_title="Error Count",
        height=400,
        showlegend=False
    )

    return fig


def create_metrics_table(metrics_data):
    """Create a DataTable displaying ETL metrics."""
    if not metrics_data:
        return dbc.Alert("No metrics data available", color="info")

    # Prepare data for table
    table_data = []
    for metric in metrics_data:
        status_class = "success" if metric["success_rate"] >= 95 else "danger"

        row = {
            "name": metric["name"],
            "last_run_time": _format_datetime(metric["last_run_time"]),
            "items_processed": metric["items_processed"],
            "success_rate": f"{metric['success_rate']:.1f}%",
            "avg_duration": f"{metric['avg_duration']:.2f}s",
            "error_count": metric["error_count"],
            "status": metric["status"],
            "status_class": status_class
        }
        table_data.append(row)

    # Create DataTable
    table = dash_table.DataTable(
        id="metrics-table",
        data=table_data,
        columns=[
            {"name": "name", "id": "name", "deletable": False},
            {"name": "last_run_time", "id": "last_run_time", "deletable": False},
            {"name": "items_processed", "id": "items_processed", "deletable": False},
            {"name": "success_rate", "id": "success_rate", "deletable": False},
            {"name": "avg_duration", "id": "avg_duration", "deletable": False},
            {"name": "error_count", "id": "error_count", "deletable": False},
            {"name": "status", "id": "status", "deletable": False},
        ],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left"},
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
        style_data_conditional=[
            {
                "if": {"row_index": "odd", "column_id": "status_class"},
                "backgroundColor": "#f8f9fa"
            },
            {
                "if": {"column_id": "status_class", "filter_query": "danger"},
                "backgroundColor": "#f8d7da",
                "color": "#721c24"
            },
            {
                "if": {"column_id": "status_class", "filter_query": "success"},
                "backgroundColor": "#d1e7dd",
                "color": "#0f5132"
            },
        ],
        page_size=20,
        sort_action="native",
    )

    return html.Div([
        # Auto-refresh every 30 seconds
        dcc.Interval(
            id="metrics-update-interval",
            interval=30 * 1000,  # 30 seconds
            n_intervals=0
        ),

        table,

        html.Small(
            f"Last updated: {_format_datetime(metrics_manager.last_updated or datetime.now(timezone.utc))} | Auto-refresh every 30 seconds",
            className="text-muted mt-3"
        )
    ])


def create_error_details_section(source_name, error_details):
    """Create detailed error information section."""
    if not error_details:
        return dbc.Alert(f"No error details available for {source_name}", color="info")

    # Error details header
    header = dbc.Row([
        dbc.Col([
            html.H5(f"Error Details for {source_name}", className="text-danger mb-3"),
            dbc.Button("Close", id="close-error-details", color="secondary", size="sm", className="mb-3"),
        ]),
    ])

    # Error details list
    error_items = []
    for i, error in enumerate(error_details[:10]):  # Limit to last 10 errors
        error_items.append(
            dbc.Alert([
                html.H6(f"Error {i+1}:", className="alert-heading"),
                html.P(error.get("message", "Unknown error"), className="mb-2"),
                html.Small(
                    f"Time: {_format_datetime(error.get('timestamp'))} | "
                    f"Context: {error.get('context', 'No context')}"
                ),
            ], color="danger", className="mb-2")
        )

    if len(error_details) > 10:
        error_items.append(
            dbc.Alert(
                f"... and {len(error_details) - 10} more errors",
                color="warning"
            )
        )

    return html.Div([
        header,
        html.Div(error_items),
        html.Div(
            style={"display": "none"},  # Hidden close button callback will show this
            id="error-details-data"
        ),
    ])


def _format_datetime(dt):
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# Load data when module is imported
metrics_manager.load_data()