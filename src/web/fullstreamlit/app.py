"""
Watchtower Streamlit Application - Main file
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import utilities from our modules
from src.utils.logging import get_logger
from src.web.fullstreamlit.styles.main import get_main_style
from src.web.fullstreamlit.utils.data_service_ultra_optimized import create_ultra_optimized_service

# Import all components
from src.web.fullstreamlit.components import (
    shortcuts_tab,
    videos_tab,
    news_tab,
    games_tab,
    courses_tab,
    events_tab,
    admin_tab,
    arxiv_papers,
    arxiv_search,
    dev_communities_tab,
    innovation_tab,
    crypto_tab,
    security_tab,
    enhanced_arxiv_papers,
    monitoring_tab,
    tech_events_tab,
    ai_platforms_tab,
    google_cloud_blog_tab,
    aws_training_tab,
    azure_training_tab,
    home_server_tab
)
# Import for Anime Tab
from src.web.fullstreamlit.components.anime_display import display_anime_section
from src.models.anime import AnimeItem
import json
from pathlib import Path
from typing import List, Dict, Optional # Already imported but good for clarity


# Import enhanced components
from src.web.fullstreamlit.components import enhanced_innovation_tab

# Initialize logger and data service
logger = get_logger("WatchtowerApp")
data_service = create_ultra_optimized_service(logger)

# Set page configuration
st.set_page_config(
    page_title="Watchtower",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply CSS styles
st.markdown(get_main_style(), unsafe_allow_html=True)

# Header
st.title("🗼 Watchtower")

if st.button("🔄 Actualizar"):
    st.cache_data.clear()
    st.rerun()

# Load data
@st.cache_data(ttl=1800)
def get_cached_data():
    """Load and cache data"""
    try:
        data = {}
        data['games'] = data_service.get_games_data()
        data['courses'] = data_service.get_courses_data()
        data['news'] = data_service.get_news_data()
        data['videos'] = data_service.get_videos_data()
        data['arxiv'] = data_service.get_arxiv_data()
        data['events'] = data_service.get_events_data()
        data['new_game_releases'] = data_service.get_new_game_releases_data() # Added
        data['google_cloud_blog'] = data_service.get_google_cloud_blog_data()
        data['aws_training'] = data_service.get_aws_training_data()
        data['azure_training'] = data_service.get_azure_training_data()
        data['home_server_trends'] = data_service.get_home_server_trends_data()
        return data
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return {}

cached_data = get_cached_data()

# Retrieve the new data slices
google_cloud_blog_data = cached_data.get('google_cloud_blog', [])
aws_training_data = cached_data.get('aws_training', [])
azure_training_data = cached_data.get('azure_training', [])

# Tabs
main_tabs = st.tabs([
    "Dashboard",
    "Videos",
    "Noticias",
    "Google Cloud Blog",
    "AWS Training",      # New tab
    "Azure Training",    # New tab
    "Juegos",
    "Cursos",
    "Eventos Tech",
    "Comunidades Dev",
    "Seguridad",
    "Innovación",
    "Plataformas IA",
    "Home Server", # New Tab
    "Crypto",
    "ArXiv",
    "⛩️ Anime", # New Tab
    "Monitoreo",
    "Eventos Valencia",
    "Admin"
])

# --- Anime Tab Specific Functions ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def load_anime_data(json_path: Path) -> List[AnimeItem]:
    """Loads anime data from a JSON file and converts to AnimeItem models."""
    if not json_path.exists():
        logger.error(f"Anime data file not found: {json_path}")
        return []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Assuming the JSON is a list of dicts, each convertible to AnimeItem
        return [AnimeItem(**item) for item in data]
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {json_path}")
        return []
    except Exception as e: # Catch Pydantic validation errors or others
        logger.error(f"Error parsing anime data from {json_path}: {e}")
        return []

def display_anime_calendar_tab():
    """Displays the Anime Calendar tab with sections for seasonal, popular, and rated anime."""
    st.title("⛩️ Anime Calendar & Guide")

    DATA_PATH = Path("data/anime")
    current_season_file = DATA_PATH / "current_season_anime.json"
    top_popular_file = DATA_PATH / "top_popular_anime.json"
    top_rated_file = DATA_PATH / "top_rated_anime.json"

    seasonal_anime = load_anime_data(current_season_file)
    popular_anime = load_anime_data(top_popular_file)
    rated_anime = load_anime_data(top_rated_file)

    season_tab, popular_tab, rated_tab = st.tabs([
        f"🌸 Current Season ({len(seasonal_anime)})" if seasonal_anime else "🌸 Current Season",
        f"🔥 Top Popular ({len(popular_anime)})" if popular_anime else "🔥 Top Popular",
        f"⭐ Top Rated ({len(rated_anime)})" if rated_anime else "⭐ Top Rated"
    ])

    with season_tab:
        display_anime_section(
            "🌸 Current Season Anime",
            seasonal_anime,
            num_columns=3
        )

    with popular_tab:
        display_anime_section(
            "🔥 Top Popular Anime",
            popular_anime,
            num_columns=3
        )

    with rated_tab:
        display_anime_section(
            "⭐ Top Rated Anime",
            rated_anime,
            num_columns=3
        )

# --- End Anime Tab Specific Functions ---

def render_tab_safely(tab_name, render_func, *args, **kwargs):
    """Safely render a tab with error handling"""
    try:
        render_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error rendering {tab_name}: {str(e)}")
        st.error(f"Error cargando {tab_name}")

# Render tabs
with main_tabs[0]:
    render_tab_safely("Dashboard", shortcuts_tab.render, logger, data_service)

with main_tabs[1]:
    videos_data = cached_data.get('videos', {})
    render_tab_safely("Videos", videos_tab.render, logger, videos_data)

with main_tabs[2]:
    render_tab_safely("Noticias", news_tab.render, logger)

with main_tabs[3]: # Google Cloud Blog
    render_tab_safely("Google Cloud Blog", google_cloud_blog_tab.render, logger, google_cloud_blog_data)

with main_tabs[4]: # AWS Training
    render_tab_safely("AWS Training", aws_training_tab.render, logger, aws_training_data)

with main_tabs[5]: # Azure Training
    render_tab_safely("Azure Training", azure_training_tab.render, logger, azure_training_data)

with main_tabs[6]: # Juegos
    games_data = cached_data.get('games', (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
    new_releases_df = cached_data.get('new_game_releases', pd.DataFrame())
    
    if isinstance(games_data, tuple) and len(games_data) == 4:
        deals_df, bundles_df, giveaways_df, trending_df = games_data
    elif isinstance(games_data, tuple) and len(games_data) == 3:
        deals_df, bundles_df, giveaways_df = games_data
        trending_df = pd.DataFrame()
    else:
        deals_df = bundles_df = giveaways_df = trending_df = pd.DataFrame()
    
    render_tab_safely("Juegos", games_tab.render, deals_df, bundles_df, giveaways_df, trending_df, new_releases_df, logger)

with main_tabs[7]: # Cursos
    courses_data = cached_data.get('courses', {})
    render_tab_safely("Cursos", courses_tab.render, courses_data, logger)

with main_tabs[8]: # Eventos Tech
    render_tab_safely("Eventos Tech", tech_events_tab.render, logger, data_service)

with main_tabs[9]: # Comunidades Dev
    render_tab_safely("Comunidades Dev", dev_communities_tab.render, logger)

with main_tabs[10]: # Seguridad
    render_tab_safely("Seguridad", security_tab.render, logger, data_service)

with main_tabs[11]: # Innovación
    render_tab_safely("Innovación", enhanced_innovation_tab.render, logger, data_service)

with main_tabs[12]: # Plataformas IA
    render_tab_safely("Plataformas IA", ai_platforms_tab.render, logger)

with main_tabs[13]: # Home Server
    render_tab_safely("Home Server", home_server_tab.render, logger, data_service)

with main_tabs[14]: # Crypto
    render_tab_safely("Crypto", crypto_tab.render, logger)

with main_tabs[15]: # ArXiv
    arxiv_subtabs = st.tabs(["Mejorado", "Papers", "Búsqueda"])
    
    with arxiv_subtabs[0]:
        render_tab_safely("ArXiv Mejorado", enhanced_arxiv_papers.display_enhanced_papers)
    
    with arxiv_subtabs[1]:
        render_tab_safely("Papers ArXiv", arxiv_papers.display)
    
    with arxiv_subtabs[2]:
        render_tab_safely("Búsqueda ArXiv", arxiv_search.display)

with main_tabs[16]: # Index for Anime Tab
    render_tab_safely("Anime Calendar", display_anime_calendar_tab)

with main_tabs[17]: # Index for Monitoreo
    render_tab_safely("Monitoreo", monitoring_tab.render, logger)

with main_tabs[18]: # Index for Eventos Valencia
    render_tab_safely("Eventos Valencia", events_tab.render, logger)

with main_tabs[19]: # Index for Admin
    render_tab_safely("Admin", admin_tab.render, logger)
