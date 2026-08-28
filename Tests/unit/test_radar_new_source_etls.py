"""Unit tests for the T-070 Tech Radar source ETLs: Phoronix, Unraid forums,
and the hardened Lobsters fetch.

All feeds are exercised through fixture XML + monkeypatched ``requests.get``
— no network in unit tests.
"""

import json

import requests

from src.etl.news import news_get_lobsters as lobsters_etl
from src.etl.news import news_get_phoronix as phoronix_etl
from src.etl.news import news_get_unraid_forums as unraid_etl


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


def test_unraid_uses_discovered_invision_url():
    assert unraid_etl.RSS_FEED == "https://forums.unraid.net/rss/1-all-unraid-topics.xml/"


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
