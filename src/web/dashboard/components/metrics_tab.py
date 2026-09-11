"""Metrics Dashboard Tab - ETL Performance and System Health Visualization
Displays ETL metrics, performance charts, and error tracking
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, dash_table, dcc, html

# Import shared utilities
from src.web.dashboard.utils import get_data_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_FRESHNESS_STYLES = {
    "fresh": ("🟢", "success"),
    "stale": ("🟡", "warning"),
    "critical": ("🔴", "danger"),
}


def _load_freshness_summary() -> dict | None:
    """Load the data-freshness watcher's latest summary, if it exists."""
    path = Path(DATA_DIR) / "watchers" / "data_freshness" / "freshness_latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _render_freshness_card() -> html.Div:
    """Source-freshness card (data_freshness_watcher output) for the Metrics tab."""
    summary = _load_freshness_summary()
    if not summary:
        return html.Div()  # watcher hasn't run yet — render nothing
    counts = summary.get("counts", {})
    offenders = [s for s in summary.get("sources", []) if s["status"] != "fresh"]
    offenders.sort(key=lambda s: (s["status"] != "critical", -(s["age_hours"] or 1e9)))

    chips = [
        dbc.Badge(f"🟢 {counts.get('fresh', 0)} frescos", color="success", className="me-2"),
        dbc.Badge(f"🟡 {counts.get('stale', 0)} stale", color="warning", className="me-2"),
        dbc.Badge(f"🔴 {counts.get('critical', 0)} críticos", color="danger", className="me-2"),
    ]
    rows = [
        html.Li(
            [
                dbc.Badge(f"{age_badge} {s['label']}", color=age_color, className="me-2"),
                html.Small(
                    f"{s['age_hours']:.0f}h" if s["age_hours"] is not None else "sin fichero",
                    className="text-muted",
                ),
            ],
            className="mb-1",
        )
        for s in offenders[:8]
        for age_badge, age_color in [_FRESHNESS_STYLES.get(s["status"], ("❔", "secondary"))]
    ] or [html.Li("Todas las fuentes están frescas ✨", className="text-success")]

    return dbc.Card(
        [
            dbc.CardHeader(html.H5("🩺 Source Freshness", className="mb-0")),
            dbc.CardBody(
                [
                    html.Div(chips, className="mb-2"),
                    html.Ul(rows, className="mb-0 ms-3"),
                    html.Small(
                        f"Último check: {str(summary.get('checked_at', ''))[:19]} (data_freshness_watcher, tras cada run del orquestador)",
                        className="text-muted",
                    ),
                ]
            ),
        ],
        className="mb-4",
    )


# Constants
# Constants
DATA_DIR = get_data_path("")  # Root data directory


