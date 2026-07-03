---
name: etl-pipeline
description: Build a new Watchtower ETL pipeline the standard way, or wire an existing one into the orchestrator so it actually runs. Use whenever the user wants to add a scraper, add a data source, create an ETL, add a new feed, fetch data from a site/API/RSS, "add a pipeline", or when an ETL exists but isn't being executed. Trigger on "new etl", "scrape X", "add a data source", "fetch from", "wire up the etl", "add to the orchestrator", "it's not running".
---

# ETL Pipeline

Every Watchtower ETL follows the same Template Method contract and gets wired
into one orchestrator. This skill keeps new pipelines consistent and — the most
common gap — actually *registered* so they run in production.

## The 3 obligations of a new ETL

If you skip any of these, the pipeline is half-built. All three are required.

1. **Implement the pipeline** as a `BaseETL` subclass with `extract/transform/load`.
2. **Register it** in `run_all_etl_orchestrator.py` → `ETL_SCRIPTS`.
3. **Add a model** in `src/models/` if the data has new shape (otherwise reuse).

## Obligation 1 — the pipeline

Subclass `BaseETL[I, O]` (see `src/etl/base.py`). The base gives you metrics,
checkpointing, a tenacity-based retry wrapper, the circuit breaker
(`src/etl/circuit_breaker.py`), and proxy rotation (`src/etl/proxy_manager.py`)
for free. Do **not** hand-roll retries or HTTP error handling.

```python
"""<source_name> ETL — one-line purpose."""
from __future__ import annotations

from typing import Any

from src.etl.base import BaseETL
from src.models.base import TimestampedModel   # only if you add a model


class MySourceETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """Fetch <thing> from <source>, normalize, persist under data/<name>/."""

    def extract(self) -> list[dict[str, Any]]:
        """Pull raw records. Use the circuit breaker + retry from BaseETL."""
        ...

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate with a Pydantic model, then return plain dicts for load."""
        ...

    def load(self, data: list[dict[str, Any]]) -> None:
        """Write data/<name>/output/<name>_{timestamp}.json + _latest.json
        and a run_summary_latest.json. BaseETL helpers exist for this."""
        ...


if __name__ == "__main__":
    MySourceETL().run()
```

Conventions (match the surrounding ETLs — look at a sibling like
`src/etl/news/news_get_techcrunch.py` before writing):

- **File naming**: lowercase snake_case, verb-aware. News domain uses
  `news_get_<source>.py`; RSS feeds use `<source>_etl.py`. Pick the dominant
  convention of the target subpackage under `src/etl/`.
- **Subpackage**: place in the right domain folder (`news/`, `games/`,
  `intelligence/`, `goldigging/`, `expanded/`, …). Create the folder + an
  `__init__.py` only if a new domain is genuinely needed.
- **HTTP**: prefer `requests` for APIs and `feedparser` for RSS. Use Playwright
  (`src/etl/` has examples) only when the page is JS-rendered — it's heavy.
- **Output shape**: persist to `data/<name>/output/<name>_{timestamp}.json` plus a
  `<name>_latest.json`. The dashboard reads the `_latest.json` files. See
  `AGENTS.md` → "Data storage layout".
- **Validate with Pydantic** before load — extract → model → dict, never dump raw
  scraped dicts. Reuse a model from `src/models/` if one fits; only add a new one
  if the data has a novel shape.
- **`if __name__ == "__main__":` block is mandatory** — the orchestrator invokes
  each script as `uv run python <script>` (see below), so the entrypoint must run.

## Obligation 2 — register it (THIS is what people forget)

The orchestrator (`run_all_etl_orchestrator.py`) has a top-level list,
`ETL_SCRIPTS`, of script paths. **If your script isn't in that list, it never
runs in production** — no error, just silence. This is the #1 cause of "my new
ETL isn't producing data."

Add your path as a new string in the appropriate domain comment-section:

```python
ETL_SCRIPTS = [
    ...
    # News ETL
    ...
    "src/etl/news/news_get_my_source.py",   # <- add here, with a short comment
    ...
]
```

How the orchestrator runs each entry (`run_script` in that file, for reference):

```python
cmd = ["uv", "run", "python", script_path]        # so uv env is guaranteed
# stdout+stderr -> logs/<basename>.log, per-script
# timeout = 1800s (30 min) per script
# run in a ThreadPoolExecutor, default --workers 4
```

So a correct entry is a path to a **runnable script** that does its work under
`if __name__ == "__main__":`. An importable class alone is not enough.

Run the whole orchestrator locally to confirm registration:
`uv run python run_all_etl_orchestrator.py --workers 4`.

## Obligation 3 — model (only if new shape)

If the source's records don't fit an existing model, add one to `src/models/`
inheriting from `TimestampedModel` / `StatusModel` as appropriate, with full type
hints and a Google-style docstring. Register/export it the same way sibling
models are. If an existing model fits (e.g. `NewsArticleModel`), reuse it — don't
fork.

## Definition of done

Before declaring the ETL done, verify each:

- [ ] `uv run python src/etl/<domain>/<my_etl>.py` runs standalone and writes a
      `_latest.json` under `data/<name>/output/`.
- [ ] Path is added to `ETL_SCRIPTS` in `run_all_etl_orchestrator.py`.
- [ ] `uv run ruff check src/etl/<domain>/<my_etl>.py` is clean.
- [ ] If a model was added: `uv run mypy src/models/<my_model>.py` is clean.
- [ ] No new dependency was silently added; if one was needed, it's in
      `pyproject.toml` and `uv lock` was updated.

## When fixing an existing ETL that "isn't running"

Almost always one of:
1. Not in `ETL_SCRIPTS` → add it (Obligation 2).
2. In the list but the script file path is wrong / file was renamed → fix the path
   (the orchestrator logs `Warning: Script ... does not exist. Skipping.`).
3. Script runs but throws → check `logs/<basename>.log` locally, or
   `/mnt/user/appdata/watchtower/logs/` on Unraid (see `unraid-deploy` skill).
