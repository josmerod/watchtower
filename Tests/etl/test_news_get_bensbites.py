"""Ben's Bites ETL (T-176): the newsletter feed replaces a Playwright scrape that failed every cycle.

The scrape of ``news.bensbites.com/trending`` ended with "No articles retrieved" and exit
code 0 since April 2026. These tests fix the records the feed produces and the exit code
the orchestrator reads.
"""

import json
import runpy
import time
from pathlib import Path
from typing import Any

import feedparser
import pytest
import requests

from src.etl.news import news_get_bensbites as bensbites
from src.utils import file_system

LONG_BODY = "A sentence of the body. " * 40
BENSBITES_FEED = (
    """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
<channel>
  <title>Ben's Bites</title>
  <item>
    <title>Commitment issues (app edition)</title>
    <description>It&#8217;s not me, it&#8217;s you</description>
    <link>https://www.bensbites.com/p/commitment-issues-app-edition</link>
    <guid isPermaLink="false">https://www.bensbites.com/p/commitment-issues-app-edition</guid>
    <dc:creator><![CDATA[Ben Tossell]]></dc:creator>
    <pubDate>Tue, 24 Nov 2026 14:04:45 GMT</pubDate>
    <content:encoded><![CDATA[<p>Last week, a mathematician &amp; a model.</p>]]></content:encoded>
  </item>
  <item>
    <title>Older issue with a long body</title>
    <description></description>
    <link>https://www.bensbites.com/p/older-issue</link>
    <pubDate>Thu, 19 Nov 2026 14:08:21 GMT</pubDate>
    <content:encoded><![CDATA[<p>"""
    + LONG_BODY.strip()
    + """</p>]]></content:encoded>
  </item>
  <item>
    <title>An entry without link is skipped</title>
    <pubDate>Fri, 20 Nov 2026 10:00:00 GMT</pubDate>
  </item>
</channel>
</rss>
"""
)
ISSUE_TITLES = ["Commitment issues (app edition)", "Older issue with a long body"]


class _Response:
    """The two attributes of a ``requests`` response the ETL reads."""

    def __init__(self, content: bytes, status: int = 200):
        self.content = content
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status} for the feed")


@pytest.fixture()
def no_waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Collect every pause instead of waiting; returns the list of seconds asked."""
    pauses: list[float] = []
    monkeypatch.setattr(time, "sleep", pauses.append)
    return pauses


@pytest.fixture()
def isolated_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Send the project-root lookups of a script run to tmp_path and create the output folder."""
    monkeypatch.setattr(file_system, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(file_system, "ensure_directories", lambda directories: None)
    (tmp_path / "data" / "bensbites").mkdir(parents=True)
    return tmp_path


def _feed_down(url: str, **kwargs: Any) -> _Response:
    raise requests.ConnectionError("feed down")


def _run_as_script(module: Any) -> int:
    """Run a script the way the orchestrator does (``python <file>``) and return its exit code."""
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(module.__file__), run_name="__main__")
    return int(excinfo.value.code)


def test_entries_become_issues_newest_first():
    issues = bensbites.process_entries(feedparser.parse(BENSBITES_FEED).entries)

    assert [issue["title"] for issue in issues] == ISSUE_TITLES
    newest = issues[0]
    assert newest["url"] == "https://www.bensbites.com/p/commitment-issues-app-edition"
    assert newest["published_at"] == "2026-11-24T14:04:45+00:00"
    assert newest["source"] == "Ben's Bites"
    assert newest["description"] == "It’s not me, it’s you"
    assert newest["metadata"]["author"] == "Ben Tossell"
    assert newest["metadata"]["api_source"] == "bensbites_rss"
    assert issues[1]["published_at"] == "2026-11-19T14:08:21+00:00"


