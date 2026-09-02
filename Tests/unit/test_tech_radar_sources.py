"""Unit tests for the spec-13 Tech Radar additions.

Covers the HN front-page ETL normalization, the radar tab's multi-file
community-pulse merging/dedup, date-desc sorting, the reddit RSS
atom-date parsing fix, and the T-051 "Mi stack" GitHub releases ETL +
subtab (TR-F4).
"""

import json

import pytest

from src.etl.github import stack_releases_etl as stack_etl
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
    reddit_post = {"title": "t", "url": "u", "score": 42, "num_comments": 7, "subreddit": "SelfHosted", "summary": "<div>hello <b>world</b></div>"}
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


# ---------------------------------------------------------------------------
# T-051 TR-F4: "Mi stack" GitHub releases ETL + subtab
# ---------------------------------------------------------------------------

_IMMICH_CFG = {"owner": "immich-app", "repo": "immich", "max_releases": 5}
_N8N_CFG = {"owner": "n8n-io", "repo": "n8n", "max_releases": 5}


def _release_entry(owner: str, repo: str, tag: str, updated: str, notes_html: str = "<p>Initial stable release.</p>") -> str:
    """One releases.atom <entry> with XML-escaped HTML release notes."""
    escaped = notes_html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "  <entry>\n"
        f"    <title>{tag}</title>\n"
        f'    <link href="https://github.com/{owner}/{repo}/releases/tag/{tag}"/>\n'
        "    <id>tag:github.com,2008:repository/1234</id>\n"
        f"    <updated>{updated}</updated>\n"
        f'    <content type="html">{escaped}</content>\n'
        "  </entry>\n"
    )


def _stack_atom(entries_xml: str) -> bytes:
    """Wrap entry XML into a minimal GitHub-style atom feed body."""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n' + entries_xml + "</feed>\n").encode()


def test_stack_repos_configured():
    repos = {f"{cfg['owner']}/{cfg['repo']}" for cfg in stack_etl.STACK_REPOS}
    assert {"n8n-io/n8n", "home-assistant/core", "immich-app/immich", "jellyfin/jellyfin", "JustArchiNET/ArchiSteamFarm", "HaveAGitGat/Tdarr"} == repos
    # HA core releases almost daily (incl. betas) — it must carry a tighter cap.
    ha = next(cfg for cfg in stack_etl.STACK_REPOS if cfg["repo"] == "core")
    assert ha["max_releases"] < stack_etl.DEFAULT_MAX_RELEASES


def test_stack_etl_parses_atom_releases():
    feed = _stack_atom(
        _release_entry(
            "immich-app",
            "immich",
            "v3.1.0",
            "2026-08-27T20:37:47Z",
            '<h2><a href="https://github.com/immich-app/immich/compare/v3.0.0...v3.1.0">v3.1.0</a> (2026-08-27)</h2> <ul><li>Fix **thumbnail** generation.</li></ul>',
        )
        + _release_entry("immich-app", "immich", "v3.0.0", "2026-07-29T14:26:17Z")
    )
    releases = stack_etl.parse_repo_releases(feed, _IMMICH_CFG)
    assert len(releases) == 2
    first = releases[0]
    assert first["repo"] == "immich" and first["owner"] == "immich-app"
    assert first["tag"] == "v3.1.0" and first["version"] == "3.1.0"
    assert first["title"] == "v3.1.0"
    assert first["link"] == "https://github.com/immich-app/immich/releases/tag/v3.1.0"
    assert first["published"] == "2026-08-27T20:37:47+00:00"  # atom updated_parsed -> ISO UTC
    assert first["summary"] == "v3.1.0 (2026-08-27) Fix thumbnail generation."  # HTML + markdown stripped, first sentence
    assert first["source_category"] == "mi_stack"


def test_stack_etl_summary_strips_markup_and_caps_length():
    markup = "<h2><a href='x'>2.37.3</a> (2026-08-27)</h2> <ul><li>Fix **login** &amp; session bug. Second sentence.</li></ul>"
    assert stack_etl._summarize(markup) == "2.37.3 (2026-08-27) Fix login & session bug."
    assert stack_etl._summarize("") == ""
    wall = "no sentence ends here " * 30
    capped = stack_etl._summarize(f"<p>{wall}</p>")
    assert len(capped) <= stack_etl.SUMMARY_MAX_CHARS and capped.endswith("…")


