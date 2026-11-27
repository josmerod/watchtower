"""``fetch_all_subreddits`` gives up on a run Reddit is refusing (T-174).

The server got an empty feed from every one of the 39 subreddits between
2026-11-17 and 2026-11-27, each after a minute of back-off: 38 minutes per
cycle for no posts. No network here: the feed fetcher is replaced.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from src.etl.news import reddit_unified_etl as reddit

FEEDS = list(reddit.SUBREDDITS_CONFIG)


@pytest.fixture()
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Collect the sleeps (pacing and back-off) instead of waiting."""
    taken: list[float] = []
    monkeypatch.setattr(reddit.time, "sleep", taken.append)
    return taken


@pytest.fixture()
def no_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither read nor write the checkpoint state."""
    monkeypatch.setattr(reddit, "load_state", lambda: {})
    monkeypatch.setattr(reddit, "save_state", lambda state: None)


def answer_with(monkeypatch: pytest.MonkeyPatch, empty: set[str]) -> list[str]:
    """One post per feed, none for those in ``empty`` (which answer 429); returns the feeds asked, in order."""
    asked: list[str] = []

    def fake(subreddit: str, stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        asked.append(subreddit)
        if subreddit in empty:
            if stats is not None:
                stats["rate_limited"] = True
            return []
        return [{"title": f"from r/{subreddit}", "url": f"https://www.reddit.com/r/{subreddit}/1"}]

    monkeypatch.setattr(reddit, "fetch_subreddit_rss", fake)
    return asked


def test_a_run_reddit_refuses_ends_after_three_empty_feeds(monkeypatch: pytest.MonkeyPatch, waits: list[float], no_state: None, caplog: pytest.LogCaptureFixture) -> None:
    asked = answer_with(monkeypatch, empty=set(FEEDS))

    with caplog.at_level(logging.WARNING, logger="RedditUnifiedETL"):
        posts = reddit.fetch_all_subreddits()

    assert asked == FEEDS[: reddit.EMPTY_FEEDS_BEFORE_STOPPING] == FEEDS[:3]
    assert posts == {name: [] for name in asked}
    assert f"the other {len(FEEDS) - 3} are not tried" in caplog.text
    assert waits == [3.0, 4.0]  # pacing between the three feeds tried, none after the last


def test_isolated_empty_feeds_do_not_stop_the_run(monkeypatch: pytest.MonkeyPatch, waits: list[float], no_state: None) -> None:
    asked = answer_with(monkeypatch, empty={FEEDS[4], FEEDS[20], FEEDS[21]})

    posts = reddit.fetch_all_subreddits()

    assert asked == FEEDS
    assert sum(1 for feed in posts.values() if feed) == len(FEEDS) - 3
    assert len(waits) == len(FEEDS)


def test_a_stopped_run_leaves_the_previous_files_alone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """What the consumers read stays what the last good run wrote."""
    (tmp_path / "data" / "reddit_unified").mkdir(parents=True)
    previous = tmp_path / "data" / "reddit_unified" / "reddit_news_latest.json"
    previous.write_text(json.dumps([{"title": "from the last good run"}]), encoding="utf-8")
    monkeypatch.setattr(reddit, "get_project_root", lambda: tmp_path)
    monkeypatch.setattr(reddit, "ensure_directories", lambda folders: None)

    reddit.save_reddit_data({name: [] for name in FEEDS[:3]})

    assert json.loads(previous.read_text(encoding="utf-8")) == [{"title": "from the last good run"}]
    assert sorted(path.name for path in previous.parent.iterdir()) == ["reddit_news_latest.json"]
