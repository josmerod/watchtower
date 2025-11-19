# Story 1.4: Metrics Dashboard Tab

**Epic**: 1 - Observability Infrastructure
**Status**: done
**Date**: 2025-01-16
**Author**: Joshi

---

## User Story

**As a** developer/operator,
**I want** a dashboard tab showing ETL metrics and system health,
**So that** I can visualize system performance and identify issues.

---

## Acceptance Criteria

1. **Given** metrics data exists from Story 1.1, **when** I navigate to the "Metrics" dashboard tab, **then** I see a table of all ETL sources with: name, last run time, items processed, success rate (%), avg duration

2. **And** I see a chart showing ETL run times over the last 7 days

3. **And** I see error count per source (last 24 hours)

4. **And** failed ETLs are highlighted in red

5. **And** I can click a source to see detailed error logs

---

## Tasks

- [ ] Create new tab `src/web/dashboard/components/metrics_tab.py`
- [ ] Use dash-bootstrap-components Table for metrics display
- [ ] Use Plotly for time-series charts
- [ ] Load data from `data/metrics/` directory
- [ ] Implement MetricsManager class following VideoManager pattern
- [ ] Add single callback for source selection and error log drill-down

---

## Context Reference

- **Context File**: `1-4-metrics-dashboard-tab.context.xml`
- **Generated**: 2025-01-16
- **Generator**: BMAD Story Context Workflow

---

## Dev Notes

- **Prerequisites**: Story 1.1 (needs metrics data), Story 1.2 (health calculation logic)
- **Dependencies**: Plotly, Dash, Bootstrap components
- **Constraints**:
  - Load time <2 seconds with 7 days of data
  - Single callback pattern to prevent conflicts
  - Graceful handling of missing/corrupted metrics files
  - Bootstrap styling consistency
- **Testing**: Performance testing with historical data required