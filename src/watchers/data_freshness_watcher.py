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

Usage:
    uv run python -m src.watchers.data_freshness_watcher
"""

import json
import time
from datetime import datetime, timezone
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
    {"key": "google_ai", "label": "Google AI Blog", "path": "news/google_ai_blog_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "verge_ai", "label": "The Verge AI", "path": "news/verge_ai_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "kdnuggets", "label": "KDnuggets", "path": "kdnuggets/kdnuggets.json", "warn_hours": 26, "critical_hours": 168},
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
    {"key": "techcrunch", "label": "TechCrunch", "path": "news/techcrunch_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "arxiv", "label": "ArXiv papers", "path": "arxiv/arxiv_papers_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "hf_trending", "label": "HF Trending papers", "path": "arxiv/hf_daily_papers_latest.json", "warn_hours": 30, "critical_hours": 168},
    {"key": "reddit_unified", "label": "Reddit unified", "path": "reddit_unified/reddit_unified_latest.json", "warn_hours": 26, "critical_hours": 168},
    {"key": "trends", "label": "Cross-source trends", "path": "analytics/trends/latest_trends.json", "warn_hours": 26, "critical_hours": 168},
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
]


def assess_freshness(source_files: list[dict[str, Any]] | None = None, data_dir: Path | None = None, now: float | None = None) -> dict[str, Any]:
    """Assess every registered source file's staleness.

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
        record = {
            "key": src["key"],
            "label": src["label"],
            "path": src["path"],
            "exists": path.exists(),
            "age_hours": None,
            "status": "critical",  # a missing file is critical by definition
        }
        if path.exists():
            age_hours = max(0.0, (now - path.stat().st_mtime) / 3600)
            record["age_hours"] = round(age_hours, 1)
            if age_hours >= src["critical_hours"]:
                record["status"] = "critical"
            elif age_hours >= src["warn_hours"]:
                record["status"] = "stale"
            else:
                record["status"] = "fresh"
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
            if prev and prev != record["status"]:
                self._record_event(
                    f"freshness_{prev}_to_{record['status']}",
                    old_value=prev,
                    new_value=record["status"],
                    details={"label": record["label"], "age_hours": record["age_hours"], "exists": record["exists"]},
                )
            elif not prev and record["status"] != "fresh":
                self._record_event(
                    "freshness_initial_alert",
                    old_value=None,
                    new_value=record["status"],
                    details={"label": record["label"], "age_hours": record["age_hours"], "exists": record["exists"]},
                )

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
