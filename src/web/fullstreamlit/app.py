import subprocess
import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
import plotly.express as px
from urllib.parse import unquote
import sys

# Set page configuration - MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="Watchtower: Monitor de Tendencias y Noticias",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger

# Initialize logger for the Streamlit app
logger = get_logger("GameDealsApp")

# Function to determine number of columns based on screen width
def get_responsive_cols():
    # Get the current viewport width using JavaScript
    viewport_width = st.session_state.get('viewport_width', 1200)  # Default to 1200px
    
    if viewport_width >= 1200:
        return 6  # Large screens
    elif viewport_width >= 992:
        return 4  # Medium-large screens
    elif viewport_width >= 768:
        return 3  # Medium screens
    elif viewport_width >= 576:
        return 2  # Small screens
    else:
        return 1  # Extra small screens

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

# Define data paths
GAMES_DATA_DIR = "../../../data/games"

FUTURETOOLS_NEWS_DATA_DIR = "../../../data/futuretools"
YCOMBINATOR_NEWS_DATA_DIR = "../../../data/hackernews"
MEDIUM_NEWS_DATA_DIR = "../../../data/medium_genai"
BENSBITES_NEWS_DATA_DIR = "../../../data/bensbites"

VIDEOS_DATA_DIR = "../../../data/youtube"

WATCHERS_DATA_DIR = "../../../data/watchers"

DEALS_FILE = os.path.join(GAMES_DATA_DIR, "deals.json")
BUNDLES_FILE = os.path.join(GAMES_DATA_DIR, "bundles.json")
GIVEAWAYS_FILE = os.path.join(GAMES_DATA_DIR, "giveaways.json")

FUTURETOOLS_NEWS_FILE = os.path.join(FUTURETOOLS_NEWS_DATA_DIR, "futuretoolsnews.json")
YCOMBINATOR_NEWS_FILE = os.path.join(YCOMBINATOR_NEWS_DATA_DIR, "hackernews.json")
MEDIUM_NEWS_FILE = os.path.join(MEDIUM_NEWS_DATA_DIR, "medium_genai.json")
BENSBITES_NEWS_FILE = os.path.join(BENSBITES_NEWS_DATA_DIR, "bensbites_news.json")

DEV_VIDEOS_FILE = os.path.join(VIDEOS_DATA_DIR, "dev", "youtube_videos.json")
PERSONAL_DEV_VIDEOS_FILE = os.path.join(VIDEOS_DATA_DIR, "personal_development", "youtube_videos.json")
ECONOMICS_VIDEOS_FILE = os.path.join(VIDEOS_DATA_DIR, "economics", "youtube_videos.json")

# Log application startup
logger.info("Starting Watchtower Dashboard")

