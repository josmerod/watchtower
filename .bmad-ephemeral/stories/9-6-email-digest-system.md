# Story 9.6: Email Digest System

Status: drafted

## Story

As a **user**,
I want **daily or weekly email digests of important content**,
So that **I stay informed even when not actively checking Megalith**.

## Acceptance Criteria

1. **Given** I've enabled email digests in my user preferences
   **When** the digest schedule triggers (daily/weekly)
   **Then** I receive an email with: top stories, trending content, alert summary, personalized recommendations

2. **And** email is formatted with responsive HTML design that works across all email clients and devices

3. **And** each item links back to dashboard with proper context and deep linking

4. **And** I can unsubscribe or change frequency through email links and dashboard preferences

5. **And** I can customize which content appears in digest based on sources, categories, and alert types

6. **And** digest content is personalized using recommendations from Story 8.1 and trends from Story 8.2

## Tasks / Subtasks

- [ ] **Email Template System and Design** (AC: 1, 2, 3)
  - [ ] Create responsive HTML email templates using Jinja2 templating engine
  - [ ] Design email templates with Megalith branding and consistent styling
    - [ ] Daily digest template: Top 10 items + 3 alerts from last 24 hours
    - [ ] Weekly digest template: Top 20 items + trend summary from last 7 days
    - [ ] Alert-specific template for critical notifications
  - [ ] Implement fallback plain text versions for email clients that don't support HTML
  - [ ] Create email preview and testing system for template validation
  - [ ] Add responsive design testing for major email clients (Gmail, Outlook, Apple Mail)

- [ ] **Email Infrastructure and Delivery** (AC: 1, 4)
  - [ ] Set up SMTP configuration for email sending with fallback to SendGrid/Mailgun
  - [ ] Create email service in `src/services/email_service.py` with queue management
  - [ ] Implement email queue system for handling high-volume digest delivery
  - [ ] Add email delivery status tracking and bounce handling
  - [ ] Create email sending analytics and performance monitoring
  - [ ] Implement rate limiting and throttling for email service providers

- [ ] **Digest Content Generation and Personalization** (AC: 1, 5, 6)
  - [ ] Create digest generation service in `src/services/digest_service.py`
  - [ ] Implement personalized content selection using Story 8.1 recommendation algorithms
  - [ ] Integrate trending content analysis using Story 8.2 trend indicators
  - [ ] Create content filtering system based on user preferences and source categories
  - [ ] Implement alert summary generation with priority and relevance scoring
  - [ ] Add content deduplication and quality filtering for digest items

- [ ] **Scheduling and Automation System** (AC: 1, 6)
  - [ ] Create cron job scheduler or Celery beat configuration for digest generation
  - [ ] Implement user-specific scheduling with timezone support
  - [ ] Create digest generation pipeline with error handling and retry logic
  - [ ] Add digest preview system for users to see upcoming content
  - [ ] Implement manual digest generation for testing and special occasions
  - [ ] Create scheduling analytics and performance monitoring

- [ ] **User Preferences and Configuration Management** (AC: 4, 5)
  - [ ] Extend user profile with email digest preferences and configuration
  - [ ] Create digest preference management in dashboard UI:
    - [ ] Enable/disable email digests
    - [ ] Choose frequency (daily, weekly, custom)
    - [ ] Select preferred delivery time and timezone
    - [ ] Configure content sources and categories
    - [ ] Set alert types and priority thresholds
  - [ ] Implement unsubscribe system with secure token verification
  - [ ] Create preference management API endpoints for email settings

- [ ] **Content Aggregation and Intelligence Integration** (AC: 1, 6)
  - [ ] Integrate with Story 8.1 usage-based recommendations for personalized content
  - [ ] Connect with Story 8.2 trend indicators for trending content identification
  - [ ] Create content scoring algorithm combining multiple intelligence sources:
    - [ ] User engagement metrics and reading history
    - [ ] Content relevance and personalization scores
    - [ ] Trend analysis and popularity indicators
    - [ ] Alert priority and urgency assessment
  - [ ] Implement content categorization and source filtering
  - [ ] Add content quality assessment and duplicate detection

