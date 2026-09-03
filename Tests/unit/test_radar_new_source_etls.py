"""Unit tests for the T-070/T-078/T-082 Tech Radar source ETLs: Phoronix,
Unraid forums, the hardened Lobsters fetch, the T-078 additions (GitHub
Trending HTML, ServeTheHome RSS, Xataka RSS) and the T-082 additions (Lemmy
merged community feeds, Product Hunt radar Atom, Azure blog RSS).

All feeds are exercised through fixture XML/HTML + monkeypatched
``requests.get`` — no network in unit tests.
"""

import json

import feedparser
import requests

from src.etl.github import github_trending_etl as trending_etl
from src.etl.news import news_get_azure_blog as azure_etl
from src.etl.news import news_get_lemmy as lemmy_etl
from src.etl.news import news_get_lobsters as lobsters_etl
from src.etl.news import news_get_phoronix as phoronix_etl
from src.etl.news import news_get_producthunt_radar as ph_etl
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


# ---------------------------------------------------------------------------
# T-082: Lemmy communities (merged lemmy.world RSS feeds)
# ---------------------------------------------------------------------------


def _lemmy_item(title: str, link: str, pub: str, description: str = "submitted by &lt;a href='https://lemmy.world/u/u'&gt;u&lt;/a&gt; to &lt;a href='https://lemmy.world/c/c'&gt;c&lt;/a&gt;") -> str:
    """One Lemmy RSS <item> with the community's HTML description."""
    return f"<item><title>{title}</title><link>{link}</link><guid>{link}</guid><pubDate>{pub}</pubDate><description>{description}</description></item>"


LEMMY_SELFHOSTED_FEED = _rss(
    [
        _lemmy_item(
            "What do you selfhost in 2026?",
            "https://lemmy.world/post/60585",
            "Sun, 11 Jun 2023 18:55:57 +0000",  # pinned welcome post (old)
            'submitted by &lt;a href="https://lemmy.world/u/devve"&gt;devve&lt;/a&gt; to &lt;a href="https://lemmy.world/c/selfhosted"&gt;selfhosted&lt;/a&gt;&lt;br /&gt;519 points | &lt;a href="https://lemmy.world/post/60585"&gt;42 comments&lt;/a&gt;',
        ),
        _lemmy_item(
            "Migrating from Docker to Podman",
            "https://lemmy.world/post/61000",
            "Wed, 02 Sep 2026 09:00:00 +0000",
            'submitted by &lt;a href="https://lemmy.world/u/ada"&gt;ada&lt;/a&gt; to &lt;a href="https://lemmy.world/c/selfhosted"&gt;selfhosted&lt;/a&gt;&lt;br /&gt;87 points | &lt;a href="https://lemmy.world/post/61000"&gt;13 comments&lt;/a&gt;',
        ),
    ]
)

LEMMY_HOMELAB_FEED = _rss(
    [
        _lemmy_item(
            "Proxmox 9.2 launches with the 7.0 kernel",
            "https://lemmy.world/post/47207771",
            "Fri, 22 May 2026 14:31:57 +0000",
            'submitted by &lt;a href="https://lemmy.world/u/kim"&gt;kim&lt;/a&gt; to &lt;a href="https://lemmy.world/c/homelab"&gt;homelab&lt;/a&gt;&lt;br /&gt;312 points | &lt;a href="https://lemmy.world/post/47207771"&gt;77 comments&lt;/a&gt;',
        ),
        _lemmy_item(
            "Migrating from Docker to Podman",  # cross-post: same link, deduped at merge
            "https://lemmy.world/post/61000",
            "Wed, 02 Sep 2026 09:00:00 +0000",
            'submitted by &lt;a href="https://lemmy.world/u/ada"&gt;ada&lt;/a&gt; to &lt;a href="https://lemmy.world/c/homelab"&gt;homelab&lt;/a&gt;&lt;br /&gt;no counters here',
        ),
    ]
)


