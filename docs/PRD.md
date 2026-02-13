# megalith - Product Requirements Document

**Author:** Joshi
**Date:** 2025-01-11
**Version:** 1.0

---

## Executive Summary

**Megalith (Watchtower)** is a self-extending intelligence platform designed to solve the complexity problem of monitoring 50+ diverse information sources across generative AI, global news, deals, training, and services. Built for power users with deep technical knowledge, it provides a unified dashboard that eliminates context switching while maintaining an architecture optimized for rapid extensibility.

The platform addresses the critical pain point faced by technology professionals: staying current with fast-moving developments across multiple domains without drowning in complexity or missing important updates. By combining intelligent ETL pipelines, real-time watchers, and domain-focused navigation, Megalith transforms information chaos into actionable intelligence.

### What Makes This Special

**The magic of Megalith lies in its architecture-first approach to extensibility.** While other aggregators focus on breadth or simplicity, Megalith is built for depth and growth. The BaseETL framework, modular watcher system, and unified data model enable adding new sources in under 30 minutes - transforming what would normally be a multi-day integration into a streamlined workflow.

This is not a tool for casual browsing - it's a **personal intelligence framework** that grows with its users. The dashboard doesn't hide complexity; it organizes it intelligently, allowing power users to dive deep into specific domains (AI developments, news cycles, deals, training opportunities) while maintaining a coherent overview. For tech-savvy professionals who need to stay ahead, Megalith becomes indispensable: everything important in one place, nothing important missed, infinitely extensible.

---

## Project Classification

**Technical Type:** Web Application (Dashboard Platform with Backend Data Processing)
**Domain:** General (Information Aggregation & Intelligence)
**Complexity:** High (Architectural Complexity, Low Domain Complexity)

Megalith is a **brownfield web application** that combines a frontend dashboard (Dash-based) with a sophisticated backend data processing system (50+ ETL pipelines and real-time watchers). The complexity stems not from domain-specific requirements (no regulatory or compliance needs) but from **architectural challenges**:

- **Scale**: 50+ diverse data sources with different protocols (RSS, APIs, web scraping)
- **Extensibility**: Architecture must support rapid addition of new sources (<30 min integration time)
- **Data Unification**: Diverse data formats must be normalized into coherent domain views
- **Real-time Processing**: Continuous monitoring with state management and change detection
- **Performance**: Fast data loading and responsive dashboard for large datasets

**Key Architectural Patterns in Use:**
- Template Method Pattern (BaseETL, BaseWatcher)
- Component-based Dashboard (modular tabs)
- File-based JSON storage for performance
- Pydantic models for data validation
- Event-driven watcher system

The project exists in the "platform/framework" category - it's as much about creating an extensible system as delivering specific features.

---

## Success Criteria

### Primary Success Metrics

**1. Daily Usage & Indispensability**
- **Target**: Used daily by you (primary user) as the first information source of the day
- **Measure**: You stop checking individual sources (HackerNews, Reddit, ArXiv, etc.) directly because Megalith has it all
- **Success means**: "I can't imagine my workflow without it"

**2. Extensibility Achievement**
- **Target**: New data source integration takes < 30 minutes from concept to dashboard
- **Measure**: Time from "I want to add X" to "X is live and working"
- **Success means**: Adding sources feels effortless, not a project

**3. Zero Missed Opportunities**
- **Target**: Never miss important AI developments, deals, or training opportunities due to timing
- **Measure**: Real-time watcher alerts catch time-sensitive content (free courses, limited deals, breaking news)
- **Success means**: "I found that $200 course 1 hour after it went free"

**4. Colleague Adoption**
- **Target**: 3-5 tech-savvy colleagues actively use Megalith for their intelligence needs
- **Measure**: Colleagues can customize for their domains and add their own sources
- **Success means**: "Can you add [new source] to our Megalith instance?"

### Quality Metrics

**5. System Reliability**
- **Target**: 99%+ uptime for watchers and ETL pipelines
- **Measure**: Failed ETL runs < 1%, watcher downtime < 1 hour/month
- **Success means**: Trust that the system is always monitoring

**6. Dashboard Performance**
- **Target**: Dashboard loads in < 2 seconds with 1,500+ items
- **Measure**: Page load times, interaction responsiveness
- **Success means**: No waiting, instant domain switching

**7. Data Quality**
- **Target**: < 1% noise (irrelevant/duplicate content)
- **Measure**: Manual review of daily feed quality
- **Success means**: High signal-to-noise ratio, no junk

### Long-term Vision Metrics (6-12 months)

**8. Source Coverage**
- **Current**: 50+ sources
- **Target**: 100+ sources covering all relevant domains
- **Success means**: Comprehensive coverage with no important gaps

**9. Personalization**
- **Target**: Each user has personalized views/filters for their interests
- **Success means**: Same platform, different experiences per user

---

## Product Scope

### MVP - Current Baseline (Must Maintain)

**Core Data Processing Infrastructure:**
- ✅ **50+ ETL Pipelines**: ArXiv, News (HackerNews, Reddit, Medium), Games, Courses, AI Platforms, Entertainment, Deals, Anime, ADHD Research, 4chan, Spanish Public Aid, Valencia Events
- ✅ **BaseETL Framework**: Template method pattern with metrics, checkpointing, retry logic, validation
- ✅ **Watcher System**: Real-time monitoring with state persistence and event logging
- ✅ **JSON Storage**: File-based storage in `data/` with timestamped outputs and latest files
- ✅ **Pydantic Models**: Type-safe data validation across all sources

