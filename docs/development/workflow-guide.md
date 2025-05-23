# Development Workflow Guide

A comprehensive guide for contributing to the Watchtower project, covering development practices, coding standards, and collaboration workflows.

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Coding Standards](#coding-standards)
4. [Testing Workflow](#testing-workflow)
5. [Git Workflow](#git-workflow)
6. [Code Review Process](#code-review-process)
7. [Release Process](#release-process)

---

## Getting Started

### Prerequisites for Contributors

```bash
# Required tools
Python 3.10+
Git
Poetry (recommended) or pip
VS Code or similar IDE

# Recommended VS Code extensions
ms-python.python
ms-python.ruff
ms-python.pylint
ms-toolsai.jupyter
```

### Initial Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/watchtower.git
cd watchtower

# Setup development environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate.bat  # Windows

# Install development dependencies
pip install -r requirements-dev.txt
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run initial tests to verify setup
python -m pytest Tests/unit/ -v
```

---

## Development Environment

### Recommended IDE Configuration

**VS Code Settings (`.vscode/settings.json`)**:
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.linting.pylintEnabled": false,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["Tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

### Environment Variables

Create a `.env.dev` file for development:

```bash
# Development environment
ENVIRONMENT=development
DEBUG=true

# Logging configuration
LOGGING__LEVEL=DEBUG
LOGGING__FILE_ENABLED=true

# Database configuration
DATABASE__URL=sqlite:///watchtower_dev.db
DATABASE__ECHO=true

# ETL configuration
ETL__BATCH_SIZE=100  # Smaller batches for testing
ETL__MAX_WORKERS=2

# Scraping configuration
SCRAPING__TIMEOUT=10
SCRAPING__MAX_RETRIES=2
SCRAPING__CONCURRENT_LIMIT=5
```

### Development Scripts

```bash
# Run development server
./start_dev_server.sh

# Run all tests
./run_tests.sh

# Format code
./format_code.sh

# Type checking
./check_types.sh
```

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with the following specific guidelines:

#### 1. Imports
```python
# Standard library imports first
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# Third-party imports
import pandas as pd
from pydantic import BaseModel

# Local imports
from src.config.settings import get_settings
from src.utils.logging import get_logger
```

#### 2. Type Hints
```python
# Always include type hints for function parameters and returns
def process_data(
    input_data: List[Dict[str, Any]], 
    batch_size: int = 1000
) -> List[Dict[str, Any]]:
    """Process data in batches.
    
    Args:
        input_data: Raw data to process
        batch_size: Number of items per batch
        
    Returns:
        Processed data list
    """
    # Implementation
    pass

# Use type aliases for complex types
DataDict = Dict[str, Union[str, int, float, bool]]
ProcessedData = List[DataDict]
```

#### 3. Docstrings
Use **Google-style docstrings**:

```python
def extract_content(url: str, timeout: int = 30) -> str:
    """Extract content from a web page.
    
    Args:
        url: The URL to fetch content from
        timeout: Request timeout in seconds
        
    Returns:
        The extracted HTML content
        
    Raises:
        ExtractionError: If the content cannot be extracted
        TimeoutError: If the request times out
        
    Example:
        >>> content = extract_content("https://example.com")
        >>> len(content) > 0
        True
    """
    # Implementation
    pass
```

#### 4. Error Handling
```python
# Use specific exceptions with context
from src.exceptions.etl import ExtractionError

def risky_operation(data: Any) -> Any:
    try:
        result = process_data(data)
        return result
    except ValueError as e:
        raise ExtractionError(
            message=f"Failed to process data: {e}",
            error_code="DATA_PROCESSING_FAILED",
            context={"input_type": type(data).__name__}
        ) from e
```

#### 5. Configuration Usage
```python
# Always use configuration system
from src.config.settings import get_settings

def setup_component():
    settings = get_settings()
    batch_size = settings.etl.batch_size
    max_workers = settings.etl.max_workers
    # Use settings throughout the function
```

### Code Organization

#### 1. File Structure
```python
# Standard file structure
"""Module docstring explaining purpose."""

# Imports section
import ...

# Constants (if any)
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Type aliases (if any)
DataType = Dict[str, Any]

# Classes
class ComponentName:
    """Class docstring."""
    pass

# Functions
def utility_function():
    """Function docstring."""
    pass

# Main execution (if applicable)
if __name__ == "__main__":
    main()
```

#### 2. Class Design
```python
class DataProcessor:
    """Processes data with configurable options.
    
    Attributes:
        batch_size: Number of items to process per batch
        logger: Logger instance for this processor
    """
    
    def __init__(self, batch_size: int = 1000):
        """Initialize the processor.
        
        Args:
            batch_size: Items per batch
        """
        self.batch_size = batch_size
        self.logger = get_logger(self.__class__.__name__)
        self._setup()
    
    def _setup(self) -> None:
        """Private setup method."""
        # Internal setup logic
        pass
    
    def process(self, data: List[Any]) -> List[Any]:
        """Public interface method."""
        # Implementation
        pass
```

---

## Testing Workflow

### Test Organization

```
Tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests
├── etl/           # ETL-specific tests
├── data/          # Test data files
└── fixtures/      # Pytest fixtures
```

### Writing Tests

#### 1. Unit Tests
```python
# test_data_processor.py
import pytest
from unittest.mock import Mock, patch

from src.components.data_processor import DataProcessor
from src.exceptions.etl import ProcessingError

class TestDataProcessor:
    """Test suite for DataProcessor."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.processor = DataProcessor(batch_size=10)
    
    def test_process_valid_data(self):
        """Test processing with valid data."""
        # Arrange
        input_data = [{"id": i, "value": f"item_{i}"} for i in range(5)]
        
        # Act
        result = self.processor.process(input_data)
        
        # Assert
        assert len(result) == 5
        assert all("processed" in item for item in result)
    
    @pytest.mark.parametrize("invalid_data", [
        None,
        [],
        [{"missing_id": "value"}]
    ])
    def test_process_invalid_data(self, invalid_data):
        """Test processing with invalid data."""
        with pytest.raises(ProcessingError):
            self.processor.process(invalid_data)
    
    def test_process_with_mocked_dependency(self):
        """Test with mocked external dependency."""
        with patch('src.components.data_processor.external_api') as mock_api:
            mock_api.return_value = {"status": "success"}
            
            result = self.processor.process([{"id": 1}])
            
            assert result is not None
            mock_api.assert_called_once()
```

#### 2. Integration Tests
```python
# test_etl_integration.py
import pytest
import tempfile
from pathlib import Path

from src.etl.news.hackernews_etl import HackerNewsETL

class TestHackerNewsETLIntegration:
    """Integration tests for HackerNews ETL."""
    
    def test_full_etl_pipeline(self):
        """Test complete ETL pipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup
            etl = HackerNewsETL(
                name="test_hackernews",
                output_dir=Path(temp_dir)
            )
            
            # Execute
            metrics = etl.run()
            
            # Verify
            assert metrics.is_successful
            assert metrics.records_extracted > 0
            assert metrics.records_loaded > 0
            assert (Path(temp_dir) / "hackernews.json").exists()
```

#### 3. Test Fixtures
```python
# conftest.py
import pytest
import tempfile
from pathlib import Path

from src.config.settings import Settings

@pytest.fixture
def temp_directory():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def test_settings():
    """Provide test configuration."""
    return Settings(
        environment="testing",
        debug=True,
        database__url="sqlite:///:memory:",
        logging__level="DEBUG"
    )

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return [
        {"id": 1, "title": "Test Article 1", "score": 100},
        {"id": 2, "title": "Test Article 2", "score": 200},
    ]
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest Tests/unit/
pytest Tests/integration/
pytest Tests/etl/

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest Tests/unit/test_data_processor.py -v

# Run tests matching pattern
pytest -k "test_process" -v

# Run tests with markers
pytest -m "slow" -v
pytest -m "not slow" -v
```

### Test Markers

```python
# Mark slow tests
@pytest.mark.slow
def test_large_dataset_processing():
    """Test that takes significant time."""
    pass

# Mark integration tests
@pytest.mark.integration
def test_database_integration():
    """Test requiring database."""
    pass

# Mark tests requiring network
@pytest.mark.network
def test_external_api():
    """Test requiring internet connection."""
    pass
```

---

## Git Workflow

### Branch Strategy

```
main                 # Production-ready code
├── develop          # Integration branch
├── feature/xxx      # Feature development
├── bugfix/xxx       # Bug fixes
├── hotfix/xxx       # Critical production fixes
└── release/x.x.x    # Release preparation
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(etl): add HackerNews RSS parsing

- Implement RSS feed parsing for HackerNews
- Add data validation with Pydantic models
- Include comprehensive error handling

Closes #123

fix(watcher): handle connection timeouts gracefully

- Add retry logic for network failures
- Increase default timeout to 30 seconds
- Log connection errors with context

Fixes #456

docs(api): update ETL framework documentation

- Add comprehensive API reference
- Include usage examples
- Update architecture diagrams
```

### Development Workflow

#### 1. Feature Development
```bash
# Start from develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/new-etl-source

# Make changes
# ... development work ...

# Commit changes
git add .
git commit -m "feat(etl): add new ETL source support"

# Push to remote
git push origin feature/new-etl-source

# Create pull request
# ... via GitHub/GitLab interface ...
```

#### 2. Bug Fixes
```bash
# Create bugfix branch from develop
git checkout develop
git checkout -b bugfix/fix-watcher-timeout

# Fix the issue
# ... fix implementation ...

# Test the fix
pytest Tests/ -v

# Commit and push
git commit -m "fix(watcher): handle connection timeouts"
git push origin bugfix/fix-watcher-timeout
```

#### 3. Hotfixes
```bash
# Create hotfix from main
git checkout main
git checkout -b hotfix/critical-security-fix

# Apply critical fix
# ... fix implementation ...

# Test thoroughly
pytest Tests/ -v

# Commit and push
git commit -m "fix(security): patch critical vulnerability"
git push origin hotfix/critical-security-fix

# Merge to both main and develop
```

---

## Code Review Process

### Pull Request Guidelines

#### 1. PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## Related Issues
Closes #123
```

#### 2. Review Checklist

**Code Quality**:
- [ ] Follows coding standards
- [ ] Proper error handling
- [ ] Appropriate logging
- [ ] Type hints included
- [ ] Docstrings present

**Testing**:
- [ ] Adequate test coverage
- [ ] Tests are meaningful
- [ ] Edge cases covered
- [ ] Performance considerations

**Documentation**:
- [ ] API documentation updated
- [ ] README changes if needed
- [ ] Changelog updated

### Review Process

1. **Self-Review**: Author reviews their own code first
2. **Automated Checks**: CI/CD pipeline runs tests and linting
3. **Peer Review**: At least one team member reviews
4. **Approval**: Required approvals before merge
5. **Merge**: Squash and merge to develop branch

---

## Release Process

### Version Management

We use **Semantic Versioning** (SemVer):
- `MAJOR.MINOR.PATCH`
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Release Steps

#### 1. Prepare Release
```bash
# Create release branch
git checkout develop
git checkout -b release/1.2.0

# Update version numbers
# - pyproject.toml
# - src/__init__.py
# - docs/

# Update CHANGELOG.md
# Run full test suite
pytest Tests/ -v --cov=src

# Commit version updates
git commit -m "chore(release): bump version to 1.2.0"
```

#### 2. Create Release
```bash
# Merge to main
git checkout main
git merge release/1.2.0

# Tag release
git tag -a v1.2.0 -m "Release version 1.2.0"

# Push to remote
git push origin main
git push origin v1.2.0

# Merge back to develop
git checkout develop
git merge main
```

#### 3. Post-Release
```bash
# Create GitHub release
# Upload distribution packages
# Update documentation site
# Announce release
```

### Changelog Format

```markdown
# Changelog

## [1.2.0] - 2025-01-23

### Added
- New ETL source for Reddit data
- Performance monitoring dashboard
- Configuration validation

### Changed
- Improved error handling in watchers
- Updated dependencies

### Fixed
- Memory leak in batch processing
- Timezone handling in timestamps

### Deprecated
- Old configuration format (will be removed in 2.0.0)

### Security
- Updated dependencies with security patches
```

---

## Best Practices Summary

### Development
- **Start Small**: Implement features incrementally
- **Test Early**: Write tests alongside code
- **Document Everything**: Code, APIs, and decisions
- **Review Thoroughly**: Use peer reviews effectively

### Code Quality
- **Type Safety**: Use type hints consistently
- **Error Handling**: Handle errors gracefully with context
- **Logging**: Add appropriate logging for debugging
- **Performance**: Consider performance implications

### Collaboration
- **Clear Communication**: Use descriptive commit messages and PR descriptions
- **Incremental Changes**: Keep PRs focused and reviewable
- **Documentation**: Keep documentation updated with changes
- **Testing**: Ensure adequate test coverage

This workflow guide ensures consistent, high-quality contributions to the Watchtower project while maintaining code quality and team collaboration. 