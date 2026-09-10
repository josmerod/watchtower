"""OSV stack advisories ETL — stack-relevant security advisories via OSV.dev (T-091).

Queries the keyless, free OSV.dev aggregate (GitHub GHSA + PyPI + CVE records)
for every wired service of the self-hosted stack and keeps the advisories with
severity >= HIGH. This complements the KEV cross (:mod:`src.etl.security.stack_cves`):
KEV only covers CVEs *actively exploited*, while OSV/GHSA covers ALL published
advisories — e.g. the recent critical n8n RCEs land here days before any KEV
entry exists.

Ecosystem mapping (live-probed 2026-09-10, POST https://api.osv.dev/v1/query):
- n8n-io/n8n → npm package "n8n": 140 advisories (24 CRITICAL, 53 HIGH) — wired.
- home-assistant/core → PyPI package "homeassistant": 20 advisories (GHSA +
  PYSEC + CVE conversion records) — wired.
- immich-app/immich → GIT ecosystem
  (``https://github.com/immich-app/immich``): 8 CVE records — wired.
- jellyfin/jellyfin → GIT ecosystem
  (``https://github.com/jellyfin/jellyfin``): 22 CVE records — wired.

Negatives (probed, returned zero advisories — NOT wired, kept out of the map so
they cost no requests): JustArchiNET/ArchiSteamFarm (NuGet "ArchiSteamFarm" → 0,
GIT → 0 — ASF advisories simply are not published on OSV) and HaveAGitGat/Tdarr
(npm "tdarr" → 0, GIT → 0).

Severity grading: a CVSS v3.1 vector is computed to the exact base score when
present; otherwise the GitHub ``database_specific.severity`` string is used;
CVSS v4-only vectors (CVE records) are *approximated* by mapping their metrics
onto the v3.1 formula (``AT:P``→``AC:H``, ``UI:A/R/P``→``UI:R``, worst of
vulnerable/subsequent system impact, changed scope when any S* is High) — good
enough for the >=HIGH band cut, never presented as an exact score.

Usage:
    uv run python -m src.etl.security.osv_stack_advisories_etl

Output:
    data/security/osv_stack_latest.json (+ timestamped snapshot) — an envelope
    ``{"generated_at", "services": [{"repo", "service_label", "advisories":
    [...]}], "total_advisories": N}`` consumed by the Security tab's "🧰 Tu
    stack" OSV companion card. One service failing never kills the run; a run
    where EVERY wired service failed keeps the previous last-good file.
"""

import json
import math
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.github.stack_releases_etl import STACK_REPOS
from src.etl.security.stack_cves import repo_key
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("OsvStackAdvisoriesETL")

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
REQUEST_TIMEOUT = 30
MAX_PAGES = 3  # bounded pagination: page 1 already carries the full catalog in practice
SERVICE_DELAY_SECONDS = 1.0  # polite pacing between OSV queries
ADVISORIES_PER_SERVICE = 10  # newest-first cap keeping the card signal > noise
SUMMARY_MAX_CHARS = 250

# Only services whose OSV probe returned sensible advisories (see module
# docstring). Repo key (lowercase "owner/repo") -> OSV package query.
OSV_SERVICE_MAP: dict[str, dict[str, str]] = {
    "n8n-io/n8n": {"package_name": "n8n", "ecosystem": "npm"},
    "home-assistant/core": {"package_name": "homeassistant", "ecosystem": "PyPI"},
    "immich-app/immich": {"package_name": "https://github.com/immich-app/immich", "ecosystem": "GIT"},
    "jellyfin/jellyfin": {"package_name": "https://github.com/jellyfin/jellyfin", "ecosystem": "GIT"},
}

SEVERITY_RANK: dict[str, int] = {"LOW": 1, "MODERATE": 2, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
SEVERITY_FLOOR = "HIGH"

# CVSS v3.1 base-score weights (first.org specification).
_AV_WEIGHTS = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_AC_WEIGHTS = {"L": 0.77, "H": 0.44}
_PR_WEIGHTS_UNCHANGED = {"N": 0.85, "L": 0.62, "H": 0.27}
_PR_WEIGHTS_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.50}
_UI_WEIGHTS = {"N": 0.85, "R": 0.62}
_CIA_WEIGHTS = {"H": 0.56, "L": 0.22, "N": 0.0}

_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def _parse_vector(vector: str) -> dict[str, str] | None:
    """Split a CVSS vector string into its metrics; ``None`` when malformed."""
    try:
        metrics = dict(part.split(":", 1) for part in vector.split("/")[1:])
    except (ValueError, AttributeError):
        return None
    return metrics if metrics else None


