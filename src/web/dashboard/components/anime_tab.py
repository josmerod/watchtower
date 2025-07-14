"""Anime Tab Component for Watchtower Dashboard"""
import json
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime, timedelta
import calendar

# Set up logging
logger = logging.getLogger(__name__)

def load_anime_data() -> Dict[str, List[Dict[str, Any]]]:
    """Load anime data from JSON files categorized by type"""
    try:
        data_dir = Path("data/anime")
        anime_categories = {
            'seasonal': [],
            'popular': [],
            'favorite': [],
            'rated': [],
            'top_rated_all': [],
            'top_airing': [],
            'top_upcoming': [],
            'top_tv_series': [],
            'top_movies': [],
            'top_ova': [],
            'top_special': []
        }
        
        # Look for anime JSON files in the data directory
        if data_dir.exists():
            file_mapping = {
                'current_season_anime.json': 'seasonal',
                'top_popular_anime.json': 'popular', 
                'top_favorite_anime.json': 'favorite',
                'top_rated_anime.json': 'rated',
                'top_rated_all_time.json': 'top_rated_all',
                'top_airing_anime.json': 'top_airing',
                'top_upcoming_anime.json': 'top_upcoming',
                'top_tv_series.json': 'top_tv_series',
                'top_movies.json': 'top_movies',
                'top_ova.json': 'top_ova',
                'top_special.json': 'top_special'
            }
            
            for filename, category in file_mapping.items():
                json_file = data_dir / filename
                if json_file.exists():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
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
            'seasonal': [], 'popular': [], 'favorite': [], 'rated': [],
            'top_rated_all': [], 'top_airing': [], 'top_upcoming': [],
            'top_tv_series': [], 'top_movies': [], 'top_ova': [], 'top_special': []
        }

def create_community_rankings_section(anime_data: Dict[str, List[Dict[str, Any]]]) -> html.Div:
    """Create comprehensive community rankings section with extensive anime lists"""
    try:
        ranking_sections = []
        
        # Define ranking categories with enhanced descriptions
        ranking_info = {
            'top_rated_all': {
                'title': '🏆 All-Time Greatest Anime', 
                'description': 'The highest-rated anime of all time according to MyAnimeList community (Top 100)',
                'badge_color': 'warning',
                'icon': '👑'
            },
            'top_tv_series': {
                'title': '📺 Top TV Series', 
                'description': 'Best TV anime series ranked by community ratings (Top 100)',
                'badge_color': 'primary',
                'icon': '🎬'
            },
            'top_movies': {
                'title': '🎭 Top Anime Movies', 
                'description': 'Highest-rated anime movies that define cinematic excellence (Top 50)',
                'badge_color': 'danger',
                'icon': '🎯'
            },
            'top_airing': {
                'title': '📡 Top Currently Airing', 
                'description': 'Best anime currently broadcasting, updated live (Top 50)',
                'badge_color': 'success',
                'icon': '⚡'
            },
            'top_upcoming': {
                'title': '🔮 Most Anticipated Upcoming', 
                'description': 'Highly anticipated anime releasing soon (Top 50)',
                'badge_color': 'info',
                'icon': '🚀'
            },
            'top_ova': {
                'title': '💎 Top OVA Series', 
                'description': 'Original Video Animations with exceptional quality (Top 30)',
                'badge_color': 'secondary',
                'icon': '💿'
            },
            'top_special': {
                'title': '⭐ Top Special Episodes', 
                'description': 'Special episodes, side stories, and unique content (Top 30)',
                'badge_color': 'dark',
                'icon': '🌟'
            }
        }
        
        for category, anime_list in anime_data.items():
            if category not in ranking_info or not anime_list:
                continue
                
            info = ranking_info[category]
            
            # Create ranking cards with enhanced layout
            ranking_cards = []
            for idx, anime in enumerate(anime_list[:50]):  # Show more for rankings
                if not anime:
                    continue
                    
                rank_display = anime.get('rank', idx + 1)
                score = anime.get('mean')
                title = anime.get('title', 'Unknown Title')
                
                # Create compact ranking card
                card_content = [
                    dbc.Row([
                        dbc.Col([
                            dbc.Badge(
                                f"#{rank_display}", 
                                color=info['badge_color'], 
                                className="me-2"
                            ),
                            html.Strong(title, style={'fontSize': '0.95rem'})
                        ], width=8),
                        dbc.Col([
                            html.Div([
                                html.Small("⭐", className="me-1"),
                                html.Strong(
                                    f"{score:.2f}" if score is not None else "N/A",
                                    style={'fontSize': '0.9rem'}
                                )
                            ], className="text-end")
                        ], width=4)
                    ], className="align-items-center")
                ]
                
                # Add genre info if available
                genres = anime.get('genres', [])
                if genres:
                    genre_names = [g.get('name', '') for g in genres[:3] if g]
                    if genre_names:
                        card_content.append(
                            html.Div([
                                html.Small(
                                    ' • '.join(genre_names),
                                    className="text-muted",
                                    style={'fontSize': '0.75rem'}
                                )
                            ], className="mt-1")
                        )
                
                card = dbc.Card(
                    dbc.CardBody(card_content, className="py-2 px-3"),
                    className="mb-2 border-0 shadow-sm",
                    style={'backgroundColor': '#f8f9fa'}
                )
                ranking_cards.append(card)
            
            # Create section for this ranking category
            section_content = html.Div([
                html.H4([
                    html.Span(info['icon'], className="me-2"),
                    info['title']
                ], className="mb-2"),
                html.P(info['description'], className="text-muted mb-3"),
                html.Div(ranking_cards),
                html.Hr(className="my-5")
            ])
            
            ranking_sections.append(section_content)
        
        if not ranking_sections:
            return html.Div([
                dbc.Alert([
                    html.H4("Community Rankings Not Available", className="alert-heading"),
                    html.P("Comprehensive anime rankings data is not yet available."),
                    html.Hr(),
                    html.P("Run the enhanced ETL to fetch community rankings:", className="mb-2"),
                    html.Code("uv run python src/etl/anime/mal_etl.py", className="d-block p-2 bg-light")
                ], color="info")
            ])
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("🏅 Community Rankings", className="mb-3"),
                        html.P(
                            "Comprehensive anime rankings based on MyAnimeList community ratings, "
                            "updated regularly to reflect the latest community preferences.",
                            className="text-muted mb-4"
                        )
                    ])
                ])
            ], className="mb-4"),
            html.Div(ranking_sections)
        ])
        
    except Exception as e:
        logger.error(f"Error creating community rankings: {e}")
        return html.Div([
            dbc.Alert("Error loading community rankings", color="danger")
        ])