def test_issue_without_subtitle_shows_the_opening_of_its_body():
    description = bensbites.process_entries(feedparser.parse(BENSBITES_FEED).entries)[1]["description"]

    assert description == f"{LONG_BODY.strip()[: bensbites.DESCRIPTION_MAX_CHARS].rstrip()}..."


def test_date_the_feed_does_not_carry_is_empty():
    feed = "<rss><channel><item><title>t</title><link>https://example.test/a</link></item></channel></rss>"

    assert bensbites.process_entries(feedparser.parse(feed).entries)[0]["published_at"] == ""


def test_fetch_returns_the_entries(monkeypatch: pytest.MonkeyPatch, no_waits: list[float]):
    asked: list[dict[str, Any]] = []

    def get(url: str, **kwargs: Any) -> _Response:
        asked.append({"url": url, **kwargs})
        return _Response(BENSBITES_FEED.encode("utf-8"))

    monkeypatch.setattr(bensbites.requests, "get", get)

    assert len(bensbites.fetch_feed()) == 3
    assert asked == [{"url": bensbites.RSS_URL, "headers": {"User-Agent": bensbites.SCRAPER_DEFAULT_USER_AGENT}, "timeout": 30}]
    assert no_waits == []


def test_fetch_gives_up_after_the_retries(monkeypatch: pytest.MonkeyPatch, no_waits: list[float]):
    monkeypatch.setattr(bensbites.requests, "get", _feed_down)

    assert bensbites.fetch_feed(max_retries=3, retry_delay=5) == []
    assert no_waits == [5, 5]


def test_fetch_rejects_a_page_that_is_not_a_feed(monkeypatch: pytest.MonkeyPatch, no_waits: list[float]):
    monkeypatch.setattr(bensbites.requests, "get", lambda url, **kwargs: _Response(b"<html><body>Maintenance</body></html>"))

    assert bensbites.fetch_feed(max_retries=2) == []


def test_script_exits_with_1_and_writes_nothing_when_the_feed_is_down(monkeypatch: pytest.MonkeyPatch, no_waits: list[float], isolated_output: Path):
    monkeypatch.setattr(bensbites.requests, "get", _feed_down)

    assert _run_as_script(bensbites) == 1
    assert list((isolated_output / "data" / "bensbites").iterdir()) == []


def test_script_exits_with_1_when_the_feed_is_empty(monkeypatch: pytest.MonkeyPatch, no_waits: list[float], isolated_output: Path):
    monkeypatch.setattr(bensbites.requests, "get", lambda url, **kwargs: _Response(b"<rss><channel></channel></rss>"))

    assert _run_as_script(bensbites) == 1


def test_main_keeps_the_previous_file_when_nothing_arrives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    output = tmp_path / "data" / "bensbites"
    output.mkdir(parents=True)
    previous = output / "bensbites_news.json"
    previous.write_text('[{"title": "the issue of yesterday"}]', encoding="utf-8")
    monkeypatch.setattr(bensbites, "fetch_feed", lambda: [])
    monkeypatch.setattr(bensbites, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(bensbites, "ensure_directories", lambda directories: None)

    assert bensbites.main() is False
    assert json.loads(previous.read_text(encoding="utf-8")) == [{"title": "the issue of yesterday"}]


def test_script_exits_with_0_and_writes_json_and_csv(monkeypatch: pytest.MonkeyPatch, no_waits: list[float], isolated_output: Path):
    monkeypatch.setattr(bensbites.requests, "get", lambda url, **kwargs: _Response(BENSBITES_FEED.encode("utf-8")))

    assert _run_as_script(bensbites) == 0

    folder = isolated_output / "data" / "bensbites"
    issues = json.loads((folder / "bensbites_news.json").read_text(encoding="utf-8"))
    assert [issue["title"] for issue in issues] == ISSUE_TITLES
    csv_text = (folder / "bensbites_news.csv").read_text(encoding="utf-8")
    assert csv_text.startswith("title,url,source,published_at,description,metadata")
    assert "It’s not me, it’s you" in csv_text
