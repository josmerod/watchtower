# Story 9.1: REST API Foundation

Status: drafted

## Story

As a **developer**,
I want **a REST API to access Megalith data programmatically**,
So that **I can build integrations and external tools**.

## Acceptance Criteria

1. **Given** API is deployed and authentication system is available (Prerequisite: Story 5.1)
   **When** I make authenticated requests with valid API key or OAuth token
   **Then** I can access endpoints: `/api/sources`, `/api/content/{domain}`, `/api/user/preferences`, `/api/alerts`

2. **And** all endpoints require authentication (API keys or OAuth) with proper validation and error handling

3. **And** responses are JSON with consistent structure, proper HTTP status codes, and standardized error responses

4. **And** rate limiting is enforced (100 requests/hour per user) with appropriate HTTP headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)

5. **And** API documentation is available at `/api/docs` (OpenAPI/Swagger) with interactive testing capabilities

6. **And** API endpoints follow RESTful conventions with proper HTTP methods (GET, POST, PUT, DELETE) and resource naming

## Tasks / Subtasks

- [ ] **API Framework Setup and Configuration** (AC: 1, 2, 3, 4, 5, 6)
  - [ ] Create FastAPI application structure in `src/api/` directory
  - [ ] Set up Uvicorn ASGI server configuration for production deployment
  - [ ] Configure CORS middleware for cross-origin requests with security policies
  - [ ] Implement structured logging with request/response tracking and performance monitoring
  - [ ] Set up environment-based configuration using Pydantic Settings for API-specific settings

- [ ] **Authentication and Authorization System** (AC: 1, 2)
  - [ ] Create API key authentication middleware in `src/api/auth/api_key_auth.py`
  - [ ] Implement OAuth2 token authentication with JWT tokens in `src/api/auth/oauth_auth.py`
  - [ ] Create API key management endpoints: generate, revoke, list, and refresh API keys
  - [ ] Integrate with existing user authentication system from Story 5.1 (SQLite user database)
  - [ ] Implement user permission system with role-based access control for different endpoint categories

- [ ] **Core API Endpoints Implementation** (AC: 1, 3, 6)
  - [ ] Create `src/api/endpoints/sources.py` with source listing and filtering endpoints
    - [ ] GET `/api/sources` - list all available data sources with metadata
    - [ ] GET `/api/sources/{source_id}` - get specific source details and status
    - [ ] GET `/api/sources?category={category}` - filter sources by category
  - [ ] Create `src/api/endpoints/content.py` with content access endpoints
    - [ ] GET `/api/content/{domain}?limit=50&offset=0` - get paginated content for domain
    - [ ] GET `/api/content/search?q={query}` - search across all content domains
    - [ ] GET `/api/content/{domain}/latest` - get latest updates for specific domain
  - [ ] Create `src/api/endpoints/users.py` with user preference management endpoints
    - [ ] GET `/api/user/preferences` - retrieve user preferences and settings
    - [ ] PUT `/api/user/preferences` - update user preferences with validation
    - [ ] GET `/api/user/profile` - get user profile information and API key details
  - [ ] Create `src/api/endpoints/alerts.py` with alert management endpoints
    - [ ] GET `/api/alerts` - get user's alert history with pagination and filtering
    - [ ] GET `/api/alerts/{alert_id}` - get specific alert details
    - [ ] POST `/api/alerts/{alert_id}/acknowledge` - acknowledge alert receipt

- [ ] **Rate Limiting and Security Implementation** (AC: 4)
  - [ ] Implement Flask-Limiter (or FastAPI equivalent) for rate limiting per user
  - [ ] Create rate limiting configuration with different tiers for different endpoint types
  - [ ] Add rate limiting headers to all API responses (X-RateLimit-* headers)
  - [ ] Implement Redis or in-memory rate limiting storage for distributed deployments
  - [ ] Create rate limiting bypass mechanism for system administrators and internal services
  - [ ] Add IP-based rate limiting as additional security layer for anonymous endpoints

