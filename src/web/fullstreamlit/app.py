"""
Watchtower Streamlit Application - Main file
"""
import streamlit as st
import pandas as pd
import sys
import os
import time
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

# Load data with improved error handling and optimized caching - MINIMAL LOADING FOR PERFORMANCE
@st.cache_data(ttl=600, max_entries=1, show_spinner=True)  # Reduced TTL for more frequent updates
def get_cached_data():
    """Load and cache minimal essential data only for improved performance"""
    if not data_service:
        logger.error("Data service not available")
        return _get_default_data_structure()
    
    try:
        logger.info("Loading minimal cached data for fast startup…")
        data = {}
        
        # PERFORMANCE OPTIMIZATION: Load only absolutely essential lightweight data on startup
        # Heavy datasets will be loaded lazily when their respective tabs are accessed
        essential_loaders = [
            ('allkeyshop', data_service.get_allkeyshop_data),  # Keep this as it's shown in dashboard
            ('google_cloud_blog', data_service.get_google_cloud_blog_data),  # Keep for dashboard
        ]
        
        # Load essential data only
        for data_key, loader_func in essential_loaders:
            try:
                logger.info(f"Loading essential {data_key} data...")
                result = loader_func()
                data[data_key] = result
                logger.info(f"✅ {data_key} data loaded successfully")
            except Exception as e:
                logger.error(f"❌ Error loading {data_key}: {str(e)}")
                data[data_key] = _get_default_empty_value(data_key)
        
        # Set lightweight defaults for other data that will be loaded on-demand
        data.update({
            'aws_training': [],
            'azure_training': [],
            'events': pd.DataFrame(),
            'museums': pd.DataFrame(),
        })
        
        logger.info("Essential data loading completed - faster startup achieved")
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
with st.spinner("Loading essential data..."):
    cached_data = get_cached_data()

# Retrieve the lightweight data that's loaded at startup
google_cloud_blog_data = cached_data.get('google_cloud_blog', [])
allkeyshop_data = cached_data.get('allkeyshop', [])

# ---------------------------------------------------------------------------
# Lazy tab-specific data loaders (heavy datasets) - PERFORMANCE OPTIMIZED
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

# NEW: Lazy loaders for data that was previously loaded at startup
@st.cache_data(ttl=1200, show_spinner=True)
def load_aws_training_data():
    """Lazy load AWS training data."""
    if data_service:
        return data_service.get_aws_training_data()
    return []

@st.cache_data(ttl=1200, show_spinner=True) 
def load_azure_training_data():
    """Lazy load Azure training data."""
    if data_service:
        return data_service.get_azure_training_data()
    return []

@st.cache_data(ttl=1200, show_spinner=True)
def load_events_data():
    """Lazy load events data."""
    if data_service:
        return data_service.get_events_data()
    return pd.DataFrame()

@st.cache_data(ttl=1200, show_spinner=True)
def load_museums_data():
    """Lazy load museums data."""
    if data_service:
        return data_service.get_museum_data()
    return pd.DataFrame()

# Performance optimization: Use selectbox for tab navigation instead of rendering all tabs
tab_names = [
    "📊 Dashboard",
    "📺 Videos", 
    "📰 Noticias",
    "☁️ Google Cloud Blog",
    "🎓 AWS Training",
    "🔷 Azure Training", 
    "🎮 Juegos",
    "🎯 AllKeyShop Deals",
    "📚 Cursos",
    "🗓️ Eventos Tech",
    "🧑‍💻 Comunidades Dev",
    "🛡️ Seguridad", 
    "💡 Innovación",
    "🤖 Plataformas IA",
    "🏠 Home Server",
    "🛒 E-commerce",
    "🔬 ArXiv",
    "⛩️ Anime",
    "🧠 ADHD Research",
    "🌍 ExpatCircle",
    "📈 Monitoreo",
    "📍 Eventos Valencia", 
    "🏛️ Museos Virtuales",
    "⚙️ Admin",
    "📑 4chan Generals",
    "⛏️ Scavenging",
]

# Initialize performance tracking
from web.fullstreamlit.utils.performance import tracker, setup_session_state_defaults
from web.fullstreamlit.utils.memory_optimizer import memory_optimizer, monitor_memory_usage, optimize_app_memory
setup_session_state_defaults()

# Run initial memory optimization
optimize_app_memory()

