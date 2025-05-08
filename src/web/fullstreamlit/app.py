"""
Watchtower Streamlit Application - Main file
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
import json

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import utilities from our modules
from src.utils.logging import get_logger
from src.web.fullstreamlit.styles.main import get_main_style
from src.web.fullstreamlit.utils.helpers import make_clickable, format_timestamp, clean_url, get_responsive_cols
from src.web.fullstreamlit.utils.data_loader import load_courses_data

# Import all components
from src.web.fullstreamlit.components import (
    shortcuts_tab,
    videos_tab,
    news_tab,
    games_tab,
    courses_tab,
    watchers_tab,
    events_tab,
    admin_tab,
    arxiv_papers,
    arxiv_search
)

# Define data paths
GAMES_DATA_DIR = "../../../data/games"
DEALS_FILE = os.path.join(GAMES_DATA_DIR, "deals.json")
BUNDLES_FILE = os.path.join(GAMES_DATA_DIR, "bundles.json")
GIVEAWAYS_FILE = os.path.join(GAMES_DATA_DIR, "giveaways.json")

# Define local data loading functions
def load_data(file_path, _logger=None):
    """Load data from JSON file with error handling"""
    try:
        if os.path.exists(file_path):
            if _logger:
                _logger.info(f"Loading data from {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            if _logger:
                _logger.info(f"Successfully loaded {len(df)} records from {file_path}")
            return df
        else:
            if _logger:
                _logger.error(f"File not found: {file_path}")
            st.error(f"Archivo no encontrado: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        if _logger:
            _logger.error(f"Error loading data from {file_path}: {str(e)}")
        st.error(f"Error al cargar datos desde {file_path}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_game_data(_logger=None):
    """Fetch and process game deals data"""
    if _logger:
        _logger.info("Fetching and processing game deals data")
    
    # Load data files
    deals_df = load_data(DEALS_FILE, _logger)
    bundles_df = load_data(BUNDLES_FILE, _logger)
    giveaways_df = load_data(GIVEAWAYS_FILE, _logger)

    # Process deals data
    if not deals_df.empty:
        if _logger:
            _logger.info("Processing deals data")
        # Convert timestamps to datetime
        if "published" in deals_df.columns:
            deals_df["published_date"] = deals_df["published"].apply(format_timestamp)

        # Extract discount percentage as numeric value
        if "discount" in deals_df.columns:
            deals_df["discount_value"] = (
                deals_df["discount"]
                .str.replace("-", "")
                .str.replace("%", "")
                .astype(float, errors="ignore")
            )

    # Process bundles data
    if not bundles_df.empty:
        if _logger:
            _logger.info("Processing bundles data")
        # Convert timestamps to datetime
        if "published" in bundles_df.columns:
            bundles_df["published_date"] = bundles_df["published"].apply(
                format_timestamp
            )

        # Count games in each bundle
        if "games" in bundles_df.columns:
            bundles_df["game_count"] = bundles_df["games"].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )

    # Process giveaways data
    if not giveaways_df.empty:
        if _logger:
            _logger.info("Processing giveaways data")
        # Convert timestamps to datetime
        if "published" in giveaways_df.columns:
            giveaways_df["published_date"] = giveaways_df["published"].apply(
                format_timestamp
            )

        if "expires" in giveaways_df.columns:
            giveaways_df["expires_date"] = giveaways_df["expires"].apply(
                format_timestamp
            )

            # Calculate if giveaway is still active
            current_time = datetime.now().timestamp()
            giveaways_df["is_active"] = giveaways_df["expires"].apply(
                lambda x: x > current_time * 1000
                if isinstance(x, (int, float)) and not pd.isna(x)
                else False
            )

            active_count = giveaways_df["is_active"].sum()
            if _logger:
                _logger.info(f"Found {active_count} active giveaways")

    if _logger:
        _logger.info("Data processing completed")
    return deals_df, bundles_df, giveaways_df

@st.cache_data(ttl=3600)
def get_courses_data(_logger=None):
    """Fetch and process courses data"""
    if _logger:
        _logger.info("Fetching and processing courses data")
    
    try:
        # Load courses data from different platforms using the utility
        courses_data = load_courses_data()
        
        if _logger:
            platforms = ', '.join(courses_data.keys()) if courses_data else "none"
            course_counts = {k: len(v) for k, v in courses_data.items()} if courses_data else {}
            _logger.info(f"Loaded courses data from platforms: {platforms}")
            _logger.info(f"Course counts by platform: {course_counts}")
        
        return courses_data
    except Exception as e:
        if _logger:
            _logger.error(f"Error loading courses data: {str(e)}")
        # Return empty dict if there's an error
        return {}

# Initialize logger for the Streamlit app
logger = get_logger("GameDealsApp")

# Set page configuration - MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="Watchtower: Monitor de Tendencias y Noticias",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply CSS styles
st.markdown(get_main_style(), unsafe_allow_html=True)

# Add JavaScript to get viewport width
st.markdown("""
    <script>
        // Function to update viewport width
        function updateViewportWidth() {
            const width = window.innerWidth;
            localStorage.setItem('viewportWidth', width);
        }
        
        // Update on load and resize
        window.addEventListener('load', updateViewportWidth);
        window.addEventListener('resize', updateViewportWidth);
    </script>
