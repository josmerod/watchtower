"""Data Freshness Watcher — flags sources whose latest data went stale.

After every orchestrator run this watcher checks the mtime of each source's
``*_latest.json`` and records an event when a source crosses a staleness
threshold (fresh → stale → critical). The summary lands in
``data/watchers/data_freshness/freshness_latest.json`` and is rendered as the
"Source Freshness" card in the Metrics tab — at a glance, which feeds are
dead (this is the check that would have caught the 2026-08-27 deploy gap and
the silent reddit 403s without anyone looking manually).

Stale/critical sources are also mirrored into the shared alert-rule store
(``data/alerts/rules.json``, severity: critical→high, stale→medium) so they
surface in the Notifications tab; recovery to fresh resolves the rule. See
:mod:`src.alerts.rules_store`.

The age of a file only says whether its ETL ran. A news ETL rewrites its file
every cycle even when its source stopped publishing (FutureTools: a file written
every 2 h whose newest item is from 2024-05), so the sources registered with
``content_date`` are also judged by the age of their newest item: a week without
anything new is stale, a month is critical.

Usage:
    uv run python -m src.watchers.data_freshness_watcher
"""

import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from src.alerts.rules_store import sync_freshness_rules
from src.utils.file_system import get_project_root
from src.utils.logging import get_logger
from src.watchers.base_watcher import BaseWatcher

logger = get_logger("DataFreshnessWatcher")

