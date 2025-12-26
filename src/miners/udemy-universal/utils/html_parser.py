"""HTML parsing utilities.

Provides centralized HTML parsing with BeautifulSoup.
"""

from bs4 import BeautifulSoup


def parse_html(content: str) -> BeautifulSoup:
    """Parse HTML content into BeautifulSoup object.

    Args:
        content: HTML content string

    Returns:
        BeautifulSoup object
    """
    return BeautifulSoup(content, "html5lib")


def find_text(element, selector: str | None = None, default: str = "") -> str:
    """Extract text from an HTML element.

    Args:
        element: BeautifulSoup element
        selector: CSS selector to find within element
        default: Default value if text not found

    Returns:
        Extracted text string
    """
    if element is None:
        return default

    if selector:
        found = element.select_one(selector)
        if found:
            return found.get_text(strip=True)
        return default

    return element.get_text(strip=True)


def find_attribute(element: str, attr: str, selector: str | None = None, default: str = "") -> str:
    """Extract attribute from an HTML element.

    Args:
        element: BeautifulSoup element
        attr: Attribute name
        selector: CSS selector to find within element
        default: Default value if attribute not found

    Returns:
        Attribute value string
    """
    if element is None:
        return default

    if selector:
        found = element.select_one(selector)
        if found and found.get(attr):
            return found[attr]
        return default

    return element.get(attr, default)
