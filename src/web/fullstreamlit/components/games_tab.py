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
            display_deals(deals_df)

        # Display bundles in responsive columns
        if "Paquetes de Juegos" in selected_tables:
            display_bundles(bundles_df)

        # Display giveaways in responsive columns
        if "Juegos Gratuitos" in selected_tables:
            display_giveaways(giveaways_df)

        st.markdown('</div>', unsafe_allow_html=True)


def display_deals(deals_df):
    """Display game deals"""
    deals_html = '<div class="deals-column"><div class="deals-card">'
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
    
    deals_html += '</div></div>'
    st.markdown(deals_html, unsafe_allow_html=True)


def display_bundles(bundles_df):
    """Display game bundles"""
    bundles_html = '<div class="deals-column"><div class="deals-card">'
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
    
    bundles_html += '</div></div>'
    st.markdown(bundles_html, unsafe_allow_html=True)


def display_giveaways(giveaways_df):
    """Display game giveaways"""
    giveaways_html = '<div class="deals-column"><div class="deals-card">'
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
    
    giveaways_html += '</div></div>'
    st.markdown(giveaways_html, unsafe_allow_html=True) 