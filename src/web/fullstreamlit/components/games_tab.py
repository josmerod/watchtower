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
    # Keep the card styling, remove the outer column div
    deals_html = '<div class="deals-card">'
    deals_html += '<h2>Ofertas de Juegos</h2>'

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
        
        giveaways_html += display_giveaways_df.to_html(escape=False, index=False)

    else:
        giveaways_html += '<p>No hay juegos gratuitos disponibles.</p>'

    # Close the card div
    giveaways_html += '</div>'
    st.markdown(giveaways_html, unsafe_allow_html=True) 