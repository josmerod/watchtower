"""The four News ETLs store plain text, not the markup the feeds carry (T-190).

Measured on 2026-11-27 on a live run of each ETL: every one of the 68 Kagi descriptions was HTML, up to 22,915 characters (the whole
article); every one of the 15 Microsiervos descriptions (images with styles, up to 5,611); every one of the 100 Medium summaries, which
also sat under ``metadata.summary`` where the News tab never looked, so those cards had no text. Dev.to only kept an entity
("Welcome&nbsp;!"). Each ETL now goes through the shared ``html_to_text`` / ``plain_excerpt``, like the Knowledge Garden ones (T-164),
and Medium's summary also sits at the top level. Fixtures only: no network, nothing under data/ is read or written.
"""

from types import SimpleNamespace

import pytest

from src.etl.news import microsiervos_etl, news_get_devto, news_get_genai_medium, news_get_kagi

MICROSIERVOS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Microsiervos</title>
<item><title>T&amp;amp;i &amp; m&#225;s</title><link>https://example.invalid/1</link>
<pubDate>Fri, 27 Nov 2026 10:00:00 +0100</pubDate>
<description><p class="imagen" style="text-align: center;"><a href="https://example.invalid/a"><img alt="Lo-pi Radio" src="x.png" /></a></p><p>Body &amp; more</p></description></item>
</channel></rss>"""


def _microsiervos(feed: bytes) -> microsiervos_etl.MicrosiervosETL:
    """An instance without its constructor, which creates data/ in the real tree, answering with the given feed."""
    etl = microsiervos_etl.MicrosiervosETL.__new__(microsiervos_etl.MicrosiervosETL)
    session = SimpleNamespace(get=lambda url, timeout: SimpleNamespace(content=feed, raise_for_status=lambda: None))
    etl.max_retries = 1  # what http_session passes along
    etl.proxy_manager = SimpleNamespace(get_session=lambda retries: session)
    return etl


def test_microsiervos_descriptions_are_plain_excerpts() -> None:
    (item,) = _microsiervos(MICROSIERVOS_FEED).extract()

    assert item["title"] == "T&i & más"  # the feed double-escapes it: once by the XML, once by html_to_text
    assert item["description"] == "Body & more"  # the image went out with its markup
    assert item["published_at"] == "2026-11-27T09:00:00+00:00"


def test_microsiervos_cuts_a_long_article_after_the_markup_is_gone() -> None:
    feed = MICROSIERVOS_FEED.replace(b"<p>Body &amp; more</p>", ("<p>" + "word " * 200 + "</p>").encode())

    (item,) = _microsiervos(feed).extract()

    assert len(item["description"]) == 500 and item["description"].endswith("word…") and "<" not in item["description"]


def test_kagi_descriptions_are_plain_excerpts() -> None:
    # What feedparser hands over: tags in place, entities decoded once
    body = "<p>" + "fact " * 200 + "&amp; figures</p>"
    raw = {"science": [{"title": "Bread &amp; Fred", "url": "https://example.invalid/1", "published_at": "2026-11-27T10:00:00Z", "source": "kagi_science", "category": "science", "description": body}]}

    (article,) = news_get_kagi.process_kagi_articles(raw)["science"]

    assert article["title"] == "Bread & Fred"
    assert article["description"].startswith("fact fact") and article["description"].endswith("…") and len(article["description"]) == 500
    assert "<" not in article["description"]


def test_a_short_kagi_description_keeps_its_whole_text() -> None:
    raw = {"science": [{"title": "Short", "url": "https://example.invalid/2", "description": "<p>Bread &amp; Fred, free until <b>Thursday</b></p><img src=\"x.png\">"}]}

    (article,) = news_get_kagi.process_kagi_articles(raw)["science"]

    assert article["description"] == "Bread & Fred, free until Thursday"


def test_devto_titles_and_summaries_are_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [{"title": "Golden &amp; metric", "url": "https://example.invalid/1", "published_at": "2026-11-27T10:00:00Z", "user": {"username": "u"}, "description": "Welcome&nbsp;!  In Part 1, <b>we</b> set up"}]
    monkeypatch.setattr(news_get_devto.requests, "get", lambda *args, **kwargs: SimpleNamespace(json=lambda: payload, raise_for_status=lambda: None))

    (article,) = news_get_devto.get_devto_articles()

    assert article["title"] == "Golden & metric"
    assert article["summary"] == "Welcome ! In Part 1, we set up"


def test_medium_summaries_are_plain_and_where_the_news_tab_reads_them() -> None:
    summary = '<div class="medium-feed-item"><p class="medium-feed-image"><a href="https://example.invalid/i"><img alt="Cover" src="c.png"></a></p><p>Why <i>AI</i> matters &amp; more</p></div>'
    raw = [{"title": "Reshape &amp; Co.", "url": "https://example.invalid/3", "published_at": "2026-11-27T10:00:00Z", "source": "medium.com", "author": "a", "summary": summary, "medium_id": "m1", "feed_source": "https://example.invalid/feed", "tags": []}]

    (article,) = news_get_genai_medium.process_medium_articles(raw)

    assert article["title"] == "Reshape & Co."
    assert article["summary"] == "Why AI matters & more"  # the top level: news_tab reads article.get("summary")
    assert article["metadata"]["summary"] == "Why AI matters & more"  # the old place keeps it too
