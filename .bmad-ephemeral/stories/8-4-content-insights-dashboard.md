# Story 8.4: Content Insights Dashboard

Status: ready-for-dev

## Story

As a **user**,
I want **a dashboard showing my content consumption insights**,
So that **I understand my information diet**.

## Acceptance Criteria

1. **Given** I've been using Megalith for >1 week
   **When** I navigate to "Insights" tab
   **Then** I see: most-read sources, top categories, reading trends over time, content volume per day

2. **And** charts visualize data (bar charts, line charts, pie charts)

3. **And** insights cover last 7 days, 30 days, 90 days (selectable)

4. **And** I can export insights as JSON or CSV

## Tasks / Subtasks

- [ ] Create InsightsAnalyzer service in `src/analytics/insights.py` (AC: 1)
  - [ ] Process user activity data from `data/users/{user_id}/activity_log.json`
  - [ ] Calculate most-read sources by click count and engagement time
  - [ ] Analyze top categories by content interaction
  - [ ] Generate reading trends over time with daily aggregations
  - [ ] Compute content volume per day metrics

- [ ] Create Insights dashboard tab component (AC: 1, 2)
  - [ ] Create `src/web/dashboard/components/insights_tab.py`
  - [ ] Implement InsightsManager class for data loading and caching
  - [ ] Add "Insights" tab to main dashboard navigation
  - [ ] Follow single-callback pattern to prevent dashboard conflicts

- [ ] Implement data visualizations using Plotly (AC: 2)
  - [ ] Bar chart: Top 10 sources by clicks with interactive tooltips
  - [ ] Pie chart: Category distribution with percentage labels
  - [ ] Line chart: Daily content volume with trend analysis
  - [ ] Heatmap: Reading patterns by day/hour with color intensity
  - [ ] Responsive design for mobile compatibility

- [ ] Add time period selection functionality (AC: 3)
  - [ ] Implement date range selector (7 days, 30 days, 90 days)
  - [ ] Filter insights data based on selected time period
  - [ ] Update visualizations dynamically when period changes
  - [ ] Cache computed insights per time period (6-hour retention)

- [ ] Implement data export functionality (AC: 4)
  - [ ] Add export buttons for JSON and CSV formats
  - [ ] Generate structured data exports using pandas
  - [ ] Include all insight metrics and time period data
  - [ ] Handle large datasets with streaming exports

- [ ] **Testing** - Create comprehensive test suite for insights system
  - [ ] Unit tests for InsightsAnalyzer calculations and algorithms
  - [ ] Unit tests for data aggregation and filtering logic
  - [ ] Integration tests for dashboard tab component rendering
  - [ ] Performance tests for insights calculation and caching
  - [ ] E2E tests for export functionality and user interactions

- [ ] **Documentation** - Add user guide for insights dashboard
  - [ ] Document how insights are calculated and what metrics mean
  - [ ] Explain time period selection and filtering options
  - [ ] Add troubleshooting guide for insights and export issues
  - [ ] Include data privacy and retention information

## Dev Notes

### Architecture Patterns and Constraints

The content insights dashboard must integrate with existing BaseETL and dashboard architecture while preserving the <30-minute source integration capability. Use existing user activity data from Story 8.1 and maintain consistency with current dashboard patterns [Source: docs/architecture.md#Decision-Summary].

Key architectural constraints:
- Leverage existing user activity data from `data/users/{user_id}/activity_log.json`
- Integration with existing dashboard component system
- Performance: Must handle insights calculation without blocking dashboard rendering
- Data Visualization: Responsive Plotly charts with mobile compatibility
- Intelligent Caching: 6-hour cache for computed insights to optimize performance

### Source Tree Components to Touch

```
src/analytics/                           # ENHANCEMENT - Analytics services (Epic 8.4)
├── insights.py                         # InsightsAnalyzer class - insights calculation
├── models.py                           # Analytics-specific Pydantic models
└── __init__.py                         # Package initialization

src/web/dashboard/components/           # NEW - Insights dashboard tab
├── insights_tab.py                     # NEW - Insights tab with visualizations
├── base_component.py                   # EXISTING - Update for insights tab integration
└── insights_charts.py                  # NEW - Reusable chart components

data/cache/                            # NEW - Insights cache storage
└── insights/
    ├── {user_id}_{period}_insights.json # Cached insights calculations
    ├── chart_data.json                 # Pre-computed chart data
    └── cache_metadata.json             # Cache hit rates and performance metrics

utils/                                  # ENHANCEMENT - Shared utilities
├── insights_utils.py                   # NEW - Shared insights calculation utilities
└── export_utils.py                     # NEW - Data export utilities (pandas-based)
```

### Testing Standards Summary

Follow existing pytest patterns with >70% coverage target. Test files should be in `Tests/analytics/` with comprehensive coverage of:
- Insights calculation algorithms and data aggregation accuracy
- Time period filtering and data processing logic
- Dashboard component rendering and chart generation
- Cache performance and hit rate validation
- Export functionality and data format validation

Use existing patterns: `test_insights_analyzer.py`, `test_insights_tab.py`, `test_insights_charts.py` with mocking for external dependencies.

### Project Structure Notes

The content insights dashboard follows the existing component-based architecture pattern:
- Models: Pydantic for type safety and validation (UserInsights, ChartData, ExportFormat)
- Caching: Intelligent 6-hour cache for performance optimization
- Integration: New dashboard tab following existing tab patterns
- Testing: pytest with fixtures and mocks following established patterns
- Visualization: Plotly integration with responsive design and accessibility

**No conflicts detected** - aligns with unified project structure and existing patterns. Integrates cleanly with current dashboard architecture and leverages user activity data from Story 8.1.

### Prerequisites

- **Story 5.5.1 (Per-User Dashboard Preferences)**: Must be completed first for user activity tracking infrastructure
- **Story 8.1 (Usage-Based Recommendations)**: Must be completed first for user activity logging and data foundation
- **Existing dashboard components**: Leverage current tab architecture for seamless integration
- **BaseETL framework**: Use existing metrics and logging patterns for insights calculation

### References

- [Source: docs/epics.md#Story-84-Content-Insights-Dashboard] - Epic requirements and acceptance criteria
- [Source: docs/architecture.md#Data-Storage-Patterns] - Caching patterns and performance optimization
- [Source: docs/architecture.md#Decision-Summary] - Technology choices: Pydantic, intelligent caching, Plotly visualizations
- [Source: docs/epic-8-implementation-readiness-report.md] - Epic 8 implementation blueprint and readiness assessment
- [Source: stories/8-1-usage-based-recommendations.md] - User activity tracking foundation and data sources
- [Source: stories/8-2-simple-trend-indicators.md] - Analytics services patterns and caching strategies

## Dev Agent Record

### Context Reference

- **Context File**: `8-4-content-insights-dashboard.context.xml`
- **Generated**: 2025-11-18
- **Generator**: BMAD Story Context Workflow

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

### Change Log

**Created**: 2025-11-18 - Initial story draft with comprehensive requirements and technical implementation plan