# Apply custom styling
st.markdown("""
<style>
    /* Import Google Fonts - Poppins */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    /* Main app background and text */
    .stApp {
        background-color: #1E1E2E !important;
        color: #E2E8F0;
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #A37FFF !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
    }
    
    /* Body text */
    p, div, span, li {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 400;
        line-height: 1.6;
        color: #E2E8F0;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: #2D2B55;
        border-radius: 8px 8px 0 0;
        padding: 5px 5px 0 5px;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #2D2B55;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #CCC6F2;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500;
        transition: all 0.3s ease;
        white-space: nowrap;
        min-width: auto;
    }
    .stTabs [aria-selected="true"] {
        background-color: #A37FFF !important;
        color: #1E1E2E !important;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(163, 127, 255, 0.2);
    }
    
    /* Responsive tables */
    .stDataFrame {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    table {
        background-color: #2D2B55 !important;
        border-collapse: collapse;
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        font-family: 'Poppins', sans-serif !important;
        min-width: 600px; /* Ensure minimum width for readability */
    }
    
    /* Responsive cards */
    .video-card {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        transition: transform 0.2s;
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Responsive grid container */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        width: 100%;
    }
    
    /* Media queries for responsive layout */
    @media screen and (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            padding: 8px 12px;
            font-size: 0.9rem;
        }
        
        table {
            font-size: 0.9rem;
        }
        
        th, td {
            padding: 8px;
        }
        
        .video-card {
            padding: 10px;
        }
    }
    
    @media screen and (max-width: 480px) {
        .stTabs [data-baseweb="tab"] {
            padding: 6px 10px;
            font-size: 0.8rem;
        }
        
        table {
            font-size: 0.8rem;
        }
        
        th, td {
            padding: 6px;
        }
    }
    
    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc {
        background-color: #2D2B55 !important;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #A37FFF !important;
        color: #1E1E2E !important;
        border: none !important;
        border-radius: 6px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #B792FF !important;
        box-shadow: 0 4px 8px rgba(163, 127, 255, 0.3);
        transform: translateY(-2px);
    }
    
    /* Cards and tables */
    .card, div.stDataFrame {
        background-color: #2D2B55 !important;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        border-left: 3px solid #A37FFF;
    }
    
    /* Table styling */
    th {
        background-color: #3C3970 !important;
        color: #E2E8F0 !important;
        padding: 12px;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.85em;
        letter-spacing: 0.5px;
    }
    td {
        padding: 10px 12px;
        border-bottom: 1px solid #3C3970;
        vertical-align: middle;
        color: #E2E8F0;
    }
    tr:nth-child(even) {
        background-color: #252343 !important;
    }
    tr:hover {
        background-color: #34325A !important;
    }
    
    /* Input fields */
    .stTextInput input, .stDateInput input, .stSelectbox select {
        border-radius: 6px !important;
        border: 1px solid #3C3970 !important;
        background-color: #252343 !important;
        color: #E2E8F0 !important;
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* Links */
    a {
        color: #A37FFF !important;
        text-decoration: none;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    a:hover {
        color: #B792FF !important;
        text-decoration: underline;
    }
    
    /* Custom scrollbar for better UX */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1E1E2E;
    }
    ::-webkit-scrollbar-thumb {
        background: #3C3970;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #A37FFF;
    }
    
    /* Warning messages */
    .stAlert {
        background-color: #3C3970 !important;
        color: #E2E8F0 !important;
    }
    
    /* Dropdown elements */
    .stSelectbox > div[data-baseweb="select"] > div {
        background-color: #252343 !important;
        color: #E2E8F0 !important;
    }
    
    /* Date input */
    .stDateInput > div[data-baseweb="input"] > div {
        background-color: #252343 !important;
        color: #E2E8F0 !important;
    }
    
    /* Success messages */
    div[data-testid="stSuccessMessage"] {
        background-color: #2D2B55 !important;
        color: #A5FFAF !important;
        border-color: #A5FFAF !important;
    }
</style>
""", unsafe_allow_html=True)


