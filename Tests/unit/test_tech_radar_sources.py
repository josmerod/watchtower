"""Unit tests for the spec-13 Tech Radar additions.

Covers the HN front-page ETL normalization, the radar tab's multi-file
community-pulse merging/dedup, date-desc sorting, and the reddit RSS
atom-date parsing fix.
"""

import json

import pytest

from src.etl.news import news_get_hn_frontpage as hn_etl
from src.web.dashboard.components import tech_radar_tab as tab

# ---------------------------------------------------------------------------
# HN front-page ETL (Algolia)
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_hn_normalization_prefers_article_url(monkeypatch):
    hit = {
        "objectID": "49345263",
        "title": "The Amazon tax",
        "url": "https://seths.blog/2026/08/the-amazon-tax/",
        "points": 1274,
        "num_comments": 649,
        "author": "herbertl",
        "created_at": "2026-08-18T13:22:38Z",
    }
    monkeypatch.setattr(hn_etl.requests, "get", lambda *a, **kw: _FakeResponse({"hits": [hit]}))
    entries = hn_etl.fetch_hn_frontpage()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["link"] == hit["url"]
    assert entry["hn_link"] == "https://news.ycombinator.com/item?id=49345263"
    assert "1274 points" in entry["summary"] and "649 comments" in entry["summary"]
    assert entry["published"] == hit["created_at"]


def test_hn_normalization_falls_back_to_hn_discussion_link(monkeypatch):
    hit = {"objectID": "42", "title": "Ask HN: no url", "points": 5, "num_comments": 1, "author": "a", "created_at": "2026-08-19T00:00:00Z"}
    monkeypatch.setattr(hn_etl.requests, "get", lambda *a, **kw: _FakeResponse({"hits": [hit]}))
    entry = hn_etl.fetch_hn_frontpage()[0]
    assert entry["link"] == "https://news.ycombinator.com/item?id=42"


# ---------------------------------------------------------------------------
# Radar tab: multi-file sources, dedup, sorting, normalization
# ---------------------------------------------------------------------------

def _write(tmp_path, rel, articles):
    target = tmp_path / "data" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(articles), encoding="utf-8")


def test_pulse_source_merges_and_dedups(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))  # isolate from other tests' cached loads
    _write(tmp_path, "reddit_unified/SelfHosted_latest.json", [{"title": "a", "url": "https://x/1"}, {"title": "dup", "url": "https://x/2"}])
    _write(tmp_path, "reddit_unified/homelab_latest.json", [{"title": "dup-homelab", "url": "https://x/2"}, {"title": "b", "url": "https://x/3"}])
    source = {"key": "pulse", "label": "pulse", "files": ["reddit_unified/SelfHosted_latest.json", "reddit_unified/homelab_latest.json"]}
    merged = tab._load_source_data(source)
    assert len(merged) == 3  # https://x/2 appears in both feeds, kept once


def test_sortable_date_orders_newest_first_undated_last():
    articles = [
        {"title": "old", "published": "2026-08-01T00:00:00+00:00"},
        {"title": "new", "published": "2026-08-19T10:00:00+00:00"},
        {"title": "rss", "published": "Tue, 18 Aug 2026 12:00:00 +0000"},
        {"title": "nodate"},
    ]
    articles.sort(key=tab._sortable_date, reverse=True)
    assert [a["title"] for a in articles] == ["new", "rss", "old", "nodate"]


def test_normalize_synthesizes_and_strips_summary():
    reddit_post = {"title": "t", "url": "u", "score": 42, "num_comments": 7, "subreddit": "SelfHosted", "summary": '<div>hello <b>world</b></div>'}
    normalized = tab._normalize_article(reddit_post)
    assert normalized["summary"] == "hello world"
    assert normalized["link"] == "u"

    json_post = {"title": "t2", "url": "u2", "score": 10, "num_comments": 1, "subreddit": "homelab"}
    assert "⬆ 10" in tab._normalize_article(json_post)["summary"]

    kdnuggets = {"title": "t3", "metadata": {"summary": "s3"}, "published_at": "2026-08-18"}
    flat = tab._normalize_article(kdnuggets)
    assert flat["summary"] == "s3" and flat["published"] == "2026-08-18"


