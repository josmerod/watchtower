"""
Watchtower Streamlit Application - Main file
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

# Alternative approach - add absolute path
import os
watchtower_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
src_absolute = os.path.join(watchtower_root, 'src')
if src_absolute not in sys.path:
    sys.path.insert(0, src_absolute)

# Import utilities from our modules
try:
    from utils.logging import get_logger
except ImportError as e:
    print(f"❌ Failed to import get_logger: {e}")
    # Fallback - create a simple logger
    import logging
    def get_logger(name):
        return logging.getLogger(name)

from web.fullstreamlit.styles.main import get_main_style

# Import all components
from web.fullstreamlit.components import (
    shortcuts_tab,
    videos_tab,
    news_tab,
    games_tab,
    allkeyshop_tab,
    courses_tab,
    events_tab,
    admin_tab,
    arxiv_papers,
    arxiv_search,
    dev_communities_tab,
    security_tab,
    enhanced_arxiv_papers,
    monitoring_tab,
    tech_events_tab,
    ai_platforms_tab,
    google_cloud_blog_tab,
    aws_training_tab,
    azure_training_tab,
    home_server_tab,
    museums_tab,
    adhd_tab,
    chan_generals_tab,
    scavenging_tab,
    ecommerce_tab,
    enhanced_innovation_tab,
    expatcircle_tab
)

# Import for Anime Tab
from web.fullstreamlit.components.anime_display import display_anime_section
from models.anime import AnimeItem
import json
from typing import List, Dict, Optional

# Initialize logger
logger = get_logger("WatchtowerApp")

# Set page configuration
st.set_page_config(
    page_title="Watchtower",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply CSS styles
st.markdown(get_main_style(), unsafe_allow_html=True)

# Header
st.title("🗼 Watchtower")

# Improved cache clear button
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("🔄 Refresh Data"):
        # Clear cache with better error handling
        try:
            st.cache_data.clear()
            if 'cached_data' in st.session_state:
                del st.session_state['cached_data']
            st.success("Cache cleared successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing cache: {e}")

# Initialize data service with caching to avoid re-creation on every rerun
@st.cache_resource(ttl=1800, show_spinner=False)  # Reduced TTL for better data freshness
def _get_data_service():
    """Create and cache the ultra-optimised data service (30-minute TTL)."""
    from web.fullstreamlit.utils.data_service_ultra_optimized import create_ultra_optimized_service
    return create_ultra_optimized_service(logger)

try:
    logger.info("Initializing data service (cached)…")
    data_service = _get_data_service()
    
    if data_service is None:
        logger.error("Data service initialization returned None")
        st.error("⚠️ Data service failed to initialize. Please check the logs.")
        st.stop()
    
    logger.info("Data service initialized successfully")
    
    # Verify critical methods exist
    required_methods = ['get_security_intelligence', 'get_home_server_trends_data', 'get_ai_platforms_data']
    missing_methods = []
    for method in required_methods:
        if not hasattr(data_service, method):
            missing_methods.append(method)
    
    if missing_methods:
        logger.warning(f"Data service missing methods: {missing_methods}")
        # Don't stop the app, just log the warning
    
except Exception as e:
    logger.error(f"Failed to initialize data service: {e}")
    st.error(f"⚠️ Failed to initialize data service: {e}")
    st.info("The application will continue with limited functionality.")
    data_service = None

# Load data with improved error handling and optimized caching
@st.cache_data(ttl=600, max_entries=1, show_spinner=True)  # Reduced TTL for more frequent updates
def get_cached_data():
    """Load and cache data with improved error handling"""
    if not data_service:
        logger.error("Data service not available")
        return _get_default_data_structure()
    
    try:
        logger.info("Loading cached meta data (lightweight)…")
        data = {}
        
        # Only light / small datasets are eagerly loaded; heavy ones will be lazy-loaded per tab
        data_loaders = [
            ('allkeyshop', data_service.get_allkeyshop_data),
            ('google_cloud_blog', data_service.get_google_cloud_blog_data),
            ('aws_training', data_service.get_aws_training_data),
            ('azure_training', data_service.get_azure_training_data),
            ('events', data_service.get_events_data),
            ('museums', data_service.get_museum_data),
        ]
        
        # Load data sequentially with individual timeouts
        for data_key, loader_func in data_loaders:
            try:
                logger.info(f"Loading {data_key} data...")
                result = loader_func()
                data[data_key] = result
                logger.info(f"✅ {data_key} data loaded successfully")
            except Exception as e:
                logger.error(f"❌ Error loading {data_key}: {str(e)}")
                data[data_key] = _get_default_empty_value(data_key)
        
        logger.info("All data loading completed")
        return data
        
    except Exception as e:
        logger.error(f"Critical error in get_cached_data: {str(e)}")
        return _get_default_data_structure()


def _get_default_empty_value(data_key: str):
    """Get appropriate default empty value for a data key"""
    if data_key == 'games':
        return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    elif data_key in ['courses', 'news', 'videos']:
        return {}
    elif data_key in ['museums', 'events', 'new_game_releases']:
        return pd.DataFrame()
    else:
        return []


def _get_default_data_structure():
    """Get complete default data structure for app crash prevention"""
    return {
        'allkeyshop': [],
        # Heavy datasets default to empty; they will be lazy-loaded per tab
        'courses': {},
        'news': {},
        'videos': {},
        'events': pd.DataFrame(),
        'google_cloud_blog': [],
        'aws_training': [],
        'azure_training': [],
        'museums': pd.DataFrame(),
    }


# Load cached data with status indicator
with st.spinner("Loading data..."):
    cached_data = get_cached_data()

# Retrieve the new data slices
google_cloud_blog_data = cached_data.get('google_cloud_blog', [])
aws_training_data = cached_data.get('aws_training', [])
azure_training_data = cached_data.get('azure_training', [])
allkeyshop_data = cached_data.get('allkeyshop', [])

# ---------------------------------------------------------------------------
# Lazy tab-specific data loaders (heavy datasets)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1200, show_spinner=True)  # Reduced TTL for better freshness
def load_games_data():
    """Lazy load games datasets (deals, bundles, giveaways, trending)."""
    if data_service:
        return data_service.get_games_data()
    return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

@st.cache_data(ttl=1200, show_spinner=True)  # Reduced TTL for better freshness
def load_new_game_releases():
    """Lazy load new game releases data."""
    if data_service:
        return data_service.get_new_game_releases_data()
    return pd.DataFrame()

@st.cache_data(ttl=1200, show_spinner=True)  # Reduced TTL for better freshness
def load_videos_data():
    """Lazy load videos datasets."""
    if data_service:
        return data_service.get_videos_data()
    return {}

@st.cache_data(ttl=1200, show_spinner=True)  # Reduced TTL for better freshness
def load_courses_data():
    """Lazy load courses datasets."""
    if data_service:
        return data_service.get_courses_data()
    return {}

@st.cache_data(ttl=1200, show_spinner=True)  # Reduced TTL for better freshness
def load_news_data():
    """Lazy load news datasets."""
    if data_service:
        return data_service.get_news_data()
    return {}

# Tabs
main_tabs = st.tabs([
    "📊 Dashboard",
    "📺 Videos",
    "📰 Noticias",
    "☁️ Google Cloud Blog",
    "🎓 AWS Training",      # New tab
    "🔷 Azure Training",    # New tab
    "🎮 Juegos",
    "🎯 AllKeyShop Deals",  # New AllKeyShop tab
    "📚 Cursos",
    "🗓️ Eventos Tech",
    "🧑‍💻 Comunidades Dev",
    "🛡️ Seguridad",
    "💡 Innovación",
    "🤖 Plataformas IA",
    "🏠 Home Server", # New Tab

    "🛒 E-commerce", # Added tab
    "🔬 ArXiv",
    "⛩️ Anime", # New Tab
    "🧠 ADHD Research", # Added ADHD tab
    "📈 Monitoreo",
    "📍 Eventos Valencia",
    "🏛️ Museos Virtuales", # New tab added
    "⚙️ Admin",
    "📑 4chan Generals",
    "⛏️ Scavenging",
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
        st.error(f"Error cargando {tab_name}: {str(e)}")
        st.info("Please try refreshing the data or contact support if the issue persists.")

# Render tabs
with main_tabs[0]:
    render_tab_safely("Dashboard", shortcuts_tab.render, logger, data_service)

with main_tabs[1]:
    videos_data = load_videos_data()
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
    games_data = load_games_data()
    new_releases_df = load_new_game_releases()
    
    if isinstance(games_data, tuple) and len(games_data) == 4:
        deals_df, bundles_df, giveaways_df, trending_df = games_data
        logger.info(f"Games data loaded: deals={len(deals_df)}, bundles={len(bundles_df)}, giveaways={len(giveaways_df)}, trending={len(trending_df)}")
    elif isinstance(games_data, tuple) and len(games_data) == 3:
        deals_df, bundles_df, giveaways_df = games_data
        trending_df = pd.DataFrame()
        logger.info(f"Games data loaded (3-tuple): deals={len(deals_df)}, bundles={len(bundles_df)}, giveaways={len(giveaways_df)}")
    else:
        deals_df = bundles_df = giveaways_df = trending_df = pd.DataFrame()
        logger.warning(f"Games data format unexpected: {type(games_data)} - creating empty dataframes")
    
    render_tab_safely("Juegos", games_tab.render, deals_df, bundles_df, giveaways_df, trending_df, new_releases_df, logger)

with main_tabs[7]: # AllKeyShop Deals
    render_tab_safely("AllKeyShop Deals", allkeyshop_tab.render, allkeyshop_data, logger)

with main_tabs[8]: # Cursos
    courses_data = load_courses_data()
    render_tab_safely("Cursos", courses_tab.render, courses_data, logger)

with main_tabs[9]: # Eventos Tech
    render_tab_safely("Eventos Tech", tech_events_tab.render, logger, data_service)

with main_tabs[10]: # Comunidades Dev
    render_tab_safely("Comunidades Dev", dev_communities_tab.render, logger)

with main_tabs[11]: # Seguridad
    render_tab_safely("Seguridad", security_tab.render, logger, data_service)

with main_tabs[12]: # Innovación
    render_tab_safely("Innovación", enhanced_innovation_tab.render, logger, data_service)

with main_tabs[13]: # Plataformas IA
    render_tab_safely("Plataformas IA", ai_platforms_tab.render, logger)

with main_tabs[14]: # Home Server
    render_tab_safely("Home Server", home_server_tab.render, logger, data_service)

with main_tabs[15]: # E-commerce tab
    render_tab_safely("E-commerce", ecommerce_tab.render, logger)

with main_tabs[16]: # ArXiv
    arxiv_subtabs = st.tabs(["Mejorado", "Papers", "Búsqueda"])
    
    with arxiv_subtabs[0]:
        render_tab_safely("ArXiv Mejorado", enhanced_arxiv_papers.display_enhanced_papers)
    
    with arxiv_subtabs[1]:
        render_tab_safely("Papers ArXiv", arxiv_papers.display)
    
    with arxiv_subtabs[2]:
        render_tab_safely("Búsqueda ArXiv", arxiv_search.display)

with main_tabs[17]: # Index for Anime Tab
    render_tab_safely("Anime Calendar", display_anime_calendar_tab)

with main_tabs[18]: # Index for ADHD Research - NEW TAB
    render_tab_safely("ADHD Research", adhd_tab.display)

with main_tabs[19]: # Index for ExpatCircle News
    render_tab_safely("ExpatCircle News", expatcircle_tab.render, logger)

with main_tabs[20]: # Index for Monitoreo
    render_tab_safely("Monitoreo", monitoring_tab.render, logger)

with main_tabs[21]: # Index for Eventos Valencia
    render_tab_safely("Eventos Valencia", events_tab.render, logger)

with main_tabs[22]: # Index for Museos Virtuales - New tab
    museum_data = cached_data.get('museums', pd.DataFrame())
    render_tab_safely("Museos Virtuales", museums_tab.render, logger, museum_data)

with main_tabs[23]: # Index for Admin
    render_tab_safely("Admin", admin_tab.render, logger)

# New 4chan Generals Tab
with main_tabs[24]:
    render_tab_safely("4chan Generals", chan_generals_tab.render, logger)

# Scavenging Tab
with main_tabs[25]:
    render_tab_safely("Scavenging", scavenging_tab.render, logger)
