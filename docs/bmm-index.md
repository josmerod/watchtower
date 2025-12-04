# Watchtower Documentation Index

**Primary AI Retrieval Source for Claude Code and AI-Assisted Development**

**Project:** Watchtower (MEGALITH)
**Type:** Data Processing & ETL Platform
**Generated:** 2025-11-17
**Documentation Version:** 3.0 (BMM Document-Project Workflow - Exhaustive Scan)

---

## 🎯 Quick Reference

### Project Overview

- **Name:** Watchtower (also known as MEGALITH)
- **Type:** Python Monolith - Data Processing & ETL Platform
- **Language:** Python 3.10+
- **Package Manager:** UV (recommended) / pip + venv
- **Architecture Pattern:** Template Method (ETL) + Observer (Watchers) + Factory (Config)

### Key Statistics

| Metric | Value |
|--------|-------|
| **ETL Pipelines** | 20+ production domains |
| **Data Models** | 21 total (15 domain + 6 base) |
| **Data Sources** | 50+ platforms |
| **Dashboard Tabs** | 15+ interactive components |
| **Python Files** | 200+ |
| **Test Coverage Target** | ≥80% |
| **Documentation Pages** | 25+ comprehensive guides |

### Tech Stack at a Glance

| Category | Primary Technologies |
|----------|---------------------|
| **Core** | Python 3.10+, UV, Pydantic 2.11.5+ |
| **Data** | pandas 2.2.3+, polars 0.20.0+, numpy 2.2.5+ |
| **Web** | Dash 2.0+, Streamlit 1.45+, Plotly 5.0+ |
| **Scraping** | Playwright 1.51+, BeautifulSoup4 4.13+ |
| **Quality** | ruff, mypy, black, pytest |

---

## 📚 Generated Documentation (This Scan)

### Core Reference Documents

1. **[Project Overview](./project-overview.md)** ⭐ **START HERE**
   - Executive summary and architecture overview
   - Technology stack details
   - Development workflow guidance

2. **[Architecture Documentation](./architecture.md)**
   - Detailed system architecture
   - Component relationships and patterns
   - Design principles and decisions

3. **[Data Models Reference](./data-models-main.md)**
   - Complete Pydantic model documentation
   - 21 data models with field descriptions
   - Enum definitions and validations

4. **[Source Tree Analysis](./source-tree-analysis.md)**
   - Complete directory structure with annotations
   - Critical folders explained
   - Entry points and integration points

### Development Guides

5. **[Development Guide](./QUICKSTART.md)**
   - UV setup and installation
   - Local development commands
   - Common development tasks

6. **[Contributing Guide](./CONTRIBUTING.md)**
   - Code style and standards
   - PR process and review guidelines
   - Testing requirements

7. **[Configuration Guide](./technical/CONFIGURATION_GUIDE.md)**
   - Pydantic settings management
   - Environment variable configuration
   - Component-specific settings

### Deployment & Operations

8. **[Deployment Guide](./technical/DEPLOYMENT_GUIDE.md)**
   - Production deployment instructions
   - Docker and containerization
   - Environment setup

9. **[Advanced Deployment](./technical/ADVANCED_DEPLOYMENT_GUIDE.md)**
   - Scalability considerations
   - High availability configurations
   - Performance optimization

### Business & Planning

10. **[Product Requirements Document](./PRD.md)**
    - Feature specifications and requirements
    - User stories and acceptance criteria
    - Development roadmap

11. **[Epics & Features](./epics.md)**
    - Detailed feature breakdown
    - Epic 8: Intelligence Data Sources Catalog
    - Implementation status tracking

12. **[Implementation Readiness Report](./epic-8-implementation-readiness-report.md)**
    - Current implementation status
    - Technical readiness assessment
    - Risk analysis and mitigation

---

## 🔍 Existing Technical Documentation

### Architecture & Design

13. **[Architecture Overview](./technical/ARCHITECTURE_OVERVIEW.md)**
    - System architecture deep dive
    - Component interaction diagrams
    - Design patterns explanation

### Research & Analysis

14. **[Technical Research](./research-technical-2025-01-11.md)**
    - Technology research findings
    - Alternative solutions analysis
    - Technical decision documentation

15. **[Brainstorming Session](./bmm-brainstorming-session-2025-01-11.md)**
    - Feature ideation and exploration
    - Innovation opportunities
    - Strategic technical discussions

### User Documentation

16. **[FAQ](./FAQ.md)**
    - Common questions and answers
    - Troubleshooting guidance
    - User support information

17. **[Master Index](./INDEX.md)**
    - Complete documentation navigation
    - Cross-reference guide
    - Topic organization

---

## 🚀 Getting Started

### For New Developers

