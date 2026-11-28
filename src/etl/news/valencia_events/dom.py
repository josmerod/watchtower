"""Small DOM helpers used by more than one Valencia events source."""

import re
from typing import Any, cast

from bs4 import Tag


def href_str(tag: Tag) -> str:
    """Read a tag's href as a plain str.

    bs4 types attribute values as ``str | AttributeValueList`` because
    multi-valued attributes (e.g. ``class``) come back as lists; ``href`` is
    never multi-valued, so the cast is typing-only and runtime-neutral.
    """
    return cast("str", tag.get("href", ""))


def text_of(node: Any, separator: str = " ") -> str:
    """Text of a node with runs of whitespace collapsed; "" for a missing node."""
    if node is None or not isinstance(node, Tag):
        return ""
    return re.sub(r"\s+", " ", node.get_text(separator, strip=True)).strip()


def absolute_url(href: str, base: str) -> str:
    """Turn a listing link into an absolute URL on ``base``; "" for an empty link."""
    href = (href or "").strip()
    if not href:
        return ""
    return href if href.startswith(("http://", "https://")) else base.rstrip("/") + ("" if href.startswith("/") else "/") + href


def is_meetup_date_text(text: str | None) -> bool:
    """Match span text carrying a year or a Spanish month abbreviation (Meetup fallback)."""
    return bool(text and ("202" in text or "ene" in text.lower() or "feb" in text.lower()))
