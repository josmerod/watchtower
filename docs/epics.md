# megalith - Epic Breakdown

**Author:** Joshi
**Date:** 2025-01-11
**Project Level:** High Complexity (Architectural)
**Target Scale:** 50+ data sources → 100+ sources

---

## Overview

This document provides the complete epic and story breakdown for **megalith (Watchtower)**, decomposing the requirements from the [PRD](./PRD.md) into implementable stories.

### Final Epic Structure (9 Epics + Buffers)

**Stakeholder Review Applied**: Incorporated feedback from Architect (Winston), Developer (Amelia), and UX Designer (Sally)

**EPIC 1: Observability Infrastructure**
- **Value**: Essential monitoring foundation - see system health and catch issues early
- **Scope**:
  - **Backend Track**: ETL metrics collection, error logging improvements, structured logging, checkpoint monitoring
  - **Frontend Track**: Basic search functionality, metrics dashboard tab, health status indicators
- **Duration**: 3 weeks
- **Phase**: Foundation (Weeks 1-3)
- **Architect Feedback Applied**: Split into backend (Track A - Week 1-2) and frontend (Track B - Week 2-3). Backend enables all future work.
- **UX Feedback Applied**: Added basic search (FR-5.1 requirement) - critical for current usability

**EPIC 2: Personalized Intelligence Hub**
- **Value**: Transform dashboard from "one-size-fits-all" to "tailored for you"
- **Scope**:
  - Dashboard customization (tab ordering, visibility)
  - Saved filter presets per domain
  - Personal shortcuts to favorite sources
  - Mobile-responsive layout improvements (basic)
  - Items-per-page preferences
- **Duration**: 4 weeks
- **Phase**: Growth Phase 1 (Weeks 5-8)
- **UX Feedback Applied**: MOVED BEFORE notifications - personalization enables smart filtering. Added mobile basics for notification support.
- **Developer Feedback Applied**: Owns all frontend/UI changes - clear boundaries from Epic 3

