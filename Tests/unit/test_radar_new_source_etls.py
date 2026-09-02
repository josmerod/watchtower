"""Unit tests for the T-070/T-078 Tech Radar source ETLs: Phoronix, Unraid
forums, the hardened Lobsters fetch, and the T-078 additions (GitHub
Trending HTML, ServeTheHome RSS, Xataka RSS).

All feeds are exercised through fixture XML/HTML + monkeypatched
``requests.get`` — no network in unit tests.
"""

import json

import feedparser
import requests

from src.etl.github import github_trending_etl as trending_etl
from src.etl.news import news_get_lobsters as lobsters_etl
from src.etl.news import news_get_phoronix as phoronix_etl
from src.etl.news import news_get_sth as sth_etl
from src.etl.news import news_get_unraid_forums as unraid_etl
from src.etl.news import news_get_xataka as xataka_etl


class _BytesResponse:
    """Minimal requests.Response stand-in carrying raw feed bytes."""

    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def _rss(items: list[str]) -> bytes:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>fixture</title>\n' + "\n".join(items) + "\n</channel></rss>\n").encode()


def _item(title: str, link: str, pub: str, description: str = "&lt;p&gt;some &lt;b&gt;markup&lt;/b&gt;&lt;/p&gt;") -> str:
    return f"<item><title>{title}</title><link>{link}</link><pubDate>{pub}</pubDate><description>{description}</description></item>"


# ---------------------------------------------------------------------------
# Phoronix
# ---------------------------------------------------------------------------

PHORONIX_FEED = _rss(
    [
        _item("Linux 7.3 Will Begin Checking USB-C Cables", "https://www.phoronix.com/news/Linux-7.3-USB", "Fri, 28 Aug 2026 06:15:13 -0400"),
        _item("AMD Ryzen Benchmarks", "https://www.phoronix.com/news/amd-ryzen", "Thu, 27 Aug 2026 09:00:00 +0000", "plain text summary"),
    ]
)


def test_phoronix_parses_fixture_feed(monkeypatch):
    monkeypatch.setattr(phoronix_etl.requests, "get", lambda *a, **kw: _BytesResponse(PHORONIX_FEED))
    entries = phoronix_etl.fetch_phoronix()
    assert len(entries) == 2
    first = entries[0]
    assert first["title"] == "Linux 7.3 Will Begin Checking USB-C Cables"
    assert first["link"] == "https://www.phoronix.com/news/Linux-7.3-USB"
    assert first["published"] == "2026-08-28T06:15:13-04:00"  # RSS date -> ISO
    assert first["source"] == "phoronix" and first["source_category"] == "linux_hardware"
    assert first["platform"] == "phoronix" and first["content_type"] == "news_article"
    assert "some markup" in first["summary"] and "<" not in first["summary"]  # HTML stripped


def test_phoronix_caps_items_at_25(monkeypatch):
    feed = _rss([_item(f"story {i}", f"https://www.phoronix.com/news/{i}", "Fri, 28 Aug 2026 06:15:13 -0400") for i in range(30)])
    monkeypatch.setattr(phoronix_etl.requests, "get", lambda *a, **kw: _BytesResponse(feed))
    entries = phoronix_etl.fetch_phoronix()
    assert len(entries) == phoronix_etl.MAX_ITEMS == 25
    assert entries[0]["title"] == "story 0"  # feed order kept (newest first upstream)


def test_phoronix_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(phoronix_etl.requests, "get", _boom)
    assert phoronix_etl.fetch_phoronix() == []


def test_phoronix_save_writes_latest_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(phoronix_etl, "get_project_root", lambda: str(tmp_path))
    entries = [{"title": "t", "link": "https://x/1", "published": "2026-08-28T06:15:13-04:00", "source": "phoronix"}]
    phoronix_etl.save_phoronix_entries(entries)
    data_dir = tmp_path / "data" / "news"
    latest = json.loads((data_dir / "phoronix_latest.json").read_text(encoding="utf-8"))
    assert latest == entries
    snapshots = [p for p in data_dir.glob("phoronix_*.json") if p.name != "phoronix_latest.json"]
    assert len(snapshots) == 1
    phoronix_etl.save_phoronix_entries([])  # empty run skips saving…
    assert json.loads((data_dir / "phoronix_latest.json").read_text(encoding="utf-8")) == entries  # …last-good kept


