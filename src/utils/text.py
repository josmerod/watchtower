"""Plain-text helpers for content that arrives as HTML."""

import re
from html import unescape

# What goes out as markup: a comment, a declaration, or a tag, which starts with "<" or "</" and a letter. Anything
# else that starts with "<" is text, as the signs of "if a < b and b > c": taking everything up to the next ">" ate them (T-208).
_TAG_OR_COMMENT = re.compile(r"<!--.*?-->|<!DOCTYPE[^>]*>|<\?[^>]*\?>|</?[A-Za-z][^>]*>", re.DOTALL | re.IGNORECASE)


def html_to_text(value: str | None) -> str:
    """Turn a snippet that carries HTML markup or entities into plain text.

    Tags and comments go out, entities are decoded and runs of whitespace
    collapse into one space. The result is stripped. Nothing is unescaped
    twice: ``&lt;b&gt;`` is text the author wanted to be read, so it stays
    once decoded.

    Only markup shaped like markup goes out, so a comparison keeps its signs.
    The limit is a comparison that is shaped like a tag: ``x <y> z`` comes
    out ``x z``, as a browser would read it, an unknown element around a word.

    Args:
        value: The HTML snippet, or anything falsy (``None``, empty).

    Returns:
        The plain text; an empty string for an empty input.
    """
    if not value:
        return ""
    text = _TAG_OR_COMMENT.sub(" ", value) if "<" in value else value
    return re.sub(r"\s+", " ", unescape(text)).strip()


def plain_excerpt(value: str | None, limit: int) -> str:
    """``html_to_text`` as an excerpt of at most ``limit`` characters, ending in an ellipsis when something was cut.

    The cut comes after the markup is gone: inside a tag it would leave half of it, inside an entity a bare ``&``.

    Args:
        value: The HTML snippet, or anything falsy (``None``, empty).
        limit: The most characters the excerpt may have, ellipsis included.

    Returns:
        The excerpt; an empty string for an empty input.
    """
    text = html_to_text(value)
    return f"{text[: limit - 1].rstrip()}…" if len(text) > limit else text