- [ ] **Email Tracking and Analytics** (AC: 3, 4)
  - [ ] Implement email open tracking using transparent pixels (optional with privacy)
  - [ ] Create click-through tracking for digest items and dashboard links
  - [ ] Add unsubscribe rate monitoring and analytics
  - [ ] Create email engagement dashboard showing open rates, click-throughs, and user preferences
  - [ ] Implement A/B testing for email templates and content optimization
  - [ ] Add digest performance metrics and content effectiveness analysis

- [ ] **Database Models and Storage** (AC: 1, 4, 5)
  - [ ] Extend SQLite database with email digest tables:
    - [ ] EmailDigestConfig: user preferences, scheduling, content filters
    - [ ] EmailDigest: generated digest content, delivery status, analytics
    - [ ] EmailTracking: open rates, click-throughs, engagement metrics
  - [ ] Create database migrations for email digest functionality
  - [ ] Implement email content storage with version history and rollback capability
  - [ ] Add data retention policies for email analytics and tracking data
  - [ ] Create indexes for efficient digest queries and user preference lookups

- [ ] **Security and Privacy Compliance** (AC: 2, 4)
  - [ ] Implement secure unsubscribe tokens with expiration and validation
  - [ ] Add email verification for digest subscription changes
  - [ ] Create GDPR compliance features for email processing and user data
  - [ ] Implement email content security and XSS prevention
  - [ ] Add rate limiting for email preference changes to prevent abuse
  - [ ] Create audit logging for email digest activities and user actions

- [ ] **Testing and Quality Assurance** (AC: 1, 2, 3)
  - [ ] Create comprehensive test suite for email digest functionality
  - [ ] Implement email template testing across different email clients
  - [ ] Add integration tests for content generation and personalization algorithms
  - [ ] Create end-to-end tests for complete digest generation and delivery workflow
  - [ ] Implement load testing for high-volume email digest delivery
  - [ ] Add security testing for unsubscribe functionality and preference management

- [ ] **Monitoring and Maintenance** (AC: 1, 4, 6)
  - [ ] Create email digest health monitoring and alerting
  - [ ] Implement delivery failure detection and recovery mechanisms
  - [ ] Add content quality monitoring and user feedback collection
  - [ ] Create automated testing for email templates and content generation
  - [ ] Implement performance monitoring for digest generation and delivery times
  - [ ] Create maintenance tools for email list management and cleanup

## Dev Notes

### Architecture Patterns and Constraints

The Email Digest System leverages Megalith's intelligence capabilities while introducing reliable email delivery and personalization:

- **Intelligence Integration**: Uses Story 8.1 recommendations and Story 8.2 trends for personalized content selection
- **Email Infrastructure**: SMTP with fallback to commercial services (SendGrid/Mailgun) for reliable delivery
- **Template System**: Jinja2-based responsive HTML templates with fallback plain text versions
- **Scheduling**: Cron-based automation with Celery beat for reliable digest generation timing
- **Analytics**: Email tracking and engagement monitoring while respecting user privacy preferences

Key architectural constraints:
- **Prerequisite Dependencies**: Stories 8.1 (recommendations) and 8.2 (trends) must be completed for personalization
- **Email Client Compatibility**: Templates must work across diverse email clients with varying HTML/CSS support
- **Performance**: Digest generation must complete efficiently for large user bases without impacting dashboard performance
- **Privacy**: Email tracking must be implemented with user consent and privacy compliance
- **Deliverability**: Email sending must respect ISP rate limits and maintain good sender reputation

### Source Tree Components to Touch

