"""Entertainment Dashboard Tab
Integrates entertainment-related ETLs including cinema, meme economics, and other entertainment content
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
from dash import Input, Output, callback, dash_table, dcc, html

# Import shared utilities
from src.web.dashboard.utils import file_exists, get_data_path, parse_date_universal

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import centralized configuration
from src.services.data_loader import ENTERTAINMENT_SOURCES_CONFIG

# NEW: Repository-based loading (SOLID Pattern)
class EntertainmentRepository(BaseRepository[dict[str, Any]]):
    """Repository for entertainment data."""

    def __init__(self, data_path: str):
        """Initialize entertainment repository.

        Args:
            data_path: Path to entertainment data file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> dict[str, Any]:
        """Transform JSON data into entertainment dictionary.

        Args:
            raw_data: Raw JSON data

        Returns:
            Entertainment data dictionary
        """
        if isinstance(raw_data, dict):
            return raw_data
        elif isinstance(raw_data, list):
            return {"items": raw_data}
        else:
            return {}

# Create singleton instances for each source
cinema_ecartelera_repo = EntertainmentRepository(ENTERTAINMENT_SOURCES_CONFIG["cinema_ecartelera"]["path"])
cinema_ecartelera_improved_repo = EntertainmentRepository(ENTERTAINMENT_SOURCES_CONFIG["cinema_ecartelera_improved"]["path"])
meme_economics_repo = EntertainmentRepository(ENTERTAINMENT_SOURCES_CONFIG["meme_economics"]["path"])
trakt_movies_repo = EntertainmentRepository(ENTERTAINMENT_SOURCES_CONFIG["trakt_movies"]["path"])
trakt_shows_repo = EntertainmentRepository(ENTERTAINMENT_SOURCES_CONFIG["trakt_shows"]["path"])
spotify_browse_repo = EntertainmentRepository(ENTERTAINMENT_SOURCES_CONFIG["spotify_browse"]["path"])


def load_entertainment_data(file_path):
    """Load entertainment data using repository pattern (NEW)."""
    try:
        # Select appropriate repository based on file path
        if "cinema_showtimes" in file_path and "improved" not in file_path:
            data = cinema_ecartelera_repo.get()
        elif "cinema_improved" in file_path:
            data = cinema_ecartelera_improved_repo.get()
        elif "meme_economics" in file_path:
            data = meme_economics_repo.get()
        elif "trakt_movies" in file_path:
            data = trakt_movies_repo.get()
        elif "trakt_shows" in file_path:
            data = trakt_shows_repo.get()
        elif "spotify_browse" in file_path:
            data = spotify_browse_repo.get()
        else:
            logger.info(f"Unknown entertainment data source: {file_path}")
            return []

        # Process the loaded data
        if isinstance(data, dict):
            # Handle structured data formats
            if "movies" in data:
                # Cinema data structure
                processed_data = []
                for movie in data["movies"]:
                    processed_item = process_entertainment_item(movie)
                    if processed_item:
                        processed_data.append(processed_item)
                return processed_data
            elif "items" in data:
                # Generic items structure
                processed_data = []
                for item in data["items"]:
                    processed_item = process_entertainment_item(item)
                    if processed_item:
                        processed_data.append(processed_item)
                return processed_data
            else:
                # Single item or different structure
                processed_item = process_entertainment_item(data)
                return [processed_item] if processed_item else []
        elif isinstance(data, list):
            processed_data = []
            for item in data:
                processed_item = process_entertainment_item(item)
                if processed_item:
                    processed_data.append(processed_item)
            return processed_data
        return []
    except Exception as e:
        logger.error(f"Error loading entertainment data from {file_path}: {e}")
        return []


