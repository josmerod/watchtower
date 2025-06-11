"""
News tab component for the Watchtower Streamlit application.
Displays news from different sources.
"""

import streamlit as st
import pandas as pd
import os
import json
import sys
# from web.fullstreamlit.utils.helpers import make_clickable # Removed as make_clickable is no longer used here

# Get the project root directory
def get_project_root():
    """Get the project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from src/web/fullstreamlit/components to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    return project_root

# Define news data paths using absolute paths
PROJECT_ROOT = get_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

FUTURETOOLS_NEWS_DATA_DIR = os.path.join(DATA_DIR, "futuretools")
YCOMBINATOR_NEWS_DATA_DIR = os.path.join(DATA_DIR, "hackernews")
MEDIUM_NEWS_DATA_DIR = os.path.join(DATA_DIR, "medium_genai")
BENSBITES_NEWS_DATA_DIR = os.path.join(DATA_DIR, "bensbites")
GOODDEVS_NEWS_DATA_DIR = os.path.join(DATA_DIR, "gooddevs")
KDNUGGETS_DATA_DIR = os.path.join(DATA_DIR, "kdnuggets")
MENEAME_DATA_DIR = os.path.join(DATA_DIR, "meneame")
PODCASTS_DATA_DIR = os.path.join(DATA_DIR, "podcasts")

FUTURETOOLS_NEWS_FILE = os.path.join(FUTURETOOLS_NEWS_DATA_DIR, "futuretoolsnews.json")
YCOMBINATOR_NEWS_FILE = os.path.join(YCOMBINATOR_NEWS_DATA_DIR, "hackernews.json")
MEDIUM_NEWS_FILE = os.path.join(MEDIUM_NEWS_DATA_DIR, "medium_genai.json")
BENSBITES_NEWS_FILE = os.path.join(BENSBITES_NEWS_DATA_DIR, "bensbites_news.json")
GOODDEVS_NEWS_FILE = os.path.join(GOODDEVS_NEWS_DATA_DIR, "gooddevs_latest.json")
KDNUGGETS_NEWS_FILE = os.path.join(KDNUGGETS_DATA_DIR, "kdnuggets.json")
MENEAME_GENERAL_FILE = os.path.join(MENEAME_DATA_DIR, "meneame_general_latest.json")
MENEAME_TECNO_FILE = os.path.join(MENEAME_DATA_DIR, "meneame_tecnologia_latest.json")
PODCASTS_FILE = os.path.join(PODCASTS_DATA_DIR, "podcasts_latest.json")

def clean_dataframe_for_caching(df: pd.DataFrame) -> pd.DataFrame:
    """Clean DataFrame to avoid unhashable type errors."""
    if df.empty:
        return df
    
    # Create a copy to avoid modifying the original
    df_clean = df.copy()
    
    # Convert any dictionary or list columns to strings
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            # Check if column contains dictionaries or lists
            try:
                # Sample a few non-null values to check type
                sample_values = df_clean[col].dropna().head(3)
                if not sample_values.empty:
                    for val in sample_values:
                        if isinstance(val, (dict, list)):
                            # Convert all values that are dict or list to JSON strings
                            df_clean[col] = df_clean[col].apply(
                                lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list)) else x
                            )
                            break
            except (TypeError, ValueError):
                # If there's any issue, convert the entire column to string
                df_clean[col] = df_clean[col].astype(str)
    
    return df_clean

# Local version of load_data
def load_data(file_path, _logger=None):
    """Load data from JSON file with error handling"""
    try:
        if os.path.exists(file_path):
            if _logger:
                _logger.info(f"Loading data from {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            # Clean the dataframe to avoid unhashable type errors
            df = clean_dataframe_for_caching(df)
            if _logger:
                _logger.info(f"Successfully loaded {len(df)} records from {file_path}")
            return df
        else:
            if _logger:
                _logger.warning(f"File not found: {file_path}")
            st.warning(f"📁 Archivo no encontrado: {os.path.basename(file_path)}")
            return pd.DataFrame()
    except Exception as e:
        if _logger:
            _logger.error(f"Error loading data from {file_path}: {str(e)}")
        st.error(f"❌ Error al cargar datos desde {os.path.basename(file_path)}: {str(e)}")
        return pd.DataFrame()

def render(logger=None):
    """Render the news tab"""

    # Initialize session state for active exportable DataFrame and its source name
    if "active_df_for_export" not in st.session_state:
        st.session_state.active_df_for_export = None
    if "active_source_name" not in st.session_state:
        st.session_state.active_source_name = None

    st.header("📰 Noticias")

    # Show data loading status
    with st.expander("📊 Estado de Fuentes de Datos", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Fuentes Principales:**")
            sources_status = {
                "FutureTools": os.path.exists(FUTURETOOLS_NEWS_FILE),
                "Hacker News": os.path.exists(YCOMBINATOR_NEWS_FILE),
                "Medium GenAI": os.path.exists(MEDIUM_NEWS_FILE),
                "Ben's Bites": os.path.exists(BENSBITES_NEWS_FILE)
            }
            
            for source, exists in sources_status.items():
                if exists:
                    st.success(f"✅ {source}")
                else:
                    st.error(f"❌ {source}")
        
        with col2:
            st.markdown("**Fuentes Adicionales:**")
            additional_sources = {
                "KDnuggets": os.path.exists(KDNUGGETS_NEWS_FILE),
                "Good Devs": os.path.exists(GOODDEVS_NEWS_FILE),
                "Meneame General": os.path.exists(MENEAME_GENERAL_FILE),
                "Meneame Tech": os.path.exists(MENEAME_TECNO_FILE),
                "Podcasts": os.path.exists(PODCASTS_FILE)
            }
            
            for source, exists in additional_sources.items():
                if exists:
                    st.success(f"✅ {source}")
                else:
                    st.error(f"❌ {source}")

    # Load news data
    futuretools_news_df = load_data(FUTURETOOLS_NEWS_FILE, _logger=logger)
    ycombinator_news_df = load_data(YCOMBINATOR_NEWS_FILE, _logger=logger)
    medium_news_df = load_data(MEDIUM_NEWS_FILE, _logger=logger)
    kdnuggets_news_df = load_data(KDNUGGETS_NEWS_FILE, _logger=logger)
    bensbites_news_df = load_data(BENSBITES_NEWS_FILE, _logger=logger)
    gooddevs_df = load_data(GOODDEVS_NEWS_FILE, _logger=logger)
    # Load Meneame data
    meneame_general_df = load_data(MENEAME_GENERAL_FILE, _logger=logger)
    meneame_tecnologia_df = load_data(MENEAME_TECNO_FILE, _logger=logger)
    # Load Podcasts data
    podcasts_df = load_data(PODCASTS_FILE, _logger=logger)

    # Count available data
    available_sources = 0
    total_articles = 0
    
    data_counts = {}
    for name, df in [
        ("FutureTools", futuretools_news_df),
        ("Ben's Bites", bensbites_news_df),
        ("Medium GenAI", medium_news_df),
        ("KDnuggets", kdnuggets_news_df),
        ("Good Devs", gooddevs_df),
        ("Hacker News", ycombinator_news_df),
        ("Meneame General", meneame_general_df),
        ("Meneame Tech", meneame_tecnologia_df),
        ("Podcasts", podcasts_df)
    ]:
        if not df.empty:
            available_sources += 1
            total_articles += len(df)
            data_counts[name] = len(df)

    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Fuentes Activas", f"{available_sources}/9")
    with col2:
        st.metric("📰 Total Artículos", f"{total_articles:,}")
    with col3:
        if data_counts:
            most_active = max(data_counts, key=data_counts.get)
            st.metric("🔥 Fuente Más Activa", f"{most_active}")

    # Check if any content is available
    if (futuretools_news_df.empty and bensbites_news_df.empty and medium_news_df.empty and kdnuggets_news_df.empty and gooddevs_df.empty
        and meneame_general_df.empty and meneame_tecnologia_df.empty and podcasts_df.empty and ycombinator_news_df.empty):
        st.warning("📭 No hay noticias disponibles para mostrar.")
        st.info("💡 **Sugerencia:** Ejecuta los procesos ETL para recopilar noticias actualizadas.")
        
        # Show ETL run buttons
        st.markdown("### 🔄 Ejecutar ETL de Noticias")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Ejecutar ETL Principal", help="Ejecuta FutureTools, HackerNews, Medium"):
                st.info("Ejecutando ETL principal... esto puede tomar unos minutos.")
        
        with col2:
            if st.button("📡 Ejecutar ETL Completo", help="Ejecuta todos los ETL de noticias"):
                st.info("Ejecutando ETL completo... esto puede tomar varios minutos.")
        
    else:
        # Create tabs for different news sources including Podcasts
        news_tabs = st.tabs([
            "🚀 FutureTools & Ben's Bites", 
            "🗞️ Hacker News", 
            "🤖 Medium GenAI", 
            "📊 KDnuggets", 
            "👨‍💻 Good Devs",
            "🇪🇸 Meneame General", 
            "🔧 Meneame Tech", 
            "🎧 Podcasts"
        ])

        with news_tabs[0]:
            render_futuretools_bensbites(futuretools_news_df, bensbites_news_df)

        with news_tabs[1]:
            render_hackernews(ycombinator_news_df)

        with news_tabs[2]:
            render_medium(medium_news_df)

        with news_tabs[3]:
            render_kdnuggets(kdnuggets_news_df)

        with news_tabs[4]:
            render_gooddevs(gooddevs_df)

        with news_tabs[5]:
            render_meneame_general(meneame_general_df)

        with news_tabs[6]:
            render_meneame_tecnologia(meneame_tecnologia_df)

        with news_tabs[7]:
            render_podcasts(podcasts_df)

    # Download buttons section based on active session state
    if st.session_state.active_df_for_export is not None and \
       not st.session_state.active_df_for_export.empty and \
       st.session_state.active_source_name:

        st.markdown("---")
        active_df = st.session_state.active_df_for_export
        source_name = st.session_state.active_source_name

        # Format the display name, handling potential "ft_bensbites" case specifically if needed for title
        display_source_title = source_name.replace('_', ' ').title()
        if source_name == "ft_bensbites":
            display_source_title = "FutureTools & Ben's Bites" # Custom title for this specific case

        st.write(f"**Opciones de descarga para: {display_source_title}**")

        button_label_prefix = "📥"
        if source_name == "podcasts":
            button_label_prefix = "🎙️"

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label=f"{button_label_prefix} Descargar CSV",
                data=active_df.to_csv(index=False).encode('utf-8'),
                file_name=f"{source_name}_data.csv",
                mime='text/csv',
                key=f"csv_download_active_{source_name}"
            )
        with col2:
            st.download_button(
                label=f"{button_label_prefix} Descargar JSON",
                data=active_df.to_json(orient='records', indent=2).encode('utf-8'),
                file_name=f"{source_name}_data.json",
                mime='application/json',
                key=f"json_download_active_{source_name}"
            )


def render_futuretools_bensbites(futuretools_news_df, bensbites_news_df):
    """Render FutureTools and Ben's Bites news"""
    st.subheader("FutureTools & Ben's Bites")
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
            
            # Format date for display - ensure it's a string to avoid column type issues
            combined_news_df["published_display"] = combined_news_df["published_date"].dt.strftime('%Y-%m-%d %H:%M').astype(str)

            # Prepare DataFrame for st.data_editor
            source_name_for_download = "ft_bensbites" # Define unique source name
            df_for_editor = combined_news_df.rename(columns={
                "title": "Título",
                "source": "Fuente",
                "published_display": "Fecha de Publicación",
                "url": "URL_Enlace"
            })
            
            # Ensure required columns exist and select them in order
            required_cols = ["Título", "Fuente", "Fecha de Publicación", "URL_Enlace"]
            cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
            df_for_editor = df_for_editor[cols_to_display]

            st.session_state.active_df_for_export = df_for_editor
            st.session_state.active_source_name = source_name_for_download

            st.data_editor(
                df_for_editor,
                column_config={
                    "Título": st.column_config.TextColumn(width="medium", help="Título del artículo"),
                    "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la noticia"),
                    "Fecha de Publicación": st.column_config.TextColumn(width="small", help="Fecha de publicación original"),
                    "URL_Enlace": st.column_config.LinkColumn(
                        label="Enlace",
                        display_text="Leer Artículo",
                        width="small",
                        help="Enlace directo al artículo"
                    )
                },
                hide_index=True,
                use_container_width=True,
                disabled=True
            )
        else:
            source_name_for_download = "ft_bensbites" # Must be defined in else branch too
            if st.session_state.get("active_source_name") == source_name_for_download:
                st.session_state.active_df_for_export = None
                st.session_state.active_source_name = None
            st.warning("No hay noticias disponibles de FutureTools o Ben's Bites.")


