"""AllKeyShop tab component for the Watchtower Streamlit application.
Displays game deals from AllKeyShop with filtering and sorting capabilities.
"""

from datetime import datetime
from typing import Any

import numpy as np  # Added to handle missing numeric values
import pandas as pd
import plotly.express as px
import streamlit as st


def render(allkeyshop_data: list[dict[str, Any]], logger=None):
    """Render the AllKeyShop games tab."""
    st.header("🎮 AllKeyShop - Game Deals")

    if not allkeyshop_data:
        if logger:
            logger.warning("No AllKeyShop game data available to display.")
        st.warning("No hay datos de AllKeyShop disponibles para mostrar.")
        st.info("💡 Ejecuta el ETL de AllKeyShop para obtener los últimos deals de juegos.")
        return

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(allkeyshop_data)

    # Ensure required columns exist to prevent KeyError if some fields are missing
    required_columns = [
        'current_price', 'discount_percentage', 'deal_score', 'title',
        'store_name', 'original_price', 'rating', 'is_dlc'
    ]
    for col in required_columns:
        if col not in df.columns:
            # Use appropriate default based on expected data type
            if col in {'title', 'store_name'}:
                df[col] = None
            elif col == 'is_dlc':
                df[col] = False
            else:
                df[col] = np.nan

    # Display summary statistics
    display_summary_stats(df)

    # Create tabs for different views
    tabs = st.tabs([
        "🏆 Mejores Deals",
        "💰 Por Precio",
        "🔍 Explorar Todo",
        "📊 Análisis",
        "⚙️ Filtros Avanzados"
    ])

    with tabs[0]:
        display_best_deals(df)

    with tabs[1]:
        display_by_price_range(df)

    with tabs[2]:
        display_all_games(df)

    with tabs[3]:
        display_analytics(df)

    with tabs[4]:
        display_advanced_filters(df)


