import subprocess
import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
import plotly.express as px
from urllib.parse import unquote
import sys

# Add the project root to the path to ensure imports work correctly
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
)


from src.utils.logging import get_logger



# Import centralized logging utility

# Initialize logger for the Streamlit app
logger = get_logger("GameDealsApp")

# Define data paths
GAMES_DATA_DIR = "../../../data/games"
FUTURETOOLS_NEWS_DATA_DIR = "../../../data/futuretools"
YCOMBINATOR_NEWS_DATA_DIR = "../../../data/hackernews"
VIDEOS_DATA_DIR = "../../../data/youtube"

DEALS_FILE = os.path.join(GAMES_DATA_DIR, "deals.json")
BUNDLES_FILE = os.path.join(GAMES_DATA_DIR, "bundles.json")
GIVEAWAYS_FILE = os.path.join(GAMES_DATA_DIR, "giveaways.json")
FUTURETOOLS_NEWS_FILE = os.path.join(FUTURETOOLS_NEWS_DATA_DIR, "futuretoolsnews.json")
YCOMBINATOR_NEWS_FILE = os.path.join(YCOMBINATOR_NEWS_DATA_DIR, "hackernews.json")
VIDEOS_FILE = os.path.join(VIDEOS_DATA_DIR, "youtube_videos.json")

# Log application startup
logger.info("Starting Watchtower Dashboard")