**EPIC 3: Smart Notifications & Alerts**
- **Value**: Never miss time-sensitive opportunities (free courses, deals, breaking news)
- **Scope**:
  - Backend alert system (watcher integration, rule engine)
  - Browser notifications with filtering (uses Epic 2's saved filters)
  - Notification history and management
  - Basic email alerts (optional)
- **Duration**: 3 weeks
- **Phase**: Growth Phase 1 (Weeks 9-11)
- **UX Feedback Applied**: MOVED AFTER personalization - notifications need Epic 2's filtering to avoid noise
- **Developer Feedback Applied**: Starts Week 9 (after Epic 1 backend is complete), clear dependency respected

**EPIC 4: Intelligent Data Quality**
- **Value**: Higher signal-to-noise ratio through smart filtering and deduplication
- **Scope**:
  - Duplicate detection (title + content similarity)
  - Improved NLP classification accuracy
  - Simple relevance scoring (heuristic: recency, source reputation, engagement)
  - Automated retention policies per source type
  - Data validation improvements
- **Duration**: 4 weeks
- **Phase**: Growth Phase 2 (Weeks 13-16)
- **Developer Feedback Applied**: MOVED to run AFTER Epic 3 (sequential, not parallel) - both touch data pipeline. Clear ownership: Epic 4 owns backend data processing.
- **Architect Feedback Applied**: Includes data migration for changed schemas

**EPIC 5: Multi-User Foundation**
- **Value**: Enable 3-5 colleagues to use Megalith (authentication only, shared preferences)
- **Scope**:
  - User authentication (bcrypt, session management, CSRF protection)
  - Login/logout/registration UI
  - Basic user profiles (username, email)
  - Session persistence
  - Security hardening (rate limiting, secure cookies)
- **Duration**: 3 weeks
- **Phase**: Growth Phase 2 (Weeks 17-19)
- **Architect Feedback Applied**: DESCOPED to authentication only (was 3-4 weeks for auth + profiles + per-user prefs + shared sources). Proper auth takes 2-3 weeks alone.
- **Note**: Per-user preferences come in Epic 5.5

**EPIC 5.5: Per-User Personalization**
- **Value**: Each colleague gets their own customized Megalith experience
- **Scope**:
  - Per-user dashboard preferences (from Epic 2, now multi-user)
  - Per-user notification settings (from Epic 3, now multi-user)
  - Shared vs. personal sources
  - User onboarding experience (welcome tour, source selection wizard)
  - Data migration from single-user to multi-user structure
- **Duration**: 3 weeks
- **Phase**: Growth Phase 3 (Weeks 21-23)
- **Architect Feedback Applied**: Split from Epic 5 - refactoring data layer from single to multi-user is significant work
- **UX Feedback Applied**: Added onboarding experience for colleague adoption success

**EPIC 6: Source Integration Acceleration**
- **Value**: Reduce source integration from 30min → 15min with basic tooling
- **Scope**:
  - Source registry (JSON/YAML catalog with metadata)
  - Simple CLI scaffolding tool (`megalith new-source <name>`)
  - Documentation templates for new sources
  - Integration testing helpers
  - Source performance dashboard
- **Duration**: 2 weeks
- **Phase**: Growth Phase 3 (Weeks 24-25)
- **Why Moved**: Not urgent - 30min already works. Deprioritized after multi-user (more critical).

**EPIC 7: Technical Debt & Performance Sprint**
- **Value**: Maintain velocity as system scales to 100+ sources
- **Scope**:
  - **Measurable Goals**:
    - Standardize 10 oldest ETLs to BaseETL v2.0 pattern
    - Increase test coverage from 40% → 70% (unit tests)
    - Reduce dashboard load time from 2s → 1s (optimization)
    - Refactor 5 most complex modules (cyclomatic complexity > 15)
    - Performance profiling of all 50+ ETL pipelines
- **Duration**: 3 weeks
- **Phase**: Growth Phase 3 (Weeks 26-28)
- **Developer Feedback Applied**: Added concrete, measurable goals - prevents scope creep
- **Architect Feedback Applied**: Includes data migration for refactored ETL patterns

**EPIC 8: Simple Intelligence Features**
- **Value**: Proactive insights using heuristics (no ML research required)
- **Scope**: Usage-based recommendations ("sources you read most"), simple trend indicators (change %), related content suggestions
- **Duration**: 2-3 weeks
- **Phase**: Vision Phase 1 (Months 5-6)
- **Why Changed**: DESCOPED heavily - removed ML/AI research. Focus on simple heuristics that deliver 80% of value in 20% of time.

**EPIC 9: Platform Ecosystem & Integrations**
- **Value**: Community growth and external integrations
- **Scope**: REST API, webhook support, Slack/Discord integration, browser extension, API documentation
- **Duration**: 4-6 weeks
- **Phase**: Vision Phase 2 (Months 7-9)
- **Why Changed**: Kept largely the same but removed "marketplace" (too ambitious) - focus on API + key integrations

---

### Final Execution Strategy with Buffers

**Full Timeline: 32 weeks (8 months) with 4 buffer weeks built in**

**Phase 1: Foundation (Weeks 1-4)**
- Week 1-3: Epic 1 (Observability Infrastructure)
- Week 4: **BUFFER** - Review, retrospective, minor fixes

**Phase 2: Growth Phase 1 - User Experience (Weeks 5-12)**
- Week 5-8: Epic 2 (Personalized Intelligence Hub)
- Week 9-11: Epic 3 (Smart Notifications & Alerts)
- Week 12: **BUFFER** - Review, retrospective, integration testing

**Phase 3: Growth Phase 2 - Data & Collaboration (Weeks 13-20)**
- Week 13-16: Epic 4 (Intelligent Data Quality)
- Week 17-19: Epic 5 (Multi-User Foundation)
- Week 20: **BUFFER** - Review, security audit, multi-user testing

**Phase 4: Growth Phase 3 - Refinement (Weeks 21-29)**
- Week 21-23: Epic 5.5 (Per-User Personalization)
- Week 24-25: Epic 6 (Source Integration Acceleration)
- Week 26-28: Epic 7 (Technical Debt & Performance Sprint)
- Week 29: **BUFFER** - Review, performance validation, documentation

**Phase 5: Vision Phase (Months 8-11)**
- Months 8-9: Epic 8 (Simple Intelligence Features)
- Months 10-11: Epic 9 (Platform Ecosystem & Integrations)

**Key Improvements Applied:**
1. ✅ **Clear Dependencies**: Epic 3 (Notifications) after Epic 2 (Personalization) - UX sequencing correct
2. ✅ **No Parallel Conflicts**: Removed Epic 3/4 parallelization - sequential prevents merge conflicts
3. ✅ **Realistic Multi-User**: Split into Epic 5 (auth only, 3 weeks) + Epic 5.5 (per-user prefs, 3 weeks)
4. ✅ **Buffer Weeks**: 4 review weeks built into timeline - allows for overruns and quality checks
5. ✅ **Measurable Goals**: Epic 7 has concrete targets (test coverage 40%→70%, load time 2s→1s)
6. ✅ **Mobile Basics**: Added to Epic 2 for notification support
7. ✅ **Onboarding UX**: Added to Epic 5.5 for colleague adoption success
8. ✅ **Migration Stories**: Explicit data migration in Epics 4, 5.5, 7

### Updated Dependency Map

```
Epic 1 (Observability)
  ├─→ Epic 3 (Notifications - needs backend alert system)
  └─→ Epic 7 (Tech Debt - needs metrics to measure improvements)

Epic 2 (Personalization)
  ├─→ Epic 3 (Notifications - needs saved filters for smart alerts)
  ├─→ Epic 5.5 (Per-User Prefs - needs personalization patterns)
  └─→ Epic 8 (Intelligence - needs usage patterns)

Epic 3 (Notifications)
  └─→ Epic 5.5 (Per-User Notifications - needs per-user settings)

Epic 4 (Data Quality)
  └─→ Epic 8 (Intelligence - needs quality data for insights)

Epic 5 (Multi-User Auth)
  ├─→ Epic 5.5 (Per-User Prefs - needs auth first)
  ├─→ Epic 8 (Intelligence - needs user behavior data)
  └─→ Epic 9 (Ecosystem - API needs auth layer)

Epic 5.5 (Per-User Prefs)
  └─→ Epic 8 (Intelligence - needs per-user data)

Epic 6 (Integration Tools) → Independent (can run anytime)
Epic 7 (Tech Debt) → Recommended after Epics 1-5.5 (needs baseline metrics)
Epic 8 (Intelligence) → Depends on Epics 2, 4, 5.5 (needs data + users)
Epic 9 (Ecosystem) → Depends on Epic 5 (API needs auth)
```

### Value Delivery Timeline

**Month 1 (Weeks 1-4)**:
- ✅ Observability infrastructure + basic search
- 🎯 Value: System health visibility, find content easily

**Month 2 (Weeks 5-8)**:
- ✅ Personalized dashboard (saved filters, shortcuts, mobile basics)
- 🎯 Value: "My Megalith" - tailored experience

**Month 3 (Weeks 9-12)**:
- ✅ Smart notifications with filtering
- 🎯 Value: Never miss time-sensitive opportunities

**Month 4 (Weeks 13-16)**:
- ✅ Intelligent data quality (deduplication, better classification)
- 🎯 Value: Higher signal-to-noise ratio

**Month 5 (Weeks 17-20)**:
- ✅ Multi-user authentication
- 🎯 Value: Colleagues can create accounts (shared preferences)

**Month 6 (Weeks 21-23)**:
- ✅ Per-user personalization + onboarding
- 🎯 Value: Each colleague has customized experience

**Month 7 (Weeks 24-29)**:
- ✅ Integration tooling + technical debt sprint
- 🎯 Value: Faster source additions, better performance, healthier codebase

**Months 8-11**:
- ✅ Simple intelligence + platform ecosystem
- 🎯 Value: Proactive insights + external integrations

---

## Epic 1: Observability Infrastructure

**Epic Goal**: Essential monitoring foundation - see system health and catch issues early. Enable all future work with robust metrics collection and provide users with basic search functionality.

**Duration**: 3 weeks | **Phase**: Foundation (Weeks 1-3)

### Story 1.1: Enhanced Metrics Collection Infrastructure

As a **developer**,
I want **comprehensive ETL metrics collection with structured logging**,
So that **I can monitor system health and diagnose issues quickly**.

**Acceptance Criteria:**

**Given** the existing BaseETL framework
**When** any ETL pipeline runs
**Then** it automatically collects and stores: start_time, end_time, items_processed, items_failed, errors_detail, checkpoint_status

**And** metrics are stored in JSON format at `data/metrics/{etl_name}/{timestamp}_metrics.json`

**And** structured logging includes: log level, timestamp, component, operation, context data

**And** error context is preserved (stack traces, input data causing errors)

**Prerequisites:** None (foundation story)

**Technical Notes:**
- Extend ETLMetrics Pydantic model with additional fields
- Implement structured logging using Python logging with JSON formatter
- Create metrics storage directory structure
- Update BaseETL to automatically save metrics after each run

---

### Story 1.2: Health Check API Endpoints

As a **system operator**,
I want **REST API endpoints to check system health**,
So that **I can monitor Megalith status and integrate with monitoring tools**.

**Acceptance Criteria:**

**Given** the Dash application is running
**When** I call GET `/health`
**Then** I receive JSON response with: status (ok/degraded/down), timestamp, version, uptime

**And** status is "degraded" if >10% of last 10 ETL runs failed

**And** status is "down" if dashboard cannot read data files

**When** I call GET `/metrics`
**Then** I receive JSON with: total_sources, total_items, last_etl_run_times, error_rates_per_source

**Prerequisites:** Story 1.1 (needs metrics data)

**Technical Notes:**
- Add Flask/Dash server endpoints in `src/web/dashboard/app.py`
- Read latest metrics files from `data/metrics/` directory
- Calculate health status from recent ETL metrics
- Cache metrics response for 5 minutes

---

### Story 1.3: Basic Full-Text Search

As a **user**,
I want **to search across all content in current dashboard tab**,
So that **I can quickly find specific articles, papers, or deals**.

**Acceptance Criteria:**

**Given** I'm viewing any dashboard tab with content
**When** I type a search query in the search box
**Then** results update in real-time (<1 second)

**And** search matches against: title, description, source name, tags/categories

**And** matching terms are highlighted in results

**And** I can clear search with one click

**And** search works within already-filtered results

**Prerequisites:** None (independent feature)

**Technical Notes:**
- Add search input component to each tab layout
- Implement client-side filtering using Dash callbacks
- Use case-insensitive substring matching (no complex indexing needed)
- Highlight matches using HTML `<mark>` tags
- Search state persists within session per tab

---

### Story 1.4: Metrics Dashboard Tab

As a **developer/operator**,
I want **a dashboard tab showing ETL metrics and system health**,
So that **I can visualize system performance and identify issues**.

**Acceptance Criteria:**

**Given** metrics data exists from Story 1.1
**When** I navigate to the "Metrics" dashboard tab
**Then** I see a table of all ETL sources with: name, last run time, items processed, success rate (%), avg duration

**And** I see a chart showing ETL run times over the last 7 days

**And** I see error count per source (last 24 hours)

**And** failed ETLs are highlighted in red

**And** I can click a source to see detailed error logs

**Prerequisites:** Story 1.1 (needs metrics data), Story 1.2 (health calculation logic)

**Technical Notes:**
- Create new tab `src/web/dashboard/components/metrics_tab.py`
- Use dash-bootstrap-components Table for metrics display
- Use Plotly for time-series charts
- Load data from `data/metrics/` directory
- Implement MetricsManager class following VideoManager pattern
- Add single callback for source selection

---

## Epic 2: Personalized Intelligence Hub

**Epic Goal**: Transform dashboard from "one-size-fits-all" to "tailored for you" - enable each user to customize their Megalith experience.

**Duration**: 4 weeks | **Phase**: Growth Phase 1 (Weeks 5-8)

### Story 2.1: Saved Filter Presets

As a **user**,
I want **to save my frequently-used filter combinations as named presets**,
So that **I can quickly apply complex filters without re-configuring them each time**.

**Acceptance Criteria:**

**Given** I've applied filters on any dashboard tab (source, date range, category)
**When** I click "Save Filter Preset"
**Then** I'm prompted to name the preset

**And** the preset is saved to browser localStorage per tab

**When** I return to the tab
**Then** I see my saved presets in a dropdown

**When** I select a preset
**Then** all filters are applied instantly (<300ms)

**And** I can update or delete existing presets

**Prerequisites:** None (builds on existing filtering)

**Technical Notes:**
- Store presets in browser localStorage as JSON
- Format: `{tab_name: [{name: "preset1", filters: {...}}, ...]}`
- Add preset dropdown to each tab's filter section
- Use Dash callbacks to apply preset filters
- Maximum 10 presets per tab

---

### Story 2.2: Personal Source Shortcuts

As a **user**,
I want **to create shortcuts to my favorite sources**,
So that **I can access frequently-checked sources with one click**.

**Acceptance Criteria:**

**Given** I'm viewing any content item
**When** I click "Add to Shortcuts" on a source
**Then** the source is added to my shortcuts list

**When** I view the dashboard
**Then** I see a "Shortcuts" section in the sidebar/header

**And** shortcuts are grouped by domain (Papers, News, Deals, etc.)

**When** I click a shortcut
**Then** I navigate to that domain tab with source filter pre-applied

**And** I can reorder shortcuts via drag-and-drop

**And** I can remove shortcuts

**Prerequisites:** None (new feature)

**Technical Notes:**
- Store shortcuts in browser localStorage
- Format: `{shortcuts: [{id, name, domain, source_filter, order}]}`
- Create Shortcuts component in dashboard layout
- Use dash-bootstrap-components Offcanvas or sidebar
- Support drag-and-drop reordering using dash-sortable or custom JS

---

### Story 2.3: Dashboard Tab Customization

As a **user**,
I want **to control which tabs are visible and their order**,
So that **I only see domains I care about in my preferred sequence**.

**Acceptance Criteria:**

**Given** I open the dashboard
**When** I click "Customize Tabs" in settings
**Then** I see a list of all available tabs with toggle switches

**And** I can hide/show tabs

**And** I can drag to reorder tabs

**When** I save my preferences
**Then** only visible tabs appear in my preferred order

**And** preferences persist across sessions

**And** I can reset to default tab configuration

**Prerequisites:** None (modifies existing tab bar)

**Technical Notes:**
- Store tab preferences in browser localStorage
- Format: `{tab_visibility: {videos: true, papers: true, ...}, tab_order: ["videos", "papers", ...]}`
- Dynamically generate tab bar based on preferences
- Modal or offcanvas for customization UI
- Default configuration includes all tabs in alphabetical order

---

### Story 2.4: Items Per Page Preferences

As a **user**,
I want **to control how many items are displayed per tab**,
So that **I can optimize for my screen size and browsing style**.

**Acceptance Criteria:**

**Given** I'm viewing any dashboard tab
**When** I select items-per-page (12, 24, 48, 96)
**Then** the display updates immediately

**And** my choice is saved per tab in browser storage

**When** I return to the tab
**Then** my items-per-page preference is applied

**And** pagination controls adjust accordingly

**Prerequisites:** None (enhances existing pagination)

**Technical Notes:**
- Store preference per tab in localStorage
- Format: `{items_per_page: {videos: 48, papers: 24, ...}}`
- Update tab display logic to respect preference
- Add items-per-page selector to each tab
- Default: 48 items (current Videos tab behavior)

---

### Story 2.5: Mobile-Responsive Layout Improvements

As a **mobile user**,
I want **the dashboard to work well on mobile devices**,
So that **I can check Megalith on my phone/tablet**.

**Acceptance Criteria:**

**Given** I access dashboard from mobile device (<768px width)
**When** the page loads
**Then** navigation tabs collapse into hamburger menu

**And** content cards stack vertically (1 column)

**And** filter controls collapse into expandable section

**And** touch targets are minimum 44px (tap-friendly)

**When** I navigate between tabs
**Then** transitions are smooth (<500ms)

**And** search and filters work on mobile

**Prerequisites:** None (CSS/layout improvements)

**Technical Notes:**
- Use Bootstrap responsive breakpoints (xs, sm, md, lg, xl)
- Implement collapsible navbar with hamburger icon
- Adjust card grid: 4 cols (desktop) → 2 cols (tablet) → 1 col (mobile)
- Use Bootstrap Collapse for mobile filter section
- Test on iOS Safari, Chrome Mobile, Firefox Mobile
- Minimum touch target: 44x44px for buttons/links

---


## Epic 3: Smart Notifications & Alerts

**Epic Goal**: Never miss time-sensitive opportunities through intelligent, filtered notifications.

**Duration**: 3 weeks | **Phase**: Growth Phase 1 (Weeks 9-11)

### Story 3.1: Backend Alert Rule Engine

As a **system**,
I want **a rule engine to evaluate content and trigger alerts**,
So that **users receive notifications for content matching their criteria**.

**Acceptance Criteria:**

**Given** new content is detected by watchers
**When** the alert engine evaluates the content
**Then** it checks against all active user alert rules

**And** rules support conditions: source_match, keyword_match, category_match, price_threshold

**And** matching content generates alert events

**And** alert events are stored in `data/alerts/{user_id}/events/`

**And** duplicate alerts within 1 hour are suppressed

**Prerequisites:** Story 1.1 (metrics infrastructure), Story 2.1 (filter presets for rule definitions)

**Technical Notes:**
- Create AlertRule Pydantic model with conditions
- Create AlertEngine class in `src/alerts/engine.py`
- Integrate with BaseWatcher to trigger evaluations
- Store alert events as JSON with timestamp, content_id, rule_id
- Implement deduplication logic (content hash + time window)

---

### Story 3.2: Alert Rule Configuration UI

As a **user**,
I want **to create and manage notification rules**,
So that **I only receive alerts for content I care about**.

**Acceptance Criteria:**

**Given** I open the Notifications settings
**When** I click "Create Alert Rule"
**Then** I can define: rule name, domains, sources, keywords, categories

**And** I can choose notification channels (browser, email)

**And** I can set quiet hours (no notifications during specified times)

**And** I can test the rule against recent content

**When** I save the rule
**Then** it becomes active immediately

**And** I see a list of all my rules with edit/delete options

**Prerequisites:** Story 3.1 (alert engine), Story 2.1 (can reuse saved filter presets as rule templates)

**Technical Notes:**
- Create Notifications settings page/modal
- Store rules in `data/alerts/{user_id}/rules.json`
- Rule format: `{id, name, conditions: {...}, channels: [], quiet_hours: {start, end}, active: bool}`
- Add "Create from Preset" to convert filter presets to alert rules
- Test button runs rule against last 24 hours of content

---

### Story 3.3: Telegram Bot Notifications

As a **user**,
I want **to receive Telegram notifications when new content matches my rules**,
So that **I'm immediately alerted to time-sensitive opportunities with persistent message history**.

**Acceptance Criteria:**

**Given** I've linked my Telegram account to Megalith
**When** an alert event is generated (Story 3.1)
**Then** I receive a Telegram message (if Telegram channel enabled)

**And** message shows: title, source, brief preview, timestamp, direct link to content

**And** message uses rich Markdown formatting (bold titles, clickable links)

**When** I click the link in the message
**Then** dashboard opens to that content item

**And** message remains in Telegram chat history for later review

**And** I can configure quiet hours (no notifications during specified times)

**Prerequisites:** Story 3.1 (alert events), Story 3.2 (user rules)

**Technical Notes:**
- Use `python-telegram-bot 20.x` library
- Create Telegram bot via @BotFather, store bot token in environment variables
- Implement in `src/alerts/telegram_bot.py`
- User onboarding flow:
  1. User creates first alert rule
  2. System generates unique verification code
  3. User messages bot with `/start <code>` to link account
  4. System stores user's Telegram chat_id in user profile
- Message format: `🔔 *{title}*\n📰 Source: {source}\n🔗 [View in Megalith]({url})\n⏰ {timestamp}`
- Respect quiet hours from user preferences
- Handle Telegram API rate limits gracefully
- Log delivery status to alert events
- Future enhancement: Inline buttons for "Mark as Read", "Snooze 1h"

---

### Story 3.4: Notification History & Management

As a **user**,
I want **to view my notification history and manage alerts**,
So that **I can review past notifications and control notification volume**.

**Acceptance Criteria:**

**Given** I've received notifications
**When** I open the Notifications panel
**Then** I see a chronological list of all notifications (last 7 days)

**And** I can filter by: read/unread, domain, source

**And** I can mark as read/unread

**And** I can click to view the content

**And** I see notification stats: total alerts (24h), alerts per source

**And** I can mute specific sources for 24 hours

**Prerequisites:** Story 3.1 (alert events), Story 3.3 (notifications)

**Technical Notes:**
- Create Notifications panel (modal or sidebar)
- Load from `data/alerts/{user_id}/events/` directory
- Display using dash-bootstrap-components List or Table
- Add read_status field to alert events
- Implement mute functionality (temporarily disable rules for source)
- Auto-delete notifications older than 30 days

---

## Epic 4: Intelligent Data Quality

**Epic Goal**: Higher signal-to-noise ratio through smart deduplication and improved classification.

**Duration**: 4 weeks | **Phase**: Growth Phase 2 (Weeks 13-16)

### Story 4.1: Content Deduplication Engine

As a **user**,
I want **duplicate content automatically detected and hidden**,
So that **I don't see the same article/paper/deal multiple times**.

**Acceptance Criteria:**

**Given** content is loaded from multiple sources
**When** the deduplication engine runs
**Then** it identifies duplicates using: title similarity (>80%), content hash, URL matching

**And** duplicate groups are created (original + duplicates)

**And** only the highest-quality version is displayed by default

**And** I can click "Show X duplicates" to see all versions

**And** deduplication runs automatically during ETL processing

**Prerequisites:** None (enhances existing data pipeline)

**Technical Notes:**
- Create DeduplicationEngine in `src/data_quality/deduplication.py`
- Use difflib.SequenceMatcher for title similarity (ratio > 0.8)
- Use hashlib for content hashing (if full text available)
- Store duplicate_group_id in data files
- Prioritize by: source reputation score, recency, completeness
- Add is_duplicate flag to hide in default views
- Integrate into BaseETL transform phase

---

### Story 4.2: Enhanced NLP Classification

As a **user**,
I want **more accurate content categorization**,
So that **filtering and organization work better**.

**Acceptance Criteria:**

**Given** content is processed by ETL pipelines
**When** NLP classification runs
**Then** accuracy improves from current baseline to >85% for major categories

**And** multi-label classification is supported (content can have multiple categories)

**And** confidence scores are stored per category

**And** low-confidence classifications (<60%) are flagged for review

**And** classification model is retrained monthly with user feedback (future)

**Prerequisites:** None (improves existing NLP classifier)

**Technical Notes:**
- Enhance existing NLP classifier in `src/utils/nlp_classifier.py`
- Add multi-label support (content can be both "AI" and "Security")
- Store classifications: `{category: str, confidence: float, multi_labels: List[str]}`
- Use scikit-learn or simple keyword-based classifier (no deep learning yet)
- Add confidence thresholds: high (>80%), medium (60-80%), low (<60%)
- Flag low-confidence items in dashboard with indicator

---

### Story 4.3: Heuristic Relevance Scoring

As a **user**,
I want **content ranked by relevance**,
So that **the most important items appear first**.

**Acceptance Criteria:**

**Given** content is displayed in any tab
**When** relevance scoring is applied
**Then** each item has a relevance_score (0-100)

**And** scoring considers: recency (newer = higher), source_reputation, engagement_signals (future), category_match_to_user_prefs

**And** I can sort by: relevance (default), newest, oldest, source

**And** relevance weights are configurable per domain

**And** scoring runs during ETL processing

**Prerequisites:** Story 4.2 (classification for category matching)

**Technical Notes:**
- Create RelevanceScorer in `src/data_quality/relevance.py`
- Simple heuristic formula: `relevance = (recency_score * 0.4) + (source_rep * 0.3) + (category_match * 0.3)`
- Recency: exponential decay (100 for today, 50 for 1 week old, etc.)
- Source reputation: manually curated scores per source (70-100 range)
- Category match: bonus if matches user's most-viewed categories
- Store relevance_score in data files
- Add sort dropdown to each tab

---

### Story 4.4: Automated Retention Policies

As a **system operator**,
I want **old data automatically cleaned up per source type**,
So that **storage doesn't grow unbounded**.

**Acceptance Criteria:**

**Given** retention policies are configured per source
**When** the cleanup job runs daily
**Then** data older than retention period is archived or deleted

**And** policies vary by source type: news (30 days), papers (1 year), deals (7 days), videos (6 months)

**And** archived data moves to `data/archive/{source}/` (compressed)

**And** cleanup logs retention actions to metrics

**And** manual override allows keeping specific items indefinitely

**Prerequisites:** Story 1.1 (metrics for cleanup logging)

**Technical Notes:**
- Create RetentionManager in `src/data_quality/retention.py`
- Define policies in config: `{source_type: {retention_days: int, action: "delete"|"archive"}}`
- Scheduled job (cron/systemd timer) runs cleanup daily
- Archive: gzip JSON files, move to archive directory
- Log cleanup actions to `data/metrics/retention/{date}_cleanup.json`
- Add "Keep Forever" flag to individual items (stored in separate file)

---

### Story 4.5: Data Migration for Schema Changes

As a **developer**,
I want **automated migration when data schemas change**,
So that **existing data continues working after model updates**.

**Acceptance Criteria:**

**Given** a Pydantic model is updated (fields added/removed/renamed)
**When** I run the migration tool
**Then** it scans all data files for that source

**And** transforms old schema to new schema

**And** validates all migrated data

**And** creates backup before migration

**And** logs migration results (success/failure counts)

**Prerequisites:** None (developer tooling)

**Technical Notes:**
- Create DataMigrator in `src/data_quality/migration.py`
- CLI tool: `python src/data_quality/migration.py --source arxiv --backup`
- Migration strategies: add_field (with default), remove_field, rename_field, transform_value
- Backup: copy to `data/backups/{source}/{timestamp}/`
- Validation: use Pydantic model validation on migrated data
- Rollback: restore from backup if validation fails

---

## Epic 5: Multi-User Foundation

**Epic Goal**: Enable 3-5 colleagues to create accounts and access Megalith (shared preferences initially).

**Duration**: 3 weeks | **Phase**: Growth Phase 2 (Weeks 17-19)

### Story 5.1: User Authentication System

As a **user**,
I want **to create an account and log in securely**,
So that **I can access Megalith with my credentials**.

**Acceptance Criteria:**

**Given** I'm a new user
**When** I navigate to `/register`
**Then** I can create an account with: username, email, password

**And** password is hashed using bcrypt (minimum 12 characters)

**And** I receive confirmation of successful registration

**When** I navigate to `/login`
**Then** I can log in with username/email and password

**And** successful login creates a session cookie (HTTP-only, secure)

**And** invalid credentials show clear error message

**And** session expires after 7 days of inactivity

**Prerequisites:** None (foundation for multi-user)

**Technical Notes:**
- Use Flask-Login or create custom auth system
- Store users in `data/users/users.json` (or SQLite for better performance)
- User model: `{id, username, email, password_hash, created_at, last_login}`
- Use bcrypt for password hashing (12 rounds)
- Session management: secure cookies with CSRF tokens
- Create login/register pages using Dash pages or Flask routes

---

### Story 5.2: Session Management & Security

As a **system**,
I want **secure session management with CSRF protection**,
So that **user accounts are protected from common attacks**.

**Acceptance Criteria:**

**Given** a user is logged in
**When** they make requests
**Then** session token is validated on every request

**And** CSRF tokens are generated and validated for state-changing operations

**And** failed login attempts are rate-limited (5 attempts per 15 minutes per IP)

**And** sessions are invalidated on logout

**And** concurrent sessions are supported (user can be logged in on multiple devices)

**Prerequisites:** Story 5.1 (authentication system)

**Technical Notes:**
- Implement rate limiting using Flask-Limiter or custom middleware
- CSRF protection using Flask-WTF or custom token generation
- Session storage: server-side (file-based or Redis)
- Rate limit: store failed attempts in `data/security/failed_logins.json`
- Secure cookie flags: HttpOnly, Secure (HTTPS), SameSite=Lax
- Session timeout: 30 minutes inactive, 7 days absolute

---

### Story 5.3: User Profile Management

As a **user**,
I want **to view and update my profile**,
So that **I can manage my account information**.

**Acceptance Criteria:**

**Given** I'm logged in
**When** I navigate to `/profile`
**Then** I see my: username, email, account created date, last login

**And** I can update my email address

**And** I can change my password (requires current password)

**And** I can delete my account (with confirmation)

**And** changes are saved immediately

**And** I see success/error messages for all actions

**Prerequisites:** Story 5.1 (user accounts)

**Technical Notes:**
- Create profile page using Dash layout
- Profile form: email update, password change (current + new + confirm)
- Account deletion: soft delete (mark as deleted) or hard delete (remove data)
- Validate password change: current password must match, new password must meet requirements
- Update `data/users/users.json` or database

---

### Story 5.4: Login/Logout UI Flow

As a **user**,
I want **clear login/logout flows integrated into the dashboard**,
So that **authentication feels seamless**.

**Acceptance Criteria:**

**Given** I'm not logged in
**When** I access the dashboard
**Then** I'm redirected to `/login` page

**And** login page has: username/email input, password input, "Remember me" checkbox, "Forgot password?" link (future), "Create account" link

**When** I log in successfully
**Then** I'm redirected to the dashboard home

**And** I see my username in the navbar

**When** I click logout
**Then** I'm logged out and redirected to login page

**And** my session is cleared

**Prerequisites:** Story 5.1 (auth system)

**Technical Notes:**
- Create login page with Dash layout
- Use Dash dcc.Location for redirects
- Protected routes: check session before rendering dashboard
- Navbar: show username + logout button when authenticated
- Remember me: extend session duration to 30 days
- Clear session cookie on logout

---

### Story 5.5: Basic Admin Dashboard

As an **admin user**,
I want **to view and manage all user accounts**,
So that **I can administer the multi-user system**.

**Acceptance Criteria:**

**Given** I'm logged in as admin
**When** I navigate to `/admin/users`
**Then** I see a table of all users with: username, email, created_date, last_login, status

**And** I can activate/deactivate user accounts

**And** I can reset user passwords (generates temporary password)

**And** I can view user activity logs (future)

**And** non-admin users cannot access admin pages

**Prerequisites:** Story 5.1 (user system), Story 5.3 (profile management)

**Technical Notes:**
- Add is_admin flag to User model
- Create admin dashboard using Dash layout
- Admin-only routes: check user.is_admin before rendering
- User table: filterable and sortable
- Password reset: generate random temporary password, email to user
- Activity logs: track login times, page views (future)

---

## Epic 5.5: Per-User Personalization

**Epic Goal**: Each colleague gets their own customized Megalith experience with personal preferences.

**Duration**: 3 weeks | **Phase**: Growth Phase 3 (Weeks 21-23)

### Story 5.5.1: Per-User Dashboard Preferences

As a **user**,
I want **my dashboard preferences (from Epic 2) to be personal, not shared**,
So that **my colleague's preferences don't affect mine**.

**Acceptance Criteria:**

**Given** I'm logged in
**When** I customize my dashboard (tab order, visibility, items-per-page, saved filters, shortcuts)
**Then** preferences are saved per my user ID

**And** my preferences don't affect other users

**And** preferences persist across devices where I'm logged in

**And** I can reset my preferences to defaults

**Prerequisites:** Epic 2 (personalization features), Story 5.1 (user accounts)

**Technical Notes:**
- Migrate preferences from browser localStorage to server-side storage
- Store in `data/users/{user_id}/preferences.json`
- Preference model: `{tab_visibility, tab_order, items_per_page, saved_filters, shortcuts}`
- Load preferences on login, sync with frontend
- API endpoints: GET/PUT `/api/preferences`
- Data migration: copy existing localStorage prefs to first logged-in user

---

### Story 5.5.2: Per-User Notification Settings

As a **user**,
I want **my notification rules to be personal**,
So that **I only receive alerts for content I care about**.

**Acceptance Criteria:**

**Given** I'm logged in
**When** I create notification rules
**Then** rules are saved per my user ID

**And** I only receive notifications for my rules

**And** other users' rules don't trigger notifications for me

**And** I can import rules from another user (with permission)

**Prerequisites:** Epic 3 (notifications), Story 5.1 (user accounts)

**Technical Notes:**
- Migrate alert rules from global to per-user storage
- Store in `data/alerts/{user_id}/rules.json`
- Alert engine evaluates rules per user
- Notification delivery: check user session/device registration
- Rule import: admin can export/import rule templates

---

### Story 5.5.3: Shared vs Personal Sources

As a **user**,
I want **to add personal data sources that only I can see**,
So that **I can customize my Megalith without affecting others**.

**Acceptance Criteria:**

**Given** I'm logged in
**When** I add a data source
**Then** I can mark it as "Personal" or "Shared"

**And** personal sources only appear in my dashboard

**And** shared sources appear for all users

**And** admins can convert personal sources to shared

**And** source configuration is stored per user ID for personal sources

**Prerequisites:** Story 5.1 (user accounts)

**Technical Notes:**
- Add source_type field: "shared" | "personal"
- Personal sources stored in `data/users/{user_id}/sources/`
- Shared sources stored in global `data/` directory
- Dashboard filters sources by: global + user-specific
- ETL pipelines for personal sources run per user
- UI: "Add Personal Source" button in dashboard

---

### Story 5.5.4: User Onboarding Experience

As a **new user**,
I want **guided onboarding when I first log in**,
So that **I understand how to use Megalith effectively**.

**Acceptance Criteria:**

**Given** I log in for the first time
**When** the dashboard loads
**Then** I see a welcome modal with: product tour option, quick start guide, "Skip" button

**When** I choose product tour
**Then** I see step-by-step highlights of: navigation, filtering, shortcuts, notifications, customization

**And** tour progresses with "Next", "Back", "Skip" buttons

**And** tour marks feature highlights on actual UI elements

**When** I complete or skip the tour
**Then** I'm taken to a source selection wizard

**And** wizard shows curated sources by domain with "Add to My Sources" buttons

**And** I can select domains I'm interested in

**When** I complete wizard
**Then** my dashboard is configured with selected sources

**And** I'm marked as onboarded (won't see tour again)

