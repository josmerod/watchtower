"""Anime Tab Component for Watchtower Dashboard"""

import datetime
import json
import logging
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

# Set up logging
logger = logging.getLogger(__name__)


def load_anime_data() -> dict[str, list[dict[str, Any]]]:
    """Load anime data from JSON files categorized by type"""
    try:
        data_dir = Path("data/anime")
        anime_categories = {
            "seasonal": [],
            "popular": [],
            "favorite": [],
            "rated": [],
            "top_rated_all": [],
            "top_airing": [],
            "top_upcoming": [],
            "top_tv_series": [],
            "top_movies": [],
            "top_ova": [],
            "top_special": [],
            "schedule": [],
        }

        # Look for anime JSON files in the data directory
        if data_dir.exists():
            file_mapping = {
                "current_season_anime.json": "seasonal",
                "top_popular_anime.json": "popular",
                "top_favorite_anime.json": "favorite",
                "top_rated_anime.json": "rated",
                "top_rated_all_time.json": "top_rated_all",
                "top_airing_anime.json": "top_airing",
                "top_upcoming_anime.json": "top_upcoming",
                "top_tv_series.json": "top_tv_series",
                "top_movies.json": "top_movies",
                "top_ova.json": "top_ova",
                "top_special.json": "top_special",
                "anilist_schedule.json": "schedule",
            }

            for filename, category in file_mapping.items():
                json_file = data_dir / filename
                if json_file.exists():
                    try:
                        with open(json_file, encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                anime_categories[category] = data
                            elif isinstance(data, dict):
                                anime_categories[category] = [data]
                    except Exception as e:
                        logger.error(f"Error loading {json_file}: {e}")

        total_items = sum(len(v) for v in anime_categories.values())
        logger.info(f"Loaded {total_items} anime items across {len(anime_categories)} categories")
        return anime_categories
    except Exception as e:
        logger.error(f"Error loading anime data: {e}")
        return {
            "seasonal": [],
            "popular": [],
            "favorite": [],
            "rated": [],
            "top_rated_all": [],
            "top_airing": [],
            "top_upcoming": [],
            "top_tv_series": [],
            "top_movies": [],
            "top_ova": [],
            "top_special": [],
            "schedule": [],
        }


def create_anime_card(anime: dict[str, Any], rank_info: dict[str, str], idx: int) -> dbc.Card:
    """Create an enhanced anime card with image and better layout"""
    try:
        rank_display = anime.get("rank", idx + 1)
        score = anime.get("mean")
        title = anime.get("title", "Unknown Title")
        image_url = anime.get("main_picture", {}).get("medium", "")
        synopsis = anime.get("synopsis", "")

        # Truncate synopsis for card display
        short_synopsis = synopsis[:120] + "..." if len(synopsis) > 120 else synopsis

        # Genre information
        genres = anime.get("genres", [])
        genre_names = [g.get("name", "") for g in genres[:3] if g]

        card_content = [
            dbc.Row(
                [
                    # Image column
                    dbc.Col(
                        [
                            (
                                html.Img(
                                    src=(image_url if image_url else "/assets/anime-placeholder.png"),
                                    style={
                                        "width": "60px",
                                        "height": "85px",
                                        "objectFit": "cover",
                                        "borderRadius": "4px",
                                    },
                                    className="mb-2",
                                )
                                if image_url
                                else html.Div(
                                    style={
                                        "fontSize": "2rem",
                                        "textAlign": "center",
                                        "width": "60px",
                                        "height": "85px",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                        "backgroundColor": "#2c2c2c",
                                        "borderRadius": "4px",
                                        "color": "#6c757d",
                                    },
                                )
                            )
                        ],
                        width=3,
                        className="d-flex justify-content-center",
                    ),
                    # Content column
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    dbc.Badge(
                                        f"#{rank_display}",
                                        color=rank_info["badge_color"],
                                        className="me-2 mb-1",
                                    ),
                                    html.H6(
                                        title,
                                        className="mb-1",
                                        style={"lineHeight": "1.2"},
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Span("⭐", className="me-1"),
                                    html.Strong(
                                        f"{score:.2f}" if score is not None else "N/A",
                                        style={"fontSize": "0.9rem"},
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Small(
                                        (" • ".join(genre_names) if genre_names else "No genres"),
                                        className="text-muted",
                                        style={"fontSize": "0.75rem"},
                                    )
                                ],
                                className="mb-2",
                            ),
                            (
                                html.P(
                                    short_synopsis,
                                    className="text-muted mb-0",
                                    style={"fontSize": "0.8rem", "lineHeight": "1.3"},
                                )
                                if short_synopsis
                                else None
                            ),
                        ],
                        width=9,
                    ),
                ],
                className="g-2",
            )
        ]

        return dbc.Card(
            dbc.CardBody(card_content, className="p-3"),
            className="mb-3 h-100 shadow-sm border-0",
            color="dark",
            inverse=True,
            style={"minHeight": "140px"},
        )
    except Exception as e:
        logger.error(f"Error creating anime card: {e}")
        return dbc.Card(
            dbc.CardBody([html.P("Error loading anime")]),
            className="mb-3",
        )


