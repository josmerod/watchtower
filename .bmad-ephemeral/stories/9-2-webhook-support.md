# Story 9.2: Webhook Support

Status: drafted

## Story

As a **developer**,
I want **webhooks to receive real-time events**,
So that **external systems can react to Megalith events**.

## Acceptance Criteria

1. **Given** I've configured a webhook URL in my user profile and selected specific events to monitor
   **When** an event occurs (new content, alert triggered, source updated)
   **Then** Megalith sends HTTP POST to my webhook URL with structured payload

2. **And** payload includes: event_type, timestamp, data relevant to the event, and HMAC-SHA256 signature for verification

3. **And** failed webhooks are retried automatically with exponential backoff (3 attempts: 30s, 5m, 30m delays)

4. **And** comprehensive webhook logs show delivery status, timestamps, retry attempts, and error details

5. **And** I can test webhook configuration with sample payloads for each supported event type

6. **And** webhook endpoints respond with proper HTTP status codes and delivery confirmation

## Tasks / Subtasks

- [ ] **Webhook Configuration and Management System** (AC: 1, 5, 6)
  - [ ] Create webhook configuration endpoints extending Story 9.1 API:
    - [ ] POST `/api/webhooks` - create new webhook configuration
    - [ ] GET `/api/webhooks` - list all user webhooks with status
    - [ ] PUT `/api/webhooks/{webhook_id}` - update webhook configuration
    - [ ] DELETE `/api/webhooks/{webhook_id}` - remove webhook configuration
    - [ ] POST `/api/webhooks/{webhook_id}/test` - test webhook with sample payload
  - [ ] Create webhook configuration model with URL, secret, event subscriptions, and active status
  - [ ] Implement webhook secret generation and secure storage in user profile
  - [ ] Add webhook validation (URL format, SSL requirement, connectivity testing)

- [ ] **Event System and Payload Generation** (AC: 1, 2, 6)
  - [ ] Create event dispatcher service in `src/api/webhooks/event_dispatcher.py`
  - [ ] Implement supported event types:
    - [ ] `content.new` - new content available from ETL sources
    - [ ] `alert.triggered` - notification alerts fired by alert rules
    - [ ] `source.updated` - ETL source updates and status changes
  - [ ] Create standardized payload format: `{event: str, timestamp: str, data: {...}, signature: str}`
  - [ ] Implement event-specific data schemas for different event types
  - [ ] Add HMAC-SHA256 signature generation using webhook secret for security
  - [ ] Create payload size limits and data sanitization for large payloads

- [ ] **Webhook Delivery and Retry System** (AC: 1, 3, 4, 6)
  - [ ] Create webhook delivery service in `src/api/webhooks/delivery_service.py`
  - [ ] Implement HTTP POST delivery with proper headers (Content-Type, User-Agent, X-Webhook-Signature)
  - [ ] Create retry mechanism with exponential backoff: 30s, 5m, 30m delays
  - [ ] Add delivery status tracking (pending, delivered, failed, retry_exhausted)
  - [ ] Implement timeout handling and connection management for webhook endpoints
  - [ ] Create webhook response processing and status code handling

- [ ] **Webhook Logging and Monitoring** (AC: 4, 6)
  - [ ] Create comprehensive logging system for all webhook activities
  - [ ] Store webhook delivery logs in `data/webhooks/{user_id}/deliveries.json`
  - [ ] Implement log rotation and cleanup for webhook delivery logs
  - [ ] Create webhook analytics endpoint: GET `/api/webhooks/analytics`
  - [ ] Add webhook performance monitoring and success rate tracking
  - [ ] Create webhook health monitoring and alerting for delivery failures

- [ ] **Database Models and Storage** (AC: 1, 4)
  - [ ] Extend SQLite user database with webhook configuration tables
  - [ ] Create WebhookConfig model: id, user_id, url, secret, events, active_status, created_at, updated_at
  - [ ] Create WebhookDelivery model: id, webhook_id, event_type, payload, status, attempts, created_at
  - [ ] Implement database migrations for webhook tables
  - [ ] Add database indexes for efficient webhook queries and logging
  - [ ] Create data retention policies for webhook logs and delivery history

- [ ] **Security and Authentication** (AC: 2, 6)
  - [ ] Implement webhook secret generation using cryptographically secure random strings
  - [ ] Add HMAC-SHA256 signature verification for incoming webhook confirmations
  - [ ] Create webhook endpoint security with rate limiting and abuse prevention
  - [ ] Implement webhook URL validation (HTTPS requirement, SSL certificate validation)
  - [ ] Add webhook payload encryption for sensitive data transmission
  - [ ] Create webhook authentication headers and secure communication protocols