# ---------------------------------------------------------------------------
# Unraid forums (Invision feed at forums.unraid.net)
# ---------------------------------------------------------------------------

UNRAID_FEED = _rss(
    [
        _item("Machine check event error help", "https://forums.unraid.net/topic/200406-machine-check-event-error-help/", "Fri, 28 Aug 2026 07:47:24 +0000"),
        _item("Unraid 7.1 released", "https://forums.unraid.net/topic/200400-unraid-7-1/", "Thu, 27 Aug 2026 18:00:00 +0000"),
    ]
)


def test_unraid_parses_fixture_feed(monkeypatch):
    monkeypatch.setattr(unraid_etl.requests, "get", lambda *a, **kw: _BytesResponse(UNRAID_FEED))
    entries = unraid_etl.fetch_unraid_forums()
    assert len(entries) == 2
    first = entries[0]
    assert first["title"] == "Machine check event error help"
    assert first["link"].startswith("https://forums.unraid.net/topic/")
    assert first["published"] == "2026-08-28T07:47:24+00:00"
    assert first["source"] == "unraid_forums" and first["source_category"] == "self_hosting"
    assert first["platform"] == "forums.unraid.net" and first["content_type"] == "forum_thread"


def test_unraid_uses_focused_announcements_feed_with_fallback():
    # T-075: primary is the News & Announcements forum feed (id 7); the noisy
    # all-topics aggregate is only a fallback.
    assert unraid_etl.NEWS_FEED_URL == "https://forums.unraid.net/forum/7-announcements.xml/"
    assert unraid_etl.ALL_TOPICS_FEED_URL == "https://forums.unraid.net/rss/1-all-unraid-topics.xml/"


def test_unraid_marks_items_with_serving_feed(monkeypatch):
    monkeypatch.setattr(unraid_etl.requests, "get", lambda *a, **kw: _BytesResponse(UNRAID_FEED))
    entries = unraid_etl.fetch_unraid_forums()
    assert all(e["feed"] == "announcements" for e in entries)


def _parse_entries(response):
    """Feed-parse helper mirroring _fetch_feed's parsing step."""
    return list(feedparser.parse(response.content).entries)


def test_unraid_falls_back_to_all_topics_when_news_feed_fails(monkeypatch):
    calls = []

    def _flaky_fetch(url):
        calls.append(url)
        if url == unraid_etl.NEWS_FEED_URL:
            raise requests.ConnectionError("news feed down")
        return _parse_entries(_BytesResponse(UNRAID_FEED))

    monkeypatch.setattr(unraid_etl, "_fetch_feed", _flaky_fetch)
    entries = unraid_etl.fetch_unraid_forums()
    assert calls == [unraid_etl.NEWS_FEED_URL, unraid_etl.ALL_TOPICS_FEED_URL]
    assert len(entries) == 2
    assert all(e["feed"] == "all_topics" for e in entries)


def test_unraid_falls_back_when_news_feed_is_empty(monkeypatch):
    def _empty_then_feed(url):
        return [] if url == unraid_etl.NEWS_FEED_URL else _parse_entries(_BytesResponse(UNRAID_FEED))

    monkeypatch.setattr(unraid_etl, "_fetch_feed", _empty_then_feed)
    entries = unraid_etl.fetch_unraid_forums()
    assert len(entries) == 2 and entries[0]["feed"] == "all_topics"


def test_unraid_caps_items_at_25(monkeypatch):
    feed = _rss([_item(f"thread {i}", f"https://forums.unraid.net/topic/{i}/", "Fri, 28 Aug 2026 07:47:24 +0000") for i in range(40)])
    monkeypatch.setattr(unraid_etl.requests, "get", lambda *a, **kw: _BytesResponse(feed))
    assert len(unraid_etl.fetch_unraid_forums()) == unraid_etl.MAX_ITEMS == 25