**Dashboard & Visualization:**
- ✅ **Dash Dashboard** (port 7780): Modern web interface with Bootstrap styling
- ✅ **Domain Tabs**: Organized navigation by content type (Videos, Papers, News, Deals, etc.)
- ✅ **Interactive Filtering**: Channel/source selection, date filtering, search capabilities
- ✅ **Component Architecture**: Modular tab system with data managers
- ✅ **Health Monitoring**: `/health` and `/metrics` API endpoints

**Operational Requirements:**
- ✅ **UV Package Manager**: Fast dependency management and execution
- ✅ **Automated ETL Runs**: Scripts for running all pipelines (`run_all_etl.sh/bat`)
- ✅ **Configuration Management**: Pydantic settings with environment variable support
- ✅ **Error Handling**: Custom exception hierarchy with graceful degradation
- ✅ **Performance**: <2 second dashboard loads, efficient data caching

**Quality Standards:**
- ✅ **Testing**: pytest coverage for ETL and models
- ✅ **Code Quality**: Ruff formatting, type hints with mypy
- ✅ **Documentation**: Comprehensive CLAUDE.md and inline docs

### Growth Features (Next 3-6 Months)

**Extensibility Improvements:**
1. **ETL Template Generator**: CLI tool to scaffold new ETL pipelines from templates
   - Target: Reduce 30-min integration to 10-15 min
   - Auto-generate boilerplate (model, ETL class, dashboard tab)

2. **Source Registry**: Centralized catalog of all data sources with metadata
   - Source status tracking (active, deprecated, failing)
   - Performance metrics per source (success rate, avg runtime)
   - Documentation per source (URL, update frequency, schema)

3. **Dashboard Customization**:
   - User preferences stored per user
   - Custom tab ordering and visibility
   - Saved filters and views
   - Personal shortcuts to favorite sources

**Data Quality Enhancements:**
4. **Duplicate Detection**: Identify and merge duplicate content across sources
5. **NLP Classification Improvements**: Better categorization and trend analysis
6. **Smart Filtering**: ML-based relevance scoring to reduce noise

**User Experience:**
7. **Notification System**: Real-time alerts for high-value content (time-sensitive deals, breaking news)
8. **Search Enhancement**: Full-text search across all domains with relevance ranking
9. **Mobile Optimization**: Responsive design improvements for mobile browsing

**Operational Excellence:**
10. **ETL Orchestration Dashboard**: Visual monitoring of pipeline status, errors, and performance
11. **Automated Healing**: Auto-retry failed pipelines with intelligent backoff
12. **Data Retention Management**: Automated cleanup policies with configurable retention

### Vision Features (6-12+ Months)

**Platform Evolution:**
1. **Multi-User Architecture**:
   - User authentication and profiles
   - Per-user data feeds and personalization
   - Shared vs. personal sources
   - Collaboration features (shared shortcuts, annotations)

2. **AI-Powered Intelligence**:
   - Trend detection across domains ("AI safety discussions increasing 40% this week")
   - Correlation analysis ("News X is related to Paper Y")
   - Personalized recommendations based on reading patterns
   - Smart summaries of daily highlights

3. **Source Marketplace**:
   - Community-contributed ETL modules
   - One-click source installation
   - Share custom sources with colleagues
   - Source quality ratings and reviews

4. **Advanced Analytics**:
   - Historical trend visualization
   - Comparative analysis (domain growth over time)
   - Export to BI tools (data warehouse integration)
   - API for programmatic access

5. **Integration Ecosystem**:
   - Slack/Discord notifications
   - Email digests (daily/weekly summaries)
   - Zapier/Make.com integration
   - Browser extension for quick access
   - Mobile apps (iOS/Android)

6. **Self-Service Extensions**:
   - No-code ETL builder (point-and-click source configuration)
   - Visual workflow designer
   - Template library for common patterns
   - AI-assisted source creation ("I want to monitor X" → auto-generate ETL)

---

## Web Application Specific Requirements

### Browser Support & Compatibility

**Target Browsers:**
- Chrome/Edge (Chromium): Primary (latest 2 versions)
- Firefox: Secondary (latest 2 versions)
- Safari: Secondary (latest 2 versions)
- Mobile browsers: iOS Safari, Chrome Mobile

**Compatibility Requirements:**
- Modern ES6+ JavaScript (no IE11 support needed)
- CSS Grid and Flexbox for layouts
- WebSocket support for real-time features (future)
- Local storage for user preferences

### Application Architecture

**Frontend Stack:**
- **Framework**: Dash (Python-based reactive framework)
- **UI Library**: dash-bootstrap-components for responsive design
- **Visualization**: Plotly for charts and data visualization
- **State Management**: Dash callbacks with single-callback pattern
- **Styling**: Bootstrap 5 CSS with custom theme

**Backend Stack:**
- **Language**: Python 3.10+
- **Web Server**: Dash development server (production: Gunicorn/WSGI)
- **Data Processing**: Pandas, Polars for high-performance data operations
- **Validation**: Pydantic models for type safety
- **Configuration**: Pydantic Settings with environment variables

**Data Layer:**
- **Storage**: File-based JSON (no database required)
- **File Structure**: `data/{source}/output/` for processed data
- **Caching Strategy**: Component-level caching, latest file symlinks
- **Performance**: Lazy loading, efficient JSON parsing