- [ ] **API Documentation and Developer Experience** (AC: 5, 6)
  - [ ] Set up OpenAPI/Swagger UI at `/api/docs` with interactive API testing
  - [ ] Configure FastAPI automatic OpenAPI schema generation with proper documentation
  - [ ] Create comprehensive API documentation with examples for each endpoint
  - [ ] Implement API versioning strategy (e.g., `/api/v1/` preparation for future changes)
  - [ ] Add API health check endpoint at `/api/health` with system status and dependencies
  - [ ] Create API metrics endpoint at `/api/metrics` for monitoring and analytics

- [ ] **Data Models and Validation** (AC: 3, 6)
  - [ ] Create Pydantic models in `src/api/models/` for all request/response objects
    - [ ] `SourceModel` - source data representation with validation
    - [ ] `ContentModel` - content item model with domain-specific fields
    - [ ] `UserPreferencesModel` - user preferences with validation rules
    - [ ] `AlertModel` - alert data model with status and timestamps
    - [ ] `ErrorResponseModel` - standardized error response format
  - [ ] Implement request validation using Pydantic models with proper error messages
  - [ ] Create response serialization with consistent JSON structure and field naming
  - [ ] Add data transformation utilities for converting internal data formats to API responses

- [ ] **Error Handling and HTTP Status Codes** (AC: 3, 6)
  - [ ] Implement standardized error response format with error codes and messages
  - [ ] Create custom exception handlers for different error types (validation, authentication, etc.)
  - [ ] Add proper HTTP status codes for different scenarios (200, 201, 400, 401, 403, 404, 429, 500)
  - [ ] Implement request validation error responses with detailed field-level error information
  - [ ] Create error logging system for monitoring API issues and debugging
  - [ ] Add graceful error degradation for dependent service failures

- [ ] **Performance Optimization and Caching** (AC: 3, 4)
  - [ ] Implement response caching for frequently accessed data (sources, user preferences)
  - [ ] Add database query optimization with proper indexing and connection pooling
  - [ ] Create pagination helpers for large data sets with consistent cursor-based pagination
  - [ ] Implement compression for API responses using gzip middleware
  - [ ] Add request timeout handling and circuit breaker patterns for external dependencies
  - [ ] Monitor API performance metrics and implement automatic performance regression detection

- [ ] **Testing Strategy Implementation**
  - [ ] Create unit tests for all API endpoints using FastAPI TestClient
  - [ ] Add integration tests for authentication flow and rate limiting functionality
  - [ ] Implement API contract testing with OpenAPI schema validation
  - [ ] Create performance tests for rate limiting and high-load scenarios
  - [ ] Add security testing for authentication bypass and injection vulnerabilities
  - [ ] Create end-to-end tests for complete API workflows with real data

- [ ] **Integration with Existing Systems**
  - [ ] Connect API to existing ETL data storage in `data/` directory structure
  - [ ] Integrate with existing dashboard user management and preferences system
  - [ ] Create data access layer that uses existing data models and services
  - [ ] Implement proper separation between API layer and existing dashboard functionality
  - [ ] Add API usage tracking and analytics integration with existing monitoring systems

## Dev Notes

### Architecture Patterns and Constraints