**Prerequisites:** Story 5.1 (user accounts), Story 5.5.3 (source selection)

**Technical Notes:**
- Create OnboardingModal component using dash-bootstrap-components
- Product tour: use Shepherd.js or custom Dash component
- Tour steps: highlight navbar, filters, shortcuts panel, notification bell, settings
- Source wizard: paginated by domain, show source descriptions
- Store onboarding_completed flag in user profile
- Skip option available at every step

---

### Story 5.5.5: Data Migration from Single to Multi-User

As a **developer**,
I want **automated migration from single-user to multi-user data structure**,
So that **existing data continues working after multi-user deployment**.

**Acceptance Criteria:**

**Given** Megalith is deployed with single-user data
**When** I run the multi-user migration tool
**Then** existing preferences migrate to first admin user

**And** existing alert rules migrate to first admin user

**And** all sources are marked as "shared"

**And** backup is created before migration

**And** migration is idempotent (safe to run multiple times)

**Prerequisites:** Stories 5.5.1-5.5.3 (multi-user data structures)

**Technical Notes:**
- Create migration script: `python src/scripts/migrate_to_multiuser.py`
- Steps: 1) Create backup, 2) Create default admin user, 3) Migrate localStorage data, 4) Migrate alert rules, 5) Mark sources as shared
- Idempotency: check if migration already completed (flag file)
- Backup location: `data/backups/single_user_backup_{timestamp}/`
- Log all migration actions