# Performance-optimized tab selection
col1, col2 = st.columns([2, 8])
with col1:
    selected_tab = st.selectbox(
        "Seleccionar sección:",
        tab_names,
        index=st.session_state.get('current_tab_index', 0),
        key='tab_selector'
    )
    
    # Store current tab index
    if 'current_tab_index' not in st.session_state:
        st.session_state.current_tab_index = 0
    
    current_index = tab_names.index(selected_tab)
    if current_index != st.session_state.current_tab_index:
        st.session_state.current_tab_index = current_index
        st.rerun()

with col2:
    st.markdown(f"### {selected_tab}")

# Performance monitoring
start_time = time.time()

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

# Lazy tab rendering - only render the active tab for better performance
@tracker.time_function("render_active_tab")
def render_active_tab(tab_index):
    """Render only the currently active tab"""
    try:
        if tab_index == 0:  # Dashboard
            render_tab_safely("Dashboard", shortcuts_tab.render, logger, data_service)
        
        elif tab_index == 1:  # Videos
            with st.spinner("Cargando datos de videos..."):
                videos_data = load_videos_data()
            render_tab_safely("Videos", videos_tab.render, logger, videos_data)
        
        elif tab_index == 2:  # Noticias
            render_tab_safely("Noticias", news_tab.render, logger)
        
        elif tab_index == 3:  # Google Cloud Blog
            render_tab_safely("Google Cloud Blog", google_cloud_blog_tab.render, logger, google_cloud_blog_data)
        
        elif tab_index == 4:  # AWS Training
            with st.spinner("Cargando datos de AWS Training..."):
                aws_training_data = load_aws_training_data()
            render_tab_safely("AWS Training", aws_training_tab.render, logger, aws_training_data)
        
        elif tab_index == 5:  # Azure Training
            with st.spinner("Cargando datos de Azure Training..."):
                azure_training_data = load_azure_training_data()
            render_tab_safely("Azure Training", azure_training_tab.render, logger, azure_training_data)
        
        elif tab_index == 6:  # Juegos
            with st.spinner("Cargando datos de juegos..."):
                games_data = load_games_data()
                new_releases_df = load_new_game_releases()
            
            if isinstance(games_data, tuple) and len(games_data) == 4:
                deals_df, bundles_df, giveaways_df, allkeyshop_df = games_data
                logger.info(f"Games data loaded: deals={len(deals_df)}, bundles={len(bundles_df)}, giveaways={len(giveaways_df)}, allkeyshop={len(allkeyshop_df)}")
            elif isinstance(games_data, tuple) and len(games_data) == 3:
                deals_df, bundles_df, giveaways_df = games_data
                allkeyshop_df = pd.DataFrame()
                logger.info(f"Games data loaded (3-tuple): deals={len(deals_df)}, bundles={len(bundles_df)}, giveaways={len(giveaways_df)}")
            else:
                deals_df = bundles_df = giveaways_df = allkeyshop_df = pd.DataFrame()
                logger.warning(f"Games data format unexpected: {type(games_data)} - creating empty dataframes")
            
            # Create empty trending_df for backward compatibility
            trending_df = pd.DataFrame()
            render_tab_safely("Juegos", games_tab.render, deals_df, bundles_df, giveaways_df, trending_df, new_releases_df, allkeyshop_df, logger)
        
        elif tab_index == 7:  # AllKeyShop Deals
            render_tab_safely("AllKeyShop Deals", allkeyshop_tab.render, allkeyshop_data, logger)
        
        elif tab_index == 8:  # Cursos
            with st.spinner("Cargando datos de cursos..."):
                courses_data = load_courses_data()
            render_tab_safely("Cursos", courses_tab.render, courses_data, logger)
        
        elif tab_index == 9:  # Eventos Tech
            render_tab_safely("Eventos Tech", tech_events_tab.render, logger, data_service)
        
        elif tab_index == 10:  # Comunidades Dev
            render_tab_safely("Comunidades Dev", dev_communities_tab.render, logger)
        
        elif tab_index == 11:  # Seguridad
            render_tab_safely("Seguridad", security_tab.render, logger, data_service)
        
        elif tab_index == 12:  # Innovación
            render_tab_safely("Innovación", enhanced_innovation_tab.render, logger, data_service)
        
        elif tab_index == 13:  # Plataformas IA
            render_tab_safely("Plataformas IA", ai_platforms_tab.render, logger)
        
        elif tab_index == 14:  # Home Server
            render_tab_safely("Home Server", home_server_tab.render, logger, data_service)
        
        elif tab_index == 15:  # E-commerce
            render_tab_safely("E-commerce", ecommerce_tab.render, logger)
        
        elif tab_index == 16:  # ArXiv
            arxiv_subtabs = st.tabs(["Mejorado", "Papers", "Búsqueda"])
            
            with arxiv_subtabs[0]:
                render_tab_safely("ArXiv Mejorado", enhanced_arxiv_papers.display_enhanced_papers)
            
            with arxiv_subtabs[1]:
                render_tab_safely("Papers ArXiv", arxiv_papers.display)
            
            with arxiv_subtabs[2]:
                render_tab_safely("Búsqueda ArXiv", arxiv_search.display)
        
        elif tab_index == 17:  # Anime
            render_tab_safely("Anime Calendar", display_anime_calendar_tab)
        
        elif tab_index == 18:  # ADHD Research
            render_tab_safely("ADHD Research", adhd_tab.display)
        
        elif tab_index == 19:  # ExpatCircle
            render_tab_safely("ExpatCircle News", expatcircle_tab.render, logger)
        
        elif tab_index == 20:  # Monitoreo
            render_tab_safely("Monitoreo", monitoring_tab.render, logger)
        
        elif tab_index == 21:  # Eventos Valencia
            render_tab_safely("Eventos Valencia", events_tab.render, logger)
        
        elif tab_index == 22:  # Museos Virtuales
            with st.spinner("Cargando datos de museos..."):
                museum_data = load_museums_data()
            render_tab_safely("Museos Virtuales", museums_tab.render, logger, museum_data)
        
        elif tab_index == 23:  # Admin
            render_tab_safely("Admin", admin_tab.render, logger)
        
        elif tab_index == 24:  # 4chan Generals
            render_tab_safely("4chan Generals", chan_generals_tab.render, logger)
        
        elif tab_index == 25:  # Scavenging
            render_tab_safely("Scavenging", scavenging_tab.render, logger)
        
        else:
            st.error(f"Tab index {tab_index} not implemented")
    
    except Exception as e:
        logger.error(f"Error rendering tab {tab_index}: {str(e)}")
        st.error(f"Error cargando la sección: {str(e)}")
        st.info("Por favor, intenta refrescar los datos o contacta con soporte si el problema persiste.")

