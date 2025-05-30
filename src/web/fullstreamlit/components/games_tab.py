"""
Games tab component for the Watchtower Streamlit application.
Displays game deals, bundles, and giveaways.
"""

import streamlit as st
import pandas as pd
from src.web.fullstreamlit.utils.helpers import make_clickable

def render(deals_df, bundles_df, giveaways_df, logger=None):
    """Render the games tab"""
    st.header("🎮 Juegos")

    # Check if all dataframes are empty
    if deals_df.empty and bundles_df.empty and giveaways_df.empty:
        if logger:
            logger.warning("No game data available to display (deals, bundles, giveaways).")
        st.warning("No hay datos de juegos disponibles para mostrar.")
        return # Exit if no data

    # Create tabs for different game sections
    tab_titles = []
    if not giveaways_df.empty:
        tab_titles.append("Juegos Gratuitos")
    if not bundles_df.empty:
        tab_titles.append("Paquetes de Juegos")
    if not deals_df.empty:
        tab_titles.append("Ofertas de Juegos")

    if not tab_titles: # Should not happen if the initial check passed, but good practice
        st.warning("No hay datos de juegos válidos para mostrar en las pestañas.")
        return

    tabs = st.tabs(tab_titles)
    tab_map = {title: tab for title, tab in zip(tab_titles, tabs)}

    # Display content within each tab
    if "Juegos Gratuitos" in tab_map:
        with tab_map["Juegos Gratuitos"]:
            display_giveaways(giveaways_df)

    if "Paquetes de Juegos" in tab_map:
        with tab_map["Paquetes de Juegos"]:
            display_bundles(bundles_df)

    if "Ofertas de Juegos" in tab_map:
        with tab_map["Ofertas de Juegos"]:
            display_deals(deals_df)

    # Removed the multiselect and the old sequential display logic.
    # The container div is also removed as tabs handle the layout.


def display_deals(deals_df):
    """Display game deals"""
    if deals_df.empty:
        st.info("No hay ofertas de juegos disponibles en este momento.")
        return

    filtered_deals_df = deals_df.copy()
    available_columns = filtered_deals_df.columns.tolist()

    # Determine title column
    title_col_actual = None
    if "title" in available_columns:
        title_col_actual = "title"
    elif "name" in available_columns:
        title_col_actual = "name"
    
    if not title_col_actual:
        st.error("Los datos de ofertas no tienen una columna de título ('title' or 'name').")
        return

    # Define source columns for selection
    source_columns_to_select = [title_col_actual]
    if "store" in available_columns:
        source_columns_to_select.append("store")
    if "price" in available_columns:
        source_columns_to_select.append("price")
    if "discount" in available_columns: # This is often a string like "-90%"
        source_columns_to_select.append("discount")
    if "published_date" in available_columns:
        source_columns_to_select.append("published_date")
    if "link" in available_columns: # Needed for the clickable link
        source_columns_to_select.append("link")

    # Sort by discount value if available (assuming 'discount_value' is numeric for sorting)
    if "discount_value" in available_columns:
        filtered_deals_df = filtered_deals_df.sort_values(by="discount_value", ascending=False)
    
    display_deals_df = filtered_deals_df[source_columns_to_select].copy()

    # Create clickable link
    if "link" in display_deals_df.columns:
        display_deals_df["Ver Oferta"] = display_deals_df["link"].apply(lambda x: make_clickable(x, "Ver"))
    else:
        display_deals_df["Ver Oferta"] = "N/A"


    # Format price
    if "price" in display_deals_df.columns:
        display_deals_df["price"] = display_deals_df["price"].apply(
            lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
        )

    # Rename columns
    rename_map = {
        title_col_actual: "Título",
        "store": "Tienda",
        "price": "Precio",
        "discount": "Descuento", # Already formatted string
        "published_date": "Fecha de Publicación",
        "Ver Oferta": "Link"
    }
    
    # Filter rename_map to only include columns present in display_deals_df
    active_rename_map = {k: v for k, v in rename_map.items() if k in display_deals_df.columns}
    display_deals_df.rename(columns=active_rename_map, inplace=True)

    # Final column order
    final_columns_order = ["Título", "Tienda", "Precio", "Descuento", "Fecha de Publicación", "Link"]
    
    # Filter final_columns_order to only include columns that actually exist in display_deals_df
    ordered_columns_present = [col for col in final_columns_order if col in display_deals_df.columns]
    display_deals_df = display_deals_df[ordered_columns_present]
    
    st.write(f"Mostrando {len(display_deals_df)} ofertas")
    st.markdown(display_deals_df.to_html(escape=False, index=False), unsafe_allow_html=True)


