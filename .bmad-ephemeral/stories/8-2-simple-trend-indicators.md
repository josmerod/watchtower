# Story 8.2: Simple Trend Indicators

Status: ready-for-dev

## Story

As a **user**,
I want **to see trending topics and increasing activity**,
So that **I'm aware of emerging trends**.

## Acceptance Criteria

1. **Given** content is being aggregated
   **When** I view any dashboard tab
   **Then** trending items are marked with "🔥 Trending" badge

2. **And** trend calculation uses: item count increase, category growth, keyword frequency changes

3. **And** trends are calculated over 7-day rolling window

4. **And** I can filter to show only trending content

5. **And** trend indicators show % change (e.g., "+40% this week")

## Tasks / Subtasks

- [ ] Create TrendAnalyzer service in `src/analytics/trends.py` (AC: 2, 3)
  - [ ] Implement 7-day rolling window trend analysis
  - [ ] Calculate item count increase per category
  - [ ] Calculate category growth rates
  - [ ] Analyze keyword frequency changes
  - [ ] Apply >30% increase threshold for trending status

- [ ] Create Pydantic models for trend data (AC: 1, 5)
  - [ ] TrendIndicator model with trend_direction and percentage_change
  - [ ] TrendAnalysis model with metrics and confidence intervals
  - [ ] TrendBadge model for UI display information

- [ ] Implement daily background trend calculation job (AC: 3)
  - [ ] Create TrendScheduler for daily execution
  - [ ] Store trend data in `data/analytics/trends/{date}_trends.json`
  - [ ] Calculate trends for all content categories
  - [ ] Apply trend detection algorithms

- [ ] Integrate trend indicators into dashboard UI (AC: 1, 4, 5)
  - [ ] Add "🔥 Trending" badges to content cards
  - [ ] Add "Trending" filter option to each tab
  - [ ] Display % change indicators on trending items
  - [ ] Implement single-callback pattern for trend filtering

- [ ] **Testing** - Create comprehensive test suite for trend system
  - [ ] Unit tests for TrendAnalyzer algorithms
  - [ ] Unit tests for trend calculation accuracy
  - [ ] Integration tests for dashboard component display
  - [ ] Performance tests for daily trend generation

- [ ] **Documentation** - Add user guide for trend features
  - [ ] Document how trends are calculated and displayed
  - [ ] Explain filtering options and badge meanings
  - [ ] Add troubleshooting guide for trend issues

## Dev Notes

### Architecture Patterns and Constraints

The trend analysis system must integrate with existing BaseETL and dashboard architecture while preserving the <30-minute source integration capability. Use existing Pydantic models and JSON file storage to maintain consistency with current architecture [Source: docs/architecture.md#Decision-Summary].

Key architectural constraints:
- File-based JSON storage for trend data [Source: docs/architecture.md#Data-Storage-Patterns]
- Integration with existing dashboard component system
- Performance: Must handle trend calculation without blocking dashboard rendering
- Real-time analysis: Daily background job for trend calculation

### Source Tree Components to Touch

```
src/analytics/                           # NEW - Analytics services (Epic 8.2)
├── trends.py                           # TrendAnalyzer class - trend calculation logic
├── models.py                           # Analytics-specific Pydantic models
└── __init__.py                         # Package initialization

src/web/dashboard/components/           # EXISTING - Enhancement
├── [existing_tabs].py                  # UPDATE - Add trend badges and filtering
├── base_component.py                   # EXISTING - Update for trend integration
└── trend_filter.py                     # NEW - Shared trend filtering component

data/analytics/                         # NEW - Analytics data storage
└── trends/
    ├── {date}_trends.json             # Daily trend analysis results
    ├── trend_indicators.json          # Latest trend indicators
    └── trend_settings.json            # Trend calculation configuration

utils/                                  # EXISTING - Enhancement
├── trend_scheduler.py                  # NEW - Background trend calculation job
└── analytics_utils.py                  # NEW - Shared analytics utilities
```

### Testing Standards Summary

Follow existing pytest patterns with >70% coverage target. Test files should be in `Tests/analytics/` with comprehensive coverage of:
- Trend analysis algorithms and accuracy
- 7-day rolling window calculations
- Dashboard component integration and user interaction
- Background job reliability and performance
- Trend detection threshold validation

Use existing patterns: `test_trend_analyzer.py`, `test_trends_dashboard.py`, `test_scheduler.py` with mocking for external dependencies.

### Project Structure Notes

The trend analysis system follows the existing component-based architecture pattern:
- Models: Pydantic for type safety and validation (TrendIndicator, TrendAnalysis)
- Storage: JSON files for proven performance and consistency with existing patterns
- Integration: Non-blocking background jobs to preserve dashboard performance
- Testing: pytest with fixtures and mocks following established patterns
- Real-time Processing: Daily trend calculation with configurable thresholds

**No conflicts detected** - aligns with unified project structure and existing patterns. Integrates cleanly with current dashboard architecture.

### Prerequisites

- **Story 4.2 (Enhanced NLP Classification)**: Must be completed first for keyword extraction and category analysis
- **Existing dashboard components**: Leverage current tab architecture for seamless integration
- **BaseETL framework**: Use existing metrics and logging patterns for trend calculation

### References

- [Source: docs/epics.md#Story-82-Simple-Trend-Indicators] - Epic requirements and acceptance criteria
- [Source: docs/architecture.md#Data-Storage-Patterns] - JSON storage patterns and file structure
- [Source: docs/architecture.md#Decision-Summary] - Technology choices: Pydantic, JSON storage, background jobs
- [Source: docs/epic-8-implementation-readiness-report.md] - Epic 8 implementation blueprint and readiness assessment
- [Source: stories/8-1-usage-based-recommendations.md] - Previous story implementation patterns for analytics integration

## Dev Agent Record

### Context Reference

- **Context File**: `8-2-simple-trend-indicators.context.xml`
- **Generated**: 2025-11-18
- **Generator**: BMAD Story Context Workflow

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

### Change Log

**Created**: 2025-11-18 - Initial story draft with comprehensive requirements and technical implementation plan