# Set page configuration
st.set_page_config(
    page_title="Panel watchtower",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Helper functions
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
st.title("🎮 Panel de Ofertas de Juegos")
st.markdown(
    """
<div class="card">
    <p>Este panel muestra información sobre ofertas de juegos, bundles y regalos de <a href="https://isthereanydeal.com/" target="_blank">IsThereAnyDeal</a>. 
    Navega por las pestañas para explorar diferentes tipos de ofertas de juegos.</p>
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
tab3, tab2, tab1 = st.tabs(
    ["📺 Videos", "📰 Noticias", "🎮 Juegos" ]
)

with tab1: # Juegos
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

        # Display summary statistics
        col1, col2, col3 = st.columns(3)
        # Set column height to 400º
        col2.markdown("<style>div.stDataFrame {height: 400px;}</style>", unsafe_allow_html=True)
        col3.markdown("<style>div.stDataFrame {height: 400px;}</style>", unsafe_allow_html=True)

        with col1:
            col1.markdown("<style>div.stDataFrame {height: 400px;}</style>", unsafe_allow_html=True)
        
            # Apply filters
            filtered_deals_df = deals_df.copy()

            st.header("Ofertas de Juegos")

            # Order by discount value
            filtered_deals_df = filtered_deals_df.sort_values(by="discount_value", ascending=False)

            # Prepare display dataframe
            display_deals_df = filtered_deals_df[
                ["title", "price", "discount", "store", "published_date"]
            ].copy()

            # Add clickable links
            display_deals_df["Ver Oferta"] = filtered_deals_df["link"].apply(
                lambda x: make_clickable(x, "Ver")
            )

            # Format price with currency symbol
            if "price" in display_deals_df.columns:
                display_deals_df["price"] = display_deals_df["price"].apply(
                    lambda x: f"€{x:.2f}" if pd.notna(x) else "N/A"
                )

            # Change column names to spanish
            display_deals_df.rename(columns={
                "title": "Título",
                "price": "Precio",
                "discount": "Descuento",
                "store": "Tienda",
                "published_date": "Fecha de Publicación"
            }, inplace=True)
            
            # Display the dataframe with clickable links
            st.markdown(
                display_deals_df.to_html(escape=False, index=False), unsafe_allow_html=True
            )

        with col2:
            logger.info("Rendering Bundles subtab")
            st.header("Paquetes de Juegos")

            if bundles_df.empty:
                logger.warning("No bundles data available to display")
                st.warning("No hay datos de paquetes disponibles.")
            else:
                # Apply filters
                filtered_bundles_df = bundles_df.copy()

            # Order by published date
            filtered_bundles_df = filtered_bundles_df.sort_values(by="published_date", ascending=False)


            logger.info(
                f"Bundles filtered: {len(filtered_bundles_df)} results after applying filters"
            )

            # Prepare display dataframe
            if "game_count" in filtered_bundles_df.columns:
                display_bundles_df = filtered_bundles_df[
                    ["title", "price", "game_count", "published_date"]
                ].copy()
            else:
                display_bundles_df = filtered_bundles_df[["title", "price", "published_date"]].copy()

            # Add clickable links
            display_bundles_df["Ver Paquete"] = filtered_bundles_df["link"].apply(
                lambda x: make_clickable(x, "Ver")
            )

            # Format price with currency symbol
            if "price" in display_bundles_df.columns:
                display_bundles_df["price"] = display_bundles_df["price"].apply(
                    lambda x: f"€{x:.2f}" if pd.notna(x) else "N/A"
                )

            # Change column names to spanish
            display_bundles_df.rename(columns={
                "title": "Título",
                "price": "Precio",
                "game_count": "Juegos en el Paquete",
                "published_date": "Fecha de Publicación"
            }, inplace=True)

            # Display the dataframe with clickable links
            st.markdown(
                display_bundles_df.to_html(escape=False, index=False), unsafe_allow_html=True
            )


        with col3:
            logger.info("Rendering Giveaways subtab")
            st.header("Juegos Gratuitos")

            if giveaways_df.empty:
                logger.warning("No giveaways data available to display")
                st.warning("No hay datos de juegos gratuitos disponibles.")
            else:
                # Filter for active giveaways
                
                filtered_giveaways_df = giveaways_df.copy()
                # Fix the filtering for active giveaways
                
                # Display data
                if filtered_giveaways_df.empty:
                        logger.warning("No giveaways data available")
                        st.warning("No hay datos de juegos gratuitos disponibles.")
                else:
                    # Prepare display dataframe
                    if "expires_date" in filtered_giveaways_df.columns:
                        display_giveaways_df = filtered_giveaways_df[
                            ["title", "published_date", "expires_date"]
                        ].copy()
                    else:
                        display_giveaways_df = filtered_giveaways_df[["title", "published_date"]].copy()

                    # Add clickable links
                    display_giveaways_df["Obtener Juego"] = filtered_giveaways_df["link"].apply(
                        lambda x: make_clickable(x, "Reclamar")
                    )

                    # Change column names to spanish
                    display_giveaways_df.rename(columns={
                        "title": "Título",
                        "published_date": "Fecha de Publicación",
                        "expires_date": "Fecha de Expiración"
                    }, inplace=True)
    
                    # Display the dataframe with clickable links
                    st.markdown(
                        display_giveaways_df.to_html(escape=False, index=False), unsafe_allow_html=True
                    )


with tab2:
    @st.cache_data(ttl=3600)
    def get_news_data():
        """Fetch and process news data"""
        logger.info("Loading news data")
        futuretools_news_df = load_data(FUTURETOOLS_NEWS_FILE)
        ycombinator_news_df = load_data(YCOMBINATOR_NEWS_FILE)
        
        if not futuretools_news_df.empty:
            futuretools_news_df['published_date'] = pd.to_datetime(futuretools_news_df['published_at'])

        if not ycombinator_news_df.empty:
            ycombinator_news_df['published_date'] = pd.to_datetime(ycombinator_news_df['published_at'])
            
        return futuretools_news_df, ycombinator_news_df
    


    logger.info("Rendering News tab")
    st.header("📰 Noticias Generative AI")
    
    # Add a button to call the script to scrape the data
    if st.button("(Re)cargar datos de noticias"):
        logger.info("Cargando datos de noticias...")
        # Call the script to scrape the data and wait until it is finished
        subprocess.run(["python3", "../../../src/etl/news/news_get_futuretools.py"])
        subprocess.run(["python3", "../../../src/etl/news/news_get_ycombinator.py"])
        # Wait until the script is finished
        logger.info("Datos de noticias cargados correctamente")
        st.success("Datos de noticias cargados correctamente")
        # Refresh the data
        futuretools_news_df, ycombinator_news_df = get_news_data()
        logger.info("Datos de noticias actualizados correctamente")
        # Refresh the page
        st.rerun()


    # Load news data
    futuretools_news_df, ycombinator_news_df = get_news_data()

    logger.info(f"Loaded {len(futuretools_news_df)} futuretools news articles")
    logger.info(f"Loaded {len(ycombinator_news_df)} ycombinator news articles")
    
    if futuretools_news_df.empty and ycombinator_news_df.empty:
        logger.warning("No news data available")
        st.warning("No hay datos de noticias disponibles.")
    else:
        news_futuretools_col, news_ycombinator_col = st.columns([3, 2])
        with news_futuretools_col:
            # Display results
            if futuretools_news_df.empty:
                logger.warning("No matches found")
                st.warning("No hay noticias que coincidan con los filtros seleccionados.")
            else:
                # Prepare display data
                display_news_df = futuretools_news_df[['title', 'published_at', 'source']].copy()
            
                # Add clickable links
                display_news_df['Ver Noticia'] = futuretools_news_df['url'].apply(
                    lambda x: make_clickable(x, "Leer más")
                )
                
                # Rename columns to Spanish
                display_news_df.rename(columns={
                    'title': 'Título',
                    'published_at': 'Fecha de Publicación',
                    'source': 'Fuente'
                }, inplace=True)
            
                # Sort by published_date
                display_news_df = display_news_df.sort_values(by='Fecha de Publicación', ascending=False)
                # Show table
                st.markdown(
                    display_news_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True
                )
            
        with news_ycombinator_col:
            # Display results
            if ycombinator_news_df.empty:
                logger.warning("No matches found")
                st.warning("No hay noticias que coincidan con los filtros seleccionados.")
            else:
                # Prepare display data
                display_news_df = ycombinator_news_df[['title', 'published_at', 'source']].copy()

                # Add clickable links
                display_news_df['Ver Noticia'] = ycombinator_news_df['url'].apply(
                    lambda x: make_clickable(x, "Leer más")
                )

                # Rename columns to Spanish
                display_news_df.rename(columns={
                    'title': 'Título',
                    'published_at': 'Fecha de Publicación',
                    'source': 'Fuente'
                }, inplace=True)

                # Show table
                st.markdown(
                    display_news_df.to_html(escape=False, index=False),
                    unsafe_allow_html=True
                )

with tab3:
    logger.info("Rendering Videos tab")
    st.header("📺 Videos de Youtube")
    
    # Load videos data
    @st.cache_data(ttl=3600)
    def get_videos_data():
        """Fetch and process videos data"""
        logger.info("Loading videos data")
        videos_df = load_data(VIDEOS_FILE)
        
        if not videos_df.empty:
            videos_df['published_date'] = pd.to_datetime(videos_df['published_at'])
            # Add thumbnail URLs if available
            if 'thumbnail_url' in videos_df.columns:
                videos_df['thumbnail'] = videos_df['thumbnail_url']
            
        return videos_df

    videos_df = get_videos_data()
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
            [videos_df['published_date'].min(), videos_df['published_date'].max()],
            min_value=videos_df['published_date'].min().date(),
            max_value=videos_df['published_date'].max().date()
        )

        # Apply filters
        filtered_videos_df = videos_df.copy()
        
        if search_term:
            filtered_videos_df = filtered_videos_df[
                filtered_videos_df['title'].str.contains(search_term, case=False, na=False)
            ]

        if len(date_range) == 2:
            filtered_videos_df = filtered_videos_df[
                (filtered_videos_df['published_date'].dt.date >= date_range[0]) &
                (filtered_videos_df['published_date'].dt.date <= date_range[1])
            ]

        logger.info(f"Filtered to {len(filtered_videos_df)} video results")
        
        # Display results
        if filtered_videos_df.empty:
            logger.warning("No video matches found")
            st.warning("No hay videos que coincidan con los filtros seleccionados.")
        else:
            # Display videos in a grid format
            num_cols = 8  # Number of columns in the grid
            rows = [filtered_videos_df.iloc[i:i+num_cols] for i in range(0, len(filtered_videos_df), num_cols)]
            
            for row_data in rows:
                cols = st.columns(num_cols)
                
                for i, (_, video) in enumerate(row_data.iterrows()):
                    if i < len(cols):
                        with cols[i]:
                            st.subheader(video['title'])
                            st.write(f"**Canal:** {video.get('channel', 'N/A')}")
                            st.write(f"**Publicado:** {video.get('published_at', 'N/A')}")
                            if 'url' in video and pd.notna(video['url']):
                                st.markdown(make_clickable(video['url'], "Ver en YouTube"), unsafe_allow_html=True)
                            st.markdown("---")




# Footer
st.markdown(
    """
<div style="text-align: center; margin-top: 30px; padding: 20px; opacity: 0.7;">
    <p>Datos obtenidos de <a href="https://isthereanydeal.com/" target="_blank">IsThereAnyDeal</a>, <a href="https://futuretools.io/news" target="_blank">FutureTools.io</a> y <a href="https://www.youtube.com/" target="_blank">Youtube</a></p>
</div>
""",
    unsafe_allow_html=True,
)
logger.info("Dashboard rendering completed")