class MetricsManager:
    """Manages metrics data loading and processing for the dashboard.

    Primary source is the orchestrator aggregate ``data/metrics/etl_runs_latest.json``
    (one record per ETL). Run history for trends/errors is rebuilt from per-component
    ``run_summary_*.json`` files, but only those modified within the recent window —
    the data directory can hold tens of thousands of historical summaries and reading
    them all blocks the dashboard for minutes.
    """

    RECENT_WINDOW_DAYS = 7
    RELOAD_TTL_SECONDS = 300
    MAX_HISTORY_FILES = 2000

    def __init__(self):
        """Initialize the MetricsManager."""
        self.metrics_data: list[dict] = []
        self._history: list[dict] = []
        self.loaded = False
        self.last_updated: datetime | None = None

    def load_data(self, force_refresh: bool = False):
        """Load per-source metrics from the orchestrator summary plus recent runs."""
        now = datetime.now(timezone.utc)
        if self.loaded and not force_refresh and self.last_updated and (now - self.last_updated).total_seconds() < self.RELOAD_TTL_SECONDS:
            return

        logger.info("Loading metrics data...")
        self.metrics_data = []
        self._history = []

        try:
            root_path = Path(DATA_DIR)

            # 1) Latest run per ETL from the orchestrator aggregate
            latest_by_name: dict[str, dict] = {}
            runs_file = root_path / "metrics" / "etl_runs_latest.json"
            if runs_file.exists():
                with open(runs_file, encoding="utf-8") as f:
                    payload = json.load(f)
                records = payload.get("runs", {}) if isinstance(payload, dict) else {}
                if isinstance(records, dict):
                    for name, rec in records.items():
                        if isinstance(rec, dict):
                            latest_by_name[name] = rec
                elif isinstance(records, list):
                    for rec in records:
                        if isinstance(rec, dict) and rec.get("etl_name"):
                            latest_by_name[rec["etl_name"]] = rec
            logger.info(f"Latest-run records from orchestrator summary: {len(latest_by_name)}")

            # 2) Recent run history (bounded by mtime window) for trends and error counts
            self._history = self._load_recent_history(root_path, now)
            logger.info(f"Recent run events loaded: {len(self._history)}")

            # 3) Aggregate history per source
            stats: dict[str, dict] = {}
            for event in self._history:
                entry = stats.setdefault(
                    event["name"],
                    {"runs": 0, "success_runs": 0, "errors": 0, "durations": [], "last": None},
                )
                entry["runs"] += 1
                entry["success_runs"] += 1 if event["success"] else 0
                entry["errors"] += event["error_count"]
                entry["durations"].append(event["duration"])
                if entry["last"] is None or event["timestamp"] > entry["last"]:
                    entry["last"] = event["timestamp"]

            # 4) Build one record per source (history sources plus orchestrator summary)
            names = set(stats) | set(latest_by_name)
            for name in names:
                entry = stats.get(name, {"runs": 0, "success_runs": 0, "errors": 0, "durations": [], "last": None})
                latest = latest_by_name.get(name, {})
                last_run_time = self._parse_datetime(latest.get("end_time")) or entry["last"]
                durations = entry["durations"]
                avg_duration = round(sum(durations) / len(durations), 3) if durations else latest.get("duration_seconds", 0.0)
                runs_total = entry["runs"]
                success_rate = round(entry["success_runs"] / runs_total * 100, 1) if runs_total else (100.0 if latest.get("success") else 0.0)
                self.metrics_data.append(
                    {
                        "name": name,
                        "last_run_time": last_run_time,
                        "items_processed": latest.get("records_loaded", 0),
                        "success_count": entry["success_runs"],
                        "error_count": entry["errors"] if runs_total else latest.get("error_count", 0),
                        "avg_duration": avg_duration,
                        "total_duration": round(sum(durations), 3),
                        "error_details": latest.get("errors_detail", latest.get("error_details", [])),
                        "status": "success" if latest.get("success") else ("failed" if latest else "unknown"),
                        "start_time": self._parse_datetime(latest.get("start_time")),
                        "end_time": last_run_time,
                        "success_rate": success_rate,
                        "runs_7d": runs_total,
                    }
                )

            # Sort by last run time (newest first)
            self.metrics_data.sort(
                key=lambda x: x.get("last_run_time") or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )

            self.last_updated = now
            self.loaded = True
            logger.info(f"Total metrics loaded: {len(self.metrics_data)} sources")

        except Exception as e:
            logger.error(f"Error loading metrics data: {e}")
            self.loaded = True

    def _load_recent_history(self, root_path: Path, now: datetime) -> list[dict]:
        """Collect run events from run_summary files modified within the recent window."""
        cutoff = now - timedelta(days=self.RECENT_WINDOW_DAYS)
        events: list[dict] = []
        files_read = 0
        try:
            for component_dir in root_path.iterdir():
                output_dir = component_dir / "output"
                if not output_dir.is_dir():
                    continue
                for summary_file in output_dir.glob("run_summary_*.json"):
                    try:
                        mtime = datetime.fromtimestamp(summary_file.stat().st_mtime, tz=timezone.utc)
                        if mtime < cutoff:
                            continue
                        if files_read >= self.MAX_HISTORY_FILES:
                            logger.warning("History scan hit MAX_HISTORY_FILES cap; trends may be partial")
                            return events
                        with open(summary_file, encoding="utf-8") as f:
                            data = json.load(f)
                        records = data if isinstance(data, list) else [data]
                        for rec in records:
                            if not isinstance(rec, dict):
                                continue
                            ts = self._parse_datetime(rec.get("end_time") or rec.get("start_time"))
                            if ts is None:
                                continue
                            events.append(
                                {
                                    "name": rec.get("etl_name", rec.get("name", "Unknown ETL")),
                                    "timestamp": ts,
                                    "duration": rec.get("duration_seconds", 0.0),
                                    "success": bool(rec.get("success", rec.get("status") == "success")),
                                    "error_count": rec.get("error_count", 0),
                                }
                            )
                        files_read += 1
                    except Exception as e:
                        logger.debug(f"Skipping metrics file {summary_file}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error scanning run summaries: {e}")
        return events

    def _parse_datetime(self, date_str):
        """Parse an ISO datetime string into a timezone-aware UTC datetime.

        Deliberately NOT ``utils.parse_date_universal``: run summaries are
        written by ``BaseETL`` via naive ``utcnow().isoformat()``, so naive
        strings mean UTC here — the shared parser would reinterpret them as
        server-local and shift every run time by the host offset.
        """
        if not date_str or not isinstance(date_str, str):
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def get_metrics_summary(self):
        """Get summary statistics across all ETL sources."""
        if not self.loaded:
            self.load_data()

        if not self.metrics_data:
            return {
                "total_sources": 0,
                "avg_success_rate": 0.0,
                "total_items_processed": 0,
                "total_errors": 0,
                "last_24h_errors": 0,
                "last_updated": self.last_updated,
            }

        success_rates = [m["success_rate"] for m in self.metrics_data]
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)
        last_24h_errors = sum(m["error_count"] for m in self.metrics_data if m["last_run_time"] and m["last_run_time"] >= day_ago)

        return {
            "total_sources": len(self.metrics_data),
            "avg_success_rate": round(sum(success_rates) / len(success_rates), 1),
            "total_items_processed": sum(m["items_processed"] for m in self.metrics_data),
            "total_errors": sum(m["error_count"] for m in self.metrics_data),
            "last_24h_errors": last_24h_errors,
            "last_updated": self.last_updated,
        }

    def get_error_counts(self):
        """Get error counts per source for the last 24 hours."""
        if not self.loaded:
            self.load_data()

        error_counts = {}
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)

        for event in self._history:
            if event["error_count"] > 0 and day_ago <= event["timestamp"] <= now:
                error_counts[event["name"]] = error_counts.get(event["name"], 0) + event["error_count"]

        return dict(sorted(error_counts.items(), key=lambda kv: kv[1], reverse=True))

    def get_time_series_data(self, days=7):
        """Get per-run time series data for the specified number of days."""
        if not self.loaded:
            self.load_data()

        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=days)

        time_series = [
            {
                "timestamp": event["timestamp"],
                "name": event["name"],
                "duration": event["duration"],
                "success_rate": 100.0 if event["success"] else 0.0,
                "status": "success" if event["success"] else "failed",
                "error_count": event["error_count"],
            }
            for event in self._history
            if event["timestamp"] >= cutoff_date
        ]

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

    return html.Div(
        [
            # Header with summary statistics
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-chart-line me-2"),
                                    "ETL Metrics Dashboard",
                                ],
                                className="text-primary mb-3",
                            ),
                            # Summary cards
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                summary["total_sources"],
                                                                className="text-primary mb-0",
                                                            ),
                                                            html.P(
                                                                "Total ETL Sources",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                f"{summary['avg_success_rate']:.1f}%",
                                                                className="text-success mb-0",
                                                            ),
                                                            html.P(
                                                                "Avg Success Rate",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                summary["total_items_processed"],
                                                                className="text-info mb-0",
                                                            ),
                                                            html.P(
                                                                "Items Processed",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                summary["last_24h_errors"],
                                                                className="text-danger mb-0",
                                                                style={"color": ("red" if summary["last_24h_errors"] > 0 else "inherit")},
                                                            ),
                                                            html.P(
                                                                "Last 24h Errors",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=3,
                                    ),
                                ],
                                className="mb-4",
                            ),
                        ]
                    )
                ]
            ),
            _render_freshness_card(),
            # Charts and tables
            dbc.Row(
                [
                    # Time Series Chart
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H5(
                                                "ETL Performance Trends (Last 7 Days)",
                                                className="mb-0",
                                            )
                                        ]
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="metrics-time-series-chart",
                                                figure=create_time_series_chart(metrics_manager.get_time_series_data(days=7)),
                                                style={"height": "400px"},
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        xs=12,
                        md=8,
                    ),
                    # Error Distribution Chart
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("Error Distribution", className="mb-0")]),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="metrics-error-chart",
                                                figure=create_error_chart(metrics_manager.get_error_counts()),
                                                style={"height": "400px"},
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        xs=12,
                        md=4,
                    ),
                ],
                className="mb-4",
            ),
            # Metrics Table
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader([html.H5("ETL Sources Details", className="mb-0")]),
                                    dbc.CardBody(
                                        [
                                            # Auto-refresh trigger lives here so the
                                            # callback is registered against the layout
                                            dcc.Interval(id="metrics-update-interval", interval=60 * 1000, n_intervals=0),
                                            html.Div(
                                                create_metrics_table(metrics_manager.metrics_data),
                                                id="metrics-table-container",
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-4",
            ),
            # Error Details Section (hidden by default)
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(id="error-details-container", style={"display": "none"}),
                        ],
                        width=12,
                    ),
                ]
            ),
        ]
    )


