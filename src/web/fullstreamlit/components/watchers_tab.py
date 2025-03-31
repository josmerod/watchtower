"""
Watchers tab component for the Watchtower Streamlit application.
Displays monitoring data from various watchers.
"""

import streamlit as st
import pandas as pd
import os
import subprocess
import json
from datetime import datetime

# Define watcher data path
WATCHERS_DATA_DIR = "../../../data/watchers"

# Local implementation of load_watcher_states
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_watcher_states(_logger=None):
    """Load all watcher states from the watchers data directory"""
    watchers_data = []
    
    # List all directories in the watchers folder (each is a watcher)
    watcher_dirs = [d for d in os.listdir(WATCHERS_DATA_DIR) 
                    if os.path.isdir(os.path.join(WATCHERS_DATA_DIR, d))]
    
    for watcher_name in watcher_dirs:
        watcher_path = os.path.join(WATCHERS_DATA_DIR, watcher_name)
        state_file = os.path.join(watcher_path, "state.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                # Count events
                events_dir = os.path.join(watcher_path, "events")
                event_count = len(os.listdir(events_dir)) if os.path.exists(events_dir) else 0
                
                # Get last event file (most recent by filename)
                last_event = None
                if os.path.exists(events_dir) and os.listdir(events_dir):
                    event_files = sorted(os.listdir(events_dir), reverse=True)
                    if event_files:
                        last_event_file = os.path.join(events_dir, event_files[0])
                        with open(last_event_file, 'r', encoding='utf-8') as f:
                            last_event = json.load(f)
                
                # Add watcher data
                watcher_data = {
                    "name": watcher_name,
                    "state": state,
                    "event_count": event_count,
                    "last_event": last_event,
                    "path": watcher_path
                }
                
                # Add URL if available in the state
                if isinstance(state.get("last_value"), dict) and "url" in state["last_value"]:
                    watcher_data["url"] = state["last_value"]["url"]
                
                watchers_data.append(watcher_data)
            except Exception as e:
                if _logger:
                    _logger.error(f"Error loading watcher state for {watcher_name}: {str(e)}")
    
    return watchers_data

def render(logger=None):
    """Render the watchers tab"""
    st.header("👁️ Monitores de Cambios (Watchers)")
    
    # Load watcher states
    watcher_states = load_watcher_states(_logger=logger)
    
    # Add a button to refresh data
    if st.button("Actualizar datos de los watchers"):
        st.cache_data.clear()
        watcher_states = load_watcher_states(_logger=logger)
        st.success("Datos actualizados correctamente")
    
    # Add a button to run MS Skills watcher specifically
    if st.button("Ejecutar MS Skills Watcher (forzar actualización)"):
        try:
            st.info("Ejecutando MS Skills Watcher...")
            # Use the project's file_system utility to get the project root
            from src.utils.file_system import get_project_root
            project_root = get_project_root()
            watcher_script = os.path.join(project_root, "src", "watchers", "ms_skills_watcher.py")
            
            # Run the watcher script with python's -m option to ensure imports work
            result = subprocess.run(
                ["python", watcher_script, "--force"], 
                capture_output=True, 
                text=True,
                check=True,
                cwd=project_root  # Execute from the project root
            )
            st.success("MS Skills Watcher ejecutado correctamente")
            # Clear cache and reload data
            st.cache_data.clear()
            watcher_states = load_watcher_states(logger)
        except Exception as e:
            st.error(f"Error al ejecutar MS Skills Watcher: {str(e)}")
    
    if not watcher_states:
        st.warning("No hay datos de watchers disponibles.")
    else:
        # Display watcher cards
        for watcher in watcher_states:
            display_watcher_card(watcher)


def display_watcher_card(watcher):
    """Display a single watcher card"""
    with st.expander(f"📡 {watcher['name'].replace('_', ' ').title()}", expanded=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Get last check time
            last_check = watcher['state'].get('last_check')
            if last_check:
                try:
                    last_check_dt = datetime.fromisoformat(last_check)
                    last_check_str = last_check_dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    last_check_str = last_check
            else:
                last_check_str = "Nunca"
            
            # Get first seen time
            first_seen = watcher['state'].get('first_seen')
            if first_seen:
                try:
                    first_seen_dt = datetime.fromisoformat(first_seen)
                    first_seen_str = first_seen_dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    first_seen_str = first_seen
            else:
                first_seen_str = "Desconocido"
            
            # Display watcher info
            st.markdown(f"**Última comprobación:** {last_check_str}")
            st.markdown(f"**Primera detección:** {first_seen_str}")
            st.markdown(f"**Número de eventos:** {watcher['event_count']}")
            
            # Display URL if available
            if "url" in watcher:
                st.markdown(f"**URL:** [{watcher['url']}]({watcher['url']})")
            
            # Display last value details
            last_value = watcher['state'].get('last_value')
            if last_value:
                st.markdown("**Último valor:**")
                
                # Special handling for MS Applied Skills watcher
                if watcher['name'] == "ms_applied_skills" and isinstance(last_value, dict):
                    st.markdown(f"- **Método de extracción:** {last_value.get('extraction_method', 'Desconocido')}")
                    st.markdown(f"- **Número de skills:** {last_value.get('count', 0)}")
                    
                    # Show skills in a table
                    if 'skills' in last_value and last_value['skills']:
                        # Handle both formats: list of strings or list of dicts with title and url
                        if isinstance(last_value['skills'][0], dict):
                            # Create a simple markdown list with links
                            st.markdown("#### Lista de Microsoft Applied Skills:")
                            for i, skill in enumerate(last_value['skills']):
                                title = skill.get('title', '')
                                url = skill.get('url')
                                
                                # Create markdown link if URL exists
                                if url:
                                    st.markdown(f"{i+1}. {title} [🔗]({url})")
                                else:
                                    st.markdown(f"{i+1}. {title}")
                        else:
                            # Old format - simple list of skill names
                            skills_df = pd.DataFrame(last_value['skills'], columns=["Skill"])
                            st.dataframe(skills_df, use_container_width=True)
                else:
                    # Generic display for other watchers
                    st.json(last_value)
        
        with col2:
            # Display last event if available
            if watcher['last_event']:
                st.markdown("**Último evento:**")
                event_time = watcher['last_event'].get('timestamp')
                if event_time:
                    try:
                        event_dt = datetime.fromisoformat(event_time)
                        event_time_str = event_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        event_time_str = event_time
                else:
                    event_time_str = "Desconocido"
                
                st.markdown(f"- **Tipo:** {watcher['last_event'].get('type', 'Desconocido')}")
                st.markdown(f"- **Fecha:** {event_time_str}")
            
            # Add button to view all events
            if watcher['event_count'] > 0:
                if st.button(f"Ver todos los eventos ({watcher['event_count']})", key=f"events_{watcher['name']}"):
                    events_dir = os.path.join(watcher['path'], "events")
                    event_files = sorted(os.listdir(events_dir), reverse=True)
                    
                    events_data = []
                    for event_file in event_files[:10]:  # Limit to 10 most recent events
                        with open(os.path.join(events_dir, event_file), 'r', encoding='utf-8') as f:
                            event = json.load(f)
                        events_data.append(event)
                    
                    # Convert to DataFrame for display
                    events_df = pd.DataFrame([{
                        "ID": e.get("id", ""),
                        "Tipo": e.get("type", ""),
                        "Fecha": datetime.fromisoformat(e.get("timestamp", "")).strftime("%Y-%m-%d %H:%M:%S") if "timestamp" in e else "",
                        "Detalles": str(e.get("details", ""))[:50] + "..." if e.get("details") else ""
                    } for e in events_data])
                    
                    st.dataframe(events_df, use_container_width=True) 