### Deployment & Operations

**Development Environment:**
- UV package manager for fast dependency management
- `.env` files for local configuration
- Hot reload for rapid development
- Port 7780 for main dashboard

**Production Requirements:**
- Docker support for containerization
- UnRAID deployment configuration
- Environment-based configuration
- Health check endpoints (`/health`, `/metrics`)
- Logging to files with rotation

**Monitoring & Observability:**
- ETL metrics collection (success rate, runtime, errors)
- Dashboard performance metrics (load times, errors)
- Watcher status monitoring (uptime, last check time)
- Error tracking with structured logging

### Security Requirements

**Authentication (Future - Growth Phase):**
- Simple user authentication (username/password)
- Session management with secure cookies
- No OAuth/SSO required initially (single-user/small team)

**Current Security:**
- Local network access only (no public internet exposure)
- Environment variables for sensitive config
- No user-generated content (low XSS risk)
- Input validation via Pydantic models
- HTTPS for production deployment (future)

**Data Privacy:**
- All data collected is public information (no PII)
- No tracking or analytics beyond system metrics
- User preferences stored locally

### Performance Requirements

**Dashboard Performance:**
- Initial page load: < 2 seconds
- Tab switching: < 500ms
- Filter application: < 300ms
- Search results: < 1 second

**Data Processing Performance:**
- ETL pipeline execution: < 5 minutes per source
- Batch processing: Configurable batch sizes
- Watcher polling: Configurable intervals (default: 1 hour)
- File I/O optimization: Minimize disk reads

**Scalability Targets:**
- Support 100+ data sources without degradation
- Handle 10,000+ items per dashboard tab
- Support 10 concurrent users (growth phase)
- 1 year of historical data retention

### Responsive Design

**Breakpoints:**
- Desktop: 1920px+ (primary target)
- Laptop: 1366px - 1920px
- Tablet: 768px - 1366px
- Mobile: 320px - 768px (basic support)

**Layout Behavior:**
- Fluid containers with Bootstrap grid
- Card-based layouts for content items
- Collapsible navigation for mobile
- Touch-friendly controls (44px minimum tap targets)

### Real-Time Features (Future)

**Watcher Integration:**
- WebSocket connection for live updates
- Server-sent events for notifications
- Background polling as fallback
- Optimistic UI updates

**Notification System:**
- Browser notifications (with permission)
- In-app notification center
- Email alerts (configurable)
- Desktop notifications (future)

---

## User Experience Principles

### Design Philosophy

**"Power Without Complexity"** - The dashboard should expose depth and detail without overwhelming the user. This is built for experts who want control, not casual browsers who need simplification.

**Visual Personality:**
- **Professional & Technical**: Dark theme with high contrast for readability
- **Information-Dense**: Maximize data visibility, minimize chrome
- **Functional Beauty**: Clean design that prioritizes utility over decoration
- **Responsive & Fast**: Instant feedback, no loading spinners for navigation

**Key Design Tenets:**

1. **Domain-First Navigation**: Primary navigation by content domain (AI, News, Deals, Training) not by source
2. **Scannable Content**: Card-based layouts with clear hierarchy (title, source, date, preview)
3. **Progressive Disclosure**: Essential info visible, details on click/hover
4. **Consistent Patterns**: Same interaction patterns across all tabs (filter → display → detail)
5. **Status Visibility**: Always show system health, last update times, data freshness

### Key Interactions

**Primary User Flows:**

**1. Daily Intelligence Gathering (Most Frequent)**
```
Open Dashboard → Scan Latest Updates → Filter by Domain → Dive into Details → External Link
```
- Default view shows newest content across all sources
- Domain tabs for focused exploration
- One-click access to original content

**2. Domain-Specific Deep Dive**
```
Select Domain Tab → Apply Filters (source/date/search) → Browse Results → Track Interesting Items
```
- Persistent filters within session
- Ability to mark/save items of interest (future)
- Quick switch between domains without losing context

**3. Source Discovery**
```
Navigate to Domain → Review Available Sources → Understand Coverage → Identify Gaps
```
- Clear indication of active sources per domain
- Source metadata (update frequency, item count)
- Easy identification of "what's missing"

**4. Time-Sensitive Monitoring**
```
Receive Alert → Open Dashboard → Locate New Deal/News → Take Action
```
- Visual indicators for new/updated content
- Time-sensitive items prominently displayed
- Quick access to expiring deals

**Interaction Patterns:**

**Filtering & Search:**
- Dropdown selectors for categorical filters (source, channel, category)
- Date range pickers for temporal filtering
- Full-text search with real-time results
- Clear filter state visibility
- One-click filter reset

**Content Cards:**
- Thumbnail/icon for visual identification
- Title (bold, truncated at 2 lines)
- Metadata (source, date, category)
- Preview text (if applicable)
- External link button/icon
- Hover state reveals additional details

**Navigation:**
- Top navbar with domain tabs
- Sticky header on scroll
- Active tab highlighting
- Mobile: Hamburger menu with collapsible tabs

**Performance Feedback:**
- Skeleton loaders for initial data fetch
- Instant tab switching (data pre-loaded)
- Loading indicators only for search/filter operations
- Toast notifications for errors

### Information Hierarchy