def test_radar_cache_force_refresh_rereads_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "v1"}])
    first = tab._load_all_source_data()
    assert first["news/hn_frontpage_latest.json"][0]["title"] == "v1"
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "v2"}])
    assert tab._load_all_source_data()["news/hn_frontpage_latest.json"][0]["title"] == "v1"  # TTL hit
    assert tab._load_all_source_data(force_refresh=True)["news/hn_frontpage_latest.json"][0]["title"] == "v2"


# ---------------------------------------------------------------------------
# reddit_unified: atom <updated> date parsing + per-subreddit latest files
# ---------------------------------------------------------------------------

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Quarter 2 Update</title>
    <link href="https://www.reddit.com/r/SelfHosted/comments/1/quarter_2/"/>
    <updated>2026-08-19T10:00:00+00:00</updated>
    <author><name>modteam</name></author>
    <content type="html">&lt;div&gt;body&lt;/div&gt;</content>
  </entry>
</feed>
"""


def test_reddit_rss_parses_atom_updated_date(monkeypatch):
    from src.etl.news.reddit_unified_etl import fetch_subreddit_rss

    class _BytesResponse:
        def raise_for_status(self):
            return None

        content = ATOM_FEED.encode()

    monkeypatch.setattr("src.etl.news.reddit_unified_etl.requests.get", lambda *a, **kw: _BytesResponse())
    posts = fetch_subreddit_rss("SelfHosted")
    assert len(posts) == 1
    assert posts[0]["published"].startswith("2026-08-19T10:00:00")


@pytest.mark.parametrize("subreddit", ["SelfHosted", "homelab"])
def test_pulse_subreddits_configured(subreddit):
    from src.etl.news.reddit_unified_etl import SUBREDDITS_CONFIG

    assert subreddit in SUBREDDITS_CONFIG
    if subreddit == "SelfHosted":
        assert SUBREDDITS_CONFIG[subreddit]["category"] == "selfhosting"


# ---------------------------------------------------------------------------
# TR-F3: unified feed (T-041)
# ---------------------------------------------------------------------------

def test_unified_feed_merges_and_orders_chronologically(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "old hn", "url": "https://x/1", "published": "2026-08-20T10:00:00+00:00"}])
    _write(tmp_path, "news/verge_ai_latest.json", [{"title": "new verge", "url": "https://x/2", "published": "2026-08-27T09:00:00+00:00"}])
    feed = str(tab._render_unified_feed())
    assert "old hn" in feed and "new verge" in feed
    assert feed.index("new verge") < feed.index("old hn")  # newest first


def test_unified_feed_filters_by_source_and_category(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "hn item", "url": "https://x/1", "published": "2026-08-27T10:00:00+00:00"}])
    _write(tmp_path, "news/verge_ai_latest.json", [{"title": "verge item", "url": "https://x/2", "published": "2026-08-27T09:00:00+00:00"}])
    only_hn = str(tab._render_unified_feed(source_filter="hn_frontpage"))
    assert "hn item" in only_hn and "verge item" not in only_hn
    hn_source = next(s for s in tab.RADAR_SOURCES if s["key"] == "hn_frontpage")
    only_discussion = str(tab._render_unified_feed(category_filter=hn_source["category"]))
    assert "hn item" in only_discussion and "verge item" not in only_discussion


def test_unified_feed_search_term_and_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "kubernetes rocks", "url": "https://x/1"}, {"title": "unrelated", "url": "https://x/2"}])
    searched = str(tab._render_unified_feed(search_term="kubernetes"))
    # highlight_segments splits the title around the match — check both halves
    assert "kubernetes" in searched and "rocks" in searched and "unrelated" not in searched
    monkeypatch.setattr(tab, "MAX_UNIFIED_ITEMS", 1)
    capped = str(tab._render_unified_feed())
    assert "mostrados" in capped and "1 mostrados" in capped


def test_unified_category_options_distinct():
    options = tab._unified_category_options()
    values = [o["value"] for o in options]
    assert len(values) == len(set(values)) and "AI" in values