def test_stack_etl_per_repo_cap():
    # GitHub atom feeds list releases newest-first; the cap keeps the first N.
    entries = "".join(_release_entry("immich-app", "immich", f"v1.{i}.0", f"2026-08-{i:02d}T10:00:00Z") for i in range(7, 0, -1))
    feed = _stack_atom(entries)
    assert [r["tag"] for r in stack_etl.parse_repo_releases(feed, _IMMICH_CFG)] == ["v1.7.0", "v1.6.0", "v1.5.0", "v1.4.0", "v1.3.0"]  # default cap 5, feed order kept
    tight = dict(_IMMICH_CFG, max_releases=3)
    assert len(stack_etl.parse_repo_releases(feed, tight)) == 3


def test_stack_etl_tag_from_percent_encoded_link():
    assert stack_etl._tag_from_link("https://github.com/n8n-io/n8n/releases/tag/n8n%402.37.3") == "n8n@2.37.3"
    assert stack_etl._tag_from_link("https://github.com/n8n-io/n8n") == ""
    assert stack_etl._version_from_tag("n8n@2.37.3") == "2.37.3"  # scoped tag -> bare version
    assert stack_etl._version_from_tag("v3.1.0") == "3.1.0" and stack_etl._version_from_tag("beta") == "beta"


def test_stack_etl_save_writes_latest_and_run_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(stack_etl, "get_project_root", lambda: str(tmp_path))
    releases = [
        {"repo": "immich", "owner": "immich-app", "tag": "v3.1.0", "version": "3.1.0", "title": "v3.1.0", "link": "https://x/1", "published": "2026-08-27T20:37:47+00:00", "summary": "s"},
        {"repo": "n8n", "owner": "n8n-io", "tag": "n8n@2.37.3", "version": "2.37.3", "title": "n8n@2.37.3", "link": "https://x/2", "published": "2026-08-25T13:03:52+00:00", "summary": "s"},
    ]
    stats = {"repos_total": 6, "repos_ok": 6, "releases_per_repo": {"immich": 1, "n8n": 1}}
    assert stack_etl.save_stack_releases(releases, stats) is True

    data_dir = tmp_path / "data" / "github"
    latest = json.loads((data_dir / "stack_releases_latest.json").read_text(encoding="utf-8"))
    assert isinstance(latest, list) and len(latest) == 2  # the tab reads files that are plain lists
    snapshots = [p for p in data_dir.glob("stack_releases_*.json") if p.name != "stack_releases_latest.json"]
    assert len(snapshots) == 1
    summary = json.loads((data_dir / "run_summary_latest.json").read_text(encoding="utf-8"))
    assert summary["etl_name"] == "stack_releases" and summary["success"] is True
    assert summary["records_loaded"] == 2 and summary["repos_ok"] == 6 and "releases_per_repo" in summary


def test_stack_etl_save_keeps_last_good_on_empty_or_partial_run(tmp_path, monkeypatch):
    monkeypatch.setattr(stack_etl, "get_project_root", lambda: str(tmp_path))
    good = [{"repo": "n8n", "title": "LAST-GOOD"}]
    assert stack_etl.save_stack_releases(good, {"repos_total": 6, "repos_ok": 6, "releases_per_repo": {}}) is True
    latest_path = tmp_path / "data" / "github" / "stack_releases_latest.json"

    assert stack_etl.save_stack_releases([], {"repos_total": 6, "repos_ok": 0, "releases_per_repo": {}}) is False
    assert stack_etl.save_stack_releases(good, {"repos_total": 6, "repos_ok": 1, "releases_per_repo": {}}) is False  # 1/6 repos < majority
    assert json.loads(latest_path.read_text(encoding="utf-8")) == good  # last-good untouched

    assert stack_etl.save_stack_releases(good, {"repos_total": 6, "repos_ok": 3, "releases_per_repo": {}}) is True  # majority writes
    assert json.loads(latest_path.read_text(encoding="utf-8")) == good


def _write_stack_fixture(tmp_path):
    _write(
        tmp_path,
        "github/stack_releases_latest.json",
        [
            {"repo": "n8n", "owner": "n8n-io", "title": "n8n@2.37.3", "link": "https://github.com/n8n-io/n8n/releases/tag/n8n@2.37.3", "published": "2026-08-25T13:03:52+00:00", "summary": "Bug fixes."},
            {"repo": "immich", "owner": "immich-app", "title": "v3.2.0-rc.1", "link": "https://x/immich", "published": "2026-08-27T20:37:47+00:00", "summary": "chore: version v3.2.0-rc.1"},
        ],
    )