- [ ] **Event Integration with Existing Systems** (AC: 1)
  - [ ] Integrate webhook event triggers with ETL pipeline completion notifications
  - [ ] Connect webhook system with existing alert engine from Story 3.1
  - [ ] Create event publishers for content updates in existing data sources
  - [ ] Implement webhook integration with notification system for unified event handling
  - [ ] Add event filtering and routing logic based on user preferences
  - [ ] Create event batching mechanisms for high-frequency events

- [ ] **Testing and Quality Assurance**
  - [ ] Create comprehensive unit tests for webhook configuration and validation
  - [ ] Add integration tests for webhook delivery and retry mechanisms
  - [ ] Implement webhook endpoint testing with mock servers
  - [ ] Create performance tests for high-volume webhook delivery scenarios
  - [ ] Add security testing for webhook signature verification and payload validation
  - [ ] Create end-to-end tests for complete webhook workflows

- [ ] **Documentation and Developer Experience**
  - [ ] Create comprehensive webhook API documentation with examples
  - [ ] Add webhook setup guides and best practices documentation
  - [ ] Implement webhook troubleshooting tools and diagnostic endpoints
  - [ ] Create webhook event reference documentation with payload schemas
  - [ ] Add webhook integration examples and code snippets for popular languages
  - [ ] Create webhook monitoring dashboard integration with existing UI

## Dev Notes

### Architecture Patterns and Constraints

The webhook support system extends the REST API foundation from Story 9.1 and builds upon Megalith's existing event-driven architecture:

- **API Foundation**: Leverages FastAPI infrastructure from Story 9.1 for webhook management endpoints
- **Event System**: Integrates with existing ETL pipeline events and alert system from Story 3.1
- **User Management**: Extends existing SQLite user database with webhook configuration storage
- **Security Model**: Uses HMAC-SHA256 signatures for webhook payload verification and secure communication
- **Retry Strategy**: Implements exponential backoff with configurable retry limits and dead-letter queue handling

Key architectural constraints:
- **Prerequisite Dependencies**: Story 9.1 (REST API Foundation) must be completed for webhook management APIs
- **Performance**: Designed to handle high-volume webhook delivery with proper queuing and batching
- **Reliability**: Comprehensive retry mechanisms and delivery tracking ensure reliable event delivery
- **Security**: Webhook secrets, signature verification, and HTTPS-only endpoints ensure secure integration
- **Scalability**: Event-driven architecture supports horizontal scaling and load distribution

### Source Tree Components to Touch

