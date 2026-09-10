"""Mi stack EOL radar ETL — support-cycle awareness via endoflife.date.

Third pillar of stack health on the Tech Radar's "🧮 Mi stack" subtab:
releases (``stack_releases_etl``) + CVEs (``src/etl/security/stack_cves.py``)
+ EOL (this ETL). It asks the keyless, free endoflife.date API which cycles
of the products around the self-hosted stack are still supported, so the
dashboard can badge "plan the upgrade" before a runtime quietly goes EOL.

API note (probed live 2026-09-10): the canonical v1 endpoint is
``GET https://endoflife.date/api/v1/products/{slug}`` (plural, no extension).
The ``api/v1/product/{slug}.json`` shape 404s for every slug; the legacy
``api/{slug}.json`` also works but is superseded. One request per product per
run, paced, keyless.

Slug probe results (2026-09-10, one request each):
- 404 (not tracked — kept in the registry as untracked so the dashboard shows
  an honest "not tracked" badge instead of silence): ``unraid``, ``unraid-os``,
  ``n8n``, ``home-assistant``, ``homeassistant``, ``jellyfin``, ``immich``,
  ``archisteamfarm``, ``tdarr``.
- 200 with real cycle data (wired): ``debian``, ``ubuntu``, ``python`` — the
  runtimes/OSes the homelab actually sits on (containers are Debian/Ubuntu
  based; the dashboard itself is Python 3.10+).

Usage:
    uv run python -m src.etl.github.stack_eol_etl

Output:
    data/stack/eol_{timestamp}.json + eol_latest.json + run_summary_latest.json
"""

import json
import os
import shutil
import time
from datetime import date, datetime, timezone
from typing import Any

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("StackEolETL")

OUTPUT_SUBDIR = "data/stack"
API_BASE = "https://endoflife.date/api/v1/products"
MAX_CYCLES_PER_PRODUCT = 2  # the 2 newest cycles carry the support story
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.0  # courteous pacing between product fetches

# Badge tiers for the dashboard (and anyone else) — thresholds in days.
EOL_CRITICAL_DAYS = 90  # 🔴 EOL within 90 days (or already past)
EOL_WARN_DAYS = 180  # 🟠 EOL within 180 days

# Products whose lifecycle the "🧮 Mi stack" story cares about. ``fetch``
# mirrors the live probe above: the six stack services are NOT covered by
# endoflife.date (404), so they never hit the API — they are still emitted
# with ``tracked: false`` so the tab can render an explicit "not tracked"
# badge. Flip ``fetch`` to True if/when endoflife.date adds coverage.
STACK_EOL_PRODUCTS: list[dict[str, Any]] = [
    # The self-hosted stack itself (labels mirror STACK_REPOS in stack_releases_etl).
    {"product": "n8n", "label": "n8n", "role": "mi_stack", "fetch": False},
    {"product": "home-assistant", "label": "home-assistant", "role": "mi_stack", "fetch": False},
    {"product": "immich", "label": "immich", "role": "mi_stack", "fetch": False},
    {"product": "jellyfin", "label": "jellyfin", "role": "mi_stack", "fetch": False},
    {"product": "archisteamfarm", "label": "ArchiSteamFarm", "role": "mi_stack", "fetch": False},
    {"product": "tdarr", "label": "Tdarr", "role": "mi_stack", "fetch": False},
    # Tracked adjacents: the OS/runtime layer the box depends on.
    {"product": "debian", "label": "Debian", "role": "adjacent", "fetch": True},
    {"product": "ubuntu", "label": "Ubuntu", "role": "adjacent", "fetch": True},
    {"product": "python", "label": "Python", "role": "adjacent", "fetch": True},
]


def product_url(product: str) -> str:
    """Return the endoflife.date v1 URL for one product slug."""
    return f"{API_BASE}/{product}"


