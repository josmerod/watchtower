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
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)


from src.utils.logging import get_logger



# Import centralized logging utility

# Initialize logger for the Streamlit app
logger = get_logger("GameDealsApp")

# Define data paths
DATA_DIR = "../../../../data/games"
DEALS_FILE = os.path.join(DATA_DIR, "deals.json")
BUNDLES_FILE = os.path.join(DATA_DIR, "bundles.json")
GIVEAWAYS_FILE = os.path.join(DATA_DIR, "giveaways.json")

# Log application startup
logger.info("Starting Game Deals Dashboard")

# Set page configuration
st.set_page_config(
    page_title="Panel de Ofertas de Juegos",
    page_icon="🎮",
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
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Resumen", "💰 Ofertas", "📦 Bundles", "🎁 Regalos"]
)

with tab1:
    logger.info("Rendering Overview tab")
    st.header("Resumen del Panel")

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-value">{len(deals_df)}</div>
            <div class="metric-label">Ofertas Activas</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-value">{len(bundles_df)}</div>
            <div class="metric-label">Paquetes de Juegos</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        # Fix the error with active_giveaways calculation
        active_giveaways = 0
        if not giveaways_df.empty and "is_active" in giveaways_df.columns:
            active_giveaways = giveaways_df["is_active"].sum()
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-value">{active_giveaways}</div>
            <div class="metric-label">Regalos Activos</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Top deals visualization
    if not deals_df.empty and "discount_value" in deals_df.columns:
        logger.info("Generating top discounts visualization")
        st.subheader("Mayores Descuentos")

        top_deals = deals_df.sort_values("discount_value", ascending=False).head(10)

        fig = px.bar(
            top_deals,
            x="title",
            y="discount_value",
            color="discount_value",
            color_continuous_scale="Viridis",
            labels={"discount_value": "Descuento %", "title": "Juego"},
            title="Top 10 Juegos por Porcentaje de Descuento",
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            height=500,
            margin=dict(l=20, r=20, t=40, b=20),
        )

        st.plotly_chart(fig, use_container_width=True)

    # Store distribution
    if not deals_df.empty and "store" in deals_df.columns:
        logger.info("Generating store distribution visualization")
        st.subheader("Ofertas por Tienda")

        store_counts = deals_df["store"].value_counts().reset_index()
        store_counts.columns = ["Tienda", "Cantidad"]

        fig = px.pie(
            store_counts,
            values="Cantidad",
            names="Tienda",
            title="Distribución de Ofertas por Tienda",
            hole=0.4,
        )

        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=500)

        st.plotly_chart(fig, use_container_width=True)

with tab2:
    logger.info("Rendering Deals tab")
    st.header("Ofertas de Juegos")

    if deals_df.empty:
        logger.warning("No deals data available to display")
        st.warning("No hay datos de ofertas disponibles.")
    else:
        # Filters
        col1, col2 = st.columns(2)

        with col1:
            min_discount = st.slider("Descuento Mínimo %", 0, 100, 0)

        with col2:
            if "store" in deals_df.columns:
                stores = ["Todas"] + sorted(
                    deals_df["store"].dropna().unique().tolist()
                )
                selected_store = st.selectbox("Seleccionar Tienda", stores)

        # Apply filters
        filtered_df = deals_df.copy()

        if min_discount > 0 and "discount_value" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["discount_value"] >= min_discount]

        if selected_store != "Todas" and "store" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["store"] == selected_store]

        logger.info(
            f"Deals filtered: {len(filtered_df)} results after applying filters"
        )

        # Display data
        if filtered_df.empty:
            logger.warning("No deals match the selected filters")
            st.warning("No hay ofertas que coincidan con los filtros seleccionados.")
        else:
            # Prepare display dataframe
            display_df = filtered_df[
                ["title", "price", "discount", "store", "published_date"]
            ].copy()

            # Add clickable links
            display_df["Ver Oferta"] = filtered_df["link"].apply(
                lambda x: make_clickable(x, "Ver")
            )

            # Format price with currency symbol
            if "price" in display_df.columns:
                display_df["price"] = display_df["price"].apply(
                    lambda x: f"€{x:.2f}" if pd.notna(x) else "N/A"
                )

            # Display the dataframe with clickable links
            st.markdown(
                display_df.to_html(escape=False, index=False), unsafe_allow_html=True
            )

            # Download option
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar datos como CSV",
                data=csv,
                file_name="ofertas_juegos.csv",
                mime="text/csv",
            )

