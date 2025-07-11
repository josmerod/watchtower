"""
Utility module for setting up Python paths and imports in Streamlit components.
This centralizes the path configuration to avoid duplicating code.
"""
import sys
import os
from pathlib import Path

def setup_src_path():
    """Setup the src directory in Python path for imports"""
    # Add the src directory to the Python path
    current_dir = Path(__file__).parent
    src_dir = current_dir.parent.parent.parent.parent  # Go up from components -> fullstreamlit -> web -> src
    
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Alternative approach - add absolute path
    watchtower_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
    src_absolute = os.path.join(watchtower_root, 'src')
    if src_absolute not in sys.path:
        sys.path.insert(0, src_absolute)

def get_safe_logger(module_name: str = __name__):
    """Get logger with fallback if utils.logging is not available"""
    try:
        from utils.logging import get_logger
        return get_logger(module_name)
    except ImportError as e:
        print(f"❌ Failed to import get_logger in {module_name}: {e}")
        # Fallback - create a simple logger
        import logging
        return logging.getLogger(module_name)

# Auto-setup when imported
setup_src_path() 