def test_unraid_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(unraid_etl.requests, "get", _boom)
    assert unraid_etl.fetch_unraid_forums() == []


def test_unraid_save_keeps_last_good_on_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(unraid_etl, "get_project_root", lambda: str(tmp_path))
    good = [{"title": "t", "link": "https://x/1", "published": "2026-08-28T07:47:24+00:00", "source": "unraid_forums"}]
    unraid_etl.save_unraid_forums_entries(good)
    latest_path = tmp_path / "data" / "news" / "unraid_forums_latest.json"
    unraid_etl.save_unraid_forums_entries([])
    assert json.loads(latest_path.read_text(encoding="utf-8")) == good


# ---------------------------------------------------------------------------
# Lobsters — hardened fetch (requests + UA + timeout, Wired pattern)
# ---------------------------------------------------------------------------

LOBSTERS_FEED = _rss(
    [
        _item("Changes to SourceHut's terms of service", "https://sourcehut.org/blog/2026-08-27-tos-changes/", "Thu, 27 Aug 2026 03:37:19 -0500"),
    ]
)


def test_lobsters_hardened_fetch_parses_fixture(monkeypatch):
    monkeypatch.setattr(lobsters_etl.requests, "get", lambda *a, **kw: _BytesResponse(LOBSTERS_FEED))
    entries = lobsters_etl.fetch_lobsters()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["title"] == "Changes to SourceHut's terms of service"
    assert entry["link"] == "https://sourcehut.org/blog/2026-08-27-tos-changes/"
    assert entry["published"] == "2026-08-27T03:37:19-05:00"
    assert entry["source"] == "lobsters" and entry["source_category"] == "developer_community"


def test_lobsters_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(lobsters_etl.requests, "get", _boom)
    assert lobsters_etl.fetch_lobsters() == []


# ---------------------------------------------------------------------------
# T-078: GitHub Trending (github.com/trending server-rendered HTML)
# ---------------------------------------------------------------------------


class _TextResponse:
    """Minimal requests.Response stand-in carrying decoded HTML."""

    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


def _trending_card(repo: str, description: str, language: str, stars_today: str, total_stars: str) -> str:
    """One trending ``article.Box-row`` mirroring live markup (T-078 probe).

    Includes the A/B-tested ``tmp-``-prefixed utility classes on purpose —
    the ETL selectors must not depend on them.
    """
    owner, name = repo.split("/", 1)
    return (
        '<article class="Box-row">\n'
        ' <h2 class="h3 lh-condensed">\n'
        f'  <a class="Link" href="/{repo}"><svg aria-hidden="true"></svg><span class="text-normal">{owner} /</span> {name}</a>\n'
        " </h2>\n"
        ' <p class="col-9 color-fg-muted my-1 tmp-pr-4">' + description + "</p>\n"
        ' <div class="f6 color-fg-muted mt-2">\n'
        '  <span class="tmp-mr-3 d-inline-block ml-0 tmp-ml-0"><span class="repo-language-color" style="background-color: #3572A5"></span>'
        f'<span itemprop="programmingLanguage">{language}</span></span>\n'
        f'  <a class="tmp-mr-3 Link Link--muted d-inline-block" href="/{repo}/stargazers"><svg aria-label="star"></svg>{total_stars}</a>\n'
        f'  <span class="d-inline-block float-sm-right">{stars_today}</span>\n'
        " </div>\n"
        "</article>\n"
    )


TRENDING_HTML = (
    "<html><body><main>\n"
    + _trending_card("Gitlawb/openclaude", "runs anywhere. uses anything", "TypeScript", "80 stars today", "31,572")
    + _trending_card("THU-MAIC/OpenMAIC", "Open Multi-Agent Interactive Classroom", "TypeScript", "3,128 stars today", "12,404")
    + _trending_card("no-lang/no-stars", "Minimal card exercising the empty-field paths", "", "", "")
    + "</main></body></html>\n"
)


