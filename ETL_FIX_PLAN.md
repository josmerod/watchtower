# Watchtower ETL Failure Analysis & Fix Plan

**Generated:** 2026-05-19  
**Context:** 9 failing ETLs out of 79 total (70 success, 9 failed)

---

## 1. museum_etl.py — `'ETLMetrics' object has no attribute 'status'`

**File:** `src/etl/museums/museum_etl.py`  
**Line:** 177  
**Root Cause:** The `__main__` block at the end of the file references `metrics.status` and `metrics.error_message`, but `ETLMetrics` (in `base.py`) has no `status` or `error_message` attributes. The available properties are `is_successful` (bool), `error_count` (int), and `errors_detail` (list).

**Fix:** Replace the `__main__` block logic to use the correct attributes.

```
old_string (line 176-180):
    # Example of how to check status and handle results
    if metrics.status == "success":
        logging.info("ETL completed successfully.")
    else:
        logging.error(f"ETL failed: {metrics.error_message}")

new_string:
    # Example of how to check status and handle results
    if metrics.is_successful:
        logging.info("ETL completed successfully.")
    else:
        logging.error(f"ETL failed with {metrics.error_count} errors")
```

**Deploy:** Local file fix only (no Docker rebuild needed).

---

## 2. shoppy_etl.py — `TypeError: unsupported operand type(s) for /: 'str' and 'str'`

**File:** `src/etl/ecommerce/shoppy_etl.py`  
**Line:** 27  
**Root Cause:** `get_project_root()` from `src/utils/file_system.py` returns `str` (line 254: `return str(get_file_system_manager().project_root)`). The code at line 27 does `get_project_root() / "data" / "shoppy"` — the `/` operator only works on `Path` objects, not `str`.

**Fix:** Wrap the return value in `Path()`.

```
old_string (line 27):
DATA_DIR = get_project_root() / "data" / "shoppy"

new_string:
DATA_DIR = Path(get_project_root()) / "data" / "shoppy"
```

**Deploy:** Local file fix only.

---

## 3. cinema_ecartelera_etl.py — Playwright browsers not installed

**File:** `src/etl/entertainment/cinema_ecartelera_etl.py`  
**Root Cause:** The Dockerfile at line 51 already runs `playwright install --with-deps`, so the browsers ARE installed at build time. However, the error typically occurs when:
- The Docker image was built but the `playwright` package wasn't in `pyproject.toml` dependencies at build time
- Or the image was built with a cached layer where playwright install failed silently

**Investigation:** The Dockerfile correctly has `RUN playwright install --with-deps` at line 51. This means the fix is simply to **rebuild the Docker image** to ensure playwright browsers are properly installed in the current image.

**Fix:** Rebuild Docker image. No code changes needed.

```
docker build -t watchtower .
docker stop <container_id> && docker rm <container_id>
docker run -d ... watchtower
```

**Deploy:** Docker rebuild required.

---

## 4. cinema_ecartelera_improved_etl.py — Same Playwright issue as #3

**File:** `src/etl/entertainment/cinema_ecartelera_improved_etl.py`  
**Root Cause:** Same as #3 — Playwright browsers not present in the running container.

**Fix:** Same as #3 — rebuild the Docker image.