def _cvss_v3_base_score(vector: str) -> float | None:
    """Compute the exact CVSS v3.1 base score from a vector string.

    Implements the specification formula (impact sub-score, exploitability,
    scope-dependent weighting and the Roundup to one decimal). Returns
    ``None`` when the vector is missing metrics or carries unknown values.
    """
    metrics = _parse_vector(vector)
    if not metrics:
        return None
    try:
        changed_scope = metrics["S"] == "C"
        av = _AV_WEIGHTS[metrics["AV"]]
        ac = _AC_WEIGHTS[metrics["AC"]]
        pr = (_PR_WEIGHTS_CHANGED if changed_scope else _PR_WEIGHTS_UNCHANGED)[metrics["PR"]]
        ui = _UI_WEIGHTS[metrics["UI"]]
        iss = 1 - (1 - _CIA_WEIGHTS[metrics["C"]]) * (1 - _CIA_WEIGHTS[metrics["I"]]) * (1 - _CIA_WEIGHTS[metrics["A"]])
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if changed_scope else 6.42 * iss
        if impact <= 0:
            return 0.0
        exploitability = 8.22 * av * ac * pr * ui
        score = 1.08 * (impact + exploitability) if changed_scope else impact + exploitability
        return min(math.ceil(round(min(score, 10.0) * 10, 4)) / 10, 10.0)
    except KeyError:
        return None


def _worst_metric(*levels: str | None) -> str:
    """Return the worst of several CVSS impact levels (H > L > N)."""
    for level in ("H", "L", "N"):
        if level in levels:
            return level
    return "N"


def _cvss_v4_approx_score(vector: str) -> float | None:
    """Approximate a CVSS v4.0 vector by mapping it onto the v3.1 formula.

    Honest approximation (documented in the module docstring): ``AT:P`` →
    ``AC:H`` (attack requirements make exploitation harder), ``UI:A/R/P`` →
    ``UI:R``, each impact metric takes the worst of the vulnerable/subsequent
    system pair, and scope counts as changed when any subsequent-system impact
    is High. The result is only used for the >=HIGH band cut — never presented
    as an exact score. Returns ``None`` when required metrics are missing.
    """
    metrics = _parse_vector(vector)
    if not metrics:
        return None
    required = ("AV", "PR", "UI", "VC", "VI", "VA")
    if any(metric not in metrics for metric in required):
        return None
    changed_scope = any(metrics.get(metric) == "H" for metric in ("SC", "SI", "SA"))
    v3_vector = "/".join(
        [
            "CVSS:3.1",
            f"AV:{metrics['AV']}" if metrics["AV"] in _AV_WEIGHTS else "",
            "AC:H" if metrics.get("AT") == "P" else (f"AC:{metrics['AC']}" if metrics.get("AC") in _AC_WEIGHTS else ""),
            f"PR:{metrics['PR']}" if metrics["PR"] in _PR_WEIGHTS_UNCHANGED else "",
            "UI:R" if metrics["UI"] in ("A", "R", "P") else "UI:N",
            "S:C" if changed_scope else "S:U",
            f"C:{_worst_metric(metrics.get('VC'), metrics.get('SC'))}",
            f"I:{_worst_metric(metrics.get('VI'), metrics.get('SI'))}",
            f"A:{_worst_metric(metrics.get('VA'), metrics.get('SA'))}",
        ]
    )
    return _cvss_v3_base_score(v3_vector)


def _band_from_score(score: float) -> str:
    """Map a CVSS base score to its qualitative severity band."""
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MODERATE"
    return "LOW"


def advisory_severity(raw: dict[str, Any]) -> tuple[str | None, float | None, str]:
    """Grade one raw OSV advisory; return ``(band, cvss_score, source)``.

    Precedence: exact CVSS v3.1 vector score, then the GitHub
    ``database_specific.severity`` string, then the CVSS v4 approximation
    (``cvss_v4_approx`` — band only, score stays ``None``). Unknown bands and
    ungradeable advisories return ``(None, None, "none")``.
    """
    for entry in raw.get("severity") or []:
        if not isinstance(entry, dict) or entry.get("type") != "CVSS_V3":
            continue
        score = _cvss_v3_base_score(str(entry.get("score") or ""))
        if score is not None:
            return _band_from_score(score), score, "cvss_v3"
    db_severity = str((raw.get("database_specific") or {}).get("severity") or "").upper()
    if db_severity in SEVERITY_RANK:
        return ("MODERATE" if db_severity == "MEDIUM" else db_severity), None, "database_specific"
    for entry in raw.get("severity") or []:
        if not isinstance(entry, dict) or entry.get("type") != "CVSS_V4":
            continue
        approx = _cvss_v4_approx_score(str(entry.get("score") or ""))
        if approx is not None:
            return _band_from_score(approx), None, "cvss_v4_approx"
    return None, None, "none"


