"""ETL for the OpenRouter model catalog — powers the "New Models" feed.

Fetches the keyless public listing at ``https://openrouter.ai/api/v1/models``
(no API key needed) and turns it into a normalized catalog plus a "new models"
diff against the previous runs:

- Every model record carries id, name, creation date (unix + ISO), context
  length, per-Mtok USD prompt/completion prices (converted from OpenRouter's
  per-token price strings) and provider/modality metadata.
- ``data/benchmarks/openrouter_seen_models.json`` keeps a map of
  ``model id -> first_seen ISO date``. On each run, ids missing from that map
  get ``first_seen = now`` and surface in ``new_models`` (capped at the 30
  newest, newest first); the map is then upserted.
- **Baseline behaviour: the FIRST run ever (empty/absent seen-map) marks the
  whole current catalog as seen and reports an empty ``new_models`` list.**
  New models only start appearing from the second run onwards.

Output (under ``data/benchmarks/``):
- ``openrouter_models_latest.json`` — full snapshot + new-model diff.
- ``openrouter_models_<timestamp>.json`` — timestamped copy.
- ``openrouter_seen_models.json`` — id -> first_seen map (diff state).

Failure policy: when the fetch fails after retries the existing files are left
untouched (last-good data wins), and the seen-map is only upserted after the
snapshot has been persisted successfully.

Runnable standalone: ``uv run python -m src.etl.benchmarks.openrouter_models_etl``
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import get_project_root
from src.utils.retry import with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OUTPUT_LATEST = "openrouter_models_latest.json"
SEEN_MAP_FILE = "openrouter_seen_models.json"
REQUEST_TIMEOUT = 30
NEW_MODELS_CAP = 30


def get_data_dir() -> Path:
    """Return the ``data/benchmarks`` directory, creating it if needed."""
    data_dir = Path(get_project_root()) / "data" / "benchmarks"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@with_retry
def _fetch_raw() -> dict[str, Any]:
    """Fetch the raw catalog JSON (retried on transient errors by ``with_retry``)."""
    response = requests.get(OPENROUTER_MODELS_URL, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT, "Accept": "application/json"}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_models_catalog() -> list[dict[str, Any]] | None:
    """Fetch the OpenRouter model catalog.

    Returns:
        The raw ``data`` list of model records, or ``None`` on any failure
        (logged, never raised).
    """
    try:
        body = _fetch_raw()
    except Exception as e:  # broad by design: fetch seam is patchable; contract is "never raise" (see test_failure_returns_none)
        logger.error(f"OpenRouter catalog fetch failed: {type(e).__name__}: {e}")
        return None
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, list) or not data:
        logger.warning(f"OpenRouter catalog response had no usable data (keys={sorted(body) if isinstance(body, dict) else type(body).__name__}).")
        return None
    logger.info(f"Fetched OpenRouter catalog: {len(data)} models.")
    return data


def parse_price_per_mtok(value: Any) -> float | None:
    """Convert an OpenRouter per-token price string to USD per 1M tokens.

    OpenRouter prices are strings like ``"0.000000834"`` (USD per single
    token). ``"0"`` maps to ``0.0`` (free); missing/invalid/negative values
    map to ``None`` (OpenRouter emits a few negative placeholder prices that
    carry no display meaning).
    """
    if value is None:
        return None
    try:
        per_token = float(str(value).strip())
    except (ValueError, TypeError):
        return None
    if per_token < 0:
        return None
    return round(per_token * 1_000_000, 6)


def _provider_of(model_id: str, name: str) -> str | None:
    """Derive the provider/author slug from the model id or display name."""
    if "/" in model_id:
        return model_id.split("/", 1)[0]
    if ":" in name:
        return name.split(":", 1)[0].strip()
    return None


def parse_model(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a raw OpenRouter model record into the persisted schema.

    Returns:
        The normalized dict, or ``None`` when the record has no usable id.
    """
    model_id = str(raw.get("id") or "").strip()
    if not model_id:
        return None
    name = str(raw.get("name") or model_id)
    created = raw.get("created")
    try:
        created = int(created) if created is not None else None
    except (ValueError, TypeError):
        created = None
    raw_architecture = raw.get("architecture")
    architecture = raw_architecture if isinstance(raw_architecture, dict) else {}
    raw_pricing = raw.get("pricing")
    pricing = raw_pricing if isinstance(raw_pricing, dict) else {}
    return {
        "id": model_id,
        "name": name,
        "created": created,
        "created_iso": datetime.fromtimestamp(created, tz=timezone.utc).isoformat() if created is not None else None,
        "context_length": raw.get("context_length"),
        "prompt_price_per_mtok": parse_price_per_mtok(pricing.get("prompt")),
        "completion_price_per_mtok": parse_price_per_mtok(pricing.get("completion")),
        "provider": _provider_of(model_id, name),
        "modality": architecture.get("modality"),
        "input_modalities": architecture.get("input_modalities") or [],
        "output_modalities": architecture.get("output_modalities") or [],
        "tokenizer": architecture.get("tokenizer"),
    }


