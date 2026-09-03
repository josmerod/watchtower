"""Shared alert-rule store over ``data/alerts/rules.json``.

The Notifications tab reads its rules from the flat ``data/alerts/rules.json``
list (via ``AlertRulesRepository``), while :class:`src.alerts.engine.AlertEngine`
keeps its own per-user copies. This module gives watchers and other producers a
small, dependency-free API against that shared file:

* :func:`upsert_rule` — insert or update a rule by ``id`` (idempotent).
* :func:`resolve_rule` — remove a rule by ``id`` (the tab's ``delete_rule``
  semantics; a resolved alert disappears from the Notifications list).
* :func:`sync_freshness_rules` — map a DataFreshnessWatcher summary onto rules:
  stale/critical sources get a rule (critical→high, stale→medium), sources back
  to ``fresh`` get their rule resolved.
* :func:`sync_stack_cve_rules` — map the security ETL's stack matches onto
  rules: every CISA KEV CVE hitting a self-hosted stack service gets a HIGH
  rule; matches that aged out of the KEV window get resolved (T-081).

Rules managed by the freshness sync are namespaced with
``FRESHNESS_RULE_PREFIX`` and stack-CVE rules with ``STACK_CVE_RULE_PREFIX``,
so manually-created user rules are never touched.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.file_system import get_project_root
from src.utils.logging import get_logger

logger = get_logger("AlertRulesStore")

# Stable id prefix for watcher-managed freshness rules (never collide with user rules).
FRESHNESS_RULE_PREFIX = "data_freshness_"

# Stable id prefix for security-ETL-managed stack CVE rules (T-081) — KEV
# entries actively exploited that hit one of the self-hosted stack services.
STACK_CVE_RULE_PREFIX = "stack_cve_"

# Freshness status -> alert severity (warn-level "stale" -> medium, "critical" -> high).
SEVERITY_BY_FRESHNESS: dict[str, str] = {"stale": "medium", "critical": "high"}

# Fields whose change turns an upsert into an update (bookkeeping fields excluded
# so repeated checks with unchanged freshness leave the rule byte-identical).
_PAYLOAD_FIELDS = ("name", "description", "severity", "status", "source_key", "age_hours")


def default_rules_file() -> Path:
    """Return the shared rules file path under the project's ``data/`` dir."""
    return Path(get_project_root()) / "data" / "alerts" / "rules.json"


def load_rules(rules_file: Path | None = None) -> list[dict[str, Any]]:
    """Load all rules from the shared store.

    Args:
        rules_file: Explicit store path; defaults to ``data/alerts/rules.json``.

    Returns:
        The list of rule dicts (empty when the store is missing, unreadable, or
        holds a non-list payload — a lone dict is wrapped, mirroring the tab's
        ``AlertRulesRepository.transform_data``).
    """
    path = rules_file or default_rules_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Cannot read alert rules from {path}: {e}")
        return []
    if isinstance(data, dict):
        data = [data]
    return data if isinstance(data, list) else []


def save_rules(rules: list[dict[str, Any]], rules_file: Path | None = None) -> bool:
    """Persist the full rule list back to the shared store.

    Args:
        rules: Complete list of rule dicts to write.
        rules_file: Explicit store path; defaults to ``data/alerts/rules.json``.

    Returns:
        ``True`` on success, ``False`` if the write failed.
    """
    path = rules_file or default_rules_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rules, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return True
    except OSError as e:
        logger.error(f"Cannot write alert rules to {path}: {e}")
        return False


def freshness_rule_id(source_key: str) -> str:
    """Return the stable rule id for a freshness source key."""
    return f"{FRESHNESS_RULE_PREFIX}{source_key}"


