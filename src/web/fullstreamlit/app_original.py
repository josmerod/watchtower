"""
Watchtower Streamlit Application - Main file
Enhanced version with improved UX/UI, better navigation, and streamlined performance.
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
import time

# Add the project root to the path to ensure imports work correctly
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
    tech_events_tab
)

# Import enhanced components
from src.web.fullstreamlit.components import enhanced_innovation_tab

# Initialize logger and data service
logger = get_logger("WatchtowerApp")
data_service = create_ultra_optimized_service(logger)

# Set page configuration - MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="Watchtower: Monitor de Tendencias y Noticias",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Utility function to safely get/set session state
def safe_get_session_state(key: str, default_value=None):
    """Safely get a session state value with a default"""
    if key not in st.session_state:
        st.session_state[key] = default_value
    return st.session_state[key]

def safe_set_session_state(key: str, value):
    """Safely set a session state value"""
    st.session_state[key] = value

# Apply CSS styles with improvements
st.markdown(get_main_style(), unsafe_allow_html=True)

# Custom CSS for better UX
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        color: white;
    }
    
    .metric-title {
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        opacity: 0.9;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0;
    }
    
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .status-online {
        background-color: #10B981;
        color: white;
    }
    
    .status-loading {
        background-color: #F59E0B;
        color: white;
    }
    
    .status-error {
        background-color: #EF4444;
        color: white;
    }
    
    .tab-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding: 1rem;
        background: rgba(45, 43, 85, 0.1);
        border-radius: 8px;
        border-left: 4px solid #A37FFF;
    }
    
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
    
    .quick-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state with error handling
safe_get_session_state('viewport_width', 1200)
safe_get_session_state('last_refresh', datetime.now())
safe_get_session_state('data_status', {})

# Enhanced header with real-time status
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    st.title("🗼 Watchtower: Monitor de Tendencias y Noticias")

with col2:
    if st.button("🔄 Actualizar Datos", help="Recargar todos los datos"):
        st.cache_data.clear()
        # Update last refresh timestamp
        safe_set_session_state('last_refresh', datetime.now())
        st.rerun()

with col3:
    st.markdown(f"""
    <div class="status-indicator status-online">
        🟢 Online
    </div>
    """, unsafe_allow_html=True)

# Enhanced introduction with quick stats
st.markdown(
    """
<div class="card" style="background: linear-gradient(135deg, #2D2B55 0%, #3D3B75 100%); padding: 20px; border-radius: 12px; border-left: 5px solid #A37FFF; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3); margin-bottom: 2rem;">
    <h3 style="color: #A37FFF; margin-bottom: 1rem;">Panel de Control Integrado</h3>
    <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #E2E8F0;">
        Monitor completo de tendencias en tecnología, IA generativa, desarrollo, juegos, cursos y más. 
        Datos actualizados en tiempo real desde múltiples fuentes especializadas.
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# Sidebar for navigation and filters
with st.sidebar:
    st.header("🧭 Navegación Rápida")
    
    # Quick stats in sidebar
    st.subheader("📊 Estadísticas Rápidas")
    
    # Data loading with progress
    with st.spinner("Cargando estadísticas..."):
        try:
            # Quick data overview without full loading
            last_refresh = safe_get_session_state('last_refresh', datetime.now())
            st.metric("Última Actualización", 
                     last_refresh.strftime("%H:%M"))
        except Exception as e:
            st.error("Error cargando estadísticas")
    
    st.divider()
    
    # Navigation sections
    st.subheader("📱 Secciones Principales")
    nav_options = {
        "🔖 Dashboard": "Vista general y accesos rápidos",
        "📺 Contenido Multimedia": "Videos y material audiovisual",
        "📰 Noticias Tech": "Últimas noticias del sector",
        "🎮 Gaming": "Ofertas, bundles y giveaways",
        "🎓 Educación": "Cursos y recursos de aprendizaje"
    }
    
    for option, description in nav_options.items():
        st.markdown(f"**{option}**")
        st.caption(description)
    
    st.divider()
    
    st.subheader("🔍 Herramientas")
    tools_options = {
        "👨‍💻 Comunidades Dev": "DEV, Product Hunt, etc.",
        "🚀 Innovation Hub": "Tendencias y nuevas tecnologías",
        "₿ Crypto Sentiment": "Análisis de sentimiento crypto",
        "📚 Investigación ArXiv": "Papers y búsqueda académica",
        "👁️ Watchers": "Monitoreo automatizado",
        "🏙️ Eventos Valencia": "Eventos locales tech"
    }
    
    for option, description in tools_options.items():
        st.markdown(f"**{option}**")
        st.caption(description)

