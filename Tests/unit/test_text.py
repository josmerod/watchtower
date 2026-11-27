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