---

## Epic 6: Source Integration Acceleration

**Epic Goal**: Reduce source integration time from 30min to 15min with basic tooling.

**Duration**: 2 weeks | **Phase**: Growth Phase 3 (Weeks 24-25)

### Story 6.1: Source Registry System

As a **developer**,
I want **a centralized registry of all data sources**,
So that **I can view metadata and status for all sources**.

**Acceptance Criteria:**

**Given** sources exist in the system
**When** I view the source registry
**Then** I see metadata for each source: name, URL, type (RSS/API/scraper), update_frequency, status (active/deprecated/failing), added_date, owner

**And** I can filter by: status, type, domain

**And** I can export registry as JSON or CSV

**And** registry is auto-generated from source code annotations

**Prerequisites:** None (developer tooling)

**Technical Notes:**
- Create SourceRegistry in `src/registry/registry.py`
- Registry format: `{sources: [{id, name, url, type, frequency, status, metadata}]}`
- Auto-discover sources by scanning ETL directory for classes inheriting BaseETL
- CLI tool: `python src/registry/registry.py --export json`
- Store registry in `data/registry/sources.json`
- Add decorators to ETL classes for metadata: `@source(name="ArXiv", url="...", frequency="daily")`

---

### Story 6.2: CLI Scaffolding Tool

