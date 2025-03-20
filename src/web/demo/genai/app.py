import streamlit as st
import pandas as pd
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("FutureNewsApp")

# Constants
DATA_DIR = "../../../../data/futuretools"
NEWS_FILE = os.path.join(DATA_DIR, "futuretoolsnews.json")

logger.info("Iniciando Panel de Noticias")

# Page config
st.set_page_config(
    page_title="Panel de Noticias de Tecnología",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_data(file_path):
    """Load and parse JSON data file"""
    try:
        if os.path.exists(file_path):
            logger.info(f"Cargando datos desde {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            logger.info(f"Se cargaron {len(df)} registros")
            return df
        
        logger.error(f"Archivo no encontrado: {file_path}")
        st.error(f"Archivo no encontrado: {file_path}")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error al cargar datos: {str(e)}")
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

def make_clickable(link, text=None):
    """Generate HTML for clickable link"""
    if pd.isna(link):
        return "N/A"
    text = text if text else link
    return f'<a href="{link}" target="_blank">{text}</a>'

# Header
st.title("📰 Panel de Noticias de Tecnología")
st.markdown(
    """
    <div class="card">
        <p>Este panel muestra las últimas noticias de tecnología y avances en IA de 
        <a href="https://futuretools.io/news" target="_blank">FutureTools.io</a>.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Load and cache data
@st.cache_data(ttl=3600)
def get_data():
    """Fetch and process news data"""
    logger.info("Cargando datos de noticias")
    news_df = load_data(NEWS_FILE)

    if not news_df.empty:
        news_df['published_date'] = pd.to_datetime(news_df['published_at'])
        
    return news_df

news_df = get_data()
logger.info(f"Se cargaron {len(news_df)} artículos")

# Main content
st.header("Noticias Tecnológicas")

if news_df.empty:
    logger.warning("No hay datos de noticias disponibles")
    st.warning("No hay datos de noticias disponibles.")
else:
    # Filters
    search_term = st.text_input("🔍 Buscar en títulos", "")
    
    date_range = st.date_input(
        "Rango de fechas",
        [news_df['published_date'].min(), news_df['published_date'].max()],
        min_value=news_df['published_date'].min().date(),
        max_value=news_df['published_date'].max().date()
    )

    # Apply filters
    filtered_df = news_df.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_term, case=False, na=False)
        ]

    if len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['published_date'].dt.date >= date_range[0]) &
            (filtered_df['published_date'].dt.date <= date_range[1])
        ]

    logger.info(f"Filtrado a {len(filtered_df)} resultados")

    # Display results
    if filtered_df.empty:
        logger.warning("No se encontraron coincidencias")
        st.warning("No hay noticias que coincidan con los filtros seleccionados.")
    else:
        # Prepare display data
        display_df = filtered_df[['title', 'published_at', 'source']].copy()
        display_df['Ver Noticia'] = filtered_df['url'].apply(
            lambda x: make_clickable(x, "Leer más")
        )

        # Show table
        st.markdown(
            display_df.to_html(escape=False, index=False),
            unsafe_allow_html=True
        )

        # Download button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar datos como CSV",
            data=csv,
            file_name="noticias_tecnologia.csv",
            mime="text/csv"
        )

# Footer
st.markdown(
    """
    <div style="text-align: center; margin-top: 30px; padding: 20px; opacity: 0.7;">
        <p>Datos obtenidos de <a href="https://futuretools.io/news" target="_blank">FutureTools.io</a></p>
    </div>
    """,
    unsafe_allow_html=True
)

logger.info("Renderizado del panel completado")