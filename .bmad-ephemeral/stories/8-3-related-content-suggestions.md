# Story 8.3: Related Content Suggestions

Status: ready-for-dev

## Story

As a **user**,
I want **to see related content when viewing an item**,
So that **I can explore connected topics**.

## Acceptance Criteria

1. **Given** I'm viewing a content item detail
   **When** the page loads
   **Then** I see "Related Content" section with 3-5 similar items

2. **And** similarity is based on: shared categories, similar titles, same source domain, keyword overlap

3. **And** related items are clickable links

4. **And** items are sorted by relevance score

## Tasks / Subtasks

- [ ] Create RelatedContentEngine service in `src/analytics/related.py` (AC: 2, 4)
  - [ ] Implement similarity scoring algorithm (Category: +30, Title: +25, Domain: +20, Keywords: +5 each)
  - [ ] Calculate title similarity using string matching (>60% threshold)
  - [ ] Extract and compare keywords between content items
  - [ ] Implement multi-factor relevance scoring system
  - [ ] Sort results by relevance score (highest first)

- [ ] Create Pydantic models for related content data (AC: 1, 4)
  - [ ] RelatedContent model with content_id, title, url, relevance_score
  - [ ] SimilarityScore model with detailed scoring breakdown
  - [ ] ContentSimilarity model for comparison results

- [ ] Implement intelligent caching system (Performance optimization)
  - [ ] Create RelatedContentCache for 24-hour result caching
  - [ ] Cache key generation based on content_id and similarity factors
  - [ ] Cache invalidation on content updates
  - [ ] Performance monitoring for cache hit rates

- [ ] Integrate related content into dashboard UI (AC: 1, 3)
  - [ ] Add "Related Content" section to content detail views
  - [ ] Display 3-5 related items using Bootstrap card components
  - [ ] Implement clickable links to related content
  - [ ] Responsive design for mobile compatibility

- [ ] **Testing** - Create comprehensive test suite for related content system
  - [ ] Unit tests for RelatedContentEngine similarity algorithms
  - [ ] Unit tests for scoring accuracy and edge cases
  - [ ] Integration tests for dashboard component display
  - [ ] Performance tests for caching effectiveness
  - [ ] E2E tests for user interaction flows

- [ ] **Documentation** - Add user guide for related content features
  - [ ] Document how related content is calculated and ranked
  - [ ] Explain similarity factors and relevance scoring
  - [ ] Add troubleshooting guide for related content issues
  - [ ] Include performance optimization guidelines

## Dev Notes

### Architecture Patterns and Constraints

The related content system must integrate with existing BaseETL and dashboard architecture while preserving the <30-minute source integration capability. Use existing Pydantic models and intelligent caching to maintain consistency with current architecture [Source: docs/architecture.md#Decision-Summary].

Key architectural constraints:
- On-demand calculation with 24-hour intelligent caching for performance
- Integration with existing dashboard component system
- Performance: Must handle similarity calculations without blocking content rendering
- Real-time analysis: Multi-factor similarity scoring with transparent algorithms

### Source Tree Components to Touch

```
src/analytics/                           # NEW - Analytics services (Epic 8.3)
├── related.py                          # RelatedContentEngine class - similarity calculation
├── models.py                           # Analytics-specific Pydantic models
├── cache.py                            # RelatedContentCache - intelligent caching system
└── __init__.py                         # Package initialization

src/web/dashboard/components/           # EXISTING - Enhancement
├── [existing_tabs].py                  # UPDATE - Add related content sections
├── related_content_component.py       # NEW - Reusable related content component
└── content_detail_modal.py             # UPDATE - Integrate related content

data/cache/                            # NEW - Related content cache storage
└── related_content/
    ├── {content_hash}_related.json     # Cached related content results
    ├── similarity_scores.json         # Pre-computed similarity scores
    └── cache_metadata.json             # Cache hit rates and performance metrics

utils/                                  # EXISTING - Enhancement
├── similarity_utils.py                 # NEW - Shared similarity calculation utilities
└── cache_utils.py                      # NEW - Shared caching utilities
```

### Testing Standards Summary

Follow existing pytest patterns with >70% coverage target. Test files should be in `Tests/analytics/` with comprehensive coverage of:
- Similarity scoring algorithms and accuracy
- Title similarity calculation and edge cases
- Cache performance and hit rate validation
- Dashboard component integration and user interaction
- Performance benchmarks for on-demand calculations

Use existing patterns: `test_related_content_engine.py`, `test_similarity_scoring.py`, `test_related_content_cache.py` with mocking for external dependencies.

### Project Structure Notes

The related content system follows the existing component-based architecture pattern:
- Models: Pydantic for type safety and validation (RelatedContent, SimilarityScore)
- Caching: Intelligent 24-hour cache for performance optimization
- Integration: On-demand calculation with non-blocking background jobs
- Testing: pytest with fixtures and mocks following established patterns
- Performance: Smart caching preserves dashboard responsiveness

**No conflicts detected** - aligns with unified project structure and existing patterns. Integrates cleanly with current dashboard architecture.

### Prerequisites

- **Story 4.2 (Enhanced NLP Classification)**: Must be completed first for category analysis and keyword extraction
- **Story 4.3 (Heuristic Relevance Scoring)**: Must be completed first for relevance scoring patterns
- **Existing dashboard components**: Leverage current content detail view architecture for seamless integration
- **BaseETL framework**: Use existing metrics and logging patterns for similarity calculations

### References

- [Source: docs/epics.md#Story-83-Related-Content-Suggestions] - Epic requirements and acceptance criteria
- [Source: docs/architecture.md#Data-Storage-Patterns] - Caching patterns and performance optimization
- [Source: docs/architecture.md#Decision-Summary] - Technology choices: Pydantic, intelligent caching, background jobs
- [Source: docs/epic-8-implementation-readiness-report.md] - Epic 8 implementation blueprint and readiness assessment
- [Source: stories/8-1-usage-based-recommendations.md] - Previous story implementation patterns for analytics integration
- [Source: stories/8-2-simple-trend-indicators.md] - Previous story implementation patterns for analytics services

## Dev Agent Record

### Context Reference

- **Context File**: `8-3-related-content-suggestions.context.xml`
- **Generated**: 2025-11-18
- **Generator**: BMAD Story Context Workflow

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

### Change Log

**Created**: 2025-11-18 - Initial story draft with comprehensive requirements and technical implementation plan