```
src/api/                                    # ENHANCEMENT - Extend FastAPI application
├── webhooks/                               # NEW - Webhook system implementation
│   ├── __init__.py                        # Package initialization
│   ├── models.py                          # Pydantic models for webhook configuration and payloads
│   ├── services.py                        # Webhook business logic and event handling
│   ├── event_dispatcher.py                # Event dispatching and delivery coordination
│   ├── delivery_service.py                # HTTP delivery and retry mechanisms
│   ├── signature_verifier.py              # HMAC signature verification and security
│   ├── webhook_manager.py                 # High-level webhook management interface
│   └── event_publishers.py                # Event publishers for existing system events
├── endpoints/                             # ENHANCEMENT - Add webhook endpoints
│   ├── webhooks.py                        # Webhook CRUD operations and management
│   └── webhook_events.py                  # Webhook testing and diagnostics
├── models/                                # ENHANCEMENT - Add webhook data models
│   ├── webhook_models.py                  # WebhookConfig and WebhookDelivery Pydantic models
│   └── event_models.py                    # Event payload models and schemas
├── services/                              # ENHANCEMENT - Extend service layer
│   ├── webhook_service.py                 # Webhook configuration and management service
│   └── event_service.py                   # Event processing and routing service
├── middleware/                            # ENHANCEMENT - Add webhook-specific middleware
│   ├── webhook_auth_middleware.py         # Webhook authentication and signature verification
│   └── webhook_rate_limiting.py           # Rate limiting for webhook endpoints
└── utils/                                 # ENHANCEMENT - Add webhook utilities
    ├── signature_utils.py                 # HMAC signature generation and verification
    ├── retry_utils.py                     # Exponential backoff and retry logic
    └── event_utils.py                     # Event formatting and payload utilities

data/                                      # ENHANCEMENT - Extend data storage for webhooks
├── megalith.db                            # ENHANCEMENT - SQLite database with webhook tables
│   ├── webhooks                           # NEW - Webhook configuration storage
│   ├── webhook_deliveries                 # NEW - Delivery attempt logs and tracking
│   └── webhook_events                     # NEW - Event queue and processing logs
└── webhooks/                              # NEW - Webhook-specific data storage
    ├── {user_id}/                         # User-specific webhook data
    │   ├── deliveries.json                # Delivery attempt logs with timestamps
    │   ├── configurations.json            # Webhook configuration backups
    │   └── analytics.json                 # Usage and performance analytics
    ├── events/                            # Event queue and processing
    │   ├── pending/                       # Pending webhook deliveries
    │   ├── processing/                    # Currently processing events
    │   └── completed/                     # Completed event deliveries
    └── failed/                            # Failed delivery attempts and retry queue

src/etl/                                   # ENHANCEMENT - Add webhook event publishing
├── webhook_publisher.py                   # NEW - ETL completion event publisher
├── base_etl.py                            # ENHANCEMENT - Add webhook event triggers
└── webhook_integration/                   # NEW - ETL webhook integration utilities
    ├── __init__.py
    ├── event_mapper.py                    # Map ETL events to webhook formats
    └── payload_builder.py                 # Build webhook payloads from ETL data

src/alerts/                                # ENHANCEMENT - Add webhook integration to alert system
├── webhook_publisher.py                   # NEW - Alert event webhook publisher
├── alert_engine.py                        # ENHANCEMENT - Add webhook triggers to alert processing
└── webhook_integration/                   # NEW - Alert webhook integration
    ├── __init__.py
    ├── alert_mapper.py                    # Map alert events to webhook formats
    └── alert_payload_builder.py           # Build webhook payloads from alert data

src/web/dashboard/components/               # ENHANCEMENT - Add webhook management UI
├── webhook_management_tab.py              # NEW - Webhook configuration and management interface
├── webhook_logs_view.py                   # NEW - Webhook delivery logs and analytics dashboard
└── webhook_test_panel.py                  # NEW - Interactive webhook testing interface

Tests/api/                                  # ENHANCEMENT - Add webhook testing
├── test_webhooks.py                       # Comprehensive webhook system tests
├── test_webhook_delivery.py               # Webhook delivery and retry mechanism tests
├── test_webhook_security.py               # Webhook signature verification and security tests
└── test_webhook_integration.py            # Integration tests with ETL and alert systems
```

### Testing Standards Summary

Follow existing pytest patterns with >85% coverage target for webhook functionality. Test files should be in `Tests/api/` with comprehensive coverage of:

- **Webhook Configuration**: CRUD operations, validation rules, security checks, and user permission testing
- **Event Dispatching**: Event publishing, payload generation, signature verification, and routing logic
- **Delivery System**: HTTP delivery, retry mechanisms, error handling, and status tracking
- **Security**: Signature verification, secret management, URL validation, and abuse prevention
- **Integration**: ETL event publishing, alert system integration, and end-to-end workflows
- **Performance**: High-volume delivery testing, concurrent webhook processing, and resource usage monitoring

Use existing patterns: `test_webhooks.py`, `test_webhook_delivery.py` with proper mocking for HTTP requests and external services.

### Project Structure Notes

The webhook support system enables Megalith to become a truly event-driven platform that can integrate with external systems in real-time:

**Comprehensive Event Publishing:**
- **ETL Integration**: Automatically publishes webhook events when ETL pipelines complete, sources update, or new content becomes available across 50+ data sources
- **Alert System Integration**: Delivers real-time webhook notifications when alert rules trigger, enabling external systems to react immediately to important events
- **Content Updates**: Provides instant notifications when new intelligence data is available, supporting real-time dashboard updates and external data synchronization

**Robust Delivery Infrastructure:**
- **Exponential Backoff Retry**: Ensures reliable event delivery with intelligent retry scheduling (30s, 5m, 30m) and configurable retry limits
- **Signature-Based Security**: HMAC-SHA256 signatures provide payload integrity verification and prevent webhook spoofing attacks
- **Comprehensive Logging**: Detailed delivery logs with timestamps, retry attempts, and error messages for troubleshooting and analytics

**Developer-Friendly Management:**
- **REST API Integration**: Seamless extension of Story 9.1 API with dedicated webhook management endpoints
- **Interactive Testing**: Built-in webhook testing capabilities with sample payloads for each supported event type
- **Real-time Monitoring**: Webhook analytics and delivery status tracking integrated with existing dashboard infrastructure

