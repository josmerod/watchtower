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

# Define shortcuts data structure - customize categories and links here
SHORTCUTS = {
    "Development": [
        {"name": "GitHub", "url": "https://github.com/", "icon": "🐙", "description": "Code hosting platform for version control and collaboration"},
        {"name": "Stack Overflow", "url": "https://stackoverflow.com/", "icon": "📚", "description": "Community for developers to learn and share knowledge"},
        {"name": "VS Code", "url": "https://vscode.dev/", "icon": "💻", "description": "Online code editor based on VS Code"}
    ],
    "AI Tools": [
        {"name": "ChatGPT", "url": "https://chat.openai.com/", "icon": "🤖", "description": "AI assistant for natural language conversations"},
        {"name": "Hugging Face", "url": "https://huggingface.co/", "icon": "🤗", "description": "AI model repository and community"},
        {"name": "Cursor", "url": "https://cursor.sh/", "icon": "✨", "description": "AI-first code editor"},
        {"name": "Midjourney", "url": "https://www.midjourney.com/", "icon": "🎨", "description": "AI image generation platform"}
    ],
    "Learning Resources": [
        {"name": "Medium", "url": "https://medium.com/", "icon": "📝", "description": "Platform for reading and writing articles"},
        {"name": "YouTube", "url": "https://www.youtube.com/", "icon": "📺", "description": "Video platform with vast educational content"},
        {"name": "Coursera", "url": "https://www.coursera.org/", "icon": "🎓", "description": "Online courses from top universities"}
    ],
    "Productivity": [
        {"name": "Notion", "url": "https://www.notion.so/", "icon": "📋", "description": "All-in-one workspace for notes and tasks"},
        {"name": "Trello", "url": "https://trello.com/", "icon": "📊", "description": "Visual tool for managing projects and tasks"},
        {"name": "Google Drive", "url": "https://drive.google.com/", "icon": "📁", "description": "Cloud storage and file sharing"}
    ]
}

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

VALENCIA_EVENTS_DATA_DIR = "../../../data/valencia_events"

# New path for shortcuts data
SHORTCUTS_DATA_DIR = "../../../data/shortcuts"
CUSTOM_SHORTCUTS_FILE = os.path.join(SHORTCUTS_DATA_DIR, "custom_shortcuts.json")

DEALS_FILE = os.path.join(GAMES_DATA_DIR, "deals.json")
BUNDLES_FILE = os.path.join(GAMES_DATA_DIR, "bundles.json")
GIVEAWAYS_FILE = os.path.join(GAMES_DATA_DIR, "giveaways.json")

FUTURETOOLS_NEWS_FILE = os.path.join(FUTURETOOLS_NEWS_DATA_DIR, "futuretoolsnews.json")
YCOMBINATOR_NEWS_FILE = os.path.join(YCOMBINATOR_NEWS_DATA_DIR, "hackernews.json")
MEDIUM_NEWS_FILE = os.path.join(MEDIUM_NEWS_DATA_DIR, "medium_genai.json")
BENSBITES_NEWS_FILE = os.path.join(BENSBITES_NEWS_DATA_DIR, "bensbites_news.json")