**Dashboard Layout Priority:**
```
1. Navigation (Domain Tabs) - Always visible
2. Filters/Search - Contextual, collapsible on scroll
3. Content Grid - Primary focus, maximum vertical space
4. System Status - Footer or notification area
```

**Content Card Priority:**
```
1. Title (most prominent)
2. Source/Channel (context)
3. Date (recency indicator)
4. Preview/Description (supporting detail)
5. Action (view/open link)
```

### Accessibility Considerations

**Baseline Requirements:**
- Keyboard navigation support (tab, enter, arrow keys)
- Sufficient color contrast (WCAG AA minimum)
- Alt text for images/icons
- Screen reader friendly semantic HTML
- Focus indicators for interactive elements

**Nice-to-Have:**
- Keyboard shortcuts for common actions (j/k navigation, filters)
- Customizable font sizes
- High contrast mode toggle
- Reduced motion option

---

## Functional Requirements

### FR-1: Data Source Management

**FR-1.1: Multi-Source Data Ingestion**
- **Requirement**: System must support 50+ diverse data sources across multiple protocols (RSS, REST APIs, web scraping, JSON feeds)
- **Current Sources**: ArXiv, HackerNews, Reddit, Medium, YouTube, GitHub, Steam, Epic Games, Udemy, Coursera, OpenAI, Anthropic, MyAnimeList, PubMed, 4chan, Spanish public aid sites, Valencia events
- **Acceptance Criteria**:
  - Each source has dedicated ETL pipeline
  - Sources organized by domain (AI, News, Deals, Training, Entertainment, Research)
  - Failed sources don't block other pipelines

**FR-1.2: Source Registry & Metadata**
- **Requirement**: Centralized catalog of all data sources with operational metadata
- **Metadata**: Source name, URL, update frequency, data schema, status (active/deprecated/failing), performance metrics
- **Acceptance Criteria**:
  - Machine-readable source registry (JSON/YAML)
  - Performance tracking (success rate, avg runtime, error count)
  - Documentation per source

**FR-1.3: Source Extensibility**
- **Requirement**: Adding new data source takes < 30 minutes
- **Process**: Create Pydantic model → Implement ETL class → Add dashboard tab → Test
- **Acceptance Criteria**:
  - BaseETL provides template method pattern
  - Standard project structure for new sources
  - Automated testing for new ETLs

### FR-2: ETL Processing Framework

**FR-2.1: BaseETL Template Pattern**
- **Requirement**: All ETL pipelines inherit from BaseETL with extract → transform → load phases
- **Features**: Metrics collection, checkpointing, retry logic, error handling, data validation
- **Acceptance Criteria**:
  - ETLMetrics tracked for all runs (start_time, end_time, items_processed, errors)
  - Checkpoint files enable resumable operations
  - Exponential backoff for transient failures

**FR-2.2: Data Transformation & Validation**
- **Requirement**: All data validated against Pydantic models before storage
- **Validation**: Type checking, required fields, data format validation, custom validators
- **Acceptance Criteria**:
  - Invalid data logged and rejected (not stored)
  - Detailed error messages for debugging
  - Validation metrics tracked

**FR-2.3: Batch Processing**
- **Requirement**: Configurable batch sizes for memory-efficient processing
- **Use Case**: Handle large datasets (10K+ items) without memory exhaustion
- **Acceptance Criteria**:
  - Batch size configurable per ETL
  - Progress tracking per batch
  - Partial success handling (some batches fail, others succeed)

**FR-2.4: Data Storage**
- **Requirement**: JSON file-based storage with timestamped outputs
- **Structure**: `data/{source}/output/{timestamp}.json` + `latest.json` symlink
- **Acceptance Criteria**:
  - Timestamped files for historical tracking
  - Latest file always points to most recent data
  - Automatic directory creation
  - File permissions managed

**FR-2.5: Retention Management**
- **Requirement**: Automatic cleanup of old timestamped files
- **Policy**: Configurable retention period (default: 30 days for most sources, 1 year for important sources)
- **Acceptance Criteria**:
  - Scheduled cleanup jobs
  - Retention policy per source type
  - Archive option for critical data

**FR-2.6: ETL Orchestration**
- **Requirement**: Run all ETL pipelines on demand or scheduled
- **Scripts**: `run_all_etl.sh` (Linux/Mac), `run_all_etl.bat` (Windows)
- **Acceptance Criteria**:
  - Sequential execution with error isolation
  - Overall success/failure summary
  - Execution time tracking
  - Parallel execution option (future)

### FR-3: Real-Time Monitoring (Watchers)

**FR-3.1: BaseWatcher Framework**
- **Requirement**: Watcher system for continuous monitoring with state persistence
- **Pattern**: Abstract base class with extract_value() and has_changed() methods
- **Acceptance Criteria**:
  - State stored in `data/watchers/{name}/state.json`
  - Event logs in `data/watchers/{name}/events/`
  - Configurable polling intervals

**FR-3.2: Change Detection**
- **Requirement**: Detect and log changes in monitored values
- **Use Cases**: New ArXiv papers, deal price changes, breaking news
- **Acceptance Criteria**:
  - Change events logged with timestamp
  - Previous and new values recorded
  - Notification triggers (future)

**FR-3.3: Watcher Resilience**
- **Requirement**: Individual watcher failures don't stop monitoring system
- **Error Handling**: Graceful degradation, error logging, automatic retry
- **Acceptance Criteria**:
  - Failed watchers logged but don't crash system
  - Retry with exponential backoff
  - Alert on persistent failures

