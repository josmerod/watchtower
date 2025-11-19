# Epic Technical Specification: Observability Infrastructure

Date: 2025-11-16
Author: Joshi
Epic ID: 1
Status: Approved

---

## Overview

Epic 1 establishes the essential observability foundation for Megalith, enabling comprehensive system health monitoring and providing users with basic content discovery capabilities. This epic addresses two critical needs: (1) operational visibility into the 50+ ETL pipelines and watcher systems that form the platform's data ingestion layer, and (2) user-facing search functionality to quickly locate specific content across all dashboard tabs.

The observability infrastructure will collect, store, and visualize metrics from all ETL operations, providing real-time health status, error tracking, and performance monitoring. This foundation enables future work by establishing metrics baselines needed for Epic 7 (Tech Debt sprint) and providing the backend alert infrastructure required for Epic 3 (Smart Notifications). Simultaneously, the basic full-text search capability delivers immediate user value by solving the current usability gap identified in PRD requirement FR-5.1.

## Objectives and Scope

### In Scope

**Backend Observability (Track A - Weeks 1-2):**
- Enhanced ETL metrics collection infrastructure with automatic instrumentation
- Structured logging framework with JSON formatters and contextual error tracking
- Metrics storage in JSON format at `data/metrics/{etl_name}/{timestamp}_metrics.json`
- Health check REST API endpoints (`/health`, `/metrics`) integrated into Dash application
- ETL success/failure rate calculation and health status determination logic

**Frontend Capabilities (Track B - Weeks 2-3):**
- Client-side full-text search across all dashboard tabs (<1 second response time)
- Metrics dashboard tab for visualizing ETL performance and system health
- Search highlighting and real-time filtering integrated into existing tab components
- Metrics visualization using Plotly charts (ETL run times, error rates, success rates)

**Quality Standards:**
- All metrics collection must add <50ms overhead to ETL execution
- Search must handle 10,000+ items per tab without performance degradation
- Health API responses must be <200ms
- Zero disruption to existing 50+ ETL pipelines

### Out of Scope

- Advanced search features (fuzzy matching, relevance ranking, full-text indexing with PostgreSQL)
- External monitoring tool integrations (Prometheus, Grafana, Datadog)
- Alerting and notification capabilities (deferred to Epic 3)
- Historical trend analysis beyond 7-day charts (future enhancement)
- Automated remediation or self-healing capabilities
- Performance profiling infrastructure (deferred to Epic 7)

## System Architecture Alignment

Epic 1 integrates seamlessly into Megalith's existing brownfield architecture while establishing new patterns for observability:

**Existing Components Leveraged:**
- **BaseETL Framework** (`src/etl/base.py`): Extended with automatic metrics collection using the existing ETLMetrics Pydantic model
- **Dash Dashboard** (`src/web/dashboard/app.py`): New health API endpoints added to Flask server, new metrics tab following established component patterns
- **File-based JSON Storage** (`data/` directory): Consistent with existing architecture, metrics stored in `data/metrics/` using same patterns as ETL outputs
- **Pydantic Models** (`src/models/`): ETLMetrics model extended with additional fields for comprehensive tracking

**New Architectural Components:**
- **Metrics Storage Layer**: `data/metrics/{etl_name}/` directory structure with timestamped JSON files
- **Health API Endpoints**: `/health` and `/metrics` REST endpoints integrated into Dash/Flask server
- **Metrics Dashboard Tab**: `src/web/dashboard/components/metrics_tab.py` following VideoManager pattern
- **Search Components**: Client-side search inputs added to all existing dashboard tabs using Dash callbacks

**Architecture Constraints Respected:**
- Zero disruption to existing 50+ ETL pipelines - metrics collection is opt-in via BaseETL framework
- File-based storage pattern maintained - no database dependencies introduced
- Component-based dashboard architecture - metrics tab is independent module
- Single-callback pattern per component - prevents callback conflicts
- Bootstrap styling consistency - all new UI components use dash-bootstrap-components

**Integration Points:**
- BaseETL.run() method instrumented to automatically save metrics after each execution
- Dash app.server (Flask instance) extended with new API routes
- Each dashboard tab component enhanced with search input and filtering callback
- Health status calculation reads from centralized `data/metrics/` directory

## Detailed Design

### Services and Modules

| Module | Responsibility | Inputs | Outputs | Owner |
|--------|---------------|--------|---------|-------|
| **BaseETL (Enhanced)** | Automatic metrics collection and persistence during ETL execution | ETL execution context, start/end times, items processed/failed | `data/metrics/{etl_name}/{timestamp}_metrics.json` | Backend |
| **MetricsCollector** | Centralized metrics aggregation and storage utilities | ETL name, execution metrics, error details | Structured JSON metrics files with consistent schema | Backend |
| **HealthAPI** | REST endpoints for system health and metrics queries | HTTP GET requests to `/health` and `/metrics` | JSON responses with health status, aggregated metrics | Backend |
| **MetricsManager** | Data service for loading and filtering metrics in dashboard | Metrics directory path, source filters, time ranges | Processed metrics data for visualization | Frontend |
| **MetricsTab** | Dashboard component for visualizing ETL performance | Metrics data from MetricsManager | Interactive Plotly charts, filterable tables | Frontend |
| **SearchComponent** | Reusable search input with real-time filtering | Tab-specific data (videos, papers, news, etc.) | Filtered results with highlighted matches | Frontend |
| **StructuredLogger** | Enhanced logging with JSON formatting and context | Log level, component, operation, context data | Structured log entries to `logs/` directory | Backend |