# Helper functions
@st.cache_data(ttl=3600)
def load_data(file_path):
    """Load data from JSON file with error handling"""
    try:
        if os.path.exists(file_path):
            logger.info(f"Loading data from {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            logger.info(f"Successfully loaded {len(df)} records from {file_path}")
            return df
        else:
            logger.error(f"File not found: {file_path}")
            st.error(f"Archivo no encontrado: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {str(e)}")
        st.error(f"Error al cargar datos desde {file_path}: {str(e)}")
        return pd.DataFrame()

# Load videos data
@st.cache_data(ttl=3600)
def get_videos_data(file_path):
    """Fetch and process videos data"""
    logger.info("Loading videos data")
    videos_df = load_data(file_path)

    if not videos_df.empty:
        videos_df["published_date"] = pd.to_datetime(videos_df["published_at"])
        # Add thumbnail URLs if available
        if "thumbnail_url" in videos_df.columns:
            videos_df["thumbnail"] = videos_df["thumbnail_url"]

    return videos_df


def format_timestamp(timestamp):
    """Convert timestamp to readable date format"""
    try:
        if pd.isna(timestamp):
            return "N/A"
        # Convert milliseconds to seconds if needed
        if timestamp > 1e11:  # Likely milliseconds
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        logger.warning(f"Failed to format timestamp {timestamp}: {str(e)}")
        return "Fecha inválida"


def clean_url(url):
    """Clean and format URL for display"""
    if pd.isna(url):
        return "N/A"
    try:
        return unquote(url.replace("\\", ""))
    except Exception as e:
        logger.warning(f"Failed to clean URL {url}: {str(e)}")
        return url


def make_clickable(link, text=None):
    """Create clickable link for dataframe"""
    if pd.isna(link):
        return "N/A"
    text = text if text else clean_url(link)
    return f'<a href="{clean_url(link)}" target="_blank">{text}</a>'


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


# Load data
@st.cache_data(ttl=3600)
def get_data():
    logger.info("Fetching and processing game deals data")
    # Use the global data paths defined earlier
    deals_df = load_data(DEALS_FILE)
    bundles_df = load_data(BUNDLES_FILE)
    giveaways_df = load_data(GIVEAWAYS_FILE)

    # Process deals data
    if not deals_df.empty:
        logger.info("Processing deals data")
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
        logger.info("Processing bundles data")
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
        logger.info("Processing giveaways data")
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
            logger.info(f"Found {active_count} active giveaways")

    logger.info("Data processing completed")
    return deals_df, bundles_df, giveaways_df


logger.info("Loading and preparing data")
deals_df, bundles_df, giveaways_df = get_data()
logger.info(
    f"Data loaded: {len(deals_df)} deals, {len(bundles_df)} bundles, {len(giveaways_df)} giveaways"
)

# Create tabs for different data views
tab3, tab2, tab1, tab4, tab5, tab6 = st.tabs(["📺 Videos Programación e IA", "📰 Noticias", "🎮 Juegos", "📺 Videos Desarrollo personal", "📺 Videos Ecopolitica", "👁️ Watchers"])

with tab1:  # Juegos
    logger.info("Rendering Summary subtab")
    st.header("Resumen de Ofertas")

    # Add a button to call the script to scrape the data
    if st.button("(Re)cargar datos de ofertas"):
        logger.info("Cargando datos de ofertas...")
        # Call the script to scrape the data and wait until it is finished
        subprocess.run(["python3", "../../../src/etl/games/games_get_deals.py"])
        # Wait until the script is finished

        logger.info("Data scraped successfully")
        st.success("Data scraped successfully")
        # Refresh the data
        deals_df, bundles_df, giveaways_df = get_data()
        logger.info("Data refreshed successfully")
        # Refresh the page
        st.rerun()

    if deals_df.empty:
        logger.warning("No deals data available to display")
        st.warning("No hay datos de ofertas disponibles.")

    else:
        # Calculate summary statistics
        total_deals = len(deals_df)
        total_bundles = len(bundles_df)
        total_giveaways = len(giveaways_df)

        # Add responsive container CSS for deals
        st.markdown("""
            <style>
            .deals-container {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            
            @media (min-width: 992px) {
                .deals-container {
                    flex-direction: row;
                }
                
                .deals-column {
                    flex: 1;
                    min-width: 0;
                }
            }
            
            .deals-card {
                background-color: #2D2B55;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
                border-left: 3px solid #A37FFF;
            }
            
            @media (max-width: 992px) {
                .deals-card {
                    margin: 10px 0;
                }
                
                .stDataFrame {
                    max-height: none !important;
                }
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="deals-container">', unsafe_allow_html=True)

        # Display deals in responsive columns
        st.markdown('<div class="deals-column">', unsafe_allow_html=True)
        with st.container():
            st.header("Ofertas de Juegos")
            filtered_deals_df = deals_df.copy()
            filtered_deals_df = filtered_deals_df.sort_values(by="discount_value", ascending=False)
            display_deals_df = filtered_deals_df[["title", "price", "discount", "store", "published_date"]].copy()
            display_deals_df["Ver Oferta"] = filtered_deals_df["link"].apply(lambda x: make_clickable(x, "Ver"))
            
            if "price" in display_deals_df.columns:
                display_deals_df["price"] = display_deals_df["price"].apply(
                    lambda x: f"€{x:.2f}" if pd.notna(x) else "N/A"
                )
            
            display_deals_df.rename(
                columns={
                    "title": "Título",
                    "price": "Precio",
                    "discount": "Descuento",
                    "store": "Tienda",
                    "published_date": "Fecha de Publicación",
                },
                inplace=True,
            )
            
            st.markdown(
                '<div class="deals-card">' + 
                display_deals_df.to_html(escape=False, index=False) +
                '</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

        # Display bundles in responsive columns
        st.markdown('<div class="deals-column">', unsafe_allow_html=True)
        with st.container():
            st.header("Paquetes de Juegos")
            if not bundles_df.empty:
                filtered_bundles_df = bundles_df.copy()
                filtered_bundles_df = filtered_bundles_df.sort_values(by="published_date", ascending=False)
                
                if "game_count" in filtered_bundles_df.columns:
                    display_bundles_df = filtered_bundles_df[["title", "price", "game_count", "published_date"]].copy()
                else:
                    display_bundles_df = filtered_bundles_df[["title", "price", "published_date"]].copy()
                
                display_bundles_df["Ver Paquete"] = filtered_bundles_df["link"].apply(lambda x: make_clickable(x, "Ver"))
                
                if "price" in display_bundles_df.columns:
                    display_bundles_df["price"] = display_bundles_df["price"].apply(
                        lambda x: f"€{x:.2f}" if pd.notna(x) else "N/A"
                    )
                
                display_bundles_df.rename(
                    columns={
                        "title": "Título",
                        "price": "Precio",
                        "game_count": "Juegos en el Paquete",
                        "published_date": "Fecha de Publicación"
                    },
                    inplace=True,
                )
                
                st.markdown(
                    '<div class="deals-card">' + 
                    display_bundles_df.to_html(escape=False, index=False) +
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No hay datos de paquetes disponibles.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Display giveaways in responsive columns
        st.markdown('<div class="deals-column">', unsafe_allow_html=True)
        with st.container():
            st.header("Juegos Gratuitos")
            if not giveaways_df.empty:
                filtered_giveaways_df = giveaways_df.copy()
                
                if "expires_date" in filtered_giveaways_df.columns:
                    display_giveaways_df = filtered_giveaways_df[["title", "published_date", "expires_date"]].copy()
                else:
                    display_giveaways_df = filtered_giveaways_df[["title", "published_date"]].copy()
                
                display_giveaways_df["Obtener Juego"] = filtered_giveaways_df["link"].apply(
                    lambda x: make_clickable(x, "Reclamar")
                )
                
                display_giveaways_df.rename(
                    columns={
                        "title": "Título",
                        "published_date": "Fecha de Publicación",
                        "expires_date": "Fecha de Expiración"
                    },
                    inplace=True,
                )
                
                st.markdown(
                    '<div class="deals-card">' + 
                    display_giveaways_df.to_html(escape=False, index=False) +
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No hay datos de juegos gratuitos disponibles.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


with tab2:

    @st.cache_data(ttl=3600)
    def get_news_data():
        """Fetch and process news data"""
        logger.info("Loading news data")
        futuretools_news_df = load_data(FUTURETOOLS_NEWS_FILE)
        ycombinator_news_df = load_data(YCOMBINATOR_NEWS_FILE)
        medium_news_df = load_data(MEDIUM_NEWS_FILE)
        bensbites_news_df = load_data(BENSBITES_NEWS_FILE)

        if not futuretools_news_df.empty:
            futuretools_news_df["published_date"] = pd.to_datetime(
                futuretools_news_df["published_at"]
            )

        if not ycombinator_news_df.empty:
            ycombinator_news_df["published_date"] = pd.to_datetime(
                ycombinator_news_df["published_at"]
            )

        if not bensbites_news_df.empty:
            bensbites_news_df["published_date"] = pd.to_datetime(
                bensbites_news_df["published_at"]
            )

        return futuretools_news_df, ycombinator_news_df, medium_news_df, bensbites_news_df

    logger.info("Rendering News tab")
    st.header("📰 Noticias Generative AI")

    # Add a button to call the script to scrape the data
    if st.button("(Re)cargar datos de noticias"):
        logger.info("Cargando datos de noticias...")
        # Call the script to scrape the data and wait until it is finished
        subprocess.run(["python3", "../../../src/etl/news/news_get_futuretools.py"])
        subprocess.run(["python3", "../../../src/etl/news/news_get_ycombinator.py"])
        subprocess.run(["python3", "../../../src/etl/news/news_get_genai_medium.py"])
        subprocess.run(["python3", "../../../src/etl/news/news_get_bensbites.py"])  # Add Ben's Bites refresh
        # Wait until the script is finished
        logger.info("Datos de noticias cargados correctamente")
        st.success("Datos de noticias cargados correctamente")
        # Refresh the data
        futuretools_news_df, ycombinator_news_df, medium_news_df, bensbites_news_df = get_news_data()
        logger.info("Datos de noticias actualizados correctamente")
        # Refresh the page
        st.rerun()

    # Load news data
    futuretools_news_df, ycombinator_news_df, medium_news_df, bensbites_news_df = get_news_data()

    logger.info(f"Loaded {len(futuretools_news_df)} futuretools news articles")
    logger.info(f"Loaded {len(ycombinator_news_df)} ycombinator news articles")
    logger.info(f"Loaded {len(medium_news_df)} medium news articles")
    logger.info(f"Loaded {len(bensbites_news_df)} bensbites news articles")

    # Display news data
    if futuretools_news_df.empty and ycombinator_news_df.empty and bensbites_news_df.empty:
        logger.warning("No news data available")
        st.warning("No hay datos de noticias disponibles.")
    else:
        news_futuretools_col, news_ycombinator_col, news_medium_genai_col = st.columns([1, 1, 1])
        
        # Add responsive container CSS
        st.markdown("""
            <style>
            .news-container {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            
            @media (min-width: 768px) {
                .news-container {
                    flex-direction: row;
                }
                
                .news-column {
                    flex: 1;
                    min-width: 0; /* Prevent flex items from overflowing */
                }
            }
            
            .news-card {
                background-color: #2D2B55;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
                border-left: 3px solid #A37FFF;
            }
            
            @media (max-width: 768px) {
                .news-card {
                    margin: 10px 0;
                }
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="news-container">', unsafe_allow_html=True)
        
        # FutureTools and Ben's Bites News
        st.markdown('<div class="news-column">', unsafe_allow_html=True)
        with news_futuretools_col:
            st.header("Noticias de FutureTools y Ben's Bites")
            if futuretools_news_df.empty and bensbites_news_df.empty:
                st.warning("No hay noticias que coincidan con los filtros seleccionados.")
            else:
                # Debug logging for data combination
                logger.info("Combining FutureTools and Ben's Bites news")
                logger.info(f"FutureTools columns: {futuretools_news_df.columns.tolist()}")
                logger.info(f"Ben's Bites columns: {bensbites_news_df.columns.tolist()}")
                
                # Prepare display data for both sources
                futuretools_display = futuretools_news_df[["title", "published_at", "source", "url"]].copy() if not futuretools_news_df.empty else pd.DataFrame(columns=["title", "published_at", "source", "url"])
                bensbites_display = bensbites_news_df[["title", "published_at", "source", "url"]].copy() if not bensbites_news_df.empty else pd.DataFrame(columns=["title", "published_at", "source", "url"])
                
                # Combine FutureTools and Ben's Bites news
                combined_news_df = pd.concat([futuretools_display, bensbites_display])
                logger.info(f"Combined DataFrame shape: {combined_news_df.shape}")
                
                # Sort by published_at
                combined_news_df = combined_news_df.sort_values("published_at", ascending=False)
                
                # Add clickable links using the URL column
                combined_news_df["Ver Noticia"] = combined_news_df["url"].apply(lambda x: make_clickable(x, "Leer más"))
                
                # Drop the URL column as it's no longer needed
                combined_news_df = combined_news_df.drop(columns=["url"])
                
                # Rename columns to Spanish
                combined_news_df.rename(
                    columns={
                        "title": "Título",
                        "published_at": "Fecha de Publicación",
                        "source": "Fuente",
                    },
                    inplace=True,
                )
                
                logger.info("Displaying combined news table")
                # Show table
                st.markdown(
                    combined_news_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Hacker News
        st.markdown('<div class="news-column">', unsafe_allow_html=True)
        with news_ycombinator_col:
            st.header("Noticias de Hacker News")
            # Display results
            if ycombinator_news_df.empty:
                logger.warning("No matches found")
                st.warning(
                    "No hay noticias que coincidan con los filtros seleccionados."
                )
            else:
                # Prepare display data
                display_news_df = ycombinator_news_df[
                    ["title", "published_at", "source"]
                ].copy()

                # Add clickable links
                display_news_df["Ver Noticia"] = ycombinator_news_df["url"].apply(
                    lambda x: make_clickable(x, "Leer más")
                )

                # Rename columns to Spanish
                display_news_df.rename(
                    columns={
                        "title": "Título",
                        "published_at": "Fecha de Publicación",
                        "source": "Fuente",
                    },
                    inplace=True,
                )

                # Show table
                st.markdown(
                    display_news_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Medium News
        st.markdown('<div class="news-column">', unsafe_allow_html=True)
        with news_medium_genai_col:
            # Display results
            st.header("Noticias de Medium sobre IA")
            if medium_news_df.empty:
                logger.warning("No matches found")
                st.warning(
                    "No hay noticias que coincidan con los filtros seleccionados."
                )
            else:
                # Prepare display data
                display_news_df = medium_news_df[
                    ["title", "published_at", "source"]
                ].copy()

                # Add clickable links
                display_news_df["Ver Noticia"] = medium_news_df["url"].apply(
                    lambda x: make_clickable(x, "Leer más")
                )

                # Rename columns to Spanish
                display_news_df.rename(
                    columns={
                        "title": "Título",
                        "published_at": "Fecha de Publicación",
                        "source": "Fuente",
                    },
                    inplace=True,
                )

                # Show table
                st.markdown(
                    display_news_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)


with tab3:
    logger.info("Rendering Videos tab")
    st.header("📺 Videos de Youtube sobre Desarrollo (informática)")



    videos_df = get_videos_data(DEV_VIDEOS_FILE)
    logger.info(f"Loaded {len(videos_df)} videos")

    if videos_df.empty:
        logger.warning("No videos data available")
        st.warning("No hay datos de videos disponibles.")
    else:
        # Filters
        search_term = st.text_input("🔍 Buscar en títulos de videos", "")

        # Date range filter
        date_range = st.date_input(
            "Rango de fechas para videos",
            [videos_df["published_date"].min(), videos_df["published_date"].max()],
            min_value=videos_df["published_date"].min().date(),
            max_value=videos_df["published_date"].max().date(),
            key="dev_videos_date_range"
        )

        # Apply filters
        filtered_videos_df = videos_df.copy()

        if search_term:
            filtered_videos_df = filtered_videos_df[
                filtered_videos_df["title"].str.contains(
                    search_term, case=False, na=False
                )
            ]

        if len(date_range) == 2:
            filtered_videos_df = filtered_videos_df[
                (filtered_videos_df["published_date"].dt.date >= date_range[0])
                & (filtered_videos_df["published_date"].dt.date <= date_range[1])
            ]

        logger.info(f"Filtered to {len(filtered_videos_df)} video results")

        # Display results
        if filtered_videos_df.empty:
            logger.warning("No video matches found")
            st.warning("No hay videos que coincidan con los filtros seleccionados.")
        else:
            # Display videos in a responsive grid format
            num_cols = get_responsive_cols()
            for i in range(0, len(filtered_videos_df), num_cols):
                cols = st.columns(num_cols)
                for j, (_, video) in enumerate(filtered_videos_df.iloc[i:i + num_cols].iterrows()):
                    with cols[j % num_cols]:
                        with st.container():
                            st.subheader(video["title"])
                            st.write(f"**Canal:** {video.get('channel', 'N/A')}")
                            st.write(f"**Publicado:** {video.get('published_at', 'N/A')}")
                            if "url" in video and pd.notna(video["url"]):
                                st.markdown(make_clickable(video["url"], "Ver en YouTube"), unsafe_allow_html=True)
                            st.markdown("---")

with tab4:
    logger.info("Rendering Videos tab")
    st.header("📺 Videos de Youtube sobre Desarrollo (personal)")



    videos_df = get_videos_data(PERSONAL_DEV_VIDEOS_FILE)
    logger.info(f"Loaded {len(videos_df)} videos")

    if videos_df.empty:
        logger.warning("No videos data available")
        st.warning("No hay datos de videos disponibles.")
    else:
        # Filters
        search_term_personal = st.text_input("🔍 Buscar en títulos de videos de desarrollo personal", "")

        # Date range filter
        date_range = st.date_input(
            "Rango de fechas para videos",
            [videos_df["published_date"].min(), videos_df["published_date"].max()],
            min_value=videos_df["published_date"].min().date(),
            max_value=videos_df["published_date"].max().date(),
            key="date_input_personal_dev_videos"
        )

        # Apply filters
        filtered_videos_df = videos_df.copy()

        if search_term_personal:
            filtered_videos_df = filtered_videos_df[
                filtered_videos_df["title"].str.contains(
                    search_term_personal, case=False, na=False
                )
            ]

        if len(date_range) == 2:
            filtered_videos_df = filtered_videos_df[
                (filtered_videos_df["published_date"].dt.date >= date_range[0])
                & (filtered_videos_df["published_date"].dt.date <= date_range[1])
            ]

        logger.info(f"Filtered to {len(filtered_videos_df)} video results")

        # Display results
        if filtered_videos_df.empty:
            logger.warning("No video matches found")
            st.warning("No hay videos que coincidan con los filtros seleccionados.")
        else:
            # Display videos in a responsive grid format
            num_cols = get_responsive_cols()
            for i in range(0, len(filtered_videos_df), num_cols):
                cols = st.columns(num_cols)
                for j, (_, video) in enumerate(filtered_videos_df.iloc[i:i + num_cols].iterrows()):
                    with cols[j % num_cols]:
                        with st.container():
                            st.subheader(video["title"])
                            st.write(f"**Canal:** {video.get('channel', 'N/A')}")
                            st.write(f"**Publicado:** {video.get('published_at', 'N/A')}")
                            if "url" in video and pd.notna(video["url"]):
                                st.markdown(make_clickable(video["url"], "Ver en YouTube"), unsafe_allow_html=True)
                            st.markdown("---")

with tab5:
    logger.info("Rendering Videos tab")
    st.header("📺 Videos de Youtube sobre Economía y Política")



    videos_df = get_videos_data(ECONOMICS_VIDEOS_FILE)
    logger.info(f"Loaded {len(videos_df)} videos")

    if videos_df.empty:
        logger.warning("No videos data available")
        st.warning("No hay datos de videos disponibles.")
    else:
        # Filters
        search_term_economics = st.text_input("🔍 Buscar en títulos de videos de economía y política", "")

        # Date range filter
        date_range = st.date_input(
            "Rango de fechas para videos",
            [videos_df["published_date"].min(), videos_df["published_date"].max()],
            min_value=videos_df["published_date"].min().date(),
            max_value=videos_df["published_date"].max().date(),
            key="date_input_economics_videos"
        )

        # Apply filters
        filtered_videos_df = videos_df.copy()

        if search_term_economics:
            filtered_videos_df = filtered_videos_df[
                filtered_videos_df["title"].str.contains(
                    search_term_economics, case=False, na=False
                )
            ]

        if len(date_range) == 2:
            filtered_videos_df = filtered_videos_df[
                (filtered_videos_df["published_date"].dt.date >= date_range[0])
                & (filtered_videos_df["published_date"].dt.date <= date_range[1])
            ]

        logger.info(f"Filtered to {len(filtered_videos_df)} video results")

        # Display results
        if filtered_videos_df.empty:
            logger.warning("No video matches found")
            st.warning("No hay videos que coincidan con los filtros seleccionados.")
        else:
            # Display videos in a responsive grid format
            num_cols = get_responsive_cols()
            for i in range(0, len(filtered_videos_df), num_cols):
                cols = st.columns(num_cols)
                for j, (_, video) in enumerate(filtered_videos_df.iloc[i:i + num_cols].iterrows()):
                    with cols[j % num_cols]:
                        with st.container():
                            st.subheader(video["title"])
                            st.write(f"**Canal:** {video.get('channel', 'N/A')}")
                            st.write(f"**Publicado:** {video.get('published_at', 'N/A')}")
                            if "url" in video and pd.notna(video["url"]):
                                st.markdown(make_clickable(video["url"], "Ver en YouTube"), unsafe_allow_html=True)
                            st.markdown("---")

with tab6:
    logger.info("Rendering Watchers tab")
    st.header("👁️ Monitores de Cambios (Watchers)")
    
    # Helper function to load watcher state data
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def load_watcher_states():
        """Load all watcher states from the watchers data directory"""
        watchers_data = []
        
        # List all directories in the watchers folder (each is a watcher)
        watcher_dirs = [d for d in os.listdir(WATCHERS_DATA_DIR) 
                        if os.path.isdir(os.path.join(WATCHERS_DATA_DIR, d))]
        
        for watcher_name in watcher_dirs:
            watcher_path = os.path.join(WATCHERS_DATA_DIR, watcher_name)
            state_file = os.path.join(watcher_path, "state.json")
            
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    
                    # Count events
                    events_dir = os.path.join(watcher_path, "events")
                    event_count = len(os.listdir(events_dir)) if os.path.exists(events_dir) else 0
                    
                    # Get last event file (most recent by filename)
                    last_event = None
                    if os.path.exists(events_dir) and os.listdir(events_dir):
                        event_files = sorted(os.listdir(events_dir), reverse=True)
                        if event_files:
                            last_event_file = os.path.join(events_dir, event_files[0])
                            with open(last_event_file, 'r', encoding='utf-8') as f:
                                last_event = json.load(f)
                    
                    # Add watcher data
                    watcher_data = {
                        "name": watcher_name,
                        "state": state,
                        "event_count": event_count,
                        "last_event": last_event,
                        "path": watcher_path
                    }
                    
                    # Add URL if available in the state
                    if isinstance(state.get("last_value"), dict) and "url" in state["last_value"]:
                        watcher_data["url"] = state["last_value"]["url"]
                    
                    watchers_data.append(watcher_data)
                except Exception as e:
                    logger.error(f"Error loading watcher state for {watcher_name}: {str(e)}")
        
        return watchers_data
    
    # Load watcher states
    watcher_states = load_watcher_states()
    
    # Add a button to refresh data
    if st.button("Actualizar datos de los watchers"):
        st.cache_data.clear()
        watcher_states = load_watcher_states()
        st.success("Datos actualizados correctamente")
    
    # Add a button to run MS Skills watcher specifically
    if st.button("Ejecutar MS Skills Watcher (forzar actualización)"):
        try:
            st.info("Ejecutando MS Skills Watcher...")
            # Use the project's file_system utility to get the project root
            from src.utils.file_system import get_project_root
            project_root = get_project_root()
            watcher_script = os.path.join(project_root, "src", "watchers", "ms_skills_watcher.py")
            
            # Run the watcher script with python's -m option to ensure imports work
            result = subprocess.run(
                ["python", watcher_script, "--force"], 
                capture_output=True, 
                text=True,
                check=True,
                cwd=project_root  # Execute from the project root
            )
            st.success("MS Skills Watcher ejecutado correctamente")
            # Clear cache and reload data
            st.cache_data.clear()
            watcher_states = load_watcher_states()
        except Exception as e:
            st.error(f"Error al ejecutar MS Skills Watcher: {str(e)}")
    
    if not watcher_states:
        st.warning("No hay datos de watchers disponibles.")
    else:
        # Display watcher cards
        for watcher in watcher_states:
            with st.expander(f"📡 {watcher['name'].replace('_', ' ').title()}", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Get last check time
                    last_check = watcher['state'].get('last_check')
                    if last_check:
                        try:
                            last_check_dt = datetime.fromisoformat(last_check)
                            last_check_str = last_check_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            last_check_str = last_check
                    else:
                        last_check_str = "Nunca"
                    
                    # Get first seen time
                    first_seen = watcher['state'].get('first_seen')
                    if first_seen:
                        try:
                            first_seen_dt = datetime.fromisoformat(first_seen)
                            first_seen_str = first_seen_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            first_seen_str = first_seen
                    else:
                        first_seen_str = "Desconocido"
                    
                    # Display watcher info
                    st.markdown(f"**Última comprobación:** {last_check_str}")
                    st.markdown(f"**Primera detección:** {first_seen_str}")
                    st.markdown(f"**Número de eventos:** {watcher['event_count']}")
                    
                    # Display URL if available
                    if "url" in watcher:
                        st.markdown(f"**URL:** [{watcher['url']}]({watcher['url']})")
                    
                    # Display last value details
                    last_value = watcher['state'].get('last_value')
                    if last_value:
                        st.markdown("**Último valor:**")
                        
                        # Special handling for MS Applied Skills watcher
                        if watcher['name'] == "ms_applied_skills" and isinstance(last_value, dict):
                            st.markdown(f"- **Método de extracción:** {last_value.get('extraction_method', 'Desconocido')}")
                            st.markdown(f"- **Número de skills:** {last_value.get('count', 0)}")
                            
                            # Show skills in a table
                            if 'skills' in last_value and last_value['skills']:
                                # Handle both formats: list of strings or list of dicts with title and url
                                if isinstance(last_value['skills'][0], dict):
                                    # Create a simple markdown list with links
                                    st.markdown("#### Lista de Microsoft Applied Skills:")
                                    for i, skill in enumerate(last_value['skills']):
                                        title = skill.get('title', '')
                                        url = skill.get('url')
                                        
                                        # Create markdown link if URL exists
                                        if url:
                                            st.markdown(f"{i+1}. {title} [🔗]({url})")
                                        else:
                                            st.markdown(f"{i+1}. {title}")
                                else:
                                    # Old format - simple list of skill names
                                    skills_df = pd.DataFrame(last_value['skills'], columns=["Skill"])
                                    st.dataframe(skills_df, use_container_width=True)
                        else:
                            # Generic display for other watchers
                            st.json(last_value)
                
                with col2:
                    # Display last event if available
                    if watcher['last_event']:
                        st.markdown("**Último evento:**")
                        event_time = watcher['last_event'].get('timestamp')
                        if event_time:
                            try:
                                event_dt = datetime.fromisoformat(event_time)
                                event_time_str = event_dt.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                event_time_str = event_time
                        else:
                            event_time_str = "Desconocido"
                        
                        st.markdown(f"- **Tipo:** {watcher['last_event'].get('type', 'Desconocido')}")
                        st.markdown(f"- **Fecha:** {event_time_str}")
                    
                    # Add button to view all events
                    if watcher['event_count'] > 0:
                        if st.button(f"Ver todos los eventos ({watcher['event_count']})", key=f"events_{watcher['name']}"):
                            events_dir = os.path.join(watcher['path'], "events")
                            event_files = sorted(os.listdir(events_dir), reverse=True)
                            
                            events_data = []
                            for event_file in event_files[:10]:  # Limit to 10 most recent events
                                with open(os.path.join(events_dir, event_file), 'r', encoding='utf-8') as f:
                                    event = json.load(f)
                                events_data.append(event)
                            
                            # Convert to DataFrame for display
                            events_df = pd.DataFrame([{
                                "ID": e.get("id", ""),
                                "Tipo": e.get("type", ""),
                                "Fecha": datetime.fromisoformat(e.get("timestamp", "")).strftime("%Y-%m-%d %H:%M:%S") if "timestamp" in e else "",
                                "Detalles": str(e.get("details", ""))[:50] + "..." if e.get("details") else ""
                            } for e in events_data])
                            
                            st.dataframe(events_df, use_container_width=True)

# Footer
st.markdown(
    """
<div style="text-align: center; margin-top: 30px; padding: 20px; opacity: 0.9; background-color: #2D2B55; border-radius: 8px; box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3); border-top: 3px solid #A37FFF;">
    <p style="font-family: 'Poppins', sans-serif; color: #E2E8F0; font-size: 14px;">Datos obtenidos de <a href="https://isthereanydeal.com/" target="_blank">IsThereAnyDeal</a>, <a href="https://futuretools.io/news" target="_blank">FutureTools.io</a>, <a href="https://www.medium.com/" target="_blank">Medium</a> y <a href="https://www.youtube.com/" target="_blank">Youtube</a></p>
</div>
""",
    unsafe_allow_html=True,
)
logger.info("Dashboard rendering completed")