@with_retry
def _fetch_product(product: str) -> dict[str, Any]:
    """Fetch one product's v1 payload, retrying transient network/HTTP errors.

    Raises ``requests.HTTPError`` for non-2xx (including 404 — handled by the
    caller) and ``ValueError`` for malformed JSON.
    """
    response = requests.get(product_url(product), headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _today() -> date:
    """Return today's UTC date (EOL dates are dates, not datetimes)."""
    return datetime.now(timezone.utc).date()


def _parse_date(value: Any) -> date | None:
    """Coerce an API date field into a ``date``; None/booleans/garbage → None.

    endoflife.date v1 uses ``YYYY-MM-DD`` strings (the legacy API sometimes
    used ``false`` for "no date"), so anything that is not a parseable string
    is treated as unknown rather than an error.
    """
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_iso_date(value: Any) -> str | None:
    """Normalize an API date field into ``YYYY-MM-DD``; anything not parseable → None."""
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed else None


def days_until(value: Any, now: date) -> int | None:
    """Whole days from ``now`` to a date field; negative = already past."""
    parsed = _parse_date(value)
    return (parsed - now).days if parsed else None


def _normalize_cycle(raw: dict[str, Any], now: date) -> dict[str, Any]:
    """Map one v1 release cycle onto the persisted cycle shape."""
    latest = raw.get("latest") or {}
    eol = parse_iso_date(raw.get("eolFrom"))
    return {
        "cycle": str(raw.get("name") or ""),
        "release_name": str(raw.get("label") or raw.get("name") or ""),
        "release_date": parse_iso_date(raw.get("releaseDate")),
        "latest_release": str(latest.get("name") or ""),
        "latest_release_date": parse_iso_date(latest.get("date")),
        "eol": eol,
        "support": parse_iso_date(raw.get("eoasFrom")),
        "lts_from": parse_iso_date(raw.get("ltsFrom")),
        "is_lts": bool(raw.get("isLts")),
        "is_maintained": bool(raw.get("isMaintained")),
        "days_to_eol": days_until(eol, now) if eol else None,
    }


def _release_sort_key(raw: dict[str, Any]) -> str:
    """Sort key for "newest cycle first"; unknown release dates sort last."""
    parsed = _parse_date(raw.get("releaseDate"))
    return parsed.isoformat() if parsed else ""


def normalize_cycles(releases: list[dict[str, Any]], now: date) -> list[dict[str, Any]]:
    """Keep the MAX_CYCLES_PER_PRODUCT newest cycles, newest first.

    The v1 API already returns releases newest-first; sorting defensively by
    ``releaseDate`` (unknown dates last) keeps the contract true even if the
    ordering ever changes.
    """
    ordered = sorted(releases, key=_release_sort_key, reverse=True)
    return [_normalize_cycle(raw, now) for raw in ordered[:MAX_CYCLES_PER_PRODUCT]]


def nearest_eol(cycles: list[dict[str, Any]], now: date) -> tuple[str | None, int | None]:
    """Pick the most actionable EOL date across a product's kept cycles.

    Preference order: the soonest still-future EOL (upgrade deadline); if
    every kept cycle is already EOL, the most recently passed one (still a
    live "you are past EOL" signal, unlike an ancient date); None when no
    cycle carries a date. Returns ``(iso_date, days_from_now)``.
    """
    dates = [date.fromisoformat(c["eol"]) for c in cycles if c.get("eol")]
    future = [d for d in dates if d >= now]
    target = min(future) if future else (max(dates) if dates else None)
    if target is None:
        return None, None
    return target.isoformat(), (target - now).days


def normalize_product(payload: dict[str, Any], cfg: dict[str, Any], now: date) -> dict[str, Any]:
    """Normalize one product's v1 envelope (``{"result": …}``) to the output shape."""
    result = payload.get("result") or {}
    cycles = normalize_cycles(result.get("releases") or [], now)
    nearest_iso, days = nearest_eol(cycles, now)
    return {
        "product": cfg["product"],
        "label": str(result.get("label") or cfg["label"]),
        "role": cfg.get("role", ""),
        "tracked": True,
        "cycles": cycles,
        "nearest_eol": nearest_iso,
        "days_to_eol": days,
    }


def _untracked_product(cfg: dict[str, Any], error: str | None = None) -> dict[str, Any]:
    """Build the not-tracked record for a registry entry (zero network)."""
    record: dict[str, Any] = {
        "product": cfg["product"],
        "label": cfg["label"],
        "role": cfg.get("role", ""),
        "tracked": False,
        "cycles": [],
        "nearest_eol": None,
        "days_to_eol": None,
    }
    if error:
        record["error"] = error
    return record


def eol_badge(product: dict[str, Any]) -> tuple[str, str]:
    """Map a persisted product record onto its badge tier.

    Returns ``(symbol, tier)`` with tier one of ``critical`` (red, EOL within
    90 days or past), ``expiring`` (orange, within 180 days), ``ok`` (white,
    fine or no date) and ``untracked`` (dash, endoflife.date does not cover
    the product).
    """
    if not product.get("tracked"):
        return "➖", "untracked"
    days = product.get("days_to_eol")
    if days is None:
        return "⚪", "ok"
    if days < EOL_CRITICAL_DAYS:
        return "🔴", "critical"
    if days < EOL_WARN_DAYS:
        return "🟠", "expiring"
    return "⚪", "ok"


def fetch_stack_eol(now: date | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch every fetchable registry product; return records plus run stats.

    Resilient per product: a network failure, a 404 (product dropped by
    endoflife.date) or malformed JSON degrades that one product to a
    no-cycles record and never aborts the run. Registry entries marked
    ``fetch: False`` are emitted as untracked without touching the network.
    """
    today = now or _today()
    products: list[dict[str, Any]] = []
    fetchable = [cfg for cfg in STACK_EOL_PRODUCTS if cfg.get("fetch")]
    stats: dict[str, Any] = {
        "products_total": len(STACK_EOL_PRODUCTS),
        "products_tracked_expected": len(fetchable),
        "products_ok": 0,
        "errors": {},
    }
    for index, cfg in enumerate(STACK_EOL_PRODUCTS):
        if not cfg.get("fetch"):
            products.append(_untracked_product(cfg))
            continue
        logger.info(f"Fetching EOL cycles for {cfg['product']}")
        try:
            payload = _fetch_product(cfg["product"])
            record = normalize_product(payload, cfg, today)
            products.append(record)
            if record["cycles"]:
                stats["products_ok"] += 1
        except requests.HTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 404:
                logger.warning(f"{cfg['product']} is no longer tracked by endoflife.date")
                products.append(_untracked_product(cfg, error="not tracked by endoflife.date"))
            else:
                logger.error(f"HTTP {status} fetching {cfg['product']}: {exc}")
                products.append({**_untracked_product(cfg), "tracked": True, "error": f"HTTP {status}"})
            stats["errors"][cfg["product"]] = str(exc)
        except (requests.RequestException, ValueError) as exc:
            logger.error(f"Could not fetch {cfg['product']}: {exc}")
            products.append({**_untracked_product(cfg), "tracked": True, "error": str(exc)})
            stats["errors"][cfg["product"]] = str(exc)
        if index < len(STACK_EOL_PRODUCTS) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)
    logger.info(f"EOL radar: {stats['products_ok']}/{stats['products_tracked_expected']} tracked products answered")
    return products, stats


def save_stack_eol(products: list[dict[str, Any]], stats: dict[str, Any], start_time: datetime | None = None) -> bool:
    """Persist the EOL envelope under ``data/stack/``; return whether files were written.

    Writes a timestamped snapshot, ``eol_latest.json`` and a
    ``run_summary_latest.json`` with the fields other ETLs expose. Graceful
    failure: when less than half of the fetchable products answered, the
    previous last-good ``eol_latest.json`` is kept untouched (mirrors
    ``stack_releases_etl``).
    """
    if stats.get("products_ok", 0) < (stats.get("products_tracked_expected", 0) + 1) // 2:
        logger.warning(f"Partial run ({stats.get('products_ok', 0)}/{stats.get('products_tracked_expected', 0)} products) — keeping previous latest file")
        return False

    output_dir = os.path.join(get_project_root(), OUTPUT_SUBDIR)
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    envelope = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "endoflife.date",
        "products": products,
    }

    snapshot_file = os.path.join(output_dir, f"eol_{timestamp}.json")
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2, ensure_ascii=False)

    latest_file = os.path.join(output_dir, "eol_latest.json")
    shutil.copy2(snapshot_file, latest_file)

    end_time = datetime.now(timezone.utc)
    started = start_time or end_time
    run_summary = {
        "etl_name": "stack_eol",
        "start_time": started.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": (end_time - started).total_seconds(),
        "records_extracted": len(products),
        "records_transformed": len(products),
        "records_loaded": len(products),
        "records_failed": len(stats.get("errors", {})),
        "error_count": len(stats.get("errors", {})),
        "success": True,
        "products_total": stats.get("products_total", 0),
        "products_tracked_expected": stats.get("products_tracked_expected", 0),
        "products_ok": stats.get("products_ok", 0),
        "errors": stats.get("errors", {}),
        "output_dir": output_dir,
    }
    with open(os.path.join(output_dir, "run_summary_latest.json"), "w", encoding="utf-8") as f:
        json.dump(run_summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(products)} product EOL records to {latest_file}")
    return True


def main() -> None:
    """Run the mi-stack EOL cycles ETL."""
    logger.info("Starting mi-stack EOL cycles ETL")
    start_time = datetime.now(timezone.utc)
    try:
        products, stats = fetch_stack_eol()
        if save_stack_eol(products, stats, start_time=start_time):
            logger.info(f"Mi-stack EOL ETL complete: {stats['products_ok']}/{stats['products_tracked_expected']} tracked products answered.")
        else:
            logger.warning("Mi-stack EOL ETL produced no usable data; previous outputs kept.")
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Mi-stack EOL ETL failed: {exc}")
        raise

    # Notifications rules: products EOL-ing within the alert horizon (T-092).
    # Best-effort — alert wiring must never fail the data pipeline.
    try:
        from src.alerts.rules_store import sync_stack_eol_rules

        counts = sync_stack_eol_rules(products)
        if counts["created"] or counts["updated"] or counts["resolved"]:
            logger.info(f"Stack EOL alert rules synced: {counts}")
    except Exception as exc:  # broad by design: alert wiring must never fail the ETL
        logger.warning(f"Could not sync stack EOL alert rules: {exc}")


if __name__ == "__main__":
    main()
