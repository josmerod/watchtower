"""
AI Platforms Dashboard Tab
Integrates all AI platform monitoring ETLs including OpenAI, Anthropic, HuggingFace, etc.
"""

import json
import logging
import os
import sys

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, dash_table, html

from src.web.dashboard.utils import get_data_path, file_exists, parse_date_universal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI Platforms configuration with enhanced metadata
AI_PLATFORMS_CONFIG = {
    "openai": {
        "path": get_data_path(
            "openai_platform", "output", "openai_platform_latest.json"
        ),
        "name": "OpenAI Platform",
        "icon": "🤖",
        "category": "Foundation Models",
        "description": "OpenAI API status, model updates, and platform monitoring",
    },
    "anthropic": {
        "path": get_data_path(
            "anthropic_platform", "output", "anthropic_platform_latest.json"
        ),
        "name": "Anthropic Claude",
        "icon": "🔮",
        "category": "Foundation Models",
        "description": "Claude API status, model capabilities, and platform updates",
    },
    "huggingface": {
        "path": get_data_path(
            "huggingface_platform", "output", "huggingface_latest.json"
        ),
        "name": "HuggingFace Hub",
        "icon": "🤗",
        "category": "Model Repository",
        "description": "Trending models, datasets, and spaces on HuggingFace",
    },
    "google_gemini": {
        "path": get_data_path("ai_models", "google", "google_updates_latest.json"),
        "name": "Google Gemini",
        "icon": "✨",
        "category": "Foundation Models",
        "description": "Gemini API status, model updates, and capabilities",
    },
    "github_copilot": {
        "path": get_data_path("github_copilot", "output", "github_copilot_latest.json"),
        "name": "GitHub Copilot",
        "icon": "👨‍💻",
        "category": "Coding Assistant",
        "description": "Copilot features, updates, and usage analytics",
    },
    "ai_models": {
        "path": get_data_path("ai_models", "ai_models_latest.json"),
        "name": "AI Model Monitoring",
        "icon": "📊",
        "category": "Analytics",
        "description": "Cross-platform model performance and benchmarks",
    },
    "ai_platform_monitoring": {
        "path": get_data_path(
            "ai_platform_monitoring", "output", "ai_platform_intelligence_latest.json"
        ),
        "name": "Platform Health",
        "icon": "🔍",
        "category": "Monitoring",
        "description": "Overall AI platform health and status monitoring",
    },
}


def load_ai_platform_data(file_path):
    """Load and parse AI platform data from JSON file"""
    try:
        if not file_exists(file_path):
            logger.warning(f"AI platform data file not found: {file_path}")
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            processed_data = []
            for item in data:
                processed_item = process_ai_item(item)
                if processed_item:
                    processed_data.append(processed_item)
            return processed_data
        if isinstance(data, dict):
            processed_item = process_ai_item(data)
            return [processed_item] if processed_item else []
        return []
    except Exception as e:
        logger.error(f"Error loading AI platform data from {file_path}: {e}")
        return []


def process_ai_item(item):
    """Process individual AI platform item with standardized fields"""
    try:
        title = item.get("title", item.get("name", item.get("model_name", "Unknown")))
        description = item.get(
            "description",
            item.get("summary", item.get("details", "No description available")),
        )
        timestamp = None
        for time_field in [
            "timestamp",
            "created_at",
            "updated_at",
            "last_update",
            "date",
        ]:
            if time_field in item:
                timestamp = parse_date_universal(item[time_field])
                break
        metadata = {}
        if "version" in item:
            metadata["version"] = item["version"]
        if "status" in item:
            metadata["status"] = item["status"]
        if "provider" in item:
            metadata["provider"] = item["provider"]
        if "category" in item:
            metadata["category"] = item["category"]
        if "downloads" in item:
            metadata["downloads"] = item["downloads"]
        if "stars" in item:
            metadata["stars"] = item["stars"]
        return {
            "title": title,
            "description": (
                description[:200] + "..." if len(description) > 200 else description
            ),
            "timestamp": timestamp,
            "url": item.get("url", item.get("link", "#")),
            "platform": item.get("platform", "Unknown"),
            "metadata": metadata,
            "raw_data": item,
        }
    except Exception as e:
        logger.error(f"Error processing AI platform item: {e}")
        return None


# Load all AI platform data
AI_PLATFORMS_DATA = {}
for platform_id, config in AI_PLATFORMS_CONFIG.items():
    data = load_ai_platform_data(config["path"])
    AI_PLATFORMS_DATA[platform_id] = data
    logger.info(f"Loaded {len(data)} items for {config['name']}")


def create_platform_card(platform_id, config, data):
    """Create an enhanced card for each AI platform"""
    item_count = len(data)
    last_update = "Never"
    if data:
        timestamps = [item["timestamp"] for item in data if item["timestamp"]]
        if timestamps:
            last_update = max(timestamps).strftime("%Y-%m-%d %H:%M")
    status_color = "success" if item_count > 0 else "secondary"
    status_text = f"{item_count} items" if item_count > 0 else "No data"
    card = dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5(
                        [html.Span(config["icon"], className="me-2"), config["name"]],
                        className="mb-0",
                    ),
                    dbc.Badge(status_text, color=status_color, className="float-end"),
                ]
            ),
            dbc.CardBody(
                [
                    html.P(
                        config["description"], className="card-text text-muted small"
                    ),
                    html.Div(
                        [
                            html.Strong("Category: "),
                            dbc.Badge(
                                config["category"], color="info", className="me-2"
                            ),
                        ],
                        className="mb-2",
                    ),
                    html.Div(
                        [
                            html.Strong("Last Update: "),
                            html.Span(last_update, className="text-muted small"),
                        ]
                    ),
                    html.Hr(),
                    dbc.Button(
                        f"View {config['name']} Data",
                        id=f"btn-{platform_id}",
                        color="outline-primary",
                        size="sm",
                        className="w-100",
                    ),
                ]
            ),
        ],
        className="mb-4 h-100",
    )
    return card