""", unsafe_allow_html=True)

# Get viewport width from localStorage
if 'viewport_width' not in st.session_state:
    st.session_state.viewport_width = 1200  # Default value

# Title and introduction
st.title("🗼 Watchtower: Monitor de Tendencias y Noticias")
st.markdown(
    """
<div class="card" style="background-color: #2D2B55; padding: 18px; border-radius: 8px; border-left: 5px solid #A37FFF; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);">
    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #E2E8F0;">Las paridas de Josele presentan el panel de Watchtower, un monitor de tendencias y noticias en el mundo del Generative AI y Dev. Si, se me ha ido un poco de las manos...</p>
</div>
""",
    unsafe_allow_html=True,
)

# Create tabs for different data views
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🔖 Accesos Directos", 
    "📺 Videos", 
    "📰 Noticias", 
    "🎮 Juegos",
    "🎓 Cursos",
    "👁️ Watchers", 
    "🏙️ Eventos Valencia", 
    "📚 ArXiv Papers",
    "🔍 Búsqueda ArXiv",
    "⚙️ Admin"
])

# Render each tab
with tab0:
    logger.info("Rendering Shortcuts tab")
    shortcuts_tab.render(logger)

with tab1:
    logger.info("Rendering Videos tab")
    videos_tab.render(logger)

with tab2:
    logger.info("Rendering Noticias tab")
    news_tab.render(logger)

with tab3:
    logger.info("Rendering Juegos tab")
    # Load game data for this tab
    deals_df, bundles_df, giveaways_df = get_game_data(_logger=logger)
    games_tab.render(deals_df, bundles_df, giveaways_df, logger)

with tab4:
    logger.info("Rendering Cursos tab")
    # Load courses data for this tab
    courses_data = get_courses_data(_logger=logger)
    courses_tab.render(courses_data, logger)

with tab5:
    logger.info("Rendering Watchers tab")
    watchers_tab.render(logger)

with tab6:
    logger.info("Rendering Valencia Events tab")
    events_tab.render(logger)

with tab7:
    logger.info("Rendering ArXiv Papers tab")
    arxiv_papers.display()

with tab8:
    logger.info("Rendering ArXiv Search tab")
    arxiv_search.display()

with tab9:
    logger.info("Rendering Admin tab")
    admin_tab.render(logger)

# Footer
st.markdown(
    """
<div style="text-align: center; margin-top: 30px; padding: 20px; opacity: 0.9; background-color: #2D2B55; border-radius: 8px; box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3); border-top: 3px solid #A37FFF;">
    <p style="font-family: 'Poppins', sans-serif; color: #E2E8F0; font-size: 14px;">Datos obtenidos de <a href="https://isthereanydeal.com/" target="_blank">IsThereAnyDeal</a>, <a href="https://futuretools.io/news" target="_blank">FutureTools.io</a>, <a href="https://www.medium.com/" target="_blank">Medium</a>, <a href="https://arxiv.org/" target="_blank">ArXiv</a> y <a href="https://www.youtube.com/" target="_blank">Youtube</a></p>
</div>
""",
    unsafe_allow_html=True,
)
logger.info("Dashboard rendering completed")
