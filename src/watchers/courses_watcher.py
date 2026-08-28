"""Courses Watcher — detects newly published courses that match interest keywords.

The five course ETLs (AWS Skill Builder, GCP Skills Boost, Hugging Face Learn,
Microsoft Applied Skills and the Udemy spreadsheet) refresh their catalogs
under ``data/`` on every orchestrator run. This watcher diffs each provider
catalog against the previous snapshot (persisted as
``data/watchers/courses/previous_catalogs.json``) and records one
``new_matching_course`` event per course that (a) was not in the previous
snapshot and (b) whose title matches any of ``KEYWORDS``. The first run is a
baseline (no events). Providers whose file is missing, empty or malformed are
skipped and noted in ``state.json`` so drift is visible — and because they are
left out of the snapshot, their return re-baselines instead of flooding events
with courses that were never really new.

Usage:
    uv run python -m src.watchers.courses_watcher
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.file_system import get_project_root
from src.utils.logging import get_logger
from src.watchers.base_watcher import BaseWatcher

logger = get_logger("CoursesWatcher")

# Interest keywords: lowercase, matched as case-insensitive substrings of the course title.
KEYWORDS: tuple[str, ...] = ("llm", "rag", "agent", "docker", "kubernetes", "python", "data", "mcp", "ai")

# Registry of provider catalogs, mirroring the output paths of src/etl/courses/*. Note
# that none of these ETLs uses the *_latest.json convention: four write fixed-name
# files under data/courses/ and the Udemy spreadsheet persists to
# data/udemy/udemy_courses.json for the dashboard.
COURSE_SOURCES: dict[str, dict[str, str]] = {
    "aws_skill_builder": {"label": "AWS Skill Builder", "path": "courses/aws_skill_builder.json"},
    "gcp_skills_boost": {"label": "GCP Skills Boost", "path": "courses/gcp_skills_boost.json"},
    "hf_learn": {"label": "Hugging Face", "path": "courses/hf_learn.json"},
    "ms_applied_skills": {"label": "Microsoft Learn", "path": "courses/ms_applied_skills.json"},
    "udemy": {"label": "Udemy", "path": "udemy/udemy_courses.json"},
}


def _course_key(course: dict[str, Any]) -> str:
    """Compute the stable identity key for one course record.

    The URL is the primary identity: all five ETLs emit one for every item, three
    of them (AWS, GCP, MS) already key their own ``first_detected_at`` bookkeeping
    on it, and Udemy derives its URLs deterministically from the Course ID (or the
    title), so URLs are stable across runs. Titles can be re-worded by a source
    and may collide, so the normalized title is only a fallback for rows whose
    URL is missing or blank.

    Args:
        course: One course record from a provider catalog.

    Returns:
        Normalized identity string (lowercased URL, or ``title:<normalized title>``).
    """
    url = str(course.get("url") or "").strip().lower()
    if url:
        return url
    title = " ".join(str(course.get("title") or "").split()).lower()
    return f"title:{title}"


def _matched_keywords(title: str, keywords: Sequence[str]) -> list[str]:
    """Return the keywords contained in the title (case-insensitive substring)."""
    lowered = title.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def load_catalogs(data_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Load every registered provider catalog under ``data_dir`` (IO seam for tests).

    Missing, empty, malformed or non-list catalog files are skipped and reported
    in ``missing`` — the data dir is written by many ETLs concurrently, so a
    partially written file must never crash the watcher.

    Args:
        data_dir: Root ``data/`` directory holding the provider catalogs.

    Returns:
        Tuple of (provider key -> list of course dicts, provider keys that were
        missing or unreadable).
    """
    catalogs: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []
    for key, source in COURSE_SOURCES.items():
        path = data_dir / source["path"]
        if not path.exists():
            missing.append(key)
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Malformed catalog {path}: {e!s} — treating {key} as missing")
            missing.append(key)
            continue
        if not isinstance(raw, list):
            logger.warning(f"Catalog {path} is not a JSON list — treating {key} as missing")
            missing.append(key)
            continue
        courses = [item for item in raw if isinstance(item, dict)]
        if not courses:
            missing.append(key)
            continue
        catalogs[key] = courses
    return catalogs, missing


