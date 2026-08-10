"""ETL for community AI model leaderboards — scores + pricing.

Aggregates two no-auth, actively-maintained sources into one leaderboard view
for the Benchmarks dashboard tab, providing reliable data given that the other
two sources are currently gated (Artificial Analysis needs a paid API key) or
broken (BridgeBench URL structure changed):

1. **LMArena leaderboard** — fetched from the ``lmarena-ai/arena-leaderboard``
   Hugging Face Space's dated CSV snapshots (no auth). Contains MT-bench and
   MMLU scores for ~340 open/proprietary LLMs.
2. **Community LLM catalog** — fetched from
   ``JonathanChavezTamales/llm-leaderboard`` GitHub repo (no auth). Contains
   per-provider model pricing and capability metadata (context length,
   modalities, throughput/latency), which complements the scores.

Output (under ``data/benchmarks/``):
- ``llm_leaderboard.json`` — aggregate of the latest scores + pricing.
- ``llm_leaderboard_scores.csv`` — the raw LMArena scores snapshot.

Runnable standalone: ``uv run python -m src.etl.benchmarks.llm_leaderboard_etl``
"""

from __future__ import annotations

import csv
import io
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import get_project_root

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# LMArena HF Space — stores dated CSV snapshots (no auth required).
LMARENA_SPACE = "lmarena-ai/arena-leaderboard"
LMARENA_TREE_URL = f"https://huggingface.co/api/spaces/{LMARENA_SPACE}/tree/main"
LMARENA_RESOLVE = f"https://huggingface.co/spaces/{LMARENA_SPACE}/resolve/main"

# Community LLM catalog (pricing/capabilities).
CATALOG_OWNER = "JonathanChavezTamales"
CATALOG_REPO = "llm-leaderboard"
CATALOG_API = f"https://api.github.com/repos/{CATALOG_OWNER}/{CATALOG_REPO}"
CATALOG_RAW = f"https://raw.githubusercontent.com/{CATALOG_OWNER}/{CATALOG_REPO}/main"

REQUEST_TIMEOUT = 20


