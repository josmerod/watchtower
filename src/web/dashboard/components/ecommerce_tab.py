"""E-commerce Dashboard Tab
Gumroad products, travel deals, and commercial opportunities
"""

import json
import logging
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dash_table, dcc, html

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import centralized configuration
from src.services.data_loader import ECOMMERCE_SOURCES_CONFIG

# NEW: Repository-based loading (SOLID Pattern)
class EcommerceRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for e-commerce data."""

    def __init__(self, data_path: str):
        """Initialize e-commerce repository.

        Args:
            data_path: Path to e-commerce data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of e-commerce items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of e-commerce item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

# Create singleton instances for each source (only if configured)
gumroad_repo = EcommerceRepository(ECOMMERCE_SOURCES_CONFIG["gumroad_scraper"]["path"]) if "gumroad_scraper" in ECOMMERCE_SOURCES_CONFIG else None
viajeros_piratas_repo = EcommerceRepository(ECOMMERCE_SOURCES_CONFIG["viajeros_piratas"]["path"]) if "viajeros_piratas" in ECOMMERCE_SOURCES_CONFIG else None


# OLD: Direct file loading (commented out for migration - SAFE TO ROLLBACK)
# def load_ecommerce_data(file_path):
#     """Load and parse e-commerce data from JSON file"""
#     try:
#         if not file_exists(file_path):
#             logger.warning(f"E-commerce data file not found: {file_path}")
#             return []
#
#         with open(file_path, encoding="utf-8") as f:
#             data = json.load(f)
#
#         if isinstance(data, list):
#             return [process_ecommerce_item(item) for item in data if process_ecommerce_item(item)]
#         elif isinstance(data, dict):
#             processed_item = process_ecommerce_item(data)
#             return [processed_item] if processed_item else []
#
#         return []
#     except Exception as e:
#         logger.error(f"Error loading e-commerce data from {file_path}: {e}")
#         return []


def load_ecommerce_data(file_path):
    """Load and parse e-commerce data using repository pattern (NEW).

    Args:
        file_path: Path to e-commerce data file

    Returns:
        List of processed e-commerce items
    """
    try:
        # Select appropriate repository based on file path
        if "gumroad" in file_path:
            data = gumroad_repo.get()
        elif "viajeros_piratas" in file_path or "travel_deals" in file_path:
            data = viajeros_piratas_repo.get()
        else:
            logger.warning(f"Unknown e-commerce data source: {file_path}")
            return []

        if isinstance(data, list):
            return [process_ecommerce_item(item) for item in data if process_ecommerce_item(item)]
        elif isinstance(data, dict):
            processed_item = process_ecommerce_item(data)
            return [processed_item] if processed_item else []

        return []
    except Exception as e:
        logger.error(f"Error loading e-commerce data from {file_path}: {e}")
        return []


def process_ecommerce_item(item):
    """Process individual e-commerce item"""
    try:
        # Extract pricing information
        price = item.get("price", item.get("cost", 0))
        original_price = item.get("original_price", item.get("regular_price", price))

        # Calculate discount if applicable
        discount = 0
        if original_price and price and original_price > price:
            discount = ((original_price - price) / original_price) * 100

        return {
            "title": item.get("title", item.get("name", item.get("product_name", "Unknown Product"))),
            "description": item.get("description", item.get("summary", "No description available")),
            "price": float(price) if price else 0,
            "original_price": float(original_price) if original_price else 0,
            "discount": discount,
            "category": item.get("category", item.get("type", "General")),
            "seller": item.get("seller", item.get("author", item.get("vendor", "Unknown"))),
            "rating": float(item.get("rating", 0)) if item.get("rating") else 0,
            "sales": (int(item.get("sales", item.get("purchases", 0))) if item.get("sales") or item.get("purchases") else 0),
            "url": item.get("url", item.get("link", "#")),
            "image": item.get("image", item.get("thumbnail", "")),
            "tags": item.get("tags", item.get("keywords", [])),
            "release_date": parse_date_universal(item.get("release_date", item.get("created_at", item.get("date")))),
            "raw_data": item,
        }
    except Exception as e:
        logger.error(f"Error processing e-commerce item: {e}")
        return None