### Data Models and Contracts

**ETLMetrics Model (Enhanced)** - `src/etl/base.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List, Any

class ETLMetrics(BaseModel):
    """Comprehensive metrics for ETL pipeline execution."""

    # Existing fields
    etl_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    items_processed: int
    items_failed: int
    success_rate: float = Field(ge=0.0, le=1.0)

    # New fields for Epic 1
    checkpoint_status: Optional[str] = None  # "completed", "partial", "failed"
    errors_detail: List[Dict[str, Any]] = Field(default_factory=list)
    # Each error: {"timestamp": str, "error_type": str, "message": str, "context": dict}

    # Performance metrics
    memory_usage_mb: Optional[float] = None
    cpu_time_seconds: Optional[float] = None

    # Data quality metrics
    duplicates_detected: int = 0
    validation_failures: int = 0

    # Metadata
    etl_version: str = "1.0"
    python_version: str
    execution_environment: str  # "development", "production", "docker"
```

**HealthStatus Model** - `src/web/dashboard/app.py`

```python
class HealthStatus(BaseModel):
    """System health status response."""

    status: str  # "ok", "degraded", "down"
    timestamp: datetime
    version: str = "0.1.0"
    uptime_seconds: float

    # Optional detailed metrics
    etl_health: Optional[Dict[str, Any]] = None
    # {"total_sources": int, "failed_last_run": int, "avg_success_rate": float}
```

**MetricsSummary Model** - `src/web/dashboard/app.py`

```python
class MetricsSummary(BaseModel):
    """Aggregated metrics response."""

    total_sources: int
    total_items_processed: int  # Last 24 hours
    last_etl_runs: Dict[str, datetime]  # {etl_name: timestamp}
    error_rates: Dict[str, float]  # {etl_name: error_rate}
    avg_duration_seconds: Dict[str, float]  # {etl_name: avg_duration}
```

**Metrics Storage Schema** - `data/metrics/{etl_name}/{timestamp}_metrics.json`

```json
{
  "etl_name": "arxiv_etl",
  "start_time": "2025-01-16T10:00:00Z",
  "end_time": "2025-01-16T10:02:30Z",
  "duration_seconds": 150.5,
  "items_processed": 45,
  "items_failed": 2,
  "success_rate": 0.956,
  "checkpoint_status": "completed",
  "errors_detail": [
    {
      "timestamp": "2025-01-16T10:01:15Z",
      "error_type": "ValidationError",
      "message": "Invalid date format",
      "context": {"paper_id": "2501.12345", "field": "published_date"}
    }
  ],
  "memory_usage_mb": 125.3,
  "cpu_time_seconds": 45.2,
  "duplicates_detected": 0,
  "validation_failures": 2,
  "etl_version": "1.0",
  "python_version": "3.10.12",
  "execution_environment": "production"
}
```

### APIs and Interfaces

**Health Check Endpoint** - `/health`

```
GET /health
Accept: application/json

Response 200 OK:
{
  "status": "ok" | "degraded" | "down",
  "timestamp": "2025-01-16T10:00:00Z",
  "version": "0.1.0",
  "uptime_seconds": 86400.5,
  "etl_health": {
    "total_sources": 52,
    "failed_last_run": 1,
    "avg_success_rate": 0.982
  }
}

Status Determination Logic:
- "ok": <5% ETL failure rate in last 10 runs
- "degraded": 5-10% ETL failure rate in last 10 runs
- "down": >10% ETL failure rate OR cannot read data files

Response Time: <200ms
Caching: 5 minutes
```

**Metrics Summary Endpoint** - `/metrics`

```
GET /metrics
Accept: application/json
Query Parameters:
  - time_range: "1h" | "24h" | "7d" (default: "24h")
  - sources: comma-separated ETL names (optional, default: all)

Response 200 OK:
{
  "total_sources": 52,
  "total_items_processed": 12453,
  "last_etl_runs": {
    "arxiv_etl": "2025-01-16T09:00:00Z",
    "news_etl": "2025-01-16T09:15:00Z",
    ...
  },
  "error_rates": {
    "arxiv_etl": 0.022,
    "news_etl": 0.0,
    ...
  },
  "avg_duration_seconds": {
    "arxiv_etl": 150.5,
    "news_etl": 45.2,
    ...
  }
}

Response Time: <500ms
Caching: 5 minutes
```

**BaseETL Metrics Interface** - Extended `run()` method

```python
class BaseETL:
    def run(self) -> ETLMetrics:
        """Execute ETL pipeline with automatic metrics collection."""

        metrics = ETLMetrics(
            etl_name=self.__class__.__name__,
            start_time=datetime.now(),
            python_version=sys.version,
            execution_environment=os.getenv("ENV", "development")
        )

        try:
            # Existing ETL execution logic
            self.extract()
            self.transform()
            self.load()

            # Update metrics
            metrics.end_time = datetime.now()
            metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.items_processed = self.items_count
            metrics.success_rate = self._calculate_success_rate()

        except Exception as e:
            # Error handling with context preservation
            metrics.errors_detail.append({
                "timestamp": datetime.now().isoformat(),
                "error_type": type(e).__name__,
                "message": str(e),
                "context": self._get_error_context()
            })
            raise
        finally:
            # Always save metrics
            self._save_metrics(metrics)

        return metrics
```

**Search Component Interface** - Dash callback signature

