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
    museums_tab # Added import for museums_tab
)

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
        data['museums'] = data_service.get_museum_data() # Added museum data loading
        return data
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return {}

cached_data = get_cached_data()

# Tabs
main_tabs = st.tabs([
    "Dashboard", 
    "Videos", 
    "Noticias", 
    "Juegos",
    "Cursos",
    "Eventos Tech",
    "Comunidades Dev",
    "Seguridad",
    "Innovación",
    "Plataformas IA",
    "Crypto",
    "ArXiv", 
    "Monitoreo", 
    "Eventos Valencia",
    "Museos Virtuales", # New tab added
    "Admin"
])

# Define the expected order of tab titles for robust index finding
# This list should exactly match the list passed to st.tabs above
EXPECTED_TAB_TITLES = [
    "Dashboard", "Videos", "Noticias", "Juegos", "Cursos",
    "Eventos Tech", "Comunidades Dev", "Seguridad", "Innovación",
    "Plataformas IA", "Crypto", "ArXiv", "Monitoreo",
    "Eventos Valencia", "Museos Virtuales", "Admin"
]

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

with main_tabs[3]:
    games_data = cached_data.get('games', (pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
    if isinstance(games_data, tuple) and len(games_data) == 3:
        deals_df, bundles_df, giveaways_df = games_data
    else:
        deals_df = bundles_df = giveaways_df = pd.DataFrame()
    render_tab_safely("Juegos", games_tab.render, deals_df, bundles_df, giveaways_df, logger)

with main_tabs[4]:
    courses_data = cached_data.get('courses', {})
    render_tab_safely("Cursos", courses_tab.render, courses_data, logger)

with main_tabs[5]:
    render_tab_safely("Eventos Tech", tech_events_tab.render, logger, data_service)

with main_tabs[6]:
    render_tab_safely("Comunidades Dev", dev_communities_tab.render, logger)

with main_tabs[7]:
    render_tab_safely("Seguridad", security_tab.render, logger, data_service)

with main_tabs[8]:
    render_tab_safely("Innovación", enhanced_innovation_tab.render, logger, data_service)

with main_tabs[9]:
    render_tab_safely("Plataformas IA", ai_platforms_tab.render, logger)

with main_tabs[10]:
    render_tab_safely("Crypto", crypto_tab.render, logger)

with main_tabs[11]:
    arxiv_subtabs = st.tabs(["Mejorado", "Papers", "Búsqueda"])
    
    with arxiv_subtabs[0]:
        render_tab_safely("ArXiv Mejorado", enhanced_arxiv_papers.display_enhanced_papers)
    
    with arxiv_subtabs[1]:
        render_tab_safely("Papers ArXiv", arxiv_papers.display)
    
    with arxiv_subtabs[2]:
        render_tab_safely("Búsqueda ArXiv", arxiv_search.display)

with main_tabs[12]:
    render_tab_safely("Monitoreo", monitoring_tab.render, logger)

with main_tabs[EXPECTED_TAB_TITLES.index("Eventos Valencia")]: # Index 13
    render_tab_safely("Eventos Valencia", events_tab.render, logger)

with main_tabs[EXPECTED_TAB_TITLES.index("Museos Virtuales")]: # Index 14 - New tab
    museum_data = cached_data.get('museums', pd.DataFrame())
    render_tab_safely("Museos Virtuales", museums_tab.render, logger, museum_data)

with main_tabs[EXPECTED_TAB_TITLES.index("Admin")]: # Index 15 - Shifted Admin tab
    render_tab_safely("Admin", admin_tab.render, logger)