def test_stack_tab_label_and_single_column():
    layout = str(tab.render_tech_radar_tab())
    assert "🧮 Mi stack" in layout and "tech-radar-tab-stack" in layout
    assert layout.count("tech-radar-col-mi_stack") == 1  # column lives on the Mi stack tab only, id stays unique


def test_stack_section_renders_release_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_stack_fixture(tmp_path)
    source = next(s for s in tab.RADAR_SOURCES if s["key"] == "mi_stack")
    section = str(tab._render_source_section(source))
    assert "Mi stack" in section and "release" in section
    assert section.index("v3.2.0-rc.1") < section.index("n8n@2.37.3")  # newest first
    assert "immich" in section and "n8n" in section  # repo badge per row


def test_unified_feed_includes_stack_items_with_repo_badge(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_stack_fixture(tmp_path)
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "hn item", "url": "https://x/hn", "published": "2026-08-26T10:00:00+00:00"}])

    merged = str(tab._render_unified_feed())
    assert "v3.2.0-rc.1" in merged and "n8n@2.37.3" in merged and "immich" in merged  # repo badge shows in the merged feed

    only_stack = str(tab._render_unified_feed(source_filter="mi_stack"))
    assert "n8n@2.37.3" in only_stack and "hn item" not in only_stack
    stack_category = str(tab._render_unified_feed(category_filter="Mi Stack"))
    assert "v3.2.0-rc.1" in stack_category and "hn item" not in stack_category


def test_unified_dropdown_options_include_stack():
    assert "mi_stack" in [o["value"] for o in tab._unified_source_options()]
    assert "Mi Stack" in [o["value"] for o in tab._unified_category_options()]


# ---------------------------------------------------------------------------
# T-070: Lobsters / Phoronix / Unraid-forums radar sources
# ---------------------------------------------------------------------------

_T070_SOURCES = {"lobsters", "phoronix", "unraid_forums"}


def test_t070_sources_registered_with_unique_keys_and_columns():
    keys = [s["key"] for s in tab.RADAR_SOURCES]
    assert len(keys) == len(set(keys)), "RADAR_SOURCES keys must stay unique"
    assert set(keys) >= _T070_SOURCES
    layout = str(tab.render_tech_radar_tab())
    for key in _T070_SOURCES:
        source = next(s for s in tab.RADAR_SOURCES if s["key"] == key)
        assert source.get("file") and not source.get("files")
        assert not source.get("own_tab"), "new sources render as normal Por-fuente columns"
        assert layout.count(f"tech-radar-col-{key}") == 1  # one column id, in the grid


def _write_t070_fixture(tmp_path):
    _write(tmp_path, "news/lobsters_latest.json", [{"title": "lobsters story", "link": "https://lobste.rs/s/1", "published": "2026-08-27T10:00:00+00:00", "source": "lobsters"}])
    _write(tmp_path, "news/phoronix_latest.json", [{"title": "phoronix story", "link": "https://www.phoronix.com/news/1", "published": "2026-08-26T10:00:00+00:00", "source": "phoronix"}])
    _write(tmp_path, "news/unraid_forums_latest.json", [{"title": "unraid thread", "link": "https://forums.unraid.net/topic/1", "published": "2026-08-25T10:00:00+00:00", "source": "unraid_forums"}])


def test_t070_sources_render_in_por_fuente_grid(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_t070_fixture(tmp_path)
    for key in _T070_SOURCES:
        source = next(s for s in tab.RADAR_SOURCES if s["key"] == key)
        section = str(tab._render_source_section(source))
        assert source["label"] in section
    lobsters_section = str(tab._render_source_section(next(s for s in tab.RADAR_SOURCES if s["key"] == "lobsters")))
    assert "lobsters story" in lobsters_section


def test_t070_sources_in_unified_feed_and_dropdowns(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_t070_fixture(tmp_path)
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "hn item", "url": "https://x/hn", "published": "2026-08-20T10:00:00+00:00"}])

    merged = str(tab._render_unified_feed())
    assert "lobsters story" in merged and "phoronix story" in merged and "unraid thread" in merged
    assert merged.index("lobsters story") < merged.index("hn item")  # newer first

    only_unraid = str(tab._render_unified_feed(source_filter="unraid_forums"))
    assert "unraid thread" in only_unraid and "hn item" not in only_unraid
    linux_hw = str(tab._render_unified_feed(category_filter="Linux/Hardware"))
    assert "phoronix story" in linux_hw and "hn item" not in linux_hw

    options = [o["value"] for o in tab._unified_source_options()]
    assert set(options) >= _T070_SOURCES
    categories = [o["value"] for o in tab._unified_category_options()]
    assert "Linux/Hardware" in categories and len(categories) == len(set(categories))


