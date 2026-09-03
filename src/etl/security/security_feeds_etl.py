"""Security intelligence ETL — CISA KEV + BleepingComputer + The Hacker News.

Three keyless sources merged into one feed (T-050):
- CISA Known Exploited Vulnerabilities catalog (official JSON) — the CVEs
  actively exploited in the wild, newest first. Directly relevant to a homelab
  with exposed services.
- BleepingComputer RSS — security news + breach/malware reporting.
- The Hacker News RSS — offensive/defensive security research news.

Since T-081 the KEV records are also crossed against the self-hosted stack
(:mod:`src.etl.security.stack_cves`) and the matches mirrored as HIGH alert
rules (:mod:`src.alerts.rules_store`) — CVEs actively exploited that hit one
of the homelab's own services.

Usage:
    uv run python -m src.etl.security.security_feeds_etl

Output:
    data/security/security_latest.json (+ timestamped snapshot) — an envelope
    ``{"generated_at", "items": [...], "stack_matches": [...]}`` where
    ``items`` is the flat merged feed (unchanged shape per record) and
    ``stack_matches`` the per-repo KEV cross matches.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from src.alerts.rules_store import sync_stack_cve_rules
from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.security.stack_cves import match_stack_to_kev, total_stack_matches
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("SecurityFeedsETL")

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
# BleepingComputer evaluated and skipped: Cloudflare challenge (403) against
# the scraper UA. These three parse cleanly with the shared UA.
RSS_FEEDS: list[dict[str, str]] = [
    {"url": "https://feeds.feedburner.com/TheHackersNews", "source": "thehackernews", "platform": "thehackernews"},
    {"url": "https://www.securityweek.com/feed/", "source": "securityweek", "platform": "securityweek"},
    {"url": "https://krebsonsecurity.com/feed/", "source": "krebs", "platform": "krebsonsecurity"},
]
KEV_ITEMS_KEPT = 60


@with_retry
def fetch_kev() -> list[dict[str, Any]]:
    """Fetch the CISA KEV catalog, newest entries first, as article records."""
    records: list[dict[str, Any]] = []
    logger.info(f"Fetching CISA KEV catalog from {CISA_KEV_URL}")
    try:
        response = requests.get(CISA_KEV_URL, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=60)
        response.raise_for_status()
        vulns = response.json().get("vulnerabilities", [])
    except (requests.RequestException, ValueError) as exc:
        logger.error(f"Could not fetch CISA KEV: {exc}")
        return records

    vulns.sort(key=lambda v: v.get("dateAdded", ""), reverse=True)
    for vuln in vulns[:KEV_ITEMS_KEPT]:
        cve = vuln.get("cveID", "")
        product = vuln.get("product", "")
        vendor = vuln.get("vendor", "")
        summary = vuln.get("description", "")
        ransomware = vuln.get("knownRansomwareCampaignUse", "Unknown")
        summary_line = f"{summary} — vendor: {vendor} · ransomware use: {ransomware}"
        records.append(
            {
                "source": "cisa_kev",
                "source_category": "vulnerability",
                "title": f"🔴 {cve} — {product}",
                "link": f"https://nvd.nist.gov/vuln/detail/{cve}" if cve else "",
                "published": vuln.get("dateAdded", ""),
                "summary": summary_line[:500],
                "severity": "known-exploited",
                "cve": cve,
                "vendor": vendor,
                "product": product,
                "ransomware_use": ransomware,
                "due_date": vuln.get("dueDate", ""),
                "required_action": vuln.get("requiredAction", "")[:300],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "cisa",
                "content_type": "vulnerability_alert",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(records)} recent KEV entries (catalog: {len(vulns)} total)")
    return records


def _parse_date(published_raw: str) -> str:
    """Parse an RSS date string to ISO format, falling back to the raw value."""
    if not published_raw:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(published_raw, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return published_raw


def _fetch_rss_feed(feed: dict[str, str]) -> list[dict[str, Any]]:
    """Fetch and normalize one security news RSS feed."""
    entries: list[dict[str, Any]] = []
    logger.info(f"Fetching security feed {feed['source']} from {feed['url']}")
    try:
        response = requests.get(feed["url"], headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if parsed.bozo:
            logger.warning(f"Feed parse warning ({feed['source']}): {parsed.bozo_exception}")
    except requests.RequestException as exc:
        logger.error(f"Could not fetch {feed['source']}: {exc}")
        return entries

    for entry in parsed.entries:
        summary = ""
        if hasattr(entry, "summary") and entry.summary:
            summary = re.sub(r"<[^>]+>", "", entry.summary).strip()
        entries.append(
            {
                "source": feed["source"],
                "source_category": "security_news",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": _parse_date(entry.get("published", "")),
                "summary": summary[:500],
                "severity": "news",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": feed["platform"],
                "content_type": "news_article",
                "language": "en",
                "region": "global",
            }
        )
    logger.info(f"Retrieved {len(entries)} items from {feed['source']}")
    return entries


def fetch_security_feed() -> list[dict[str, Any]]:
    """Fetch every security source and merge into one feed (KEV first)."""
    entries = fetch_kev()
    for feed in RSS_FEEDS:
        entries.extend(_fetch_rss_feed(feed))
    logger.info(f"Security feed merged: {len(entries)} items")
    return entries


def save_security_entries(entries: list[dict[str, Any]], stack_matches: list[dict[str, Any]] | None = None) -> None:
    """Persist the security feed under ``data/security/`` as an envelope.

    The payload is ``{"generated_at", "items", "stack_matches"}`` — the flat
    merged feed plus the KEV-vs-stack cross matches (T-081). Readers that only
    need the feed consume ``items``; the Security tab shows both.
    """
    if not entries:
        logger.info("No security entries to save. Skipping.")
        return
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": entries,
        "stack_matches": stack_matches or [],
    }
    output_dir = os.path.join(get_project_root(), "data", "security")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "security_latest.json")
    snapshot = os.path.join(output_dir, f"security_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(entries)} security entries ({total_stack_matches(payload['stack_matches'])} stack matches) to {latest}")


def _sync_stack_cve_alerts(stack_matches: list[dict[str, Any]]) -> None:
    """Mirror stack-matching KEV CVEs into the shared alert store (best effort).

    Wrapped in try/except so a broken rules store (locked file, bad JSON…)
    never takes the whole security ETL down — same contract as the data
    freshness watcher's alert wiring.
    """
    try:
        counts = sync_stack_cve_rules(stack_matches)
        logger.info(
            f"Stack CVE alert rules: {counts['created']} created, {counts['updated']} updated, "
            f"{counts['unchanged']} unchanged, {counts['resolved']} resolved ({total_stack_matches(stack_matches)} active matches)"
        )
    except Exception as exc:  # alert wiring must never break the ETL
        logger.error(f"Failed to sync stack CVE alert rules: {exc}")


def main() -> None:
    """Run the security feeds ETL."""
    logger.info("Starting security feeds ETL")
    try:
        entries = fetch_security_feed()
        if not entries:
            logger.warning("No entries fetched from security sources. Exiting.")
            return
        kev_entries = [e for e in entries if e.get("source") == "cisa_kev"]
        stack_matches = match_stack_to_kev(kev_entries)
        save_security_entries(entries, stack_matches)
        _sync_stack_cve_alerts(stack_matches)
        logger.info(f"Security feeds ETL complete: {len(entries)} items, {total_stack_matches(stack_matches)} stack matches.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Security feeds ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
