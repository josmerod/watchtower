"""
News tab component for the Watchtower Streamlit application.
Displays news from different sources.
"""

import streamlit as st
import pandas as pd
import os
import json
from src.web.fullstreamlit.utils.helpers import make_clickable

# Define news data paths locally
FUTURETOOLS_NEWS_DATA_DIR = "../../../data/futuretools"
YCOMBINATOR_NEWS_DATA_DIR = "../../../data/hackernews"
MEDIUM_NEWS_DATA_DIR = "../../../data/medium_genai"
BENSBITES_NEWS_DATA_DIR = "../../../data/bensbites"
GOODDEVS_NEWS_DATA_DIR = "../../../data/gooddevs"

FUTURETOOLS_NEWS_FILE = os.path.join(FUTURETOOLS_NEWS_DATA_DIR, "futuretoolsnews.json")
YCOMBINATOR_NEWS_FILE = os.path.join(YCOMBINATOR_NEWS_DATA_DIR, "hackernews.json")
MEDIUM_NEWS_FILE = os.path.join(MEDIUM_NEWS_DATA_DIR, "medium_genai.json")
BENSBITES_NEWS_FILE = os.path.join(BENSBITES_NEWS_DATA_DIR, "bensbites_news.json")
GOODDEVS_NEWS_FILE = os.path.join(GOODDEVS_NEWS_DATA_DIR, "gooddevs_latest.json")

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

def render(logger=None):
    """Render the news tab"""
    st.header("📰 Noticias")

    # Load news data
    futuretools_news_df = load_data(FUTURETOOLS_NEWS_FILE, _logger=logger)
    ycombinator_news_df = load_data(YCOMBINATOR_NEWS_FILE, _logger=logger)
    medium_news_df = load_data(MEDIUM_NEWS_FILE, _logger=logger)
    bensbites_news_df = load_data(BENSBITES_NEWS_FILE, _logger=logger)
    gooddevs_df = load_data(GOODDEVS_NEWS_FILE, _logger=logger)

    if futuretools_news_df.empty and bensbites_news_df.empty and medium_news_df.empty and gooddevs_df.empty:
        st.warning("No hay noticias disponibles para mostrar.")
    else:
        # Create tabs for different news sources
        news_tabs = st.tabs(["FutureTools & Ben's Bites", "Hacker News", "Medium GenAI", "Good Devs"])

        with news_tabs[0]:
            render_futuretools_bensbites(futuretools_news_df, bensbites_news_df)

        with news_tabs[1]:
            render_hackernews(ycombinator_news_df)

        with news_tabs[2]:
            render_medium(medium_news_df)

        with news_tabs[3]:
            render_gooddevs(gooddevs_df)


def render_futuretools_bensbites(futuretools_news_df, bensbites_news_df):
    """Render FutureTools and Ben's Bites news"""
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


def render_hackernews(ycombinator_news_df):
    """Render Hacker News"""
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


def render_medium(medium_news_df):
    """Render Medium GenAI news"""
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


# New function to render Good Devs blog posts
def render_gooddevs(gooddevs_df):
    """Render Good Devs blog posts"""
    st.header("Good Devs")
    if gooddevs_df.empty:
        st.warning("No hay posts disponibles de Good Devs.")
    else:
        display_df = gooddevs_df.copy() # Work with a copy

        # Ensure we have a consistent date column and sort
        date_col_present = False
        sort_col = None
        if "published_date" in display_df.columns:
            display_df["published_date"] = pd.to_datetime(display_df["published_date"], errors="coerce")
            display_df.dropna(subset=["published_date"], inplace=True) # Remove rows where conversion failed
            if not display_df.empty:
                 display_df = display_df.sort_values("published_date", ascending=False)
                 sort_col = "published_date"
                 date_col_present = True
        elif "published_at" in display_df.columns:
            display_df["published_at"] = pd.to_datetime(display_df["published_at"], errors="coerce")
            display_df.dropna(subset=["published_at"], inplace=True) # Remove rows where conversion failed
            if not display_df.empty:
                display_df = display_df.sort_values("published_at", ascending=False)
                sort_col = "published_at"
                date_col_present = True

        display_df["Ver Post"] = display_df["url"].apply(lambda x: make_clickable(x, "Leer más"))

        cols_to_display = ["title", "source", "Ver Post"]
        rename_map = {
            "title": "Título",
            "source": "Fuente",
            "Ver Post": "Ver Post"
        }

        # Add date column if available and formatted
        if date_col_present and sort_col:
             # Check if the sort column is actually datetime before formatting
            if pd.api.types.is_datetime64_any_dtype(display_df[sort_col]):
                display_df["formatted_date"] = display_df[sort_col].dt.strftime('%Y-%m-%d') # Format date only
                cols_to_display.insert(1, "formatted_date") # Insert date after title
                rename_map["formatted_date"] = "Fecha de Publicación"
            else: # If it's not datetime after checks, treat as string
                 cols_to_display.insert(1, sort_col)
                 rename_map[sort_col] = "Fecha de Publicación"


        display_final_df = display_df[cols_to_display].copy()
        display_final_df.rename(columns=rename_map, inplace=True)

        # Display the final DataFrame as HTML
        st.markdown(
            display_final_df.to_html(escape=False, index=False),
            unsafe_allow_html=True,
        ) 