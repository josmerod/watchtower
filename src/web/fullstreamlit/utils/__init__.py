"""Utilities module for Watchtower Streamlit Application."""

from .data_loader import load_coursera_courses, load_courses_data
from .data_service import DataService

__all__ = ["DataService", "load_coursera_courses", "load_courses_data"]