def render_hackernews(ycombinator_news_df):
    """Render Hacker News"""
    st.subheader("Hacker News")
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
        
        # Format date for display - ensure it's a string to avoid column type issues
        display_news_df["published_display"] = display_news_df["published_date"].dt.strftime('%Y-%m-%d %H:%M').astype(str)

        # Prepare DataFrame for st.data_editor
        source_name_for_download = "hackernews" # Define unique source name
        df_for_editor = display_news_df.rename(columns={
            "title": "Título",
            "source": "Fuente",
            "published_display": "Fecha de Publicación",
            "url": "URL_Enlace"
        })

        # Ensure required columns exist and select them in order
        required_cols = ["Título", "Fuente", "Fecha de Publicación", "URL_Enlace"]
        cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
        df_for_editor = df_for_editor[cols_to_display]

        st.session_state.active_df_for_export = df_for_editor
        st.session_state.active_source_name = source_name_for_download
        
        st.data_editor(
            df_for_editor,
            column_config={
                "Título": st.column_config.TextColumn(width="medium", help="Título del artículo"),
                "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la noticia"),
                "Fecha de Publicación": st.column_config.TextColumn(width="small", help="Fecha de publicación original"),
                "URL_Enlace": st.column_config.LinkColumn(
                    label="Enlace",
                    display_text="Leer Artículo",
                    width="small",
                    help="Enlace directo al artículo"
                )
            },
            hide_index=True,
            use_container_width=True,
            disabled=True
        )