# Pre-load commonly used data with better error handling and loading states
@st.cache_data(ttl=1800, show_spinner=False)  # Reduced TTL for fresher data
def get_cached_data():
    """Pre-load and cache all data for better performance"""
    logger.info("Loading application data...")
    data_status = {}
    
    try:
        data = {}
        
        # Load each dataset with individual error handling
        datasets = {
            'games': ('Juegos', data_service.get_games_data),
            'courses': ('Cursos', data_service.get_courses_data),
            'news': ('Noticias', data_service.get_news_data),
            'videos': ('Videos', data_service.get_videos_data),
            'arxiv': ('ArXiv', data_service.get_arxiv_data),
            'events': ('Eventos', data_service.get_events_data)
        }
        
        for key, (name, func) in datasets.items():
            try:
                data[key] = func()
                data_status[key] = 'success'
                logger.info(f"Successfully loaded {name} data")
            except Exception as e:
                logger.error(f"Error loading {name} data: {str(e)}")
                data[key] = pd.DataFrame() if 'events' in key or 'arxiv' in key else {}
                data_status[key] = 'error'
        
        st.session_state.data_status = data_status
        return data
        
    except Exception as e:
        logger.error(f"Critical error loading application data: {str(e)}")
        st.session_state.data_status = {k: 'error' for k in datasets.keys()}
        return {}

# Load data with loading indicator
data_placeholder = st.empty()
with data_placeholder.container():
    with st.spinner("🔄 Cargando datos de todas las fuentes..."):
        try:
            cached_data = get_cached_data()
            logger.info("Successfully loaded all application data")
        except Exception as e:
            logger.error(f"Error loading application data: {str(e)}")
            cached_data = {}
            st.error("❌ Error cargando datos. Algunas funcionalidades pueden estar limitadas.")

data_placeholder.empty()

# Display data status indicators
data_status = safe_get_session_state('data_status', {})
if data_status:
    status_cols = st.columns(len(data_status))
    for idx, (source, status) in enumerate(data_status.items()):
        with status_cols[idx]:
            if status == 'success':
                st.success(f"✅ {source.title()}")
            else:
                st.error(f"❌ {source.title()}")

# Reorganized tabs with better grouping and naming
main_tabs = st.tabs([
    "🔖 Dashboard", 
    "📺 Multimedia", 
    "📰 Tech News", 
    "🎮 Gaming",
    "🎓 Educación",
    "📅 Tech Events",
    "👨‍💻 Dev Hub",
    "🛡️ Security",
    "🚀 Innovation",
    "₿ Crypto",
    "📚 ArXiv Research", 
    "👁️ Monitoring", 
    "🏙️ Valencia", 
    "⚙️ Admin"
])

# Helper function to render tab with error handling
def render_tab_safely(tab_name, render_func, *args, **kwargs):
    """Safely render a tab with error handling and loading states"""
    try:
        logger.info(f"Rendering {tab_name} tab")
        
        # Render the actual content without the problematic header
        render_func(*args, **kwargs)
        
    except Exception as e:
        logger.error(f"Error rendering {tab_name} tab: {str(e)}")
        st.error(f"❌ Error cargando {tab_name}. Intenta actualizar la página.")
        st.exception(e)

# Render each tab with improved error handling
with main_tabs[0]:  # Dashboard
    render_tab_safely("Dashboard", shortcuts_tab.render, logger, data_service)

with main_tabs[1]:  # Multimedia 
    videos_data = cached_data.get('videos', {})
    render_tab_safely("Multimedia", videos_tab.render, logger, videos_data)

with main_tabs[2]:  # Tech News
    render_tab_safely("Tech News", news_tab.render, logger)

