# Watchtower Codebase Audit Summary

## Overview
Audit completed on Watchtower data aggregation system at ~/dev/watchtower/. Focused on ETL orchestrator, scheduler, problematic ETLs, API code, and Docker/supervisord configuration.

## Detailed Findings

### 1. ETL Orchestrator (`run_all_etl_orchestrator.py`)
- **Path**: `/Users/josele/dev/watchtower/run_all_etl_orchestrator.py`
- **Worker Count**: Configurable via `--workers` (default: 4) - appropriate
- **Timeout**: 30 minutes per script (`process.wait(timeout=1800)`) - may be excessive for failing scripts
- **Error Handling**: Robust - catches timeouts, exceptions, logs stdout/stderr, continues on failures
- **ETL Scripts**: 136 scripts listed across 20+ categories (News, Intelligence, Entertainment, Museums, etc.)

### 2. ETL Scheduler (`deployment/etl_scheduler.py`)
- **Path**: `/Users/josele/dev/watchtower/deployment/etl_scheduler.py`
- **Interval**: 2 hours (`time.sleep(2 * 3600)`) - more frequent than stated 4h
- **Dashboard Restart**: Correctly restarts only API server (not dashboard) to avoid UX disruption
- **Startup Behavior**: Runs immediately on start for fresh data on deploy
- **Failure Resilience**: Uses `check=False` to prevent scheduler crashes on ETL failures

### 3. Problematic ETLs

#### A. CVE/NVD ETL (`src/etl/intelligence/nvd_cve_etl.py`)
- **Path**: `/Users/josele/dev/watchtower/src/etl/intelligence/nvd_cve_etl.py`
- **Issue**: Returns historical CVEs (1988-1999) instead of recent threats
- **Root Cause**: 
  - Date filtering uses 90-day window but API testing shows empty responses
  - No `nvd_cve_latest.json` file found in `data/intelligence/`
  - NVD API returned 0 bytes content with 200 OK during test
- **Fix**: 
  - Verify NVD API date format parameters
  - Test API directly to confirm functionality
  - Consider reducing lookback window to 7-30 days
  - Add API failure fallback to cached data

#### B. Entertainment ETL (Trakt) (`src/etl/entertainment/trakt_trending_etl.py`)
- **Path**: `/Users/josele/dev/watchtower/src/etl/entertainment/trakt_trending_etl.py`
- **Issue**: Data frozen at Jan 5, 2026 (~5 months stale)
- **Root Cause**:
  - Missing `TRAKT_CLIENT_ID` environment variable/secrets
  - No `trakt_*_latest.json` files found in `data/entertainment/`
  - Graceful failure returns empty list when credentials missing
- **Fix**:
  - Ensure Trakt API credentials are properly deployed
  - Implement fallback to last successful run when auth fails
  - Add alerting/monitoring for credential failures

#### C. Museums ETL (`src/etl/museums/museum_etl.py`)
- **Path**: `/Users/josele/dev/watchtower/src/etl/museums/museum_etl.py`
- **Issue**: Only 1 museum item (Mundaneum) despite querying for 100
- **Root Cause**:
  - SPARQL query requires `wdt:P856 ?website` (official website) which filters heavily
  - Validation likely failing in `transform()` method for 99/100 results
  - `museums_latest.json` shows 1093 lines but only 1 valid entry
- **Fix**:
  - Debug validation failures - add detailed logging of why items fail
  - Check required fields in `VirtualMuseumModel` vs. extracted data
  - Consider temporarily relaxing website requirement to increase sample size
  - Examine Pydantic validation errors in transform method

#### D. SEC EDGAR ETL (`src/etl/intelligence/sec_edgar_rss.py`)
- **Path**: `/Users/josele/dev/watchtower/src/etl/intelligence/sec_edgar_rss.py`
- **Issue**: 0 items collected
- **Root Cause**:
  - SEC.gov returns HTTP 403 Forbidden (bot blocking)
  - No User-Agent header set in feedparser request
  - No `sec_edgar_latest.json` file found in `data/intelligence/`
- **Fix**:
  - Add proper User-Agent header identifying Watchtower bot
  - Implement rate limiting to respect SEC.gov policies
  - Consider alternative SEC data sources if RSS remains blocked
  - Add retry logic with exponential backoff for temporary blocks

### 4. API Code (`src/api/main.py`)
- **Path**: `/Users/josele/dev/watchtower/src/api/main.py`
- **Health Endpoint**: EXISTS and functional (`@app.get("/health")` returns `{"status": "ok"}`)
  - *Note: Context claimed 404 - this appears outdated/incorrect*
- **CORS**: Properly configured for localhost, internal IP, and production domain
- **Rate Limiting**: MISSING - no implementation found
- **Router Inclusion**: Properly includes API routers at `/api/v1` prefix

### 5. Docker/Supervisord

#### Dockerfile (`deployment/Dockerfile`)
- **Path**: `/Users/josele/dev/watchtower/deployment/Dockerfile`
- **Base**: `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` (good)
- **Dependencies**: Installs supervisor, curl, git, dos2unix, procps
- **Playwright**: Chromium only (space-efficient)
- **Entry Point**: Correctly starts supervisord with config
- **Ports**: Exposes 7780 (dashboard) and 45714 (API)

#### Supervisord Config (`deployment/supervisord.conf`)
- **Path**: `/Users/josele/dev/watchtower/deployment/supervisord.conf`
- **Programs**: 
  - `dashboard`: `uv run python run_watchtower_dashboard.py`
  - `etl_scheduler`: `uv run python deployment/etl_scheduler.py` 
  - `api`: `uv run uvicorn src.api.main:app --host 0.0.0.0 --port 45714`
- **Settings**: All set to `autostart=true`, `autorestart=true` with proper logging

## Priority Fix Recommendations

### Immediate (High Impact)
1. **SEC EDGAR ETL**: Add User-Agent header and rate limiting
2. **CVE/NVD ETL**: Fix date parameters and add API failure handling
3. **Trakt ETL**: Deploy credentials and add auth failure fallback
4. **Museums ETL**: Debug validation failures preventing 99% of results

### Medium Term
5. **API Rate Limiting**: Implement rate limiting on `/api/v1` endpoints
6. **Scheduler Alignment**: Adjust interval from 2h to stated 4h if desired
7. **Orchestrator Timeout**: Consider adaptive timeouts based on historical ETL durations

## Verification Notes
- The `/health` endpoint is actually present and working correctly - contrary to context claims of returning 404
- All ETL scripts are properly listed and orchestrated with thread pooling
- Docker/supervisord configuration is sound and follows container best practices

## Conclusion
The Watchtower system has a solid architectural foundation with proper orchestration, scheduling, and deployment patterns. The primary issues lie in four specific ETLs suffering from authentication problems, API blocking, overly restrictive filters, and validation failures. Addressing these will restore the system to full functionality with current, diverse data across all categories.