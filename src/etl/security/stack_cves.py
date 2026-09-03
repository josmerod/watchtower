"""Stack CVE matcher — CISA KEV crossed against the self-hosted stack (T-081).

Pure, network-free matching logic that maps the homelab's service registry
(``STACK_REPOS`` from :mod:`src.etl.github.stack_releases_etl`) onto the KEV
records normalized by :mod:`src.etl.security.security_feeds_etl`. A KEV record
matches a stack repo when the KEV product name contains one of the repo's
aliases as a whole, case-insensitive token run — so ``n8n`` matches "n8n" or
"N8N Dashboard" but never "n8nenterprise-unrelated".

The result feeds three consumers:
- the ``stack_matches`` section of ``data/security/security_latest.json``,
- the Security tab's "🧰 Tu stack" card + match list,
- the HIGH alert rules mirrored by :mod:`src.alerts.rules_store`.
"""

import re
from typing import Any

from src.etl.github.stack_releases_etl import STACK_REPOS

# Stack repo key (``owner/repo``, lowercase) -> product-name aliases seen in
# the CISA KEV catalog. Keep tokens specific: generic words ("assistant",
# "farm", "media") would false-positive against unrelated vendors.
VENDOR_ALIASES: dict[str, tuple[str, ...]] = {
    "n8n-io/n8n": ("n8n",),
    "home-assistant/core": ("home assistant", "homeassistant", "hassio", "hass"),
    "immich-app/immich": ("immich",),
    "jellyfin/jellyfin": ("jellyfin",),
    "justarchinet/archisteamfarm": ("archisteamfarm", "archi steam farm"),
    "haveagitgat/tdarr": ("tdarr",),
}


def repo_key(repo_cfg: dict[str, Any]) -> str:
    """Return the lowercase ``owner/repo`` key for one stack registry entry."""
    return f"{repo_cfg.get('owner', '')}/{repo_cfg.get('repo', '')}".lower()


def _tokens(value: str) -> list[str]:
    """Split a product/alias string into lowercase alphanumeric tokens."""
    return [token for token in re.split(r"[^a-z0-9]+", (value or "").lower()) if token]


def _alias_matches(alias: str, product: str) -> bool:
    """Return whether ``alias`` appears in ``product`` as a whole token run.

    Contiguous token-subsequence matching (never substring): "n8n" matches
    "n8n" and "n8n automation" but not "n8nenterprise-unrelated"; "home
    assistant" matches "Home Assistant Container" but not "Assistant".
    """
    alias_tokens = _tokens(alias)
    product_tokens = _tokens(product)
    if not alias_tokens or not product_tokens or len(alias_tokens) > len(product_tokens):
        return False
    return any(product_tokens[i : i + len(alias_tokens)] == alias_tokens for i in range(len(product_tokens) - len(alias_tokens) + 1))


def kev_matches_repo(record: dict[str, Any], repo_cfg: dict[str, Any]) -> bool:
    """Return whether one normalized KEV record's product matches one stack repo."""
    aliases = VENDOR_ALIASES.get(repo_key(repo_cfg), ())
    product = str(record.get("product") or "")
    return bool(product) and any(_alias_matches(alias, product) for alias in aliases)


def match_stack_to_kev(kev_records: list[dict[str, Any]], stack_repos: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Cross KEV records against the stack registry; return per-repo match groups.

    Args:
        kev_records: Normalized ``cisa_kev`` records as persisted by the
            security ETL (each needs ``cve``, ``product``, ``published``,
            ``title`` and ``ransomware_use``; ``fetch_kev`` adds them).
        stack_repos: Stack registry to match against; defaults to ``STACK_REPOS``.

    Returns:
        List of ``{"repo": owner/repo, "service_label": label, "cves": [...]}``
        groups — only repos with at least one match, in registry order; CVEs
        keep the KEV newest-first order and are deduped by CVE id.
    """
    matches: list[dict[str, Any]] = []
    for repo_cfg in stack_repos if stack_repos is not None else STACK_REPOS:
        key = repo_key(repo_cfg)
        if not VENDOR_ALIASES.get(key):
            continue
        label = str(repo_cfg.get("label") or key)
        seen: set[str] = set()
        cves: list[dict[str, Any]] = []
        for record in kev_records:
            cve = str(record.get("cve") or "")
            if not cve or cve in seen:
                continue
            if not kev_matches_repo(record, repo_cfg):
                continue
            seen.add(cve)
            cves.append(
                {
                    "cve": cve,
                    "product": str(record.get("product") or ""),
                    "dateAdded": str(record.get("published") or ""),
                    "title": str(record.get("title") or ""),
                    "ransomware": str(record.get("ransomware_use") or "Unknown"),
                }
            )
        if cves:
            matches.append({"repo": key, "service_label": label, "cves": cves})
    return matches


def total_stack_matches(stack_matches: list[dict[str, Any]]) -> int:
    """Return the total number of (repo, cve) matches across all groups."""
    return sum(len(group.get("cves", [])) for group in stack_matches)