```
src/services/                              # ENHANCEMENT - Add email and digest services
├── email_service.py                       # NEW - Email sending and delivery management
├── digest_service.py                      # NEW - Digest content generation and personalization
├── template_service.py                    # NEW - Email template rendering and management
├── scheduler_service.py                   # NEW - Digest scheduling and automation
├── analytics_service.py                   # ENHANCEMENT - Add email analytics tracking
└── integrations/                          # NEW - External service integrations
    ├── __init__.py
    ├── sendgrid_client.py                 # SendGrid API integration (optional)
    ├── mailgun_client.py                  # Mailgun API integration (optional)
    └── smtp_client.py                     # SMTP client configuration and management

src/api/                                   # ENHANCEMENT - Add email digest API endpoints
├── endpoints/                             # ENHANCEMENT - Add digest management endpoints
│   └── email_digests.py                   # Email digest preferences and management API
├── models/                                # ENHANCEMENT - Add email digest API models
│   └── digest_models.py                   # API request/response models for email digests
└── middleware/                            # ENHANCEMENT - Add email-specific middleware
    └── rate_limiting.py                   # ENHANCEMENT - Add email API rate limiting

src/web/dashboard/components/               # ENHANCEMENT - Add email digest UI
├── email_digest_preferences_tab.py        # NEW - Email digest configuration interface
├── digest_preview_panel.py                # NEW - Digest content preview and testing
├── email_analytics_dashboard.py           # NEW - Email engagement analytics and metrics
└── template_gallery_interface.py          # NEW - Email template gallery and customization

data/                                      # ENHANCEMENT - Add email digest data storage
├── megalith.db                            # ENHANCEMENT - SQLite with email digest tables
│   ├── email_digest_configs               # NEW - User email digest preferences
│   ├── email_digests                      # NEW - Generated digest content and delivery logs
│   ├── email_tracking                     # NEW - Email open and click tracking data
│   └── email_templates                    # NEW - Custom email templates and versions
└── email_digests/                         # NEW - Email digest specific data storage
    ├── templates/                         # Email template storage and versions
    │   ├── daily_digest.html              # Daily digest HTML template
    │   ├── weekly_digest.html             # Weekly digest HTML template
    │   ├── daily_digest.txt               # Daily digest plain text template
    │   └── weekly_digest.txt              # Weekly digest plain text template
    ├── generated/                         # Generated digest content and analytics
    │   ├── {user_id}/                     # User-specific digest data
    │   │   ├── latest/                    # Most recent digest versions
    │   │   ├── history/                   # Historical digest archive
    │   │   └── analytics.json             # User-specific engagement analytics
    │   ├── analytics/                     # Aggregate analytics and metrics
    │   └── failed/                        # Failed digest generation and delivery logs
    ├── assets/                            # Email template assets and images
    │   ├── images/                        # Embedded images and branding assets
    │   ├── css/                           # Email-specific CSS styles
    │   └── fonts/                         # Custom fonts for email templates
    └── queues/                            # Email delivery queues and processing
        ├── pending/                       # Pending email deliveries
        ├── processing/                    # Currently processing emails
        └── failed/                        # Failed delivery retry queue

src/utils/                                 # ENHANCEMENT - Add email utilities
├── email_utils.py                         # NEW - Email formatting and validation utilities
├── template_utils.py                      # NEW - Jinja2 template rendering utilities
├── content_aggregator.py                  # NEW - Content aggregation and filtering
└── privacy_utils.py                       # NEW - Email privacy and compliance utilities

scripts/                                  # NEW - Email digest automation scripts
├── generate_daily_digests.py             # Daily digest generation script
├── generate_weekly_digests.py            # Weekly digest generation script
├── cleanup_old_digests.py                 # Old digest cleanup and maintenance
├── email_performance_monitoring.py        # Email delivery performance monitoring
└── digest_analytics_processing.py         # Email analytics processing and reporting

Tests/                                     # ENHANCEMENT - Add email digest testing
├── email_digests/                         # NEW - Email digest test suite
│   ├── test_email_service.py              # Email delivery and SMTP testing
│   ├── test_digest_service.py             # Digest content generation testing
│   ├── test_template_service.py           # Email template rendering testing
│   ├── test_scheduler_service.py          # Digest scheduling automation testing
│   └── test_email_analytics.py            # Email analytics and tracking testing
└── fixtures/                              # ENHANCEMENT - Add email test data
    ├── email_templates/                   # Test email templates and samples
    ├── sample_digests/                    # Sample digest content for testing
    └── mock_email_responses.json          # Mock email service responses

config/                                   # ENHANCEMENT - Add email configuration
├── email_config.yaml                      # NEW - Email service configuration
├── smtp_settings.yaml                    # NEW - SMTP server configuration
└── digest_templates/                      # NEW - Digest template configurations
```

