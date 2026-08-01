# Watchtower API Documentation

The Watchtower API exposes aggregated data from the News and Knowledge Garden dashboards.

**Base URL**: `http://<unraid-ip>:45714/api/v1`

## Endpoints

### 1. Get News
Fetch aggregated news items.

- **URL**: `/news`
- **Method**: `GET`
- **Parameters**:
    - `source` (optional): Filter by source key (e.g., `techcrunch`, `venturebeat`).
    - `limit` (optional): Maximum number of items to return (default: 50, max: 10000).
    - `offset` (optional): Number of items to skip (default: 0).

**Example**:
```bash
curl "http://localhost:45714/api/v1/news?source=techcrunch&limit=5&offset=10"
```

### 2. Get Knowledge Garden Items
Fetch items from knowledge garden sources (Open Source, Reddit, etc.).

- **URL**: `/knowledge-garden`
- **Method**: `GET`
- **Parameters**:
    - `source` (optional): Filter by source key (e.g., `opensource`, `gooddevs`).
    - `limit` (optional): Maximum number of items to return (default: 50, max: 10000).
    - `offset` (optional): Number of items to skip (default: 0).

**Example**:
```bash
curl "http://localhost:45714/api/v1/knowledge-garden?source=opensource"
```

### 3. Get Available Sources
List all available source keys for filtering.

- **URL**: `/sources`
- **Method**: `GET`

## Data Model
All items are returned in a unified format:

```json
{
  "title": "Title of the article or project",
  "url": "https://example.com/link",
  "source": "Source Name",
  "published_at": "2024-02-18 12:00 UTC",
  "category": "category_key"
}
```

## Deployment
The API runs automatically alongside the dashboard on port **45714**.
To deploy updates:
```bash
uv run --with paramiko deployment/deploy.py
```
