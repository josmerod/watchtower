from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# --- Data Loading ---
# Import centralized configuration
from src.services.data_loader import TRAVEL_SOURCES_CONFIG

# Import shared utilities
from src.web.dashboard.utils import parse_date_universal


# NEW: Repository-based loading (SOLID Pattern)
class TravelRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for travel data."""

    def __init__(self, data_path: str):
        """Initialize travel repository.

        Args:
            data_path: Path to travel data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform JSON data into list of travel items.

        Args:
            raw_data: Raw JSON data

        Returns:
            List of travel item dictionaries
        """
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            # Try common keys
            for key in ["items", "products", "deals", "data", "results"]:
                if key in raw_data and isinstance(raw_data[key], list):
                    return raw_data[key]
            # If single item
            if any(k in raw_data for k in ["title", "name", "url"]):
                return [raw_data]
            return []
        else:
            return []


# Create singleton instances for each source (only if configured)
gumroad_repo = TravelRepository(TRAVEL_SOURCES_CONFIG["gumroad"]["path"]) if "gumroad" in TRAVEL_SOURCES_CONFIG else None
viajeros_piratas_repo = TravelRepository(TRAVEL_SOURCES_CONFIG["viajeros_piratas"]["path"]) if "viajeros_piratas" in TRAVEL_SOURCES_CONFIG else None


def load_travel_data(source_key):
    """Load travel data using repository pattern (NEW)."""
    try:
        # Select appropriate repository based on source key
        if source_key == "gumroad":
            data = gumroad_repo.get()
        elif source_key == "viajeros_piratas":
            data = viajeros_piratas_repo.get()
        else:
            print(f"Unknown travel source: {source_key}")
            return []

        return data if data else []
    except Exception as e:
        print(f"Error loading {source_key} data: {e}")
        return []


def create_travel_cards():
    """Create summary cards for travel data."""
    cards = []

    for source_key, config in TRAVEL_SOURCES_CONFIG.items():
        data = load_travel_data(source_key)
        count = len(data)

        # Calculate latest update
        latest_date = "No data"
        if data:
            dates = []
            for item in data:
                for date_field in ["date", "timestamp", "created_at", "published_date"]:
                    if date_field in item:
                        try:
                            dt = parse_date_universal(item[date_field])
                            if dt:
                                dates.append(dt)
                        except:
                            pass

            if dates:
                latest_date = max(dates).strftime("%Y-%m-%d")

        color = "success" if count > 0 else "secondary"

        card = dbc.Card(
            dbc.CardBody(
                [
                    html.H4(f"{count:,}", className=f"card-title text-{color}"),
                    html.P(config["name"], className="card-text"),
                    html.Small(f"Last update: {latest_date}", className="text-muted"),
                ]
            ),
            color=color,
            outline=True,
            className="mb-3",
        )
        cards.append(card)

    return cards


def create_travel_table(source_key):
    """Create travel data table for a specific source."""
    data = load_travel_data(source_key)
    config = TRAVEL_SOURCES_CONFIG.get(source_key, {})

    if not data:
        return html.Div(
            [
                html.P(
                    f"No {config.get('name', source_key)} data available.",
                    className="text-muted text-center p-4",
                )
            ]
        )

    # Limit to 50 most recent items
    recent_data = data[:50]

    table_rows = []
    for item in recent_data:
        # Extract common fields
        title = item.get("title", item.get("name", item.get("product_name", "Untitled")))

        url = item.get("url", item.get("link", "#"))

        # Price handling
        price = item.get("price", item.get("cost", item.get("value", "N/A")))
        if isinstance(price, (int, float)):
            price = f"${price:.2f}"
        elif price and str(price).replace(".", "").replace("$", "").replace(",", "").isdigit():
            price = f"${float(str(price).replace('$', '').replace(',', '')):.2f}"

        # Date handling
        date_str = "Unknown"
        for date_field in ["date", "timestamp", "created_at", "published_date"]:
            if date_field in item:
                try:
                    dt = parse_date_universal(item[date_field])
                    if dt:
                        date_str = dt.strftime("%Y-%m-%d")
                        break
                except:
                    pass

        # Description
        description = item.get("description", item.get("summary", ""))[:200]
        if len(item.get("description", item.get("summary", ""))) > 200:
            description += "..."

        # Category/Tags
        category = item.get("category", item.get("type", item.get("tag", "General")))

        row = html.Tr(
            [
                html.Td(
                    [
                        html.A(
                            title,
                            href=url,
                            target="_blank",
                            className="text-decoration-none",
                        ),
                    ]
                ),
                html.Td(price, className="text-success fw-bold"),
                html.Td(category, className="small"),
                html.Td(date_str, className="text-muted small"),
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
                            html.Th("Title/Product", style={"width": "25%"}),
                            html.Th("Price", style={"width": "10%"}),
                            html.Th("Category", style={"width": "15%"}),
                            html.Th("Date", style={"width": "10%"}),
                            html.Th("Description", style={"width": "40%"}),
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


def travel_tab():
    """Main travel/deals tab function."""
    return dbc.Container(
        [
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("✈️ Travel & Digital Products", className="mb-3"),
                            html.P(
                                "Travel deals, digital products, and marketplace intelligence",
                                className="text-muted mb-4",
                            ),
                        ]
                    )
                ]
            ),
            # Summary Cards
            dbc.Row(
                [dbc.Col(card, md=6) for card in create_travel_cards()],
                className="mb-4",
            ),
            # Data Sections
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("🛍️ Gumroad Products"),
                                    dbc.CardBody([create_travel_table("gumroad")]),
                                ]
                            )
                        ],
                        md=12,
                        className="mb-4",
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader("🏴‍☠️ Viajeros Piratas - Travel Deals"),
                                    dbc.CardBody([create_travel_table("viajeros_piratas")]),
                                ]
                            )
                        ],
                        md=12,
                    )
                ]
            ),
        ],
        fluid=True,
    )