def build_freshness_rule(record: dict[str, Any], now: float | None = None) -> dict[str, Any]:
    """Build the alert-rule dict for a stale/critical freshness record.

    Args:
        record: One entry of the freshness summary's ``sources`` list.
        now: Epoch used to derive the last-data timestamp from ``age_hours``
            (defaults to the current time).

    Returns:
        Rule dict with a stable id, severity mapped from the freshness status,
        and a Spanish message: ``Fuente {label} sin datos desde {timestamp} ({hours}h)``.
    """
    now = time.time() if now is None else now
    name = str(record.get("label") or record.get("key") or "desconocida")
    age_hours = record.get("age_hours")
    if age_hours is None:
        message = f"Fuente {name} sin datos (archivo ausente)"
    else:
        last_data_at = datetime.fromtimestamp(now - age_hours * 3600, tz=timezone.utc)
        message = f"Fuente {name} sin datos desde {last_data_at:%Y-%m-%d %H:%M} UTC ({age_hours:g}h)"
    return {
        "id": freshness_rule_id(str(record["key"])),
        "name": f"Freshness: {name}",
        "description": message,
        "severity": SEVERITY_BY_FRESHNESS.get(str(record.get("status")), "medium"),
        "status": record.get("status"),
        "source": "data_freshness",
        "source_key": record.get("key"),
        "age_hours": age_hours,
        "active": True,
        "auto_managed": True,
    }


def upsert_rule(rule: dict[str, Any], rules_file: Path | None = None) -> str:
    """Insert or update a rule by ``id`` — never duplicates.

    Args:
        rule: Rule dict keyed by its ``id``.
        rules_file: Explicit store path; defaults to ``data/alerts/rules.json``.

    Returns:
        One of ``"created"``, ``"updated"`` (payload changed), or
        ``"unchanged"`` (identical payload — file left untouched, keeping the
        operation idempotent across repeated checks).
    """
    rules = load_rules(rules_file)
    now_iso = datetime.now(timezone.utc).isoformat()
    index = next((i for i, r in enumerate(rules) if isinstance(r, dict) and r.get("id") == rule.get("id")), None)

    if index is None:
        rules.append({**rule, "created_at": now_iso, "updated_at": now_iso})
        save_rules(rules, rules_file)
        return "created"

    existing = rules[index]
    if all(existing.get(field) == rule.get(field) for field in _PAYLOAD_FIELDS):
        return "unchanged"

    rules[index] = {**rule, "created_at": existing.get("created_at", now_iso), "updated_at": now_iso}
    save_rules(rules, rules_file)
    return "updated"


def resolve_rule(rule_id: str, rules_file: Path | None = None) -> bool:
    """Remove a rule by ``id`` from the shared store.

    Args:
        rule_id: Id of the rule to clear.
        rules_file: Explicit store path; defaults to ``data/alerts/rules.json``.

    Returns:
        ``True`` if the rule was present and removed, ``False`` otherwise.
    """
    rules = load_rules(rules_file)
    remaining = [r for r in rules if not (isinstance(r, dict) and r.get("id") == rule_id)]
    if len(remaining) == len(rules):
        return False
    save_rules(remaining, rules_file)
    return True


def sync_freshness_rules(summary: dict[str, Any], rules_file: Path | None = None, now: float | None = None) -> dict[str, int]:
    """Sync a freshness summary onto the shared alert-rule store.

    For every source in the summary: ``stale``/``critical`` sources get their
    rule upserted (idempotent, keyed by ``data_freshness_{key}``); sources back
    to ``fresh`` get their rule resolved (removed). Rules for sources no longer
    in the registry are also cleaned up. Manually-created rules are untouched.

    Args:
        summary: Freshness summary dict (``sources`` list of records).
        rules_file: Explicit store path; defaults to ``data/alerts/rules.json``.
        now: Epoch used for message timestamps (defaults to the current time).

    Returns:
        Counts dict: ``created`` / ``updated`` / ``unchanged`` / ``resolved``.
    """
    counts = {"created": 0, "updated": 0, "unchanged": 0, "resolved": 0}
    managed_ids = {freshness_rule_id(str(r["key"])) for r in summary.get("sources", []) if "key" in r}

    for record in summary.get("sources", []):
        if "key" not in record:
            continue
        rule_id = freshness_rule_id(str(record["key"]))
        if record.get("status") in SEVERITY_BY_FRESHNESS:
            counts[upsert_rule(build_freshness_rule(record, now=now), rules_file=rules_file)] += 1
        elif resolve_rule(rule_id, rules_file=rules_file):
            counts["resolved"] += 1

    # Drop rules for sources removed from the registry (keys vanish from SOURCE_FILES).
    for rule in load_rules(rules_file):
        if isinstance(rule, dict) and str(rule.get("id", "")).startswith(FRESHNESS_RULE_PREFIX) and rule.get("id") not in managed_ids:
            if resolve_rule(str(rule["id"]), rules_file=rules_file):
                counts["resolved"] += 1

    return counts


