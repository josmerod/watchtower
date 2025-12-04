import json

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# --- Data Loading ---


def load_ms_skills_data():
    """Load Microsoft Skills watcher data."""
    file_path = get_data_path("watchers", "ms_skills", "events", "latest.json")
    if not file_exists(file_path):
        # Try alternative paths
        alt_paths = [
            get_data_path("watchers", "ms_skills", "ms_skills_events.json"),
            get_data_path("ms_skills", "ms_skills_latest.json"),
            get_data_path("watchers", "ms_skills.json"),
        ]
        for alt_path in alt_paths:
            if file_exists(alt_path):
                file_path = alt_path
                break

    if not file_exists(file_path):
        return []

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Try common keys
                for key in ["events", "items", "data", "skills", "courses"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # Single item
                if any(k in data for k in ["title", "name", "skill_name"]):
                    return [data]
            return []
    except Exception as e:
        print(f"Error loading MS Skills data: {e}")
        return []


def load_watcher_state():
    """Load watcher state information."""
    state_file = get_data_path("watchers", "ms_skills", "state.json")
    if not file_exists(state_file):
        return {}

    try:
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading watcher state: {e}")
        return {}


def create_watcher_status_cards():
    """Create watcher status cards."""
    ms_skills_data = load_ms_skills_data()
    watcher_state = load_watcher_state()

    # MS Skills status
    ms_skills_count = len(ms_skills_data)
    last_check = watcher_state.get("last_check_time", "Unknown")
    if last_check != "Unknown":
        try:
            dt = parse_date_universal(last_check)
            last_check = dt.strftime("%Y-%m-%d %H:%M") if dt else last_check
        except:
            pass

    status_color = "success" if ms_skills_count > 0 else "warning"

    cards = [
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4("🔍 MS Skills Watcher", className="card-title"),
                    html.H5(f"{ms_skills_count:,} Events", className=f"text-{status_color}"),
                    html.P(
                        f"Last check: {last_check}",
                        className="card-text small text-muted",
                    ),
                ]
            ),
            color=status_color,
            outline=True,
            className="mb-3",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.H4("📊 Watcher Health", className="card-title"),
                    html.H5(
                        "Active" if watcher_state else "Unknown",
                        className="text-success" if watcher_state else "text-warning",
                    ),
                    html.P(
                        "System monitoring status",
                        className="card-text small text-muted",
                    ),
                ]
            ),
            color="info",
            outline=True,
            className="mb-3",
        ),
    ]

    return cards


def create_ms_skills_chart(data):
    """Create MS Skills activity chart."""
    if not data:
        return go.Figure().add_annotation(
            text="No MS Skills data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    # Extract dates for activity timeline
    dates = []
    for item in data:
        for date_field in ["timestamp", "date", "created_at"]:
            if date_field in item:
                try:
                    dt = parse_date_universal(item[date_field])
                    if dt:
                        dates.append(dt.date())
                        break
                except:
                    pass

    if not dates:
        return go.Figure().add_annotation(
            text="No date information available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    # Count by date
    date_counts = pd.Series(dates).value_counts().sort_index()

    fig = px.line(
        x=date_counts.index,
        y=date_counts.values,
        title="MS Skills Activity Timeline",
        labels={"x": "Date", "y": "Events Count"},
    )
    fig.update_layout(height=400)

    return fig


def create_ms_skills_table(data):
    """Create MS Skills events table."""
    if not data:
        return html.Div(
            [
                html.P(
                    "No MS Skills events available.",
                    className="text-muted text-center p-4",
                )
            ]
        )

    # Limit to 50 most recent items
    recent_data = data[:50]

    table_rows = []
    for item in recent_data:
        # Extract fields
        title = item.get("title", item.get("name", item.get("skill_name", "Untitled")))

        # Event type
        event_type = item.get("event_type", item.get("type", item.get("change_type", "Update")))
        event_color = {
            "new": "success",
            "updated": "info",
            "removed": "danger",
            "changed": "warning",
        }.get(event_type.lower(), "secondary")

        # URL if available
        url = item.get("url", item.get("link", "#"))

        # Timestamp
        timestamp = "Unknown"
        for date_field in ["timestamp", "date", "created_at"]:
            if date_field in item:
                try:
                    dt = parse_date_universal(item[date_field])
                    if dt:
                        timestamp = dt.strftime("%Y-%m-%d %H:%M")
                        break
                except:
                    pass

        # Description or changes
        description = item.get("description", item.get("changes", item.get("summary", "")))
        if isinstance(description, list):
            description = ", ".join(description)
        description = description[:200] + ("..." if len(description) > 200 else "")

        # Category
        category = item.get("category", item.get("skill_area", item.get("subject", "General")))

        row = html.Tr(
            [
                html.Td(timestamp, className="text-muted small"),
                html.Td(dbc.Badge(event_type.title(), color=event_color)),
                html.Td(
                    [
                        (
                            html.A(
                                title,
                                href=url,
                                target="_blank",
                                className="text-decoration-none",
                            )
                            if url != "#"
                            else title
                        )
                    ]
                ),
                html.Td(category, className="text-info small"),
                html.Td(description, className="small text-muted"),
            ]
        )
        table_rows.append(row)

    table = dbc.Table(
        [
            html.Thead(
                [
                    html.Tr(
                        [
                            html.Th("Time", style={"width": "15%"}),
                            html.Th("Type", style={"width": "10%"}),
                            html.Th("Title", style={"width": "25%"}),
                            html.Th("Category", style={"width": "15%"}),
                            html.Th("Description", style={"width": "35%"}),
                        ]
                    )
                ]
            ),
            html.Tbody(table_rows),
        ],
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        size="sm",
    )

    return table


# --- Main Tab Function ---


def watchers_tab():
    """Main watchers/monitoring tab function."""
    ms_skills_data = load_ms_skills_data()

    return dbc.Container(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("👁️ Watchers & Monitoring", className="mb-3"),
                            html.P(
                                "System watchers, change detection, and monitoring intelligence",
                                className="text-muted mb-4",
                            ),
                        ]
                    )
                ]
            ),
            # Status Cards
            dbc.Row(
                [dbc.Col(card, md=6) for card in create_watcher_status_cards()],
                className="mb-4",
            ),
            # Activity Chart
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("📈 MS Skills Activity Timeline"),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="ms-skills-chart",
                                                figure=create_ms_skills_chart(ms_skills_data),
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        md=12,
                    )
                ],
                className="mb-4",
            ),
            # Events Table
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.H5("🔍 MS Skills Events", className="mb-0"),
                                            html.Small(
                                                f"Showing latest {min(50, len(ms_skills_data))} events",
                                                className="text-muted",
                                            ),
                                        ]
                                    ),
                                    dbc.CardBody([create_ms_skills_table(ms_skills_data)]),
                                ]
                            )
                        ]
                    )
                ]
            ),
        ],
        fluid=True,
    )
