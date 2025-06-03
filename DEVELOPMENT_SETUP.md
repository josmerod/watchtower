# Watchtower Development Setup Guide

This guide explains how to set up the Watchtower project for development with the improved project structure and development workflow.

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Git
- A code editor (VS Code, PyCharm, etc.)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd watchtower
   ```

2. **Install the project in development mode:**
   ```bash
   python install_dev.py
   ```

3. **Verify installation:**
   ```bash
   python -c "from src.config.settings import get_settings; print('✅ Setup successful!')"
   ```

4. **Start the Streamlit dashboard:**
   ```bash
   streamlit run src/web/fullstreamlit/app.py
   ```

## 🏗️ Project Architecture

### Package Structure
```
watchtower/
├── src/                    # Main source code (installable package)
│   ├── config/            # Configuration management
│   ├── etl/               # ETL pipelines
│   ├── models/            # Pydantic data models
│   ├── utils/             # Shared utilities
│   ├── watchers/          # Monitoring components
│   └── web/               # Web interfaces
├── data/                  # Data storage
├── logs/                  # Application logs
├── tests/                 # Test suite
├── docs/                  # Documentation
├── pyproject.toml         # Project metadata and dependencies
├── setup.py               # Package installation script
└── requirements*.txt      # Dependency specifications
```

### Key Architectural Patterns

1. **ETL Framework Pattern** (`src/etl/base.py`)
   - Template method pattern with `BaseETL`
   - Comprehensive metrics and checkpointing
   - Error handling and retry mechanisms

2. **Pydantic Configuration** (`src/config/`)
   - Environment-based configuration
   - Type validation and defaults
   - Nested configuration models

3. **Streamlit Components** (`src/web/fullstreamlit/`)
   - Tab-based modular architecture
   - Ultra-optimized data services
   - Error boundaries and caching

4. **Watcher Pattern** (`src/watchers/`)
   - State persistence and event tracking
   - Configurable monitoring intervals
   - Change detection algorithms

## 🛠️ Development Workflow

### Installing Dependencies

The project supports multiple dependency profiles:

```bash
# Install all dependencies
pip install -e ".[all]"

# Install specific profiles
pip install -e ".[dev]"      # Development tools
pip install -e ".[ml]"       # Machine learning libraries  
pip install -e ".[web]"      # Web development tools
```

### Code Quality Tools

The project uses several code quality tools configured in `pyproject.toml`:

- **Ruff**: Linting and formatting
- **mypy**: Type checking
- **pytest**: Testing framework

Run quality checks:
```bash
# Formatting and linting
ruff format .
ruff check .

# Type checking
mypy src/

# Run tests
pytest
```

### Environment Configuration

Use environment variables or `.env` files for configuration:

```bash
# .env file example
WATCHTOWER_ENVIRONMENT=development
WATCHTOWER_DEBUG=true
WATCHTOWER_DATABASE__URL=sqlite:///dev.db
WATCHTOWER_LOGGING__LEVEL=DEBUG
```

## 📦 Import Structure

### Before (Problematic)
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config.settings import get_settings
```

### After (Clean)
```python
from src.config.settings import get_settings
```

The development installation makes the `src/` package importable directly.

## 🔧 Development Scripts

### Import Cleanup
Remove legacy `sys.path.insert` statements:
```bash
python fix_imports.py
```

### Development Installation
Install package in editable mode:
```bash
python install_dev.py
```

### Running ETL Pipelines
```bash
# Run specific ETL
python -m src.etl.arxiv.arxiv_etl

# Run all ETLs
python run_all_etl.py
```

### Starting Services
```bash
# Streamlit dashboard
streamlit run src/web/fullstreamlit/app.py

# API server (if implemented)
python -m src.api.main
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/unit/test_config.py
```

### Test Structure
```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── etl/           # ETL-specific tests
└── web/           # Web component tests
```

## 📊 Performance Optimization

### Streamlit Optimization
- Use `@st.cache_data` for expensive operations
- Implement TTL-based caching for data loading
- Component-based rendering with error boundaries

### ETL Optimization
- Batch processing with configurable sizes
- Checkpointing for long-running processes
- Parallel processing for independent tasks

### Data Storage
- JSON files for structured data
- CSV exports for analysis
- Incremental data loading

## 🐛 Debugging

### Common Issues

1. **Import Errors**
   - Ensure package is installed: `python install_dev.py`
   - Check for remaining `sys.path.insert` statements

2. **Configuration Issues**
   - Verify environment variables
   - Check `.env` file format
   - Validate configuration with: `python -c "from src.config.settings import get_settings; print(get_settings())"`

3. **Data Loading Errors**
   - Check data directory permissions
   - Verify file paths in configuration
   - Review logs in `logs/` directory

### Debug Mode
Enable debug logging:
```bash
export WATCHTOWER_DEBUG=true
export WATCHTOWER_LOGGING__LEVEL=DEBUG
```

## 🚀 Deployment

### Development Deployment
```bash
# Start all services
streamlit run src/web/fullstreamlit/app.py --server.port 8501
```

### Production Considerations
- Set `WATCHTOWER_ENVIRONMENT=production`
- Configure proper database connections
- Set up proper logging and monitoring
- Use process managers (systemd, supervisor)

## 📝 Adding New Components

### ETL Pipeline
1. Create new file in `src/etl/domain/`
2. Inherit from `BaseETL`
3. Implement `extract()`, `transform()`, `load()` methods
4. Add to run scripts

### Streamlit Component
1. Create new file in `src/web/fullstreamlit/components/`
2. Follow the tab pattern
3. Add to `__init__.py`
4. Import in main app

### Data Model
1. Create Pydantic model in `src/models/`
2. Include validation and enums
3. Add to model exports

## 🤝 Contributing

1. Follow the established patterns
2. Add tests for new functionality
3. Update documentation
4. Run quality checks before committing
5. Use descriptive commit messages

## 📚 Additional Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)

For questions or issues, please check the existing documentation or create an issue in the project repository. 