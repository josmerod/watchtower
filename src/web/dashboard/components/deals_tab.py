"""Comprehensive Deals Dashboard Tab
Aggregates all deal-related ETLs including bargain deals, software, books, travel, etc.
"""

import json
import logging
from collections import Counter

import dash_bootstrap_components as dbc
import plotly.express as px
from dash import Input, Output, State, dcc, html, dash

# Import shared utilities
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal
from src.web.dashboard.search_utils import (
    create_search_input,
    filter_content,
    get_common_searchable_fields,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Comprehensive deals configuration
DEALS_SOURCES_CONFIG = {
    "bargain_deals": {
        "path": get_data_path("deals", "bargain_deals.json"),
        "name": "Bargain Deals",
        "icon": "💰",
        "category": "General",
        "color": "success",
        "description": "Best bargain deals across multiple platforms and categories",
    },
    "software_deals": {
        "path": get_data_path("deals", "software_deals.json"),
        "name": "Software Deals",
        "icon": "💻",
        "category": "Technology",
        "color": "primary",
        "description": "Software licenses, apps, and development tools on sale",
    },
    "book_deals": {
        "path": get_data_path("deals", "book_deals.json"),
        "name": "Book Deals",
        "icon": "📚",
        "category": "Education",
        "color": "info",
        "description": "eBooks, audiobooks, and physical book deals",
    },
    "educational_deals": {
        "path": get_data_path("deals", "educational_deals.json"),
        "name": "Educational Deals",
        "icon": "🎓",
        "category": "Education",
        "color": "warning",
        "description": "Online courses, training programs, and educational resources",
    },
    "travel_deals": {
        "path": get_data_path("deals", "travel_deals.json"),
        "name": "Travel Deals",
        "icon": "✈️",
        "category": "Travel",
        "color": "info",
        "description": "Flight deals, hotel discounts, and travel packages",
    },
    "crypto_finance_deals": {
        "path": get_data_path("deals", "crypto_finance_deals.json"),
        "name": "Crypto & Finance",
        "icon": "₿",
        "category": "Finance",
        "color": "warning",
        "description": "Cryptocurrency tools, trading platforms, and finance apps",
    },
    "fashion_retail_deals": {
        "path": get_data_path("deals", "fashion_retail_deals.json"),
        "name": "Fashion & Retail",
        "icon": "👕",
        "category": "Retail",
        "color": "danger",
        "description": "Clothing, accessories, and retail merchandise deals",
    },
    "health_fitness_deals": {
        "path": get_data_path("deals", "health_fitness_deals.json"),
        "name": "Health & Fitness",
        "icon": "💪",
        "category": "Health",
        "color": "success",
        "description": "Health supplements, fitness equipment, and wellness products",
    },
    "music_deals": {
        "path": get_data_path("deals", "music_deals.json"),
        "name": "Music Deals",
        "icon": "🎵",
        "category": "Entertainment",
        "color": "primary",
        "description": "Music software, instruments, and audio equipment deals",
    },
    "bundle_deals": {
        "path": get_data_path("deals", "bundle_deals.json"),
        "name": "Bundle Deals",
        "icon": "📦",
        "category": "Bundles",
        "color": "secondary",
        "description": "Software bundles, game bundles, and multi-item deal packages",
    },
    "hardware_tech_deals": {
        "path": get_data_path("deals", "hardware_tech_deals.json"),
        "name": "Hardware & Tech",
        "icon": "🔧",
        "category": "Technology",
        "color": "info",
        "description": "Electronics, computers, gadgets, and tech accessories",
    },
    "itad_deals": {
        "path": get_data_path("deals", "isthereanydeal_deals_latest.json"),
        "name": "ITAD Deals",
        "icon": "🎮",
        "category": "Games",
        "color": "primary",
        "description": "Latest game deals from IsThereAnyDeal (RSS)",
    },
    "itad_bundles": {
        "path": get_data_path("deals", "isthereanydeal_bundles_latest.json"),
        "name": "ITAD Bundles",
        "icon": "🧰",
        "category": "Games",
        "color": "secondary",
        "description": "Game bundles from IsThereAnyDeal (RSS)",
    },
    "itad_giveaways": {
        "path": get_data_path("deals", "isthereanydeal_giveaways_latest.json"),
        "name": "ITAD Giveaways",
        "icon": "🎁",
        "category": "Games",
        "color": "success",
        "description": "Game giveaways from IsThereAnyDeal (RSS)",
    },
    # New community-driven feeds
    "slickdeals": {
        "path": get_data_path("deals", "slickdeals_latest.json"),
        "name": "Slickdeals",
        "icon": "🔥",
        "category": "Community Deals",
        "color": "danger",
        "description": "Community-validated hot deals across categories",
    },
    "woot": {
        "path": get_data_path("deals", "woot_latest.json"),
        "name": "Woot!",
        "icon": "⚡",
        "category": "Daily Deals",
        "color": "warning",
        "description": "Amazon-owned daily deals with limited quantities",
    },
}


def load_deals_data(file_path):
    """Load and parse deals data from JSON file"""
    try:
        if not file_exists(file_path):
            logger.warning(f"Deals data file not found: {file_path}")
            return []

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            processed_data = []
            for deal in data:
                processed_deal = process_deal_item(deal)
                if processed_deal:
                    processed_data.append(processed_deal)
            return processed_data

        return []
    except Exception as e:
        logger.error(f"Error loading deals data from {file_path}: {e}")
        return []


def process_deal_item(deal):
    """Process individual deal item with standardized fields"""
    try:
        # Extract common fields
        title = deal.get(
            "title", deal.get("name", deal.get("product_name", "Unknown Deal"))
        )
        description = deal.get(
            "description", deal.get("summary", "No description available")
        )

        # Price information
        original_price = deal.get("original_price", deal.get("regular_price", 0))
        current_price = deal.get(
            "current_price", deal.get("sale_price", deal.get("price", 0))
        )
        # Fallback for feeds that provide structured price info
        price_struct = deal.get("price_mentioned") or deal.get("price_info")
        if isinstance(price_struct, dict):
            if not original_price:
                if "original_price" in price_struct and price_struct.get("original_price"):
                    original_price = price_struct.get("original_price")
                elif isinstance(price_struct.get("prices"), list) and price_struct["prices"]:
                    try:
                        original_price = max(float(p) for p in price_struct["prices"])
                    except Exception:
                        pass
            if not current_price:
                if "sale_price" in price_struct and price_struct.get("sale_price"):
                    current_price = price_struct.get("sale_price")
                elif isinstance(price_struct.get("prices"), list) and price_struct["prices"]:
                    try:
                        current_price = min(float(p) for p in price_struct["prices"])
                    except Exception:
                        pass

        # Calculate savings if not provided
        discount_percentage = deal.get("discount_percentage", 0)
        # Fallback if discount is a structure with percentage/amount
        if isinstance(discount_percentage, dict):
            discount_percentage = discount_percentage.get("percentage", 0)
        savings = deal.get("savings", 0)

        if original_price and current_price and original_price > current_price:
            if not discount_percentage:
                discount_percentage = (
                    (original_price - current_price) / original_price
                ) * 100
            if not savings:
                savings = original_price - current_price

        # Deal quality metrics
        deal_rating = deal.get("deal_rating", deal.get("rating", 0))
        bargain_score = deal.get("bargain_score", deal.get("score", 0))

        # Urgency and timing
        urgency = deal.get("urgency", deal.get("deal_urgency", "low"))
        expires_at = None
        if "expires_at" in deal or "expiry_date" in deal:
            expires_at = parse_date_universal(
                deal.get("expires_at", deal.get("expiry_date"))
            )

        # Platform and store info
        platform = deal.get("platform", deal.get("source", "Unknown"))
        store_name = deal.get("store_name", deal.get("store", deal.get("retailer")))
        if not store_name:
            stores = deal.get("store_mentioned")
            if isinstance(stores, list) and stores:
                store_name = ", ".join(stores)
            else:
                store_name = platform

        # Categories and tags
        category = deal.get("category", "general")
        tags = deal.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        return {
            "title": title,
            "description": (
                description[:150] + "..." if len(description) > 150 else description
            ),
            "original_price": float(original_price) if original_price else 0,
            "current_price": float(current_price) if current_price else 0,
            "savings": float(savings) if savings else 0,
            "discount_percentage": (
                float(discount_percentage) if discount_percentage else 0
            ),
            "deal_rating": float(deal_rating) if deal_rating else 0,
            "bargain_score": float(bargain_score) if bargain_score else 0,
            "urgency": urgency,
            "platform": platform,
            "store_name": store_name,
            "category": category,
            "tags": tags,
            "url": deal.get("url", deal.get("link", "#")),
            "expires_at": expires_at,
            "raw_data": deal,
        }
    except Exception as e:
        logger.error(f"Error processing deal item: {e}")
        return None


# Load all deals data
DEALS_DATA = {}
for source_id, config in DEALS_SOURCES_CONFIG.items():
    data = load_deals_data(config["path"])
    DEALS_DATA[source_id] = data
    logger.info(f"Loaded {len(data)} deals for {config['name']}")

# Combine all deals for analytics
ALL_DEALS = []
for source_id, data in DEALS_DATA.items():
    for deal in data:
        deal["source_category"] = DEALS_SOURCES_CONFIG[source_id]["category"]
        deal["source_name"] = DEALS_SOURCES_CONFIG[source_id]["name"]
        ALL_DEALS.append(deal)


def create_deals_distribution_chart():
    """Create a bar chart showing distribution of deals by category"""
    if not ALL_DEALS:
        return html.Div("No deals data available for visualization")

    # Count deals by source category
    category_counts = Counter()
    for deal in ALL_DEALS:
        category_counts[deal["source_category"]] += 1

    categories = list(category_counts.keys())
    counts = list(category_counts.values())

    fig = px.bar(
        x=categories,
        y=counts,
        title="Deals Distribution by Category",
        labels={"x": "Category", "y": "Number of Deals"},
        color=counts,
        color_continuous_scale="Viridis",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CDD6F4",
        title_font_color="#A37FFF",
    )

    return dcc.Graph(figure=fig)


def create_savings_distribution_chart():
    """Create a histogram showing distribution of savings amounts"""
    if not ALL_DEALS:
        return html.Div("No deals data available")

    # Filter deals with valid savings data
    deals_with_savings = [deal for deal in ALL_DEALS if deal["discount_percentage"] > 0]

    if not deals_with_savings:
        return html.Div("No savings data available")

    discount_percentages = [deal["discount_percentage"] for deal in deals_with_savings]

    fig = px.histogram(
        x=discount_percentages,
        nbins=20,
        title="Distribution of Discount Percentages",
        labels={"x": "Discount Percentage (%)", "y": "Number of Deals"},
        color_discrete_sequence=["#A37FFF"],
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CDD6F4",
        title_font_color="#A37FFF",
    )

    return dcc.Graph(figure=fig)


# Note: Removed old callback-based functions since we're using static tabs now


def render_deals_tab():
    """Main render function for the Deals dashboard tab - simplified without callbacks"""
    total_deals = len(ALL_DEALS)
    total_categories = len(set(deal["source_category"] for deal in ALL_DEALS))
    active_sources = sum(1 for data in DEALS_DATA.values() if len(data) > 0)

    # Calculate total potential savings
    total_savings = sum(deal["savings"] for deal in ALL_DEALS if deal["savings"] > 0)

    return html.Div(
        [
            # Header with statistics
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-tags me-2"),
                                    "Comprehensive Deals Dashboard",
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
                                                                total_deals,
                                                                className="text-primary mb-0",
                                                            ),
                                                            html.P(
                                                                "Total Deals",
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
                                                                f"${total_savings:.0f}",
                                                                className="text-success mb-0",
                                                            ),
                                                            html.P(
                                                                "Total Savings",
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
                                                                className="text-info mb-0",
                                                            ),
                                                            html.P(
                                                                "Deal Categories",
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
                                                                active_sources,
                                                                className="text-warning mb-0",
                                                            ),
                                                            html.P(
                                                                "Active Sources",
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
                                    dbc.CardHeader(
                                        html.H5("Deals by Category", className="mb-0")
                                    ),
                                    dbc.CardBody([create_deals_distribution_chart()]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            "Discount Distribution", className="mb-0"
                                        )
                                    ),
                                    dbc.CardBody([create_savings_distribution_chart()]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            # Deals categories with direct content (no callbacks)
            html.H4("Deal Categories", className="text-primary mb-3"),
            dbc.Row(create_deals_tabs_content(), className="mb-4"),
        ]
    )


def create_deals_tabs_content():
    """Create tabbed content for all deal categories (similar to news tab)"""
    tab_definitions = [
        {"label": "🎮 Bundle Deals", "keys": "bundle_deals", "id": "bundle"},
        {"label": "🎵 Music Deals", "keys": "music_deals", "id": "music"},
        {"label": "🛒 Bargain Hunter", "keys": "bargain_deals", "id": "bargain"},
        {"label": "📚 Educational", "keys": "educational_deals", "id": "educational"},
        {"label": "📖 Books", "keys": "book_deals", "id": "books"},
        {"label": "💻 Software", "keys": "software_deals", "id": "software"},
        {"label": "✈️ Travel", "keys": "travel_deals", "id": "travel"},
        {"label": "💰 Crypto & Finance", "keys": "crypto_finance_deals", "id": "crypto"},
        {"label": "👗 Fashion & Retail", "keys": "fashion_retail_deals", "id": "fashion"},
        {"label": "🏃 Health & Fitness", "keys": "health_fitness_deals", "id": "health"},
        {"label": "🔧 Hardware & Tech", "keys": "hardware_tech_deals", "id": "hardware"},
    ]

    tabs_children = []
    for tab_def in tab_definitions:
        tab_id = f"deals-tab-{tab_def['id']}"
        content = create_deals_category_tab_content(tab_def["keys"])
        tabs_children.append(
            dbc.Tab(
                label=tab_def["label"],
                tab_id=tab_id,
                children=content,
            )
        )

    return dbc.Tabs(
        id="deals-category-tabs",
        children=tabs_children,
        active_tab="deals-tab-bundle",
    )


def create_deals_category_tab_content(category_key):
    """Create content for a specific deal category with search functionality"""
    deals = DEALS_DATA.get(category_key, [])
    tab_search_id = f"deals-search-{category_key}"

    if not deals:
        return dbc.Alert(
            "No deals available for this category.", color="info"
        )

    # Sort deals by discount percentage (highest first)
    sorted_deals = sorted(deals, key=lambda x: x["discount_percentage"], reverse=True)

    # Store deals data for search filtering
    deals_data = html.Div(
        sorted_deals[:100],  # Store more deals for search
        id=f"{tab_search_id}-data",
        style={"display": "none"}
    )

    # Create initial table
    table = create_deals_table(sorted_deals[:50])

    return html.Div([
        # Search input
        create_search_input(
            input_id=tab_search_id,
            placeholder=f"Search {DEALS_SOURCES_CONFIG.get(category_key, {}).get('name', 'deals')}...",
            clear_button=True
        ),

        # Hidden data storage for search filtering
        deals_data,

        # Container for filtered results
        html.Div(
            table,
            id=f"{tab_search_id}-results",
            style={"maxHeight": "600px", "overflowY": "auto"}
        ),
    ])


def create_deals_table(deals):
    """Create a deals table from a list of deals"""
    # Create table header
    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Platform"),
                    html.Th("Original Price"),
                    html.Th("Current Price"),
                    html.Th("Savings"),
                    html.Th("Discount"),
                    html.Th("Rating"),
                ]
            )
        )
    ]

    table_body_rows = []
    for deal in deals:
        savings_display = f"${deal['savings']:.2f}" if deal["savings"] > 0 else "N/A"
        discount_display = f"{deal['discount_percentage']:.1f}%" if deal["discount_percentage"] > 0 else "N/A"
        rating_display = f"{deal['deal_rating']:.1f}" if deal["deal_rating"] > 0 else "N/A"

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.A(
                            deal["title"],
                            href=deal["url"],
                            target="_blank",
                            className="text-decoration-none",
                        )
                    ),
                    html.Td(deal["platform"]),
                    html.Td(f"${deal['original_price']:.2f}" if deal["original_price"] > 0 else "N/A"),
                    html.Td(f"${deal['current_price']:.2f}" if deal["current_price"] > 0 else "Free"),
                    html.Td(savings_display),
                    html.Td(discount_display),
                    html.Td(rating_display),
                ]
            )
        )

    table_body = [html.Tbody(table_body_rows)]

    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mt-3",
    )


