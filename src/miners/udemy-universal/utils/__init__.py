"""Utility functions."""

from .html_parser import find_attribute, find_text, parse_html
from .http import fetch_page_content, follow_redirect

__all__ = [
    "find_attribute",
    "find_text",
    "fetch_page_content",
    "follow_redirect",
    "parse_html",
]