def display_bundles(bundles_df):
    """Display game bundles"""
    if bundles_df.empty:
        st.info("No hay paquetes de juegos disponibles en este momento.")
        return

    filtered_bundles_df = bundles_df.copy()
    available_columns = filtered_bundles_df.columns.tolist()

    title_col_actual = "title" if "title" in available_columns else "name"
    if not title_col_actual:
        st.error("Los datos de paquetes no tienen una columna de título.")
        return

    with st.expander("Filtros y Opciones para Paquetes", expanded=False):
        group_col_actual = None
        if "store" in available_columns: # Prioritize 'store' as filter key
            group_col_actual = "store"
        elif "type" in available_columns:
            group_col_actual = "type"

        if group_col_actual:
            unique_groups = sorted(filtered_bundles_df[group_col_actual].dropna().unique().tolist())
            options = ["Todos"] + unique_groups
            selected_group = st.selectbox(
                f"Filtrar por {group_col_actual.replace('_', ' ').capitalize()}:",
                options=options,
                index=0,
                key="bundle_filter_selectbox"
            )
            if selected_group != "Todos":
                filtered_bundles_df = filtered_bundles_df[filtered_bundles_df[group_col_actual] == selected_group]
    
    # Determine date column and its display name
    date_col_actual = None
    date_col_display_name = None
    if "published_date" in available_columns:
        date_col_actual = "published_date"
        date_col_display_name = "Fecha de Publicación"
    elif "end_date" in available_columns:
        date_col_actual = "end_date"
        date_col_display_name = "Fecha de Expiración"

    if date_col_actual: # Sort by date if available
        filtered_bundles_df[date_col_actual] = pd.to_datetime(filtered_bundles_df[date_col_actual], errors='coerce')
        filtered_bundles_df = filtered_bundles_df.sort_values(by=date_col_actual, ascending=False)
    else: # Fallback sort by title
        filtered_bundles_df = filtered_bundles_df.sort_values(by=title_col_actual)

    # Add game_count if 'games' list exists and 'game_count' doesn't
    if "game_count" not in available_columns and "games" in available_columns:
        filtered_bundles_df["game_count"] = filtered_bundles_df["games"].apply(lambda x: len(x) if isinstance(x, list) else 0)
        available_columns.append("game_count") # Add to available if created

    # Select columns for display
    source_columns_to_select = [title_col_actual]
    if "store" in available_columns: source_columns_to_select.append("store")
    if "game_count" in available_columns: source_columns_to_select.append("game_count")
    if "price" in available_columns: source_columns_to_select.append("price")
    if "type" in available_columns: source_columns_to_select.append("type") # This is bundle category like "Humble Choice"
    if date_col_actual: source_columns_to_select.append(date_col_actual)
    if "link" in available_columns: source_columns_to_select.append("link")
    
    # Ensure no duplicates if title_col_actual or date_col_actual is already in the list by name
    source_columns_to_select = sorted(list(set(source_columns_to_select)), key=source_columns_to_select.index)


    display_bundles_df = filtered_bundles_df[source_columns_to_select].copy()

    if "link" in display_bundles_df.columns:
        display_bundles_df["Ver Paquete"] = display_bundles_df["link"].apply(lambda x: make_clickable(x, "Ver"))
    else:
        display_bundles_df["Ver Paquete"] = "N/A"

    if "price" in display_bundles_df.columns:
        display_bundles_df["price"] = display_bundles_df["price"].apply(
            lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else x
        )
    
    if date_col_actual and date_col_actual in display_bundles_df.columns:
         if pd.api.types.is_datetime64_any_dtype(display_bundles_df[date_col_actual]):
            display_bundles_df[date_col_actual] = display_bundles_df[date_col_actual].dt.strftime('%Y-%m-%d')


    rename_map = {
        title_col_actual: "Título",
        "store": "Fuente",
        "game_count": "Juegos en el Paquete",
        "price": "Precio",
        "type": "Tipo", # Bundle category
        "Ver Paquete": "Link"
    }
    if date_col_actual and date_col_display_name:
        rename_map[date_col_actual] = date_col_display_name
        
    active_rename_map = {k: v for k, v in rename_map.items() if k in display_bundles_df.columns}
    display_bundles_df.rename(columns=active_rename_map, inplace=True)

    final_columns_order = ["Título", "Fuente", "Juegos en el Paquete", "Precio", "Tipo"]
    if date_col_display_name and date_col_display_name in display_bundles_df.columns: # Add if it was successfully renamed
        final_columns_order.append(date_col_display_name)
    final_columns_order.append("Link")
    
    ordered_columns_present = [col for col in final_columns_order if col in display_bundles_df.columns]
    display_bundles_df = display_bundles_df[ordered_columns_present]
    
    st.write(f"Mostrando {len(display_bundles_df)} paquetes de juegos")
    st.markdown(display_bundles_df.to_html(escape=False, index=False), unsafe_allow_html=True)


