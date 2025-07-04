# Contributing to Watchtower

Thank you for your interest in contributing to Watchtower! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Development Standards](#development-standards)
- [Submitting Changes](#submitting-changes)
- [Testing](#testing)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a code of conduct that fosters an open and welcoming environment. By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [Poetry](https://python-poetry.org/docs/#installation) (recommended) or pip/venv
- Git
- Playwright browsers

### Setting Up Your Development Environment

1. **Fork the Repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/watchtower.git
   cd watchtower
   ```

2. **Set up Development Environment**
   ```bash
   # Using Poetry (recommended)
   poetry install
   poetry shell
   
   # Or using venv
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Playwright Browsers**
   ```bash
   playwright install
   ```

4. **Verify Setup**
   ```bash
   # Run tests to verify everything works
   pytest Tests/ -v
   
   # Start the Streamlit dashboard
   streamlit run src/web/fullstreamlit/app.py
   ```

## Development Workflow

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

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(etl): add enhanced arXiv paper classification

- Implement ML-based paper categorization
- Add confidence scoring for classifications
- Include bias detection and mitigation
- Add comprehensive logging and metrics

Closes #123

fix(watcher): handle connection timeouts gracefully

- Add exponential backoff retry logic
- Increase default timeout to 30 seconds
- Improve error logging with context
- Add connection health monitoring

Fixes #456
```

## Development Standards

This project adheres to high development standards:

### Code Quality
- **Type Hints**: Use comprehensive type annotations for all functions and methods
- **Docstrings**: Google-style docstrings for all public modules, classes, and functions
- **Error Handling**: Robust error handling with appropriate logging
- **Testing**: Aim for 90%+ test coverage for new code

### Code Style
- **Formatting**: Use Ruff for code formatting and linting
- **Standards**: Follow PEP 8 and Pythonic practices
- **Imports**: Organize imports logically and remove unused imports

```bash
# Format and lint your code
ruff format .
ruff check . --fix
```

### Architecture Principles
- **Single Responsibility**: Each module/class should have one clear purpose
- **Composition over Inheritance**: Prefer composition and dependency injection
- **Configuration-Driven**: Use the Pydantic Settings system for configuration
- **Async/Await**: Use async patterns for I/O operations

## Submitting Changes

### Before Submitting

1. **Run Pre-commit Checks**
   ```bash
   # Install pre-commit hooks
   pre-commit install
   
   # Or run manually
   ruff format .
   ruff check . --fix
   pytest Tests/ -v
   ```

2. **Update Documentation**
   - Update relevant documentation if you're changing functionality
   - Add docstrings for new functions/classes
   - Update the README.md if needed

3. **Test Your Changes**
   ```bash
   # Run full test suite
   pytest Tests/ -v --cov=src
   
   # Test ETL pipelines
   python src/etl/news/news_get_ycombinator.py
   
   # Test Streamlit app
   streamlit run src/web/fullstreamlit/app.py
   ```

### Creating a Pull Request

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-number
   ```

2. **Make Your Changes**
   - Implement your feature or bug fix
   - Add/update tests as needed
   - Update documentation

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Testing

### Test Structure
```
Tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interactions
└── e2e/           # End-to-end tests for complete workflows
```

### Writing Tests
- Use `pytest` as the testing framework
- Follow the existing test patterns in the `Tests/` directory
- Mock external dependencies (APIs, file system, etc.)
- Test both happy path and error conditions

### Running Tests
```bash
# Run all tests
pytest Tests/ -v

# Run with coverage
pytest Tests/ -v --cov=src

# Run specific test file
pytest Tests/unit/test_config.py -v

# Run tests matching pattern
pytest Tests/ -k "test_etl" -v
```

## Documentation

### Types of Documentation

1. **Code Documentation**
   - Comprehensive docstrings for all public interfaces
   - Type hints for all function parameters and return values
   - Inline comments for complex logic

2. **API Documentation**
   - Update `docs/development/api-reference.md` for new APIs
   - Include usage examples

3. **User Documentation**
   - Update relevant sections in `docs/` for user-facing changes
   - Add new use cases to `docs/use-cases/` if applicable

### Documentation Standards
- Use clear, concise language
- Include practical examples
- Keep documentation up-to-date with code changes
- Cross-link related documentation

## Issue Reporting

When reporting bugs or suggesting features:

1. **Search Existing Issues**: Check if the issue already exists
2. **Use Issue Templates**: Fill out the provided templates completely
3. **Provide Context**: Include relevant logs, configuration, and environment details
4. **Steps to Reproduce**: For bugs, provide clear reproduction steps

### Bug Report Template
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g. Windows 10, Ubuntu 20.04]
- Python version: [e.g. 3.11.2]
- Poetry/pip version: [e.g. Poetry 1.4.2]
- Browser (if relevant): [e.g. Chrome 91.0]

**Additional context**
Add any other context, logs, or screenshots.
```

## Pull Request Process

1. **PR Description**: Provide a clear description of changes and motivation
2. **Link Issues**: Reference related issues (e.g., "Closes #123", "Fixes #456")
3. **CI Checks**: Ensure all automated checks pass
4. **Code Review**: Address feedback from maintainers
5. **Documentation**: Update documentation if needed
6. **Testing**: Verify that tests pass and coverage is maintained

### PR Review Process
- Maintainers will review PRs within a reasonable timeframe
- Address feedback promptly and professionally
- Maintainers may request changes before merging
- Once approved, maintainers will merge the PR

## Additional Resources

- [Architecture Overview](docs/development/architecture-overview.md)
- [API Reference](docs/development/api-reference.md)
- [Workflow Guide](docs/development/workflow-guide.md)
- [Use Cases Documentation](docs/use-cases/)

Thank you for contributing to Watchtower! Your contributions help make this project better for everyone.