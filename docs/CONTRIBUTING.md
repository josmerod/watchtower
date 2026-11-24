# Contributing to Watchtower

Thank you for your interest in contributing to Watchtower! This guide will help you get started with contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Submitting Changes](#submitting-changes)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

**Core Principles**:
- Be respectful and inclusive
- Welcome newcomers and be patient with questions
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- UV package manager
- Basic knowledge of Python, ETL concepts, and web scraping

### Development Setup

1. **Fork the Repository**

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/watchtower.git
cd watchtower
```

2. **Set Up Development Environment**

```bash
# Install UV (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/macOS
# or
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install dependencies (includes the dev tools: ruff, pytest, mypy, pre-commit)
uv sync

# Install Playwright browsers
uv run playwright install
```

3. **Install the Pre-commit Hooks** (mandatory)

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

Both hook types are required. The commit stage runs the basic `pre-commit-hooks` (whitespace, file endings, syntax checks), ruff (lint and format), codespell, shellcheck and detect-secrets; the push stage runs the full test suite, which takes about 8 minutes. Over SSH, GitHub can drop the idle connection before the hook ends and the push then fails after a green run; keep the session alive with `git config --local core.sshCommand "ssh -o ServerAliveInterval=30"`, or push over HTTPS.

4. **Create a Branch**

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/issue-number-description
```

## Development Workflow

### Branch Naming

Branch off `main` with one of these prefixes:

- `feat/feature-name` - New features
- `fix/issue-number-description` - Bug fixes
- `chore/description` - Maintenance tasks
- `docs/description` - Documentation updates

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

**Examples**:

```bash
feat(etl): add GitHub trending repositories ETL

Implements a new ETL pipeline for fetching trending GitHub repositories
with filtering by language and time period.

Closes #123
```

```bash
fix(watchers): resolve state persistence issue

Fixed a bug where watcher state was not properly persisted when
encountering network errors.

Fixes #456
```

## Code Standards

### Python Style

We follow PEP 8 with enforcement through Ruff.

**Key Guidelines**:
- Maximum line length: 210 characters (Ruff is the source of truth for lint and format)
- Use 4 spaces for indentation (no tabs)
- Use snake_case for functions and variables
- Use PascalCase for classes
- Use UPPER_CASE for constants

### Type Hints

All functions must include comprehensive type hints, using the modern built-in generics (`list[...]`, `dict[...]`) and `X | None` instead of the `typing` equivalents:

```python
from typing import Any

def process_data(
    items: list[dict[str, Any]],
    filter_key: str | None = None
) -> list[dict[str, Any]]:
    """
    Process and filter data items.

    Args:
        items: List of data items to process
        filter_key: Optional key to filter by

    Returns:
        Processed and filtered list of items
    """
    # Implementation
    pass
```

### Docstrings

Use Google-style docstrings for all public modules, classes, and functions:

```python
def complex_function(param1: str, param2: int) -> dict[str, Any]:
    """
    Brief description of function purpose.

    Longer description providing more context about what this function
    does, how it works, and any important considerations.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Dictionary containing results with keys:
            - key1: Description of key1
            - key2: Description of key2

    Raises:
        ValueError: If param1 is empty
        TypeError: If param2 is negative

    Example:
        >>> result = complex_function("test", 42)
        >>> print(result["key1"])
        'processed_test'
    """
    pass
```

### Code Quality Tools

Before committing, run:

```bash
# Run every hook (ruff lint and format, codespell, shellcheck, detect-secrets)
uv run pre-commit run --all-files

# Format code
uv run ruff format .

# Check code quality
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Type checking (advisory: legacy type errors do not block commits)
uv run mypy src
```

## Testing Requirements

### Test Coverage

- All new features must include tests
- Aim for 90%+ test coverage for new code
- Test both common cases and edge cases
- Include integration tests for ETL pipelines
- Never call real external services from unit tests: use fixtures and stubs
- The only registered pytest markers are `e2e` and `slow`. `--strict-markers` is on, so any other marker is an error.

### Writing Tests

```python
# Tests/etl/test_new_feature.py
import pytest
from src.etl.module import NewFeature

class TestNewFeature:
    @pytest.fixture
    def feature(self):
        """Create feature instance for testing."""
        return NewFeature()

    def test_basic_functionality(self, feature):
        """Test basic feature operation."""
        result = feature.process("input")
        assert result == "expected_output"

    def test_edge_case(self, feature):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            feature.process("")

    @pytest.mark.e2e
    def test_end_to_end(self, feature):
        """Test against a real external service."""
        # End-to-end test code
        pass
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest Tests/etl/test_new_feature.py

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run only the unit tests
uv run pytest Tests/unit

# Skip the end-to-end tests
uv run pytest -m "not e2e"

# Run with verbose output
uv run pytest -v
```

## Submitting Changes

### Pull Request Process

1. **Ensure All Checks Pass**

```bash
uv run pre-commit run --all-files
uv run pytest
uv run ruff check .
uv run mypy src
```

2. **Update Documentation**

- Update relevant documentation files
- Add docstrings to new code
- Update README.md if adding new features
- Record the work on the task board (`docs/TASK_BOARD.md`); closed tasks and the changelog live in `docs/TASK_BOARD_ARCHIVE.md`

3. **Create Pull Request**

- Use a clear, descriptive title
- Fill out the pull request description using the template in step 4
- Reference related issues (e.g., "Closes #123")
- Include screenshots for UI changes
- Ensure CI checks pass

4. **PR Description Template**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] No new warnings generated
```

### Review Process

1. Maintainers will review your PR
2. Address any requested changes
3. Once approved, PR will be merged
4. Your contribution will be acknowledged in release notes

## Documentation

### Documentation Updates

When adding new features or changing behavior:

1. Update relevant documentation in `docs/`
2. Update code examples if needed
3. Update the main README.md
4. Add entries to FAQ.md if appropriate

### Documentation Style

- Use clear, concise language
- Include code examples
- Explain "why" not just "what"
- Keep examples practical and realistic
- Use proper Markdown formatting

## Community

### Getting Help

- **Questions**: [GitHub Discussions](https://github.com/josmerod/watchtower/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/josmerod/watchtower/issues)
- **Real-time Chat**: Discord/Slack (if available)

### Recognition

Contributors will be:
- Listed on the repository's Contributors page on GitHub
- Acknowledged in release notes
- Given credit in relevant documentation

## Development Principles

### Architecture Principles

1. **Single Responsibility**: Each class/function has one clear purpose
2. **DRY**: Don't Repeat Yourself - abstract common functionality
3. **KISS**: Keep It Simple, Stupid - prefer simplicity over complexity
4. **SOLID Principles**: Follow object-oriented design principles

### Performance Considerations

- Use async/await for I/O-bound operations
- Implement caching where appropriate
- Monitor resource usage in long-running processes

### Security Best Practices

- Never commit sensitive data (API keys, passwords)
- Use environment variables for secrets
- Validate all external input
- Follow OWASP top 10 guidelines
- Implement rate limiting for external APIs

## Specific Contribution Areas

### Adding New ETL Pipelines

1. Inherit from `BaseETL`
2. Implement `extract()`, `transform()`, `load()` methods
3. Add Pydantic models for data validation
4. Include comprehensive tests
5. Document data source and usage
6. Add the script to `ETL_SCRIPTS` in `run_all_etl_orchestrator.py`; the ETL cycle only runs listed scripts

See [ETL Development Guide](technical/ETL_DEVELOPMENT_GUIDE.md) for details.

### Adding New Watchers

1. Inherit from `BaseWatcher`
2. Implement `extract_value()` and `has_changed()`, its two abstract methods
3. Include error handling and logging
4. Add tests for change detection
5. Document watcher purpose and configuration

The contract is defined in `src/watchers/base_watcher.py`; the existing watchers in `src/watchers/` are working examples. See the [Watchers Guide](technical/WATCHERS_GUIDE.md) for background.

### Dashboard Components

1. Follow Dash component patterns
2. Load data with the helpers in `src/services/data_loader.py`, or with a `BaseRepository` subclass when the tab needs caching (see `docs/REPOSITORY_PATTERN.md`)
3. Use single-callback pattern
4. Include error boundaries
5. Ensure mobile responsiveness

See [Dashboard Development Guide](technical/DASHBOARD_DEVELOPMENT_GUIDE.md) for details.

## License

By contributing to Watchtower, you agree that your contributions will be licensed under the MIT License declared in `pyproject.toml`.

## Questions?

Don't hesitate to ask questions! We're here to help:
- Open a [GitHub Discussion](https://github.com/josmerod/watchtower/discussions)
- Comment on relevant issues
- Reach out to maintainers

Thank you for contributing to Watchtower! 🎯