def register_deals_search_callbacks(app):
    """Register search callbacks for all deals tabs."""
    # Get all deal category keys
    deal_categories = [
        "bundle_deals", "music_deals", "bargain_deals", "educational_deals",
        "book_deals", "software_deals", "travel_deals", "crypto_finance_deals",
        "fashion_retail_deals", "health_fitness_deals", "hardware_tech_deals"
    ]

    for category_key in deal_categories:
        search_id = f"deals-search-{category_key}"

        @app.callback(
            Output(f"{search_id}-results", "children"),
            Input(search_id, "value"),
            State(f"{search_id}-data", "children"),
            prevent_initial_call=True
        )
        def update_deals_search(search_term, deals_data, current_search_id=search_id):
            """Update deals display based on search term."""
            try:
                # Convert deals data back to list if needed
                if deals_data is None:
                    return html.Div("No data available")

                # Get searchable fields for deals content
                searchable_fields = get_common_searchable_fields('deals')

                # Filter deals based on search term
                filtered_deals = filter_content(search_term, deals_data, searchable_fields)

                if not filtered_deals:
                    return dbc.Alert(
                        f"No deals found matching '{search_term}'",
                        color="info"
                    )

                # Create table for filtered results (with highlighted terms)
                table = create_deals_table_with_highlighting(filtered_deals[:50])

                return html.Div([
                    dbc.Alert(
                        f"🏷️ Found {len(filtered_deals)} deals matching '{search_term}'",
                        color="success",
                        className="mb-3",
                    ),
                    html.Div(
                        table,
                        style={"maxHeight": "600px", "overflowY": "auto"}
                    )
                ])

            except Exception as e:
                logger.error(f"Error in deals search callback for {current_search_id}: {e}")
                return dbc.Alert(
                    f"Error searching deals: {e}",
                    color="danger"
                )

        # Clear search callback
        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(f"{search_id}-clear", "n_clicks"),
            prevent_initial_call=True
        )
        def clear_deals_search(n_clicks):
            """Clear search input."""
            if n_clicks:
                return ""
            return dash.no_update


