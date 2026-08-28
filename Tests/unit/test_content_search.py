"""Hermetic unit tests for the unified content-search index (T-057).

All tests build the index against ``tmp_path`` fixture files — the real
``data/`` dir is never touched.
"""

import json
from pathlib import Path

from src.services.content_search import ContentSearchIndex, build_index


def _write(root: Path, rel_path: str, payload) -> None:
    """Write a JSON payload under the temp data dir."""
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


class FakeClock:
    """Deterministic time seam for TTL tests."""

    def __init__(self) -> None:
        """Start the clock at an arbitrary epoch."""
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the current fake time."""
        return self.now


def _articles(*titles_dates) -> list[dict]:
    """Build minimal article entries from (title, published) tuples."""
    return [{"title": t, "link": f"https://example.com/{i}", "published": d} for i, (t, d) in enumerate(titles_dates)]


def test_kinds_and_normalization(tmp_path: Path):
    """Each collection maps to its kind with normalized fields."""
    _write(tmp_path, "news/techcrunch_latest.json", [{"title": "Some news", "link": "https://tc/1", "published": "2026-08-28T08:00:00Z"}])
    _write(tmp_path, "github/stack_releases_latest.json", [{"title": "n8n@2.36.8", "link": "https://github.com/n8n-io/n8n", "published": "2026-08-28T07:00:00Z"}])
    _write(tmp_path, "markets/coingecko_latest.json", [{"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "fetched_at": "2026-08-28T06:00:00Z"}])
    _write(tmp_path, "arxiv/hf_daily_papers_latest.json", [{"title": "A paper", "link": "https://arxiv/1", "published": "2026-08-28T05:00:00Z"}])
    _write(tmp_path, "youtube/SomeChannel/youtube_videos.json", [{"title": "A video", "url": "https://youtu.be/1", "published_at": "2026-08-28T04:00:00Z", "channel": "SomeChannel"}])
    items = {(i["kind"], i["title"]): i for i in build_index(tmp_path)}
    assert set(items) == {("news", "Some news"), ("release", "n8n@2.36.8"), ("coin", "Bitcoin (BTC)"), ("paper", "A paper"), ("video", "A video")}
    assert items[("coin", "Bitcoin (BTC)")]["url"] == "https://www.coingecko.com/en/coins/bitcoin"
    assert items[("coin", "Bitcoin (BTC)")]["source"] == "CoinGecko"
    assert items[("video", "A video")]["source"] == "SomeChannel"
    assert items[("news", "Some news")]["source"] == "TechCrunch"
    for item in items.values():
        assert set(item) == {"title", "url", "source", "kind", "published", "_epoch"}


def test_ranking_prefix_word_substring_source(tmp_path: Path):
    """Prefix > whole word > substring, source-only last; newest first in a tier."""
    _write(
        tmp_path,
        "news/techcrunch_latest.json",
        _articles(
            ("The tensorflowless debate", "2026-08-28T00:00:00Z"),  # tier 1 (substring only), newest
            ("The tensorflowless classic", "2026-08-20T00:00:00Z"),  # tier 1, older
            ("a tensorflow word match", "2026-08-01T00:00:00Z"),  # tier 2 (whole word)
            ("tensorflow at the start", "2026-08-01T00:00:00Z"),  # tier 3 (prefix)
        ),
    )
    # Source-only match: title has no term, source label does.
    _write(tmp_path, "selfhosted/selfhosted_latest.json", [{"title": "Unrelated title", "link": "https://sh/1", "published": "2026-08-27T00:00:00Z", "source": "TensorFlow Blog"}])
    index = ContentSearchIndex(data_dir=tmp_path)
    results = index.search("tensorflow")
    assert [r["title"] for r in results] == ["tensorflow at the start", "a tensorflow word match", "The tensorflowless debate", "Unrelated title", "The tensorflowless classic"]
    # Source-only result keeps its own source label.
    by_title = {r["title"]: r for r in results}
    assert by_title["Unrelated title"]["source"] == "TensorFlow Blog"


def test_search_is_case_insensitive_and_stripped(tmp_path: Path):
    """Query case and surrounding whitespace do not affect matching."""
    _write(tmp_path, "news/wired_latest.json", _articles(("Docker deep dive", "2026-08-28T00:00:00Z")))
    index = ContentSearchIndex(data_dir=tmp_path)
    assert len(index.search("docker")) == 1
    assert len(index.search("  DOCKER  ")) == 1
    assert index.search("") == []
    assert index.search("   ") == []


def test_limit_is_capped(tmp_path: Path):
    """limit truncates results and is clamped to [1, MAX_LIMIT]."""
    _write(tmp_path, "news/wired_latest.json", _articles(*[(f"Docker story {i}", f"2026-08-{i + 1:02d}T00:00:00Z") for i in range(10)]))
    index = ContentSearchIndex(data_dir=tmp_path)
    assert len(index.search("docker", limit=3)) == 3
    assert len(index.search("docker")) == 10  # default cap is higher than the corpus
    assert len(index.search("docker", limit=0)) <= 10  # clamped to >= 1, no crash
    assert len(index.search("docker", limit=10000)) == 10  # clamped to MAX_LIMIT


def test_ttl_rebuild(tmp_path: Path):
    """The index is cached for the TTL window, then rebuilt from disk."""
    clock = FakeClock()
    _write(tmp_path, "news/wired_latest.json", _articles(("Old story", "2026-08-01T00:00:00Z")))
    index = ContentSearchIndex(data_dir=tmp_path, ttl_seconds=300.0, now_fn=clock)
    assert index.search("story")[0]["title"] == "Old story"
    # Change the file on disk; within the TTL window the stale cache is served.
    _write(tmp_path, "news/wired_latest.json", _articles(("New story", "2026-08-28T00:00:00Z")))
    clock.now += 100.0
    assert index.search("story")[0]["title"] == "Old story"
    # Past the TTL the rebuild picks up the new content.
    clock.now += 201.0
    assert index.search("story")[0]["title"] == "New story"
    # invalidate() forces an immediate rebuild regardless of age.
    _write(tmp_path, "news/wired_latest.json", _articles(("Third story", "2026-08-28T00:00:00Z")))
    clock.now += 1.0
    index.invalidate()
    assert index.search("story")[0]["title"] == "Third story"


def test_malformed_and_missing_inputs_degrade(tmp_path: Path):
    """Invalid JSON, non-dict/titleless entries and missing files are skipped."""
    bad = tmp_path / "news" / "techcrunch_latest.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")
    _write(tmp_path, "kdnuggets/kdnuggets.json", ["not-a-dict", {}, {"link": "https://kd/1"}, {"title": "Valid entry", "link": "https://kd/2"}])
    _write(tmp_path, "markets/coingecko_latest.json", [{"name": "NoId Coin"}, {"symbol": "x"}])  # no id -> url None; no name -> skipped
    items = build_index(tmp_path)
    assert {(i["title"], i["url"]) for i in items} == {("Valid entry", "https://kd/2"), ("NoId Coin", None)}
    # Entirely missing data dir still yields an empty index.
    assert build_index(tmp_path / "does-not-exist") == []


def test_dedupe_across_files_by_url(tmp_path: Path):
    """The same URL in two collection files is indexed once (first wins)."""
    _write(tmp_path, "news/hn_frontpage_latest.json", [{"title": "Shared story", "link": "https://news.ycombinator.com/item?id=1", "published": "2026-08-28T00:00:00Z"}])
    _write(tmp_path, "hackernews/hackernews.json", [{"title": "Shared story duplicate", "link": "https://news.ycombinator.com/item?id=1", "published": "2026-08-28T00:00:00Z"}])
    items = build_index(tmp_path)
    assert len(items) == 1
    assert items[0]["title"] == "Shared story"


def test_video_without_url_or_title_skipped(tmp_path: Path):
    """Videos missing title or url are not indexed."""
    _write(tmp_path, "youtube/Chan/youtube_videos.json", [{"title": "Ok video", "url": "https://youtu.be/ok"}, {"title": "No url"}, {"url": "https://youtu.be/no-title"}])
    items = build_index(tmp_path)
    assert [i["title"] for i in items] == ["Ok video"]
    assert items[0]["source"] == "Chan"
