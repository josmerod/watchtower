"""
Games tab component for the Watchtower Streamlit application.
Displays game deals, bundles, and giveaways in a clean, unified interface.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union, cast
from datetime import datetime

def render(deals_df, bundles_df, giveaways_df, trending_df, new_releases_df, logger=None):
    """Render the games tab with unified data display"""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    st.header("🎮 Juegos")
    
    # Prepare tab data with counts
    tab_data = _prepare_tab_data(deals_df, bundles_df, giveaways_df, trending_df, new_releases_df)
    
    # Debug logging
    logger.info(f"Games tab: prepared {len(tab_data)} tabs")
    
    if not tab_data:
        st.warning("No hay datos de juegos válidos para mostrar.")
        
        # Add debug info to help troubleshoot
        with st.expander("🔍 Debug Info", expanded=True):
            st.write("**Datos recibidos:**")
            st.write(f"- deals_df: tipo={type(deals_df)}, shape={getattr(deals_df, 'shape', 'no shape')}, vacío={getattr(deals_df, 'empty', 'unknown')}")
            st.write(f"- bundles_df: tipo={type(bundles_df)}, shape={getattr(bundles_df, 'shape', 'no shape')}, vacío={getattr(bundles_df, 'empty', 'unknown')}")
            st.write(f"- giveaways_df: tipo={type(giveaways_df)}, shape={getattr(giveaways_df, 'shape', 'no shape')}, vacío={getattr(giveaways_df, 'empty', 'unknown')}")
            st.write(f"- trending_df: tipo={type(trending_df)}, shape={getattr(trending_df, 'shape', 'no shape')}, vacío={getattr(trending_df, 'empty', 'unknown')}")
        
        return
    
    # Create tabs dynamically
    tab_titles = [f"{info['title']} ({info['count']})" for info in tab_data.values()]
    tabs = st.tabs(tab_titles)
    
    # Render each tab
    for i, (tab_key, tab_info) in enumerate(tab_data.items()):
        with tabs[i]:
            _render_games_section(
                tab_info['title'], 
                tab_info['data'], 
                tab_info['config'],
                logger
            )


def _prepare_tab_data(deals_df, bundles_df, giveaways_df, trending_df, new_releases_df) -> Dict[str, Dict]:
    """Prepare data for each tab with configurations"""
    tab_data = {}
    
    # Deals tab
    if deals_df is not None and not deals_df.empty:
        tab_data['deals'] = {
            'title': 'Ofertas de Juegos',
            'data': deals_df,
            'count': len(deals_df),
            'config': {
                'columns': {
                    'title': {'display_name': 'Título', 'type': 'text', 'width': 'medium'},
                    'store': {'display_name': 'Tienda', 'type': 'text', 'width': 'small'},
                    'price': {'display_name': 'Precio', 'type': 'price', 'width': 'small'},
                    'discount': {'display_name': 'Descuento', 'type': 'text', 'width': 'small'},
                    'link': {'display_name': 'Enlace', 'type': 'link', 'width': 'small', 'display_text': 'Ver Oferta'}
                },
                'sort_by': 'discount',
                'sort_ascending': False,
                'file_name': 'game_deals'
            }
        }
    
    # Bundles tab
    if bundles_df is not None and not bundles_df.empty:
        tab_data['bundles'] = {
            'title': 'Paquetes de Juegos',
            'data': bundles_df,
            'count': len(bundles_df),
            'config': {
                'columns': {
                    'title': {'display_name': 'Título', 'type': 'text', 'width': 'medium'},
                    'store': {'display_name': 'Fuente', 'type': 'text', 'width': 'small'},
                    'price': {'display_name': 'Precio', 'type': 'price', 'width': 'small'},
                    'game_count': {'display_name': 'Juegos', 'type': 'number', 'width': 'small'},
                    'link': {'display_name': 'Enlace', 'type': 'link', 'width': 'small', 'display_text': 'Ver Paquete'}
                },
                'sort_by': 'published_date',
                'sort_ascending': False,
                'file_name': 'game_bundles'
            }
        }
    
    # Giveaways tab
    if giveaways_df is not None and not giveaways_df.empty:
        tab_data['giveaways'] = {
            'title': 'Juegos Gratuitos',
            'data': giveaways_df,
            'count': len(giveaways_df),
            'config': {
                'columns': {
                    'title': {'display_name': 'Título', 'type': 'text', 'width': 'medium'},
                    'published_date': {'display_name': 'Publicado', 'type': 'date', 'width': 'small'},
                    'expires_date': {'display_name': 'Expira', 'type': 'date', 'width': 'small'},
                    'link': {'display_name': 'Enlace', 'type': 'link', 'width': 'small', 'display_text': 'Reclamar'}
                },
                'sort_by': 'published_date',
                'sort_ascending': False,
                'file_name': 'game_giveaways'
            }
        }
    
    # Trending tab
    if trending_df is not None and not trending_df.empty:
        tab_data['trending'] = {
            'title': 'Tendencias Itch.io',
            'data': trending_df,
            'count': len(trending_df),
            'config': {
                'columns': {
                    'title': {'display_name': 'Título', 'type': 'text', 'width': 'medium'},
                    'author': {'display_name': 'Autor', 'type': 'text', 'width': 'small'},
                    'price': {'display_name': 'Precio', 'type': 'price', 'width': 'small'},
                    'link': {'display_name': 'Enlace', 'type': 'link', 'width': 'small', 'display_text': 'Ver Juego'}
                },
                'sort_by': None,
                'sort_ascending': False,
                'file_name': 'itchio_trending'
            }
        }
    
    # New releases tab
    if new_releases_df is not None and not new_releases_df.empty:
        tab_data['new_releases'] = {
            'title': 'Nuevos Lanzamientos',
            'data': new_releases_df,
            'count': len(new_releases_df),
            'config': {
                'display_type': 'expandable',  # Special display type for new releases
                'file_name': 'new_game_releases'
            }
        }
    
    return tab_data


def _render_games_section(title: str, data: pd.DataFrame, config: Dict, logger) -> None:
    """Unified function to render any games section"""
    try:
        if data is None or data.empty:
            st.info(f"No hay datos disponibles para {title.lower()}.")
            return
        
        # Handle special display types
        if config.get('display_type') == 'expandable':
            _render_expandable_games(data, logger)
            return
        
        # Standard table display
        display_df = _prepare_display_data(data, config)
        
        if display_df.empty:
            st.info(f"No hay datos válidos para mostrar en {title.lower()}.")
            return
        
        st.write(f"Mostrando {len(display_df)} elementos")
        
        # Create column configuration
        column_config = _create_column_config(config['columns'])
        
        # Display the dataframe
        st.dataframe(
            display_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )
        
        # Add download buttons
        _add_download_buttons(display_df, config['file_name'])
        
    except Exception as e:
        logger.error(f"Error displaying {title}: {e}")
        st.error(f"Error mostrando {title.lower()}: {e}")


def _prepare_display_data(data: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Prepare data for display with proper column mapping and sorting"""
    available_columns = data.columns.tolist()
    
    # Find the title column
    title_col = _find_title_column(available_columns)
    if not title_col:
        return pd.DataFrame()  # Return empty if no title column
    
    # Select and rename columns
    display_columns = []
    rename_map = {}
    
    for col_key, col_config in config['columns'].items():
        if col_key == 'title':
            # Use the found title column
            display_columns.append(title_col)
            rename_map[title_col] = col_config['display_name']
        elif col_key in available_columns:
            display_columns.append(col_key)
            rename_map[col_key] = col_config['display_name']
    
    if not display_columns:
        return pd.DataFrame()
    
    # Create display dataframe
    display_df = data[display_columns].copy()
    if rename_map:
        display_df.columns = [rename_map.get(col, col) for col in display_df.columns]
    
    # Apply formatting
    display_df = _apply_data_formatting(cast(pd.DataFrame, display_df), config['columns'], rename_map)
    
    # Sort if specified
    if config.get('sort_by') and config['sort_by'] in data.columns:
        if config['sort_by'] == 'discount':
            # Special handling for discount sorting
            display_df = _sort_by_discount(data, display_df, rename_map)
        else:
            sort_col = rename_map.get(config['sort_by'], config['sort_by'])
            if sort_col in display_df.columns:
                display_df = display_df.sort_values(
                    by=sort_col, 
                    ascending=config.get('sort_ascending', True)
                )
    
    return display_df