1. **Prerequisites**
   ```bash
   # Install UV (10-100x faster than pip)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Project Setup**
   ```bash
   # Clone and setup
   git clone <repository-url>
   cd watchtower
   uv sync --all-extras
   ```

3. **Run Development Dashboard**
   ```bash
   # Main dashboard (Dash-based)
   uv run python run_watchtower_dashboard.py
   # Available at http://localhost:7777

   # Legacy dashboard (Streamlit)
   uv run streamlit run src/web/fullstreamlit/app.py
   # Available at http://localhost:8501
   ```

4. **Run ETL Pipelines**
   ```bash
   # Run all ETL pipelines
   ./run_all_etl.sh  # Linux/Mac
   .\run_all_etl.bat # Windows

   # Run specific ETL
   uv run python src/etl/arxiv/arxiv_etl.py
   ```

### For AI-Assisted Development

**Primary AI Source:** This document (`bmm-index.md`) serves as the primary context for Claude Code and AI assistants.

**Key Context Points:**
- UV-first development environment
- Dash-based dashboard with Streamlit legacy
- Comprehensive ETL framework with 20+ domains
- Pydantic-based data validation and configuration
- File-based JSON storage architecture

**Common Development Patterns:**
- Inherit from `BaseETL` for new data sources
- Use Pydantic models for all data structures
- Follow single-callback pattern in Dash components
- Implement Manager classes for complex data handling

### For Production Deployment

1. **Health Monitoring**
   ```bash
   # Health check endpoints
   curl http://localhost:7777/health
   curl http://localhost:7777/metrics
   ```

2. **Configuration Management**
   - Use environment variables with double underscore delimiter
   - Store sensitive data in `.env` files
   - Reference configuration via `src/config/settings.py`

3. **Data Management**
   - JSON files stored in `data/` directory
   - Timestamped outputs with automatic cleanup
   - Checkpoint-based recovery for ETL processes

---

## 📊 Project Architecture Summary

### Core Components

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **ETL Framework** | Data extraction and processing | `src/etl/base.py` |
| **Dashboard System** | Interactive data visualization | `src/web/dashboard/` |
| **Data Models** | Schema validation and structure | `src/models/` |
| **Configuration** | Settings and environment management | `src/config/settings.py` |
| **Testing Suite** | Quality assurance and validation | `Tests/` |

### Data Flow Architecture

```
External Sources → ETL Pipelines → JSON Storage → Dashboard Components → User Interface
       ↓                ↓              ↓                ↓
   50+ Platforms    BaseETL Class   data/ Directory   Dash/Streamlit
   (APIs, RSS, etc.)  Template Method  Timestamped     Interactive UI
                      Pattern         Files           Components
```

### Development Workflow

1. **Local Development** → UV + Ruff + MyPy + Pytest
2. **Code Quality** → Google-style docstrings + Type annotations
3. **Testing** → Unit + Integration + E2E + Performance tests
4. **Documentation** → Auto-generated + Manual guides
5. **Deployment** → Docker + Environment configuration

---

## 🔧 Advanced Features

### ETL Framework Capabilities

- **Resumable Operations:** Checkpoint-based recovery
- **Batch Processing:** Memory-efficient data handling
- **Retry Logic:** Exponential backoff for transient failures
- **Metrics Collection:** Performance and success tracking
- **Error Handling:** Comprehensive exception hierarchy

### Dashboard Features

- **Real-time Updates:** Live data loading with caching
- **Interactive Filtering:** Dynamic content filtering
- **Mobile Responsive:** Bootstrap-based responsive design
- **Component Architecture:** Modular tab-based system
- **Error Boundaries:** Graceful degradation handling

### Configuration Management

- **Nested Settings:** Component-specific configuration
- **Environment Variables:** Double underscore delimiter support
- **Type Validation:** Full Pydantic validation
- **Auto-discovery:** Project root detection
- **Path Management:** Absolute path conversion

---

## 📈 Performance & Scalability

### Optimization Features

- **Caching Strategy:** Multi-level caching for data loading
- **Lazy Loading:** On-demand data rendering
- **Batch Processing:** Configurable batch sizes
- **JSON Storage:** Fast read operations with pandas/polars
- **Concurrent Execution:** Parallel processing where possible

### Monitoring & Health

- **Health Endpoints:** `/health` and `/metrics` APIs
- **Performance Metrics:** ETL processing times and success rates
- **Error Tracking:** Comprehensive error logging and context
- **Resource Monitoring:** Memory and CPU usage tracking

---

## 🎯 Development Standards

### Code Quality Requirements

- **Type Annotations:** 100% coverage with Python 3.10+ syntax
- **Documentation:** Google-style docstrings throughout
- **Error Handling:** Custom exception hierarchy in `src/exceptions/`
- **Testing:** Comprehensive test suite with coverage reporting
- **Linting:** Ruff for formatting and linting

### Architecture Principles

- **Template Method Pattern:** BaseETL orchestrates ETL phases
- **Factory Pattern:** Settings management with singleton behavior
- **State Pattern:** Watcher state management with JSON persistence
- **Component Pattern:** Modular dashboard architecture
- **Manager Pattern:** Centralized data handling

### Security Practices

- **Environment Variables:** Secure configuration management
- **Input Validation:** Pydantic model validation throughout
- **Path Security:** Safe file path handling
- **API Key Management:** Secure storage and environment-based access

---

**Generated:** 2025-11-17 by BMM Document-Project Workflow (Exhaustive Scan)
**Next Update:** Run `document-project` workflow again for latest changes
**AI Integration:** Use this document as primary context for Claude Code and AI assistants
