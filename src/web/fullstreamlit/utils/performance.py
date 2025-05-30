"""
Performance optimization utilities for the Watchtower Streamlit application.
"""

import streamlit as st
import time
import functools
from typing import Callable, Any, Dict
from datetime import datetime, timedelta

class PerformanceTracker:
    """Track performance metrics for the application"""
    
    def __init__(self):
        """Initialize the PerformanceTracker.

        Ensures that a 'performance_metrics' dictionary exists in
        Streamlit's session state to store metrics.
        """
        if 'performance_metrics' not in st.session_state:
            st.session_state.performance_metrics = {}
    
    def time_function(self, func_name: str):
        """Decorator to time function execution"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Store metrics in session state
                if func_name not in st.session_state.performance_metrics:
                    st.session_state.performance_metrics[func_name] = []
                
                st.session_state.performance_metrics[func_name].append({
                    'timestamp': datetime.now(),
                    'execution_time': execution_time
                })
                
                # Keep only last 10 measurements
                if len(st.session_state.performance_metrics[func_name]) > 10:
                    st.session_state.performance_metrics[func_name] = \
                        st.session_state.performance_metrics[func_name][-10:]
                
                return result
            return wrapper
        return decorator
    
    def get_average_time(self, func_name: str) -> float:
        """Get average execution time for a function"""
        if func_name not in st.session_state.performance_metrics:
            return 0.0
        
        metrics = st.session_state.performance_metrics[func_name]
        if not metrics:
            return 0.0
        
        total_time = sum(m['execution_time'] for m in metrics)
        return total_time / len(metrics)
    
    def get_performance_report(self) -> Dict[str, Dict[str, Any]]:
        """Get a comprehensive performance report"""
        report = {}
        
        for func_name, metrics in st.session_state.performance_metrics.items():
            if metrics:
                times = [m['execution_time'] for m in metrics]
                report[func_name] = {
                    'count': len(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'last_execution': metrics[-1]['timestamp']
                }
        
        return report

def optimize_dataframe_display(df, max_rows: int = 100):
    """Optimize DataFrame display for better performance"""
    if len(df) > max_rows:
        # Show pagination controls
        if 'page_number' not in st.session_state:
            st.session_state.page_number = 0
        
        total_pages = len(df) // max_rows + (1 if len(df) % max_rows > 0 else 0)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Anterior", disabled=(st.session_state.page_number == 0)):
                st.session_state.page_number -= 1
                st.rerun()
        
        with col2:
            st.write(f"Página {st.session_state.page_number + 1} de {total_pages}")
        
        with col3:
            if st.button("Siguiente ➡️", disabled=(st.session_state.page_number >= total_pages - 1)):
                st.session_state.page_number += 1
                st.rerun()
        
        # Display current page
        start_idx = st.session_state.page_number * max_rows
        end_idx = min(start_idx + max_rows, len(df))
        return df.iloc[start_idx:end_idx]
    
    return df

def lazy_load_component(component_func: Callable, *args, **kwargs):
    """Lazy load components to improve initial page load time"""
    placeholder = st.empty()
    
    with placeholder.container():
        with st.spinner('Cargando...'):
            result = component_func(*args, **kwargs)
    
    return result

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_summary_stats(data: Dict[str, Any]) -> Dict[str, int]:
    """Get cached summary statistics for dashboard"""
    stats = {}
    
    for key, value in data.items():
        if hasattr(value, '__len__'):
            stats[f"{key}_count"] = len(value)
        elif isinstance(value, (int, float)):
            stats[key] = value
    
    return stats

def setup_session_state_defaults():
    """Setup default session state values to avoid repeated calculations"""
    defaults = {
        'viewport_width': 1200,
        'current_tab': 0,
        'data_loaded': False,
        'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'performance_tracking': True
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize performance tracker
tracker = PerformanceTracker() 