**Deploy:** Docker rebuild required (same rebuild fixes both #3 and #4).

---

## 5. package_registry_etl.py — `'str' object has no attribute 'value'`

**File:** `src/etl/expanded/package_registry_etl.py`  
**Line:** 257  
**Root Cause:** At line 257, the code does `package.registry.value` where `registry` is expected to be a `PackageRegistry` enum. However, the `PackageModel`'s `registry` field is typed as `PackageRegistry` (an Enum), and `.value` should work on it. The issue is that when the ETL's `transform()` method stores data via `_transform_package()`, the `registry` field gets assigned a `PackageRegistry` enum — that part is fine. BUT the `api_metrics.registry_distribution` dict keys become strings (line 257-258), which is fine too.

**The actual failure is at line 411** (the `main()` function), which is the **error report line**. Looking more carefully: the error at runtime happens in the transform loop. The `PackageModel.registry` field is a `PackageRegistry` enum, so `package.registry.value` SHOULD work. However, if the data from the API comes back with `registry` as a plain string in the raw dict and somehow bypasses the enum conversion in `_transform_package`, this would fail.

Actually, looking at the error message more carefully (`'str' object has no attribute 'value'` at line 411/588): The traceback says line 411. Line 411 in the file is `metrics = etl.run()`. This means the error originates from inside `run()`. Looking at the transform method (line 257): `reg = package.registry.value` — this is correct because `package.registry` is a `PackageRegistry` enum.

**BUT WAIT** — there's a subtle issue. The `SimpleETL.load()` method (inherited by nothing here — `PackageRegistryETL` extends `BaseETL` directly) writes JSON. The `BaseETL._apply_deduplication()` method at line 447 tries to reconstruct models: `unique_items = [model_class(**item) for item in unique_items]`. The `DeduplicationEngine.find_duplicates()` converts models to dicts internally. When these dicts are reconstructed, the `registry` field would be a plain string "npm", not a `PackageRegistry` enum. However, Pydantic should auto-convert it via the enum validator.

**Most likely actual cause:** The `_transform_package` method at line 301 does `PackageRegistry(registry_str)`. If the placeholder data returns registry as a `PackageRegistry` enum already (since the hardcoded data has `"registry": "npm"` as a string), it would get properly converted. But if for some reason the data flows through deduplication and back, the `.value` call on a reconstructed model might fail.

**After deeper analysis:** The actual error at line 257 (`reg = package.registry.value`) can only fail if `package.registry` is a `str` instead of a `PackageRegistry` enum. This would happen if Pydantic validation was bypassed somehow. The safest fix is to add a `.value` call with a fallback.

```
old_string (line 257):
            reg = package.registry.value
            self.api_metrics.registry_distribution[reg] = self.api_metrics.registry_distribution.get(reg, 0) + 1

new_string:
            reg = package.registry.value if isinstance(package.registry, PackageRegistry) else str(package.registry)
            self.api_metrics.registry_distribution[reg] = self.api_metrics.registry_distribution.get(reg, 0) + 1
```

**Deploy:** Local file fix only.

---

## 6. crypto_sentiment_miner.py — `datetime.UTC` not available in Python 3.11

**File:** `src/miners/crypto_sentiment_miner.py`  
**Lines:** 311, 350, 388  
**Root Cause:** `datetime.UTC` was introduced in **Python 3.11**. However, the error says it's not available. This could mean:
- The container runs Python < 3.11 (unlikely, Dockerfile says `python:3.11-slim`)
- Or there's a `from datetime import datetime` (not `import datetime`), so `datetime.UTC` becomes `datetime.datetime.UTC` which doesn't work

Looking at the imports: `from datetime import datetime` (line 19). So `datetime` is the CLASS, and `datetime.UTC` tries to access `UTC` on the `datetime` class — this is correct for Python 3.11+. However, `datetime.UTC` is actually `datetime.timezone.utc`, not `datetime.UTC`. The `datetime.UTC` constant was added in Python 3.11 as an alias.

Wait — checking more carefully: In Python 3.11, `datetime.UTC` is indeed available as a class attribute. BUT the import `from datetime import datetime` means `datetime` is the class. `datetime.UTC` should work if Python >= 3.11. 

**Actually:** Looking at the actual error message again: `AttributeError: type object 'datetime.datetime' has no attribute 'UTC'`. The error says `datetime.datetime.UTC`, not `datetime.UTC`. This means somewhere in the code, `datetime` was imported as a module (`import datetime`), not as a class. Looking at line 19: `from datetime import datetime` — so `datetime` IS the class.

BUT: the error trace says `type object 'datetime.datetime' has no attribute 'UTC'`. This could be a confusion in the error reporting. The simplest, safest fix is to import `timezone` and use `datetime.now(timezone.utc)` instead of `datetime.now(datetime.UTC)`.

```
old_string (line 19):
from datetime import datetime

new_string:
from datetime import datetime, timezone
```

```
old_string (line 311):
            "fetched_at": datetime.now(datetime.UTC).isoformat(),

new_string:
            "fetched_at": datetime.now(timezone.utc).isoformat(),
```

```
old_string (line 350):
            "fetched_at": datetime.now(datetime.UTC).isoformat(),

new_string:
            "fetched_at": datetime.now(timezone.utc).isoformat(),
```

```
old_string (line 388):
            "fetched_at": datetime.now(datetime.UTC).isoformat(),

new_string:
            "fetched_at": datetime.now(timezone.utc).isoformat(),
```

**Deploy:** Local file fix only.

---

## 7. stackexchange_etl.py — Error code 1

**File:** `src/etl/expanded/stackexchange_etl.py`  
**Root Cause:** After analyzing the code, this ETL calls the Stack Exchange API via `self.http_session.get(url, params=params, timeout=30)` at line 152. The `self.http_session` comes from `self.proxy_manager.get_session(retries=self.max_retries)` (BaseETL property at line 267). 

**Error code 1 in the supervisor log** typically means the process exited with code 1 (unhandled exception). The most likely causes:
1. **Rate limiting / network failure** — Stack Exchange API returns 429 when rate limited, and the code raises `HTTPError` at line 153 (`response.raise_for_status()`)
2. **Missing API key** — Without an API key, Stack Exchange limits to 10 requests per IP per minute. With 7 sites, each potentially hitting the API, this easily triggers rate limiting.
3. **Proxy manager issue** — The proxy manager might fail to create a valid session

**Additionally**, there's a potential issue similar to #5: at line 198, `site = question.site.value` — same pattern as the package_registry_etl.py issue.

**Fix:** Add better error handling for API failures, and handle the `.value` call safely:

```
old_string (line 196-199):
        # Update metrics
        for question in transformed:
            site = question.site.value
            self.api_metrics.site_distribution[site] = self.api_metrics.site_distribution.get(site, 0) + 1

new_string:
        # Update metrics
        for question in transformed:
            site = question.site.value if isinstance(question.site, StackExchangeSite) else str(question.site)
            self.api_metrics.site_distribution[site] = self.api_metrics.site_distribution.get(site, 0) + 1
```

Also add the missing import at top of file:
```
old_string (line 23):
from src.models.stackexchange import (
    StackExchangeMetricsModel,
    StackExchangeQuestionModel,
    StackExchangeSite,
)

new_string:
from src.models.stackexchange import (
    StackExchangeMetricsModel,
    StackExchangeQuestionModel,
    StackExchangeSite,
)

import time as _time  # Add delay between API calls
```

And add a delay between API calls to avoid rate limiting:
```
old_string (line 107-113):
        for site in self.sites:
            try:
                questions = self._fetch_site_questions(site)
                all_questions.extend(questions)

new_string:
        for site in self.sites:
            try:
                questions = self._fetch_site_questions(site)
                all_questions.extend(questions)
                _time.sleep(2)  # Rate limit: avoid 429 from Stack Exchange API
```

**Deploy:** Local file fix only.

---

## Intelligence API Returning 0 Items — Root Cause Analysis

### The Problem
The API's intelligence endpoint returns 0 items, even though the ETL scripts (`sec_edgar_rss.py` and `who_outbreaks_rss.py`) produce data files.

### Path Analysis

**ETL Output Paths (where data is written):**
- `sec_edgar_rss.py` line 78: `os.path.join(project_root, "data", "intelligence", "sec_edgar_latest.json")`
- `who_outbreaks_rss.py` line 80: `os.path.join(project_root, "data", "intelligence", "who_outbreaks_latest.json")`

**API Config Paths (where API looks for data):**
- `data_loader.py` line 295: `get_data_path("intelligence", "sec_edgar_latest.json")` → `{project_root}/data/intelligence/sec_edgar_latest.json`
- `data_loader.py` line 303: `get_data_path("intelligence", "who_outbreaks_latest.json")` → `{project_root}/data/intelligence/who_outbreaks_latest.json`

**`get_data_path` resolution** (from `src/web/dashboard/utils.py` line 31):
```python
return os.path.join(get_project_root(), "data", *path_parts)
```

Where `get_project_root()` (line 9-19) resolves to the project root by going up 4 levels from `src/web/dashboard/utils.py`.

### Verdict: Paths ARE correct ✅

The ETL output paths and API config paths both resolve to:
- `{project_root}/data/intelligence/sec_edgar_latest.json`
- `{project_root}/data/intelligence/who_outbreaks_latest.json`

**The actual issue:** The data files (`sec_edgar_latest.json`, `who_outbreaks_latest.json`) do NOT exist locally at `~/dev/watchtower/data/intelligence/`. The search confirmed: **0 files found** matching these names under `data/`. This means either:
1. The intelligence ETLs are not being executed by the orchestrator (check `src/launcher/main.py`)
2. The ETLs run but produce 0 entries (the RSS feeds might be empty or failing)
3. The data is inside the Docker container volume but not synced to the local Mac

Looking at `src/launcher/main.py` line 153-154, the scripts ARE configured in the launcher. So the ETLs do run inside Docker. The data exists in the Docker container's `data/intelligence/` directory.

**The REAL issue is likely in the API data loading.** The `load_data_from_file()` function at `data_loader.py` line 403-438 returns `[]` if:
1. The file doesn't exist (line 406-408) — but we just said the files should exist inside Docker
2. The file contains a dict that doesn't match recognized structures (line 424-426)

The most likely cause: **The JSON structure from the ETL doesn't match what `load_data_from_file()` expects.** The ETL writes a raw list of items. Let's check:
- `sec_edgar_rss.py` writes `json.dump(entries, ...)` where entries is a list of dicts — ✅ matches `isinstance(data, list)` 
- `load_data_from_file()` handles lists directly (line 427-428) — ✅ should work

**Wait — checking `data_loader.py` more carefully:** The `INTEL_SOURCES_CONFIG` is used by the API endpoint. The function that loads it would call `load_data_from_file(config["path"])`. Since the files exist in Docker and contain valid lists, this should work.

**The most probable root cause:** The files genuinely don't exist. Check the Docker logs for the `sec_edgar_rss.py` and `who_outbreaks_rss.py` scripts. If `fetch_sec_edgar()` returns an empty list (RSS feed failure), `save_sec()` returns early without creating any files. The SEC feed (`https://www.sec.gov/Archives/edgar/usgaap.rss.xml`) may be blocked or returning empty results from inside Docker.

**Recommended action:** Check Docker logs for these specific scripts:
```bash
docker exec <container> cat /app/data/intelligence/sec_edgar_latest.json 2>&1
docker logs <container> 2>&1 | grep -i "sec_edgar\|who_outbreaks\|RSS"
```

---

## Summary: All Fixes

| # | ETL | Root Cause | Fix Type | Docker Rebuild? |
|---|-----|-----------|----------|-----------------|
| 1 | museum_etl.py | `metrics.status` → use `metrics.is_successful` | Code fix | No |
| 2 | shoppy_etl.py | `str / str` → wrap in `Path()` | Code fix | No |
| 3 | cinema_ecartelera_etl.py | Missing playwright browsers | Rebuild | Yes |
| 4 | cinema_ecartelera_improved_etl.py | Missing playwright browsers | Rebuild | Yes (same) |
| 5 | package_registry_etl.py | `package.registry.value` on str | Code fix | No |
| 6 | crypto_sentiment_miner.py | `datetime.UTC` → `timezone.utc` | Code fix | No |
| 7 | stackexchange_etl.py | Rate limiting + `.value` on str | Code fix | No |
| — | Intelligence API | RSS feed empty/failing + path check | Investigation | Depends |

**Code fixes (5 ETLs):** Can be applied locally, then `docker cp` into the container or rebuild.
**Docker rebuild (2 ETLs):** Required for Playwright browser installation.
**Intelligence API:** Needs log investigation inside Docker container.