### Testing Standards Summary

Email digest testing requires specialized approaches due to external dependencies and client variability:

- **Template Testing**: Test email templates across major email clients (Gmail, Outlook, Apple Mail) with responsive design validation
- **Content Generation**: Validate digest content generation, personalization algorithms, and recommendation integration
- **Delivery Testing**: Test email delivery through SMTP and commercial services with error handling and retry logic
- **Integration Testing**: Test integration with Story 8.1 recommendations and Story 8.2 trends for content personalization
- **Performance Testing**: Monitor digest generation time and email queue performance for large user bases
- **Security Testing**: Validate unsubscribe token security, preference management, and privacy compliance

Use existing pytest patterns with mocking for external email services and template rendering.

### Project Structure Notes

The Email Digest System transforms Megalith from a pull-based platform into a proactive intelligence delivery system:

**Personalized Content Curation:**
- **Intelligence Integration**: Leverages Story 8.1 usage-based recommendations and Story 8.2 trend indicators for highly personalized content selection
- **Smart Filtering**: Advanced content filtering based on user preferences, reading history, and engagement patterns
- **Quality Scoring**: Multi-factor content quality assessment combining relevance, freshness, and user interest alignment
- **Adaptive Learning**: Content selection algorithms learn from user engagement and digest interaction patterns

**Professional Email Design:**
- **Responsive Templates**: Modern HTML email templates using Jinja2 with cross-client compatibility and fallback plain text versions
- **Brand Consistency**: Megalith-branded email design maintaining visual consistency with dashboard and documentation
- **Accessibility**: WCAG-compliant email design with proper color contrast, text sizing, and screen reader support
- **Interactive Elements**: Rich email content with dashboard deep linking and actionable engagement tracking

**Enterprise-Grade Delivery:**
- **Multi-Provider Support**: SMTP with commercial service fallback (SendGrid/Mailgun) for reliable delivery and scalability
- **Queue Management**: Advanced email queuing system with retry logic, bounce handling, and delivery monitoring
- **Performance Optimization**: Efficient digest generation with background processing and minimal impact on dashboard performance
- **Analytics Integration**: Comprehensive email analytics tracking engagement, delivery rates, and content effectiveness

**User-Controlled Experience:**
- **Flexible Scheduling**: Daily, weekly, or custom digest scheduling with timezone-aware delivery and personalized timing
- **Granular Preferences**: Detailed control over content sources, categories, alert types, and digest frequency
- **Privacy Protection**: Optional tracking with transparent privacy controls and GDPR compliance features
- **Easy Management**: One-click unsubscribe, preference management through email links, and dashboard integration

**No conflicts detected** - provides proactive intelligence delivery while maintaining full compatibility with existing recommendation systems and user preferences.

### Prerequisites

- **Story 8.1 (Usage-Based Recommendations)**: Must be completed for personalized content selection and recommendation algorithms
- **Story 8.2 (Simple Trend Indicators)**: Must be completed for trending content identification and trend analysis
- **Story 9.1 (REST API Foundation)**: Must be completed for email digest preference management APIs
- **Existing User System**: Leverages existing user authentication, preferences, and profile management

### Email Digest Template Specifications

**Daily Digest HTML Template Structure:**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Megalith Daily Digest - {{ date }}</title>
  <style>
    /* Responsive email CSS with inline styles for maximum compatibility */
  </style>