**Enterprise-Ready Reliability:**
- **Queue-Based Processing**: Event queue system handles high-volume webhook delivery with proper batching and load distribution
- **Dead-Letter Handling**: Failed webhook attempts are tracked and can be manually reviewed or reprocessed
- **Performance Optimization**: Intelligent caching, connection pooling, and batch processing ensure scalable webhook delivery

**No conflicts detected** - significantly enhances Megalith's event-driven capabilities while maintaining full compatibility with existing API infrastructure and establishing the foundation for real-time integrations.

### Prerequisites

- **Story 9.1 (REST API Foundation)**: Must be completed first for webhook management APIs and authentication infrastructure
- **Story 3.1 (Backend Alert Rule Engine)**: Must be completed for alert event publishing and integration
- **Existing ETL Framework**: Integrate with existing BaseETL patterns and completion notifications
- **Base Notification System**: Leverage existing notification patterns and event handling infrastructure

### Webhook Event Specifications

**Supported Event Types and Payloads:**

```json
// Content New Event
{
  "event": "content.new",
  "timestamp": "2025-01-19T10:30:00Z",
  "data": {
    "source_id": "arxiv-rss",
    "source_type": "academic_papers",
    "content_count": 15,
    "categories": ["machine_learning", "computer_vision"],
    "sample_items": [
      {
        "id": "arxiv:2501.12345",
        "title": "Advanced Neural Architecture Search",
        "url": "https://arxiv.org/abs/2501.12345",
        "published_at": "2025-01-19T09:15:00Z"
      }
    ]
  },
  "signature": "hmac_sha256_signature"
}

// Alert Triggered Event
{
  "event": "alert.triggered",
  "timestamp": "2025-01-19T10:30:00Z",
  "data": {
    "alert_id": "user_123_alert_456",
    "alert_type": "keyword_match",
    "severity": "high",
    "title": "AI Research Alert: GPT-5 Updates",
    "description": "New papers mentioning GPT-5 found in recent arXiv updates",
    "matched_keywords": ["GPT-5", "language model"],
    "content_count": 3,
    "urgency": "immediate"
  },
  "signature": "hmac_sha256_signature"
}

// Source Updated Event
{
  "event": "source.updated",
  "timestamp": "2025-01-19T10:30:00Z",
  "data": {
    "source_id": "github-trending",
    "source_type": "repository_trends",
    "update_type": "scheduled_etl",
    "status": "success",
    "items_processed": 250,
    "new_items": 45,
    "processing_time_seconds": 127,
    "last_successful_run": "2025-01-19T10:28:00Z"
  },
  "signature": "hmac_sha256_signature"
}
```

### Integration Strategy

**Event Publisher Integration:**
- Extend existing ETL pipeline completion hooks to publish webhook events for content updates
- Integrate with alert engine to publish webhook notifications when alerts trigger
- Create event mappers that transform internal data structures into webhook-compatible payloads
- Implement event filtering and routing based on user webhook subscriptions and preferences

**Performance and Scalability:**
- Implement event queuing system with Redis or in-memory queues for high-volume event processing
- Add webhook delivery batching for multiple events to the same endpoint to reduce HTTP overhead
- Create connection pooling and keep-alive mechanisms for efficient webhook delivery
- Implement circuit breaker patterns for webhook endpoints that consistently fail

**Security and Reliability:**
- Use webhook secrets stored securely in database with proper encryption
- Implement signature verification for webhook confirmation and security validation
- Add webhook endpoint health checking and validation before enabling delivery
- Create comprehensive error handling and fallback mechanisms for delivery failures

### References

- [Source: docs/epics.md#Story-92-Webhook-Support] - Epic requirements and webhook specifications
- [Source: docs/architecture.md#Decision-Summary] - Technology choices: FastAPI, SQLite integration, event-driven architecture
- [Source: stories/9-1-rest-api-foundation.md] - Previous story: REST API foundation and authentication infrastructure
- [Source: stories/8-18-cybersecurity-developer-security-intelligence.md] - Previous story learnings: comprehensive data processing and security patterns
- [Source: docs/architecture.md#Project-Structure] - Integration with existing event systems and notification infrastructure

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

### Change Log

**Created**: 2025-11-19 - Initial story draft with comprehensive webhook support requirements including event publishing, delivery system, retry mechanisms, and security implementation