def render_anime_tab() -> html.Div:
    """Render the anime tab with enhanced community rankings"""
    try:
        anime_data = load_anime_data()
        
        # Check if we have any data
        total_anime = sum(len(v) for v in anime_data.values())
        if total_anime == 0:
            return html.Div([
                dbc.Alert(
                    [
                        html.H4("No Anime Data Available", className="alert-heading"),
                        html.P("No anime data found. Please run the anime ETL to populate data."),
                        html.Hr(),
                        html.P("Expected data location: data/anime/*.json", className="mb-0"),
                        html.P("Run: uv run python src/etl/anime/mal_etl.py", className="mb-0 mt-2 font-monospace")
                    ],
                    color="info"
                )
            ], className="p-4")
        
        # Create tabs for different views
        tab_content = dbc.Tabs([
            dbc.Tab(
                label="🏅 Community Rankings",
                tab_id="rankings-tab",
                children=[
                    html.Div([
                        create_community_rankings_section(anime_data)
                    ], className="p-4")
                ]
            )
        ], id="anime-tabs", active_tab="rankings-tab")
        
        return html.Div([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("🎌 Anime Dashboard", className="mb-3"),
                    html.P(f"Total anime loaded: {total_anime} across {len([k for k, v in anime_data.items() if v])} categories", className="text-muted")
                ])
            ], className="mb-4 p-4 pb-0"),
            
            # Tabs
            tab_content
            
        ])
        
    except Exception as e:
        logger.error(f"Error rendering anime tab: {e}")
        return html.Div([
            dbc.Alert(
                f"Error loading anime tab: {str(e)}",
                color="danger"
            )
        ], className="p-4")

# Register any callbacks if needed
def register_anime_callbacks(app):
    """Register callbacks for anime tab"""
    # Currently no interactive callbacks needed
    # Future: could add filtering, search, favorites functionality
    pass