# Load all e-commerce data
ECOMMERCE_DATA = {}
for source_id, config in ECOMMERCE_SOURCES_CONFIG.items():
    data = load_ecommerce_data(config["path"])
    ECOMMERCE_DATA[source_id] = data
    logger.info(f"Loaded {len(data)} items for {config['name']}")

# Combine all data
ALL_ECOMMERCE = []
for source_id, data in ECOMMERCE_DATA.items():
    for item in data:
        item["source_name"] = ECOMMERCE_SOURCES_CONFIG[source_id]["name"]
        item["source_category"] = ECOMMERCE_SOURCES_CONFIG[source_id]["category"]
        ALL_ECOMMERCE.append(item)


def create_ecommerce_summary_cards():
    """Create summary cards for each e-commerce source"""
    cards = []

    for source_id, config in ECOMMERCE_SOURCES_CONFIG.items():
        data = ECOMMERCE_DATA[source_id]
        item_count = len(data)

        # Calculate metrics
        avg_price = sum(item["price"] for item in data if item["price"] > 0) / len([item for item in data if item["price"] > 0]) if any(item["price"] > 0 for item in data) else 0
        avg_rating = sum(item["rating"] for item in data if item["rating"] > 0) / len([item for item in data if item["rating"] > 0]) if any(item["rating"] > 0 for item in data) else 0
        total_sales = sum(item["sales"] for item in data if item["sales"] > 0)

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
                            color="primary",
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
                                dbc.Badge(config["category"], color="info"),
                            ],
                            className="mb-1",
                        ),
                        html.Div(
                            [
                                html.Strong("Avg Price: "),
                                html.Span(
                                    f"${avg_price:.2f}" if avg_price > 0 else "Free",
                                    className="text-success",
                                ),
                            ],
                            className="mb-1",
                        ),
                        html.Div(
                            [
                                html.Strong("Avg Rating: "),
                                html.Span(
                                    f"{avg_rating:.1f}/5" if avg_rating > 0 else "N/A",
                                    className="text-warning",
                                ),
                            ],
                            className="mb-1",
                        ),
                        html.Div(
                            [
                                html.Strong("Total Sales: "),
                                html.Span(
                                    f"{total_sales:,}" if total_sales > 0 else "N/A",
                                    className="text-info",
                                ),
                            ],
                            className="mb-2",
                        ),
                        dbc.Button(
                            f"View {config['name']}",
                            id=f"btn-ecommerce-{source_id}",
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


def create_ecommerce_table(source_id, items):
    """Create table for e-commerce items"""
    if not items:
        return dbc.Alert("No e-commerce items available.", color="info", className="text-center")

    # Sort by rating and sales
    sorted_items = sorted(items, key=lambda x: (x["rating"], x["sales"]), reverse=True)

    df_data = []
    for item in sorted_items:
        # Format pricing
        price_str = f"${item['price']:.2f}" if item["price"] > 0 else "Free"
        if item["discount"] > 0:
            price_str += f" (-{item['discount']:.1f}%)"

        # Format tags
        tags_str = ", ".join(item["tags"][:3]) if item["tags"] else "None"
        if len(item["tags"]) > 3:
            tags_str += f" +{len(item['tags']) - 3} more"

        row = {
            "Title": (item["title"][:60] + "..." if len(item["title"]) > 60 else item["title"]),
            "Category": item["category"],
            "Seller": item["seller"],
            "Price": price_str,
            "Rating": f"{item['rating']:.1f}/5" if item["rating"] > 0 else "N/A",
            "Sales": f"{item['sales']:,}" if item["sales"] > 0 else "N/A",
            "Tags": tags_str,
            "Description": (item["description"][:100] + "..." if len(item["description"]) > 100 else item["description"]),
            "URL": item["url"],
        }
        df_data.append(row)

    df = pd.DataFrame(df_data)

    columns = [
        {"name": "Title", "id": "Title", "type": "text"},
        {"name": "Category", "id": "Category", "type": "text"},
        {"name": "Seller", "id": "Seller", "type": "text"},
        {"name": "Price", "id": "Price", "type": "text"},
        {"name": "Rating", "id": "Rating", "type": "text"},
        {"name": "Sales", "id": "Sales", "type": "text"},
        {"name": "Tags", "id": "Tags", "type": "text"},
        {"name": "Description", "id": "Description", "type": "text"},
        {"name": "Link", "id": "URL", "type": "text", "presentation": "markdown"},
    ]

    df["URL"] = df.apply(
        lambda row: f"[🛒 View Product]({row['URL']})" if row["URL"] != "#" else "N/A",
        axis=1,
    )

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=columns,
        page_size=12,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Poppins, sans-serif",
            "maxWidth": "150px",
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
            {"if": {"row_index": "odd"}, "backgroundColor": "#252343"},
            {
                "if": {"filter_query": "{Price} contains Free"},
                "backgroundColor": "#3C5A3C",
                "color": "#AEF4AE",
            },
        ],
    )