def register_metrics_callbacks(app):
    """Register callbacks for metrics tab functionality."""

    @app.callback(
        [
            Output("metrics-time-series-chart", "figure"),
            Output("metrics-error-chart", "figure"),
            Output("metrics-table-container", "children"),
        ],
        [Input("metrics-update-interval", "n_intervals")],
    )
    def update_metrics_data(n_intervals):
        """Update metrics charts and table."""
        try:
            # Reload data to get latest metrics
            metrics_manager.load_data(force_refresh=True)

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
            return (
                empty_fig,
                empty_fig,
                dbc.Alert(f"Error loading metrics data: {e}", color="danger"),
            )

    @app.callback(
        Output("error-details", "children", allow_duplicate=True),
        Input("metrics-table", "active_cell"),
        [State("metrics-table", "data")],
        prevent_initial_call=True,
    )
    def show_error_details(active_cell, table_data):
        """Show detailed error logs for selected ETL source."""
        try:
            if not active_cell or not table_data:
                return html.Div()

            # Get row and column from active_cell
            row = active_cell["row"]

            # table_data rows are dicts keyed by column id
            if row < len(table_data) and "name" in table_data[row]:
                source_name = table_data[row]["name"]

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
            x=0.5,
            y=0.5,
            text="No time series data available",
            xref="paper",
            yref="paper",
            showarrow=False,
        )

    # Create DataFrame for easier plotting
    df = pd.DataFrame(time_series_data)
    df["date"] = df["timestamp"].dt.date

    # Daily aggregates: run count, error count and mean duration across sources
    daily_data = df.groupby("date").agg(runs=("name", "count"), errors=("error_count", "sum"), duration=("duration", "mean")).reset_index()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily_data["date"],
            y=daily_data["runs"],
            name="Runs",
            marker_color="rgba(31,119,180,0.55)",
        )
    )
    fig.add_trace(
        go.Bar(
            x=daily_data["date"],
            y=daily_data["errors"],
            name="Errors",
            marker_color="rgba(214,39,40,0.75)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_data["date"],
            y=daily_data["duration"],
            mode="lines+markers",
            name="Avg duration (s)",
            yaxis="y2",
            line={"width": 2},
            marker={"size": 6},
        )
    )

    fig.update_layout(
        title="ETL Performance Trends (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Runs / Errors",
        yaxis2={"title": "Avg duration (s)", "overlaying": "y", "side": "right"},
        hovermode="x unified",
        template="plotly_white",
        height=400,
        barmode="group",
        legend={"orientation": "h", "yanchor": "bottom"},
    )

    return fig