### FR-4: Dashboard & Visualization

**FR-4.1: Unified Dashboard**
- **Requirement**: Single Dash-based web interface on port 7780
- **Technology**: Dash + Bootstrap components + Plotly
- **Acceptance Criteria**:
  - Responsive layout (desktop primary, mobile basic)
  - Dark theme for readability
  - Accessible via http://localhost:7780

**FR-4.2: Domain-Based Navigation**
- **Requirement**: Tab-based navigation organized by content domain
- **Domains**: Videos, Papers (AI/Research), News, Deals, Games, Courses, Entertainment, etc.
- **Acceptance Criteria**:
  - Top navbar with clickable tabs
  - Active tab highlighting
  - Fast tab switching (<500ms)
  - Mobile: Collapsible menu

**FR-4.3: Modular Component Architecture**
- **Requirement**: Each tab is independent component with data manager
- **Pattern**: Tab function + Manager class for data loading/filtering
- **Acceptance Criteria**:
  - Single callback per component (no conflicts)
  - Consistent component structure
  - Reusable utilities

**FR-4.4: Content Display**
- **Requirement**: Card-based layout for content items
- **Card Elements**: Thumbnail/icon, title, source, date, preview, external link
- **Acceptance Criteria**:
  - Scannable grid layout
  - Hover effects for additional details
  - Truncation for long titles/descriptions
  - Responsive grid (4 cols desktop, 2 cols tablet, 1 col mobile)

**FR-4.5: Interactive Filtering**
- **Requirement**: Real-time filtering by source, date, category, search
- **Filter Types**: Dropdown selectors, date pickers, text search
- **Acceptance Criteria**:
  - Instant filter application (<300ms)
  - Clear filter state display
  - One-click filter reset
  - Persistent filters within session

**FR-4.6: Data Loading & Performance**
- **Requirement**: Fast initial load and tab switching
- **Optimization**: Component-level caching, lazy loading, efficient JSON parsing
- **Acceptance Criteria**:
  - Initial page load <2 seconds
  - Tab switching <500ms
  - Handle 10,000+ items per tab
  - Skeleton loaders for initial fetch

**FR-4.7: Health Monitoring Endpoints**
- **Requirement**: API endpoints for system health checks
- **Endpoints**: `/health` (status), `/metrics` (performance data)
- **Acceptance Criteria**:
  - JSON responses with system status
  - ETL success rates
  - Data freshness indicators
  - Error counts

### FR-5: Search & Discovery

**FR-5.1: Full-Text Search**
- **Requirement**: Search across all content in current domain
- **Search Fields**: Title, description, source, tags
- **Acceptance Criteria**:
  - Real-time search results (<1 second)
  - Relevance ranking
  - Highlight search terms in results
  - Search within filtered results

**FR-5.2: Source Discovery**
- **Requirement**: Users can see all available sources per domain
- **Display**: Source list with metadata (item count, last update, status)
- **Acceptance Criteria**:
  - Filterable source list
  - Active/inactive status indicators
  - Link to source configuration

**FR-5.3: Content Recommendations** (Future - Growth)
- **Requirement**: Suggest relevant content based on user patterns
- **Approach**: ML-based relevance scoring or simple heuristics
- **Acceptance Criteria**:
  - "Recommended for you" section
  - Based on reading history
  - Configurable/dismissible

### FR-6: User Preferences & Customization

**FR-6.1: Basic Preferences** (Current)
- **Requirement**: Store user preferences locally
- **Settings**: Theme (dark/light), default view, items per page
- **Storage**: Browser local storage
- **Acceptance Criteria**:
  - Preferences persist across sessions
  - Easy reset to defaults

**FR-6.2: Advanced Customization** (Future - Growth)
- **Requirement**: Per-user dashboard customization
- **Features**: Tab visibility, tab ordering, saved filters, shortcuts
- **Acceptance Criteria**:
  - Drag-and-drop tab reordering
  - Hide unused tabs
  - Save filter presets
  - Personal shortcuts to sources

**FR-6.3: Multi-User Support** (Future - Vision)
- **Requirement**: Multiple users with individual profiles
- **Features**: Authentication, user profiles, personal feeds
- **Acceptance Criteria**:
  - User registration/login
  - Isolated user preferences
  - Shared vs. personal sources
  - Collaboration features

### FR-7: System Health & Monitoring

**FR-7.1: ETL Metrics Collection**
- **Requirement**: Track performance metrics for all ETL pipelines
- **Metrics**: Success rate, runtime, items processed, error count, last run time
- **Acceptance Criteria**:
  - Metrics stored per ETL run
  - Historical trending
  - Alert on degradation

**FR-7.2: Error Handling & Logging**
- **Requirement**: Comprehensive error tracking with context
- **Logging**: Structured logs with severity levels (DEBUG, INFO, WARNING, ERROR)
- **Acceptance Criteria**:
  - Logs stored in `logs/` directory
  - Component-specific log files
  - Log rotation to prevent disk fill
  - Error context preserved (stack traces, input data)

**FR-7.3: Automated Healing** (Future - Growth)
- **Requirement**: Automatically retry failed operations
- **Strategy**: Exponential backoff, circuit breaker pattern
- **Acceptance Criteria**:
  - Auto-retry failed ETL runs
  - Circuit breaker after repeated failures
  - Manual override to force retry
  - Alert on persistent failures

