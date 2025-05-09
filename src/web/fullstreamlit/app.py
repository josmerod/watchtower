"""
Watchtower Streamlit Application - Main file
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
import json
import numpy as np

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
HUMBLE_BUNDLES_FILE = os.path.join(GAMES_DATA_DIR, "humblebundles.json")

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

    _logger.info("Fetching and processing game deals data")

    deals_df = pd.DataFrame()
    bundles_df = pd.DataFrame()
    giveaways_df = pd.DataFrame()

    try:
        # Load game deals if the file exists
        if os.path.exists(DEALS_FILE):
            with open(DEALS_FILE, "r", encoding="utf-8") as f:
                deals = json.load(f)
                if deals:
                    deals_df = pd.DataFrame(deals)
                    if "published_date" in deals_df.columns:
                        deals_df["published_date"] = pd.to_datetime(deals_df["published_date"]).dt.date
                    
                    # Convert price to numeric if present
                    if "price" in deals_df.columns:
                        deals_df["price"] = pd.to_numeric(
                            deals_df["price"].replace({None: np.nan, "": np.nan}), errors="coerce"
                        )
                    
                    # Calculate discount percentage if not already present
                    if "discount" not in deals_df.columns and "discount_value" in deals_df.columns:
                        deals_df["discount"] = deals_df["discount_value"].map(lambda x: f"-{x}%" if pd.notna(x) else "")
                    
                    # Calculate discount value if not already present
                    if "discount_value" not in deals_df.columns and "discount" in deals_df.columns:
                        deals_df["discount_value"] = deals_df["discount"].str.replace("%", "").str.replace("-", "").replace({None: np.nan, "": np.nan}).astype(float)
                    
                    _logger.info(f"Loaded {len(deals_df)} game deals")
                else:
                    _logger.warning("No game deals found in the data file")

        # Load game bundles if the file exists
        bundles_loaded = False
        
        # First try loading Humble Bundles
        if os.path.exists(HUMBLE_BUNDLES_FILE):
            try:
                with open(HUMBLE_BUNDLES_FILE, "r", encoding="utf-8") as f:
                    bundles = json.load(f)
                    if bundles:
                        # Filter to only include game bundles
                        game_bundles = [b for b in bundles if b.get("type") == "games"]
                        if game_bundles:
                            humble_df = pd.DataFrame(game_bundles)
                            
                            # Rename end_date to published_date for compatibility
                            if "end_date" in humble_df.columns:
                                humble_df = humble_df.rename(columns={"end_date": "published_date"})
                            
                            if "published_date" in humble_df.columns:
                                humble_df["published_date"] = pd.to_datetime(humble_df["published_date"]).dt.date
                            
                            # Add game_count based on games list
                            if "games" in humble_df.columns:
                                humble_df["game_count"] = humble_df["games"].apply(len)
                            
                            # Add store information
                            humble_df["store"] = "Humble Bundle"
                            
                            bundles_df = humble_df
                            bundles_loaded = True
                            _logger.info(f"Loaded {len(humble_df)} Humble Bundle game bundles")
            except Exception as e:
                _logger.error(f"Error loading Humble Bundle data: {str(e)}")
        
        # Then try loading regular bundles if no Humble Bundles were found
        if not bundles_loaded and os.path.exists(BUNDLES_FILE):
            with open(BUNDLES_FILE, "r", encoding="utf-8") as f:
                bundles = json.load(f)
                if bundles:
                    bundles_df = pd.DataFrame(bundles)
                    if "published_date" in bundles_df.columns:
                        bundles_df["published_date"] = pd.to_datetime(bundles_df["published_date"]).dt.date
                    
                    # Convert price to numeric if present
                    if "price" in bundles_df.columns:
                        bundles_df["price"] = pd.to_numeric(
                            bundles_df["price"].replace({None: np.nan, "": np.nan}), errors="coerce"
                        )
                    
                    _logger.info(f"Loaded {len(bundles_df)} game bundles from bundles.json")
                else:
                    _logger.warning("No game bundles found in the data file")

        # Load game giveaways if the file exists
        if os.path.exists(GIVEAWAYS_FILE):
            with open(GIVEAWAYS_FILE, "r", encoding="utf-8") as f:
                giveaways = json.load(f)
                if giveaways:
                    giveaways_df = pd.DataFrame(giveaways)
                    if "published_date" in giveaways_df.columns:
                        giveaways_df["published_date"] = pd.to_datetime(giveaways_df["published_date"]).dt.date
                    
                    if "expires_date" in giveaways_df.columns:
                        giveaways_df["expires_date"] = pd.to_datetime(giveaways_df["expires_date"]).dt.date
                    
                    _logger.info(f"Loaded {len(giveaways_df)} game giveaways")
                else:
                    _logger.warning("No game giveaways found in the data file")

    except Exception as e:
        _logger.error(f"Error loading game data: {str(e)}", exc_info=True)

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
