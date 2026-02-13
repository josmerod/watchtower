# Configuration Guide

Comprehensive guide to configuring the Watchtower platform.

## Table of Contents

- [Overview](#overview)
- [Configuration Architecture](#configuration-architecture)
- [Environment Variables](#environment-variables)
- [Settings System](#settings-system)
- [Component Configuration](#component-configuration)
- [Deployment Configurations](#deployment-configurations)
- [Best Practices](#best-practices)

## Overview

Watchtower uses a sophisticated configuration system built on Pydantic Settings with support for:
- Environment variables with `.env` files
- Nested configuration models
- Auto-discovery of project paths
- Type validation and coercion
- Component-specific configurations

## Configuration Architecture

```
┌──────────────────────────┐
│  Environment Variables   │
│     (.env file)          │
└───────────┬──────────────┘
            │
┌───────────▼──────────────┐
│   Pydantic Settings      │
│  (src/config/settings.py)│
└───────────┬──────────────┘
            │
┌───────────▼──────────────┐
│  Configuration Models    │
│ (src/config/models.py)   │
└───────────┬──────────────┘
            │
┌───────────▼──────────────┐
│   Component Configs      │
│ ETL│Watcher│Dashboard│DB │
└──────────────────────────┘
```

## Environment Variables

### Creating .env File

Create a `.env` file in the project root:

```bash
# Copy example if exists
cp .env.example .env

# Or create manually
nano .env
```

### Basic Configuration

```bash
# .env
# Python environment
PYTHON_ENV=development  # or production, staging

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or text

# Data directories
DATA_DIR=./data
LOGS_DIR=./logs

# Dashboard
DASHBOARD_PORT=7780
DASHBOARD_DEBUG=True
```

### API Keys (Optional)

```bash
# GitHub (for trending repositories)
GITHUB_TOKEN=ghp_your_token_here

# Reddit (for specific subreddits)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=watchtower:v1.0

# Cloud Platforms (optional)
AWS_ACCESS_KEY_ID=your_access_key
AZURE_SUBSCRIPTION_ID=your_subscription_id
GCP_PROJECT_ID=your_project_id
```

### Database Configuration (Future)

```bash
# PostgreSQL (when implemented)
DATABASE_URL=postgresql://user:password@localhost:5432/watchtower

# Or SQLite
DATABASE_URL=sqlite:///./data/watchtower.db
```

## Settings System

### Accessing Settings

```python
from src.config.settings import get_settings

# Get singleton settings instance
settings = get_settings()

# Access configuration
print(settings.data_dir)  # Path to data directory
print(settings.etl.batch_size)  # ETL batch size
print(settings.database.url)  # Database URL
```

### Settings Structure

```python
# src/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    python_env: str = Field(default="development")

    # Paths
    project_root: Path = Field(default_factory=discover_project_root)
    data_dir: Path = Field(default="data")
    logs_dir: Path = Field(default="logs")

    # Nested configs
    etl: ETLConfig = Field(default_factory=ETLConfig)
    watcher: WatcherConfig = Field(default_factory=WatcherConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"  # Use double underscore for nested configs
```

## Component Configuration

### ETL Configuration

```python
# src/config/models.py
class ETLConfig(BaseModel):
    """ETL pipeline configuration."""

    batch_size: int = Field(default=100, ge=1)
    retry_attempts: int = Field(default=3, ge=1)
    retry_delay: int = Field(default=5, ge=1)
    timeout: int = Field(default=30, ge=1)
    enable_checkpoints: bool = Field(default=True)
    checkpoint_dir: Path = Field(default="data/checkpoints")
```

**Environment Variables**:

```bash
# .env
ETL__BATCH_SIZE=200
ETL__RETRY_ATTEMPTS=5
ETL__TIMEOUT=60
ETL__ENABLE_CHECKPOINTS=true
```

**Usage**:

```python
from src.config.settings import get_settings

settings = get_settings()
batch_size = settings.etl.batch_size  # 200
retry_attempts = settings.etl.retry_attempts  # 5
```

### Watcher Configuration

```python
class WatcherConfig(BaseModel):
    """Watcher system configuration."""

    check_interval: int = Field(default=3600, ge=60)  # 1 hour
    state_dir: Path = Field(default="data/watchers")
    enable_notifications: bool = Field(default=False)
    notification_email: Optional[str] = None
```

**Environment Variables**:

```bash
WATCHER__CHECK_INTERVAL=7200  # 2 hours
WATCHER__ENABLE_NOTIFICATIONS=true
WATCHER__NOTIFICATION_EMAIL=alerts@example.com
```

### Dashboard Configuration

```python
class DashboardConfig(BaseModel):
    """Dashboard configuration."""

    port: int = Field(default=7780, ge=1024, le=65535)
    host: str = Field(default="127.0.0.1")
    debug: bool = Field(default=False)
    auto_reload: bool = Field(default=False)
    cache_timeout: int = Field(default=300)  # 5 minutes
```

**Environment Variables**:

```bash
DASHBOARD__PORT=8888
DASHBOARD__HOST=0.0.0.0
DASHBOARD__DEBUG=false
DASHBOARD__CACHE_TIMEOUT=600
```

### Database Configuration

```python
class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = Field(default="sqlite:///./data/watchtower.db")
    echo: bool = Field(default=False)
    pool_size: int = Field(default=5, ge=1)
    max_overflow: int = Field(default=10, ge=0)
```

**Environment Variables**:

```bash
DATABASE__URL=postgresql://user:pass@localhost/watchtower
DATABASE__ECHO=true
DATABASE__POOL_SIZE=10
```

## Deployment Configurations

### Development Configuration

```bash
# .env.development
PYTHON_ENV=development
LOG_LEVEL=DEBUG
DASHBOARD__DEBUG=True
DASHBOARD__AUTO_RELOAD=True
ETL__BATCH_SIZE=10
DATABASE__ECHO=True
```

### Production Configuration

```bash
# .env.production
PYTHON_ENV=production
LOG_LEVEL=INFO
DASHBOARD__DEBUG=False
DASHBOARD__HOST=0.0.0.0
DASHBOARD__AUTO_RELOAD=False
ETL__BATCH_SIZE=1000
ETL__RETRY_ATTEMPTS=5
DATABASE__URL=postgresql://user:pass@db-server/watchtower
DATABASE__POOL_SIZE=20
```

### Docker Configuration

```bash
# .env.docker
DATA_DIR=/app/data
LOGS_DIR=/app/logs
DASHBOARD__HOST=0.0.0.0
DATABASE__URL=postgresql://watchtower:password@postgres:5432/watchtower
```

## Advanced Configuration

### Custom Validators

```python
from pydantic import validator

class ETLConfig(BaseModel):
    batch_size: int = 100

    @validator('batch_size')
    def validate_batch_size(cls, v):
        """Ensure batch size is reasonable."""
        if v > 10000:
            raise ValueError("Batch size too large (max 10000)")
        return v
```

### Dynamic Configuration

```python
from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Singleton settings instance
    """
    return Settings()

# Settings are loaded once and cached
settings = get_settings()
```

### Environment-Specific Settings

```python
import os
from pathlib import Path

def get_env_file() -> Path:
    """Get environment-specific .env file."""
    env = os.getenv("PYTHON_ENV", "development")
    env_file = Path(f".env.{env}")

    if env_file.exists():
        return env_file

    return Path(".env")

class Settings(BaseSettings):
    class Config:
        env_file = get_env_file()
```

## Component-Specific Configuration Files

### ETL Pipeline Configuration

```python
# src/etl/arxiv/config.py
from pydantic import BaseModel

class ArxivETLConfig(BaseModel):
    """ArXiv ETL specific configuration."""

    categories: List[str] = ["cs.AI", "cs.LG", "cs.CL"]
    max_results: int = 100
    sort_by: str = "submittedDate"
    sort_order: str = "descending"
```

**Usage**:

```python
from src.etl.arxiv.config import ArxivETLConfig

config = ArxivETLConfig(
    categories=["cs.AI"],
    max_results=50
)
```

### Watcher Configuration

```python
# src/watchers/arxiv_watcher.py
from pydantic import BaseModel

class ArxivWatcherConfig(BaseModel):
    """ArXiv watcher configuration."""

    check_interval: int = 3600
    categories: List[str] = ["cs.AI"]
    notify_on_new_papers: bool = True
```

## Configuration Best Practices

### 1. Use Type Hints

```python
class Config(BaseModel):
    # Good: Type hints with validation
    timeout: int = Field(default=30, ge=1, le=300)
    api_key: Optional[str] = None

    # Avoid: No type hints
    # timeout = 30
```

### 2. Provide Defaults

```python
class Config(BaseModel):
    # Good: Sensible defaults
    batch_size: int = Field(default=100)
    enable_cache: bool = Field(default=True)

    # Avoid: Required fields for optional configs
    # batch_size: int  # No default, must be provided
```

### 3. Use Environment Variables for Secrets

```python
# Good: Secrets from environment
api_key: str = Field(..., env="API_KEY")

# Avoid: Hardcoded secrets
# api_key: str = "hardcoded_key_123"
```

### 4. Validate Constraints

```python
class Config(BaseModel):
    port: int = Field(default=7780, ge=1024, le=65535)
    batch_size: int = Field(default=100, ge=1, le=10000)

    @validator('port')
    def validate_port_available(cls, v):
        """Check if port is available."""
        # Custom validation logic
        return v
```

### 5. Document Configuration

```python
class ETLConfig(BaseModel):
    """
    ETL pipeline configuration.

    Attributes:
        batch_size: Number of items to process per batch (1-10000)
        timeout: Request timeout in seconds (1-300)
        enable_checkpoints: Enable checkpoint creation for resumability
    """
    batch_size: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Items per batch"
    )
```

### 6. Use Config Hierarchy

```python
# Global settings
settings = get_settings()

# Component-specific config
etl_config = settings.etl

# Pipeline-specific config
arxiv_config = ArxivETLConfig()
```

## Testing Configuration

### Test Configuration

```python
# tests/conftest.py
import pytest
from src.config.settings import Settings

@pytest.fixture
def test_settings():
    """Override settings for testing."""
    return Settings(
        python_env="testing",
        data_dir="tests/data",
        logs_dir="tests/logs",
        etl=ETLConfig(batch_size=10),
        database=DatabaseConfig(url="sqlite:///:memory:")
    )
```

### Mock Configuration

```python
# tests/test_etl.py
from unittest.mock import patch

def test_etl_with_custom_config():
    """Test ETL with custom configuration."""
    test_config = ETLConfig(batch_size=5)

    with patch('src.config.settings.get_settings') as mock_settings:
        mock_settings.return_value.etl = test_config
        # Run test
```

## Troubleshooting

### Configuration Not Loading

```python
# Debug configuration loading
from src.config.settings import get_settings

settings = get_settings()
print(f"Config loaded from: {settings.Config.env_file}")
print(f"Data dir: {settings.data_dir}")
print(f"ETL batch size: {settings.etl.batch_size}")
```

### Environment Variables Not Working

Check delimiter for nested configs:

```bash
# Correct
ETL__BATCH_SIZE=200

# Incorrect
ETL.BATCH_SIZE=200
ETL_BATCH_SIZE=200
```

### Type Validation Errors

```python
# Check validation errors
from pydantic import ValidationError

try:
    config = ETLConfig(batch_size="invalid")
except ValidationError as e:
    print(e.json())
```

## Additional Resources

- **Settings Source**: `src/config/settings.py`
- **Config Models**: `src/config/models.py`
- **Pydantic Settings Docs**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **Environment Variables**: https://12factor.net/config

This guide provides comprehensive coverage of the Watchtower configuration system. For component-specific configuration details, see individual component documentation.