### FR-8: Extensibility Framework

**FR-8.1: ETL Template Generator** (Future - Growth)
- **Requirement**: CLI tool to scaffold new ETL pipelines
- **Generated Files**: Pydantic model, ETL class, dashboard tab, tests
- **Acceptance Criteria**:
  - Interactive wizard for source details
  - Standard project structure
  - Working boilerplate code
  - Integration tests included

**FR-8.2: Plugin Architecture** (Future - Vision)
- **Requirement**: Community-contributed sources as plugins
- **Features**: Plugin discovery, installation, version management
- **Acceptance Criteria**:
  - Plugin manifest format
  - One-click installation
  - Dependency management
  - Security validation

**FR-8.3: API for Programmatic Access** (Future - Vision)
- **Requirement**: REST API for external integrations
- **Endpoints**: Query data, trigger ETL runs, retrieve metrics
- **Acceptance Criteria**:
  - RESTful API design
  - API authentication
  - Rate limiting
  - OpenAPI documentation

### FR-9: Data Quality & Intelligence

**FR-9.1: Duplicate Detection** (Future - Growth)
- **Requirement**: Identify and merge duplicate content across sources
- **Algorithm**: Fuzzy matching on title + content similarity
- **Acceptance Criteria**:
  - <1% false positives
  - Manual review for edge cases
  - Configurable similarity threshold

**FR-9.2: NLP Classification** (Current - Enhancement Needed)
- **Requirement**: Automated content categorization and tagging
- **Categories**: Technology areas, sentiment, importance
- **Acceptance Criteria**:
  - Category assignment per item
  - Confidence scores
  - User feedback to improve

**FR-9.3: Trend Detection** (Future - Vision)
- **Requirement**: Identify emerging trends across domains
- **Analysis**: Topic clustering, growth rate tracking, correlation detection
- **Acceptance Criteria**:
  - "Trending now" indicator
  - Historical trend visualization
  - Cross-domain correlation alerts

### FR-10: Integration & Notifications

**FR-10.1: Notification System** (Future - Growth)
- **Requirement**: Real-time alerts for high-value content
- **Channels**: Browser notifications, email, Slack/Discord
- **Acceptance Criteria**:
  - Configurable notification rules
  - Opt-in per channel
  - Rate limiting to prevent spam
  - Notification history

**FR-10.2: External Integrations** (Future - Vision)
- **Requirement**: Connect with external tools
- **Integrations**: Zapier, email digests, browser extension, mobile apps
- **Acceptance Criteria**:
  - OAuth for third-party services
  - Webhook support
  - Integration marketplace

---

## Non-Functional Requirements

### Performance

**NFR-1: Dashboard Response Times**
- **Initial Page Load**: < 2 seconds (target: 1.5s)
- **Tab Switching**: < 500ms (target: 300ms)
- **Filter Application**: < 300ms (target: 200ms)
- **Search Results**: < 1 second (target: 500ms)
- **Measurement**: 95th percentile on development hardware (laptop)
- **Rationale**: Fast interaction keeps users engaged and productive

**NFR-2: ETL Pipeline Performance**
- **Single Pipeline Execution**: < 5 minutes per source (target: 2-3 minutes)
- **Full ETL Suite**: < 2 hours for all 50+ sources (target: 1 hour with parallelization)
- **Data Processing Rate**: > 100 items/second for transform operations
- **Memory Efficiency**: < 500MB RAM per ETL process
- **Rationale**: Regular updates require fast processing without resource exhaustion

**NFR-3: Data Loading Efficiency**
- **JSON Parsing**: < 100ms for files up to 5MB
- **Data Caching**: 90%+ cache hit rate for repeated accesses within session
- **Lazy Loading**: Only load data when tab is accessed (not all upfront)
- **Concurrent Requests**: Handle 10 simultaneous API requests without blocking
- **Rationale**: Large datasets (10K+ items) must load quickly

**NFR-4: Watcher Performance**
- **Polling Interval**: Configurable (default: 1 hour, minimum: 5 minutes)
- **Check Duration**: < 30 seconds per watcher
- **Resource Usage**: < 50MB RAM per active watcher
- **Concurrent Watchers**: Support 20+ watchers running simultaneously
- **Rationale**: Continuous monitoring without degrading system performance

### Security

**NFR-5: Data Security**
- **Sensitive Configuration**: All API keys, tokens, passwords stored in environment variables or `.env` files (never committed to git)
- **File Permissions**: Data directories have appropriate permissions (read/write for app user only)
- **Input Validation**: All external data validated via Pydantic models before processing
- **Injection Prevention**: No direct SQL (file-based), parameterized queries if database added
- **Rationale**: Protect API credentials and prevent malicious data injection

**NFR-6: Network Security** (Current: Local, Future: Remote)
- **Current State**: Local network only (localhost or LAN)
- **HTTPS**: Required for production deployment outside localhost
- **CORS**: Configured to allow only trusted origins
- **Rate Limiting**: API endpoints rate-limited to prevent abuse (future)
- **Rationale**: Initial single-user deployment is low-risk; multi-user requires HTTPS

**NFR-7: Authentication & Authorization** (Future - Growth Phase)
- **Authentication**: Username/password with bcrypt hashing (minimum)
- **Session Management**: Secure HTTP-only cookies, automatic timeout
- **Authorization**: Role-based access control (admin, user, viewer)
- **Password Policy**: Minimum 12 characters, no complexity requirements (passphrase-friendly)
- **Rationale**: Multi-user deployment requires access control