def process_entertainment_item(item):
    """Process individual entertainment item with standardized fields"""
    try:
        # Extract common fields
        title = item.get("title", item.get("name", item.get("movie_title", "Unknown")))
        description = item.get(
            "description",
            item.get("synopsis", item.get("summary", "No description available")),
        )

        # Handle different timestamp formats
        timestamp = None
        for time_field in [
            "timestamp",
            "date",
            "created_at",
            "showtime",
            "release_date",
        ]:
            if time_field in item:
                timestamp = parse_date_universal(item[time_field])
                break

        # Entertainment-specific fields
        genre = item.get("genre", item.get("category", "Unknown"))
        rating = item.get("rating", item.get("score", 0))
        duration = item.get("duration", item.get("runtime", "Unknown"))

        # Cinema-specific fields
        cinema_name = item.get("cinema_name", item.get("theater", ""))
        showtimes = item.get("showtimes", item.get("times", []))

        # Meme-specific fields
        trend_score = item.get("trend_score", item.get("popularity", 0))
        engagement = item.get("engagement", item.get("interactions", 0))

        # Price information (for paid content)
        price = item.get("price", item.get("ticket_price", 0))

        return {
            "title": title,
            "description": (description[:200] + "..." if len(description) > 200 else description),
            "timestamp": timestamp,
            "genre": genre,
            "rating": float(rating) if rating else 0,
            "duration": str(duration),
            "cinema_name": cinema_name,
            "showtimes": (showtimes if isinstance(showtimes, list) else [showtimes] if showtimes else []),
            "trend_score": float(trend_score) if trend_score else 0,
            "engagement": int(engagement) if engagement else 0,
            "price": float(price) if price else 0,
            "url": item.get("url", item.get("link", "#")),
            "image": item.get("image", item.get("poster", item.get("thumbnail", ""))),
            "source": item.get("source", "unknown"),
            "raw_data": item,
        }
    except Exception as e:
        logger.error(f"Error processing entertainment item: {e}")
        return None


# Load all entertainment data
ENTERTAINMENT_DATA = {}
for source_id, config in ENTERTAINMENT_SOURCES_CONFIG.items():
    data = load_entertainment_data(config["path"])
    ENTERTAINMENT_DATA[source_id] = data
    logger.info(f"Loaded {len(data)} items for {config['name']}")

# Combine all data for analytics
ALL_ENTERTAINMENT = []
for source_id, data in ENTERTAINMENT_DATA.items():
    for item in data:
        item["source_category"] = ENTERTAINMENT_SOURCES_CONFIG[source_id]["category"]
        item["source_name"] = ENTERTAINMENT_SOURCES_CONFIG[source_id]["name"]
        ALL_ENTERTAINMENT.append(item)


def create_simple_table(items, columns):
    if not items:
        return dbc.Alert("No data available.", color="info", className="mt-3")
    # Trim
    rows = []
    for it in items[:50]:
        rows.append({k: it.get(k) for k in columns})
    data_table_cols = [{"name": c.replace("_", " ").title(), "id": c, "type": "text"} for c in columns]
    return dash_table.DataTable(
        data=rows,
        columns=data_table_cols,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Poppins, sans-serif",
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
    )


def create_genre_distribution_chart():
    """Create a pie chart showing distribution of entertainment genres"""
    if not ALL_ENTERTAINMENT:
        return html.Div("No entertainment data available for visualization")

    # Count genres
    genre_counts = Counter()
    for item in ALL_ENTERTAINMENT:
        genre = item["genre"] if item["genre"] != "Unknown" else "Other"
        genre_counts[genre] += 1

    # Get top 10 genres
    top_genres = dict(genre_counts.most_common(10))

    fig = px.pie(
        values=list(top_genres.values()),
        names=list(top_genres.keys()),
        title="Entertainment Content by Genre",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CDD6F4",
        title_font_color="#A37FFF",
    )

    return dcc.Graph(figure=fig)


def create_rating_distribution_chart():
    """Create a histogram showing distribution of ratings"""
    if not ALL_ENTERTAINMENT:
        return html.Div("No entertainment data available")

    # Filter items with valid ratings
    items_with_ratings = [item for item in ALL_ENTERTAINMENT if item["rating"] > 0]

    if not items_with_ratings:
        return html.Div("No rating data available")

    ratings = [item["rating"] for item in items_with_ratings]

    fig = px.histogram(
        x=ratings,
        nbins=20,
        title="Distribution of Content Ratings",
        labels={"x": "Rating", "y": "Number of Items"},
        color_discrete_sequence=["#A37FFF"],
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#CDD6F4",
        title_font_color="#A37FFF",
    )

    return dcc.Graph(figure=fig)