```python
@app.callback(
    Output("filtered-content", "data"),
    Input("search-input", "value"),
    State("tab-content", "data")
)
def filter_content(search_query: str, content: List[Dict]) -> List[Dict]:
    """Filter content based on search query.

    Args:
        search_query: User search input (case-insensitive)
        content: Current tab data (videos, papers, news, etc.)

    Returns:
        Filtered content with highlighted matches
    """
    if not search_query:
        return content

    query = search_query.lower()
    filtered = []

    for item in content:
        # Search in title, description, source, tags
        searchable_text = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("source", ""),
            " ".join(item.get("tags", []))
        ]).lower()

        if query in searchable_text:
            # Highlight matches using <mark> tags
            item_copy = item.copy()
            item_copy["title"] = highlight_matches(item["title"], search_query)
            filtered.append(item_copy)

    return filtered
```

### Workflows and Sequencing

**ETL Execution with Metrics Collection** (Story 1.1)

```
1. ETL Pipeline Start
   ├─> Initialize ETLMetrics object with start_time, etl_name, environment
   ├─> Execute extract() phase
   ├─> Execute transform() phase
   ├─> Execute load() phase
   ├─> Calculate success metrics (duration, success_rate, items_processed)
   ├─> Capture any errors with full context (timestamp, type, message, stack trace)
   └─> Save metrics to data/metrics/{etl_name}/{timestamp}_metrics.json

2. Error Handling Flow
   ├─> Exception caught in try/except block
   ├─> Extract error context (input data, operation, state)
   ├─> Append to metrics.errors_detail list
   ├─> Save partial metrics before re-raising exception
   └─> Structured logger writes error with full context

3. Structured Logging Flow
   ├─> Log entry created with level, timestamp, component, operation
   ├─> Context data attached (etl_name, items_count, checkpoint_id)
   ├─> JSON formatter serializes log entry
   └─> Written to logs/{etl_name}.log with rotation
```

**Health Check Request Flow** (Story 1.2)

```
1. Client → GET /health
   ├─> Check cache (5-minute TTL)
   ├─> If cached, return immediately
   └─> Otherwise, calculate health status:

2. Health Status Calculation
   ├─> Scan data/metrics/ for latest 10 runs per ETL
   ├─> Calculate failure rate: failed_runs / total_runs
   ├─> Determine status:
   │   ├─> "ok" if failure_rate < 0.05
   │   ├─> "degraded" if 0.05 <= failure_rate < 0.10
   │   └─> "down" if failure_rate >= 0.10 OR file read errors
   ├─> Calculate uptime from app start_time
   ├─> Build HealthStatus response
   ├─> Cache result for 5 minutes
   └─> Return JSON response (<200ms)

3. Metrics Summary Request
   ├─> Client → GET /metrics?time_range=24h
   ├─> Load all metrics files from last 24 hours
   ├─> Aggregate by ETL name:
   │   ├─> Sum items_processed
   │   ├─> Calculate avg error_rate per source
   │   ├─> Track last_run timestamp
   │   └─> Calculate avg_duration
   ├─> Build MetricsSummary response
   └─> Return JSON (<500ms)
```

**Search Interaction Flow** (Story 1.3)

```
1. User types in search input
   ├─> Dash Input triggers callback on value change
   ├─> Callback receives: search_query, current_tab_data
   └─> If query empty, return all data unfiltered

2. Client-side Filtering (<1 second)
   ├─> Convert query to lowercase
   ├─> For each item in tab data:
   │   ├─> Build searchable_text from title, description, source, tags
   │   ├─> Check if query in searchable_text
   │   ├─> If match: highlight occurrences with <mark> tags
   │   └─> Add to filtered results
   ├─> Return filtered data to Output
   └─> Dashboard re-renders with filtered content

3. Search + Existing Filters
   ├─> Filters already applied (source, date range, category)
   ├─> Search operates on pre-filtered results
   └─> Maintains filter state during search
```

**Metrics Dashboard Visualization** (Story 1.4)

```
1. User navigates to Metrics tab
   ├─> MetricsManager loads data from data/metrics/
   ├─> Read latest metrics file per ETL source
   ├─> Build aggregated dataset
   └─> Return to MetricsTab component

2. Metrics Table Rendering
   ├─> Display table with columns: Source, Last Run, Items, Success Rate, Duration
   ├─> Highlight failed ETLs in red (success_rate < 0.95)
   ├─> Enable sorting by any column
   └─> Show error count per source

3. Time-Series Chart Rendering
   ├─> Load 7-day metrics history
   ├─> Build Plotly line chart: X=time, Y=duration_seconds
   ├─> Multiple traces (one per ETL source)
   └─> Interactive tooltips on hover

4. Source Selection
   ├─> User clicks row in table
   ├─> Single callback triggered with source_id
   ├─> Load detailed error logs for that source
   ├─> Display in expandable section
   └─> Show error context and timestamps
```

## Non-Functional Requirements

### Performance

**Metrics Collection Overhead:**
- ETL execution time increase: <50ms per pipeline run
- Memory overhead: <10MB additional memory for metrics objects
- File I/O operations: Single write per ETL run (non-blocking)
- Target: Zero impact on existing ETL performance characteristics

**Dashboard Response Times:**
- Health API (`/health`): <200ms (95th percentile)
- Metrics API (`/metrics`): <500ms (95th percentile)
- Search filtering: <1 second for 10,000 items per tab
- Metrics tab initial load: <2 seconds with 7 days of data
- Chart rendering: <1 second for time-series visualization