def _lemmy_get(monkeypatch, selfhosted=None, homelab=None):
    """Monkeypatch requests.get to serve per-community Lemmy fixtures (or exceptions)."""

    def _get(url, *args, **kwargs):
        if "selfhosted" in url:
            if isinstance(selfhosted, Exception):
                raise selfhosted
            return _BytesResponse(selfhosted if selfhosted is not None else LEMMY_SELFHOSTED_FEED)
        if isinstance(homelab, Exception):
            raise homelab
        return _BytesResponse(homelab if homelab is not None else LEMMY_HOMELAB_FEED)

    monkeypatch.setattr(lemmy_etl.requests, "get", _get)


def test_lemmy_merges_dedups_and_sorts_both_communities(monkeypatch):
    _lemmy_get(monkeypatch)
    entries = lemmy_etl.fetch_lemmy()
    assert len(entries) == 3  # 2 + 2 feed items, one cross-posted link kept once
    links = [e["link"] for e in entries]
    assert len(links) == len(set(links))
    assert entries[0]["title"] == "Migrating from Docker to Podman"  # newest first…
    assert entries[0]["published"] == "2026-09-02T09:00:00+00:00"
    assert entries[-1]["title"] == "What do you selfhost in 2026?"  # …pinned 2023 post last
    communities = {e["community"] for e in entries}
    assert communities == {"selfhosted", "homelab"}


def test_lemmy_summary_extracts_engagement_counters(monkeypatch):
    _lemmy_get(monkeypatch)
    entries = {e["title"]: e for e in lemmy_etl.fetch_lemmy()}
    assert entries["What do you selfhost in 2026?"]["summary"] == "⬆ 519 · 💬 42 · !selfhosted@lemmy.world"
    assert entries["Proxmox 9.2 launches with the 7.0 kernel"]["summary"] == "⬆ 312 · 💬 77 · !homelab@lemmy.world"
    assert "<" not in entries["Proxmox 9.2 launches with the 7.0 kernel"]["summary"]  # HTML stripped
    assert entries["Migrating from Docker to Podman"]["source"] == "lemmy" and entries["Migrating from Docker to Podman"]["source_category"] == "self_hosting"
    assert entries["Migrating from Docker to Podman"]["platform"] == "lemmy.world" and entries["Migrating from Docker to Podman"]["content_type"] == "forum_post"


def test_lemmy_caps_per_feed_then_merged(monkeypatch):
    # 30 items per feed: per-feed cap keeps 25 each, merged cap keeps the newest 30.
    # Each feed is newest-first (minutes descending); homelab runs at hour 10,
    # so every homelab item is newer than every selfhosted item.
    def feed(community: str, hour: int) -> bytes:
        items = [_lemmy_item(f"{community} story {i}", f"https://lemmy.world/post/{community}{i}", f"Wed, 02 Sep 2026 {hour:02d}:{59 - i:02d}:00 +0000") for i in range(30)]
        return _rss(items)

    _lemmy_get(monkeypatch, selfhosted=feed("selfhosted", 9), homelab=feed("homelab", 10))
    entries = lemmy_etl.fetch_lemmy()
    assert len(entries) == lemmy_etl.MAX_ITEMS == 30
    titles = [e["title"] for e in entries]
    assert sum(t.startswith("homelab") for t in titles) == 25  # per-feed cap applied
    assert sum(t.startswith("selfhosted") for t in titles) == 5
    assert "selfhosted story 5" not in titles  # oldest beyond the merged cap dropped


def test_lemmy_one_feed_failing_still_returns_the_other(monkeypatch):
    _lemmy_get(monkeypatch, homelab=requests.ConnectionError("homelab feed down"))
    entries = lemmy_etl.fetch_lemmy()
    assert len(entries) == 2 and all(e["community"] == "selfhosted" for e in entries)


def test_lemmy_fetch_failure_returns_empty(monkeypatch):
    _lemmy_get(monkeypatch, selfhosted=requests.ConnectionError("network down"), homelab=requests.ConnectionError("network down"))
    assert lemmy_etl.fetch_lemmy() == []


def test_lemmy_save_keeps_last_good_on_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(lemmy_etl, "get_project_root", lambda: str(tmp_path))
    good = [{"title": "t", "link": "https://lemmy.world/post/1", "published": "2026-09-02T09:00:00+00:00", "source": "lemmy"}]
    lemmy_etl.save_lemmy_entries(good)
    latest_path = tmp_path / "data" / "news" / "lemmy_latest.json"
    snapshots = [p for p in (tmp_path / "data" / "news").glob("lemmy_*.json") if p.name != "lemmy_latest.json"]
    assert len(snapshots) == 1
    lemmy_etl.save_lemmy_entries([])  # empty run skips saving…
    assert json.loads(latest_path.read_text(encoding="utf-8")) == good  # …last-good kept


