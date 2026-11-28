"""Unit tests for the plain-text helper the ETLs share."""

from src.utils.text import html_to_text, plain_excerpt


def test_tags_comments_and_entities_go():
    value = '<!-- SC_OFF --><div class="md"><p>Funding &amp; sustainability: &#8216;the&#32;point&#8217;</p></div>'

    assert html_to_text(value) == "Funding & sustainability: ‘the point’"


def test_entities_are_decoded_once():
    # the author wrote "&lt;b&gt;" to show "<b>": it is text now, not a tag to remove
    assert html_to_text("<p>use &lt;b&gt;bold&lt;/b&gt; tags</p>") == "use <b>bold</b> tags"


def test_whitespace_collapses_and_the_result_is_stripped():
    assert html_to_text("  <p>One</p>\n\t<p>two</p>  <br/> three  ") == "One two three"


def test_plain_text_passes_through():
    assert html_to_text("plain") == "plain"
    assert html_to_text("a &lt; b") == "a < b"


def test_a_comparison_keeps_its_signs():
    """The pattern used to take everything between "<" and the next ">": "if a < b and b > c" came out "if a c" (T-208)."""
    assert html_to_text("if a < b and b > c") == "if a < b and b > c"
    assert html_to_text("<p>keep it if a < b</p>") == "keep it if a < b"  # a tag next to it still goes
    assert plain_excerpt("<p>count if a < b</p>", 40) == "count if a < b"


def test_text_shaped_like_a_tag_is_read_as_one():
    """Nothing tells "x <y> z" from markup with an unknown element: a browser shows "x  z" for it, and so does this.

    Sparing it would take the list of the element names HTML defines, and then a real unknown element would stay in the text.
    """
    assert html_to_text("x <y> z") == "x z"


def test_declarations_go_like_comments():
    assert html_to_text('<!DOCTYPE html><?xml version="1.0"?><p>a</p>') == "a"


def test_empty_input_gives_empty_text():
    assert html_to_text(None) == ""
    assert html_to_text("") == ""


def test_an_excerpt_is_cut_once_the_markup_is_gone():
    excerpt = plain_excerpt("<p>" + "word " * 100 + "<!-- a comment --></p>", 20)

    assert excerpt == "word word word word…"  # 20 characters of text, not of markup, ellipsis included
    assert len(plain_excerpt("abcdefghij" * 10, 50)) == 50


def test_an_excerpt_that_fits_is_the_whole_text():
    assert plain_excerpt("<p>Short &amp; sweet</p>", 50) == "Short & sweet"
    assert plain_excerpt(None, 50) == ""