def create_data_table(platform_id, data):
    """Create a data table for platform data"""
    if not data:
        return dbc.Alert(
            "No data available for this platform.",
            color="info",
            className="text-center",
        )
    df_data = []
    for item in data:
        row = {
            "Title": item["title"],
            "Description": item["description"],
            "Platform": item["platform"],
            "Timestamp": (
                item["timestamp"].strftime("%Y-%m-%d %H:%M")
                if item["timestamp"]
                else "N/A"
            ),
            "URL": item["url"],
        }
        for key, value in item["metadata"].items():
            row[key.title()] = str(value)
        df_data.append(row)
    df = pd.DataFrame(df_data)
    columns = []
    for col in df.columns:
        if col == "URL":
            columns.append(
                {"name": col, "id": col, "type": "text", "presentation": "markdown"}
            )
        else:
            columns.append({"name": col, "id": col, "type": "text"})
    if "URL" in df.columns:
        df["URL"] = df.apply(
            lambda row: f"[🔗 Link]({row['URL']})" if row["URL"] != "#" else "N/A",
            axis=1,
        )
    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=columns,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "padding": "10px",
            "fontFamily": "Poppins, sans-serif",
        },
        style_header={
            "backgroundColor": "#3C3970",
            "color": "#E2E8F0",
            "fontWeight": "bold",
        },
        style_data={
            "whiteSpace": "normal",
            "height": "auto",
            "fontSize": "0.85rem",
            "lineHeight": "1.3rem",
        },
    )


def render_ai_platforms_tab():
    """Main render function for the AI Platforms tab"""
    total_items = sum(len(data) for data in AI_PLATFORMS_DATA.values())
    active_platforms = sum(1 for data in AI_PLATFORMS_DATA.values() if len(data) > 0)
    platform_cards = []
    visible_items = [
        (pid, cfg, AI_PLATFORMS_DATA.get(pid, []))
        for pid, cfg in AI_PLATFORMS_CONFIG.items()
        if AI_PLATFORMS_DATA.get(pid)
    ]
    if not visible_items:
        platform_cards = [dbc.Alert("No AI platform data available yet.", color="info")]
    else:
        for i, (platform_id, config, data) in enumerate(visible_items):
            card = create_platform_card(platform_id, config, data)
            if i % 3 == 0:
                platform_cards.append(dbc.Row([dbc.Col(card, md=4)], className="mb-3"))
            else:
                platform_cards[-1].children.append(dbc.Col(card, md=4))
    return html.Div(
        [
            dbc.Row(
                dbc.Col(
                    [
                        html.H3(
                            [
                                html.I(className="fas fa-robot me-2"),
                                "AI Platforms Monitoring",
                            ],
                            className="text-primary mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    total_items,
                                                    className="text-primary mb-0",
                                                ),
                                                html.P(
                                                    "Total Items",
                                                    className="text-muted small mb-0",
                                                ),
                                            ]
                                        )
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    active_platforms,
                                                    className="text-success mb-0",
                                                ),
                                                html.P(
                                                    "Active Platforms",
                                                    className="text-muted small mb-0",
                                                ),
                                            ]
                                        )
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    len(AI_PLATFORMS_CONFIG),
                                                    className="text-info mb-0",
                                                ),
                                                html.P(
                                                    "Monitored Platforms",
                                                    className="text-muted small mb-0",
                                                ),
                                            ]
                                        )
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "Live",
                                                    className="text-warning mb-0",
                                                ),
                                                html.P(
                                                    "Status",
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
                    ]
                )
            ),
            html.Div(platform_cards),
            html.Div(id="ai-platforms-data-display"),
            dcc.Store(id="selected-ai-platform"),
        ]
    )


def register_ai_platforms_callbacks(app):
    """Register callbacks for the AI Platforms tab"""
    # Single callback to handle all platform buttons to avoid conflicts
    @callback(
        Output("ai-platforms-data-display", "children"),
        Output("selected-ai-platform", "data"),
        [Input(f"btn-{platform_id}", "n_clicks") for platform_id in AI_PLATFORMS_CONFIG.keys()],
        prevent_initial_call=True,
    )
    def display_platform_data(*n_clicks_list):
        """Handle clicks from any platform button"""
        import dash
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return html.Div(), None
        
        # Find which button was clicked
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        platform_id = button_id.replace('btn-', '')
        
        if platform_id in AI_PLATFORMS_CONFIG:
            config = AI_PLATFORMS_CONFIG[platform_id]
            data = AI_PLATFORMS_DATA[platform_id]
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
                        create_data_table(platform_id, data),
                    ]
                ),
                platform_id,
            )
        
        return html.Div(), None


if __name__ == "__main__":
    print("AI Platforms Tab - Data Summary:")
    for platform_id, config in AI_PLATFORMS_CONFIG.items():
        data_count = len(AI_PLATFORMS_DATA[platform_id])
        print(f"  {config['name']}: {data_count} items")
    total = sum(len(data) for data in AI_PLATFORMS_DATA.values())
    print(f"  Total: {total} items across {len(AI_PLATFORMS_CONFIG)} platforms")