The REST API foundation leverages the established architecture decisions from the architecture document [Source: docs/architecture.md#Decision-Summary]:

- **Framework**: FastAPI 0.110.x as chosen in the architecture decision table for Epic 9
- **Server**: Uvicorn 0.27.x as the ASGI server for production deployment
- **Authentication**: Integration with existing Flask-Login system from Story 5.1 for user management
- **Data Storage**: Leverage existing SQLite database for users and file-based JSON for content sources
- **Validation**: Use existing Pydantic 2.x setup for request/response models and validation
- **Configuration**: Extend existing Pydantic Settings for API-specific configuration

Key architectural constraints:
- **Prerequisite Dependencies**: Story 5.1 (authentication system) must be completed before this API implementation
- **Performance Target**: Support 10-20 users with 1-3 concurrent API usage as per architectural goals
- **Security**: API keys stored securely in user database with proper encryption and rotation policies
- **Scalability**: Design for horizontal scaling potential while maintaining simplicity for current scale
- **Integration**: Seamless integration with existing 50+ ETL pipelines and data structures without disruption

### Source Tree Components to Touch

```
src/api/                                    # NEW - FastAPI application structure
├── __init__.py                            # Package initialization
├── main.py                                # FastAPI application factory and configuration
├── dependencies.py                        # FastAPI dependencies (auth, rate limiting, etc.)
├── middleware/                            # Custom middleware for authentication and logging
│   ├── __init__.py
│   ├── auth_middleware.py                 # Authentication and authorization middleware
│   ├── rate_limit_middleware.py           # Rate limiting enforcement
│   └── logging_middleware.py              # Request/response logging
├── auth/                                  # Authentication and authorization
│   ├── __init__.py
│   ├── api_key_auth.py                    # API key authentication implementation
│   ├── oauth_auth.py                      # OAuth2 token authentication
│   └── permissions.py                     # Role-based access control
├── endpoints/                             # API endpoint implementations
│   ├── __init__.py
│   ├── sources.py                         # Source listing and management endpoints
│   ├── content.py                         # Content access and search endpoints
│   ├── users.py                           # User preferences and profile endpoints
│   ├── alerts.py                          # Alert management and history endpoints
│   └── health.py                          # Health check and metrics endpoints
├── models/                                # Pydantic models for request/response validation
│   ├── __init__.py
│   ├── base_models.py                     # Base response and error models
│   ├── source_models.py                   # Source-related data models
│   ├── content_models.py                  # Content-related data models
│   ├── user_models.py                     # User and preference models
│   └── alert_models.py                    # Alert and notification models
├── services/                              # Business logic and data access layer
│   ├── __init__.py
│   ├── source_service.py                  # Source data access and business logic
│   ├── content_service.py                 # Content retrieval and filtering logic
│   ├── user_service.py                    # User preference and profile management
│   └── alert_service.py                   # Alert retrieval and management logic
├── utils/                                 # Utility functions and helpers
│   ├── __init__.py
│   ├── pagination.py                      # Pagination helpers and utilities
│   ├── cache.py                           # Caching utilities and decorators
│   └── response_helpers.py                # Response formatting and error handling
└── config/                                # API-specific configuration
    ├── __init__.py
    ├── settings.py                        # API configuration using Pydantic Settings
    └── logging_config.py                  # Logging configuration for API requests

data/                                      # ENHANCEMENT - Extend existing data structure
├── megalith.db                            # EXISTING - SQLite database (ENHANCE for API keys)
│   ├── api_keys                           # NEW - API key storage and management
│   ├── api_usage                          # NEW - API usage tracking and rate limiting
│   └── api_sessions                       # NEW - API session management
└── api/                                   # NEW - API-specific data storage
    ├── rate_limits/                       # Rate limiting data and counters
    ├── api_logs/                          # API request/response logs
    └── analytics/                         # API usage analytics and metrics

Tests/api/                                  # NEW - Comprehensive API testing suite
├── __init__.py
├── conftest.py                            # Pytest configuration and fixtures for API testing
├── test_auth.py                           # Authentication and authorization tests
├── test_endpoints.py                      # Endpoint functionality tests
├── test_rate_limiting.py                  # Rate limiting enforcement tests
├── test_models.py                         # Pydantic model validation tests
├── test_integration.py                    # Integration tests with real data
└── test_performance.py                    # Performance and load testing

src/web/dashboard/                         # ENHANCEMENT - API integration with dashboard
├── components/api_management_tab.py       # NEW - API key management interface
├── components/api_usage_dashboard.py      # NEW - API usage monitoring and analytics
└── health_monitor.py                      # ENHANCEMENT - Include API health monitoring
```

### Testing Standards Summary

Follow existing pytest patterns with >85% coverage target for the REST API. Test files should be in `Tests/api/` with comprehensive coverage of:

- **Authentication Flow**: API key validation, OAuth token handling, permission checking, and security vulnerability testing
- **Endpoint Functionality**: All CRUD operations, validation rules, error handling, and response formatting
- **Rate Limiting**: Per-user limits, header verification, bypass mechanisms, and distributed rate limiting
- **Performance**: Load testing with concurrent users, response time validation, and memory usage monitoring
- **Integration**: End-to-end workflows with real ETL data, user management integration, and dashboard compatibility
- **Security**: SQL injection prevention, XSS protection, authentication bypass testing, and input validation

Use existing patterns: `test_main.py`, `test_auth.py`, `test_endpoints.py` with proper mocking for external dependencies and database transactions.

### Project Structure Notes

The REST API foundation represents a critical infrastructure enhancement that enables Megalith's transition from a single-user dashboard to a multi-platform ecosystem:

**API-First Architecture Implementation:**
- FastAPI provides automatic OpenAPI documentation, interactive testing, and modern async capabilities with excellent developer experience
- Uvicorn ASGI server ensures production-ready performance with proper handling of concurrent requests and WebSocket support for future real-time features
- Comprehensive authentication system supporting both API keys for simple integrations and OAuth2 for complex applications with proper token management and refresh workflows

**Comprehensive Endpoint Coverage:**
- Source management endpoints provide access to Megalith's 50+ data sources with metadata, status monitoring, and category-based filtering for integration flexibility
- Content access endpoints enable programmatic retrieval of aggregated intelligence with pagination, search capabilities, and domain-specific filtering for custom applications
- User management endpoints allow external applications to manage preferences, profiles, and settings while maintaining security and privacy controls
- Alert management endpoints provide access to Megalith's intelligent notification system with history tracking, acknowledgment workflows, and filtering capabilities

**Enterprise-Ready Security and Performance:**
- Rate limiting prevents abuse while ensuring fair usage with configurable limits per user, proper HTTP headers, and bypass mechanisms for administrative access
- Comprehensive error handling with standardized responses, proper HTTP status codes, detailed validation errors, and graceful degradation for service dependencies
- Performance optimization through intelligent caching, connection pooling, response compression, and database query optimization for scalable operations

**Developer Experience and Documentation:**
- Interactive API documentation with Swagger UI enables developers to explore endpoints, test functionality, and understand request/response formats without additional tools
- Comprehensive testing strategy with unit, integration, performance, and security tests ensures reliability and maintainability while supporting continuous deployment practices

**No conflicts detected** - this API foundation significantly extends Megalith's capabilities while maintaining full compatibility with existing architecture and establishing the foundation for subsequent Epic 9 stories.

### Prerequisites

- **Story 5.1 (User Authentication System)**: Must be completed first for user management, SQLite database, and authentication infrastructure
- **Existing development environment**: Leverage current development tools, repositories, and deployment infrastructure
- **BaseETL framework**: Integrate with existing 50+ ETL pipelines and data storage patterns without disruption
- **Dashboard system**: Maintain compatibility with existing Dash-based dashboard and user experience

### API Integration Strategy

**Authentication Integration:**
- Extend existing SQLite user database with API key management tables and usage tracking
- Leverage existing Flask-Login session management for OAuth token validation and user authentication
- Implement proper API key encryption, rotation policies, and revocation mechanisms using established security patterns

**Data Access Integration:**
- Create service layer that interfaces with existing file-based JSON storage in `data/` directory structure
- Maintain compatibility with existing data models and ETL output formats while providing API-friendly access patterns
- Implement caching strategies that work with existing data update frequencies and dashboard performance requirements

**Monitoring and Integration:**
- Extend existing health monitoring system to include API endpoints, response times, and error rates
- Integrate API usage analytics with existing monitoring infrastructure for comprehensive system visibility
- Ensure API service follows existing deployment patterns and containerization strategies used by the main dashboard

### References

- [Source: docs/epics.md#Story-91-REST-API-Foundation] - Epic requirements and technical specifications
- [Source: docs/architecture.md#Decision-Summary] - Technology choices: FastAPI, Uvicorn, SQLite integration, authentication patterns
- [Source: docs/architecture.md#Project-Structure] - Integration with existing project structure and data storage patterns
- [Source: stories/8-18-cybersecurity-developer-security-intelligence.md] - Previous story learnings: comprehensive intelligence system patterns and data access strategies

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

### Change Log

**Created**: 2025-11-19 - Initial story draft with comprehensive REST API foundation requirements including FastAPI implementation, authentication system, rate limiting, and developer documentation
