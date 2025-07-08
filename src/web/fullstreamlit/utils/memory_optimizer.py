"""
Memory optimization utilities for the Watchtower Streamlit application.
"""

import gc
import streamlit as st
import pandas as pd
import psutil
import os
from typing import Dict, Any


class MemoryOptimizer:
    """Memory optimization and monitoring utilities"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent()
        }
    
    def cleanup_session_state(self, keep_keys: list = None) -> int:
        """Clean up old session state data, keeping specified keys"""
        if keep_keys is None:
            keep_keys = ['current_tab_index', 'performance_metrics', 'ultra_data_cache']
        
        removed_count = 0
        keys_to_remove = []
        
        for key in st.session_state.keys():
            if key not in keep_keys:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del st.session_state[key]
            removed_count += 1
        
        return removed_count
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return statistics"""
        before_count = len(gc.get_objects())
        collected = gc.collect()
        after_count = len(gc.get_objects())
        
        return {
            'collected': collected,
            'before_objects': before_count,
            'after_objects': after_count,
            'freed_objects': before_count - after_count
        }
    
    def optimize_dataframe_memory(self, df) -> Any:
        """Optimize DataFrame memory usage"""
        if hasattr(df, 'memory_usage'):
            # Convert object columns to category where appropriate
            for col in df.select_dtypes(include=['object']).columns:
                if df[col].nunique() / len(df) < 0.5:  # If less than 50% unique values
                    df[col] = df[col].astype('category')
            
            # Downcast numeric types
            for col in df.select_dtypes(include=['int']).columns:
                df[col] = pd.to_numeric(df[col], downcast='integer')
            
            for col in df.select_dtypes(include=['float']).columns:
                df[col] = pd.to_numeric(df[col], downcast='float')
        
        return df
    
    def get_cache_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics for caches"""
        stats = {}
        
        # Session state cache size
        session_state_size = 0
        if hasattr(st.session_state, 'ultra_data_cache'):
            session_state_size = len(st.session_state.ultra_data_cache)
        
        stats['session_cache_entries'] = session_state_size
        
        # Performance metrics size
        perf_metrics_size = 0
        if hasattr(st.session_state, 'performance_metrics'):
            perf_metrics_size = len(st.session_state.performance_metrics)
        
        stats['performance_metrics_entries'] = perf_metrics_size
        
        return stats


# Global memory optimizer instance
memory_optimizer = MemoryOptimizer()


def monitor_memory_usage():
    """Display memory usage in the sidebar"""
    with st.sidebar:
        st.subheader("💾 Memory Monitor")
        
        memory_stats = memory_optimizer.get_memory_usage()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("RAM Usage", f"{memory_stats['rss_mb']:.1f} MB")
        with col2:
            st.metric("Memory %", f"{memory_stats['percent']:.1f}%")
        
        # Memory optimization controls
        if st.button("🧹 Cleanup Memory"):
            gc_stats = memory_optimizer.force_garbage_collection()
            cleaned_sessions = memory_optimizer.cleanup_session_state()
            
            st.success(f"Freed {gc_stats['freed_objects']} objects")
            st.info(f"Cleaned {cleaned_sessions} session items")
            st.rerun()


def optimize_app_memory():
    """Run memory optimization routines"""
    # Force garbage collection
    memory_optimizer.force_garbage_collection()
    
    # Clean up old session state data
    memory_optimizer.cleanup_session_state()