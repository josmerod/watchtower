"""Mi stack release radar ETL — GitHub releases of the self-hosted stack.

Tracks new releases of the services that power the homelab (n8n, Home
Assistant, Immich, Jellyfin, ArchiSteamFarm, Tdarr) through GitHub's keyless
``releases.atom`` feeds, feeding the Tech Radar tab's "Mi stack" subtab
(spec 13 TR-F4).

Usage:
    uv run python -m src.etl.github.stack_releases_etl

Output:
    data/github/stack_releases_{timestamp}.json + stack_releases_latest.json
    + run_summary_latest.json
"""

import html
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote

import feedparser
import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("StackReleasesETL")

OUTPUT_SUBDIR = "data/github"
DEFAULT_MAX_RELEASES = 5  # per-repo cap keeping the feed signal > noise
SUMMARY_MAX_CHARS = 200
FEED_DELAY_SECONDS = 1.0  # polite pacing between GitHub feed fetches
REQUEST_TIMEOUT = 30

# The self-hosted stack (spec 13 TR-F4). Repo choices, probed live
# 2026-08-28 (all feeds exist and return atom with ``updated_parsed``):
# - n8n-io/n8n — automation; versioned releases plus rolling "beta"/"stable"
#   tags, the cap filters the noise.
# - home-assistant/core — chosen over operating-system/addons: the stack runs
#   HA as a container, so core is the version that actually updates (the OS
#   repo only matters for HAOS appliance installs and moves ~monthly). Core
#   publishes often (patch + beta cadence), so it gets a tighter cap of 3.
# - immich-app/immich, jellyfin/jellyfin — media stack.
# - JustArchiNET/ArchiSteamFarm — frequent stable releases.
# - HaveAGitGat/Tdarr — the feed exists but GitHub releases stopped in 2020
#   (updates ship through the app's own channel); kept for completeness, the
#   stale entries simply sort last by date.
STACK_REPOS: list[dict[str, Any]] = [
    {"owner": "n8n-io", "repo": "n8n", "label": "n8n", "max_releases": DEFAULT_MAX_RELEASES},
    {"owner": "home-assistant", "repo": "core", "label": "home-assistant", "max_releases": 3},
    {"owner": "immich-app", "repo": "immich", "label": "immich", "max_releases": DEFAULT_MAX_RELEASES},
    {"owner": "jellyfin", "repo": "jellyfin", "label": "jellyfin", "max_releases": DEFAULT_MAX_RELEASES},
    {"owner": "JustArchiNET", "repo": "ArchiSteamFarm", "label": "ArchiSteamFarm", "max_releases": DEFAULT_MAX_RELEASES},
    {"owner": "HaveAGitGat", "repo": "Tdarr", "label": "Tdarr", "max_releases": DEFAULT_MAX_RELEASES},
]


def _releases_atom_url(owner: str, repo: str) -> str:
    """Return the keyless GitHub releases.atom URL for one repository."""
    return f"https://github.com/{owner}/{repo}/releases.atom"


