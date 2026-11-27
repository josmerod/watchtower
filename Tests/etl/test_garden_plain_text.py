"""The Knowledge Garden ETLs store plain text, not the markup the feeds carry (T-164).

Measured on 2026-11-27 on copies of production: every LessWrong summary began with ``<p><i><span``, every Reddit one
with ``<!-- SC_OFF --><div class="md">``, and the titles of opensource and podcasts kept ``&amp;`` and ``&#8217;``.
Only the cards cleaned at render time, the list showed no summary, and the search matched the markup: "span" found
81 of 100 LessWrong posts. Each ETL now goes through the shared ``html_to_text`` / ``plain_excerpt``, cutting only
once the text is plain. Fixtures only: no network, nothing under data/ is read or written.
"""

import logging
from types import SimpleNamespace

import pytest

from src.etl.intelligence import lesswrong_etl
from src.etl.news import news_get_hackernews_ask, news_get_podcasts, reddit_unified_etl
from src.etl.opensource.opensource_projects_etl import OpenSourceProjectsETL
from src.etl.rss_feeds.rss_feed_etl import RSSFeedETL
from src.etl.substack.substack_etl import SubstackETL

REDDIT_FEED = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>r/tech</title>
<entry><title>Ask &amp;amp; answer</title><link href="https://www.reddit.com/r/tech/comments/x/"/>
<updated>2026-11-27T10:00:00Z</updated>
<content type="html">&lt;!-- SC_OFF --&gt;&lt;div class="md"&gt;&lt;p&gt;Body &amp;amp; more&lt;/p&gt;&lt;/div&gt;</content>
<author><name>u</name></author></entry></feed>"""


def _bare(etl_class):
    """An ETL instance without its constructor, which creates ``data/<name>/output/`` in the real tree."""
    etl = etl_class.__new__(etl_class)
    etl.logger = logging.getLogger("garden-plain-text-test")
    etl.metrics = SimpleNamespace()
    return etl


def test_lesswrong_summaries_are_plain_and_cut_after_the_markup_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    body = "<p>" + "word " * 600 + "</p>"
    posts = [{"_id": "a", "title": "A <i>title</i> &amp; more", "pageUrl": "/posts/a", "htmlBody": body}, {"_id": "b", "title": "Short", "pageUrl": "/posts/b", "htmlBody": "<p>Short <i>one</i></p>"}]
    monkeypatch.setattr(lesswrong_etl.requests, "post", lambda *args, **kwargs: SimpleNamespace(json=lambda: {"data": {"posts": {"results": posts}}}, raise_for_status=lambda: None))

    long, short = lesswrong_etl.fetch_lesswrong()

    assert long["title"] == "A title & more"
    assert len(long["summary"]) == 2000 and long["summary"].endswith("…")  # 2000 characters of text, ellipsis included
    assert "<" not in long["summary"]
    assert short["summary"] == "Short one"  # no ellipsis on what was never cut


def test_reddit_summaries_lose_the_markup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reddit_unified_etl.requests, "get", lambda *args, **kwargs: SimpleNamespace(content=REDDIT_FEED, raise_for_status=lambda: None))

    (post,) = reddit_unified_etl.fetch_subreddit_rss("tech")

    assert post["title"] == "Ask & answer"
    assert post["summary"] == "Body & more"


def test_ask_hn_text_is_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = {"askstories.json": [1], "1.json": {"id": 1, "title": "Ask HN: Best &amp; editor?", "text": "<p>I use <i>vim</i> &amp; emacs</p>", "by": "u", "score": 1, "descendants": 0, "time": 1790000000, "type": "story", "kids": []}}
    session = SimpleNamespace(get=lambda url, timeout: SimpleNamespace(json=lambda: answers[url.rsplit("/", 1)[-1]], raise_for_status=lambda: None))
    monkeypatch.setattr(news_get_hackernews_ask, "time", SimpleNamespace(sleep=lambda seconds: None))

    (post,) = news_get_hackernews_ask.fetch_ask_hn_posts(session)

    assert post["title"] == "Ask HN: Best & editor?"
    assert post["text"] == "I use vim & emacs"


def test_podcast_titles_are_decoded() -> None:
    (episode,) = news_get_podcasts.process_podcast_episodes([{"title": "Cat &amp; Dog&#8217;s show", "url": "https://example.invalid/ep", "source": "Syntax", "published_at": "x", "episode_id": "ep", "feed_source": "f"}])

    assert episode["title"] == "Cat & Dog’s show"


def test_rss_descriptions_are_plain_excerpts() -> None:
    (article,) = _bare(RSSFeedETL).transform([{"title": "Build &amp; run", "link": "https://example.invalid/1", "summary": '<img src="x.png">' + "step " * 200, "_feed_name": "Blog"}])

    assert article["title"] == "Build & run"
    assert article["description"].startswith("step step") and article["description"].endswith("…")
    assert "<" not in article["description"] and len(article["description"]) == 500


def test_substack_descriptions_are_plain_excerpts() -> None:
    (article,) = _bare(SubstackETL).transform([{"title": "Week &amp; notes", "link": "https://example.invalid/2", "summary": "<p>" + "note " * 100 + "</p>", "_newsletter_slug": "blog"}])

    assert article["title"] == "Week & notes"
    assert article["description"].startswith("note note") and article["description"].endswith("…")
    assert "<" not in article["description"] and len(article["description"]) == 300


def test_opensource_titles_and_descriptions_are_decoded_once() -> None:
    (project,) = _bare(OpenSourceProjectsETL).transform([{"title": "Lib &amp; tool", "description": "Fast &#8217;n light", "url": "https://example.invalid/lib", "tags": [], "published_at": "2026-11-27"}])

    assert project.title == "Lib & tool"
    assert project.description == "Fast ’n light"