def display_giveaways(giveaways_df):
    """Display game giveaways"""
    if giveaways_df.empty:
        st.info("No hay juegos gratuitos disponibles en este momento.")
        return

    filtered_giveaways_df = giveaways_df.copy()
    available_columns = filtered_giveaways_df.columns.tolist()

    title_col_actual = None
    if "title" in available_columns: title_col_actual = "title"
    elif "name" in available_columns: title_col_actual = "name"

    if not title_col_actual:
        st.error("Los datos de juegos gratuitos no tienen columna de título.")
        return

    published_date_col_actual = None
    if "published_date" in available_columns: published_date_col_actual = "published_date"
    elif "date" in available_columns: published_date_col_actual = "date" # Fallback for 'date'

    # Select columns for display
    source_columns_to_select = [title_col_actual]
    if published_date_col_actual: source_columns_to_select.append(published_date_col_actual)
    if "expires_date" in available_columns: source_columns_to_select.append("expires_date")
    if "link" in available_columns: source_columns_to_select.append("link")
    
    # Ensure no duplicates
    source_columns_to_select = sorted(list(set(source_columns_to_select)), key=source_columns_to_select.index)
    
    display_giveaways_df = filtered_giveaways_df[source_columns_to_select].copy()

    # Format dates if they exist and are datetime objects
    if published_date_col_actual and published_date_col_actual in display_giveaways_df.columns and \
       pd.api.types.is_datetime64_any_dtype(display_giveaways_df[published_date_col_actual]):
        display_giveaways_df[published_date_col_actual] = display_giveaways_df[published_date_col_actual].dt.strftime('%Y-%m-%d')
    
    if "expires_date" in display_giveaways_df.columns and \
       pd.api.types.is_datetime64_any_dtype(display_giveaways_df["expires_date"]):
        display_giveaways_df["expires_date"] = display_giveaways_df["expires_date"].dt.strftime('%Y-%m-%d')


    if "link" in display_giveaways_df.columns:
        display_giveaways_df["Obtener Juego"] = display_giveaways_df["link"].apply(lambda x: make_clickable(x, "Reclamar"))
    else:
        display_giveaways_df["Obtener Juego"] = "N/A"
        
    rename_map = {
        title_col_actual: "Título",
        "Obtener Juego": "Link"
    }
    if published_date_col_actual:
        rename_map[published_date_col_actual] = "Fecha de Publicación"
    if "expires_date" in available_columns: # Check original name
        rename_map["expires_date"] = "Fecha de Expiración"
        
    active_rename_map = {k:v for k,v in rename_map.items() if k in display_giveaways_df.columns}
    display_giveaways_df.rename(columns=active_rename_map, inplace=True)

    final_columns_order = ["Título"]
    if "Fecha de Publicación" in display_giveaways_df.columns: final_columns_order.append("Fecha de Publicación")
    if "Fecha de Expiración" in display_giveaways_df.columns: final_columns_order.append("Fecha de Expiración")
    final_columns_order.append("Link")
    
    ordered_columns_present = [col for col in final_columns_order if col in display_giveaways_df.columns]
    display_giveaways_df = display_giveaways_df[ordered_columns_present]

    st.write(f"Mostrando {len(display_giveaways_df)} juegos gratuitos")
    st.markdown(display_giveaways_df.to_html(escape=False, index=False), unsafe_allow_html=True)