def stack_cve_rule_id(repo_key: str, cve: str) -> str:
    """Return the stable rule id for one (stack repo, CVE) pair.

    The repo key (``owner/repo``) is slugified (``/`` and other unsupported
    characters become ``_``) and the CVE lowercased, so ids stay byte-stable
    across ETL runs regardless of upstream casing drift.
    """
    slug = re.sub(r"[^a-z0-9_-]+", "_", repo_key.lower().strip())
    return f"{STACK_CVE_RULE_PREFIX}{slug}_{cve.strip().lower()}"


def build_stack_cve_rule(repo_key: str, service_label: str, cve: str, product: str = "", date_added: str = "", ransomware: str = "") -> dict[str, Any]:
    """Build the HIGH alert rule for a KEV CVE hitting one stack service.

    Args:
        repo_key: Stack repo key (``owner/repo``, lowercase).
        service_label: Human label from the stack registry (e.g. ``home-assistant``).
        cve: CVE id (e.g. ``CVE-2026-1234``).
        product: KEV product name that triggered the match.
        date_added: KEV ``dateAdded`` for the entry.
        ransomware: KEV ransomware-campaign use (``Known``/``Unknown``).

    Returns:
        Rule dict with a stable ``stack_cve_{repo}_{cve}`` id, ``high``
        severity, and a Spanish message: ``CVE {cve} explotado activamente
        afecta a {service}``.
    """
    return {
        "id": stack_cve_rule_id(repo_key, cve),
        "name": f"Stack CVE: {service_label}",
        "description": f"CVE {cve} explotado activamente afecta a {service_label}",
        "severity": "high",
        "status": "known-exploited",
        "source": "stack_cves",
        "source_key": repo_key,
        "cve": cve,
        "product": product,
        "date_added": date_added,
        "ransomware": ransomware,
        "active": True,
        "auto_managed": True,
    }


def sync_stack_cve_rules(stack_matches: list[dict[str, Any]], rules_file: Path | None = None) -> dict[str, int]:
    """Sync stack-matching KEV CVEs onto the shared alert-rule store.

    Every current ``(repo, cve)`` match gets its HIGH rule upserted
    (idempotent, keyed by ``stack_cve_{repo}_{cve}``); matches that dropped
    out of the KEV window get their rule resolved (removed). Manually-created
    and freshness rules are untouched — cleanup only touches the
    ``stack_cve_`` namespace.

    Args:
        stack_matches: Match groups from
            :func:`src.etl.security.stack_cves.match_stack_to_kev`
            (``{"repo", "service_label", "cves": [...]}``).
        rules_file: Alert-rule store to write (defaults to ``data/alerts/rules.json``).

    Returns:
        Counts dict: ``created`` / ``updated`` / ``unchanged`` / ``resolved``.
    """
    counts = {"created": 0, "updated": 0, "unchanged": 0, "resolved": 0}
    managed_ids: set[str] = set()

    for group in stack_matches:
        repo_key = str(group.get("repo") or "")
        label = str(group.get("service_label") or repo_key)
        cves = group.get("cves")
        if not repo_key or not isinstance(cves, list):
            continue
        for cve_entry in cves:
            cve = str(cve_entry.get("cve") or "") if isinstance(cve_entry, dict) else ""
            if not cve:
                continue
            rule = build_stack_cve_rule(
                repo_key,
                label,
                cve,
                product=str(cve_entry.get("product") or ""),
                date_added=str(cve_entry.get("dateAdded") or ""),
                ransomware=str(cve_entry.get("ransomware") or ""),
            )
            managed_ids.add(str(rule["id"]))
            counts[upsert_rule(rule, rules_file=rules_file)] += 1

    # CVEs aged out of the KEV window (no longer matched) get their rule resolved.
    for rule in load_rules(rules_file):
        if isinstance(rule, dict) and str(rule.get("id", "")).startswith(STACK_CVE_RULE_PREFIX) and rule.get("id") not in managed_ids:
            if resolve_rule(str(rule["id"]), rules_file=rules_file):
                counts["resolved"] += 1

    return counts