def test_github_trending_parses_fixture_html(monkeypatch):
    monkeypatch.setattr(trending_etl.requests, "get", lambda *a, **kw: _TextResponse(TRENDING_HTML))
    records = trending_etl.fetch_github_trending()
    assert len(records) == 3
    first = records[0]
    assert first["repo"] == "Gitlawb/openclaude" and first["title"] == "Gitlawb/openclaude"
    assert first["link"] == "https://github.com/Gitlawb/openclaude"
    assert first["language"] == "TypeScript" and first["description"] == "runs anywhere. uses anything"
    assert first["stars_today"] == 80 and first["total_stars"] == 31572  # comma-grouped -> int
    assert first["source"] == "github_trending" and first["source_category"] == "open_source"
    assert first["summary"].startswith("⭐ 80 today · TypeScript · runs anywhere")
    # Card without counters degrades gracefully instead of crashing.
    bare = records[2]
    assert bare["repo"] == "no-lang/no-stars"
    assert bare["stars_today"] == 0 and bare["total_stars"] == 0
    assert "today" not in bare["summary"] and bare["summary"].startswith("Minimal card")


def test_github_trending_caps_items_at_25(monkeypatch):
    html = "<html><body>" + "".join(_trending_card(f"o/r{i}", "d", "Python", "1 stars today", "10") for i in range(30)) + "</body></html>"
    monkeypatch.setattr(trending_etl.requests, "get", lambda *a, **kw: _TextResponse(html))
    records = trending_etl.fetch_github_trending()
    assert len(records) == trending_etl.MAX_ITEMS == 25
    assert records[0]["repo"] == "o/r0"  # page (rank) order kept


def test_github_trending_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(trending_etl.requests, "get", _boom)
    assert trending_etl.fetch_github_trending() == []


def test_github_trending_save_keeps_last_good_on_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(trending_etl, "get_project_root", lambda: str(tmp_path))
    good = [{"repo": "o/r", "title": "o/r", "link": "https://github.com/o/r", "source": "github_trending"}]
    trending_etl.save_github_trending(good)
    latest_path = tmp_path / "data" / "github" / "github_trending_latest.json"
    snapshots = [p for p in (tmp_path / "data" / "github").glob("github_trending_*.json") if p.name != "github_trending_latest.json"]
    assert len(snapshots) == 1
    trending_etl.save_github_trending([])  # empty run skips saving…
    assert json.loads(latest_path.read_text(encoding="utf-8")) == good  # …last-good kept


# ---------------------------------------------------------------------------
# T-078: ServeTheHome (RSS, Wired pattern)
# ---------------------------------------------------------------------------

STH_FEED = _rss(
    [
        _item("NVIDIA RISC-V for NVIDIA GPUs at Hot Chips 2026", "https://www.servethehome.com/nvidia-risc-v-hot-chips/", "Tue, 01 Sep 2026 19:00:56 +0000"),
        _item("Dell Pro 5 14 Laptop Review", "https://www.servethehome.com/dell-pro-5-14/", "Mon, 31 Aug 2026 17:15:18 +0000", "plain text summary"),
    ]
)


def test_sth_parses_fixture_feed(monkeypatch):
    monkeypatch.setattr(sth_etl.requests, "get", lambda *a, **kw: _BytesResponse(STH_FEED))
    entries = sth_etl.fetch_servethehome()
    assert len(entries) == 2
    first = entries[0]
    assert first["title"] == "NVIDIA RISC-V for NVIDIA GPUs at Hot Chips 2026"
    assert first["link"] == "https://www.servethehome.com/nvidia-risc-v-hot-chips/"
    assert first["published"] == "2026-09-01T19:00:56+00:00"  # RSS date -> ISO
    assert first["source"] == "servethehome" and first["source_category"] == "server_hardware"
    assert first["platform"] == "servethehome" and first["content_type"] == "news_article"
    assert "some markup" in first["summary"] and "<" not in first["summary"]  # HTML stripped