</head>
<body>
  <div class="email-container">
    <!-- Email Header -->
    <header class="email-header">
      <img src="https://megalith.local/assets/logo.png" alt="Megalith" class="logo">
      <h1>Daily Intelligence Digest</h1>
      <p class="date">{{ date|date("F j, Y") }}</p>
    </header>

    <!-- Personalized Summary -->
    <section class="summary">
      <h2>Hello {{ user_name }},</h2>
      <p>Here's your personalized intelligence summary with {{ total_items }} updates from your followed sources.</p>
    </section>

    <!-- Top Stories Section -->
    <section class="top-stories">
      <h2>🔥 Top Stories Today</h2>
      {% for item in top_stories[:5] %}
      <div class="story-item">
        <h3><a href="{{ item.dashboard_link }}">{{ item.title }}</a></h3>
        <p class="source">{{ item.source_name }} • {{ item.published_time }}</p>
        <p class="summary">{{ item.summary|truncate(150) }}</p>
        <div class="tags">
          {% for tag in item.categories %}
          <span class="tag">{{ tag }}</span>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </section>

    <!-- Trending Content Section -->
    <section class="trending">
      <h2>📈 Trending in Your Interests</h2>
      {% for trend in trending_content[:3] %}
      <div class="trend-item">
        <h4>{{ trend.topic }}</h4>
        <p>{{ trend.description }}</p>
        <a href="{{ trend.dashboard_link }}">View {{ trend.item_count }} items</a>
      </div>
      {% endfor %}
    </section>

    <!-- Alert Summary Section -->
    <section class="alerts">
      <h2>🚨 Recent Alerts</h2>
      {% for alert in recent_alerts[:3] %}
      <div class="alert-item {{ alert.severity|lower }}">
        <h4>{{ alert.title }}</h4>
        <p>{{ alert.message|truncate(100) }}</p>
        <a href="{{ alert.dashboard_link }}">View Details</a>
      </div>
      {% endfor %}
    </section>

    <!-- Email Footer -->
    <footer class="email-footer">
      <p><a href="{{ dashboard_link }}">View Full Dashboard</a></p>
      <div class="preferences">
        <a href="{{ unsubscribe_link }}">Unsubscribe</a> •
        <a href="{{ preferences_link }}">Manage Preferences</a>
      </div>
      <p class="privacy">You're receiving this email because you subscribed to Megalith digests.</p>
    </footer>
  </div>
</body>
</html>
```

### Integration Strategy

**Content Intelligence Integration:**
- **Recommendation Engine**: Direct integration with Story 8.1 algorithms for personalized content scoring and selection
- **Trend Analysis**: Real-time integration with Story 8.2 trend indicators for identifying emerging topics and popular content
- **User Behavior**: Analysis of user engagement patterns to refine digest content and improve personalization accuracy
- **Content Diversity**: Balanced content selection ensuring coverage across different sources and categories while maintaining relevance

**Email Delivery Architecture:**
- **Provider Flexibility**: Multi-provider support with automatic failover between SMTP and commercial email services
- **Queue Management**: Advanced email queuing with priority handling for time-sensitive content and user preference-based scheduling
- **Performance Optimization**: Background processing and intelligent batching to handle large user volumes without system impact
- **Delivery Monitoring**: Real-time delivery tracking with bounce handling, retry logic, and performance analytics

### References

- [Source: docs/epics.md#Story-96-Email-Digest-System] - Epic requirements and email digest specifications
- [Source: stories/8-1-usage-based-recommendations.md] - Prerequisite: Usage-based recommendation system for content personalization
- [Source: stories/8-2-simple-trend-indicators.md] - Prerequisite: Trend indicators for trending content identification
- [Source: stories/9-1-rest-api-foundation.md] - Previous story: REST API foundation for preference management
- [Source: docs/architecture.md#Decision-Summary] - Technology choices: SMTP integration, template systems, scheduling automation

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

### Change Log

**Created**: 2025-11-19 - Initial story draft with comprehensive email digest system requirements including personalized content delivery, responsive email templates, and intelligence integration
