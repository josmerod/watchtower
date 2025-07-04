"""Helper utility functions for the Watchtower Streamlit application."""

from datetime import datetime
from urllib.parse import unquote

import pandas as pd
import streamlit as st


def format_timestamp(timestamp):
    """Convert timestamp to readable date format."""
    try:
        if pd.isna(timestamp):
            return "N/A"
        # Convert milliseconds to seconds if needed
        if timestamp > 1e11:  # Likely milliseconds
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "Fecha inválida"


def clean_url(url):
    """Clean and format URL for display."""
    if pd.isna(url):
        return "N/A"
    try:
        return unquote(url.replace("\\", ""))
    except Exception:
        return url


def make_clickable(link, text=None):
    """Create clickable link for dataframe."""
    if pd.isna(link):
        return "N/A"
    text = text if text else clean_url(link)
    return f'<a href="{clean_url(link)}" target="_blank">{text}</a>'


def get_responsive_cols():
    """Function to determine number of columns based on screen width."""
    # Get the current viewport width using JavaScript
    viewport_width = st.session_state.get('viewport_width', 1200)  # Default to 1200px

    if viewport_width >= 1200:
        return 6  # Large screens
    elif viewport_width >= 992:
        return 4  # Medium-large screens
    elif viewport_width >= 768:
        return 3  # Medium screens
    elif viewport_width >= 576:
        return 2  # Small screens
    else:
        return 1  # Extra small screens