def test_sth_caps_items_at_25(monkeypatch):
    feed = _rss([_item(f"story {i}", f"https://www.servethehome.com/news/{i}", "Tue, 01 Sep 2026 19:00:56 +0000") for i in range(30)])
    monkeypatch.setattr(sth_etl.requests, "get", lambda *a, **kw: _BytesResponse(feed))
    assert len(sth_etl.fetch_servethehome()) == sth_etl.MAX_ITEMS == 25


def test_sth_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(sth_etl.requests, "get", _boom)
    assert sth_etl.fetch_servethehome() == []


def test_sth_save_writes_latest_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(sth_etl, "get_project_root", lambda: str(tmp_path))
    entries = [{"title": "t", "link": "https://x/1", "published": "2026-09-01T19:00:56+00:00", "source": "servethehome"}]
    sth_etl.save_servethehome_entries(entries)
    data_dir = tmp_path / "data" / "news"
    assert json.loads((data_dir / "servethehome_latest.json").read_text(encoding="utf-8")) == entries
    snapshots = [p for p in data_dir.glob("servethehome_*.json") if p.name != "servethehome_latest.json"]
    assert len(snapshots) == 1
    sth_etl.save_servethehome_entries([])  # empty run skips saving…
    assert json.loads((data_dir / "servethehome_latest.json").read_text(encoding="utf-8")) == entries  # …last-good kept


# ---------------------------------------------------------------------------
# T-078: Xataka (Spanish tech blog RSS, Wired pattern)
# ---------------------------------------------------------------------------

XATAKA_FEED = _rss(
    [
        _item(
            "Anthropic lanza Fable 5.1",
            "https://www.xataka.com/robotica-e-ia/anthropic-lanza-fable-5-1",
            "Wed, 02 Sep 2026 09:14:30 +0200",
            '&lt;img alt="x" src="x.jpg"&gt; Anthropic presenta &lt;b&gt;Fable&lt;/b&gt; 5.1, su modelo más potente.',
        ),
        _item("La IA puede reducir un 10% de emisiones", "https://www.xataka.com/energia/ia-emisiones", "Wed, 02 Sep 2026 09:01:45 +0200", "plain text"),
    ]
)


def test_xataka_parses_fixture_feed(monkeypatch):
    monkeypatch.setattr(xataka_etl.requests, "get", lambda *a, **kw: _BytesResponse(XATAKA_FEED))
    entries = xataka_etl.fetch_xataka()
    assert len(entries) == 2
    first = entries[0]
    assert first["title"] == "Anthropic lanza Fable 5.1"
    assert first["link"] == "https://www.xataka.com/robotica-e-ia/anthropic-lanza-fable-5-1"
    assert first["published"] == "2026-09-02T09:14:30+02:00"  # RSS date with CET offset -> ISO
    assert first["source"] == "xataka" and first["source_category"] == "tech_media_es"
    assert first["language"] == "es" and first["region"] == "es"
    assert "<" not in first["summary"] and "Fable" in first["summary"]  # HTML (leading <img>) stripped


def test_xataka_caps_items_at_25(monkeypatch):
    feed = _rss([_item(f"historia {i}", f"https://www.xataka.com/h/{i}", "Wed, 02 Sep 2026 09:14:30 +0200") for i in range(30)])
    monkeypatch.setattr(xataka_etl.requests, "get", lambda *a, **kw: _BytesResponse(feed))
    assert len(xataka_etl.fetch_xataka()) == xataka_etl.MAX_ITEMS == 25


def test_xataka_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(xataka_etl.requests, "get", _boom)
    assert xataka_etl.fetch_xataka() == []


def test_xataka_save_keeps_last_good_on_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(xataka_etl, "get_project_root", lambda: str(tmp_path))
    good = [{"title": "t", "link": "https://x/1", "published": "2026-09-02T09:14:30+02:00", "source": "xataka"}]
    xataka_etl.save_xataka_entries(good)
    latest_path = tmp_path / "data" / "news" / "xataka_latest.json"
    xataka_etl.save_xataka_entries([])
    assert json.loads(latest_path.read_text(encoding="utf-8")) == good