# ---------------------------------------------------------------------------
# T-082: Product Hunt radar feed (keyless front-page Atom, Wired pattern)
# ---------------------------------------------------------------------------

PH_FEED = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n'
    b"  <title>Product Hunt</title>\n"
    b"  <entry>\n"
    b"    <title>Agent Builder by Airtop</title>\n"
    b'    <link href="https://www.producthunt.com/products/airtop"/>\n'
    b"    <id>tag:www.producthunt.com,2005:Post/1232031</id>\n"
    b"    <published>2026-08-25T07:48:06-07:00</published>\n"
    b"    <updated>2026-09-03T05:59:34-07:00</updated>\n"
    b"    <author><name>Ben Lang</name></author>\n"
    b'    <category term="Developer Tools"/>\n'
    b'    <summary type="html">&lt;p&gt;Build agents that heal themselves.&lt;/p&gt;&lt;p&gt;&lt;a href="https://www.producthunt.com/products/airtop"&gt;Check it out&lt;/a&gt;&lt;/p&gt;</summary>\n'
    b"  </entry>\n"
    b"  <entry>\n"
    b"    <title>OpenClaude</title>\n"
    b'    <link href="https://www.producthunt.com/products/openclaude"/>\n'
    b"    <id>tag:www.producthunt.com,2005:Post/1232032</id>\n"
    b"    <published>2026-08-24T07:00:00-07:00</published>\n"
    b"    <updated>2026-08-24T07:00:00-07:00</updated>\n"
    b"    <author><name>Maker</name></author>\n"
    b'    <summary type="html">&lt;p&gt;Self-hosted LLM gateway.&lt;/p&gt;&lt;p&gt;Discussion | Link&lt;/p&gt;</summary>\n'
    b"  </entry>\n"
    b"</feed>\n"
)


def test_ph_parses_fixture_atom_feed(monkeypatch):
    monkeypatch.setattr(ph_etl.requests, "get", lambda *a, **kw: _BytesResponse(PH_FEED))
    entries = ph_etl.fetch_producthunt()
    assert len(entries) == 2
    first = entries[0]
    assert first["title"] == "Agent Builder by Airtop"
    assert first["link"] == "https://www.producthunt.com/products/airtop"
    assert first["published"] == "2026-08-25T07:48:06-07:00"  # atom ISO date kept
    assert first["summary"] == "Build agents that heal themselves."  # promo link dropped, HTML stripped
    assert first["author"] == "Ben Lang"
    assert first["categories"] == ["Developer Tools"]
    assert first["source"] == "producthunt" and first["source_category"] == "products"
    assert first["platform"] == "product_hunt" and first["content_type"] == "product_launch"
    assert entries[1]["summary"] == "Self-hosted LLM gateway."  # "Discussion | Link" promo footer dropped too


def test_ph_caps_items_at_25(monkeypatch):
    entries_xml = "".join(
        f'  <entry><title>launch {i}</title><link href="https://www.producthunt.com/products/p{i}"/><id>tag:x,{i}</id>'
        f"<published>2026-09-0{i % 9 + 1}T07:00:00-07:00</published><summary type='html'>&lt;p&gt;tagline&lt;/p&gt;</summary></entry>\n"
        for i in range(30)
    )
    feed = f'<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n{entries_xml}</feed>\n'.encode()
    monkeypatch.setattr(ph_etl.requests, "get", lambda *a, **kw: _BytesResponse(feed))
    entries = ph_etl.fetch_producthunt()
    assert len(entries) == ph_etl.MAX_ITEMS == 25
    assert entries[0]["title"] == "launch 0"  # feed order kept


def test_ph_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(ph_etl.requests, "get", _boom)
    assert ph_etl.fetch_producthunt() == []