def render_medium(medium_news_df):
    """Render Medium GenAI news"""
    st.subheader("Medium GenAI")
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
        
        # Determine which date column to use for display and prepare it
        date_column_to_format = None
        if "published_date" in display_news_df.columns and pd.api.types.is_datetime64_any_dtype(display_news_df["published_date"]):
            date_column_to_format = "published_date"
        elif "published_at" in display_news_df.columns and pd.api.types.is_datetime64_any_dtype(display_news_df["published_at"]):
            date_column_to_format = "published_at"
        
        if date_column_to_format:
            display_news_df["formatted_date"] = display_news_df[date_column_to_format].dt.strftime('%Y-%m-%d %H:%M')
            date_col_for_editor = "formatted_date"
        elif "published_at" in display_news_df.columns:
            date_col_for_editor = "published_at"
        else:
            date_col_for_editor = None

        # Prepare DataFrame for st.data_editor
        source_name_for_download = "medium_genai" # Define unique source name
        df_for_editor = display_news_df.rename(columns={
            "title": "Título",
            "source": "Fuente",
            date_col_for_editor if date_col_for_editor else "non_existent_date_col": "Fecha de Publicación",
            "url": "URL_Enlace"
        })

        # Define base required columns and add date if available
        required_cols = ["Título", "Fuente"]
        column_config = {
            "Título": st.column_config.TextColumn(width="medium", help="Título del artículo"),
            "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la noticia"),
            "URL_Enlace": st.column_config.LinkColumn(
                label="Enlace",
                display_text="Leer Artículo",
                width="small",
                help="Enlace directo al artículo"
            )
        }

        if date_col_for_editor and "Fecha de Publicación" in df_for_editor.columns:
            required_cols.append("Fecha de Publicación")
            column_config["Fecha de Publicación"] = st.column_config.TextColumn(width="small", help="Fecha de publicación original")

        required_cols.append("URL_Enlace")

        cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
        df_for_editor = df_for_editor[cols_to_display]

        if not df_for_editor.empty: # Check if df_for_editor itself is empty after selection/rename
            st.session_state.active_df_for_export = df_for_editor
            st.session_state.active_source_name = source_name_for_download

            st.data_editor(
                df_for_editor,
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                disabled=True
            )
        else: # Handles case where df_for_editor becomes empty after processing, or was already
            if st.session_state.get("active_source_name") == source_name_for_download:
                st.session_state.active_df_for_export = None
                st.session_state.active_source_name = None
            # The initial warning for medium_news_df.empty handles the general "no data" case