**NFR-8: Dependency Security**
- **Vulnerability Scanning**: Automated scanning via `pip-audit` or Dependabot
- **Update Policy**: Critical vulnerabilities patched within 7 days, high within 30 days
- **Dependency Minimization**: Only add dependencies with strong justification
- **Version Pinning**: Lock file (requirements.txt or uv.lock) for reproducible builds
- **Rationale**: Prevent security vulnerabilities from third-party dependencies

### Scalability

**NFR-9: Data Volume Scalability**
- **Sources**: Support 100+ data sources without architectural changes
- **Items per Domain**: Handle 10,000+ items per dashboard tab with pagination
- **Historical Data**: Store 1 year of historical data without performance degradation
- **Database Migration Path**: File-based JSON scalable to 1M+ items; database optional for >1M
- **Rationale**: Platform should grow from 50 to 100+ sources without major refactoring

**NFR-10: User Scalability** (Future - Vision)
- **Concurrent Users**: Support 10 concurrent users without resource contention
- **User Growth**: Architecture supports 50+ users with proper infrastructure
- **Resource Isolation**: Per-user queries don't impact other users
- **Horizontal Scaling**: Load balancer + multiple app instances for high user load
- **Rationale**: Multi-user adoption requires concurrent access without slowdown

**NFR-11: Processing Scalability**
- **Parallel ETL Execution**: Support parallel execution of independent ETL pipelines
- **Batch Size Optimization**: Configurable batch sizes for memory vs. speed tradeoff
- **Worker Processes**: Use multi-processing for CPU-bound operations (NLP, parsing)
- **Queue System**: Optional job queue (Celery/RQ) for ETL orchestration at scale
- **Rationale**: Growing sources require efficient parallel processing

**NFR-12: Storage Scalability**
- **File System**: JSON file storage scales to 10GB without issues on modern systems
- **Compression**: Optional gzip compression for historical data (90% space savings)
- **Retention Policies**: Automatic cleanup prevents unbounded storage growth
- **Database Option**: Migration path to PostgreSQL/MongoDB if file-based hits limits
- **Rationale**: Long-term operation requires bounded storage growth

### Reliability

**NFR-13: System Availability**
- **Uptime Target**: 99%+ for dashboard (7 hours downtime/month acceptable)
- **ETL Reliability**: 99%+ success rate for stable sources, 95%+ for scraping-based sources
- **Watcher Reliability**: < 1 hour of undetected downtime per watcher per month
- **Graceful Degradation**: Failed individual sources don't crash entire system
- **Rationale**: Personal/small team use tolerates occasional downtime; critical data shouldn't be missed

**NFR-14: Error Recovery**
- **Automatic Retry**: Transient failures retried with exponential backoff (3 attempts)
- **Checkpointing**: ETL processes resumable from last successful checkpoint
- **Error Logging**: All failures logged with context for manual investigation
- **Alert Mechanism**: Persistent failures trigger notifications (future)
- **Rationale**: Minimize manual intervention for transient issues

**NFR-15: Data Integrity**
- **Validation**: All data validated before storage (invalid data rejected, not stored)
- **Atomic Writes**: File writes are atomic (temp file + rename pattern)
- **Backup Strategy**: Daily backups of critical data (source configurations, user preferences)
- **Rollback Capability**: Previous timestamped files enable rollback
- **Rationale**: Data quality and recoverability are critical for trust

### Maintainability

**NFR-16: Code Quality Standards**
- **Type Hints**: 100% coverage for function signatures (Python 3.10+ syntax)
- **Linting**: Ruff configured with strict rules, zero violations allowed
- **Formatting**: Ruff auto-formatting with consistent style
- **Documentation**: Google-style docstrings for all public functions/classes
- **Rationale**: High code quality enables rapid extension and debugging

**NFR-17: Testing Standards**
- **Unit Test Coverage**: > 70% for ETL and model code
- **Integration Tests**: Key workflows (ETL end-to-end, dashboard loading) covered
- **Test Execution**: Full test suite runs in < 5 minutes
- **CI/CD Integration**: Tests run automatically on commit (GitHub Actions)
- **Rationale**: Testing prevents regressions as sources grow

**NFR-18: Architecture Documentation**
- **CLAUDE.md**: Comprehensive project guide maintained for AI-assisted development
- **README.md**: Quick start guide for setup and basic operations
- **Inline Comments**: Complex logic explained with comments
- **ADR (Architecture Decision Records)**: Major architectural decisions documented
- **Rationale**: Brownfield project requires excellent documentation for maintainability

**NFR-19: Extensibility Standards**
- **BaseETL Pattern**: All new ETLs follow template method pattern
- **Pydantic Models**: All data uses type-safe models
- **Configuration Management**: Settings externalized, not hardcoded
- **Modular Design**: Dashboard tabs, ETLs, watchers are independent modules
- **Rationale**: Architectural consistency enables <30 min source additions

### Usability

**NFR-20: Learning Curve**
- **First-Time Setup**: < 15 minutes from clone to running dashboard (with UV)
- **Adding First Source**: < 2 hours for Python-proficient developer (with example)
- **Dashboard Navigation**: Intuitive for tech users without training
- **Documentation Quality**: Self-service answers for 90%+ of questions
- **Rationale**: Target users are technical but need smooth onboarding