def _find_title_column(columns: List[str]) -> Optional[str]:
    """Find the title column in the dataframe"""
    title_candidates = ['title', 'name']
    for candidate in title_candidates:
        if candidate in columns:
            return candidate
    return None


def _apply_data_formatting(df: pd.DataFrame, column_config: Dict, rename_map: Dict) -> pd.DataFrame:
    """Apply formatting to data based on column types"""
    for col_key, col_config in column_config.items():
        display_name = col_config['display_name']
        
        if display_name not in df.columns:
            continue
            
        col_type = col_config.get('type', 'text')
        
        if col_type == 'price':
            df[display_name] = df[display_name].apply(_format_price)
        elif col_type == 'date':
            df[display_name] = df[display_name].apply(_format_date)
    
    return df


def _format_price(price) -> str:
    """Format price values"""
    if pd.isna(price):
        return "N/A"
    if isinstance(price, (int, float)):
        return f"€{price:.2f}"
    return str(price)


def _format_date(date) -> str:
    """Format date values"""
    if pd.isna(date):
        return "N/A"
    if isinstance(date, str):
        try:
            # Try to parse and reformat
            dt = pd.to_datetime(date)
            return dt.strftime('%Y-%m-%d')
        except:
            return str(date)
    return str(date)


def _sort_by_discount(original_df: pd.DataFrame, display_df: pd.DataFrame, rename_map: Dict) -> pd.DataFrame:
    """Special sorting for discount column"""
    try:
        # Extract numeric discount values for sorting
        discount_col = original_df['discount'].str.extract(r'(\d+)').astype(float)
        sort_indices = discount_col.sort_values(ascending=False).index
        return display_df.loc[sort_indices].reset_index(drop=True)
    except:
        return display_df