def load_seen_map() -> dict[str, str]:
    """Load the id -> first_seen map, tolerating a missing/corrupt file."""
    path = get_data_dir() / SEEN_MAP_FILE
    if not path.exists():
        return {}
    try:
        seen = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Could not read seen-map ({e}); treating as first run.")
        return {}
    return {str(k): str(v) for k, v in seen.items()} if isinstance(seen, dict) else {}


def diff_new_models(models: list[dict[str, Any]], seen: dict[str, str], now_iso: str) -> dict[str, Any]:
    """Diff the catalog against the seen-map and produce the new-models feed.

    Args:
        models: Normalized model records (id field required).
        seen: Current ``id -> first_seen ISO`` map (empty = first run ever).
        now_iso: Timestamp to stamp on newly discovered ids.

    Returns:
        ``{"is_baseline", "new_models", "seen_map", "tracked_since"}`` where
        ``new_models`` is capped at ``NEW_MODELS_CAP`` entries, newest first
        (by model creation date), each carrying a ``first_seen`` field.
    """
    is_baseline = not seen
    unseen = [m for m in models if m["id"] not in seen]
    unseen.sort(key=lambda m: m.get("created") or 0, reverse=True)

    new_models: list[dict[str, Any]] = []
    if not is_baseline:
        new_models = [{**m, "first_seen": now_iso} for m in unseen[:NEW_MODELS_CAP]]
        if len(unseen) > NEW_MODELS_CAP:
            logger.info(f"{len(unseen)} new models discovered; capping feed at {NEW_MODELS_CAP}.")

    updated_seen = dict(seen)
    stamp = now_iso if is_baseline else None
    for m in unseen:
        updated_seen[m["id"]] = stamp or now_iso
    tracked_since = min(updated_seen.values()) if updated_seen else now_iso

    return {"is_baseline": is_baseline, "new_models": new_models, "seen_map": updated_seen, "tracked_since": tracked_since}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` as pretty JSON to ``path``."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def save_json(data: dict[str, Any], filename: str) -> Path:
    """Write ``data`` to ``data/benchmarks/<filename>`` and return the path."""
    out_path = get_data_dir() / filename
    _write_json(out_path, data)
    logger.info(f"Saved {filename} to {out_path}")
    return out_path


def run() -> None:
    """Fetch the OpenRouter catalog and persist snapshot + new-model diff.

    On failure the previous outputs are kept untouched (last-good wins) and
    the seen-map is not modified.
    """
    logger.info("Starting OpenRouter models catalog fetch...")
    raw = fetch_models_catalog()
    if not raw:
        logger.warning("No OpenRouter catalog fetched — keeping existing files untouched.")
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    models = sorted((parsed for parsed in (parse_model(r) for r in raw) if parsed), key=lambda m: m.get("created") or 0, reverse=True)
    if not models:
        logger.warning("OpenRouter catalog parsed to zero models — keeping existing files untouched.")
        return

    diff = diff_new_models(models, load_seen_map(), now_iso)

    output = {
        "source": "openrouter.ai",
        "source_url": OPENROUTER_MODELS_URL,
        "generated_at": now_iso,
        "total_models": len(models),
        "tracked_since": diff["tracked_since"],
        "new_models_count": len(diff["new_models"]),
        "is_baseline_run": diff["is_baseline"],
        "new_models": diff["new_models"],
        "models": models,
    }
    save_json(output, OUTPUT_LATEST)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_json(output, f"openrouter_models_{timestamp}.json")

    # Upsert the seen-map only after the snapshot has been persisted.
    save_json(diff["seen_map"], SEEN_MAP_FILE)
    logger.info(f"Done: {len(models)} models, {len(diff['new_models'])} new (baseline={diff['is_baseline']}).")


if __name__ == "__main__":
    run()