def create_deals_table_with_highlighting(deals):
    """Create a deals table with highlighting from search results"""
    # Create table header
    table_header = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Title"),
                    html.Th("Platform"),
                    html.Th("Original Price"),
                    html.Th("Current Price"),
                    html.Th("Savings"),
                    html.Th("Discount"),
                    html.Th("Rating"),
                ]
            )
        )
    ]

    table_body_rows = []
    for deal in deals:
        savings_display = f"${deal['savings']:.2f}" if deal["savings"] > 0 else "N/A"
        discount_display = f"{deal['discount_percentage']:.1f}%" if deal["discount_percentage"] > 0 else "N/A"
        rating_display = f"{deal['deal_rating']:.1f}" if deal["deal_rating"] > 0 else "N/A"

        table_body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.A(
                            html.Div(deal["title"], dangerously_allow_html=True),
                            href=deal["url"],
                            target="_blank",
                            className="text-decoration-none",
                        )
                    ),
                    html.Td(deal["platform"]),
                    html.Td(f"${deal['original_price']:.2f}" if deal["original_price"] > 0 else "N/A"),
                    html.Td(f"${deal['current_price']:.2f}" if deal["current_price"] > 0 else "Free"),
                    html.Td(savings_display),
                    html.Td(discount_display),
                    html.Td(rating_display),
                ]
            )
        )

    table_body = [html.Tbody(table_body_rows)]

    return dbc.Table(
        table_header + table_body,
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        color="dark",
        className="table-responsive mt-3",
    )


if __name__ == "__main__":
    print("Deals Dashboard Tab - Data Summary:")
    for source_id, config in DEALS_SOURCES_CONFIG.items():
        deal_count = len(DEALS_DATA[source_id])
        print(f"  {config['name']}: {deal_count} deals")

    total = len(ALL_DEALS)
    categories = len(set(deal["source_category"] for deal in ALL_DEALS))
    total_savings = sum(deal["savings"] for deal in ALL_DEALS if deal["savings"] > 0)
    print(
        f"  Total: {total} deals across {categories} categories, ${total_savings:.0f} in potential savings"
    )

    # Test the new static tab system
    try:
        tabs_content = create_deals_tabs_content()
        print("Static tabs system created successfully")
    except Exception as e:
        print(f"Error creating static tabs: {e}")