# Render the currently selected tab
current_tab_index = st.session_state.get('current_tab_index', 0)
render_active_tab(current_tab_index)

# Performance reporting
end_time = time.time()
render_time = end_time - start_time

# Show performance metrics in sidebar
with st.sidebar:
    st.subheader("📊 Performance Metrics")
    st.metric("Tab Render Time", f"{render_time:.3f}s")
    
    # Memory usage
    try:
        memory_stats = memory_optimizer.get_memory_usage()
        st.metric("Memory Usage", f"{memory_stats['rss_mb']:.1f} MB")
        st.metric("Memory %", f"{memory_stats['percent']:.1f}%")
    except Exception as e:
        st.info("Memory monitoring unavailable")
    
    # Get average performance metrics
    avg_dashboard = tracker.get_average_time("render_active_tab")
    if avg_dashboard > 0:
        st.metric("Avg Render Time", f"{avg_dashboard:.3f}s")
    
    # Cache status
    if data_service and hasattr(data_service, 'get_cache_stats'):
        try:
            cache_stats = data_service.get_cache_stats()
            st.metric("Cache Entries", cache_stats.get("memory_cache_size", 0))
        except Exception:
            pass
    
    # Performance report button
    if st.button("📈 Show Performance Report"):
        perf_report = tracker.get_performance_report()
        if perf_report:
            st.json(perf_report)
        else:
            st.info("No performance data available yet")
    
    # Cache clear button for performance
    if st.button("🧹 Clear All Caches"):
        try:
            st.cache_data.clear()
            if data_service and hasattr(data_service, 'clear_cache'):
                data_service.clear_cache()
            st.success("All caches cleared!")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing caches: {e}")
    
    # Memory optimization button
    if st.button("💾 Optimize Memory"):
        try:
            gc_stats = memory_optimizer.force_garbage_collection()
            cleaned_sessions = memory_optimizer.cleanup_session_state()
            st.success(f"Freed {gc_stats['freed_objects']} objects")
            st.info(f"Cleaned {cleaned_sessions} session items")
            st.rerun()
        except Exception as e:
            st.error(f"Error optimizing memory: {e}")