def _version_key(version: str) -> tuple[tuple[int, Any], ...]:
    """Build a numeric-aware sort key so ``max()`` picks the latest version.

    Each dot/dash/underscore-separated part compares as ``(0, int)`` when
    numeric and ``(1, str)`` otherwise, so ``2.28.10 > 2.28.9`` and calendar
    versions (``2026.01``) beat semver ones in the same range.
    """
    parts = re.split(r"[^0-9A-Za-z]+", version)
    return tuple((0, int(part)) if part.isdigit() else (1, part.lower()) for part in parts if part)


def extract_fixed_version(raw: dict[str, Any]) -> str:
    """Extract the latest fixed version from an advisory's affected ranges.

    SEMVER/ECOSYSTEM ranges carry plain versions in their events; GIT ranges
    carry commit SHAs, but OSV's ``database_specific.extracted_events`` hold
    the human-readable versions (SHA events are skipped). Returns ``""`` when
    no version-shaped fix exists.
    """
    candidates: list[str] = []
    for affected in raw.get("affected") or []:
        if not isinstance(affected, dict):
            continue
        for version_range in affected.get("ranges") or []:
            if not isinstance(version_range, dict):
                continue
            events: Any
            if version_range.get("type") == "GIT":
                events = (version_range.get("database_specific") or {}).get("extracted_events") or version_range.get("events") or []
            else:
                events = version_range.get("events") or []
            for event in events:
                if not isinstance(event, dict):
                    continue
                fixed = str(event.get("fixed") or "")
                if fixed and not _COMMIT_SHA_RE.match(fixed):
                    candidates.append(fixed)
    return max(candidates, key=_version_key) if candidates else ""


def _canonical_key(raw: dict[str, Any]) -> str:
    """Return the dedupe key for one advisory: its CVE alias when present, else the OSV id.

    The same issue often arrives twice from one query (e.g. a ``GHSA-…`` record
    plus its mirrored ``PYSEC-…`` record sharing the CVE alias) — the canonical
    CVE key collapses the duplicates.
    """
    for alias in raw.get("aliases") or []:
        if str(alias).startswith("CVE-"):
            return str(alias)
    return str(raw.get("id") or "")


def _dedup_rank(advisory: dict[str, Any]) -> tuple[int, int, int]:
    """Prefer duplicates that carry a fixed version, a CVSS score and a GHSA id."""
    return (
        1 if advisory.get("fixed_in") else 0,
        1 if advisory.get("cvss_score") is not None else 0,
        1 if str(advisory.get("id") or "").startswith("GHSA-") else 0,
    )