As a **developer**,
I want **a CLI tool to generate new source boilerplate**,
So that **I can start implementing a new source in minutes**.

**Acceptance Criteria:**

**Given** I want to add a new source
**When** I run `megalith new-source <name> --type <rss|api|scraper>`
**Then** it generates: Pydantic model file, ETL class file, dashboard tab file, test file

**And** files follow project naming conventions

**And** boilerplate includes: TODO comments for customization, example implementations, proper imports

**And** files are created in correct directories

**And** tool updates source registry

**Prerequisites:** Story 6.1 (source registry)

**Technical Notes:**
- CLI tool: `src/scripts/new_source.py` (uses Click or argparse)
- Templates stored in `src/templates/` or `.bmad/templates/`
- Generated files:
  - Model: `src/models/{name}_model.py`
  - ETL: `src/etl/{name}/{name}_etl.py`
  - Tab: `src/web/dashboard/components/{name}_tab.py`
  - Test: `tests/etl/test_{name}_etl.py`
- Replace template variables: {{SOURCE_NAME}}, {{SOURCE_TYPE}}, {{DATE}}
- Register source in registry JSON

---

### Story 6.3: Documentation Templates

As a **developer**,
I want **documentation templates for new sources**,
So that **documentation is consistent and complete**.

**Acceptance Criteria:**