def display_summary_stats(df: pd.DataFrame):
    """Display summary statistics at the top."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_games = len(df)
        st.metric("Total Juegos", total_games)

    with col2:
        avg_price = df['current_price'].mean()
        st.metric("Precio Promedio", f"€{avg_price:.2f}" if pd.notna(avg_price) else "N/A")

    with col3:
        avg_discount = df['discount_percentage'].mean()
        st.metric("Descuento Promedio", f"{avg_discount:.1f}%" if pd.notna(avg_discount) else "N/A")

    with col4:
        free_games = len(df[df['current_price'] == 0])
        st.metric("Juegos Gratis", free_games)

    with col5:
        best_deals = len(df[(df['discount_percentage'] >= 50) | (df['deal_score'] >= 80)])
        st.metric("Mejores Deals", best_deals)


def display_best_deals(df: pd.DataFrame):
    """Display the best deals based on discount percentage and deal score."""
    st.subheader("🏆 Mejores Ofertas")

    # Filter for best deals
    best_deals_df = df[
        (df['discount_percentage'] >= 50) |
        (df['deal_score'] >= 80) |
        (df['current_price'] == 0)  # Include free games
    ].copy()

    if best_deals_df.empty:
        st.info("No se encontraron ofertas destacadas en este momento.")
        return

    # Sort by multiple criteria
    best_deals_df['score'] = (
        best_deals_df['discount_percentage'].fillna(0) * 0.6 +
        best_deals_df['deal_score'].fillna(0) * 0.4
    )
    best_deals_df = best_deals_df.sort_values('score', ascending=False)

    # Display top deals
    for _idx, game in best_deals_df.head(10).iterrows():
        display_game_card(game, show_deal_score=True)


def display_by_price_range(df: pd.DataFrame):
    """Display games organized by price ranges."""
    st.subheader("💰 Juegos por Rango de Precio")

    # Define price ranges
    price_ranges = {
        "🆓 Gratis": (0, 0),
        "💸 Budget (€1-10)": (0.01, 10),
        "💵 Mid-tier (€10-30)": (10.01, 30),
        "💎 Premium (€30-60)": (30.01, 60),
        "👑 Luxury (€60+)": (60.01, float('inf'))
    }

    # Create tabs for each price range
    range_tabs = st.tabs(list(price_ranges.keys()))

    for i, (range_name, (min_price, max_price)) in enumerate(price_ranges.items()):
        with range_tabs[i]:
            if max_price == float('inf'):
                filtered_df = df[df['current_price'] > min_price]
            else:
                filtered_df = df[
                    (df['current_price'] >= min_price) &
                    (df['current_price'] <= max_price)
                ]

            if filtered_df.empty:
                st.info(f"No se encontraron juegos en el rango {range_name}.")
                continue

            # Sort by discount percentage for better deals first
            filtered_df = filtered_df.sort_values('discount_percentage', ascending=False, na_last=True)

            st.write(f"**{len(filtered_df)} juegos encontrados**")

            # Display games in columns
            cols = st.columns(2)
            for idx, game in filtered_df.head(20).iterrows():
                col_idx = idx % 2
                with cols[col_idx]:
                    display_game_card(game, compact=True)


def display_all_games(df: pd.DataFrame):
    """Display all games with search and filter capabilities."""
    st.subheader("🔍 Explorar Todos los Juegos")

    # Search functionality
    search_term = st.text_input("🔍 Buscar juegos:", placeholder="Escribe el nombre del juego...")

    # Filter by search term
    if search_term:
        filtered_df = df[df['title'].str.contains(search_term, case=False, na=False)]
    else:
        filtered_df = df.copy()

    # Sorting options
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox(
            "Ordenar por:",
            ["Relevancia", "Precio (menor a mayor)", "Precio (mayor a menor)",
             "Descuento", "Deal Score", "Nombre"]
        )

    with col2:
        items_per_page = st.selectbox("Juegos por página:", [10, 20, 50, 100], index=1)

    # Apply sorting
    if sort_by == "Precio (menor a mayor)":
        filtered_df = filtered_df.sort_values('current_price', na_last=True)
    elif sort_by == "Precio (mayor a menor)":
        filtered_df = filtered_df.sort_values('current_price', ascending=False, na_last=True)
    elif sort_by == "Descuento":
        filtered_df = filtered_df.sort_values('discount_percentage', ascending=False, na_last=True)
    elif sort_by == "Deal Score":
        filtered_df = filtered_df.sort_values('deal_score', ascending=False, na_last=True)
    elif sort_by == "Nombre":
        filtered_df = filtered_df.sort_values('title')

    # Pagination
    total_games = len(filtered_df)
    if total_games == 0:
        st.info("No se encontraron juegos con los criterios especificados.")
        return

    total_pages = (total_games - 1) // items_per_page + 1

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input(
            f"Página (1-{total_pages}):",
            min_value=1,
            max_value=total_pages,
            value=1
        )

    # Calculate start and end indices
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_df = filtered_df.iloc[start_idx:end_idx]

    st.write(f"Mostrando {len(page_df)} de {total_games} juegos (página {page} de {total_pages})")

    # Display games
    for _idx, game in page_df.iterrows():
        display_game_card(game)


def display_analytics(df: pd.DataFrame):
    """Display analytics and visualizations."""
    st.subheader("📊 Análisis de Datos")

    # Price distribution
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Distribución de Precios**")
        price_data = df['current_price'].dropna()
        if not price_data.empty:
            fig = px.histogram(
                price_data,
                nbins=20,
                title="Distribución de Precios",
                labels={'value': 'Precio (€)', 'count': 'Número de Juegos'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("**Distribución de Descuentos**")
        discount_data = df['discount_percentage'].dropna()
        if not discount_data.empty:
            fig = px.histogram(
                discount_data,
                nbins=20,
                title="Distribución de Descuentos",
                labels={'value': 'Descuento (%)', 'count': 'Número de Juegos'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # Top stores
    st.write("**Top Tiendas por Número de Ofertas**")
    store_counts = df['store_name'].value_counts().head(10)
    if not store_counts.empty:
        fig = px.bar(
            x=store_counts.values,
            y=store_counts.index,
            orientation='h',
            title="Top 10 Tiendas",
            labels={'x': 'Número de Ofertas', 'y': 'Tienda'}
        )
        st.plotly_chart(fig, use_container_width=True)

    # Price vs Discount scatter plot
    st.write("**Relación Precio vs Descuento**")
    scatter_data = df.dropna(subset=['current_price', 'discount_percentage'])
    if not scatter_data.empty:
        fig = px.scatter(
            scatter_data,
            x='current_price',
            y='discount_percentage',
            title="Precio vs Descuento",
            labels={'current_price': 'Precio Actual (€)', 'discount_percentage': 'Descuento (%)'},
            hover_data=['title']
        )
        st.plotly_chart(fig, use_container_width=True)


def display_advanced_filters(df: pd.DataFrame):
    """Display advanced filtering options."""
    st.subheader("⚙️ Filtros Avanzados")

    # Create filter controls
    col1, col2 = st.columns(2)

    with col1:
        # Price range filter
        price_range = st.slider(
            "Rango de Precio (€):",
            min_value=0.0,
            max_value=float(df['current_price'].max()) if df['current_price'].notna().any() else 100.0,
            value=(0.0, 50.0),
            step=1.0
        )

        # Discount filter
        min_discount = st.slider(
            "Descuento Mínimo (%):",
            min_value=0,
            max_value=100,
            value=0,
            step=5
        )

    with col2:
        # Deal score filter
        min_deal_score = st.slider(
            "Deal Score Mínimo:",
            min_value=0,
            max_value=100,
            value=0,
            step=5
        )

        # Store filter
        stores = df['store_name'].dropna().unique()
        selected_stores = st.multiselect(
            "Filtrar por Tienda:",
            options=sorted(stores),
            default=[]
        )

    # Apply filters
    filtered_df = df.copy()

    # Price range filter
    filtered_df = filtered_df[
        (filtered_df['current_price'] >= price_range[0]) &
        (filtered_df['current_price'] <= price_range[1])
    ]

    # Discount filter
    if min_discount > 0:
        filtered_df = filtered_df[
            filtered_df['discount_percentage'] >= min_discount
        ]

    # Deal score filter
    if min_deal_score > 0:
        filtered_df = filtered_df[
            filtered_df['deal_score'] >= min_deal_score
        ]

    # Store filter
    if selected_stores:
        filtered_df = filtered_df[
            filtered_df['store_name'].isin(selected_stores)
        ]

    # Display filtered results
    st.write(f"**{len(filtered_df)} juegos encontrados con los filtros aplicados**")

    if not filtered_df.empty:
        # Sort by relevance (combination of discount and deal score)
        filtered_df['relevance'] = (
            filtered_df['discount_percentage'].fillna(0) * 0.6 +
            filtered_df['deal_score'].fillna(0) * 0.4
        )
        filtered_df = filtered_df.sort_values('relevance', ascending=False)

        # Display games
        for _idx, game in filtered_df.head(20).iterrows():
            display_game_card(game)

        # Download button
        if st.button("📥 Descargar resultados filtrados"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Descargar CSV",
                data=csv.encode('utf-8'),
                file_name=f"allkeyshop_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            )


def display_game_card(game: dict[str, Any], compact: bool = False, show_deal_score: bool = False):
    """Display a game card with deal information."""
    with st.container():
        if compact:
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
        else:
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            # Game title with link
            title = game.get('title', 'Sin título')
            url = game.get('url')
            if url:
                st.markdown(f"**[{title}]({url})**")
            else:
                st.markdown(f"**{title}**")

            # Store information
            store = game.get('store_name')
            if store:
                st.caption(f"🏪 {store}")

        with col2:
            # Price information
            current_price = game.get('current_price')
            original_price = game.get('original_price')
            discount = game.get('discount_percentage')

            if current_price == 0:
                st.success("🆓 GRATIS")
            elif current_price:
                price_text = f"€{current_price:.2f}"
                if original_price and original_price > current_price:
                    price_text += f" ~~€{original_price:.2f}~~"
                st.write(price_text)

                if discount:
                    st.success(f"💰 {discount}% OFF")
            else:
                st.write("Precio no disponible")

        if not compact:
            with col3:
                # Deal score and additional info
                deal_score = game.get('deal_score')
                if show_deal_score and deal_score:
                    st.metric("Deal Score", f"{deal_score}/100")

                # Rating if available
                rating = game.get('rating')
                if rating:
                    st.write(f"⭐ {rating}/10")

                # DLC indicator
                if game.get('is_dlc'):
                    st.caption("📦 DLC")


def get_price_tier_color(price: float) -> str:
    """Get color based on price tier."""
    if price == 0:
        return "green"
    elif price <= 5:
        return "blue"
    elif price <= 20:
        return "orange"
    elif price <= 60:
        return "red"
    else:
        return "purple"


def format_currency(amount: float) -> str:
    """Format currency amount."""
    if amount == 0:
        return "GRATIS"
    return f"€{amount:.2f}"


def calculate_savings(original_price: float, current_price: float) -> str:
    """Calculate and format savings."""
    if not original_price or not current_price:
        return ""

    if original_price <= current_price:
        return ""

    savings = original_price - current_price
    percentage = (savings / original_price) * 100

    return f"Ahorras €{savings:.2f} ({percentage:.0f}%)"
