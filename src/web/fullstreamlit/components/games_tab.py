"""
Games tab component for the Watchtower Streamlit application.
Displays game deals, bundles, and giveaways.
"""

import streamlit as st
import pandas as pd
from src.web.fullstreamlit.utils.helpers import make_clickable
from . import new_releases_tab # Added import

def render(deals_df, bundles_df, giveaways_df, trending_df, new_releases_df, logger=None):
    """Render the games tab"""
    st.header("🎮 Juegos")

    # Check if all dataframes are empty
    if (deals_df.empty and bundles_df.empty and giveaways_df.empty and 
        trending_df.empty and (new_releases_df is None or new_releases_df.empty)):
        if logger:
            logger.warning("No game data available to display (deals, bundles, giveaways, trending, new releases).")
        st.warning("No hay datos de juegos disponibles para mostrar.")
        return # Exit if no data

    # Create tabs for different game sections
    tab_titles = ["Ofertas", "Paquetes", "Gratuitos", "Tendencias Itch.io", "Nuevos Lanzamientos"]

    ofertas_tab, paquetes_tab, gratuitos_tab, tendencias_tab, nuevos_lanzamientos_tab = st.tabs(tab_titles)

    with ofertas_tab:
        if not deals_df.empty:
            display_deals(deals_df)
        else:
            st.info("No hay ofertas de juegos disponibles en este momento.")

    with paquetes_tab:
        if not bundles_df.empty:
            display_bundles(bundles_df)
        else:
            st.info("No hay paquetes de juegos disponibles en este momento.")

    with gratuitos_tab:
        if not giveaways_df.empty:
            display_giveaways(giveaways_df)
        else:
            st.info("No hay juegos gratuitos disponibles en este momento.")

    with tendencias_tab:
        if not trending_df.empty:
            display_trending(trending_df)
        else:
            st.info("No hay tendencias de Itch.io disponibles en este momento.")

    with nuevos_lanzamientos_tab:
        # Assuming new_releases_tab.render handles empty df and logger correctly
        new_releases_tab.render(new_releases_df, logger)


def display_deals(deals_df):
    """Display game deals"""
    # Keep the card styling, remove the outer column div
    deals_html = '<div class="deals-card">'
    deals_html += '<h2>Ofertas de Juegos</h2>'

    if not deals_df.empty:
        filtered_deals_df = deals_df.copy()
        
        # Check which columns are available
        available_columns = filtered_deals_df.columns.tolist()
        
        # Define required columns with fallbacks
        display_columns = []
        
        # Title column is essential
        if "title" in available_columns:
            display_columns.append("title")
        elif "name" in available_columns:
            display_columns.append("name")
        else:
            deals_html += '<p>Error: Los datos de ofertas no tienen una columna de título.</p>'
            deals_html += '</div>'
            st.markdown(deals_html, unsafe_allow_html=True)
            return
        
        # Add optional columns if they exist
        for col in ["price", "discount", "store", "published_date"]:
            if col in available_columns:
                display_columns.append(col)
        
        # Sort by discount value if available
        if "discount_value" in available_columns:
            filtered_deals_df = filtered_deals_df.sort_values(by="discount_value", ascending=False)
        
        # Create the display dataframe with only available columns
        display_deals_df = filtered_deals_df[display_columns].copy()
        
        # Add clickable link if available
        if "link" in available_columns:
            display_deals_df["Ver Oferta"] = filtered_deals_df["link"].apply(lambda x: make_clickable(x, "Ver"))
        
        # Format price if available
        if "price" in display_deals_df.columns:
            display_deals_df["price"] = display_deals_df["price"].apply(
                lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
            )
        
        # Define column rename mapping
        column_renames = {
            "title": "Título",
            "name": "Título",
            "price": "Precio",
            "discount": "Descuento",
            "store": "Tienda",
            "published_date": "Fecha de Publicación",
        }
        
        # Only rename columns that exist in our DataFrame
        rename_dict = {k: v for k, v in column_renames.items() if k in display_deals_df.columns}
        if rename_dict:
            display_deals_df.rename(columns=rename_dict, inplace=True)
        
        deals_html += display_deals_df.to_html(escape=False, index=False)

    else:
        deals_html += '<p>No hay ofertas disponibles.</p>'

    # Close the card div
    deals_html += '</div>'
    st.markdown(deals_html, unsafe_allow_html=True)


