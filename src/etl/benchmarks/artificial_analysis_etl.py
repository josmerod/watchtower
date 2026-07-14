"""ETL for Artificial Analysis — comprehensive AI model benchmarks.

Fetches model data from the Artificial Analysis API (https://artificialanalysis.ai/)
and saves as JSON. Covers LLM benchmarks and image model arena ratings.

Runnable standalone: python -m src.etl.benchmarks.artificial_analysis_etl

API key: set ARTIFICIAL_ANALYSIS_API_KEY env var, or place in .env file.
Free tier: 1000 requests/day.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

API_BASE = "https://artificialanalysis.ai/api/v2/data"

ENDPOINTS = {
    "llm": "/llms/models",
    "text-to-image": "/text-to-image/models",
    "image-editing": "/image-editing/models",
    "text-to-speech": "/text-to-speech/models",
    "text-to-video": "/text-to-video/models",
    "image-to-video": "/image-to-video/models",
}

# Which endpoints produce benchmark-style data we care about
PRIMARY_ENDPOINTS = {"llm", "text-to-image"}


def get_api_key() -> str | None:
    """Get the Artificial Analysis API key from env or config files."""
    # 1. Environment variable (highest priority)
    key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY")
    if key:
        return key

    # 2. .env files in project root
    for env_file in [".env", ".env.local"]:
        env_path = Path(__file__).resolve().parents[4] / env_file
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("ARTIFICIAL_ANALYSIS_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip("\"'")
                    if val:
                        return val

    return None


def get_data_dir() -> str:
    """Get the data/benchmarks directory path."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "data",
        "benchmarks",
    )