VALENCIA_EVENTS_FILE = os.path.join(VALENCIA_EVENTS_DATA_DIR, "valencia_events.json")

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
        transition: all 0.3s ease;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        height: 100%;
    }
    
    .video-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.4);
    }
    
    /* Video thumbnail container */
    .stImage img {
        width: 100%;
        border-radius: 6px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
        transition: transform 0.3s ease;
    }
    
    .stImage img:hover {
        transform: scale(1.03);
    }
    
    /* Video title styling */
    .element-container .stMarkdown h3 {
        margin-top: 0;
        margin-bottom: 8px;
        font-size: 1.1rem;
        line-height: 1.4;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
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

    /* Deals container */
    .deals-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        width: 100%;
        padding: 1rem;
    }

    .deals-column {
        min-width: 0;
        width: 100%;
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        height: 100%;
        overflow-x: auto;
    }

    .deals-card {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        border-left: 3px solid #A37FFF;
        height: 100%;
        overflow-x: auto;
    }

    /* News container */
    .news-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        width: 100%;
        padding: 1rem;
    }

    .news-column {
        min-width: 0;
        width: 100%;
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        height: 100%;
        overflow-x: auto;
    }

    .news-card {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        border-left: 3px solid #A37FFF;
        height: 100%;
        overflow-x: auto;
    }

    /* Shortcuts styling */
    .shortcuts-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        width: 100%;
        padding: 1rem;
    }

    .shortcuts-category {
        background-color: #2D2B55;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        border-top: 3px solid #A37FFF;
        height: 100%;
    }

    .shortcut-item {
        display: flex;
        align-items: center;
        background-color: #34325A;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }

    .shortcut-item:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        background-color: #3C3970;
    }

    .shortcut-icon {
        font-size: 24px;
        margin-right: 15px;
        min-width: 30px;
        text-align: center;
    }

    .shortcut-content {
        flex-grow: 1;
    }

    .shortcut-title {
        font-weight: 600;
        font-size: 16px;
        margin-bottom: 5px;
    }

    .shortcut-description {
        font-size: 13px;
        color: #CCC6F2;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    /* Table responsiveness */
    .stDataFrame {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    table {
        width: 100%;
        min-width: 100%;
        margin-bottom: 0;
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

def load_custom_shortcuts():
    """Load custom shortcuts from JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)
        
        if os.path.exists(CUSTOM_SHORTCUTS_FILE):
            logger.info(f"Loading custom shortcuts from {CUSTOM_SHORTCUTS_FILE}")
            with open(CUSTOM_SHORTCUTS_FILE, "r", encoding="utf-8") as f:
                shortcuts = json.load(f)
            logger.info(f"Successfully loaded {len(shortcuts)} custom shortcuts")
            return shortcuts
        else:
            logger.info(f"No custom shortcuts file found at {CUSTOM_SHORTCUTS_FILE}")
            return []
    except Exception as e:
        logger.error(f"Error loading custom shortcuts: {str(e)}")
        return []

def save_custom_shortcuts(shortcuts):
    """Save custom shortcuts to JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(SHORTCUTS_DATA_DIR, exist_ok=True)
        
        logger.info(f"Saving {len(shortcuts)} custom shortcuts to {CUSTOM_SHORTCUTS_FILE}")
        with open(CUSTOM_SHORTCUTS_FILE, "w", encoding="utf-8") as f:
            json.dump(shortcuts, f, indent=4, ensure_ascii=False)
        logger.info("Custom shortcuts saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving custom shortcuts: {str(e)}")
        return False

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
tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔖 Accesos Directos", "📺 Videos", "📰 Noticias", "🎮 Juegos", "👁️ Watchers", "🏙️ Eventos Valencia", "⚙️ Admin"])

with tab0:
    logger.info("Rendering Shortcuts tab")
    st.header("🔖 Accesos Directos")
    
    st.markdown("""
    <div class="card" style="background-color: #2D2B55; padding: 18px; border-radius: 8px; border-left: 5px solid #A37FFF; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);">
        <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #E2E8F0;">
            Enlaces rápidos a sitios web y herramientas útiles. Personaliza esta sección editando la variable <code>SHORTCUTS</code> 
            en el código fuente o añade enlaces personalizados usando el panel inferior.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state for custom shortcuts if not exists
    if 'custom_shortcuts' not in st.session_state:
        st.session_state.custom_shortcuts = load_custom_shortcuts()
    
    # Search bar for filtering shortcuts
    search = st.text_input("🔍 Buscar acceso directo", placeholder="Buscar por nombre o descripción...")
    
    # Combine predefined and custom shortcuts for search
    all_shortcuts = []
    for category, shortcuts in SHORTCUTS.items():
        for shortcut in shortcuts:
            shortcut_with_category = shortcut.copy()
            shortcut_with_category['category'] = category
            all_shortcuts.append(shortcut_with_category)
    
    # Add custom shortcuts if any
    for shortcut in st.session_state.custom_shortcuts:
        shortcut_with_category = shortcut.copy()
        shortcut_with_category['category'] = "Personalizados"
        all_shortcuts.append(shortcut_with_category)
    
    # Filter shortcuts if search is not empty
    if search:
        filtered_shortcuts = [s for s in all_shortcuts if (
            search.lower() in s['name'].lower() or 
            search.lower() in s['description'].lower() or
            search.lower() in s['category'].lower()
        )]
        
        if not filtered_shortcuts:
            st.warning(f"No se encontraron accesos directos que coincidan con '{search}'")
        else:
            # Create three columns for search results
            result_cols = st.columns(3)
            
            # Distribute shortcuts across the three columns
            for i, shortcut in enumerate(filtered_shortcuts):
                with result_cols[i % 3]:
                    st.markdown(f"""
                    <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                        <div class="shortcut-item">
                            <div class="shortcut-icon">{shortcut['icon']}</div>
                            <div class="shortcut-content">
                                <div class="shortcut-title">{shortcut['name']} <span style="opacity: 0.6; font-size: 12px;">({shortcut['category']})</span></div>
                                <div class="shortcut-description">{shortcut['description']}</div>
                            </div>
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
    else:
        # Create three fixed columns for categories
        col1, col2, col3 = st.columns(3)
        
        # Combine predefined and custom categories
        all_categories = list(SHORTCUTS.keys())
        
        # Add custom categories that aren't in predefined ones
        custom_categories = set()
        for shortcut in st.session_state.custom_shortcuts:
            category = shortcut.get("category", "Personalizados")
            if category not in SHORTCUTS:
                custom_categories.add(category)
        
        all_categories.extend(sorted(list(custom_categories)))
        
        # Calculate how to distribute categories across columns
        categories_per_column = max(1, len(all_categories) // 3 + (1 if len(all_categories) % 3 > 0 else 0))
        
        # Distribute categories across columns
        for i, category in enumerate(all_categories):
            column = col1 if i % 3 == 0 else col2 if i % 3 == 1 else col3
            with column:
                st.markdown(f'<div class="shortcuts-category">', unsafe_allow_html=True)
                st.markdown(f'<h3>{category}</h3>', unsafe_allow_html=True)
                
                # Display predefined shortcuts for this category
                if category in SHORTCUTS:
                    for shortcut in SHORTCUTS[category]:
                        st.markdown(f'''
                        <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                            <div class="shortcut-item">
                                <div class="shortcut-icon">{shortcut['icon']}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut['name']}</div>
                                    <div class="shortcut-description">{shortcut['description']}</div>
                                </div>
                            </div>
                        </a>
                        ''', unsafe_allow_html=True)
                
                # Display custom shortcuts for this category
                custom_shortcuts_in_category = [s for s in st.session_state.custom_shortcuts 
                                               if s.get("category", "Personalizados") == category]
                
                for i, shortcut in enumerate(custom_shortcuts_in_category):
                    # For predefined categories, no delete button
                    if category in SHORTCUTS:
                        st.markdown(f'''
                        <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                            <div class="shortcut-item">
                                <div class="shortcut-icon">{shortcut['icon']}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut['name']}</div>
                                    <div class="shortcut-description">{shortcut['description']}</div>
                                </div>
                            </div>
                        </a>
                        ''', unsafe_allow_html=True)
                    else:
                        # Custom category with delete button
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.markdown(f'''
                            <a href="{shortcut['url']}" target="_blank" style="text-decoration: none;">
                                <div class="shortcut-item">
                                    <div class="shortcut-icon">{shortcut['icon']}</div>
                                    <div class="shortcut-content">
                                        <div class="shortcut-title">{shortcut['name']}</div>
                                        <div class="shortcut-description">{shortcut['description']}</div>
                                    </div>
                                </div>
                            </a>
                            ''', unsafe_allow_html=True)
                        with c2:
                            # Find the index in the original list for deletion
                            original_index = st.session_state.custom_shortcuts.index(shortcut)
                            if st.button("❌", key=f"del_main_{category}_{original_index}", help="Eliminar este enlace"):
                                st.session_state.custom_shortcuts.pop(original_index)
                                # Save changes
                                save_custom_shortcuts(st.session_state.custom_shortcuts)
                                st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Tabs for managing shortcuts
    manage_tab1, manage_tab2, manage_tab3, manage_tab4 = st.tabs(["Añadir enlace", "Organizar", "Exportar configuración", "Importar configuración"])
    
    with manage_tab1:
        # Form for adding custom shortcuts
        with st.form("add_custom_shortcut"):
            st.subheader("Añadir enlace personalizado")
            
            # Get existing categories from predefined shortcuts
            existing_categories = list(SHORTCUTS.keys()) + ["Personalizados", "Nueva categoría..."]
            
            # Get custom categories from custom shortcuts
            custom_categories = set()
            for shortcut in st.session_state.custom_shortcuts:
                if "category" in shortcut and shortcut["category"]:
                    custom_categories.add(shortcut["category"])
            
            # Combine all categories without duplicates
            all_categories = sorted(list(set(existing_categories) | custom_categories))
            if "Nueva categoría..." in all_categories:
                all_categories.remove("Nueva categoría...")
                all_categories.append("Nueva categoría...")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                custom_name = st.text_input("Nombre", placeholder="Nombre del enlace")
                custom_icon = st.text_input("Icono (emoji)", placeholder="🔗", max_chars=2)
                
                # Category selection
                category_selection = st.selectbox(
                "Categoría",
                    all_categories,
                    index=all_categories.index("Personalizados") if "Personalizados" in all_categories else 0
                )
                
                # Show input for new category if "Nueva categoría..." selected
                new_category = None
                if category_selection == "Nueva categoría...":
                    new_category = st.text_input("Nombre de nueva categoría", placeholder="Mi categoría")
        
            with col2:
                custom_url = st.text_input("URL", placeholder="https://example.com")
                custom_desc = st.text_input("Descripción (opcional)", placeholder="Breve descripción")
            
            # Submit button
            submitted = st.form_submit_button("Añadir enlace")
            if submitted and custom_name and custom_url:
                # Get the category
                final_category = new_category if category_selection == "Nueva categoría..." and new_category else category_selection
                
                # If it's a new valid category, add it
                if final_category != "Nueva categoría...":
                    # Save to session state
                    st.session_state.custom_shortcuts.append({
                        "name": custom_name,
                        "url": custom_url,
                        "icon": custom_icon if custom_icon else "🔗",
                        "description": custom_desc if custom_desc else "Enlace personalizado",
                        "category": final_category
                    })
                    # Save changes to file
                    save_custom_shortcuts(st.session_state.custom_shortcuts)
                    st.success(f"Enlace '{custom_name}' añadido a la categoría '{final_category}'")
                    st.rerun()
                else:
                    st.error("Por favor, ingresa un nombre válido para la nueva categoría")
    
    with manage_tab2:
        st.subheader("Organizar accesos directos")
        
        if not st.session_state.custom_shortcuts:
            st.info("No hay accesos directos personalizados para organizar.")
        else:
            # Group shortcuts by category
            shortcuts_by_category = {}
            
            for i, shortcut in enumerate(st.session_state.custom_shortcuts):
                category = shortcut.get("category", "Personalizados")
                if category not in shortcuts_by_category:
                    shortcuts_by_category[category] = []
                
                # Add index to shortcut for reference
                shortcut_with_index = shortcut.copy()
                shortcut_with_index["index"] = i
                shortcuts_by_category[category].append(shortcut_with_index)
            
            # Get existing categories from predefined shortcuts for moving items
            existing_categories = list(SHORTCUTS.keys()) + ["Personalizados"] + list(shortcuts_by_category.keys())
            existing_categories = sorted(list(set(existing_categories)))
            
            # Display shortcuts by category with organization options
            for category, shortcuts in shortcuts_by_category.items():
                with st.expander(f"{category} ({len(shortcuts)} enlaces)", expanded=True):
                    for shortcut in shortcuts:
                        col1, col2, col3 = st.columns([4, 2, 1])
                        
                        with col1:
                            st.markdown(f'''
                            <div class="shortcut-item" style="margin-bottom: 5px;">
                                <div class="shortcut-icon">{shortcut['icon']}</div>
                                <div class="shortcut-content">
                                    <div class="shortcut-title">{shortcut['name']}</div>
                                </div>
                            </div>
                            ''', unsafe_allow_html=True)
                        
                        with col2:
                            # Category movement dropdown
                            move_to = st.selectbox(
                                "Mover a",
                                existing_categories,
                                index=existing_categories.index(category),
                                key=f"move_{shortcut['index']}"
                            )
                            
                            if move_to != category:
                                # Update category
                                st.session_state.custom_shortcuts[shortcut['index']]["category"] = move_to
                                # Save changes
                                save_custom_shortcuts(st.session_state.custom_shortcuts)
                                st.success(f"'{shortcut['name']}' movido a '{move_to}'")
                                st.rerun()
                        
                        with col3:
                            # Delete button
                            if st.button("❌", key=f"del_org_{shortcut['index']}", help="Eliminar este enlace"):
                                st.session_state.custom_shortcuts.pop(shortcut['index'])
                                # Save changes
                                save_custom_shortcuts(st.session_state.custom_shortcuts)
                                st.success(f"Enlace '{shortcut['name']}' eliminado")
                                st.rerun()
            
            # Button to remove empty categories
            if st.button("Limpiar categorías vacías"):
                # Get categories with shortcuts
                used_categories = set()
                for shortcut in st.session_state.custom_shortcuts:
                    category = shortcut.get("category", "Personalizados")
                    used_categories.add(category)
                
                # Remove unused categories
                for shortcut in st.session_state.custom_shortcuts:
                    category = shortcut.get("category")
                    if category and category not in used_categories:
                        shortcut.pop("category", None)
                
                # Save changes
                save_custom_shortcuts(st.session_state.custom_shortcuts)
                st.success("Categorías vacías eliminadas")
                st.rerun()
    
    with manage_tab3:
        st.subheader("Exportar configuración")
        
        export_tab1, export_tab2 = st.tabs(["Python", "JSON"])
        
        with export_tab1:
            # Generate Python code snippet for current custom shortcuts
            if st.session_state.custom_shortcuts:
                code_snippet = "# Añade esto a la estructura SHORTCUTS en el archivo app.py\n"
                code_snippet += "\"Personalizados\": [\n"
                
                for shortcut in st.session_state.custom_shortcuts:
                    code_snippet += f"    {{\"name\": \"{shortcut['name']}\", \"url\": \"{shortcut['url']}\", \"icon\": \"{shortcut['icon']}\", \"description\": \"{shortcut['description']}\"}},\n"
                
                code_snippet += "]\n"
                
                st.code(code_snippet, language="python")
                
                st.download_button(
                    label="Descargar como Python (.py)",
                    data=code_snippet,
                    file_name="custom_shortcuts.py",
                    mime="text/plain",
                )
            else:
                st.info("Añade algunos enlaces personalizados para generar código exportable")
        
        with export_tab2:
            # Generate JSON for current custom shortcuts
            if st.session_state.custom_shortcuts:
                json_data = json.dumps(st.session_state.custom_shortcuts, indent=4, ensure_ascii=False)
                st.code(json_data, language="json")
                
                st.download_button(
                    label="Descargar como JSON",
                    data=json_data,
                    file_name="custom_shortcuts.json",
                    mime="application/json",
                )
            else:
                st.info("Añade algunos enlaces personalizados para generar JSON exportable")
    
    with manage_tab4:
        st.subheader("Importar configuración")
        
        # Upload JSON file
        uploaded_file = st.file_uploader("Subir archivo JSON de accesos directos", type=["json"])
        
        if uploaded_file is not None:
            try:
                # Read JSON from uploaded file
                imported_shortcuts = json.load(uploaded_file)
                
                # Validate structure
                valid_shortcuts = []
                for item in imported_shortcuts:
                    if isinstance(item, dict) and 'name' in item and 'url' in item:
                        # Add missing fields if needed
                        if 'icon' not in item:
                            item['icon'] = '🔗'
                        if 'description' not in item:
                            item['description'] = 'Enlace importado'
                        valid_shortcuts.append(item)
                
                # Preview imported shortcuts
                st.write(f"Accesos directos encontrados: {len(valid_shortcuts)}")
                
                for shortcut in valid_shortcuts:
                    st.markdown(f'''
                    <div class="shortcut-item">
                        <div class="shortcut-icon">{shortcut['icon']}</div>
                        <div class="shortcut-content">
                            <div class="shortcut-title">{shortcut['name']}</div>
                            <div class="shortcut-description">{shortcut['description']}</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # Add options to replace or merge
                option = st.radio(
                    "¿Cómo quieres importar estos accesos directos?",
                    ["Reemplazar todos los actuales", "Añadir a los actuales"]
                )
                
                if st.button("Importar accesos directos"):
                    if option == "Reemplazar todos los actuales":
                        st.session_state.custom_shortcuts = valid_shortcuts
                    else:  # Añadir a los actuales
                        st.session_state.custom_shortcuts.extend(valid_shortcuts)
                    
                    # Save changes
                    save_custom_shortcuts(st.session_state.custom_shortcuts)
                    st.success(f"Se han importado {len(valid_shortcuts)} accesos directos")
                    st.rerun()
                
            except Exception as e:
                st.error(f"Error al importar accesos directos: {str(e)}")

with tab1:
    logger.info("Rendering Videos tab")
    st.header("📺 Videos")

    # Load videos data
    dev_videos_df = get_videos_data(DEV_VIDEOS_FILE)
    personal_dev_videos_df = get_videos_data(PERSONAL_DEV_VIDEOS_FILE)
    economics_videos_df = get_videos_data(ECONOMICS_VIDEOS_FILE)

    if dev_videos_df.empty and personal_dev_videos_df.empty and economics_videos_df.empty:
        st.warning("No hay videos disponibles para mostrar.")
    else:
        # Create tabs for different video categories
        video_tabs = st.tabs(["Desarrollo", "Desarrollo Personal", "Economía"])

        with video_tabs[0]:
            st.header("Desarrollo")
            if not dev_videos_df.empty:
                # Sort by published date
                dev_videos_df = dev_videos_df.sort_values("published_date", ascending=False)
                
                # Get responsive columns based on screen width
                num_cols = get_responsive_cols()
                
                # Display videos in a grid
                for i in range(0, len(dev_videos_df), num_cols):
                    cols = st.columns(num_cols)
                    for j, (_, video) in enumerate(dev_videos_df.iloc[i:i + num_cols].iterrows()):
                        with cols[j % num_cols]:
                            with st.container():
                                st.markdown('<div class="video-card">', unsafe_allow_html=True)
                                
                                # Video thumbnail with link
                                if 'thumbnail' in video and pd.notna(video['thumbnail']):
                                    st.markdown(
                                        f'<a href="{video["url"]}" target="_blank"><img src="{video["thumbnail"]}" width="100%"></a>',
                                        unsafe_allow_html=True
                                    )
                                
                                # Video title with link
                                st.markdown(
                                    f'<h3><a href="{video["url"]}" target="_blank">{video["title"]}</a></h3>',
                                    unsafe_allow_html=True
                                )
                                
                                # Channel name
                                if 'channel_name' in video and pd.notna(video['channel_name']):
                                    st.markdown(f'**Canal:** {video["channel_name"]}', unsafe_allow_html=True)
                                
                                # Published date
                                if 'published_date' in video and pd.notna(video['published_date']):
                                    published_date = video['published_date'].strftime('%Y-%m-%d')
                                    st.markdown(f'**Publicado:** {published_date}', unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No hay videos de desarrollo disponibles.")

        with video_tabs[1]:
            st.header("Desarrollo Personal")
            if not personal_dev_videos_df.empty:
                # Sort by published date
                personal_dev_videos_df = personal_dev_videos_df.sort_values("published_date", ascending=False)
                
                # Get responsive columns based on screen width
                num_cols = get_responsive_cols()
                
                # Display videos in a grid
                for i in range(0, len(personal_dev_videos_df), num_cols):
                    cols = st.columns(num_cols)
                    for j, (_, video) in enumerate(personal_dev_videos_df.iloc[i:i + num_cols].iterrows()):
                        with cols[j % num_cols]:
                            with st.container():
                                st.markdown('<div class="video-card">', unsafe_allow_html=True)
                                
                                # Video thumbnail with link
                                if 'thumbnail' in video and pd.notna(video['thumbnail']):
                                    st.markdown(
                                        f'<a href="{video["url"]}" target="_blank"><img src="{video["thumbnail"]}" width="100%"></a>',
                                        unsafe_allow_html=True
                                    )
                                
                                # Video title with link
                                st.markdown(
                                    f'<h3><a href="{video["url"]}" target="_blank">{video["title"]}</a></h3>',
                                    unsafe_allow_html=True
                                )
                                
                                # Channel name
                                if 'channel_name' in video and pd.notna(video['channel_name']):
                                    st.markdown(f'**Canal:** {video["channel_name"]}', unsafe_allow_html=True)
                                
                                # Published date
                                if 'published_date' in video and pd.notna(video['published_date']):
                                    published_date = video['published_date'].strftime('%Y-%m-%d')
                                    st.markdown(f'**Publicado:** {published_date}', unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No hay videos de desarrollo personal disponibles.")

        with video_tabs[2]:
            st.header("Economía")
            if not economics_videos_df.empty:
                # Sort by published date
                economics_videos_df = economics_videos_df.sort_values("published_date", ascending=False)
                
                # Get responsive columns based on screen width
                num_cols = get_responsive_cols()
                
                # Display videos in a grid
                for i in range(0, len(economics_videos_df), num_cols):
                    cols = st.columns(num_cols)
                    for j, (_, video) in enumerate(economics_videos_df.iloc[i:i + num_cols].iterrows()):
                        with cols[j % num_cols]:
                            with st.container():
                                st.markdown('<div class="video-card">', unsafe_allow_html=True)
                                
                                # Video thumbnail with link
                                if 'thumbnail' in video and pd.notna(video['thumbnail']):
                                    st.markdown(
                                        f'<a href="{video["url"]}" target="_blank"><img src="{video["thumbnail"]}" width="100%"></a>',
                                        unsafe_allow_html=True
                                    )
                                
                                # Video title with link
                                st.markdown(
                                    f'<h3><a href="{video["url"]}" target="_blank">{video["title"]}</a></h3>',
                                    unsafe_allow_html=True
                                )
                                
                                # Channel name
                                if 'channel_name' in video and pd.notna(video['channel_name']):
                                    st.markdown(f'**Canal:** {video["channel_name"]}', unsafe_allow_html=True)
                                
                                # Published date
                                if 'published_date' in video and pd.notna(video['published_date']):
                                    published_date = video['published_date'].strftime('%Y-%m-%d')
                                    st.markdown(f'**Publicado:** {published_date}', unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No hay videos de economía disponibles.")

with tab2:
    logger.info("Rendering Noticias tab")
    st.header("📰 Noticias")

    # Load news data
    futuretools_news_df = load_data(FUTURETOOLS_NEWS_FILE)
    ycombinator_news_df = load_data(YCOMBINATOR_NEWS_FILE)
    medium_news_df = load_data(MEDIUM_NEWS_FILE)
    bensbites_news_df = load_data(BENSBITES_NEWS_FILE)

    if futuretools_news_df.empty and bensbites_news_df.empty and medium_news_df.empty:
        st.warning("No hay noticias disponibles para mostrar.")
    else:
        # Create tabs for different news sources
        news_tabs = st.tabs(["FutureTools & Ben's Bites", "Hacker News", "Medium GenAI"])

        with news_tabs[0]:
            st.header("FutureTools & Ben's Bites")
            if futuretools_news_df.empty and bensbites_news_df.empty:
                st.warning("No hay noticias disponibles de FutureTools o Ben's Bites.")
            else:
                # Combine FutureTools and Ben's Bites news
                combined_news_df = pd.concat([futuretools_news_df, bensbites_news_df])
                if not combined_news_df.empty:
                    # Ensure published_date column exists
                    if "published_date" not in combined_news_df.columns:
                        # Check if published_at exists and use it as a fallback
                        if "published_at" in combined_news_df.columns:
                            combined_news_df["published_date"] = pd.to_datetime(combined_news_df["published_at"], errors="coerce")
                        else:
                            # Create a default date column
                            combined_news_df["published_date"] = pd.Timestamp("now")
                    
                    # Sort by published_date (now guaranteed to exist)
                    combined_news_df = combined_news_df.sort_values("published_date", ascending=False)
                    
                    combined_news_df["Ver Noticia"] = combined_news_df["url"].apply(lambda x: make_clickable(x, "Leer más"))
                    
                    # Format date for display
                    combined_news_df["published_display"] = combined_news_df["published_date"].dt.strftime('%Y-%m-%d %H:%M')

                    display_combined_df = combined_news_df[["title", "published_display", "source", "Ver Noticia"]].copy()
                    
                    display_combined_df.rename(
                        columns={
                            "title": "Título",
                            "published_display": "Fecha de Publicación",
                            "source": "Fuente",
                        },
                        inplace=True,
                    )
                    
                    st.markdown(
                        display_combined_df.to_html(escape=False, index=False),
                        unsafe_allow_html=True,
                    )
                else:
                    st.warning("No hay noticias disponibles de FutureTools o Ben's Bites.")

        with news_tabs[1]:
            st.header("Hacker News")
            if ycombinator_news_df.empty:
                st.warning("No hay noticias disponibles de Hacker News.")
            else:
                # Ensure published_date column exists
                if "published_date" not in ycombinator_news_df.columns:
                    # Check if published_at exists and use it as a fallback
                    if "published_at" in ycombinator_news_df.columns:
                        ycombinator_news_df["published_date"] = pd.to_datetime(ycombinator_news_df["published_at"], errors="coerce")
                    else:
                        # Create a default date column
                        ycombinator_news_df["published_date"] = pd.Timestamp("now")
                
                # Sort by published_date (now guaranteed to exist)
                display_news_df = ycombinator_news_df.sort_values("published_date", ascending=False)

                display_news_df["Ver Noticia"] = display_news_df["url"].apply(lambda x: make_clickable(x, "Leer más"))
                
                # Format date for display
                display_news_df["published_display"] = display_news_df["published_date"].dt.strftime('%Y-%m-%d %H:%M')

                display_news_df_final = display_news_df[["title", "published_display", "source", "Ver Noticia"]].copy()
                
                display_news_df_final.rename(
                    columns={
                        "title": "Título",
                        "published_display": "Fecha de Publicación",
                        "source": "Fuente",
                    },
                    inplace=True,
                )
                
                st.markdown(
                    display_news_df_final.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )

        with news_tabs[2]:
            st.header("Medium GenAI")
            if medium_news_df.empty:
                st.warning("No hay noticias disponibles de Medium sobre IA.")
            else:
                display_news_df = medium_news_df.copy() # Work with a copy
                
                # Ensure we have a consistent date column
                if "published_date" not in display_news_df.columns:
                    # Convert published_at to datetime if it exists
                    if "published_at" in display_news_df.columns:
                        display_news_df["published_date"] = pd.to_datetime(display_news_df["published_at"], errors="coerce")
                        # Sort by converted date
                        display_news_df = display_news_df.sort_values("published_date", ascending=False)
                    else:
                        # If no date column exists, don't sort
                        pass
                else:
                    # Sort by existing published_date
                    display_news_df = display_news_df.sort_values("published_date", ascending=False)

                display_news_df["Ver Noticia"] = display_news_df["url"].apply(lambda x: make_clickable(x, "Leer más"))
                
                # Determine which date column to display
                date_col = "published_date" if "published_date" in display_news_df.columns else "published_at"
                
                if date_col in display_news_df.columns:
                    # Format dates for display if they're datetime
                    if pd.api.types.is_datetime64_any_dtype(display_news_df[date_col]):
                        display_news_df["formatted_date"] = display_news_df[date_col].dt.strftime('%Y-%m-%d %H:%M')
                        display_col = "formatted_date"
                    else:
                        display_col = date_col
                    
                    # Create final display dataframe
                    display_news_df_final = display_news_df[["title", display_col, "source", "Ver Noticia"]].copy()

                    display_news_df_final.rename(
                        columns={
                            "title": "Título",
                            display_col: "Fecha de Publicación",
                            "source": "Fuente",
                        },
                        inplace=True,
                    )
                else:
                    # No date column available
                    display_news_df_final = display_news_df[["title", "source", "Ver Noticia"]].copy()
                    
                    display_news_df_final.rename(
                        columns={
                            "title": "Título",
                            "source": "Fuente",
                        },
                        inplace=True,
                    )

                # Display the final DataFrame as HTML
                st.markdown(
                    display_news_df_final.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )

with tab3:
    logger.info("Rendering Juegos tab")
    st.header("🎮 Juegos")

    if deals_df.empty:
        logger.warning("No deals data available to display")
        st.warning("No hay datos de ofertas disponibles.")
    else:
        # Calculate summary statistics
        total_deals = len(deals_df)
        total_bundles = len(bundles_df)
        total_giveaways = len(giveaways_df)

        # Add table selector
        selected_tables = st.multiselect(
            "Selecciona las tablas a mostrar",
            ["Ofertas de Juegos", "Paquetes de Juegos", "Juegos Gratuitos"],
            default=["Ofertas de Juegos", "Paquetes de Juegos", "Juegos Gratuitos"],
            help="Elige qué tablas quieres ver en el panel"
        )

        st.markdown('<div class="deals-container">', unsafe_allow_html=True)

        # Display deals in responsive columns
        if "Ofertas de Juegos" in selected_tables:
            st.markdown('<div class="deals-column">', unsafe_allow_html=True)
            st.markdown('<div class="deals-card">', unsafe_allow_html=True)
            st.header("Ofertas de Juegos")
            if not deals_df.empty:
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
                    display_deals_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No hay ofertas disponibles.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Display bundles in responsive columns
        if "Paquetes de Juegos" in selected_tables:
            st.markdown('<div class="deals-column">', unsafe_allow_html=True)
            st.markdown('<div class="deals-card">', unsafe_allow_html=True)
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
                    display_bundles_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No hay paquetes disponibles.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Display giveaways in responsive columns
        if "Juegos Gratuitos" in selected_tables:
            st.markdown('<div class="deals-column">', unsafe_allow_html=True)
            st.markdown('<div class="deals-card">', unsafe_allow_html=True)
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
                    display_giveaways_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No hay juegos gratuitos disponibles.")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


with tab4:
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

with tab5:
    logger.info("Rendering Valencia Events tab")
    st.header("🏙️ Eventos en Valencia")
    
    @st.cache_data(ttl=3600)
    def get_valencia_events_data():
        """Fetch and process Valencia events data"""
        logger.info("Loading Valencia events data")
        valencia_events_df = load_data(VALENCIA_EVENTS_FILE)
        
        if not valencia_events_df.empty:
            # Convert dates if available
            if "start_date" in valencia_events_df.columns:
                valencia_events_df["start_date"] = pd.to_datetime(
                    valencia_events_df["start_date"], format="%d/%m/%Y", errors="coerce"
                )
            if "end_date" in valencia_events_df.columns:
                valencia_events_df["end_date"] = pd.to_datetime(
                    valencia_events_df["end_date"], format="%d/%m/%Y", errors="coerce"
                )
                
        return valencia_events_df
    
    # Load Valencia events data
    valencia_events_df = get_valencia_events_data()
    logger.info(f"Loaded {len(valencia_events_df)} Valencia events")
    
    if valencia_events_df.empty:
        logger.warning("No Valencia events data available")
        st.warning("No hay datos de eventos disponibles.")
    else:
        # Filters
        search_term = st.text_input("🔍 Buscar en títulos de eventos", "")
        
        # Category filter if categories are available
        categories = valencia_events_df["category"].dropna().unique().tolist()
        if categories:
            selected_categories = st.multiselect(
                "Filtrar por categoría",
                ["Todas"] + categories,
                default=["Todas"]
            )
        
        # Apply filters
        filtered_events_df = valencia_events_df.copy()
        
        if search_term:
            filtered_events_df = filtered_events_df[
                filtered_events_df["title"].str.contains(
                    search_term, case=False, na=False
                )
            ]
        
        if categories and selected_categories and "Todas" not in selected_categories:
            filtered_events_df = filtered_events_df[
                filtered_events_df["category"].isin(selected_categories)
            ]
        
        logger.info(f"Filtered to {len(filtered_events_df)} Valencia events")
        
        # Display results
        if filtered_events_df.empty:
            logger.warning("No event matches found")
            st.warning("No hay eventos que coincidan con los filtros seleccionados.")
        else:
            # Sort by start date if available
            if "start_date" in filtered_events_df.columns:
                filtered_events_df = filtered_events_df.sort_values(
                    by="start_date", ascending=True, na_position="last"
                )
            
            # Display events in a grid format similar to videos
            num_cols = get_responsive_cols()
            for i in range(0, len(filtered_events_df), num_cols):
                cols = st.columns(num_cols)
                for j, (_, event) in enumerate(filtered_events_df.iloc[i:i + num_cols].iterrows()):
                    with cols[j % num_cols]:
                        with st.container():
                            st.markdown(f"<div class='card'>", unsafe_allow_html=True)
                            st.subheader(event["title"])
                            
                            # Display dates if available
                            if pd.notna(event.get("date_text")):
                                st.write(f"**Fechas:** {event.get('date_text', 'No especificado')}")
                            
                            # Display category if available
                            if pd.notna(event.get("category")) and event.get("category") != "":
                                st.write(f"**Categoría:** {event.get('category', 'No especificado')}")
                            
                            # Display source
                            st.write(f"**Fuente:** {event.get('source', 'No especificado')}")
                            
                            # Add link to event
                            if "url" in event and pd.notna(event["url"]):
                                st.markdown(make_clickable(event["url"], "Ver evento"), unsafe_allow_html=True)
                            
                            st.markdown("</div>", unsafe_allow_html=True)
            
            # Provide option to view as table
            if st.checkbox("Ver como tabla"):
                display_cols = ["title", "date_text", "category", "source"]
                display_df = filtered_events_df[display_cols].copy()
                
                # Add URL column with clickable links
                display_df["Ver evento"] = filtered_events_df["url"].apply(
                    lambda x: make_clickable(x, "Ver")
                )
                
                # Rename columns for display
                display_df.rename(
                    columns={
                        "title": "Título",
                        "date_text": "Fechas",
                        "category": "Categoría",
                        "source": "Fuente",
                    },
                    inplace=True,
                )
                
                # Display as HTML table
                st.markdown(
                    display_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )

with tab6:
    logger.info("Rendering Admin tab")
    st.header("⚙️ Admin Panel")
    
    st.markdown("""
    <div class="card">
        <h3>Panel de Administración</h3>
        <p>Esta sección permite ejecutar tareas de administración del sistema.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Ejecutar todos los scrapers"):
        try:
            st.info("Ejecutando scrapers...")
            # Run all scrapers
            scripts = [
                "../../../src/etl/games/games_get_deals.py",
                "../../../src/etl/news/news_get_futuretools.py",
                "../../../src/etl/news/news_get_ycombinator.py",
                "../../../src/etl/news/news_get_genai_medium.py",
                "../../../src/etl/news/news_get_bensbites.py"
            ]
            
            for script in scripts:
                subprocess.run(["python3", script])
                
            st.success("Todos los scrapers ejecutados correctamente")
            st.rerun()
        except Exception as e:
            st.error(f"Error al ejecutar los scrapers: {str(e)}")
    
    # Add section to scan YouTube directories
    st.subheader("Actualización de videos de YouTube")
    
    # Get available YouTube categories
    youtube_categories = [d for d in os.listdir(VIDEOS_DATA_DIR) 
                        if os.path.isdir(os.path.join(VIDEOS_DATA_DIR, d))]
    
    # Option to update all channels
    if st.button("Actualizar todos los canales de YouTube"):
        try:
            st.info("Ejecutando actualización de videos...")
            # Get all category directories
            categories = youtube_categories
            
            success_count = 0
            for category in categories:
                try:
                    script_path = f"../../../src/etl/youtube/youtube_get_videos.py"
                    subprocess.run(["python3", script_path, "--category", category])
                    success_count += 1
                except Exception as category_e:
                    st.warning(f"Error actualizando categoría {category}: {str(category_e)}")
            
            st.success(f"Actualizadas {success_count} de {len(categories)} categorías correctamente")
            st.rerun()
        except Exception as e:
            st.error(f"Error al actualizar videos: {str(e)}")
    
    # Option to update specific channels
    st.subheader("Actualizar categoría específica")
    
    # Select a category to update
    selected_category = st.selectbox(
        "Seleccionar categoría",
        options=youtube_categories,
        help="Selecciona una categoría de videos para actualizar"
    )
    
    if st.button("Actualizar categoría seleccionada"):
        try:
            st.info(f"Actualizando videos de la categoría: {selected_category}")
            script_path = f"../../../src/etl/youtube/youtube_get_videos.py"
            result = subprocess.run(
                ["python3", script_path, "--category", selected_category],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.success(f"Categoría {selected_category} actualizada correctamente")
                st.text(result.stdout)
            else:
                st.error(f"Error al actualizar la categoría {selected_category}")
                st.text(result.stderr)
            st.rerun()
        except Exception as e:
            st.error(f"Error al actualizar videos: {str(e)}")

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