**Scalability Targets:**
- Support 100+ ETL sources without degradation
- Handle 1,000+ metrics files (7 days × 50 sources × 3 runs/day)
- Search performance: Linear O(n) scaling up to 50,000 items
- Concurrent users: 5-10 simultaneous dashboard users

**Caching Strategy:**
- Health status: 5-minute TTL, refreshed on cache miss
- Metrics summary: 5-minute TTL, invalidated on new ETL runs
- Dashboard data: Component-level caching using @lru_cache
- Search results: No caching (real-time filtering required)

**Performance Monitoring (from PRD):**
- Dashboard load time: Maintain <2 seconds target (Epic 1 must not degrade this)
- Tab switching: <500ms (search component adds <100ms)
- Filter application: <300ms (search is additional filter layer)

### Security

**Current Security Posture (from PRD):**
- Local network access only (no public internet exposure)
- All data collected is public information (no PII)
- No authentication required (Epic 1 scope - authentication deferred to Epic 5)

**Epic 1 Security Considerations:**

**Health API Endpoints:**
- No sensitive data exposure in `/health` or `/metrics` responses
- Internal system metrics only (no user data, credentials, or secrets)
- Rate limiting: Not required for Epic 1 (local network deployment)
- Future consideration: API keys for external monitoring tools (Epic 9)

**Metrics Data Storage:**
- File permissions: Standard OS-level permissions on `data/metrics/` directory
- No encryption at rest (public information, local deployment)
- No sensitive data in error logs (validate before storing error context)
- Structured logging: Filter out potential secrets in error messages

**Search Component:**
- Client-side only (no data sent to external services)
- No XSS risk: Input sanitized through Dash framework
- No injection attacks: Search operates on pre-loaded JSON data
- No CSRF risk: GET-only search operations

**Error Context Preservation:**
- **Critical**: Ensure error logs don't capture API keys, tokens, or credentials
- Implement error context sanitization in BaseETL._get_error_context()
- Redact sensitive patterns: API keys, passwords, tokens, email addresses
- Example: "arxiv_api_key=sk_xxx" → "arxiv_api_key=[REDACTED]"

**Dependency Security:**
- All dependencies from pyproject.toml are existing (no new security surface)
- Continue existing practice: Monitor CVEs via GitHub Dependabot
- No external API calls introduced in Epic 1

### Reliability/Availability

**Target Reliability (from PRD):**
- ETL system: 99%+ uptime, <1% failed runs
- Dashboard: Available whenever Dash server is running
- Watcher downtime: <1 hour/month

**Epic 1 Reliability Guarantees:**

**Metrics Collection Resilience:**
- **Graceful degradation**: ETL continues execution even if metrics save fails
- **No cascading failures**: Metrics errors never crash ETL pipelines
- **Best-effort persistence**: Try-except blocks around all metrics operations
- **Partial success handling**: Save what can be saved, log what cannot

**Health API Availability:**
- **No single point of failure**: Health checks degrade gracefully if metrics unavailable
- **Fallback status**: Return "degraded" status with partial data if some metrics unreadable
- **Timeout handling**: File reads timeout after 5 seconds to prevent hanging
- **Error recovery**: API returns 503 Service Unavailable if critical errors, not 500

**Search Component Resilience:**
- **Client-side robustness**: Search failures don't crash dashboard
- **Empty state handling**: Graceful display when no results match query
- **Performance safeguard**: Automatic pagination if results exceed 1,000 items
- **State recovery**: Search state persists during tab switching

**Data Integrity:**
- **Atomic writes**: Metrics files written atomically (write to temp, then rename)
- **Corruption recovery**: Invalid JSON files logged and skipped, don't block aggregation
- **Backup strategy**: Metrics files are append-only, never mutated after creation
- **Retention policy**: Automatic cleanup of metrics older than 30 days (configurable)

**Monitoring & Alerting (Epic 1 provides foundation for Epic 3):**
- Metrics collection enables future alerting on ETL failure rates
- Health API provides integration point for external monitoring (Epic 9)
- Structured logs enable future log aggregation and analysis

### Observability

**Epic 1 IS the observability foundation** - this section defines what Epic 1 enables for future debugging and monitoring.

**Metrics Signals (Story 1.1):**
- **Execution metrics**: start_time, end_time, duration_seconds, items_processed, items_failed
- **Success metrics**: success_rate (0.0-1.0), checkpoint_status (completed/partial/failed)
- **Error metrics**: errors_detail array with full context (type, message, timestamp, context)
- **Performance metrics**: memory_usage_mb, cpu_time_seconds (optional in v1.0)
- **Data quality metrics**: duplicates_detected, validation_failures

**Structured Logging (Story 1.1):**
- **Format**: JSON with fields: timestamp, level, component, operation, message, context
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Context fields**: etl_name, items_count, checkpoint_id, error_type, stack_trace
- **Destination**: `logs/{etl_name}.log` with daily rotation (7-day retention)
- **Use cases**: Debugging ETL failures, performance analysis, audit trails

**Health Monitoring (Story 1.2):**
- **Endpoint**: `/health` provides real-time system status
- **Granularity**: Overall status + per-source failure rates
- **Alerting foundation**: Status changes (ok → degraded → down) trigger future alerts (Epic 3)
- **Integration**: Health endpoint enables external monitoring tools (Epic 9)