def fetch_json(url: str, api_key: str | None = None) -> list[dict] | dict | None:
    """Fetch JSON data from the Artificial Analysis API."""
    headers = {
        "User-Agent": "Watchtower/1.0 (https://github.com/josele)",
        "Accept": "application/json",
    }
    if api_key:
        headers["x-api-key"] = api_key

    logger.info(f"Fetching {url}...")
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data
    except urllib.error.HTTPError as e:
        if e.code == 401:
            logger.error("Authentication failed — invalid or missing API key. Set ARTIFICIAL_ANALYSIS_API_KEY env var.")
        elif e.code == 429:
            logger.error("Rate limited — too many requests. Try again later.")
        else:
            logger.error(f"HTTP {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"Connection error: {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        import traceback

        traceback.print_exc()
        return None


def normalize_llm_models(models: list[dict]) -> list[dict]:
    """Normalize LLM model data into a clean, consistent format."""
    normalized = []

    for m in models:
        # Flatten creator info
        creator = m.get("model_creator") or {}
        creator_name = creator.get("name", "") if isinstance(creator, dict) else str(creator)

        # Flatten evaluations
        evals = m.get("evaluations") or {}
        if not isinstance(evals, dict):
            evals = {}

        # Flatten pricing
        pricing = m.get("pricing") or {}
        if not isinstance(pricing, dict):
            pricing = {}

        entry = {
            "id": m.get("id", ""),
            "name": m.get("name", ""),
            "slug": m.get("slug", ""),
            "creator": creator_name,
            "open_weights": m.get("openWeights", False),
            # Benchmark scores
            "intelligence_index": evals.get("intelligenceIndex"),
            "coding_index": evals.get("codingIndex"),
            "math_index": evals.get("mathIndex"),
            "mmlu_pro": evals.get("mmluPro"),
            "gpqa": evals.get("gpqa"),
            "hle": evals.get("hle"),
            "livecodebench": evals.get("livecodebench"),
            "scicode": evals.get("scicode"),
            "math_500": evals.get("math500"),
            "aime": evals.get("aime"),
            # Performance metrics
            "median_output_tps": m.get("medianOutputTokensPerSecond"),
            "median_ttft": m.get("medianTimeToFirstTokenSeconds"),
            # Pricing
            "price_input_per_1m": pricing.get("price1mInputTokens"),
            "price_output_per_1m": pricing.get("price1mOutputTokens"),
            "price_blended_3_to_1": pricing.get("price1mBlended3to1"),
            # Context window
            "context_length": m.get("contextLength"),
        }
        normalized.append(entry)

    # Sort by intelligence_index descending (best first)
    normalized.sort(
        key=lambda x: x.get("intelligence_index") or float("-inf"),
        reverse=True,
    )
    return normalized


def normalize_image_models(models: list[dict]) -> list[dict]:
    """Normalize image model arena data (ELO ratings)."""
    normalized = []

    for m in models:
        entry = {
            "id": m.get("id", ""),
            "name": m.get("name", ""),
            "slug": m.get("slug", ""),
            "creator": (m.get("model_creator") or {}).get("name", "") if isinstance(m.get("model_creator"), dict) else "",
            "open_weights": m.get("openWeights", False),
            "arena_elo": m.get("arenaElo"),
            "arena_votes": m.get("arenaVotes"),
            "quality_ranking": m.get("qualityRanking"),
            "quality_votes": m.get("qualityVotes"),
            "alignment_ranking": m.get("alignmentRanking"),
            "alignment_votes": m.get("alignmentVotes"),
            # Pricing
            "price_per_image": (m.get("pricing") or {}).get("pricePerImage"),
        }
        normalized.append(entry)

    # Sort by arena ELO descending
    normalized.sort(
        key=lambda x: x.get("arena_elo") or float("-inf"),
        reverse=True,
    )
    return normalized


def save_json(data: list[dict], filepath: str, source: str, endpoint: str):
    """Save data as JSON with metadata."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    output = {
        "source": "artificialanalysis.ai",
        "endpoint": endpoint,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(data),
        "models": data,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data)} models to {filepath}")


def run_endpoint(endpoint_key: str, api_key: str | None = None) -> bool:
    """Fetch and save data for a single endpoint. Returns True on success."""
    path = ENDPOINTS.get(endpoint_key)
    if not path:
        logger.warning(f"Unknown endpoint: {endpoint_key}")
        return False

    url = f"{API_BASE}{path}"
    data = fetch_json(url, api_key)

    if data is None:
        return False

    if not isinstance(data, list):
        logger.warning(f"Expected list from {url}, got {type(data).__name__}")
        return False

    if not data:
        logger.warning(f"No models returned from {url}")
        return False

    data_dir = get_data_dir()

    if endpoint_key == "llm":
        normalized = normalize_llm_models(data)
        filepath = os.path.join(data_dir, "artificial_analysis_llms.json")
        save_json(normalized, filepath, "artificialanalysis.ai", endpoint_key)
        return True

    elif endpoint_key == "text-to-image":
        normalized = normalize_image_models(data)
        filepath = os.path.join(data_dir, "artificial_analysis_image.json")
        save_json(normalized, filepath, "artificialanalysis.ai", endpoint_key)
        return True

    else:
        # Other endpoints — save raw with minimal normalization
        filepath = os.path.join(data_dir, f"artificial_analysis_{endpoint_key.replace('-', '_')}.json")
        save_json(data, filepath, "artificialanalysis.ai", endpoint_key)
        return True


def run(endpoints: list[str] | None = None):
    """Main ETL runner.

    Args:
        endpoints: List of endpoint keys to fetch. None = all primary endpoints.
    """
    api_key = get_api_key()
    if not api_key:
        logger.warning("No ARTIFICIAL_ANALYSIS_API_KEY found. The API may work without a key for limited access, but setting the key is recommended. Get one free at https://artificialanalysis.ai/")

    if endpoints is None:
        endpoints = list(PRIMARY_ENDPOINTS)

    logger.info(f"Running Artificial Analysis ETL for: {endpoints}")
    results = {}

    for ep in endpoints:
        success = run_endpoint(ep, api_key)
        results[ep] = "success" if success else "failed"

    # Summary
    ok = sum(1 for v in results.values() if v == "success")
    fail = sum(1 for v in results.values() if v == "failed")
    logger.info(f"Artificial Analysis ETL complete: {ok} succeeded, {fail} failed")

    return results


if __name__ == "__main__":
    run()