def get_data_dir() -> Path:
    """Return the ``data/benchmarks`` directory, creating it if needed."""
    data_dir = Path(get_project_root()) / "data" / "benchmarks"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _fetch(url: str, accept: str = "application/json") -> bytes:
    """Fetch raw bytes from ``url``, raising on HTTP error."""
    req = urllib.request.Request(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _fetch_json(url: str) -> Any:
    """Fetch and parse JSON."""
    return json.loads(_fetch(url).decode("utf-8"))


def _latest_lmarena_csv() -> str | None:
    """Return the filename of the latest LMArena leaderboard CSV snapshot.

    The space stores files like ``leaderboard_table_YYYYMMDD.csv``. Returns
    ``None`` if the listing cannot be retrieved.
    """
    try:
        entries = _fetch_json(LMARENA_TREE_URL)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.warning(f"Could not list LMArena space files ({exc}).")
        return None
    if not isinstance(entries, list):
        return None
    csvs = sorted(e["path"].split("/")[-1] for e in entries if isinstance(e, dict) and e.get("path", "").endswith(".csv"))
    return csvs[-1] if csvs else None


def fetch_lmarena_scores() -> tuple[list[dict[str, Any]], str | None]:
    """Fetch the latest LMArena leaderboard scores.

    Returns:
        A tuple of (list of model score dicts, the source CSV filename).
    """
    filename = _latest_lmarena_csv()
    if not filename:
        logger.warning("No LMArena CSV found; returning empty scores.")
        return [], None
    url = f"{LMARENA_RESOLVE}/{filename}"
    logger.info(f"Fetching LMArena scores from {filename}...")
    try:
        raw = _fetch(url, accept="text/csv").decode("utf-8")
    except (urllib.error.URLError, OSError) as exc:
        logger.warning(f"Failed to download {filename}: {exc}")
        return [], filename
    # Persist the raw snapshot for provenance.
    (get_data_dir() / "llm_leaderboard_scores.csv").write_text(raw, encoding="utf-8")

    reader = csv.DictReader(io.StringIO(raw))
    models: list[dict[str, Any]] = []
    for i, row in enumerate(reader, start=1):
        models.append(
            {
                "rank": i,
                "model": row.get("Model", "").strip(),
                "mt_bench": _to_float(row.get("MT-bench (score)")),
                "mmlu": _to_float(row.get("MMLU")),
                "knowledge_cutoff": row.get("Knowledge cutoff date", "").strip(),
                "license": row.get("License", "").strip(),
                "organization": row.get("Organization", "").strip(),
                "link": row.get("Link", "").strip(),
            }
        )
    # Sort by MT-bench descending (best first); re-rank.
    models.sort(key=lambda m: (m["mt_bench"] is not None, m["mt_bench"] or -1), reverse=True)
    for i, m in enumerate(models, start=1):
        m["rank"] = i
    logger.info(f"Parsed {len(models)} LMArena model scores.")
    return models, filename


def _to_float(value: str | None) -> float | None:
    """Best-effort parse of a score string to float."""
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def fetch_pricing_catalog() -> list[dict[str, Any]]:
    """Fetch per-provider model pricing/capability metadata.

    Returns a flat list of model entries across all providers.
    """
    try:
        entries = _fetch_json(f"{CATALOG_API}/contents/data/providers")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.warning(f"Could not list catalog providers ({exc}); skipping pricing.")
        return []
    if not isinstance(entries, list):
        return []

    providers = [e["name"] for e in entries if isinstance(e, dict) and e.get("type") == "dir"]
    logger.info(f"Found {len(providers)} catalog providers.")
    models: list[dict[str, Any]] = []
    for provider in providers:
        url = f"{CATALOG_RAW}/data/providers/{provider}/models.json"
        try:
            data = _fetch_json(url)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            logger.warning(f"Skipping {provider} pricing ({type(exc).__name__}); continuing.")
            continue
        for m in data if isinstance(data, list) else data.get("models", []):
            if not isinstance(m, dict):
                continue
            models.append(
                {
                    "model": m.get("model_name") or m.get("model_id", ""),
                    "provider": provider,
                    "organization": m.get("organization_id", ""),
                    "input_cents_per_million_tokens": m.get("input_cents_per_million_tokens"),
                    "output_cents_per_million_tokens": m.get("output_cents_per_million_tokens"),
                    "max_input_tokens": m.get("max_input_tokens"),
                    "max_output_tokens": m.get("max_output_tokens"),
                    "throughput": m.get("throughput"),
                    "latency": m.get("latency"),
                    "supports_function_calling": m.get("feature_function_calling"),
                    "supports_structured_output": m.get("feature_structured_output"),
                    "supports_web_search": m.get("feature_web_search"),
                    "input_modalities": _modalities(m, "input"),
                    "output_modalities": _modalities(m, "output"),
                }
            )
    logger.info(f"Collected {len(models)} catalog model entries.")
    return models


def _modalities(model: dict[str, Any], direction: str) -> list[str]:
    """Extract the list of supported modalities for an input/output direction."""
    found: list[str] = []
    for modality in ("text", "image", "audio", "video"):
        if model.get(f"{direction}_modality_{modality}"):
            found.append(modality)
    return found


def save_json(data: dict[str, Any], filename: str) -> Path:
    """Write ``data`` to ``data/benchmarks/<filename>`` and return the path."""
    out_path = get_data_dir() / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    counts = " | ".join(f"{k}={len(v)}" for k, v in data.items() if isinstance(v, list))
    logger.info(f"Saved {counts or '?'} to {out_path}")
    return out_path


def run() -> None:
    """Fetch scores + pricing, persist an aggregate leaderboard file."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    logger.info("Starting community LLM leaderboard fetch...")

    scores, scores_source = fetch_lmarena_scores()
    pricing = fetch_pricing_catalog()

    summary = {
        "source": "lmarena-ai/arena-leaderboard + JonathanChavezTamales/llm-leaderboard",
        "source_urls": [
            "https://huggingface.co/spaces/lmarena-ai/arena-leaderboard",
            f"https://github.com/{CATALOG_OWNER}/{CATALOG_REPO}",
        ],
        "fetched_at": fetched_at,
        "scores_source_file": scores_source,
        "scores_count": len(scores),
        "pricing_count": len(pricing),
        "scores": scores,
        "pricing": pricing,
    }
    save_json(summary, "llm_leaderboard.json")
    logger.info(f"Done: {len(scores)} scores, {len(pricing)} pricing entries.")


if __name__ == "__main__":
    run()
