# GitHub Trending RSS ETL

This module provides ETL functionality for GitHub trending repository RSS feeds.

## Overview

The GitHub Trending RSS ETL fetches trending repository data from RSS feeds provided by [GitHubTrendingRSS](https://github.com/mshibanami/GitHubTrendingRSS) and processes them into structured format for dashboard consumption.

## Feeds Supported

### All Languages
- Daily trending repositories across all programming languages
- Weekly trending repositories across all programming languages
- Monthly trending repositories across all programming languages

### Python Specific
- Daily trending Python repositories
- Weekly trending Python repositories
- Monthly trending Python repositories

### Specialized Languages
- Weekly trending Jupyter Notebook repositories
- Monthly trending Jupyter Notebook repositories
- Monthly trending CUDA repositories
- Monthly trending Terraform (HCL) repositories

## Usage

### Running the ETL

```bash
# Run directly
uv run python src/etl/github/github_trending_rss_etl.py

# Or via ETL runner scripts
./run_all_etl.sh        # Linux/Mac
.\run_all_etl.bat       # Windows
```

### Output Files

The ETL generates the following files in `data/github_trending_rss/output/github_trending/`:

- Individual feed files: `github_trending_{period}_{language}.json`
- Combined latest data: `github_trending_latest.json`
- Metadata file: `metadata.json`

### Data Structure

Each repository entry contains:

```json
{
  "id": "unique-uuid",
  "name": "repository-name",
  "full_name": "owner/repository-name",
  "description": "Repository description",
  "url": "https://github.com/owner/repo",
  "language": "Python",
  "stars": 1234,
  "forks": 567,
  "owner": "owner-username",
  "owner_type": "User",
  "topics": ["topic1", "topic2"],
  "trending_category": "Daily - Python",
  "trending_period": "daily",
  "trending_language": "python",
  "created_at": "2025-07-31T12:00:00Z",
  "updated_at": "2025-07-31T12:00:00Z",
  "fetched_at": "2025-07-31T12:00:00Z",
  "rss_published": "2025-07-31T12:00:00Z"
}
```

## Dashboard Integration

The data is consumed by the GitHub Trending dashboard tab which provides:

- Tabbed interface organized by time period and programming language
- Repository details including stars, forks, language, and description
- Links to original GitHub repositories
- Sorting by popularity and recency

## Architecture

- **ETL Module**: `src/etl/github/github_trending_rss_etl.py`
- **Data Models**: `src/models/github.py`
- **Dashboard Component**: `src/web/dashboard/components/github_trending_tab.py`
- **Configuration**: Feeds defined in ETL module, paths configured in dashboard component

## Dependencies

- feedparser: RSS feed parsing
- requests: HTTP requests with retry logic
- pydantic: Data validation and models
- src.etl.base: BaseETL framework integration