def create_error_chart(error_counts):
    """Create bar chart showing error counts per source."""
    if not error_counts:
        return go.Figure().add_annotation(
            x=0.5,
            y=0.5,
            text="No errors in last 24 hours",
            xref="paper",
            yref="paper",
            showarrow=False,
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
        color_continuous_scale="Reds",
    )

    fig.update_layout(
        xaxis_title="ETL Source",
        yaxis_title="Error Count",
        height=400,
        showlegend=False,
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
            "runs_7d": metric.get("runs_7d", 0),
            "success_rate": f"{metric['success_rate']:.1f}%",
            "avg_duration": f"{metric['avg_duration']:.2f}s",
            "error_count": metric["error_count"],
            "status": metric["status"],
            "status_class": status_class,
        }
        table_data.append(row)

    # Create DataTable
    table = dash_table.DataTable(
        id="metrics-table",
        data=table_data,
        columns=[
            {"name": "name", "id": "name", "deletable": False},
            {"name": "last_run_time", "id": "last_run_time", "deletable": False},
            {"name": "runs_7d", "id": "runs_7d", "deletable": False},
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
                "backgroundColor": "#f8f9fa",
            },
            {
                "if": {"column_id": "status_class", "filter_query": "danger"},
                "backgroundColor": "#f8d7da",
                "color": "#721c24",
            },
            {
                "if": {"column_id": "status_class", "filter_query": "success"},
                "backgroundColor": "#d1e7dd",
                "color": "#0f5132",
            },
        ],
        page_size=20,
        sort_action="native",
    )

    return html.Div(
        [
            table,
            html.Small(
                f"Last updated: {_format_datetime(metrics_manager.last_updated or datetime.now(timezone.utc))} | Auto-refresh every 60 seconds",
                className="text-muted mt-3",
            ),
        ]
    )


