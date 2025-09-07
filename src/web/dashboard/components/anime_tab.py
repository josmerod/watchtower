"""Anime Tab Component for Watchtower Dashboard"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import dash_bootstrap_components as dbc
from dash import html

# Set up logging
logger = logging.getLogger(__name__)


def load_anime_data() -> Dict[str, List[Dict[str, Any]]]:
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
            }

            for filename, category in file_mapping.items():
                json_file = data_dir / filename
                if json_file.exists():
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                anime_categories[category] = data
                            elif isinstance(data, dict):
                                anime_categories[category] = [data]
                    except Exception as e:
                        logger.error(f"Error loading {json_file}: {e}")

        total_items = sum(len(v) for v in anime_categories.values())
        logger.info(
            f"Loaded {total_items} anime items across {len(anime_categories)} categories"
        )
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
        }


def create_anime_card(anime: Dict[str, Any], rank_info: Dict[str, str], idx: int) -> dbc.Card:
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
                            html.Img(
                                src=image_url if image_url else "/assets/anime-placeholder.png",
                                style={
                                    "width": "60px",
                                    "height": "85px",
                                    "objectFit": "cover",
                                    "borderRadius": "4px",
                                },
                                className="mb-2",
                            ) if image_url else html.Div(
                                "🎌",
                                style={
                                    "fontSize": "2rem",
                                    "textAlign": "center",
                                    "width": "60px",
                                    "height": "85px",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "backgroundColor": "#f8f9fa",
                                    "borderRadius": "4px",
                                }
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
                                        " • ".join(genre_names) if genre_names else "No genres",
                                        className="text-muted",
                                        style={"fontSize": "0.75rem"},
                                    )
                                ],
                                className="mb-2",
                            ),
                            html.P(
                                short_synopsis,
                                className="text-muted mb-0",
                                style={"fontSize": "0.8rem", "lineHeight": "1.3"},
                            ) if short_synopsis else None,
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
            style={"backgroundColor": "#fafafa", "minHeight": "140px"},
        )
    except Exception as e:
        logger.error(f"Error creating anime card: {e}")
        return dbc.Card(
            dbc.CardBody([html.P("Error loading anime")]),
            className="mb-3",
        )


def create_community_rankings_section(
    anime_data: Dict[str, List[Dict[str, Any]]],
) -> html.Div:
    """Create comprehensive community rankings section with multi-column layout"""
    try:
        # Define ranking categories with enhanced descriptions
        ranking_info = {
            "top_rated_all": {
                "title": "🏆 All-Time Greatest",
                "description": "Highest-rated anime of all time",
                "badge_color": "warning",
                "icon": "👑",
                "display_count": 12,
            },
            "top_tv_series": {
                "title": "📺 Top TV Series",
                "description": "Best TV anime series",
                "badge_color": "primary",
                "icon": "🎬",
                "display_count": 12,
            },
            "top_movies": {
                "title": "🎭 Top Movies",
                "description": "Highest-rated anime movies",
                "badge_color": "danger",
                "icon": "🎯",
                "display_count": 12,
            },
            "top_airing": {
                "title": "📡 Currently Airing",
                "description": "Best anime currently broadcasting",
                "badge_color": "success",
                "icon": "⚡",
                "display_count": 12,
            },
            "top_upcoming": {
                "title": "🔮 Upcoming",
                "description": "Most anticipated upcoming anime",
                "badge_color": "info",
                "icon": "🚀",
                "display_count": 12,
            },
            "top_ova": {
                "title": "💎 Top OVA",
                "description": "Best Original Video Animations",
                "badge_color": "secondary",
                "icon": "💿",
                "display_count": 8,
            },
            "top_special": {
                "title": "⭐ Special Episodes",
                "description": "Top special episodes and content",
                "badge_color": "dark",
                "icon": "🌟",
                "display_count": 8,
            },
        }

        # Group categories for multi-column layout
        primary_categories = ["top_rated_all", "top_tv_series", "top_movies"]
        secondary_categories = ["top_airing", "top_upcoming"]
        tertiary_categories = ["top_ova", "top_special"]
        
        def create_category_column(categories: List[str]) -> html.Div:
            """Create a column of anime categories"""
            column_content = []
            
            for category in categories:
                if category not in anime_data or not anime_data[category]:
                    continue
                    
                anime_list = anime_data[category]
                info = ranking_info[category]
                display_count = info["display_count"]
                
                # Create anime cards for this category
                anime_cards = []
                for idx, anime in enumerate(anime_list[:display_count]):
                    if not anime:
                        continue
                    card = create_anime_card(anime, info, idx)
                    anime_cards.append(card)
                
                if anime_cards:
                    category_section = html.Div(
                        [
                            html.Div(
                                [
                                    html.H4(
                                        [html.Span(info["icon"], className="me-2"), info["title"]],
                                        className="mb-2",
                                        style={"fontSize": "1.25rem"},
                                    ),
                                    html.P(
                                        info["description"],
                                        className="text-muted mb-3",
                                        style={"fontSize": "0.9rem"},
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(anime_cards),
                        ],
                        className="mb-5",
                    )
                    column_content.append(category_section)
            
            return html.Div(column_content)

        # Check if we have any data
        available_categories = [cat for cat in ranking_info.keys() if anime_data.get(cat)]
        
        if not available_categories:
            return html.Div(
                [
                    dbc.Alert(
                        [
                            html.H4(
                                "Community Rankings Not Available",
                                className="alert-heading",
                            ),
                            html.P(
                                "Comprehensive anime rankings data is not yet available."
                            ),
                            html.Hr(),
                            html.P(
                                "Run the enhanced ETL to fetch community rankings:",
                                className="mb-2",
                            ),
                            html.Code(
                                "uv run python src/etl/anime/mal_etl.py",
                                className="d-block p-2 bg-light",
                            ),
                        ],
                        color="info",
                    )
                ]
            )

        return html.Div(
            [
                # Header
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H3("🏅 Community Rankings", className="mb-2"),
                                html.P(
                                    "MyAnimeList community rankings updated regularly",
                                    className="text-muted mb-4",
                                ),
                            ]
                        )
                    ],
                    className="mb-4",
                ),
                # Multi-column layout
                dbc.Row(
                    [
                        dbc.Col(
                            create_category_column(primary_categories),
                            width=12,
                            lg=4,
                            className="mb-4",
                        ),
                        dbc.Col(
                            create_category_column(secondary_categories),
                            width=12,
                            lg=4,
                            className="mb-4",
                        ),
                        dbc.Col(
                            create_category_column(tertiary_categories),
                            width=12,
                            lg=4,
                            className="mb-4",
                        ),
                    ],
                    className="g-4",
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Error creating community rankings: {e}")
        return html.Div([dbc.Alert("Error loading community rankings", color="danger")])


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
                            html.H4(
                                "No Anime Data Available", className="alert-heading"
                            ),
                            html.P(
                                "No anime data found. Please run the anime ETL to populate data."
                            ),
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
                    label="🏅 Community Rankings",
                    tab_id="rankings-tab",
                    children=[
                        html.Div(
                            [create_community_rankings_section(anime_data)],
                            className="p-4",
                        )
                    ],
                )
            ],
            id="anime-tabs",
            active_tab="rankings-tab",
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
            [dbc.Alert(f"Error loading anime tab: {str(e)}", color="danger")],
            className="p-4",
        )


# Register any callbacks if needed
def register_anime_callbacks(app):
    """Register callbacks for anime tab"""
    # Currently no interactive callbacks needed
    # Future: could add filtering, search, favorites functionality
    pass
