"""
Museums Dashboard Tab
Cultural institutions and museum data integration
"""

import json
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback, dash_table
from datetime import datetime, timezone
import os
import logging

# Import shared utilities
from src.web.dashboard.utils import get_data_path, file_exists, parse_date_universal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Museums configuration
MUSEUMS_CONFIG = {
    "museums": {
        "path": get_data_path("museums", "museums_latest.json"),
        "name": "Museums & Cultural Sites",
        "icon": "🏛️",
        "description": "Cultural institutions, exhibitions, and museum collections",
    }
}


def load_museums_data(file_path):
    """Load and parse museums data from JSON file"""
    try:
        if not file_exists(file_path):
            logger.warning(f"Museums data file not found: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return [
                process_museum_item(item) for item in data if process_museum_item(item)
            ]
        elif isinstance(data, dict):
            processed_item = process_museum_item(data)
            return [processed_item] if processed_item else []

        return []
    except Exception as e:
        logger.error(f"Error loading museums data from {file_path}: {e}")
        return []


def process_museum_item(item):
    """Process individual museum item"""
    try:
        return {
            "name": item.get("name", item.get("title", "Unknown Museum")),
            "description": item.get(
                "description", item.get("summary", "No description available")
            ),
            "location": item.get("location", item.get("address", "Unknown Location")),
            "type": item.get("type", item.get("category", "Museum")),
            "website": item.get("website", item.get("url", "#")),
            "rating": float(item.get("rating", 0)) if item.get("rating") else 0,
            "hours": item.get("hours", item.get("opening_hours", "Contact for hours")),
            "admission": item.get(
                "admission", item.get("price", "Contact for pricing")
            ),
            "exhibitions": item.get("exhibitions", item.get("current_exhibitions", [])),
            "raw_data": item,
        }
    except Exception as e:
        logger.error(f"Error processing museum item: {e}")
        return None


# Load museums data
MUSEUMS_DATA = load_museums_data(MUSEUMS_CONFIG["museums"]["path"])
logger.info(f"Loaded {len(MUSEUMS_DATA)} museums")


def create_museums_table():
    """Create table for museums data"""
    if not MUSEUMS_DATA:
        return dbc.Alert(
            "No museums data available.", color="info", className="text-center"
        )

    df_data = []
    for museum in MUSEUMS_DATA:
        exhibitions_str = (
            ", ".join(museum["exhibitions"][:3])
            if museum["exhibitions"]
            else "None listed"
        )
        if len(museum["exhibitions"]) > 3:
            exhibitions_str += f' +{len(museum["exhibitions"]) - 3} more'

        row = {
            "Name": museum["name"],
            "Location": museum["location"],
            "Type": museum["type"],
            "Rating": f"{museum['rating']:.1f}/5" if museum["rating"] > 0 else "N/A",
            "Hours": museum["hours"],
            "Admission": museum["admission"],
            "Current Exhibitions": exhibitions_str,
            "Description": (
                museum["description"][:150] + "..."
                if len(museum["description"]) > 150
                else museum["description"]
            ),
            "Website": museum["website"],
        }
        df_data.append(row)

    df = pd.DataFrame(df_data)

    columns = [
        {"name": "Name", "id": "Name", "type": "text"},
        {"name": "Location", "id": "Location", "type": "text"},
        {"name": "Type", "id": "Type", "type": "text"},
        {"name": "Rating", "id": "Rating", "type": "text"},
        {"name": "Hours", "id": "Hours", "type": "text"},
        {"name": "Admission", "id": "Admission", "type": "text"},
        {"name": "Current Exhibitions", "id": "Current Exhibitions", "type": "text"},
        {"name": "Description", "id": "Description", "type": "text"},
        {
            "name": "Website",
            "id": "Website",
            "type": "text",
            "presentation": "markdown",
        },
    ]

    df["Website"] = df.apply(
        lambda row: f"[🌐 Visit]({row['Website']})" if row["Website"] != "#" else "N/A",
        axis=1,
    )

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=columns,
        page_size=15,
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
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#252343"}
        ],
    )


def render_museums_tab():
    """Main render function for Museums tab"""
    museum_count = len(MUSEUMS_DATA)
    avg_rating = (
        sum(m["rating"] for m in MUSEUMS_DATA if m["rating"] > 0)
        / len([m for m in MUSEUMS_DATA if m["rating"] > 0])
        if any(m["rating"] > 0 for m in MUSEUMS_DATA)
        else 0
    )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-university me-2"),
                                    "Museums & Cultural Sites",
                                ],
                                className="text-primary mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                museum_count,
                                                                className="text-primary mb-0",
                                                            ),
                                                            html.P(
                                                                "Total Museums",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                (
                                                                    f"{avg_rating:.1f}/5"
                                                                    if avg_rating > 0
                                                                    else "N/A"
                                                                ),
                                                                className="text-success mb-0",
                                                            ),
                                                            html.P(
                                                                "Average Rating",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                "Cultural",
                                                                className="text-info mb-0",
                                                            ),
                                                            html.P(
                                                                "Focus",
                                                                className="text-muted small mb-0",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ],
                                        md=4,
                                    ),
                                ],
                                className="mb-4",
                            ),
                        ]
                    )
                ]
            ),
            html.H4("Museums Directory", className="text-primary mb-3"),
            create_museums_table(),
        ]
    )


if __name__ == "__main__":
    print(f"Museums Tab - Loaded {len(MUSEUMS_DATA)} museums")