def create_error_details_section(source_name, error_details):
    """Create detailed error information section."""
    if not error_details:
        return dbc.Alert(f"No error details available for {source_name}", color="info")

    # Error details header
    header = dbc.Row(
        [
            dbc.Col(
                [
                    html.H5(f"Error Details for {source_name}", className="text-danger mb-3"),
                    dbc.Button(
                        "Close",
                        id="close-error-details",
                        color="secondary",
                        size="sm",
                        className="mb-3",
                    ),
                ]
            ),
        ]
    )

    # Error details list
    error_items = []
    for i, error in enumerate(error_details[:10]):  # Limit to last 10 errors
        error_items.append(
            dbc.Alert(
                [
                    html.H6(f"Error {i + 1}:", className="alert-heading"),
                    html.P(error.get("message", "Unknown error"), className="mb-2"),
                    html.Small(f"Time: {_format_datetime(error.get('timestamp'))} | Context: {error.get('context', 'No context')}"),
                ],
                color="danger",
                className="mb-2",
            )
        )

    if len(error_details) > 10:
        error_items.append(dbc.Alert(f"... and {len(error_details) - 10} more errors", color="warning"))

    return html.Div(
        [
            header,
            html.Div(error_items),
            html.Div(
                style={"display": "none"},  # Hidden close button callback will show this
                id="error-details-data",
            ),
        ]
    )


def _format_datetime(dt):
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")