def render_kdnuggets(kdnuggets_news_df):
    """Render KDnuggets news"""
    st.subheader("KDnuggets")
    if kdnuggets_news_df.empty:
        st.warning("No hay noticias disponibles de KDnuggets.")
    else:
        if "published_date" not in kdnuggets_news_df.columns:
            if "published_at" in kdnuggets_news_df.columns:
                kdnuggets_news_df["published_date"] = pd.to_datetime(
                    kdnuggets_news_df["published_at"], errors="coerce"
                )
            else:
                kdnuggets_news_df["published_date"] = pd.Timestamp("now")

        display_df = kdnuggets_news_df.sort_values("published_date", ascending=False)
        display_df["published_display"] = display_df["published_date"].dt.strftime(
            '%Y-%m-%d %H:%M'
        )

        source_name_for_download = "kdnuggets" # Define unique source name
        df_for_editor = display_df.rename(columns={
            "title": "Título",
            "source": "Fuente",
            "published_display": "Fecha de Publicación",
            "url": "URL_Enlace"
        })

        required_cols = ["Título", "Fuente", "Fecha de Publicación", "URL_Enlace"]
        cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
        df_for_editor = df_for_editor[cols_to_display]

        st.session_state.active_df_for_export = df_for_editor
        st.session_state.active_source_name = source_name_for_download

        st.data_editor(
            df_for_editor,
            column_config={
                "Título": st.column_config.TextColumn(width="medium", help="Título del artículo"),
                "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la noticia"),
                "Fecha de Publicación": st.column_config.TextColumn(width="small", help="Fecha de publicación original"),
                "URL_Enlace": st.column_config.LinkColumn(
                    label="Enlace",
                    display_text="Leer Artículo",
                    width="small",
                    help="Enlace directo al artículo"
                )
            },
            hide_index=True,
            use_container_width=True,
            disabled=True
        )