**Metrics Dashboard (Story 1.4):**
- **Real-time visibility**: See all 50+ ETL sources at a glance
- **Historical trends**: 7-day time-series charts for duration and error rates
- **Error drill-down**: Click any source to see detailed error logs with context
- **Performance tracking**: Identify slow ETLs, compare across sources

**Traceability:**
- **ETL execution ID**: Each metrics file has unique timestamp identifier
- **Error context**: Stack traces, input data, operation state preserved
- **Reproducibility**: Enough context to reproduce errors in development
- **Correlation**: Link metrics files to structured logs via timestamp + etl_name

**Required Signals for Future Epics:**
- **Epic 3 (Notifications)**: Health status changes, error rate thresholds
- **Epic 7 (Tech Debt)**: Performance baselines, improvement measurements
- **Epic 9 (API)**: System health for external monitoring integration

**Observability Best Practices:**
- **Minimal overhead**: Logging and metrics don't impact ETL performance (<50ms)
- **Actionable signals**: Every metric has clear interpretation and action
- **Correlation IDs**: Consistent naming enables cross-system tracing
- **No signal spam**: Only log events that require action or analysis

## Dependencies and Integrations

**All dependencies are existing** - Epic 1 introduces no new external dependencies. Implementation uses only libraries already in `pyproject.toml`.

### Core Dependencies (Existing)

| Dependency | Version | Purpose in Epic 1 | Usage |
|------------|---------|-------------------|-------|
| **pydantic** | >=2.11.5 | ETLMetrics, HealthStatus, MetricsSummary model validation | Model definitions, JSON serialization |
| **pydantic-settings** | >=2.9.1 | Configuration management (already used) | Settings access (no changes) |
| **dash** | >=2.0.0 | Dashboard framework, Flask server for health API | Add routes to app.server |
| **dash-bootstrap-components** | >=1.0.0 | UI components for metrics tab and search inputs | Tables, cards, input groups |
| **plotly** | >=5.0.0 | Time-series charts in metrics dashboard | Line charts, bar charts |
| **pandas** | >=2.2.3 | Metrics data aggregation and processing | DataFrame operations |
| **python-dateutil** | >=2.9.0 | Timestamp parsing and date arithmetic | Metrics time range filtering |
| **psutil** | >=6.0.0 | System metrics (memory, CPU) collection | Optional: memory_usage_mb, cpu_time_seconds |

### Built-in Python Modules (No Installation Required)

- **json**: Metrics file serialization/deserialization
- **logging**: Structured logging with JSON formatter
- **datetime**: Timestamp handling
- **pathlib**: File system operations
- **functools**: @lru_cache decorator for API response caching
- **typing**: Type hints for all new code

### Internal Dependencies (Existing Watchtower Modules)

**Modified Components:**
- `src/etl/base.py` - BaseETL.run() enhanced with metrics collection
- `src/web/dashboard/app.py` - Add /health and /metrics routes to app.server

**New Components (Epic 1):**
- `src/web/dashboard/components/metrics_tab.py` - New metrics dashboard tab
- `src/utils/metrics_collector.py` - Metrics aggregation utilities (optional helper)
- `src/utils/structured_logger.py` - JSON logging formatter (optional enhancement)

### Integration Points

**BaseETL Framework Integration:**
- Metrics collection hooks into existing template method pattern
- Zero changes to extract(), transform(), load() signatures
- Backward compatible: All 50+ existing ETLs work without modification
- Opt-in enhancement: New ETLs automatically inherit metrics collection

**Dash Dashboard Integration:**
- Health API routes added to existing Flask server (app.server)
- Metrics tab follows existing tab component patterns (VideoManager style)
- Search components integrate into existing tab layouts via callbacks
- Bootstrap styling consistent with existing dashboard theme

**File System Integration:**
- New directory: `data/metrics/` (auto-created on first run)
- Structure mirrors existing `data/{source}/output/` pattern
- Metrics files use same JSON format as ETL outputs
- Compatible with existing backup and retention strategies