def test_t070_per_source_render_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write(tmp_path, "news/phoronix_latest.json", [{"title": f"story {i}", "link": f"https://x/{i}", "published": "2026-08-27T10:00:00+00:00"} for i in range(30)])
    source = next(s for s in tab.RADAR_SOURCES if s["key"] == "phoronix")
    section = str(tab._render_source_section(source))
    assert f"{tab.MAX_ITEMS_PER_SOURCE} articles" in section  # capped at render like every sibling
    assert "story 29" not in section


# ---------------------------------------------------------------------------
# T-075: Ollama library ("modelos locales") radar source + Unraid label switch
# ---------------------------------------------------------------------------


def test_t075_ollama_source_registered_with_unique_key_and_column():
    keys = [s["key"] for s in tab.RADAR_SOURCES]
    assert len(keys) == len(set(keys)), "RADAR_SOURCES keys must stay unique"
    assert "ollama" in keys
    source = next(s for s in tab.RADAR_SOURCES if s["key"] == "ollama")
    assert source["file"] == "ai_platforms/ollama_library_latest.json"
    assert source["category"] == "Local LLM"
    assert source.get("file") and not source.get("files")
    assert not source.get("own_tab"), "ollama renders as a normal Por-fuente column"
    layout = str(tab.render_tech_radar_tab())
    assert layout.count("tech-radar-col-ollama") == 1  # one column id, in the grid
    assert "🦙 Ollama" in layout


def _write_t075_fixture(tmp_path):
    _write(
        tmp_path,
        "ai_platforms/ollama_library_latest.json",
        [
            {"title": "qwen3.5", "name": "qwen3.5", "link": "https://ollama.com/library/qwen3.5", "published": "2026-08-27T18:00:00+00:00", "summary": "⬇ 1.2M pulls · 8b", "source": "ollama_library"},
            {"title": "gemma4", "name": "gemma4", "link": "https://ollama.com/library/gemma4", "published": "2026-08-20T09:00:00+00:00", "summary": "⬇ 800K pulls · 12b", "source": "ollama_library"},
        ],
    )


def test_t075_ollama_renders_in_por_fuente_grid(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_t075_fixture(tmp_path)
    source = next(s for s in tab.RADAR_SOURCES if s["key"] == "ollama")
    section = str(tab._render_source_section(source))
    assert source["label"] in section and "qwen3.5" in section
    assert section.index("qwen3.5") < section.index("gemma4")  # newest first


def test_t075_ollama_in_unified_feed_and_dropdowns(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_t075_fixture(tmp_path)
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "hn item", "url": "https://x/hn", "published": "2026-08-26T10:00:00+00:00"}])

    merged = str(tab._render_unified_feed())
    assert "qwen3.5" in merged
    assert merged.index("qwen3.5") < merged.index("hn item")  # newer first

    only_ollama = str(tab._render_unified_feed(source_filter="ollama"))
    assert "qwen3.5" in only_ollama and "hn item" not in only_ollama
    local_llm = str(tab._render_unified_feed(category_filter="Local LLM"))
    assert "gemma4" in local_llm and "hn item" not in local_llm

    assert "ollama" in [o["value"] for o in tab._unified_source_options()]
    categories = [o["value"] for o in tab._unified_category_options()]
    assert "Local LLM" in categories and len(categories) == len(set(categories))


def test_t075_unraid_column_relabeled_to_announcements():
    # The feed switch (news_get_unraid_forums) is surfaced in the tab label.
    source = next(s for s in tab.RADAR_SOURCES if s["key"] == "unraid_forums")
    assert source["label"] == "🟠 Unraid Announcements"
    assert source["file"] == "news/unraid_forums_latest.json"  # data file unchanged
    layout = str(tab.render_tech_radar_tab())
    assert layout.count("tech-radar-col-unraid_forums") == 1