def test_ph_save_writes_latest_and_keeps_last_good(tmp_path, monkeypatch):
    monkeypatch.setattr(ph_etl, "get_project_root", lambda: str(tmp_path))
    good = [{"title": "t", "link": "https://www.producthunt.com/products/x", "published": "2026-08-25T07:48:06-07:00", "source": "producthunt"}]
    ph_etl.save_producthunt_entries(good)
    data_dir = tmp_path / "data" / "news"
    assert json.loads((data_dir / "producthunt_radar_latest.json").read_text(encoding="utf-8")) == good
    snapshots = [p for p in data_dir.glob("producthunt_radar_*.json") if p.name != "producthunt_radar_latest.json"]
    assert len(snapshots) == 1
    ph_etl.save_producthunt_entries([])  # empty run skips saving…
    assert json.loads((data_dir / "producthunt_radar_latest.json").read_text(encoding="utf-8")) == good  # …last-good kept


# ---------------------------------------------------------------------------
# T-082: Azure blog (RSS, Wired pattern)
# ---------------------------------------------------------------------------


def _azure_item(title: str, link: str, pub: str, description: str, category: str) -> str:
    """One Azure blog RSS <item> with topic category and canonical-feed summary."""
    return f"<item><title>{title}</title><link>{link}</link><category>{category}</category><pubDate>{pub}</pubDate><description>{description}</description></item>"


AZURE_FEED = _rss(
    [
        _azure_item(
            "Managed PostgreSQL vs. self-hosted PostgreSQL",
            "https://azure.microsoft.com/en-us/blog/managed-postgresql-vs-self-hosted/",
            "Thu, 27 Aug 2026 17:00:00 +0000",
            "&lt;p&gt;Compare cost, control and operations.&lt;/p&gt;&lt;p&gt;The post &lt;a href='x'&gt;Managed PostgreSQL&lt;/a&gt; appeared first in &lt;a href='y'&gt;Microsoft Azure Blog&lt;/a&gt;.&lt;/p&gt;",
            "Databases",
        ),
        _azure_item("Azure Arc-enabled data services GA", "https://azure.microsoft.com/en-us/blog/azure-arc-ga/", "Tue, 25 Aug 2026 15:00:00 +0000", "plain text summary", "Hybrid + multicloud"),
    ]
)


def test_azure_parses_fixture_feed(monkeypatch):
    monkeypatch.setattr(azure_etl.requests, "get", lambda *a, **kw: _BytesResponse(AZURE_FEED))
    entries = azure_etl.fetch_azure_blog()
    assert len(entries) == 2
    first = entries[0]
    assert first["title"] == "Managed PostgreSQL vs. self-hosted PostgreSQL"
    assert first["link"].startswith("https://azure.microsoft.com/en-us/blog/")
    assert first["published"] == "2026-08-27T17:00:00+00:00"
    assert first["summary"] == "Compare cost, control and operations."  # trailer + HTML stripped
    assert first["categories"] == ["Databases"]
    assert first["source"] == "azure_blog" and first["source_category"] == "cloud"
    assert first["platform"] == "azure.microsoft.com" and first["content_type"] == "news_article"


def test_azure_fetch_failure_returns_empty(monkeypatch):
    def _boom(*a, **kw):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(azure_etl.requests, "get", _boom)
    assert azure_etl.fetch_azure_blog() == []


def test_azure_save_writes_latest_and_keeps_last_good(tmp_path, monkeypatch):
    monkeypatch.setattr(azure_etl, "get_project_root", lambda: str(tmp_path))
    good = [{"title": "t", "link": "https://azure.microsoft.com/en-us/blog/t/", "published": "2026-08-27T17:00:00+00:00", "source": "azure_blog"}]
    azure_etl.save_azure_blog_entries(good)
    data_dir = tmp_path / "data" / "news"
    assert json.loads((data_dir / "azure_blog_latest.json").read_text(encoding="utf-8")) == good
    snapshots = [p for p in data_dir.glob("azure_blog_*.json") if p.name != "azure_blog_latest.json"]
    assert len(snapshots) == 1
    azure_etl.save_azure_blog_entries([])  # empty run skips saving…
    assert json.loads((data_dir / "azure_blog_latest.json").read_text(encoding="utf-8")) == good  # …last-good kept