with main_tabs[3]:  # Gaming
    games_data = cached_data.get('games', (pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
    if isinstance(games_data, tuple) and len(games_data) == 3:
        deals_df, bundles_df, giveaways_df = games_data
    else:
        deals_df = bundles_df = giveaways_df = pd.DataFrame()
    render_tab_safely("Gaming", games_tab.render, deals_df, bundles_df, giveaways_df, logger)

with main_tabs[4]:  # Educación
    courses_data = cached_data.get('courses', {})
    render_tab_safely("Educación", courses_tab.render, courses_data, logger)

with main_tabs[5]:  # Tech Events
    render_tab_safely("Tech Events & Conference Intelligence", tech_events_tab.render, logger, data_service)

with main_tabs[6]:  # Dev Hub
    render_tab_safely("Dev Communities", dev_communities_tab.render, logger)

with main_tabs[7]:  # Security
    render_tab_safely("Security Intelligence", security_tab.render, logger, data_service)

with main_tabs[8]:  # Innovation
    render_tab_safely("Innovation & Tech", enhanced_innovation_tab.render, logger, data_service)

with main_tabs[9]:  # Crypto
    render_tab_safely("Crypto Sentiment", crypto_tab.render, logger)

with main_tabs[10]:  # ArXiv Research (combined tab)
    
    # Sub-tabs for ArXiv functionality
    arxiv_subtabs = st.tabs(["🚀 Enhanced Intelligence", "📄 Papers Recientes", "🔍 Búsqueda Avanzada"])
    
    with arxiv_subtabs[0]:
        render_tab_safely("Enhanced ArXiv Intelligence", enhanced_arxiv_papers.display_enhanced_papers)
    
    with arxiv_subtabs[1]:
        render_tab_safely("ArXiv Papers", arxiv_papers.display)
    
    with arxiv_subtabs[2]:
        render_tab_safely("ArXiv Search", arxiv_search.display)

with main_tabs[11]:  # Monitoring
    render_tab_safely("Monitoring", monitoring_tab.render, logger)

with main_tabs[12]:  # Valencia
    render_tab_safely("Eventos Valencia", events_tab.render, logger)

with main_tabs[13]:  # Admin
    render_tab_safely("Admin", admin_tab.render, logger)

# Enhanced footer with better information and styling
st.markdown("---")

# Performance metrics
perf_cols = st.columns(4)
with perf_cols[0]:
    # Safely get last refresh time
    last_refresh = safe_get_session_state('last_refresh', datetime.now())
    st.metric("🔄 Última Actualización", 
             last_refresh.strftime("%H:%M:%S"))

with perf_cols[1]:
    data_status = safe_get_session_state('data_status', {})
    data_sources_count = len([k for k, v in data_status.items() if v == 'success'])
    total_sources = len(data_status)
    st.metric("📊 Fuentes Activas", f"{data_sources_count}/{total_sources}")

with perf_cols[2]:
    st.metric("⚡ Estado Sistema", "Operativo")

with perf_cols[3]:
    if st.button("🔄 Actualizar Todo", key="footer_refresh"):
        st.cache_data.clear()
        safe_set_session_state('last_refresh', datetime.now())
        st.rerun()

# Enhanced footer with data sources
st.markdown(
    f"""
<div style="margin-top: 2rem; padding: 25px; background: linear-gradient(135deg, #2D2B55 0%, #1a1844 100%); border-radius: 12px; box-shadow: 0 -4px 15px rgba(0, 0, 0, 0.3); border-top: 3px solid #A37FFF;">
    <h4 style="color: #A37FFF; margin-bottom: 1rem; text-align: center;">🌐 Fuentes de Datos Integradas</h4>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: rgba(163, 127, 255, 0.1); padding: 1rem; border-radius: 8px;">
            <strong style="color: #A37FFF;">🎮 Gaming & Entertainment</strong><br>
            <span style="color: #E2E8F0; font-size: 0.9rem;">IsThereAnyDeal, Steam, Epic Games</span>
        </div>
        
        <div style="background: rgba(163, 127, 255, 0.1); padding: 1rem; border-radius: 8px;">
            <strong style="color: #A37FFF;">💻 Developer Communities</strong><br>
            <span style="color: #E2E8F0; font-size: 0.9rem;">DEV.to, Product Hunt, GitHub, Stack Overflow</span>
        </div>
        
        <div style="background: rgba(163, 127, 255, 0.1); padding: 1rem; border-radius: 8px;">
            <strong style="color: #A37FFF;">📰 Tech News</strong><br>
            <span style="color: #E2E8F0; font-size: 0.9rem;">Hacker News, TechCrunch, Indie Hackers, Lobsters</span>
        </div>
        
        <div style="background: rgba(163, 127, 255, 0.1); padding: 1rem; border-radius: 8px;">
            <strong style="color: #A37FFF;">🎓 Learning & Research</strong><br>
            <span style="color: #E2E8F0; font-size: 0.9rem;">ArXiv, Coursera, Udemy, edX</span>
        </div>
        
        <div style="background: rgba(163, 127, 255, 0.1); padding: 1rem; border-radius: 8px;">
            <strong style="color: #A37FFF;">📺 Multimedia</strong><br>
            <span style="color: #E2E8F0; font-size: 0.9rem;">YouTube, Podcasts, Medium</span>
        </div>
        
        <div style="background: rgba(163, 127, 255, 0.1); padding: 1rem; border-radius: 8px;">
            <strong style="color: #A37FFF;">🏢 Professional</strong><br>
            <span style="color: #E2E8F0; font-size: 0.9rem;">LinkedIn Jobs, AngelList, Remote.co</span>
        </div>
    </div>
    
    <div style="text-align: center; border-top: 1px solid rgba(163, 127, 255, 0.3); padding-top: 1rem;">
        <p style="color: #A0AEC0; font-size: 0.9rem; margin: 0;">
            🤖 <strong>Watchtower</strong> - Sistema de monitoreo automático de tendencias tecnológicas
        </p>
        <p style="color: #A0AEC0; font-size: 0.8rem; margin: 0.5rem 0 0 0;">
            Última sincronización: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | 
            Datos actualizados cada 30 minutos
        </p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

logger.info("Enhanced dashboard rendering completed successfully")