@with_retry
def _fetch_feed(url: str) -> bytes:
    """Fetch one atom feed, retrying transient network/HTTP errors."""
    response = requests.get(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.content


def _tag_from_link(link: str) -> str:
    """Extract the tag from a releases.atom entry link/id URL.

    Links look like ``https://github.com/{owner}/{repo}/releases/tag/{tag}``
    with the tag percent-encoded; returns ``""`` for unexpected shapes.
    """
    match = re.search(r"/releases/tag/([^/?#]+)$", link or "")
    return unquote(match.group(1)) if match else ""


def _version_from_tag(tag: str) -> str:
    """Normalize a release tag into a bare version string.

    Strips scoped-package prefixes (``n8n@2.36.8`` → ``2.36.8``) and a
    leading ``v``/``V`` (``v3.1.0`` → ``3.1.0``); falls back to the raw tag.
    """
    version = re.sub(r"^[^@]*@", "", tag).lstrip("vV")
    return version or tag


def _summarize(notes_html: str) -> str:
    """Reduce release-note HTML/markdown to a short plain-text first sentence.

    Strips HTML tags and entities, removes common markdown decoration,
    collapses whitespace and keeps at most the first sentence (hard-capped
    at ``SUMMARY_MAX_CHARS`` characters).
    """
    text = re.sub(r"<[^>]+>", " ", notes_html or "")
    text = html.unescape(text)
    # Markdown decoration that survives tag stripping (links, images,
    # emphasis, inline code, headings, bullet dashes).
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links -> label
    text = re.sub(r"[`*_#>|]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    first_sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    summary = first_sentence or text
    if len(summary) > SUMMARY_MAX_CHARS:
        summary = summary[: SUMMARY_MAX_CHARS - 1].rstrip() + "…"
    return summary


def _iso_from_parsed(parsed: Any, fallback_raw: str) -> str:
    """Convert feedparser's ``updated_parsed``/``published_parsed`` to ISO UTC.

    Atom feeds expose ``<updated>`` instead of ``<published>`` — prefer
    ``updated_parsed`` and fall back to ``published_parsed``, then to the raw
    string (mirrors ``reddit_unified_etl``). Returns ``""`` when undatable.
    """
    if isinstance(parsed, time.struct_time):
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
        except (TypeError, IndexError, ValueError):
            return ""
    return fallback_raw or ""


def parse_repo_releases(content: bytes, repo_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse one repo's releases.atom body into normalized release items."""
    feed = feedparser.parse(content)
    releases: list[dict[str, Any]] = []
    for entry in feed.entries[: repo_cfg.get("max_releases", DEFAULT_MAX_RELEASES)]:
        link = entry.get("link", "") or entry.get("id", "")
        tag = _tag_from_link(link)
        parsed_date = getattr(entry, "updated_parsed", None) or getattr(entry, "published_parsed", None)
        releases.append(
            {
                "repo": repo_cfg["repo"],
                "owner": repo_cfg["owner"],
                "tag": tag,
                "version": _version_from_tag(tag),
                "title": entry.get("title", tag) or tag,
                "link": link,
                "published": _iso_from_parsed(parsed_date, entry.get("updated", "") or entry.get("published", "")),
                "summary": _summarize(entry.get("summary", "")),
                "source": "github_releases",
                "source_category": "mi_stack",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return releases


def fetch_repo_releases(repo_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch and parse one stack repo's releases feed; failures return []."""
    url = _releases_atom_url(repo_cfg["owner"], repo_cfg["repo"])
    logger.info(f"Fetching releases feed for {repo_cfg['owner']}/{repo_cfg['repo']}")
    try:
        content = _fetch_feed(url)
    except requests.RequestException as exc:
        logger.error(f"Could not fetch {url}: {exc}")
        return []
    releases = parse_repo_releases(content, repo_cfg)
    logger.info(f"Retrieved {len(releases)} releases from {repo_cfg['owner']}/{repo_cfg['repo']}")
    return releases


def fetch_stack_releases() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch every stack repo feed; return date-sorted releases plus stats.

    A dead feed yields an empty list instead of aborting the run, so one
    flaky repo never takes the whole radar down.
    """
    all_releases: list[dict[str, Any]] = []
    stats: dict[str, Any] = {"repos_total": len(STACK_REPOS), "repos_ok": 0, "releases_per_repo": {}}
    for index, repo_cfg in enumerate(STACK_REPOS):
        releases = fetch_repo_releases(repo_cfg)
        stats["releases_per_repo"][repo_cfg["repo"]] = len(releases)
        if releases:
            stats["repos_ok"] += 1
        all_releases.extend(releases)
        if index < len(STACK_REPOS) - 1:
            time.sleep(FEED_DELAY_SECONDS)
    all_releases.sort(key=lambda r: r.get("published") or "", reverse=True)
    logger.info(f"Fetched {len(all_releases)} releases across {stats['repos_ok']}/{stats['repos_total']} stack repos")
    return all_releases, stats


def save_stack_releases(releases: list[dict[str, Any]], stats: dict[str, Any], start_time: datetime | None = None) -> bool:
    """Persist releases under ``data/github/``; return whether files were written.

    Writes a timestamped snapshot, ``stack_releases_latest.json`` and a
    ``run_summary_latest.json`` with the fields other ETLs expose. Graceful
    failure: an empty run or a partial run (less than half the repos answered)
    keeps the previous last-good ``*_latest.json`` untouched.
    """
    if not releases:
        logger.warning("No releases fetched — keeping previous latest file")
        return False
    if stats.get("repos_ok", 0) < (stats.get("repos_total", 0) + 1) // 2:
        logger.warning(f"Partial run ({stats.get('repos_ok', 0)}/{stats.get('repos_total', 0)} repos) — keeping previous latest file")
        return False

    output_dir = os.path.join(get_project_root(), OUTPUT_SUBDIR)
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    snapshot_file = os.path.join(output_dir, f"stack_releases_{timestamp}.json")
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(releases, f, indent=2, ensure_ascii=False)

    latest_file = os.path.join(output_dir, "stack_releases_latest.json")
    shutil.copy2(snapshot_file, latest_file)

    end_time = datetime.now(timezone.utc)
    started = start_time or end_time
    run_summary = {
        "etl_name": "stack_releases",
        "start_time": started.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": (end_time - started).total_seconds(),
        "records_extracted": len(releases),
        "records_transformed": len(releases),
        "records_loaded": len(releases),
        "records_failed": 0,
        "error_count": stats.get("repos_total", 0) - stats.get("repos_ok", 0),
        "success": True,
        "repos_total": stats.get("repos_total", 0),
        "repos_ok": stats.get("repos_ok", 0),
        "releases_per_repo": stats.get("releases_per_repo", {}),
        "repos": [f"{cfg['owner']}/{cfg['repo']}" for cfg in STACK_REPOS],
        "output_dir": output_dir,
    }
    with open(os.path.join(output_dir, "run_summary_latest.json"), "w", encoding="utf-8") as f:
        json.dump(run_summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(releases)} stack releases to {latest_file}")
    return True


def main() -> None:
    """Run the mi-stack GitHub releases ETL."""
    logger.info("Starting mi-stack GitHub releases ETL")
    start_time = datetime.now(timezone.utc)
    try:
        releases, stats = fetch_stack_releases()
        if save_stack_releases(releases, stats, start_time=start_time):
            logger.info(f"Mi-stack ETL complete: {len(releases)} releases from {stats['repos_ok']}/{stats['repos_total']} repos.")
        else:
            logger.warning("Mi-stack ETL produced no usable data; previous outputs kept.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Mi-stack ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
