"""Anime Tab Component for Watchtower Dashboard"""
import json
import dash_bootstrap_components as dbc
from dash import html, dcc
from pathlib import Path
from typing import List, Dict, Any
import logging

# Set up logging
logger = logging.getLogger(__name__)

def load_anime_data() -> List[Dict[str, Any]]:
    """Load anime data from JSON files"""
    try:
        data_dir = Path("data/anime")
        anime_data = []
        
        # Look for anime JSON files in the data directory
        if data_dir.exists():
            for json_file in data_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            anime_data.extend(data)
                        elif isinstance(data, dict):
                            anime_data.append(data)
                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")
        
        logger.info(f"Loaded {len(anime_data)} anime items")
        return anime_data
    except Exception as e:
        logger.error(f"Error loading anime data: {e}")
        return []

def create_anime_card(anime: Dict[str, Any]) -> dbc.Card:
    """Create a card component for a single anime item"""
    try:
        title = anime.get('title', 'Unknown Title')
        mean_score = anime.get('mean', 0)
        rank = anime.get('rank', 'N/A')
        popularity = anime.get('popularity', 'N/A')
        synopsis = anime.get('synopsis', 'No synopsis available.')
        
        # Get image
        main_picture = anime.get('main_picture', {})
        image_url = main_picture.get('large', main_picture.get('medium', ''))
        
        # Get additional details
        num_episodes = anime.get('num_episodes', 'N/A')
        media_type = anime.get('media_type', 'N/A')
        status = anime.get('status', 'N/A')
        source = anime.get('source', 'N/A')
        rating = anime.get('rating', 'N/A')
        
        # Get genres
        genres = anime.get('genres', [])
        genres_text = ', '.join([g['name'] for g in genres if isinstance(g, dict) and 'name' in g])
        
        # Get studios
        studios = anime.get('studios', [])
        studios_text = ', '.join([s['name'] for s in studios if isinstance(s, dict) and 'name' in s])
        
        # Get season info
        start_season = anime.get('start_season', {})
        season_text = f"{start_season.get('season', '').capitalize()} {start_season.get('year', '')}" if start_season else 'N/A'
        
        # Get broadcast info
        broadcast = anime.get('broadcast', {})
        broadcast_text = f"{broadcast.get('day_of_the_week', '').capitalize()} at {broadcast.get('start_time', '')} JST" if broadcast else 'N/A'
        
        card_header = dbc.CardHeader(
            html.H4(title, className="mb-0", style={'fontSize': '1.1rem'})
        )
        
        card_body_content = [
            # Image
            html.Div(
                html.Img(
                    src=image_url,
                    style={'width': '100%', 'maxWidth': '200px', 'height': 'auto'},
                    className="mb-3"
                ) if image_url else html.Div(
                    "No Image Available", 
                    className="text-muted text-center p-3 border mb-3",
                    style={'minHeight': '200px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}
                ),
                className="text-center"
            ),
            
            # Metrics
            dbc.Row([
                dbc.Col([
                    html.Small("Score", className="text-muted"),
                    html.H6(f"{mean_score:.2f}" if mean_score else "N/A", className="mb-0")
                ], width=4),
                dbc.Col([
                    html.Small("Rank", className="text-muted"),
                    html.H6(f"#{rank}" if rank != 'N/A' else "N/A", className="mb-0")
                ], width=4),
                dbc.Col([
                    html.Small("Popularity", className="text-muted"),
                    html.H6(f"#{popularity}" if popularity != 'N/A' else "N/A", className="mb-0")
                ], width=4),
            ], className="mb-3"),
            
            # Collapsible details
            dbc.Accordion([
                dbc.AccordionItem([
                    html.P(synopsis, className="mb-3"),
                    html.Hr(),
                    html.Ul([
                        html.Li(f"Episodes: {num_episodes}"),
                        html.Li(f"Media Type: {media_type.capitalize() if media_type != 'N/A' else 'N/A'}"),
                        html.Li(f"Status: {status.replace('_', ' ').title() if status != 'N/A' else 'N/A'}"),
                        html.Li(f"Source: {source.capitalize() if source != 'N/A' else 'N/A'}"),
                        html.Li(f"Rating: {rating.upper().replace('_', '-') if rating != 'N/A' else 'N/A'}"),
                        html.Li(f"Genres: {genres_text if genres_text else 'N/A'}"),
                        html.Li(f"Studios: {studios_text if studios_text else 'N/A'}"),
                        html.Li(f"Season: {season_text.strip() if season_text.strip() != 'N/A' else 'N/A'}"),
                        html.Li(f"Broadcast: {broadcast_text.strip() if broadcast_text.strip() != 'N/A' else 'N/A'}"),
                    ], className="mb-0")
                ], title="Details & Synopsis")
            ], start_collapsed=True)
        ]
        
        return dbc.Card([
            card_header,
            dbc.CardBody(card_body_content)
        ], className="mb-3 h-100")
        
    except Exception as e:
        logger.error(f"Error creating anime card: {e}")
        return dbc.Card(
            dbc.CardBody([
                html.H4("Error Loading Anime", className="card-title"),
                html.P(f"Error: {str(e)}", className="card-text")
            ]),
            className="mb-3"
        )

def render_anime_tab() -> html.Div:
    """Render the anime tab with anime data"""
    try:
        anime_data = load_anime_data()
        
        if not anime_data:
            return html.Div([
                dbc.Alert(
                    [
                        html.H4("No Anime Data Available", className="alert-heading"),
                        html.P("No anime data found. Please run the anime ETL to populate data."),
                        html.Hr(),
                        html.P("Expected data location: data/anime/*.json", className="mb-0")
                    ],
                    color="info"
                )
            ], className="p-4")
        
        # Create cards for anime items
        anime_cards = []
        for anime in anime_data[:20]:  # Limit to first 20 for performance
            anime_cards.append(create_anime_card(anime))
        
        # Create grid layout
        card_columns = []
        for i in range(0, len(anime_cards), 3):  # 3 cards per row
            row_cards = anime_cards[i:i+3]
            card_columns.append(
                dbc.Row([
                    dbc.Col(card, width=4) for card in row_cards
                ], className="mb-4")
            )
        
        return html.Div([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("🎌 Anime Collection", className="mb-3"),
                    html.P(f"Displaying {len(anime_cards)} anime items", className="text-muted")
                ])
            ], className="mb-4"),
            
            # Anime cards
            html.Div(card_columns)
            
        ], className="p-4")
        
    except Exception as e:
        logger.error(f"Error rendering anime tab: {e}")
        return html.Div([
            dbc.Alert(
                f"Error loading anime tab: {str(e)}",
                color="danger"
            )
        ], className="p-4")

# Register any callbacks if needed (none for this tab currently)
def register_anime_callbacks(app):
    """Register callbacks for anime tab (none needed currently)"""
    pass 