**Given** I've created a new source with the CLI tool
**When** I open the generated files
**Then** I see docstring templates with sections: Overview, Configuration, Data Schema, Error Handling, Testing

**And** README template includes: source description, setup instructions, example usage, troubleshooting

**And** templates have TODO markers for required customization

**And** examples are included for common patterns

**Prerequisites:** Story 6.2 (scaffolding tool includes doc templates)

**Technical Notes:**
- Doc templates in generated files use Google-style docstrings
- README template: `templates/SOURCE_README.md`
- Sections: Purpose, Prerequisites, Configuration (env vars), Data Schema (example JSON), Running Manually, Testing, Known Issues
- CLI generates README in `src/etl/{name}/README.md`

---

### Story 6.4: Integration Testing Helpers

As a **developer**,
I want **helper utilities for testing new sources**,
So that **I can quickly validate my ETL implementation**.

**Acceptance Criteria:**

**Given** I've implemented a new ETL
**When** I run `pytest tests/etl/test_{name}_etl.py`
**Then** tests verify: extract returns data, transform validates against model, load writes files correctly

**And** test fixtures provide sample data

**And** tests can run in offline mode (mock API responses)

**And** tests validate data schema using Pydantic

**Prerequisites:** Story 6.2 (test file generated)

**Technical Notes:**
- Base test class: `tests/etl/base_etl_test.py` with common test methods
- Fixtures: sample raw data, expected transformed data
- Mocking: use responses library or pytest-mock for API calls
- Schema validation: assert Pydantic model.validate(data) succeeds
- Test coverage: aim for >70% coverage per new ETL

---

## Epic 7: Technical Debt & Performance Sprint

**Epic Goal**: Maintain velocity as system scales to 100+ sources through systematic debt reduction and performance optimization.

**Duration**: 3 weeks | **Phase**: Growth Phase 3 (Weeks 26-28)

### Story 7.1: ETL Pattern Standardization

As a **developer**,
I want **all ETL pipelines to follow consistent BaseETL v2.0 patterns**,
So that **code is maintainable and predictable**.

**Acceptance Criteria:**

**Given** 10 oldest ETL pipelines are identified
**When** I refactor each to BaseETL v2.0 pattern
**Then** all implement: extract(), transform(), load() consistently

**And** all use ETLMetrics for performance tracking

**And** all implement checkpointing for resumability

**And** all use Pydantic models for validation

**And** all follow error handling best practices

**Prerequisites:** Story 1.1 (ETLMetrics), Story 4.5 (migration tooling)

**Technical Notes:**
- Identify oldest ETLs: ArXiv, News (HN/Reddit), Games (Steam/Epic), Courses (Udemy)
- Create BaseETL v2.0 with enhanced features from lessons learned
- Migration per ETL: 1) Create backup, 2) Refactor to pattern, 3) Test, 4) Deploy
- Document pattern changes in architecture docs
- Target: 2-3 ETLs per week