def display_bundles(bundles_df):
    """Display game bundles"""
    # Keep the card styling, remove the outer column div
    bundles_html = '<div class="deals-card">'
    bundles_html += '<h2>Paquetes de Juegos</h2>'

    if not bundles_df.empty:
        filtered_bundles_df = bundles_df.copy()
        
        # Check which columns are available
        available_columns = filtered_bundles_df.columns.tolist()
        
        # Title column is essential
        if "title" not in available_columns and "name" not in available_columns:
            bundles_html += '<p>Error: Los datos de paquetes no tienen una columna de título.</p>'
            bundles_html += '</div>'
            st.markdown(bundles_html, unsafe_allow_html=True)
            return
        
        # Add a selector for bundle type if the type column exists
        if "type" in available_columns or "store" in available_columns:
            # Create a grouping column based on store or type
            group_col = "store" if "store" in available_columns else "type"
            unique_groups = filtered_bundles_df[group_col].unique().tolist()
            
            # Add "All" option at the beginning
            all_option = "Todos"
            options = [all_option] + unique_groups
            
            selected_group = st.selectbox(
                "Filtrar por tipo de paquete/origen:",
                options=options,
                index=0
            )
            
            # Filter by selected group if not "All"
            if selected_group != all_option:
                filtered_bundles_df = filtered_bundles_df[filtered_bundles_df[group_col] == selected_group]
        
        # Handle date field compatibility for different bundle sources
        date_field = None
        for field in ["published_date", "end_date"]:
            if field in available_columns:
                date_field = field
                break
        
        # Default sort by date, fallback to title if no date field
        if date_field:
            filtered_bundles_df = filtered_bundles_df.sort_values(by=date_field, ascending=False)
        else:
            title_field = "title" if "title" in available_columns else "name"
            filtered_bundles_df = filtered_bundles_df.sort_values(by=title_field)
        
        # Add game count column if it doesn't exist but we have a 'games' list
        if "game_count" not in available_columns and "games" in available_columns:
            filtered_bundles_df["game_count"] = filtered_bundles_df["games"].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )
            available_columns.append("game_count")
        
        # Select columns for display - start with title
        display_columns = []
        if "title" in available_columns:
            display_columns.append("title")
        else:
            display_columns.append("name")
        
        # Add price if available
        if "price" in available_columns:
            display_columns.append("price")
        
        # Add store if available
        if "store" in available_columns:
            display_columns.append("store")
        
        # Add game count if available
        if "game_count" in available_columns:
            display_columns.append("game_count")
        
        # Add date field if available
        if date_field:
            display_columns.append(date_field)
        
        # Add bundle type if available and not already filtering by it
        if "type" in available_columns and ("store" not in available_columns or group_col != "type"):
            display_columns.append("type")
            
        display_bundles_df = filtered_bundles_df[display_columns].copy()
        
        # Add clickable link if available
        if "link" in available_columns:
            display_bundles_df["Ver Paquete"] = filtered_bundles_df["link"].apply(lambda x: make_clickable(x, "Ver"))
        
        # Format price (handle non-numeric prices like "Pay what you want")
        if "price" in display_bundles_df.columns:
            display_bundles_df["price"] = display_bundles_df["price"].apply(
                lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
            )
        
        # Rename columns for display
        column_renames = {
            "title": "Título",
            "name": "Título",
            "price": "Precio",
            "game_count": "Juegos en el Paquete",
            "type": "Tipo",
            "store": "Fuente",
        }
        
        # Add date field to renaming if it exists
        if date_field == "published_date":
            column_renames[date_field] = "Fecha de Publicación"
        elif date_field == "end_date":
            column_renames[date_field] = "Fecha de Expiración"
        
        # Only rename columns that exist in our DataFrame
        rename_dict = {k: v for k, v in column_renames.items() if k in display_bundles_df.columns}
        if rename_dict:
            display_bundles_df.rename(columns=rename_dict, inplace=True)
        
        # Show the number of bundles being displayed
        st.write(f"Mostrando {len(display_bundles_df)} paquetes de juegos")
        
        bundles_html += display_bundles_df.to_html(escape=False, index=False)
        
    else:
        bundles_html += '<p>No hay paquetes disponibles.</p>'

    # Close the card div
    bundles_html += '</div>'
    st.markdown(bundles_html, unsafe_allow_html=True)