def normalize_advisory(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize one raw OSV advisory; ``None`` when below the HIGH floor.

    Keeps the advisory id (GHSA-/PYSEC-/CVE-…), summary (falling back to the
    first snippet of ``details`` — CVE conversion records often ship an empty
    summary), severity band, exact CVSS score when known, latest fixed version,
    published date and the osv.dev permalink.
    """
    advisory_id = str(raw.get("id") or "")
    if not advisory_id:
        return None
    band, score, source = advisory_severity(raw)
    if band is None or SEVERITY_RANK.get(band, 0) < SEVERITY_RANK[SEVERITY_FLOOR]:
        return None
    summary = str(raw.get("summary") or "").strip()
    if not summary:
        summary = re.sub(r"\s+", " ", str(raw.get("details") or "")).strip()
    return {
        "id": advisory_id,
        "summary": summary[:SUMMARY_MAX_CHARS],
        "severity": band,
        "cvss_score": score,
        "severity_source": source,
        "fixed_in": extract_fixed_version(raw),
        "published": str(raw.get("published") or "")[:10],
        "url": f"https://osv.dev/vulnerability/{advisory_id}",
    }


def normalize_advisories(raw_advisories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter, dedupe, sort and cap one service's raw advisories.

    Dedupes by canonical CVE key (keeping the richest duplicate), sorts newest
    first by published date (id as deterministic tie-break) and caps at
    ``ADVISORIES_PER_SERVICE``.
    """
    by_key: dict[str, dict[str, Any]] = {}
    for raw in raw_advisories:
        if not isinstance(raw, dict):
            continue
        advisory = normalize_advisory(raw)
        if advisory is None:
            continue
        key = _canonical_key(raw)
        current = by_key.get(key)
        if current is None or _dedup_rank(advisory) > _dedup_rank(current):
            by_key[key] = advisory
    ordered = sorted(by_key.values(), key=lambda adv: (adv["published"], adv["id"]), reverse=True)
    return ordered[:ADVISORIES_PER_SERVICE]


@with_retry
def _osv_query_page(package: dict[str, str], page_token: str = "") -> dict[str, Any]:
    """POST one OSV query page, retrying transient network/HTTP errors."""
    payload: dict[str, Any] = {"package": package}
    if page_token:
        payload["page_token"] = page_token
    response = requests.post(OSV_QUERY_URL, json=payload, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_raw_advisories(package: dict[str, str]) -> list[dict[str, Any]]:
    """Fetch every raw advisory for one package, following bounded pagination."""
    vulns: list[dict[str, Any]] = []
    page_token = ""
    for _page in range(MAX_PAGES):
        data = _osv_query_page(package, page_token)
        if not isinstance(data, dict):
            break
        page_vulns = data.get("vulns")
        if isinstance(page_vulns, list):
            vulns.extend(vuln for vuln in page_vulns if isinstance(vuln, dict))
        page_token = str(data.get("next_page_token") or "")
        if not page_token:
            break
    return vulns


def fetch_service_advisories(repo_cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """Fetch and normalize one wired service's advisories; failures return ``([], False)``."""
    key = repo_key(repo_cfg)
    service = OSV_SERVICE_MAP.get(key)
    if not service:
        return [], False
    package = {"name": service["package_name"], "ecosystem": service["ecosystem"]}
    logger.info(f"Querying OSV for {key} as {service['ecosystem']}:{service['package_name']}")
    try:
        raw_advisories = fetch_raw_advisories(package)
    except (requests.RequestException, ValueError) as exc:
        logger.error(f"Could not query OSV for {key}: {exc}")
        return [], False
    advisories = normalize_advisories(raw_advisories)
    logger.info(f"Retrieved {len(raw_advisories)} raw advisories for {key} ({len(advisories)} kept at >= HIGH, capped at {len(advisories)})")
    return advisories, True


def collect_stack_advisories() -> tuple[list[dict[str, Any]], int]:
    """Collect advisories for every wired stack service, in registry order.

    Returns the per-service groups plus the count of services that answered.
    A failing service yields ``advisories: []`` plus a ``fetch_error`` flag
    instead of aborting the run.
    """
    wired = [cfg for cfg in STACK_REPOS if repo_key(cfg) in OSV_SERVICE_MAP]
    services: list[dict[str, Any]] = []
    ok_count = 0
    for index, repo_cfg in enumerate(wired):
        key = repo_key(repo_cfg)
        label = str(repo_cfg.get("label") or key)
        advisories, ok = fetch_service_advisories(repo_cfg)
        if ok:
            ok_count += 1
        else:
            logger.warning(f"OSV query failed for {key} — reported with fetch_error, run continues")
        group: dict[str, Any] = {"repo": key, "service_label": label, "advisories": advisories}
        if not ok:
            group["fetch_error"] = True
        services.append(group)
        if index < len(wired) - 1:
            time.sleep(SERVICE_DELAY_SECONDS)
    logger.info(f"OSV collection: {ok_count}/{len(wired)} wired services answered, {total_advisories(services)} advisories (>= HIGH)")
    return services, ok_count


def total_advisories(services: list[dict[str, Any]]) -> int:
    """Return the total number of advisories across all service groups."""
    return sum(len(group.get("advisories") or []) for group in services if isinstance(group, dict))


def save_stack_advisories(services: list[dict[str, Any]]) -> bool:
    """Persist the OSV envelope under ``data/security/``; return whether files were written.

    Writes ``osv_stack_latest.json`` plus a timestamped snapshot. A run where
    every wired service failed keeps the previous last-good file untouched.
    """
    if services and all(group.get("fetch_error") for group in services):
        logger.warning("Every OSV service query failed — keeping previous latest file")
        return False
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "services": services,
        "total_advisories": total_advisories(services),
    }
    output_dir = os.path.join(get_project_root(), "data", "security")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "osv_stack_latest.json")
    snapshot = os.path.join(output_dir, f"osv_stack_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {payload['total_advisories']} OSV stack advisories across {len(services)} services to {latest}")
    return True


def main() -> None:
    """Run the OSV stack advisories ETL."""
    logger.info("Starting OSV stack advisories ETL")
    try:
        services, ok_count = collect_stack_advisories()
        if save_stack_advisories(services):
            logger.info(f"OSV stack advisories ETL complete: {total_advisories(services)} advisories across {ok_count}/{len(services)} wired services.")
        else:
            logger.warning("OSV stack advisories ETL produced no usable data; previous outputs kept.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"OSV stack advisories ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