def render_ecommerce_tab():
    """Main render function for E-commerce tab"""
    total_items = len(ALL_ECOMMERCE)
    total_categories = len({item["category"] for item in ALL_ECOMMERCE})
    avg_price = sum(item["price"] for item in ALL_ECOMMERCE if item["price"] > 0) / len([item for item in ALL_ECOMMERCE if item["price"] > 0]) if any(item["price"] > 0 for item in ALL_ECOMMERCE) else 0
    free_items = len([item for item in ALL_ECOMMERCE if item["price"] == 0])

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-shopping-cart me-2"),
                                    "E-commerce Dashboard",
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
                                                                total_items,
                                                                className="text-primary mb-0",
                                                            ),
                                                            html.P(
                                                                "Total Products",
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
                                                                f"${avg_price:.2f}",
                                                                className="text-success mb-0",
                                                            ),
                                                            html.P(
                                                                "Average Price",
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
                                                                free_items,
                                                                className="text-info mb-0",
                                                            ),
                                                            html.P(
                                                                "Free Items",
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
                                                                total_categories,
                                                                className="text-warning mb-0",
                                                            ),
                                                            html.P(
                                                                "Categories",
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
            html.H4("E-commerce Sources", className="text-primary mb-3"),
            dbc.Row(create_ecommerce_summary_cards(), className="mb-4"),
            html.Div(id="ecommerce-data-display"),
            dcc.Store(id="selected-ecommerce-source"),
        ]
    )


def register_ecommerce_callbacks(app):
    """Register callbacks for E-commerce tab"""
    for source_id in ECOMMERCE_SOURCES_CONFIG:

        @callback(
            Output("ecommerce-data-display", "children"),
            Output("selected-ecommerce-source", "data"),
            Input(f"btn-ecommerce-{source_id}", "n_clicks"),
            prevent_initial_call=True,
        )
        def display_ecommerce_data(n_clicks, source_id=source_id):
            if n_clicks:
                config = ECOMMERCE_SOURCES_CONFIG[source_id]
                items = ECOMMERCE_DATA[source_id]

                return (
                    html.Div(
                        [
                            html.Hr(),
                            html.H4(
                                [
                                    html.Span(config["icon"], className="me-2"),
                                    f"{config['name']} Products",
                                ],
                                className="text-primary mb-3",
                            ),
                            create_ecommerce_table(source_id, items),
                        ]
                    ),
                    source_id,
                )

            return html.Div(), None


if __name__ == "__main__":
    print("E-commerce Tab - Data Summary:")
    for source_id, config in ECOMMERCE_SOURCES_CONFIG.items():
        item_count = len(ECOMMERCE_DATA[source_id])
        print(f"  {config['name']}: {item_count} items")

    total = len(ALL_ECOMMERCE)
    print(f"  Total: {total} e-commerce items")