---

### Story 7.2: Test Coverage Improvements

As a **developer**,
I want **unit test coverage increased from 40% to 70%**,
So that **refactoring is safe and regressions are caught early**.

**Acceptance Criteria:**

**Given** current test coverage is ~40%
**When** I add tests for uncovered code
**Then** overall coverage reaches 70% minimum

**And** all BaseETL methods have unit tests

**And** all Pydantic models have validation tests

**And** critical dashboard components have tests

**And** test suite runs in <5 minutes

**Prerequisites:** None (testing infrastructure exists)

**Technical Notes:**
- Use pytest-cov to identify uncovered code
- Priority areas: BaseETL (target 90%), models (target 80%), dashboard (target 60%)
- Add integration tests for end-to-end ETL flows
- Mock external APIs to keep tests fast
- Set up pre-commit hook to prevent coverage regression
- CI/CD integration: fail build if coverage drops below 70%

---

### Story 7.3: Dashboard Performance Optimization

As a **user**,
I want **dashboard load times reduced from 2s to 1s**,
So that **navigation feels instant**.

**Acceptance Criteria:**

**Given** current dashboard loads in ~2 seconds
**When** I apply performance optimizations
**Then** initial page load is <1 second (95th percentile)

**And** tab switching is <300ms

**And** filter application is <200ms

**And** dashboard handles 10,000+ items per tab smoothly

**Prerequisites:** Story 1.1 (metrics to measure improvements)

**Technical Notes:**
- Profile current performance with browser DevTools
- Optimizations:
  - Lazy load tab data (only load active tab)
  - Implement virtual scrolling for large lists
  - Optimize JSON parsing (use orjson or ijson)
  - Add service worker for caching
  - Minimize callback complexity
  - Pre-compute filtered results server-side
- Target metrics: LCP <1s, FID <100ms, CLS <0.1

---

### Story 7.4: Complex Module Refactoring

As a **developer**,
I want **the 5 most complex modules refactored for maintainability**,
So that **future changes are easier and safer**.

**Acceptance Criteria:**

**Given** modules with cyclomatic complexity >15 are identified
**When** I refactor the top 5 complex modules
**Then** complexity reduces to <10 per function

**And** modules are split into smaller, focused units

**And** all refactored code has >80% test coverage

**And** existing functionality remains unchanged (verified by tests)

**Prerequisites:** Story 7.2 (test coverage for safe refactoring)

**Technical Notes:**
- Use radon or pylint to measure complexity
- Likely candidates: BaseETL, dashboard data managers, NLP classifier, watchers
- Refactoring techniques: extract method, extract class, simplify conditionals
- Each refactor: 1) Add tests, 2) Refactor, 3) Verify tests pass, 4) Deploy
- Document architectural decisions in ADRs

---

### Story 7.5: ETL Performance Profiling

As a **developer**,
I want **performance profiles for all 50+ ETL pipelines**,
So that **I can identify and fix bottlenecks**.

**Acceptance Criteria:**

**Given** all ETL pipelines are running
**When** I run performance profiling
**Then** I have metrics for each: runtime, memory usage, items/second, bottleneck identification

**And** slowest 10 ETLs are identified with root causes

**And** optimization recommendations are documented

**And** baseline metrics are stored for future comparison

**Prerequisites:** Story 1.1 (metrics infrastructure)

**Technical Notes:**
- Use cProfile or py-spy for profiling
- Profile each ETL: `python -m cProfile -o profile.stats src/etl/{name}/{name}_etl.py`
- Analyze with snakeviz or profiling tools
- Store results: `data/metrics/profiling/{etl_name}_profile.json`
- Document findings in `docs/performance_analysis.md`
- Create optimization backlog for slowest ETLs

---

## Epic 8: Simple Intelligence Features

**Epic Goal**: Proactive insights using heuristics (no ML research required).

**Duration**: 2 weeks | **Phase**: Vision Phase 1 (Months 8-9)

### Story 8.1: Usage-Based Recommendations

As a **user**,
I want **content recommendations based on my reading patterns**,
So that **I discover relevant content I might miss**.

**Acceptance Criteria:**

**Given** I've been using Megalith for >1 week
**When** I view any dashboard tab
**Then** I see a "Recommended for You" section

**And** recommendations include: sources I read most, categories I engage with, similar content to what I've clicked

**And** recommendations update daily based on last 30 days of activity

**And** I can dismiss recommendations

**And** I can provide feedback (helpful/not helpful)

**Prerequisites:** Story 5.5.1 (per-user data tracking)

**Technical Notes:**
- Track user interactions: clicks, time spent, sources viewed
- Store in `data/users/{user_id}/activity_log.json`
- Simple recommendation algorithm:
  1. Top 5 sources by click count
  2. Top 3 categories by engagement
  3. Content similar to recently clicked items (title similarity)
- Run recommendation engine daily (background job)
- Store recommendations in user preferences
- Display in separate section or mixed with regular content

---

### Story 8.2: Simple Trend Indicators

As a **user**,
I want **to see trending topics and increasing activity**,
So that **I'm aware of emerging trends**.

**Acceptance Criteria:**

**Given** content is being aggregated
**When** I view any dashboard tab
**Then** trending items are marked with "🔥 Trending" badge

**And** trend calculation uses: item count increase, category growth, keyword frequency changes

**And** trends are calculated over 7-day rolling window

**And** I can filter to show only trending content

**And** trend indicators show % change (e.g., "+40% this week")

**Prerequisites:** Story 4.2 (NLP classification for keyword extraction)

**Technical Notes:**
- Create TrendAnalyzer in `src/analytics/trends.py`
- Calculate trends daily:
  1. Count items per category/keyword (current week vs previous week)
  2. Calculate % change
  3. Mark items with >30% increase as trending
- Store trend data: `data/analytics/trends/{date}_trends.json`
- Display badges on content cards
- Add "Trending" filter option to each tab

---

### Story 8.3: Related Content Suggestions

As a **user**,
I want **to see related content when viewing an item**,
So that **I can explore connected topics**.

**Acceptance Criteria:**

**Given** I'm viewing a content item detail
**When** the page loads
**Then** I see "Related Content" section with 3-5 similar items

**And** similarity is based on: shared categories, similar titles, same source domain, keyword overlap

**And** related items are clickable links

**And** items are sorted by relevance score

**Prerequisites:** Story 4.2 (NLP classification), Story 4.3 (relevance scoring)

**Technical Notes:**
- Create RelatedContentEngine in `src/analytics/related.py`
- Similarity scoring:
  - Category match: +30 points
  - Title similarity (>60%): +25 points
  - Same domain: +20 points
  - Keyword overlap: +5 points per match
- Calculate on-demand (cache results for 24 hours)
- Display using Bootstrap card component
- Max 5 related items per content piece

---

### Story 8.4: Content Insights Dashboard

As a **user**,
I want **a dashboard showing my content consumption insights**,
So that **I understand my information diet**.

**Acceptance Criteria:**

**Given** I've been using Megalith for >1 week
**When** I navigate to "Insights" tab
**Then** I see: most-read sources, top categories, reading trends over time, content volume per day

**And** charts visualize data (bar charts, line charts, pie charts)

**And** insights cover last 7 days, 30 days, 90 days (selectable)

**And** I can export insights as JSON or CSV

**Prerequisites:** Story 5.5.1 (user activity tracking), Story 8.1 (recommendation infrastructure)

**Technical Notes:**
- Create Insights tab in dashboard
- Visualizations using Plotly:
  - Bar chart: Top 10 sources by clicks
  - Pie chart: Category distribution
  - Line chart: Daily content volume
  - Heatmap: Reading patterns by day/hour