def create_schedule_card(item: dict[str, Any]) -> dbc.Card:
    """Create a compact card for the airing schedule"""
    try:
        airing_at = item.get("airing_at", 0)
        dt = datetime.datetime.fromtimestamp(airing_at)
        time_str = dt.strftime("%A, %H:%M")

        episode = item.get("episode", "?")
        title = item.get("title_romaji") or item.get("title_english") or "Unknown"
        image_url = item.get("cover_image_medium", "")

        card_content = [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Img(
                                src=image_url if image_url else "/assets/anime-placeholder.png",
                                style={
                                    "width": "100%",
                                    "height": "70px",
                                    "objectFit": "cover",
                                    "borderRadius": "4px",
                                },
                            )
                        ],
                        width=3,
                        className="p-2 d-flex align-items-center",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    dbc.Badge(time_str, color="primary", className="me-2 mb-1", style={"fontSize": "0.7rem"}),
                                    html.Small(f"Ep {episode}", className="fw-bold mb-1", style={"fontSize": "0.7rem", "color": "#adb5bd"}),
                                ]
                            ),
                            html.H6(title, className="mb-0 text-truncate text-white", style={"fontSize": "0.85rem", "maxWidth": "100%"}),
                        ],
                        width=9,
                        className="py-2 pe-2 d-flex flex-column justify-content-center",
                    ),
                ],
                className="g-0",
            )
        ]
        return dbc.Card(card_content, className="mb-2 shadow-sm border-0", color="dark", inverse=True)
    except Exception as e:
        logger.error(f"Error creating schedule card: {e}")
        return html.Div()


