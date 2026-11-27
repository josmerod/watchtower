"""Plain-text helpers for content that arrives as HTML."""

import re
from html import unescape

_TAG_OR_COMMENT = re.compile(r"<!--.*?-->|<[^>]+>", re.DOTALL)


def html_to_text(value: str | None) -> str:
    """Turn a snippet that carries HTML markup or entities into plain text.

    Tags and comments go out, entities are decoded and runs of whitespace
    collapse into one space. The result is stripped. Nothing is unescaped
    twice: ``&lt;b&gt;`` is text the author wanted to be read, so it stays
    once decoded.

    Args:
        value: The HTML snippet, or anything falsy (``None``, empty).

    Returns:
        The plain text; an empty string for an empty input.
    """
    if not value:
        return ""
    text = _TAG_OR_COMMENT.sub(" ", value) if "<" in value else value
    return re.sub(r"\s+", " ", unescape(text)).strip()