def render_gooddevs(gooddevs_df):
    """Render Good Devs blog posts"""
    st.subheader("Good Devs")
    if gooddevs_df.empty:
        st.warning("No hay posts disponibles de Good Devs.")
    else:
        display_df = gooddevs_df.copy()

        # Handle date parsing with improved error handling
        date_col_present = False
        sort_col = None
        
        # Check for published_at column (which is what gooddevs data uses)
        if "published_at" in display_df.columns:
            try:
                # Parse dates with UTC handling for mixed timezones
                display_df["published_at_parsed"] = pd.to_datetime(
                    display_df["published_at"], 
                    errors="coerce",
                    utc=True
                )
                # Remove rows with invalid dates
                valid_date_mask = display_df["published_at_parsed"].notna()
                display_df = display_df[valid_date_mask]
                
                if not display_df.empty:
                    display_df = display_df.sort_values("published_at_parsed", ascending=False)
                    # Create formatted date for display
                    display_df["formatted_date"] = display_df["published_at_parsed"].dt.strftime('%Y-%m-%d %H:%M')
                    sort_col = "published_at_parsed"
                    date_col_present = True
                    
            except Exception as e:
                st.warning(f"Error parsing dates: {str(e)}")
                # Fallback: use data as-is without sorting
                date_col_present = False
                
        elif "published_date" in display_df.columns:
            try:
                display_df["published_date"] = pd.to_datetime(display_df["published_date"], errors="coerce")
                # Remove rows with invalid dates
                valid_date_mask = display_df["published_date"].notna()
                display_df = display_df[valid_date_mask]
                
                if not display_df.empty:
                    display_df = display_df.sort_values("published_date", ascending=False)
                    display_df["formatted_date"] = display_df["published_date"].dt.strftime('%Y-%m-%d %H:%M')
                    sort_col = "published_date"
                    date_col_present = True
                    
            except Exception as e:
                st.warning(f"Error parsing published_date: {str(e)}")
                date_col_present = False

        # Prepare columns for display
        source_name_for_download = "gooddevs"
        
        # Base column mapping
        column_mapping = {
            "title": "Título",
            "source": "Fuente",
            "url": "URL_Enlace"
        }
        
        # Add date column if available
        if date_col_present and "formatted_date" in display_df.columns:
            column_mapping["formatted_date"] = "Fecha de Publicación"
        
        df_for_editor = display_df.rename(columns=column_mapping)

        # Define columns to display
        required_cols = ["Título", "Fuente"]
        if "Fecha de Publicación" in df_for_editor.columns:
            required_cols.append("Fecha de Publicación")
        required_cols.append("URL_Enlace")

        # Configure columns
        column_config = {
            "Título": st.column_config.TextColumn(width="medium", help="Título del artículo"),
            "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la noticia"),
            "URL_Enlace": st.column_config.LinkColumn(
                label="Enlace",
                display_text="Leer Post",
                width="small",
                help="Enlace directo al post"
            )
        }
        
        if "Fecha de Publicación" in df_for_editor.columns:
            column_config["Fecha de Publicación"] = st.column_config.TextColumn(
                width="small", 
                help="Fecha de publicación original"
            )

        # Filter to only existing columns
        cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
        df_for_editor = df_for_editor[cols_to_display]

        if not df_for_editor.empty:
            # Show metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📄 Total Articles", len(df_for_editor))
            with col2:
                if date_col_present:
                    st.metric("📅 Date Coverage", f"{len(df_for_editor)}/{len(gooddevs_df)} parsed")
                else:
                    st.metric("⚠️ Date Issues", "No valid dates")
            with col3:
                unique_sources = display_df["source"].nunique() if "source" in display_df.columns else 0
                st.metric("📊 Sources", unique_sources)

            # Set session state for export
            st.session_state.active_df_for_export = df_for_editor
            st.session_state.active_source_name = source_name_for_download

            # Display data
            st.data_editor(
                df_for_editor,
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                disabled=True
            )
        else:
            st.error("❌ No se pudieron procesar los datos de Good Devs.")
            st.info("Los datos pueden tener problemas de formato o fechas inválidas.")
            
            # Clear session state
            if st.session_state.get("active_source_name") == source_name_for_download:
                st.session_state.active_df_for_export = None
                st.session_state.active_source_name = None