def create_entertainment_summary_cards():
    """Create summary cards for each entertainment source"""
    cards = []

    for source_id, config in ENTERTAINMENT_SOURCES_CONFIG.items():
        data = ENTERTAINMENT_DATA[source_id]
        item_count = len(data)

        # Calculate average rating
        avg_rating = 0
        if data:
            valid_ratings = [item["rating"] for item in data if item["rating"] > 0]
            if valid_ratings:
                avg_rating = sum(valid_ratings) / len(valid_ratings)

        # Get latest update
        latest_update = "No data"
        if data:
            timestamps = [item["timestamp"] for item in data if item["timestamp"]]
            if timestamps:
                latest_update = max(timestamps).strftime("%Y-%m-%d %H:%M")

        # Status color
        status_color = config["color"] if item_count > 0 else "secondary"

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
                        html.Div(
                            [
                                html.Strong("Avg Rating: "),
                                html.Span(
                                    f"{avg_rating:.1f}/10" if avg_rating > 0 else "N/A",
                                    className="text-warning",
                                ),
                            ],
                            className="mb-1",
                        ),
                        html.Div(
                            [
                                html.Strong("Last Update: "),
                                html.Span(latest_update, className="text-muted small"),
                            ],
                            className="mb-2",
                        ),
                        dbc.Button(
                            f"View {config['name']}",
                            id=f"btn-entertainment-{source_id}",
                            color="outline-primary",
                            size="sm",
                            className="w-100",
                        ),
                    ]
                ),
            ],
            className="mb-3 h-100",
        )

        cards.append(dbc.Col(card, md=6, lg=4))

    return cards


def create_entertainment_table(source_id, items):
    """Create a detailed table for entertainment items"""
    if not items:
        return dbc.Alert(
            "No entertainment content available for this category.",
            color="info",
            className="text-center",
        )

    # Sort items by rating or timestamp
    sorted_items = sorted(
        items,
        key=lambda x: (
            x["rating"],
            x["timestamp"] or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    # Convert to DataFrame
    df_data = []
    for item in sorted_items:
        # Format timestamp
        time_str = item["timestamp"].strftime("%Y-%m-%d %H:%M") if item["timestamp"] else "N/A"

        # Format rating
        rating_str = f"{item['rating']:.1f}/10" if item["rating"] > 0 else "N/A"

        # Format showtimes for cinema
        showtime_str = ", ".join(item["showtimes"][:3]) if item["showtimes"] else "N/A"
        if len(item["showtimes"]) > 3:
            showtime_str += f" +{len(item['showtimes']) - 3} more"

        row = {
            "Title": (item["title"][:60] + "..." if len(item["title"]) > 60 else item["title"]),
            "Description": item["description"],
            "Genre": item["genre"],
            "Rating": rating_str,
            "Duration": item["duration"],
            "Cinema": item["cinema_name"] if item["cinema_name"] else "N/A",
            "Showtimes": showtime_str,
            "Trend Score": (f"{item['trend_score']:.1f}" if item["trend_score"] > 0 else "N/A"),
            "Engagement": (f"{item['engagement']:,}" if item["engagement"] > 0 else "N/A"),
            "Date": time_str,
            "URL": item["url"],
        }
        df_data.append(row)

    df = pd.DataFrame(df_data)

    # Create columns based on data availability
    columns = [
        {"name": "Title", "id": "Title", "type": "text"},
        {"name": "Description", "id": "Description", "type": "text"},
        {"name": "Genre", "id": "Genre", "type": "text"},
        {"name": "Rating", "id": "Rating", "type": "text"},
    ]

    # Add cinema-specific columns if applicable
    if any(item["cinema_name"] for item in items):
        columns.extend(
            [
                {"name": "Duration", "id": "Duration", "type": "text"},
                {"name": "Cinema", "id": "Cinema", "type": "text"},
                {"name": "Showtimes", "id": "Showtimes", "type": "text"},
            ]
        )

    # Add meme-specific columns if applicable
    if any(item["trend_score"] > 0 for item in items):
        columns.extend(
            [
                {"name": "Trend Score", "id": "Trend Score", "type": "text"},
                {"name": "Engagement", "id": "Engagement", "type": "text"},
            ]
        )

    columns.extend(
        [
            {"name": "Date", "id": "Date", "type": "text"},
            {"name": "Link", "id": "URL", "type": "text", "presentation": "markdown"},
        ]
    )

    # Convert URLs to markdown links
    df["URL"] = df.apply(lambda row: f"[🔗 View]({row['URL']})" if row["URL"] != "#" else "N/A", axis=1)

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
            # Highlight high-rated content
            {
                "if": {"filter_query": "{Rating} > 8.0", "column_id": "Rating"},
                "backgroundColor": "#3C5A3C",
                "color": "#AEF4AE",
            },
        ],
    )