# Registry of the platform's key data files. Thresholds: most ETLs run on the
# 2h scheduler, so warn_hours=26 means "missed a full day of runs" and
# critical_hours=168 means "dead for a week". Known-slow sources get looser
# thresholds.
SOURCE_FILES: list[dict[str, Any]] = [
    # Tech Radar (12 columns)
    {"key": "google_ai", "label": "Google AI Blog", "path": "news/google_ai_blog_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published"},
    {"key": "verge_ai", "label": "The Verge AI", "path": "news/verge_ai_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "kdnuggets", "label": "KDnuggets", "path": "kdnuggets/kdnuggets.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "cloud_updates", "label": "Cloud Updates", "path": "cloud_updates/cloud_updates_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "selfhosted", "label": "Self-Hosted (selfh.st + LS.io)", "path": "selfhosted/selfhosted_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "reddit_pulse", "label": "Reddit pulse (r/SelfHosted)", "path": "reddit_unified/SelfHosted_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "infoq", "label": "InfoQ", "path": "infoq/infoq_news.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "thenewstack", "label": "The New Stack", "path": "thenewstack/thenewstack_news.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "changelog", "label": "Changelog", "path": "changelog/changelog_news.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "hn_frontpage", "label": "Hacker News front page", "path": "news/hn_frontpage_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "wired", "label": "Wired", "path": "news/wired_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "mit_techreview", "label": "MIT Tech Review", "path": "news/mit_techreview_latest.json", "warn_hours": 26, "critical_hours": 168},
    # News + research
    {"key": "techcrunch", "label": "TechCrunch", "path": "news/techcrunch_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published"},
    # News tab (T-176). Its 21 files are rewritten every cycle, so their age only
    # tells that the ETL ran; "content_date" names the field that dates each item.
    {"key": "venturebeat", "label": "VentureBeat", "path": "news/venturebeat_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published"},
    {"key": "arstechnica", "label": "Ars Technica", "path": "news/arstechnica_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published"},
    {"key": "futuretools", "label": "FutureTools (News)", "path": "futuretools/futuretoolsnews.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published"},
    {"key": "bensbites", "label": "Ben's Bites", "path": "bensbites/bensbites_news.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "hackernews", "label": "Hacker News", "path": "hackernews/hackernews.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "medium_genai", "label": "Medium GenAI", "path": "medium_genai/medium_genai.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "meneame_general", "label": "Meneame General", "path": "meneame/meneame_general_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "meneame_tecnologia", "label": "Meneame Tech", "path": "meneame/meneame_tecnologia_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "indiehackers", "label": "Indie Hackers", "path": "indie_hackers/posts.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "kagi_business", "label": "Kagi Business", "path": "kagi_business/kagi_business.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "kagi_science", "label": "Kagi Science", "path": "kagi_science/kagi_science.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "kagi_gaming", "label": "Kagi Gaming", "path": "kagi_gaming/kagi_gaming.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "kagi_ai", "label": "Kagi AI (News)", "path": "kagi_ai/kagi_ai.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "kagi_europe", "label": "Kagi Europe", "path": "kagi_europe/kagi_europe.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "kagi_spain", "label": "Kagi Spain", "path": "kagi_spain/kagi_spain.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "microsiervos", "label": "Microsiervos", "path": "microsiervos/output/microsiervos_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    {"key": "spanish_tech", "label": "Spanish Tech (Xataka, Hipertextual, Genbeta)", "path": "news/spanish_tech_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published"},
    {"key": "tldr", "label": "tldr.tech (Tech/AI/Data)", "path": "tldr/tldr_news.json", "warn_hours": 26, "critical_hours": 168, "content_date": "published_at"},
    # Research
    {"key": "arxiv", "label": "ArXiv papers", "path": "arxiv/arxiv_papers_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "hf_trending", "label": "HF Trending papers", "path": "arxiv/hf_daily_papers_latest.json", "warn_hours": 30, "critical_hours": 168},
    {"key": "reddit_unified", "label": "Reddit unified", "path": "reddit_unified/reddit_unified_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "trends", "label": "Cross-source trends", "path": "analytics/trends/latest_trends.json", "warn_hours": 26, "critical_hours": 168},
    # Knowledge Garden. The ETL keeps the last good file when trendshift.io answers nothing, so a
    # blocked site shows up here as an aging snapshot.
    {"key": "trendshift", "label": "Trendshift (GitHub trending)", "path": "github/trendshift_daily_latest.json", "warn_hours": 26, "critical_hours": 168, "content_date": "snapshot_at"},
    # Benchmarks (BridgeBench is known-flaky: site mid-V3 migration)
    {"key": "llm_leaderboard", "label": "LLM leaderboard", "path": "benchmarks/llm_leaderboard.json", "warn_hours": 72, "critical_hours": 336},
    {"key": "bridgebench", "label": "BridgeBench Elo", "path": "benchmarks/bridgebench_overall.json", "warn_hours": 336, "critical_hours": 1440},
    # Markets
    {"key": "coingecko", "label": "CoinGecko markets", "path": "markets/coingecko_latest.json", "warn_hours": 26, "critical_hours": 168},
    # Security
    {"key": "security", "label": "Security feed (KEV + news)", "path": "security/security_latest.json", "warn_hours": 26, "critical_hours": 168},
    # Games
    {"key": "humblebundles", "label": "Humble bundles", "path": "games/humblebundles.json", "warn_hours": 72, "critical_hours": 336},
    {"key": "itchio_trending", "label": "Itch.io trending", "path": "games/itchio_trending.json", "warn_hours": 72, "critical_hours": 336},
    # IsThereAnyDeal. Both files stayed untouched from 2026-07-22 on (the feeds answered 403 and the ETL exited 0)
    # while nothing watched them. The deals feed holds the current day only, so a day without items is already news.
    {
        "key": "games_deals",
        "label": "Game deals (IsThereAnyDeal)",
        "path": "games/deals.json",
        "warn_hours": 26,
        "critical_hours": 168,
        "content_date": "published",
        "content_warn_hours": 26,
        "content_critical_hours": 168,
    },
    {
        "key": "games_bundles",
        "label": "Game bundles (IsThereAnyDeal)",
        "path": "games/bundles.json",
        "warn_hours": 26,
        "critical_hours": 168,
        "content_date": "published",
        "content_warn_hours": 72,
        "content_critical_hours": 336,
    },
]


# The newest item of a source registered with "content_date" is judged with its own
# thresholds: a week is long enough for a weekday newsletter or a digest that
# publishes twice a week. A source that publishes every day can set tighter ones
# with "content_warn_hours" and "content_critical_hours".
CONTENT_WARN_HOURS = 168
CONTENT_CRITICAL_HOURS = 720

_LEVEL_RANK = {"fresh": 0, "stale": 1, "critical": 2}


def _level(age_hours: float, warn_hours: float, critical_hours: float) -> str:
    """Fresh, stale or critical for an age and its two thresholds."""
    if age_hours >= critical_hours:
        return "critical"
    if age_hours >= warn_hours:
        return "stale"
    return "fresh"


def _date_epoch(value: Any) -> float | None:
    """Epoch of a date in ISO-8601 or RFC-2822 form; a date without a zone is taken as UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def newest_item_epoch(path: Path, field: str) -> float | None:
    """Epoch of the newest ``field`` among the items of a JSON file.

    The file holds a list of records, or an object with one list among its
    values. Returns ``None`` when the file cannot be read, holds no item or no
    date is understood.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning(f"Could not read {path.name} to date its content")
        return None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = next((value for value in data.values() if isinstance(value, list)), [])
    else:
        items = []
    epochs = [epoch for item in items if isinstance(item, dict) for epoch in (_date_epoch(item.get(field)),) if epoch is not None]
    return max(epochs) if epochs else None


def assess_freshness(source_files: list[dict[str, Any]] | None = None, data_dir: Path | None = None, now: float | None = None) -> dict[str, Any]:
    """Assess every registered source file's staleness.

    The age of the file is checked against the entry's thresholds. An entry with
    ``content_date`` is also judged by the age of its newest item (see
    ``CONTENT_WARN_HOURS``), and the worse of the two verdicts wins; ``age_hours``
    then holds the age that decided and ``content_age_hours`` the item's.

    Pure function (seam for tests): paths resolve under ``data_dir`` (defaults
    to the project's ``data/``), and ``now`` defaults to the current epoch.

    Returns:
        Summary dict with per-source records and fresh/stale/critical counts.
    """
    root = data_dir if data_dir is not None else Path(get_project_root()) / "data"
    now = now if now is not None else time.time()
    records: list[dict[str, Any]] = []
    for src in source_files or SOURCE_FILES:
        path = root / src["path"]
        record: dict[str, Any] = {
            "key": src["key"],
            "label": src["label"],
            "path": src["path"],
            "exists": path.exists(),
            "age_hours": None,
            "status": "critical",  # a missing file is critical by definition
        }
        if path.exists():
            file_age_hours = max(0.0, (now - path.stat().st_mtime) / 3600)
            record["age_hours"] = round(file_age_hours, 1)
            record["status"] = _level(file_age_hours, src["warn_hours"], src["critical_hours"])
            newest = newest_item_epoch(path, src["content_date"]) if src.get("content_date") else None
            if newest is not None:
                content_age_hours = max(0.0, (now - newest) / 3600)
                record["content_age_hours"] = round(content_age_hours, 1)
                content_status = _level(content_age_hours, src.get("content_warn_hours", CONTENT_WARN_HOURS), src.get("content_critical_hours", CONTENT_CRITICAL_HOURS))
                if _LEVEL_RANK[content_status] > _LEVEL_RANK[record["status"]]:
                    # The alert rule built from this record reads age_hours: hand it the age that decided
                    record["status"] = content_status
                    record["age_hours"] = round(content_age_hours, 1)
        records.append(record)

    by_status = {s: [r for r in records if r["status"] == s] for s in ("fresh", "stale", "critical")}
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "counts": {s: len(v) for s, v in by_status.items()},
        "sources": records,
    }


class DataFreshnessWatcher(BaseWatcher):
    """Watcher that flags data sources whose latest file went stale."""

    def __init__(self):
        super().__init__(name="data_freshness", url="local://watchtower/data", check_interval=7200)
        self.output_file = self.data_dir / "freshness_latest.json"

    def extract_value(self, html_content: str) -> Any:
        """Not used — this watcher reads local files, not a URL."""
        return None

    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Not used — transition detection is handled per-source in check()."""
        return True

    def check_freshness(self, data_dir: Path | None = None, now: float | None = None, rules_file: Path | None = None) -> dict[str, Any]:
        """Assess freshness, persist the summary, record transition events, and sync alert rules.

        Args:
            data_dir: Data root to check (defaults to the project's ``data/``).
            now: Epoch for staleness math (defaults to the current time).
            rules_file: Alert-rule store to write (defaults to ``data/alerts/rules.json``).

        Returns:
            The freshness summary dict (unchanged schema).
        """
        now = time.time() if now is None else now
        summary = assess_freshness(data_dir=data_dir, now=now)
        previous_statuses: dict[str, str] = self.previous_state.get("statuses", {})

        for record in summary["sources"]:
            prev = previous_statuses.get(record["key"])
            details = {"label": record["label"], "age_hours": record["age_hours"], "content_age_hours": record.get("content_age_hours"), "exists": record["exists"]}
            if prev and prev != record["status"]:
                self._record_event(f"freshness_{prev}_to_{record['status']}", old_value=prev, new_value=record["status"], details=details)
            elif not prev and record["status"] != "fresh":
                self._record_event("freshness_initial_alert", old_value=None, new_value=record["status"], details=details)

        self.output_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        new_state = {
            "last_check": summary["checked_at"],
            "statuses": {r["key"]: r["status"] for r in summary["sources"]},
            "first_seen": self.previous_state.get("first_seen", datetime.now().isoformat()),
        }
        self._save_state(new_state)
        # Advance in-memory state too — without this a second in-process check kept
        # seeing the pre-check statuses and transition events could never fire.
        self.previous_state = new_state
        counts = summary["counts"]
        logger.info(f"Freshness check: {counts['fresh']} fresh, {counts['stale']} stale, {counts['critical']} critical — summary at {self.output_file}")

        try:
            alert_counts = sync_freshness_rules(summary, rules_file=rules_file, now=now)
            logger.info(f"Freshness alert rules: {alert_counts['created']} created, {alert_counts['updated']} updated, {alert_counts['unchanged']} unchanged, {alert_counts['resolved']} resolved")
        except Exception as e:  # alert wiring must never break the freshness check
            logger.error(f"Failed to sync freshness alert rules: {e}")
        return summary


def main() -> None:
    """Run one freshness check (invoked as the last orchestrator step)."""
    watcher = DataFreshnessWatcher()
    watcher.check_freshness()


if __name__ == "__main__":
    main()