def render_meneame_general(df):
    """Render Meneame General posts"""
    st.subheader("Meneame General")
    if df.empty:
        st.warning("No hay posts disponibles de Meneame General.")
    else:
        display_df = df.copy()
        display_df["published_date"] = pd.to_datetime(display_df["published_at"], errors="coerce")
        display_df.dropna(subset=["published_date"], inplace=True)
        display_df = display_df.sort_values("published_date", ascending=False)
        display_df["formatted_date"] = display_df["published_date"].dt.strftime('%Y-%m-%d')

        source_name_for_download = "meneame_general" # Define unique source name
        df_for_editor = display_df.rename(columns={
            "title": "Título",
            "source": "Fuente",
            "formatted_date": "Fecha de Publicación",
            "url": "URL_Enlace"
        })

        required_cols = ["Título", "Fuente", "Fecha de Publicación", "URL_Enlace"]
        cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
        df_for_editor = df_for_editor[cols_to_display]

        st.session_state.active_df_for_export = df_for_editor
        st.session_state.active_source_name = source_name_for_download

        st.data_editor(
            df_for_editor,
            column_config={
                "Título": st.column_config.TextColumn(width="medium", help="Título del artículo"),
                "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la noticia"),
                "Fecha de Publicación": st.column_config.TextColumn(width="small", help="Fecha de publicación original"),
                "URL_Enlace": st.column_config.LinkColumn(
                    label="Enlace",
                    display_text="Leer Artículo",
                    width="small",
                    help="Enlace directo al artículo"
                )
            },
            hide_index=True,
            use_container_width=True,
            disabled=True
        )