def create_anime_hub_section(
    anime_data: dict[str, list[dict[str, Any]]],
) -> html.Div:
    """Create comprehensive community rankings section with multi-column layout"""
    try:
        # Sort current airing by rating descending
        # Some items might not have 'mean' so default to 0
        current_airing = sorted(anime_data.get("top_airing", []), key=lambda x: x.get("mean") or 0.0, reverse=True)[:15]

        upcoming = anime_data.get("top_upcoming", [])[:15]

        top_all_time = sorted(anime_data.get("top_rated_all", []), key=lambda x: x.get("mean") or 0.0, reverse=True)[:15]

        def create_block(title: str, description: str, icon: str, anime_list: list) -> html.Div:
            info = {"badge_color": "primary"}
            cards = [create_anime_card(anime, info, i) for i, anime in enumerate(anime_list) if anime]

            row_cols = []
            for card in cards:
                row_cols.append(dbc.Col(card, width=12, md=6, lg=6, xl=4))

            return html.Div(
                [html.H4([html.Span(icon, className="me-2"), title], className="mb-1"), html.P(description, className="text-muted mb-3", style={"fontSize": "0.9rem"}), dbc.Row(row_cols, className="g-3")],
                className="mb-2",
            )

        left_column = dbc.Col(
            [
                create_block("📡 Current Airing (Top Rated)", "Top-rated anime currently broadcasting", "🔥", current_airing),
                html.Hr(className="my-4", style={"borderColor": "#444"}),
                create_block("🔮 Upcoming Series", "Most anticipated upcoming anime", "✨", upcoming),
                html.Hr(className="my-4", style={"borderColor": "#444"}),
                create_block("🏆 Top All-Time", "Highest-rated anime of all time", "👑", top_all_time),
            ],
            width=12,
            lg=8,
            className="pe-lg-4",
        )

        # Right column: Schedule
        schedule_raw = anime_data.get("schedule", [])
        schedule_sorted = sorted(schedule_raw, key=lambda x: x.get("airing_at", 0))
        # Filter past episodes
        now_ts = datetime.datetime.now().timestamp()
        schedule_future = [s for s in schedule_sorted if s.get("airing_at", 0) > now_ts]

        schedule_cards = [create_schedule_card(item) for item in schedule_future[:40]]

        right_column = dbc.Col(
            [
                html.H4([html.Span("📅", className="me-2"), "Airing Schedule"], className="mb-1"),
                html.P("Upcoming episodes this week", className="text-muted mb-3", style={"fontSize": "0.9rem"}),
                html.Div(schedule_cards, style={"maxHeight": "1400px", "overflowY": "auto", "paddingRight": "10px"}, className="custom-scrollbar"),
            ],
            width=12,
            lg=4,
        )

        return html.Div(dbc.Row([left_column, right_column]), className="mb-4")

    except Exception as e:
        logger.error(f"Error creating community rankings: {e}")
        return html.Div([dbc.Alert("Error loading anime hub", color="danger")])


def render_anime_tab() -> html.Div:
    """Render the anime tab with enhanced community rankings"""
    try:
        anime_data = load_anime_data()

        # Check if we have any data
        total_anime = sum(len(v) for v in anime_data.values())
        if total_anime == 0:
            return html.Div(
                [
                    dbc.Alert(
                        [
                            html.H4("No Anime Data Available", className="alert-heading"),
                            html.P("No anime data found. Please run the anime ETL to populate data."),
                            html.Hr(),
                            html.P(
                                "Expected data location: data/anime/*.json",
                                className="mb-0",
                            ),
                            html.P(
                                "Run: uv run python src/etl/anime/mal_etl.py",
                                className="mb-0 mt-2 font-monospace",
                            ),
                        ],
                        color="info",
                    )
                ],
                className="p-4",
            )

        # Create tabs for different views
        tab_content = dbc.Tabs(
            [
                dbc.Tab(
                    label="🌟 Anime Hub",
                    tab_id="hub-tab",
                    children=[
                        html.Div(
                            [create_anime_hub_section(anime_data)],
                            className="p-4",
                        )
                    ],
                )
            ],
            id="anime-tabs",
            active_tab="hub-tab",
        )

        return html.Div(
            [
                # Header
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H2("🎌 Anime Dashboard", className="mb-3"),
                                html.P(
                                    f"Total anime loaded: {total_anime} across {len([k for k, v in anime_data.items() if v])} categories",
                                    className="text-muted",
                                ),
                            ]
                        )
                    ],
                    className="mb-4 p-4 pb-0",
                ),
                # Tabs
                tab_content,
            ]
        )

    except Exception as e:
        logger.error(f"Error rendering anime tab: {e}")
        return html.Div(
            [dbc.Alert(f"Error loading anime tab: {e!s}", color="danger")],
            className="p-4",
        )


# Register any callbacks if needed
def register_anime_callbacks(app):
    """Register callbacks for anime tab"""
    # Currently no interactive callbacks needed
    # Future: could add filtering, search, favorites functionality
    pass