**No Breaking Changes:**
- All existing ETLs continue working without code changes
- Dashboard tabs remain functional during Epic 1 rollout
- Health API is additive (doesn't replace existing endpoints)
- Search is opt-in per tab (doesn't modify existing filtering)

### Version Constraints

**Python Version:** >=3.10 (existing requirement, no change)

**Key Version Requirements:**
- Pydantic 2.x required for model features (already met)
- Dash 2.x required for modern callback patterns (already met)
- No version conflicts introduced

### Deployment Dependencies

**Development:**
- UV package manager (existing): `uv sync --all-extras`
- No new tools or build steps required

**Production:**
- Docker (existing): No Dockerfile changes needed
- UnRAID deployment (existing): Compatible with current setup
- Environment variables: Optional METRICS_RETENTION_DAYS (default: 30)

### Future Integration Points (Documented for Later Epics)

**Epic 3 (Notifications):**
- Alert rules will query `/metrics` endpoint for threshold violations
- Health status changes (ok → degraded) will trigger notifications

**Epic 7 (Tech Debt):**
- Performance profiling will extend metrics with cProfile integration
- Test coverage metrics will be added to ETLMetrics model

**Epic 9 (API):**
- External monitoring tools will call `/health` endpoint
- Metrics data may be exposed via REST API for programmatic access

## Acceptance Criteria (Authoritative)

These are the atomic, testable acceptance criteria extracted from Epic 1 stories in epics.md.

### Story 1.1: Enhanced Metrics Collection Infrastructure

**AC-1.1.1**: Given the existing BaseETL framework, when any ETL pipeline runs, then it automatically collects and stores: start_time, end_time, items_processed, items_failed, errors_detail, checkpoint_status

**AC-1.1.2**: Given metrics are collected, when an ETL completes, then metrics are stored in JSON format at `data/metrics/{etl_name}/{timestamp}_metrics.json`

**AC-1.1.3**: Given structured logging is implemented, when any log entry is created, then it includes: log level, timestamp, component, operation, context data

**AC-1.1.4**: Given an error occurs during ETL execution, when the error is logged, then error context is preserved including: stack traces, input data causing errors, operation state

### Story 1.2: Health Check API Endpoints

**AC-1.2.1**: Given the Dash application is running, when I call GET `/health`, then I receive JSON response with: status (ok/degraded/down), timestamp, version, uptime

**AC-1.2.2**: Given metrics data exists, when health status is calculated, then status is "degraded" if >10% of last 10 ETL runs failed

**AC-1.2.3**: Given the dashboard cannot read data files, when health check is called, then status is "down"

**AC-1.2.4**: Given the Dash application is running, when I call GET `/metrics`, then I receive JSON with: total_sources, total_items, last_etl_run_times, error_rates_per_source

### Story 1.3: Basic Full-Text Search

**AC-1.3.1**: Given I'm viewing any dashboard tab with content, when I type a search query in the search box, then results update in real-time (<1 second)

**AC-1.3.2**: Given a search query is entered, when content is filtered, then search matches against: title, description, source name, tags/categories

**AC-1.3.3**: Given search results are displayed, when matches are found, then matching terms are highlighted in results

**AC-1.3.4**: Given search is active, when I click clear search, then all content is displayed and search input is emptied

**AC-1.3.5**: Given filters are already applied, when I search, then search works within already-filtered results (not full dataset)

### Story 1.4: Metrics Dashboard Tab

**AC-1.4.1**: Given metrics data exists from Story 1.1, when I navigate to the "Metrics" dashboard tab, then I see a table of all ETL sources with: name, last run time, items processed, success rate (%), avg duration

**AC-1.4.2**: Given metrics history exists, when the metrics tab loads, then I see a chart showing ETL run times over the last 7 days

**AC-1.4.3**: Given ETLs have run in the last 24 hours, when metrics tab is displayed, then I see error count per source (last 24 hours)

**AC-1.4.4**: Given some ETLs have failed, when the metrics table is rendered, then failed ETLs are highlighted in red

**AC-1.4.5**: Given I'm viewing the metrics table, when I click a source, then I see detailed error logs for that source

## Traceability Mapping

This table maps each acceptance criterion to the spec sections that address it, the components that implement it, and test strategies.

| AC ID | Spec Section(s) | Component(s)/API(s) | Test Strategy |
|-------|----------------|---------------------|---------------|
| **AC-1.1.1** | Data Models (ETLMetrics), APIs (BaseETL.run()) | `src/etl/base.py` - BaseETL class | Unit test: Mock ETL execution, verify metrics object contains all required fields |
| **AC-1.1.2** | Data Models (Metrics Storage Schema), Workflows (ETL Execution) | `src/etl/base.py` - _save_metrics() | Integration test: Run sample ETL, verify JSON file created at correct path with valid schema |
| **AC-1.1.3** | Services (StructuredLogger), NFR-Observability | `src/utils/structured_logger.py` | Unit test: Create log entries, verify JSON format contains all required fields |
| **AC-1.1.4** | Data Models (ETLMetrics.errors_detail), APIs (BaseETL exception handling) | `src/etl/base.py` - _get_error_context() | Unit test: Trigger ETL error, verify error_detail includes stack trace, context, input data |
| **AC-1.2.1** | APIs (Health Check Endpoint), Data Models (HealthStatus) | `src/web/dashboard/app.py` - /health route | Integration test: Call GET /health, verify response structure matches HealthStatus model |
| **AC-1.2.2** | APIs (Health status determination logic), Workflows (Health Check Flow) | `src/web/dashboard/app.py` - calculate_health_status() | Unit test: Mock 10 runs with 2 failures (20%), verify status="degraded" |
| **AC-1.2.3** | APIs (Health Check Endpoint), NFR-Reliability (Error recovery) | `src/web/dashboard/app.py` - /health error handling | Integration test: Corrupt metrics file, verify status="down" |
| **AC-1.2.4** | APIs (Metrics Summary Endpoint), Data Models (MetricsSummary) | `src/web/dashboard/app.py` - /metrics route | Integration test: Call GET /metrics, verify response contains all required aggregations |
| **AC-1.3.1** | APIs (Search Component Interface), Workflows (Search Interaction Flow) | `src/web/dashboard/components/*_tab.py` - filter_content() | Performance test: Load 10K items, type query, verify results in <1s |
| **AC-1.3.2** | APIs (Search Component - searchable fields) | Dashboard tab callbacks - search logic | Unit test: Search "test", verify matches in title/description/source/tags |
| **AC-1.3.3** | APIs (Search Component - highlight_matches()) | Dashboard tab callbacks - HTML rendering | UI test: Search "arxiv", verify <mark> tags applied to matching text |
| **AC-1.3.4** | Workflows (Search Interaction Flow - clear button) | Dashboard tab UI - clear button callback | UI test: Enter search, click clear, verify all content displayed |
| **AC-1.3.5** | Workflows (Search + Existing Filters) | Dashboard tab callbacks - filter composition | Integration test: Apply source filter, then search, verify search operates on filtered subset |
| **AC-1.4.1** | Services (MetricsTab, MetricsManager), Data Models (MetricsSummary) | `src/web/dashboard/components/metrics_tab.py` | Integration test: Load metrics tab, verify table contains all expected columns and data |
| **AC-1.4.2** | Services (MetricsTab), Workflows (Metrics Dashboard Visualization - chart) | `src/web/dashboard/components/metrics_tab.py` - Plotly chart | Integration test: Verify chart component renders with 7-day data |
| **AC-1.4.3** | Services (MetricsManager - error aggregation) | MetricsManager.get_error_counts() | Unit test: Mock 24h metrics with errors, verify error count calculation |
| **AC-1.4.4** | Services (MetricsTab - conditional styling) | Dashboard callback - table rendering | UI test: Create metrics with success_rate <0.95, verify red highlighting |
| **AC-1.4.5** | Workflows (Metrics Dashboard - Source Selection) | MetricsTab callback - row click handler | Integration test: Click table row, verify error log details displayed |

## Risks, Assumptions, Open Questions

### Risks

**R-1.1: Metrics Collection Performance Impact** (Medium)
- **Description**: Metrics collection adds overhead to every ETL run, potentially slowing down data ingestion
- **Likelihood**: Medium (depends on file I/O performance)
- **Impact**: Medium (could degrade ETL performance below PRD targets)
- **Mitigation**:
  - Use asynchronous file writes where possible
  - Keep metrics payload small (<10KB per file)
  - Benchmark before/after metrics collection on slowest ETL
  - If >50ms overhead detected, make metrics collection opt-in via flag

**R-1.2: Dashboard Performance Degradation** (Low)
- **Description**: Adding search inputs and metrics tab could slow down dashboard load times
- **Likelihood**: Low (client-side operations, minimal data processing)
- **Impact**: Medium (violates <2s load time target)
- **Mitigation**:
  - Lazy-load metrics tab content (only fetch when tab selected)
  - Implement search debouncing (300ms delay)
  - Use component-level caching aggressively
  - Performance test with production data volumes before rollout

**R-1.3: Metrics Storage Disk Space** (Low)
- **Description**: Metrics files accumulate over time, potentially consuming significant disk space
- **Likelihood**: Low (JSON files are small, ~1-5KB each)
- **Impact**: Low (disk space is cheap, but cleanup needed)
- **Mitigation**:
  - Implement 30-day retention policy with automatic cleanup
  - Monitor disk usage in health check
  - Compress old metrics files if space becomes issue

**R-1.4: Breaking Changes to BaseETL** (Low)
- **Description**: Modifying BaseETL.run() could break existing ETL pipelines
- **Likelihood**: Low (changes are additive, not destructive)
- **Impact**: High (50+ ETLs could fail)
- **Mitigation**:
  - Make metrics collection optional via try-except (never raise on metrics errors)
  - Test with 3-5 representative ETLs before rolling out to all
  - Keep backward compatibility as primary design constraint

### Assumptions

**A-1.1**: Existing BaseETL framework has ETLMetrics model defined (verified: `src/etl/base.py` contains ETLMetrics)

**A-1.2**: All ETL pipelines extend BaseETL and call super().run() (to be verified during Story 1.1)

**A-1.3**: Dash dashboard runs on Flask server accessible at app.server (verified: existing architecture)

**A-1.4**: File system has write permissions to `data/` directory (standard deployment assumption)

**A-1.5**: Users access dashboard via modern browsers supporting ES6+ JavaScript (from PRD browser requirements)

**A-1.6**: Network latency between dashboard and server is <100ms (local network deployment)

**A-1.7**: ETL execution frequency averages 1-3 runs/day per source (based on current cron schedules)

### Open Questions

**Q-1.1**: Should metrics collection be mandatory or opt-in for all ETLs?
- **Recommendation**: Start mandatory (all new ETL runs save metrics), but never fail if metrics save fails
- **Decision needed**: Story 1.1 implementation
- **Owner**: Developer (Amelia)

**Q-1.2**: What is the exact threshold for "degraded" vs "down" health status?
- **Current spec**: >10% failure rate = degraded, >10% OR file read errors = down
- **Question**: Should we distinguish between "can't read files" (down) vs "high error rate" (degraded)?
- **Recommendation**: Keep simple for Epic 1, refine thresholds after observing real-world data
- **Decision needed**: Story 1.2 implementation

**Q-1.3**: Should search be added to ALL existing tabs or just new ones?
- **Current spec**: "Add search input component to each tab layout"
- **Question**: Retrofit all 15+ existing tabs or only add to 3-4 high-traffic tabs initially?
- **Recommendation**: Start with top 4 tabs (Videos, Papers, News, Deals), expand based on user feedback
- **Decision needed**: Story 1.3 scoping

**Q-1.4**: How long should health API cache responses?
- **Current spec**: 5 minutes
- **Question**: Is 5-minute staleness acceptable for health monitoring?
- **Recommendation**: Start with 5 minutes, reduce to 1 minute if real-time monitoring needed
- **Decision needed**: Story 1.2 implementation

**Q-1.5**: Should metrics files be compressed or archived after 7 days?
- **Current spec**: 30-day retention with automatic cleanup
- **Question**: Compress older files to save space vs. delete entirely?
- **Recommendation**: Simple deletion for Epic 1, compression can be added in Epic 7 if needed
- **Decision needed**: Story 1.1 retention policy

## Test Strategy Summary

### Test Levels and Coverage

**Unit Tests** (Target: 80% coverage)
- BaseETL metrics collection logic
- ETLMetrics Pydantic model validation
- Health status calculation algorithms
- Search filtering and highlighting functions
- MetricsManager data aggregation methods
- Structured logger JSON formatting

**Integration Tests** (Target: 70% coverage)
- End-to-end ETL execution with metrics persistence
- Health API endpoints with real metrics data
- Metrics API endpoints with time range filtering
- Dashboard tab data loading and rendering
- Search interaction with existing filters

**Performance Tests**
- ETL execution overhead benchmark (<50ms target)
- Health API response time (<200ms target)
- Metrics API response time (<500ms target)
- Search performance with 10,000 items (<1s target)
- Dashboard load time with Epic 1 additions (<2s target)

**UI/E2E Tests** (Using Playwright - existing dependency)
- Search input interaction and real-time filtering
- Search result highlighting verification
- Metrics tab navigation and table rendering
- Error log drill-down interaction
- Clear search button functionality

### Testing Frameworks (Existing)

**Pytest** (`pytest >=7.0`) - Primary test runner
- Existing test structure in `Tests/` directory
- Coverage reporting with `pytest-cov >=4.1.0`
- Configuration in `pyproject.toml` already set up

**Playwright** (`playwright >=1.51.0`) - E2E testing
- Already installed for web scraping
- Reuse for dashboard UI testing
- Browser automation for search and metrics tab

**Requests** (`requests >=2.32.3`) - API testing
- Test /health and /metrics endpoints
- Verify response schemas and status codes

### Test Organization

```
Tests/
├── unit/
│   ├── test_etl_metrics.py          # Story 1.1 - Metrics collection
│   ├── test_structured_logger.py    # Story 1.1 - Logging
│   ├── test_health_api.py           # Story 1.2 - Health calculations
│   └── test_search_component.py     # Story 1.3 - Search logic
├── integration/
│   ├── test_etl_with_metrics.py     # Story 1.1 - Full ETL execution
│   ├── test_health_endpoints.py     # Story 1.2 - API integration
│   └── test_metrics_tab.py          # Story 1.4 - Dashboard integration
├── performance/
│   ├── test_etl_overhead.py         # Metrics collection performance
│   ├── test_api_response_times.py   # Health/metrics API performance
│   └── test_search_performance.py   # Search with large datasets
└── e2e/
    ├── test_search_interaction.py   # Story 1.3 - Search UI
    └── test_metrics_dashboard.py    # Story 1.4 - Metrics tab UI
```

### Test Data Strategy

**Fixtures:**
- Sample ETL metrics JSON files (successful, failed, partial)
- Mock ETL pipelines for testing metrics collection
- Sample dashboard data (1K, 10K, 50K items) for search performance
- Corrupted metrics files for error handling tests

**Test Isolation:**
- Use temporary directories for metrics file writes
- Mock file I/O operations where appropriate
- Clean up test metrics after each test run
- Use pytest fixtures for reusable test data

### Acceptance Criteria Coverage

Each AC from Section "Acceptance Criteria (Authoritative)" maps to specific tests:
- **Story 1.1**: 4 ACs → 8 unit tests + 2 integration tests
- **Story 1.2**: 4 ACs → 6 unit tests + 4 integration tests + 2 performance tests
- **Story 1.3**: 5 ACs → 5 unit tests + 3 integration tests + 1 performance test + 3 E2E tests
- **Story 1.4**: 5 ACs → 5 unit tests + 3 integration tests + 2 E2E tests

**Total Test Estimate**: ~45 tests across all levels

### Testing Checklist (Pre-Story Completion)

**Story 1.1 - Metrics Collection:**
- [ ] Run 3 representative ETLs, verify metrics files created
- [ ] Trigger ETL error, verify error context captured
- [ ] Check metrics file size (<10KB)
- [ ] Benchmark ETL execution time before/after (<50ms delta)
- [ ] Verify structured logging output format

**Story 1.2 - Health API:**
- [ ] Call /health endpoint, verify JSON schema
- [ ] Mock different failure rates, verify correct status
- [ ] Corrupt metrics file, verify "down" status
- [ ] Call /metrics endpoint, verify aggregations
- [ ] Performance test: <200ms for /health, <500ms for /metrics

**Story 1.3 - Search:**
- [ ] Type search query in 4 tabs, verify real-time filtering
- [ ] Search with 10K items, verify <1s response
- [ ] Verify highlights on matched terms
- [ ] Test clear button functionality
- [ ] Combine search with existing filters

**Story 1.4 - Metrics Dashboard:**
- [ ] Navigate to metrics tab, verify table renders
- [ ] Verify 7-day chart displays
- [ ] Check error count accuracy
- [ ] Verify failed ETLs highlighted in red
- [ ] Click row, verify error log drill-down

### Continuous Integration

**Existing CI/CD** (from `.github/workflows` if exists):
- Run full test suite on pull requests
- Block merge if coverage drops below 70%
- Run performance benchmarks weekly
- Generate coverage reports

**Manual Testing Scenarios** (Before Epic 1 Release):
1. Run all 50+ ETLs once, verify no crashes
2. Load dashboard with Epic 1 changes, verify <2s load time
3. Search across all tabs with production data volumes
4. Monitor metrics tab for 24 hours, verify no memory leaks
5. Test health API from external monitoring tool (simulate Epic 9)