def render_meneame_tecnologia(df):
    """Render Meneame Tecnología posts"""
    st.subheader("Meneame Tecnología")
    if df.empty:
        st.warning("No hay posts disponibles de Meneame Tecnología.")
    else:
        display_df = df.copy()
        display_df["published_date"] = pd.to_datetime(display_df["published_at"], errors="coerce")
        display_df.dropna(subset=["published_date"], inplace=True)
        display_df = display_df.sort_values("published_date", ascending=False)
        display_df["formatted_date"] = display_df["published_date"].dt.strftime('%Y-%m-%d')

        source_name_for_download = "meneame_tecnologia" # Define unique source name
        df_for_editor = display_df.rename(columns={
            "title": "Título",
            "source": "Fuente",
            "formatted_date": "Fecha de Publicación",
            "url": "URL_Enlace"
        })

        required_cols = ["Título", "Fuente", "Fecha de Publicación", "URL_Enlace"]
        cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
        df_for_editor = df_for_editor[cols_to_display]

        st.session_state.active_df_for_export = df_for_editor
        st.session_state.active_source_name = source_name_for_download

        st.data_editor(
            df_for_editor,
            column_config={
                "Título": st.column_config.TextColumn(width="medium", help="Título del artículo"),
                "Fuente": st.column_config.TextColumn(width="small", help="Fuente de la noticia"),
                "Fecha de Publicación": st.column_config.TextColumn(width="small", help="Fecha de publicación original"),
                "URL_Enlace": st.column_config.LinkColumn(
                    label="Enlace",
                    display_text="Leer Artículo",
                    width="small",
                    help="Enlace directo al artículo"
                )
            },
            hide_index=True,
            use_container_width=True,
            disabled=True
        )

def render_podcasts(podcasts_df):
    """Render Podcast Episodes"""
    st.subheader("Podcasts")
    if podcasts_df.empty:
        st.warning("No hay episodios de podcast disponibles.")
    else:
        df = podcasts_df.copy()
        def safe_format(ts):
            try:
                return pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M")
            except Exception:
                return ""
        df["Fecha de Publicación"] = df.get("published_at", pd.Series()).apply(safe_format)
        df = df.sort_values("Fecha de Publicación", ascending=False)

        source_name_for_download = "podcasts" # Define unique source name
        df_for_editor = df.rename(columns={
            "title": "Título",
            "source": "Fuente",
            "url": "URL_Enlace"
        })

        required_cols = ["Título", "Fuente", "Fecha de Publicación", "URL_Enlace"]
        cols_to_display = [col for col in required_cols if col in df_for_editor.columns]
        df_for_editor = df_for_editor[cols_to_display]

        st.session_state.active_df_for_export = df_for_editor
        st.session_state.active_source_name = source_name_for_download

        st.data_editor(
            df_for_editor,
            column_config={
                "Título": st.column_config.TextColumn(width="medium", help="Título del episodio"),
                "Fuente": st.column_config.TextColumn(width="small", help="Fuente del podcast"),
                "Fecha de Publicación": st.column_config.TextColumn(width="small", help="Fecha de publicación original"),
                "URL_Enlace": st.column_config.LinkColumn(
                    label="Enlace",
                    display_text="Escuchar Episodio",
                    width="small",
                    help="Enlace directo al episodio"
                )
            },
            hide_index=True,
            use_container_width=True,
            disabled=True
        )