def _create_column_config(columns_config: Dict) -> Dict:
    """Create Streamlit column configuration"""
    column_config = {}
    
    for col_key, col_config in columns_config.items():
        display_name = col_config['display_name']
        col_type = col_config.get('type', 'text')
        width = col_config.get('width', 'medium')
        
        if col_type == 'link':
            column_config[display_name] = st.column_config.LinkColumn(
                label=display_name,
                display_text=col_config.get('display_text', 'Enlace'),
                width=width
            )
        elif col_type == 'number':
            column_config[display_name] = st.column_config.NumberColumn(
                label=display_name,
                width=width
            )
        else:
            column_config[display_name] = st.column_config.TextColumn(
                label=display_name,
                width=width,
                help=col_config.get('help', f"Información de {display_name.lower()}")
            )
    
    return column_config


def _add_download_buttons(df: pd.DataFrame, file_name: str) -> None:
    """Add download buttons for CSV and JSON"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📥 Descargar CSV",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"{file_name}.csv",
            mime='text/csv'
        )
    
    with col2:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Descargar JSON",
            data=json_data.encode('utf-8') if json_data else b'[]',
            file_name=f"{file_name}.json",
            mime='application/json'
        )


def _render_expandable_games(data: pd.DataFrame, logger) -> None:
    """Render games in expandable format (for new releases)"""
    try:
        st.subheader("Próximos Lanzamientos y Novedades")
        
        # Sort by release date if available
        sorted_df = data.copy()
        if 'released' in sorted_df.columns:
            try:
                sorted_df['released_dt'] = pd.to_datetime(sorted_df['released'], errors='coerce')
                sorted_df = sorted_df.sort_values(by="released_dt", ascending=False)
            except Exception as e:
                logger.warning(f"Could not sort by release date: {e}")
        
        # Display games in expandable sections
        for idx, game in sorted_df.iterrows():
            game_name = game.get('name', 'Nombre no disponible')
            
            with st.expander(f"🎮 {game_name}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Título:** {game_name}")
                    
                    # Release date
                    release_date = game.get('released', 'Fecha no disponible')
                    if release_date is not None and release_date != 'Fecha no disponible' and hasattr(release_date, 'strftime'):
                        release_date = release_date.strftime('%Y-%m-%d')
                    st.markdown(f"**Fecha de Lanzamiento:** {release_date}")
                    
                    # Platforms
                    platforms = game.get('platforms', [])
                    if isinstance(platforms, list):
                        platforms_str = ', '.join(platforms) if platforms else "No especificadas"
                    else:
                        platforms_str = str(platforms) if platforms else "No especificadas"
                    st.markdown(f"**Plataformas:** {platforms_str}")
                
                with col2:
                    # Metacritic score
                    metacritic = game.get('metacritic', 'N/A')
                    if metacritic is not None and metacritic != 'N/A' and str(metacritic).replace('.', '').isdigit():
                        metacritic_num = float(metacritic)
                        score_color = "🟢" if metacritic_num >= 80 else "🟡" if metacritic_num >= 60 else "🔴"
                        st.markdown(f"**Metacritic:** {score_color} {metacritic}")
                    else:
                        st.markdown(f"**Metacritic:** N/A")
                    
                    # RAWG link
                    rawg_link = game.get('rawg_link')
                    if rawg_link and str(rawg_link).strip():
                        st.markdown(f"**🔗 [Ver en RAWG]({rawg_link})**")
                
                # Description
                description = game.get('description_raw', "")
                if description and str(description).strip():
                    st.caption(f"📝 {description}")
        
        logger.info(f"Successfully rendered {len(sorted_df)} new game releases.")
        
    except Exception as e:
        logger.error(f"Error displaying new releases: {e}")
        st.error(f"Error mostrando nuevos lanzamientos: {e}")