# ---------------------------------------------------------------------------
# T-078: GitHub Trending / ServeTheHome / Xataka radar sources
# ---------------------------------------------------------------------------

_T078_SOURCES = {"github_trending", "servethehome", "xataka"}


def test_t078_sources_registered_with_unique_keys_and_columns():
    keys = [s["key"] for s in tab.RADAR_SOURCES]
    assert len(keys) == len(set(keys)), "RADAR_SOURCES keys must stay unique"
    assert set(keys) >= _T078_SOURCES
    layout = str(tab.render_tech_radar_tab())
    for key in _T078_SOURCES:
        source = next(s for s in tab.RADAR_SOURCES if s["key"] == key)
        assert source.get("file") and not source.get("files")
        assert not source.get("own_tab"), "new sources render as normal Por-fuente columns"
        assert layout.count(f"tech-radar-col-{key}") == 1  # one column id, in the grid
    assert "🐙 GH Trending" in layout and "🔧 ServeTheHome" in layout and "🇪🇸 Xataka" in layout


def _write_t078_fixture(tmp_path):
    _write(
        tmp_path,
        "github/github_trending_latest.json",
        [
            {
                "title": "owner/hot-repo",
                "repo": "owner/hot-repo",
                "link": "https://github.com/owner/hot-repo",
                "published": "2026-09-01T09:00:00+00:00",
                "summary": "⭐ 420 today · Rust · Blazingly fast thing",
                "source": "github_trending",
            }
        ],
    )
    _write(tmp_path, "news/servethehome_latest.json", [{"title": "sth story", "link": "https://www.servethehome.com/sth-story/", "published": "2026-08-31T19:00:56+00:00", "source": "servethehome"}])
    _write(tmp_path, "news/xataka_latest.json", [{"title": "xataka story", "link": "https://www.xataka.com/xataka-story", "published": "2026-08-30T09:14:30+02:00", "source": "xataka"}])


def test_t078_sources_render_in_por_fuente_grid(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_t078_fixture(tmp_path)
    for key in _T078_SOURCES:
        source = next(s for s in tab.RADAR_SOURCES if s["key"] == key)
        section = str(tab._render_source_section(source))
        assert source["label"] in section
    trending_section = str(tab._render_source_section(next(s for s in tab.RADAR_SOURCES if s["key"] == "github_trending")))
    assert "owner/hot-repo" in trending_section and "⭐ 420 today" in trending_section


def test_t078_sources_in_unified_feed_and_dropdowns(tmp_path, monkeypatch):
    monkeypatch.setattr(tab, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(tab, "_RADAR_CACHE", tab.TTLDataCache(ttl_seconds=300))
    _write_t078_fixture(tmp_path)
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "hn item", "url": "https://x/hn", "published": "2026-08-20T10:00:00+00:00"}])

    merged = str(tab._render_unified_feed())
    assert "owner/hot-repo" in merged and "sth story" in merged and "xataka story" in merged
    assert merged.index("owner/hot-repo") < merged.index("hn item")  # newer first

    only_xataka = str(tab._render_unified_feed(source_filter="xataka"))
    assert "xataka story" in only_xataka and "hn item" not in only_xataka
    # ServeTheHome shares Phoronix's Linux/Hardware category (T-078 pairing).
    linux_hw = str(tab._render_unified_feed(category_filter="Linux/Hardware"))
    assert "sth story" in linux_hw and "xataka story" not in linux_hw and "hn item" not in linux_hw
    open_source = str(tab._render_unified_feed(category_filter="Open Source"))
    assert "owner/hot-repo" in open_source and "xataka story" not in open_source

    options = [o["value"] for o in tab._unified_source_options()]
    assert set(options) >= _T078_SOURCES
    categories = [o["value"] for o in tab._unified_category_options()]
    assert "Tech Media ES" in categories and len(categories) == len(set(categories))


def test_t078_unified_cap_bumped_to_fit_new_sources():
    # 120 starved the tail: the three T-078 sources add up to ~55 fresh,
    # mostly-today items that crowd the newest-first window.
    assert tab.MAX_UNIFIED_ITEMS == 140