def render_entertainment_tab():
    """Main render function for the Entertainment dashboard tab"""
    total_items = len(ALL_ENTERTAINMENT)
    total_genres = len({item["genre"] for item in ALL_ENTERTAINMENT if item.get("genre") and item["genre"] != "Unknown"})
    active_sources = sum(1 for data in ENTERTAINMENT_DATA.values() if len(data) > 0)

    # Calculate average rating
    avg_rating = 0
    valid_ratings = [item["rating"] for item in ALL_ENTERTAINMENT if item.get("rating") and item["rating"] > 0]
    if valid_ratings:
        avg_rating = sum(valid_ratings) / len(valid_ratings)

    return html.Div(
        [
            # Header with statistics
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-film me-2"),
                                    "Entertainment Dashboard",
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
                                                                total_items,
                                                                className="text-primary mb-0",
                                                            ),
                                                            html.P(
                                                                "Total Items",
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
                                                                f"{avg_rating:.1f}/10",
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
                                        md=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H4(
                                                                total_genres,
                                                                className="text-info mb-0",
                                                            ),
                                                            html.P(
                                                                "Genres",
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
                                    dbc.CardHeader(html.H5("Content by Genre", className="mb-0")),
                                    dbc.CardBody([create_genre_distribution_chart()]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(html.H5("Rating Distribution", className="mb-0")),
                                    dbc.CardBody([create_rating_distribution_chart()]),
                                ]
                            )
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            # Entertainment categories
            html.H4("Entertainment Categories", className="text-primary mb-3"),
            dbc.Row(create_entertainment_summary_cards(), className="mb-4"),
            # Trakt & Spotify tables
            html.H4("Trending Movies (Trakt)", className="text-primary mb-2"),
            create_simple_table(
                ENTERTAINMENT_DATA.get("trakt_movies", []),
                ["title", "year", "watchers"],
            ),
            html.H4("Trending Shows (Trakt)", className="text-primary mt-4 mb-2"),
            create_simple_table(ENTERTAINMENT_DATA.get("trakt_shows", []), ["title", "year", "watchers"]),
            html.H4("Spotify New Releases", className="text-primary mt-4 mb-2"),
            create_simple_table(
                ((ENTERTAINMENT_DATA.get("spotify_browse", []) or {}).get("new_releases", []) if isinstance(ENTERTAINMENT_DATA.get("spotify_browse", {}), dict) else []),
                ["name", "release_date", "artists"],
            ),
            html.H4("Spotify Featured Playlists", className="text-primary mt-4 mb-2"),
            create_simple_table(
                ((ENTERTAINMENT_DATA.get("spotify_browse", []) or {}).get("playlists", []) if isinstance(ENTERTAINMENT_DATA.get("spotify_browse", {}), dict) else []),
                ["name", "owner", "tracks"],
            ),
            # Data display area
            html.Div(id="entertainment-data-display"),
            # Storage for selected source
            dcc.Store(id="selected-entertainment-source"),
        ]
    )


def register_entertainment_callbacks(app):
    """Register callbacks for the Entertainment dashboard tab"""
    # Create callbacks for each source button
    for source_id in ENTERTAINMENT_SOURCES_CONFIG:

        @callback(
            Output("entertainment-data-display", "children"),
            Output("selected-entertainment-source", "data"),
            Input(f"btn-entertainment-{source_id}", "n_clicks"),
            prevent_initial_call=True,
        )
        def display_entertainment_data(n_clicks, source_id=source_id):
            if n_clicks:
                config = ENTERTAINMENT_SOURCES_CONFIG[source_id]
                items = ENTERTAINMENT_DATA[source_id]

                return (
                    html.Div(
                        [
                            html.Hr(),
                            html.H4(
                                [
                                    html.Span(config["icon"], className="me-2"),
                                    f"{config['name']} Content",
                                ],
                                className="text-primary mb-3",
                            ),
                            create_entertainment_table(source_id, items),
                        ]
                    ),
                    source_id,
                )

            return html.Div(), None


if __name__ == "__main__":
    print("Entertainment Dashboard Tab - Data Summary:")
    for source_id, config in ENTERTAINMENT_SOURCES_CONFIG.items():
        item_count = len(ENTERTAINMENT_DATA[source_id])
        print(f"  {config['name']}: {item_count} items")

    total = len(ALL_ENTERTAINMENT)
    print(f"  Total: {total} entertainment items across {len(ENTERTAINMENT_SOURCES_CONFIG)} sources")