**NFR-21: Error Messages**
- **User-Facing Errors**: Clear, actionable messages (not stack traces)
- **Developer Errors**: Detailed context in logs for debugging
- **Recovery Guidance**: Errors suggest next steps ("Check your API key in .env")
- **Error Context**: Enough information to diagnose without asking for more
- **Rationale**: Fast problem resolution without extensive debugging

### Compatibility

**NFR-22: Platform Support**
- **Operating Systems**: Windows 10+, macOS 11+, Linux (Ubuntu 20.04+)
- **Python Version**: Python 3.10+ (f-strings, match statements, type hints)
- **Browser Support**: Chrome/Edge (latest 2), Firefox (latest 2), Safari (latest 2)
- **Deployment Targets**: Local development, Docker, UnRAID
- **Rationale**: Support major platforms without extensive testing overhead

**NFR-23: Dependency Compatibility**
- **Package Manager**: UV (primary), pip/venv (fallback)
- **Core Dependencies**: Dash, Pydantic, Pandas, Requests, BeautifulSoup4, Playwright
- **Version Constraints**: Lock file ensures reproducible builds
- **Upgrade Policy**: Major dependency updates tested in isolation first
- **Rationale**: Stable dependencies prevent "works on my machine" issues

---

## Implementation Planning

### Epic Breakdown Required

Requirements must be decomposed into epics and bite-sized stories (200k context limit).

**Next Step:** Run `workflow epics-stories` to create the implementation breakdown.

This PRD contains:
- **10 Functional Requirement Areas** with 33 specific requirements (FR-1 through FR-10)
- **23 Non-Functional Requirements** across 7 categories (NFR-1 through NFR-23)
- **Clear Phasing**: Current baseline, Growth (3-6 months), Vision (6-12+ months)

---

## PRD Summary

### What We've Captured

**Vision & Purpose:**
Megalith is a self-extending intelligence platform that solves the complexity problem of monitoring 50+ diverse information sources. Built for power users, it provides unified dashboard access while maintaining architecture optimized for rapid extensibility (<30 min per source).

**Success Criteria:**
- Daily indispensability as primary information source
- <30 min source integration time achieved
- Zero missed opportunities via real-time monitoring
- 3-5 colleague adoption within 6 months

**Product Scope:**
- **Current Baseline**: 50+ ETL pipelines, Dash dashboard, watcher system, all operational requirements maintained
- **Growth (3-6 months)**: 12 key improvements in extensibility, data quality, UX, and operations
- **Vision (6-12+ months)**: Multi-user platform with AI intelligence, source marketplace, advanced analytics, integration ecosystem

**Requirements Summary:**
- **33 Functional Requirements** organized into 10 capability areas
- **23 Non-Functional Requirements** covering performance, security, scalability, reliability, maintainability, usability, and compatibility
- **Clear Phasing** with acceptance criteria for each requirement

**Technical Classification:**
- Web Application (Dash + Python backend)
- High architectural complexity, general domain (no regulatory requirements)
- Brownfield project with sophisticated existing patterns

**The Magic Thread:**
Architecture-first extensibility enables Megalith to grow infinitely while maintaining developer velocity. What takes days in other systems takes minutes here - that's the special sauce that makes this indispensable.

---

## References

- **Project Documentation**: docs/bmm-index.md
- **Brainstorming Session**: docs/bmm-brainstorming-session-2025-01-11.md
- **Technical Research**: docs/research-technical-2025-01-11.md
- **Workflow Status**: docs/bmm-workflow-status.yaml

---

## Next Steps

### Required Next Steps

1. **Epic & Story Breakdown** (Required)
   - Command: `/bmad:bmm:workflows:create-epics-and-stories` or menu option `*create-epics-and-stories`
   - Purpose: Decompose 33 functional requirements into implementable epics and bite-sized stories
   - Output: Epic breakdown document with story mapping

2. **Architecture Document** (Recommended)
   - Command: `/bmad:bmm:workflows:architecture` or menu option `*create-architecture`
   - Purpose: Document technical architecture decisions, patterns, and technology choices
   - Output: Architecture decision document optimized for AI agent consistency

3. **Solutioning Gate Check** (Required before Implementation)
   - Command: `/bmad:bmm:workflows:solutioning-gate-check`
   - Purpose: Validate PRD + Architecture alignment before Phase 4 implementation
   - Output: Gate check report with readiness assessment

### Optional Enhancement Steps

4. **PRD Validation** (Optional)
   - Command: Menu option `*validate-prd`
   - Purpose: Systematic validation of PRD completeness and quality
   - Output: Validation report with improvement recommendations

5. **UX Design** (Conditional - if major UI changes planned)
   - Command: `/bmad:bmm:workflows:create-ux-design`
   - Purpose: Detailed user experience design for new features
   - Output: UX design document with mockups and interaction flows

---

## Product Magic Summary

**The essence of Megalith**: A personal intelligence framework that eliminates the pain of monitoring 50+ diverse information sources by providing a unified dashboard with architecture designed for infinite extensibility. The magic lies in its <30-minute source integration capability - transforming what would be multi-day projects into streamlined workflows. Built for power users who need depth, not simplification, Megalith becomes indispensable: everything important in one place, nothing important missed, infinitely extensible.

---

_Created through collaborative discovery between Joshi and AI Product Manager_
_Date: 2025-01-11_