- Data source: `data/users/{user_id}/activity_log.json`
- Add export functionality using pandas to_csv/to_json
- Cache computed insights for 6 hours

---

## Epic 9: Platform Ecosystem & Integrations

**Epic Goal**: Community growth and external integrations to extend Megalith's reach.

**Duration**: 4-6 weeks | **Phase**: Vision Phase 2 (Months 10-11)

### Story 9.1: REST API Foundation

As a **developer**,
I want **a REST API to access Megalith data programmatically**,
So that **I can build integrations and external tools**.

**Acceptance Criteria:**

**Given** API is deployed
**When** I make authenticated requests
**Then** I can access endpoints: `/api/sources`, `/api/content/{domain}`, `/api/user/preferences`, `/api/alerts`

**And** all endpoints require authentication (API keys or OAuth)

**And** responses are JSON with consistent structure

**And** rate limiting is enforced (100 requests/hour per user)

**And** API documentation is available at `/api/docs` (OpenAPI/Swagger)

**Prerequisites:** Story 5.1 (authentication system)

**Technical Notes:**
- Use Flask-RESTX or FastAPI for API framework
- API endpoints:
  - GET `/api/sources` - list all sources
  - GET `/api/content/{domain}?limit=50` - get content for domain
  - GET/PUT `/api/user/preferences` - manage preferences
  - GET `/api/alerts` - get alert history
- Authentication: API keys stored in user profile
- Rate limiting: use Flask-Limiter
- OpenAPI schema generation for documentation

---

### Story 9.2: Webhook Support

As a **developer**,
I want **webhooks to receive real-time events**,
So that **external systems can react to Megalith events**.

**Acceptance Criteria:**

**Given** I've configured a webhook URL
**When** an event occurs (new content, alert triggered, source updated)
**Then** Megalith sends HTTP POST to my webhook URL

**And** payload includes: event_type, timestamp, data

**And** failed webhooks are retried (3 attempts with exponential backoff)

**And** webhook logs show delivery status

**And** I can test webhooks with sample payloads

**Prerequisites:** Story 9.1 (API infrastructure)

**Technical Notes:**
- Webhook configuration stored in user profile: `{url, events: [], secret}`
- Supported events: content.new, alert.triggered, source.updated
- Payload format: `{event: str, timestamp: str, data: {...}, signature: str}`
- Signature: HMAC-SHA256 of payload using webhook secret
- Retry logic: 30s, 5m, 30m delays
- Webhook logs: `data/webhooks/{user_id}/deliveries.json`

---

### Story 9.3: Slack/Discord Integration

As a **user**,
I want **notifications sent to Slack or Discord**,
So that **my team sees important alerts in our chat tools**.

**Acceptance Criteria:**

**Given** I've configured Slack/Discord webhook
**When** an alert is triggered
**Then** message is posted to configured channel

**And** message includes: title, source, link, preview, timestamp

**And** message formatting uses Slack/Discord markdown

**And** I can customize which alerts go to which channels

**And** I can test integration with sample message

**Prerequisites:** Story 3.1 (alert system), Story 9.2 (webhook infrastructure)

**Technical Notes:**
- Store integration config: `{type: "slack"|"discord", webhook_url, channel_rules: [...]}`
- Slack format: use Block Kit for rich messages
- Discord format: use embeds for rich messages
- Channel rules: map alert conditions to webhook URLs
- Test endpoint sends sample alert to verify configuration
- Use async delivery to prevent blocking

---

### Story 9.4: Browser Extension (Basic)

As a **user**,
I want **a browser extension to access Megalith quickly**,
So that **I can check updates without opening the full dashboard**.

**Acceptance Criteria:**

**Given** extension is installed (Chrome/Firefox)
**When** I click the extension icon
**Then** I see popup with: latest notifications, quick links to domains, unread count

**And** I can click items to open in dashboard

**And** I can mark notifications as read

**And** extension badge shows unread notification count

**And** extension syncs with dashboard in real-time

**Prerequisites:** Story 9.1 (API for data access), Story 3.4 (notification history)

**Technical Notes:**
- Browser extension using Manifest V3
- Popup UI: HTML/CSS/JavaScript with Megalith branding
- API calls to Megalith backend for data
- Badge updates using chrome.browserAction API
- Storage: chrome.storage.sync for API key
- Support Chrome and Firefox (use webextension-polyfill)
- Publish to Chrome Web Store and Firefox Add-ons

---

### Story 9.5: API Documentation & Developer Portal

As a **developer**,
I want **comprehensive API documentation and examples**,
So that **I can quickly build integrations**.

**Acceptance Criteria:**

**Given** API is deployed
**When** I navigate to `/api/docs`
**Then** I see interactive API documentation (Swagger UI)

**And** documentation includes: all endpoints, request/response schemas, authentication details, rate limits, examples

**And** I can test API calls directly from documentation

**And** I see code examples in multiple languages (Python, JavaScript, cURL)

**And** I can generate API clients automatically

**Prerequisites:** Story 9.1 (REST API)

**Technical Notes:**
- Use Swagger/OpenAPI for documentation
- Auto-generate from API decorators/annotations
- Interactive UI: Swagger UI or ReDoc
- Code examples: use openapi-generator for client libraries
- Include tutorials: authentication, common workflows, webhook setup
- Host documentation at `/api/docs` or dedicated subdomain

---

### Story 9.6: Email Digest System

As a **user**,
I want **daily or weekly email digests of important content**,
So that **I stay informed even when not actively checking Megalith**.

**Acceptance Criteria:**

**Given** I've enabled email digests
**When** the digest schedule triggers (daily/weekly)
**Then** I receive an email with: top stories, trending content, alert summary, personalized recommendations

**And** email is formatted with HTML (responsive design)

**And** each item links back to dashboard

**And** I can unsubscribe or change frequency

**And** I can customize which content appears in digest

**Prerequisites:** Story 8.1 (recommendations), Story 8.2 (trends)

**Technical Notes:**
- Email template using Jinja2 with responsive HTML
- SMTP configuration for email sending (or use SendGrid/Mailgun)
- Digest generation:
  - Daily: Top 10 items from last 24 hours + 3 alerts
  - Weekly: Top 20 items from last 7 days + trend summary
- Schedule with cron job or Celery beat
- Store email preferences in user profile
- Unsubscribe token in email footer
- Track open rates and click-through (optional analytics)

---

## Epic Breakdown Summary

**Total Stories**: 48 stories across 9 epics

**By Epic:**
- Epic 1: 4 stories (3 weeks)
- Epic 2: 5 stories (4 weeks)
- Epic 3: 4 stories (3 weeks)
- Epic 4: 5 stories (4 weeks)
- Epic 5: 5 stories (3 weeks)
- Epic 5.5: 5 stories (3 weeks)
- Epic 6: 4 stories (2 weeks)
- Epic 7: 5 stories (3 weeks)
- Epic 8: 4 stories (2 weeks)
- Epic 9: 6 stories (4-6 weeks)

**Timeline**: 32 weeks (8 months) + 4 buffer weeks = **9 months total to Vision Phase completion**

**Success Metrics Alignment:**
- ✅ Daily indispensability: Epics 1-3 (notifications, personalization, search)
- ✅ <30 min source integration: Epic 6 (tooling)
- ✅ Zero missed opportunities: Epic 3 (smart notifications)
- ✅ 3-5 colleague adoption: Epic 5 & 5.5 (multi-user by Month 6)
- ✅ Platform extensibility: Epic 9 (API, integrations)

---

_For implementation: Use the `dev-story` workflow to execute individual stories from this breakdown._
