"""
Games tab component for the Watchtower Streamlit application.
Displays game deals, bundles, and giveaways.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import json
import logging

def render(deals_df, bundles_df, giveaways_df, trending_df, new_releases_df=None, allkeyshop_df=None, logger=None):
    """Render the games tab"""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    st.header("🎮 Juegos")

    # Check if all dataframes are empty or None with safer logic
    data_available = False
    
    if deals_df is not None and not deals_df.empty:
        data_available = True
    if bundles_df is not None and not bundles_df.empty:
        data_available = True
    if giveaways_df is not None and not giveaways_df.empty:
        data_available = True
    if trending_df is not None and not trending_df.empty:
        data_available = True
    if new_releases_df is not None and not new_releases_df.empty:
        data_available = True
    if allkeyshop_df is not None and not allkeyshop_df.empty:
        data_available = True

    # Debug information in sidebar
    if st.sidebar.checkbox("🐛 Show Debug Info"):
        st.markdown("### Debug Information:")
        st.write(f"- **Deals**: {len(deals_df) if deals_df is not None and hasattr(deals_df, '__len__') else 'None/Empty'} records")
        st.write(f"- **Bundles**: {len(bundles_df) if bundles_df is not None and hasattr(bundles_df, '__len__') else 'None/Empty'} records")
        st.write(f"- **Giveaways**: {len(giveaways_df) if giveaways_df is not None and hasattr(giveaways_df, '__len__') else 'None/Empty'} records")
        st.write(f"- **Trending**: {len(trending_df) if trending_df is not None and hasattr(trending_df, '__len__') else 'None/Empty'} records")
        st.write(f"- **New Releases**: {len(new_releases_df) if new_releases_df is not None and hasattr(new_releases_df, '__len__') else 'None/Empty'} records")
        st.write(f"- **AllKeyShop**: {len(allkeyshop_df) if allkeyshop_df is not None and hasattr(allkeyshop_df, '__len__') else 'None/Empty'} records")

    if not data_available:
        st.warning("No hay datos de juegos disponibles para mostrar.")
        st.info("💡 **Posibles soluciones:**")
        st.info("• Haz clic en '🔄 Bypass Cache (Debug)' en la barra lateral")
        st.info("• Ejecuta los ETLs de juegos para obtener datos actualizados")
        st.info("• Verifica que los archivos de datos en `data/games/` no estén vacíos")
        st.info("• Revisa los logs para identificar errores en la carga de datos")
        return

    # Create tabs for different game sections - only for non-empty dataframes
    tab_titles = []
    if giveaways_df is not None and not giveaways_df.empty:
        tab_titles.append("Juegos Gratuitos")
    if bundles_df is not None and not bundles_df.empty:
        tab_titles.append("Paquetes de Juegos")
    if deals_df is not None and not deals_df.empty:
        tab_titles.append("Ofertas de Juegos")
    if trending_df is not None and not trending_df.empty:
        tab_titles.append("Tendencias Itch.io")
    if new_releases_df is not None and not new_releases_df.empty:
        tab_titles.append("Nuevos Lanzamientos")
    if allkeyshop_df is not None and not allkeyshop_df.empty:
        tab_titles.append("AllKeyShop")

    if not tab_titles:
        st.warning("No hay datos de juegos válidos para mostrar en las pestañas.")
        return

    tabs = st.tabs(tab_titles)
    tab_map = {title: tab for title, tab in zip(tab_titles, tabs)}

    # Display content within each tab
    if "Juegos Gratuitos" in tab_map:
        with tab_map["Juegos Gratuitos"]:
            display_giveaways(giveaways_df, logger)

    if "Paquetes de Juegos" in tab_map:
        with tab_map["Paquetes de Juegos"]:
            display_bundles(bundles_df, logger)

    if "Ofertas de Juegos" in tab_map:
        with tab_map["Ofertas de Juegos"]:
            display_deals(deals_df, logger)

    if "Tendencias Itch.io" in tab_map:
        with tab_map["Tendencias Itch.io"]:
            display_trending(trending_df, logger)

    if "Nuevos Lanzamientos" in tab_map:
        with tab_map["Nuevos Lanzamientos"]:
            display_new_releases(new_releases_df, logger)

    if "AllKeyShop" in tab_map:
        with tab_map["AllKeyShop"]:
            display_allkeyshop(allkeyshop_df, logger)


def display_deals(deals_df, logger):
    """Display game deals"""
    if deals_df is None or deals_df.empty:
        st.info("No hay ofertas de juegos disponibles en este momento.")
        return

    try:
        filtered_deals_df = deals_df.copy()
        available_columns = filtered_deals_df.columns.tolist()

        # Determine title column
        title_col = None
        if "title" in available_columns:
            title_col = "title"
        elif "name" in available_columns:
            title_col = "name"

        if not title_col:
            st.error("Los datos de ofertas no tienen una columna de título ('title' or 'name').")
            return

        # Sort by discount value if available
        if "discount" in available_columns:
            # Extract numeric discount value for sorting
            try:
                filtered_deals_df['discount_numeric'] = filtered_deals_df['discount'].str.extract('(\d+)').astype(float)
                filtered_deals_df = filtered_deals_df.sort_values(by="discount_numeric", ascending=False)
            except:
                pass

        # Select columns for display
        display_columns = [title_col]
        column_config = {
            "Título": st.column_config.TextColumn(width="medium", help="Título del juego")
        }
        
        if "store" in available_columns:
            display_columns.append("store")
            column_config["Tienda"] = st.column_config.TextColumn(width="small", help="Tienda de la oferta")
        
        if "price" in available_columns:
            display_columns.append("price")
            column_config["Precio"] = st.column_config.TextColumn(width="small", help="Precio actual")
        
        if "discount" in available_columns:
            display_columns.append("discount")
            column_config["Descuento"] = st.column_config.TextColumn(width="small", help="Porcentaje de descuento")
        
        if "link" in available_columns:
            display_columns.append("link")
            column_config["Enlace"] = st.column_config.LinkColumn(label="Enlace", display_text="Ver Oferta", width="small")

        display_df = filtered_deals_df[display_columns].copy()

        # Rename columns to Spanish
        rename_map = {
            title_col: "Título",
            "store": "Tienda",
            "price": "Precio", 
            "discount": "Descuento",
            "link": "Enlace"
        }
        
        display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns}, inplace=True)

        # Format price column
        if "Precio" in display_df.columns:
            display_df["Precio"] = display_df["Precio"].apply(
                lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
            )

        st.write(f"Mostrando {len(display_df)} ofertas")
        st.dataframe(
            display_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )

        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV",
                data=display_df.to_csv(index=False).encode('utf-8'),
                file_name="game_deals.csv",
                mime='text/csv'
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON",
                data=display_df.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="game_deals.json",
                mime='application/json'
            )

    except Exception as e:
        logger.error(f"Error displaying deals: {e}")
        st.error(f"Error mostrando ofertas: {e}")


def display_bundles(bundles_df, logger):
    """Display game bundles"""
    if bundles_df is None or bundles_df.empty:
        st.info("No hay paquetes de juegos disponibles en este momento.")
        return

    try:
        filtered_bundles_df = bundles_df.copy()
        available_columns = filtered_bundles_df.columns.tolist()

        # Determine title column
        title_col = "title" if "title" in available_columns else "name"
        if title_col not in available_columns:
            st.error("Los datos de paquetes no tienen una columna de título.")
            return

        # Select columns for display
        display_columns = [title_col]
        column_config = {
            "Título": st.column_config.TextColumn(width="medium", help="Título del paquete")
        }
        
        if "store" in available_columns:
            display_columns.append("store")
            column_config["Fuente"] = st.column_config.TextColumn(width="small", help="Fuente del paquete")
        
        if "price" in available_columns:
            display_columns.append("price")
            column_config["Precio"] = st.column_config.TextColumn(width="small", help="Precio del paquete")
        
        if "game_count" in available_columns:
            display_columns.append("game_count")
            column_config["Juegos"] = st.column_config.NumberColumn(width="small", help="Número de juegos")
        
        if "link" in available_columns:
            display_columns.append("link")
            column_config["Enlace"] = st.column_config.LinkColumn(label="Enlace", display_text="Ver Paquete", width="small")

        display_df = filtered_bundles_df[display_columns].copy()

        # Rename columns to Spanish
        rename_map = {
            title_col: "Título",
            "store": "Fuente",
            "price": "Precio",
            "game_count": "Juegos",
            "link": "Enlace"
        }
        
        display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns}, inplace=True)

        # Format price column
        if "Precio" in display_df.columns:
            display_df["Precio"] = display_df["Precio"].apply(
                lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
            )

        st.write(f"Mostrando {len(display_df)} paquetes de juegos")
        st.dataframe(
            display_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )

        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV",
                data=display_df.to_csv(index=False).encode('utf-8'),
                file_name="game_bundles.csv",
                mime='text/csv'
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON",
                data=display_df.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="game_bundles.json",
                mime='application/json'
            )

    except Exception as e:
        logger.error(f"Error displaying bundles: {e}")
        st.error(f"Error mostrando paquetes: {e}")


def display_giveaways(giveaways_df, logger):
    """Display game giveaways"""
    if giveaways_df is None or giveaways_df.empty:
        st.info("No hay juegos gratuitos disponibles en este momento.")
        return

    try:
        filtered_giveaways_df = giveaways_df.copy()
        available_columns = filtered_giveaways_df.columns.tolist()

        # Determine title column
        title_col = None
        if "title" in available_columns:
            title_col = "title"
        elif "name" in available_columns:
            title_col = "name"

        if not title_col:
            st.error("Los datos de juegos gratuitos no tienen columna de título.")
            return

        # Select columns for display
        display_columns = [title_col]
        column_config = {
            "Título": st.column_config.TextColumn(width="medium", help="Título del juego gratuito")
        }
        
        if "published_date" in available_columns:
            display_columns.append("published_date")
            column_config["Publicado"] = st.column_config.TextColumn(width="small", help="Fecha de publicación")
        
        if "expires_date" in available_columns:
            display_columns.append("expires_date")
            column_config["Expira"] = st.column_config.TextColumn(width="small", help="Fecha de expiración")
        
        if "link" in available_columns:
            display_columns.append("link")
            column_config["Enlace"] = st.column_config.LinkColumn(label="Enlace", display_text="Reclamar", width="small")

        display_df = filtered_giveaways_df[display_columns].copy()

        # Rename columns to Spanish
        rename_map = {
            title_col: "Título",
            "published_date": "Publicado",
            "expires_date": "Expira",
            "link": "Enlace"
        }
        
        display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns}, inplace=True)

        st.write(f"Mostrando {len(display_df)} juegos gratuitos")
        st.dataframe(
            display_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )

        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV",
                data=display_df.to_csv(index=False).encode('utf-8'),
                file_name="game_giveaways.csv",
                mime='text/csv'
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON",
                data=display_df.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="game_giveaways.json",
                mime='application/json'
            )

    except Exception as e:
        logger.error(f"Error displaying giveaways: {e}")
        st.error(f"Error mostrando juegos gratuitos: {e}")


def display_trending(trending_df, logger):
    """Display Itch.io trending games"""
    if trending_df is None or trending_df.empty:
        st.info("No hay tendencias de Itch.io disponibles en este momento.")
        return

    try:
        filtered_trending_df = trending_df.copy()
        available_columns = filtered_trending_df.columns.tolist()

        # Determine title column
        title_col = None
        if "title" in available_columns:
            title_col = "title"
        elif "name" in available_columns:
            title_col = "name"

        if not title_col:
            st.error("Los datos de tendencias no tienen una columna de título.")
            return

        # Select columns for display
        display_columns = [title_col]
        column_config = {
            "Título": st.column_config.TextColumn(width="medium", help="Título del juego")
        }
        
        if "author" in available_columns:
            display_columns.append("author")
            column_config["Autor"] = st.column_config.TextColumn(width="small", help="Autor/Desarrollador")
        
        if "price" in available_columns:
            display_columns.append("price")
            column_config["Precio"] = st.column_config.TextColumn(width="small", help="Precio del juego")
        
        if "link" in available_columns:
            display_columns.append("link")
            column_config["Enlace"] = st.column_config.LinkColumn(label="Enlace", display_text="Ver Juego", width="small")

        display_df = filtered_trending_df[display_columns].copy()

        # Rename columns to Spanish
        rename_map = {
            title_col: "Título",
            "author": "Autor",
            "price": "Precio",
            "link": "Enlace"
        }
        
        display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns}, inplace=True)

        # Format price column
        if "Precio" in display_df.columns:
            display_df["Precio"] = display_df["Precio"].apply(
                lambda x: f"€{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
            )

        st.write(f"Mostrando {len(display_df)} juegos en tendencia de Itch.io")
        st.dataframe(
            display_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )

        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV",
                data=display_df.to_csv(index=False).encode('utf-8'),
                file_name="itchio_trending.csv",
                mime='text/csv'
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON",
                data=display_df.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="itchio_trending.json",
                mime='application/json'
            )

    except Exception as e:
        logger.error(f"Error displaying trending: {e}")
        st.error(f"Error mostrando tendencias: {e}")


def display_new_releases(new_releases_df, logger):
    """Display new game releases"""
    if new_releases_df is None or new_releases_df.empty:
        st.info("No hay nuevos lanzamientos disponibles en este momento.")
        return

    try:
        st.subheader("Próximos Lanzamientos y Novedades")

        # Sort by release date if available
        sorted_df = new_releases_df.copy()
        if 'released' in sorted_df.columns:
            try:
                sorted_df['released_dt'] = pd.to_datetime(sorted_df['released'], errors='coerce')
                sorted_df = sorted_df.sort_values(by="released_dt", ascending=False)
            except Exception as e:
                logger.warning(f"Could not sort by release date: {e}")

        # Display games in expandable sections
        for idx, game in sorted_df.iterrows():
            game_name = game.get('name', 'Nombre no disponible')
            
            with st.expander(f"{game_name}"):
                st.markdown(f"**Título:** {game_name}")

                # Release date
                release_date = game.get('released', 'Fecha no disponible')
                if pd.notna(release_date) and hasattr(release_date, 'strftime'):
                    release_date = release_date.strftime('%Y-%m-%d')
                st.markdown(f"**Fecha de Lanzamiento:** {release_date}")

                # Platforms
                platforms = game.get('platforms', [])
                if isinstance(platforms, list):
                    platforms_str = ', '.join(platforms) if platforms else "No especificadas"
                else:
                    platforms_str = str(platforms) if platforms else "No especificadas"
                st.markdown(f"**Plataformas:** {platforms_str}")

                # Metacritic score
                metacritic = game.get('metacritic', 'N/A')
                st.markdown(f"**Puntuación Metacritic:** {metacritic if pd.notna(metacritic) else 'N/A'}")

                # RAWG link
                rawg_link = game.get('rawg_link')
                if rawg_link and pd.notna(rawg_link):
                    st.markdown(f"**Enlace RAWG:** [Ver en RAWG]({rawg_link})")

                # Description
                description = game.get('description_raw', "No hay descripción disponible.")
                if pd.notna(description) and description:
                    st.caption(description)

        logger.info(f"Successfully rendered {len(sorted_df)} new game releases.")

    except Exception as e:
        logger.error(f"Error displaying new releases: {e}")
        st.error(f"Error mostrando nuevos lanzamientos: {e}")


def display_allkeyshop(allkeyshop_df, logger):
    """Display AllKeyShop games data"""
    if allkeyshop_df is None or allkeyshop_df.empty:
        st.info("No hay datos de AllKeyShop disponibles en este momento.")
        return

    try:
        st.subheader("AllKeyShop - Ofertas y Nuevos Lanzamientos")
        
        # Display summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_games = len(allkeyshop_df)
            st.metric("Total Juegos", total_games)
        
        with col2:
            new_releases = len(allkeyshop_df[allkeyshop_df['game_type'] == 'new_release'])
            st.metric("Nuevos Lanzamientos", new_releases)
        
        with col3:
            offers = len(allkeyshop_df[allkeyshop_df['game_type'] == 'offer'])
            st.metric("Ofertas", offers)
        
        with col4:
            avg_price = allkeyshop_df['current_price'].mean()
            st.metric("Precio Promedio", f"€{avg_price:.2f}" if pd.notna(avg_price) else "N/A")
        
        # Create sub-tabs for different views
        subtabs = st.tabs(["🏆 Mejores Ofertas", "🆕 Nuevos Lanzamientos", "💰 Todas las Ofertas", "🔍 Buscar"])
        
        with subtabs[0]:
            # Best deals (highest discount percentage)
            best_deals = allkeyshop_df[
                (allkeyshop_df['discount_percentage'].notna()) & 
                (allkeyshop_df['discount_percentage'] > 0)
            ].sort_values('discount_percentage', ascending=False).head(20)
            
            if not best_deals.empty:
                st.write(f"**{len(best_deals)} mejores ofertas con descuentos**")
                for idx, game in best_deals.iterrows():
                    display_allkeyshop_game_card(game)
            else:
                st.info("No hay ofertas con descuentos disponibles.")
        
        with subtabs[1]:
            # New releases
            new_releases_games = allkeyshop_df[allkeyshop_df['game_type'] == 'new_release'].head(20)
            
            if not new_releases_games.empty:
                st.write(f"**{len(new_releases_games)} nuevos lanzamientos**")
                for idx, game in new_releases_games.iterrows():
                    display_allkeyshop_game_card(game)
            else:
                st.info("No hay nuevos lanzamientos disponibles.")
        
        with subtabs[2]:
            # All offers
            offers_games = allkeyshop_df[allkeyshop_df['game_type'] == 'offer'].head(30)
            
            if not offers_games.empty:
                st.write(f"**{len(offers_games)} ofertas disponibles**")
                for idx, game in offers_games.iterrows():
                    display_allkeyshop_game_card(game)
            else:
                st.info("No hay ofertas disponibles.")
        
        with subtabs[3]:
            # Search functionality
            search_term = st.text_input("🔍 Buscar juegos:", placeholder="Escribe el nombre del juego...")
            
            if search_term:
                filtered_df = allkeyshop_df[
                    allkeyshop_df['title'].str.contains(search_term, case=False, na=False)
                ]
                
                if not filtered_df.empty:
                    st.write(f"**{len(filtered_df)} juegos encontrados**")
                    for idx, game in filtered_df.head(20).iterrows():
                        display_allkeyshop_game_card(game)
                else:
                    st.info("No se encontraron juegos con ese criterio de búsqueda.")
            else:
                st.info("Escribe un término de búsqueda para filtrar los juegos.")
        
        # Download buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Descargar CSV",
                data=allkeyshop_df.to_csv(index=False).encode('utf-8'),
                file_name="allkeyshop_games.csv",
                mime='text/csv'
            )
        with col2:
            st.download_button(
                label="📥 Descargar JSON",
                data=allkeyshop_df.to_json(orient='records', indent=2).encode('utf-8'),
                file_name="allkeyshop_games.json",
                mime='application/json'
            )

    except Exception as e:
        logger.error(f"Error displaying AllKeyShop data: {e}")
        st.error(f"Error mostrando datos de AllKeyShop: {e}")


def display_allkeyshop_game_card(game):
    """Display a single AllKeyShop game card"""
    with st.container():
        st.markdown("---")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Game title with link
            title = game.get('title', 'Sin título')
            url = game.get('url')
            if url:
                st.markdown(f"**[{title}]({url})**")
            else:
                st.markdown(f"**{title}**")
            
            # Game type and store
            game_type = game.get('game_type', 'unknown')
            store = game.get('store_name', 'Unknown Store')
            
            type_emoji = "🆕" if game_type == 'new_release' else "💰"
            st.caption(f"{type_emoji} {game_type.replace('_', ' ').title()} | 🏪 {store}")
            
            # DLC indicator
            if game.get('is_dlc'):
                st.caption("📦 DLC")
        
        with col2:
            # Price information
            current_price = game.get('current_price', 0)
            original_price = game.get('original_price')
            
            if current_price == 0:
                st.success("🆓 GRATIS")
            else:
                st.write(f"**€{current_price:.2f}**")
                
                if original_price and original_price > current_price:
                    st.caption(f"~~€{original_price:.2f}~~")
        
        with col3:
            # Discount and deal score
            discount = game.get('discount_percentage')
            deal_score = game.get('deal_score')
            
            if discount:
                st.success(f"💰 {discount:.0f}% OFF")
            
            if deal_score:
                st.metric("Deal Score", f"{deal_score}/100")