with tab3:
    logger.info("Rendering Bundles tab")
    st.header("Paquetes de Juegos")

    if bundles_df.empty:
        logger.warning("No bundles data available to display")
        st.warning("No hay datos de paquetes disponibles.")
    else:
        # Filters
        col1, col2 = st.columns(2)

        with col1:
            min_games = st.slider(
                "Mínimo de Juegos en Paquete",
                0,
                int(bundles_df["game_count"].max())
                if "game_count" in bundles_df.columns
                else 100,
                0,
            )

        with col2:
            max_price = st.slider(
                "Precio Máximo (€)",
                0.0,
                float(bundles_df["price"].max())
                if "price" in bundles_df.columns
                else 100.0,
                float(bundles_df["price"].max())
                if "price" in bundles_df.columns
                else 100.0,
            )

        # Apply filters
        filtered_df = bundles_df.copy()

        if min_games > 0 and "game_count" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["game_count"] >= min_games]

        if "price" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["price"] <= max_price]

        logger.info(
            f"Bundles filtered: {len(filtered_df)} results after applying filters"
        )

        # Display data
        if filtered_df.empty:
            logger.warning("No bundles match the selected filters")
            st.warning("No hay paquetes que coincidan con los filtros seleccionados.")
        else:
            # Prepare display dataframe
            if "game_count" in filtered_df.columns:
                display_df = filtered_df[
                    ["title", "price", "game_count", "published_date"]
                ].copy()
            else:
                display_df = filtered_df[["title", "price", "published_date"]].copy()

            # Add clickable links
            display_df["Ver Paquete"] = filtered_df["link"].apply(
                lambda x: make_clickable(x, "Ver")
            )

            # Format price with currency symbol
            if "price" in display_df.columns:
                display_df["price"] = display_df["price"].apply(
                    lambda x: f"€{x:.2f}" if pd.notna(x) else "N/A"
                )

            # Display the dataframe with clickable links
            st.markdown(
                display_df.to_html(escape=False, index=False), unsafe_allow_html=True
            )

            # Show games in selected bundle
            st.subheader("Juegos en el Paquete Seleccionado")
            selected_bundle = st.selectbox(
                "Selecciona un paquete para ver los juegos incluidos",
                filtered_df["title"].tolist(),
            )

            if selected_bundle:
                logger.info(f"Displaying games for bundle: {selected_bundle}")
                bundle_games = filtered_df[filtered_df["title"] == selected_bundle][
                    "games"
                ].iloc[0]

                if isinstance(bundle_games, list) and len(bundle_games) > 0:
                    games_df = pd.DataFrame(bundle_games, columns=["Título del Juego"])
                    logger.info(f"Found {len(games_df)} games in the selected bundle")
                    st.dataframe(games_df, height=400)
                else:
                    logger.warning(
                        f"No game list available for bundle: {selected_bundle}"
                    )
                    st.info("No hay lista de juegos disponible para este paquete.")

            # Download option
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar datos como CSV",
                data=csv,
                file_name="paquetes_juegos.csv",
                mime="text/csv",
            )

with tab4:
    logger.info("Rendering Giveaways tab")
    st.header("Juegos Gratuitos")

    if giveaways_df.empty:
        logger.warning("No giveaways data available to display")
        st.warning("No hay datos de juegos gratuitos disponibles.")
    else:
        # Filter for active giveaways
        show_active_only = st.checkbox("Mostrar Solo Regalos Activos", value=True)

        filtered_df = giveaways_df.copy()
        # Fix the filtering for active giveaways
        if show_active_only and "is_active" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["is_active"] == True]
            logger.info(
                f"Filtering for active giveaways only: {len(filtered_df)} results"
            )

        # Display data
        if filtered_df.empty:
            if show_active_only:
                logger.warning("No active giveaways available")
                st.warning("No hay regalos activos disponibles.")
            else:
                logger.warning("No giveaways data available")
                st.warning("No hay datos de juegos gratuitos disponibles.")
        else:
            # Prepare display dataframe
            if "expires_date" in filtered_df.columns:
                display_df = filtered_df[
                    ["title", "published_date", "expires_date"]
                ].copy()
            else:
                display_df = filtered_df[["title", "published_date"]].copy()

            # Add clickable links
            display_df["Obtener Juego"] = filtered_df["link"].apply(
                lambda x: make_clickable(x, "Reclamar")
            )

            # Display the dataframe with clickable links
            st.markdown(
                display_df.to_html(escape=False, index=False), unsafe_allow_html=True
            )

            # Download option
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar datos como CSV",
                data=csv,
                file_name="juegos_gratuitos.csv",
                mime="text/csv",
            )

# Footer
st.markdown(
    """
<div style="text-align: center; margin-top: 30px; padding: 20px; opacity: 0.7;">
    <p>Datos obtenidos de <a href="https://isthereanydeal.com/" target="_blank">IsThereAnyDeal</a></p>
</div>
""",
    unsafe_allow_html=True,
)
logger.info("Dashboard rendering completed")