def display_giveaways(giveaways_df):
    """Display game giveaways"""
    # Keep the card styling, remove the outer column div
    giveaways_html = '<div class="deals-card">'
    giveaways_html += '<h2>Juegos Gratuitos</h2>'

    if not giveaways_df.empty:
        filtered_giveaways_df = giveaways_df.copy()
        
        # Get available columns and define required columns with fallbacks
        available_columns = filtered_giveaways_df.columns.tolist()
        display_columns = ["title" if "title" in available_columns else "name"]
        
        # Add date columns if they exist
        if "published_date" in available_columns:
            display_columns.append("published_date")
        elif "date" in available_columns:
            display_columns.append("date")
        
        if "expires_date" in available_columns:
            display_columns.append("expires_date")
        
        # Filter to only columns that actually exist in the DataFrame
        display_columns = [col for col in display_columns if col in available_columns]
        
        # Ensure we have at least a title column
        if not display_columns or (display_columns[0] not in ["title", "name"]):
            # If we don't have a title column, there's something wrong with the data
            giveaways_html += '<p>Error: Los datos de juegos gratuitos no tienen una columna de título.</p>'
            giveaways_html += '</div>'
            st.markdown(giveaways_html, unsafe_allow_html=True)
            return
        
        display_giveaways_df = filtered_giveaways_df[display_columns].copy()
        
        # Ensure link column exists before trying to use it
        if "link" in available_columns:
            display_giveaways_df["Obtener Juego"] = filtered_giveaways_df["link"].apply(
                lambda x: make_clickable(x, "Reclamar")
            )
        
        # Rename columns for display
        column_renames = {
            "title": "Título",
            "name": "Título",
            "published_date": "Fecha de Publicación",
            "date": "Fecha",
            "expires_date": "Fecha de Expiración"
        }
        
        # Only rename columns that exist in our DataFrame
        rename_dict = {k: v for k, v in column_renames.items() if k in display_giveaways_df.columns}
        if rename_dict:
            display_giveaways_df.rename(columns=rename_dict, inplace=True)
        
        giveaways_html += display_giveaways_df.to_html(escape=False, index=False)

    else:
        giveaways_html += '<p>No hay juegos gratuitos disponibles.</p>'

    # Close the card div
    giveaways_html += '</div>'
    st.markdown(giveaways_html, unsafe_allow_html=True)

# New function for Itch.io trending games
def display_trending(trending_df):
    """Display Itch.io trending games"""
    cards_html = '<div class="deals-card">'
    cards_html += '<h2>Tendencias en Itch.io</h2>'

    if not trending_df.empty:
        df = trending_df.copy()
        # Add clickable link
        if "link" in df.columns:
            df["Ver Juego"] = df["link"].apply(lambda x: make_clickable(x, "Ver"))
        # Rename columns for display
        rename_map = {}
        if "title" in df.columns:
            rename_map["title"] = "Título"
        if "author" in df.columns:
            rename_map["author"] = "Autor"
        if "price" in df.columns:
            rename_map["price"] = "Precio"
        if "description" in df.columns:
            rename_map["description"] = "Descripción"
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        cards_html += df.to_html(escape=False, index=False)
    else:
        cards_html += '<p>No hay tendencias disponibles.</p>'

    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True) 