def assess_new_courses(
    previous_catalogs: dict[str, list[dict[str, Any]]] | None,
    current_catalogs: dict[str, list[dict[str, Any]]],
    keywords: Sequence[str] = KEYWORDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Diff the current provider catalogs against the previous snapshot (pure, no IO).

    Args:
        previous_catalogs: Provider key -> course list from the previous run, or
            None (or empty) on the first run, which is a baseline with no events.
        current_catalogs: Provider key -> course list loaded this run; providers
            whose file was missing or unreadable are simply absent.
        keywords: Keywords matched (case-insensitive substring) against titles.
        now: Timestamp recorded in the state (defaults to current UTC time).

    Returns:
        Dict with ``first_run`` (bool), ``new_matching_courses`` (event-ready
        dicts with provider/title/url/matched_keywords/message) and ``state``
        (per-provider label/status/count to persist in state.json).
    """
    now = now or datetime.now(timezone.utc)
    first_run = not previous_catalogs
    new_matching: list[dict[str, Any]] = []
    providers: dict[str, Any] = {}

    for key, source in COURSE_SOURCES.items():
        courses = current_catalogs.get(key) or []
        if not courses:
            # Missing/empty file this run: skip diffing and note it in the state.
            providers[key] = {"label": source["label"], "status": "missing", "count": None}
            continue

        # Key by identity (URL, title fallback); first occurrence wins on duplicates.
        key_to_course: dict[str, dict[str, Any]] = {}
        for course in courses:
            key_to_course.setdefault(_course_key(course), course)

        providers[key] = {"label": source["label"], "status": "ok", "count": len(courses)}
        if first_run:
            continue

        previous_courses = previous_catalogs.get(key)
        if not previous_courses:
            # Provider was missing (or brand new) on the previous run: record this
            # catalog as its baseline instead of flooding events with courses that
            # were already there before we first saw the file.
            continue
        previous_keys = {_course_key(c) for c in previous_courses}
        for course_key in sorted(set(key_to_course) - previous_keys):
            course = key_to_course[course_key]
            title = str(course.get("title") or "").strip()
            matched = _matched_keywords(title, keywords)
            if not matched:
                continue
            new_matching.append(
                {
                    "provider": source["label"],
                    "provider_key": key,
                    "title": title,
                    "url": str(course.get("url") or ""),
                    "matched_keywords": matched,
                    "message": f"nuevo curso de {source['label']} que matchea keywords {', '.join(matched)}",
                }
            )

    return {
        "first_run": first_run,
        "new_matching_courses": new_matching,
        "state": {"last_check": now.isoformat(), "keywords": list(keywords), "providers": providers},
    }


class CoursesWatcher(BaseWatcher):
    """Watcher that emits events when new keyword-matching courses appear in the catalogs."""

    def __init__(self) -> None:
        """Initialize the courses watcher over the local course catalogs."""
        super().__init__(name="courses", url="local://watchtower/data/courses", check_interval=7200)
        # Re-assert the dirs: keep the watcher usable even when the base-class
        # ensure_directories call was neutralized (e.g. in hermetic tests).
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.catalogs_file = self.data_dir / "previous_catalogs.json"

    def extract_value(self, html_content: str) -> Any:
        """Not used — this watcher reads local catalog files, not a URL."""
        return None

    def has_changed(self, old_value: Any, new_value: Any) -> bool:
        """Not used — new-course detection is handled per provider in check_courses()."""
        return False

    def _load_previous_catalogs(self) -> dict[str, list[dict[str, Any]]] | None:
        """Load the previous catalogs snapshot, or None when absent/unusable (first run).

        Returns:
            Provider key -> course list from the last check, or None to re-baseline.
        """
        if not self.catalogs_file.exists():
            return None
        try:
            raw = json.loads(self.catalogs_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"Unusable catalogs snapshot {self.catalogs_file}: {e!s} — re-baselining")
            return None
        if not isinstance(raw, dict):
            self.logger.warning(f"Catalogs snapshot {self.catalogs_file} is not a JSON object — re-baselining")
            return None
        catalogs = {key: [c for c in courses if isinstance(c, dict)] for key, courses in raw.items() if isinstance(courses, list)}
        return catalogs or None

    def _record_course_event(self, course: dict[str, Any], seq: int) -> None:
        """Record one ``new_matching_course`` event for a new matching course.

        Mirrors ``BaseWatcher._record_event``'s schema but appends a sequence
        suffix so several events recorded within the same second don't collide
        on the ``%Y%m%d%H%M%S`` filename.

        Args:
            course: Event-ready course dict from ``assess_new_courses``.
            seq: 1-based position of this course among the run's events.
        """
        timestamp = datetime.now()
        event_id = f"{timestamp.strftime('%Y%m%d%H%M%S')}_new_matching_course_{seq:03d}"
        event = {
            "id": event_id,
            "type": "new_matching_course",
            "timestamp": timestamp.isoformat(),
            "watcher": self.name,
            "url": self.url,
            "old_value": None,
            "new_value": course["title"],
            "details": {
                "message": course["message"],
                "provider": course["provider"],
                "title": course["title"],
                "url": course["url"],
                "matched_keywords": course["matched_keywords"],
            },
        }
        event_file = self.events_dir / f"{event_id}.json"
        try:
            event_file.write_text(json.dumps(event, indent=2, ensure_ascii=False), encoding="utf-8")
            self.logger.info(f"Event recorded: {event_id}")
        except Exception as e:
            self.logger.error(f"Error recording event {event_id}: {e!s}")

    def check_courses(self, data_dir: Path | None = None) -> dict[str, Any]:
        """Run one diff of the course catalogs, emitting events and persisting state.

        Args:
            data_dir: Root ``data/`` directory holding the catalogs (defaults to
                the project's ``data/``; seam for tests).

        Returns:
            The ``assess_new_courses`` result dict for this run.
        """
        root = data_dir if data_dir is not None else Path(get_project_root()) / "data"
        current_catalogs, missing = load_catalogs(root)
        previous_catalogs = self._load_previous_catalogs()

        result = assess_new_courses(previous_catalogs, current_catalogs, KEYWORDS)
        for seq, course in enumerate(result["new_matching_courses"], start=1):
            self._record_course_event(course, seq)

        # Persist the current catalogs as the next run's snapshot. Providers that
        # were missing stay out of the snapshot so their return re-baselines.
        self.catalogs_file.write_text(json.dumps(current_catalogs, indent=2, ensure_ascii=False), encoding="utf-8")
        new_state = {**result["state"], "first_seen": self.previous_state.get("first_seen", datetime.now(timezone.utc).isoformat())}
        self._save_state(new_state)
        self.previous_state = new_state

        tracked = sum(provider["count"] or 0 for provider in new_state["providers"].values())
        self.logger.info(f"Courses check: {len(result['new_matching_courses'])} new matching courses, {tracked} courses tracked, missing providers: {missing if missing else 'none'}")
        return result


def main() -> None:
    """Run one courses check (invoked as an orchestrator step after the course ETLs)."""
    watcher = CoursesWatcher()
    watcher.check_courses()


if __name__ == "__main__":
    main()
