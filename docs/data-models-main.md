# Watchtower Data Models Documentation

## Overview

Watchtower uses **Pydantic 2.x** for all data models, providing runtime validation, type safety, and automatic serialization/deserialization. All models follow a consistent hierarchy and pattern.

**Documentation Generated:** 2025-01-11
**Project Type:** Data Processing & ETL Platform
**Models Location:** `src/models/`

---

## Base Model Hierarchy

### BaseModel (`src/models/base.py`)

Core Pydantic model with common configuration:

```python
from pydantic import BaseModel as PydanticBaseModel

class BaseModel(PydanticBaseModel):
    """Base model with common configuration and methods."""
```

**Features:**
- Field population by name and alias
- Validate on assignment
- Use enum values instead of enum names
- Custom methods: `dict_without_none()`, `update_from_dict()`

### TimestampedModel

Adds automatic timestamp tracking:

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `id` | `str` | Unique identifier (UUID4) | Auto-generated |
| `created_at` | `datetime` | Creation timestamp | Auto-set to UTC now |
| `updated_at` | `datetime \| None` | Last update timestamp | Auto-set on update |

### StatusModel

Status tracking for operations:

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Status value |
| `message` | `str \| None` | Status message |
| `details` | `dict[str, Any] \| None` | Additional status details |
| `timestamp` | `datetime` | Status timestamp |

### ErrorModel

Structured error information:

| Field | Type | Description |
|-------|------|-------------|
| `error_code` | `str` | Error code |
| `error_message` | `str` | Error message |
| `error_type` | `str` | Error type/class |
| `traceback` | `str \| None` | Error traceback |
| `context` | `dict[str, Any] \| None` | Additional error context |
| `timestamp` | `datetime` | Error timestamp |

### PaginationModel

Pagination support with automatic calculations:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `page` | `int` | ≥1 | Current page number |
| `page_size` | `int` | 1-1000 | Items per page |
| `total_items` | `int` | ≥0 | Total number of items |
| `total_pages` | `int` | ≥0 | Auto-calculated |
| `has_next` | `bool` | - | Auto-calculated |
| `has_previous` | `bool` | - | Auto-calculated |

### PaginatedResponse

Generic paginated response wrapper:

| Field | Type | Description |
|-------|------|-------------|
| `items` | `list` | List of items |
| `pagination` | `PaginationModel` | Pagination information |
| `metadata` | `dict[str, Any] \| None` | Additional response metadata |

---

## Domain-Specific Models

### ArXiv Research Papers (`src/models/arxiv.py`)

**Primary Model:** `ArxivPaperModel(TimestampedModel)`

**Key Features:**
- Research paper metadata (title, authors, abstract, categories)
- Classification using NLP
- Technology Readiness Level (TRL) assessment
- Commercial potential evaluation
- GitHub repository integration

**Enumerations:**
- `TechnologyReadinessLevel` (TRL_1 to TRL_9)
- `ResearchCategory` (AI, ML, Software Engineering, Data Engineering, etc.)
- `CommercialPotential` (HIGH, MEDIUM, LOW, RESEARCH)

**Related Models:**
- `GitHubRepositoryModel` - GitHub repo metadata (stars, forks, issues)

### Anime & Entertainment (`src/models/anime.py`)

**Primary Model:** `AnimeModel(TimestampedModel)`

**Features:**
- Anime metadata from MyAnimeList
- Episode tracking
- Rating and score information
- Genre and demographic classification
- Airing schedule

### News & Articles (`src/models/news.py`)

**Primary Model:** `NewsArticleModel(TimestampedModel)`

**Features:**
- Multi-source news aggregation (HackerNews, Reddit, Medium, DEV)
- URL validation
- Publication date tracking
- Source attribution
- Content categorization

### Games & Deals (`src/models/games.py`)

**Primary Model:** `GameDealModel(TimestampedModel)`

**Features:**
- Game metadata (title, platform, genre)
- Pricing information (current price, original price, discount percentage)
- Store information (Steam, Epic, Humble Bundle)
- Release date tracking
- Deal expiration dates

### Courses & Education (`src/models/course.py`)

**Primary Model:** `CourseModel(TimestampedModel)`

**Features:**
- Course metadata (title, instructor, platform)
- Pricing (free, paid, discounted)
- Enrollment information
- Platform support (Udemy, Coursera, DeepLearning.AI, Microsoft, Cloud providers)
- Certificate availability

### GitHub Repositories (`src/models/github.py`)

**Primary Model:** `GitHubTrendingModel(TimestampedModel)`

**Features:**
- Repository trending data
- Star history tracking
- Language and framework detection
- Topic classification
- Contributor metrics

### Giveaways & Free Items (`src/models/giveaways.py`)

**Primary Model:** `GiveawayModel(TimestampedModel)`

**Features:**
- Giveaway metadata (platform, item, expiration)
- Claim instructions
- Geographic restrictions
- Value estimation

### Security Intelligence (`src/models/security.py`)

**Primary Model:** `SecurityAlertModel(TimestampedModel)`

**Features:**
- CVE tracking
- Severity classification (CRITICAL, HIGH, MEDIUM, LOW)
- Affected packages and versions
- Remediation guidance
- CVSS scores

### ADHD Research (`src/models/adhd.py`)

**Primary Model:** `ADHDPublicationModel(TimestampedModel)`

**Features:**
- PubMed research paper metadata
- ADHD-specific classification
- Study type identification
- Research findings extraction

### Spanish Public Aid (`src/models/spanish_public_aid.py`)

**Primary Model:** `SpanishPublicAidModel(TimestampedModel)`

**Features:**
- Government aid program metadata
- Eligibility criteria
- Application deadlines
- Funding amounts
- Geographic coverage (Valencia, Spain)

### Technology Trends (`src/models/technology.py`)

**Primary Model:** `TechnologyModel(TimestampedModel)`

**Features:**
- Technology trend tracking
- Adoption lifecycle stage
- Trend direction (RISING, STABLE, DECLINING)
- Industry impact assessment

**Enumerations:**
- `TrendDirection` (RISING, STABLE, DECLINING, EMERGING, MATURE)
- `AdoptionLevel` (EARLY_ADOPTER, MAINSTREAM, LEGACY)

### E-commerce Deals (`src/models/ecommerce.py`)

**Primary Model:** `EcommerceDealModel(TimestampedModel)`

**Features:**
- Product deal tracking across multiple platforms
- Price history
- Discount calculations
- Product categories
- Vendor information

### Events & Activities (`src/models/events.py`)

**Primary Model:** `EventModel(TimestampedModel)`

**Features:**
- Event metadata (title, date, location, venue)
- Valencia-specific events
- Cinema listings
- Museum exhibitions
- Cultural activities

### Museums & Cultural (`src/models/museums.py`)

**Primary Model:** `MuseumModel(TimestampedModel)`

**Features:**
- Museum information
- Exhibition tracking
- Visitor information (hours, pricing)
- Location data
- Special events

---

## Common Patterns

### 1. Inheritance Pattern

All domain models extend `TimestampedModel`:

```python
class DomainModel(TimestampedModel):
    # Automatic fields from TimestampedModel:
    # - id: str (UUID4)
    # - created_at: datetime
    # - updated_at: datetime | None

    # Domain-specific fields
    field1: str = Field(description="...")
    field2: int | None = Field(default=None, description="...")
```

### 2. Enum Usage

Enumerations for controlled vocabularies:

```python
class StatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

class DomainModel(TimestampedModel):
    status: StatusEnum = Field(description="Status")
```

### 3. Optional Fields

Use `| None` with defaults for optional fields:

```python
optional_field: str | None = Field(default=None, description="...")
```

### 4. URL Validation

Use Pydantic's `HttpUrl` for URL fields:

```python
from pydantic import HttpUrl

url: HttpUrl | None = Field(default=None, description="...")
```

### 5. Computed Fields

Use `@computed_field` for derived values:

```python
from pydantic import computed_field

@computed_field
@property
def full_name(self) -> str:
    return f"{self.first_name} {self.last_name}"
```

### 6. Field Validators

Use `@field_validator` for custom validation:

```python
from pydantic import field_validator

@field_validator("email")
@classmethod
def validate_email(cls, v: str) -> str:
    if "@" not in v:
        raise ValueError("Invalid email")
    return v.lower()
```

---

## Data Storage Pattern

All models are serialized to JSON and stored in `data/{etl_name}/`:

```
data/
├── arxiv/
│   └── arxiv_papers.json          # List of ArxivPaperModel
├── anime/
│   └── anime_list.json            # List of AnimeModel
├── news/
│   ├── hackernews_posts.json     # List of NewsArticleModel
│   ├── reddit_posts.json
│   └── medium_articles.json
├── games/
│   ├── free_games.json            # List of GameDealModel
│   └── game_deals.json
└── courses/
    └── udemy_courses.json         # List of CourseModel
```

**Serialization:**
```python
# Writing
models_list = [model1, model2, ...]
json_data = [m.model_dump() for m in models_list]
with open(output_path, 'w') as f:
    json.dump(json_data, f, indent=2, default=str)

# Reading
with open(input_path, 'r') as f:
    data = json.load(f)
models = [DomainModel(**item) for item in data]
```

---

## Validation & Type Safety

### Runtime Validation

Pydantic validates all data at runtime:

```python
# Valid
model = DomainModel(field1="value", field2=123)

# Raises ValidationError
model = DomainModel(field1="value", field2="not_a_number")
```

### Type Hints

All models use Python 3.10+ type hints:

```python
from typing import Any

field: str                        # Required string
field: str | None                 # Optional string
field: list[str]                  # List of strings
field: dict[str, Any]             # Dictionary
field: list[NestedModel]          # List of nested models
```

### Constraints

Use Field constraints for validation:

```python
from pydantic import Field

# Number constraints
age: int = Field(ge=0, le=150)              # 0 ≤ age ≤ 150
score: float = Field(gt=0.0, lt=1.0)        # 0.0 < score < 1.0

# String constraints
name: str = Field(min_length=1, max_length=100)
email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")

# Collection constraints
tags: list[str] = Field(min_length=1, max_length=10)
```

---

## Model Registry

**Total Models:** 15 domain-specific + 6 base models = **21 models**

**Domain Coverage:**
- Research & Academia (ArXiv, ADHD)
- Entertainment (Anime, Games, Events, Museums)
- Technology (GitHub, Technology Trends, Security)
- Education (Courses)
- News & Media (News Articles)
- E-commerce (Games, Deals, Giveaways)
- Public Services (Spanish Public Aid)

**Base Infrastructure:**
- TimestampedModel
- StatusModel
- ErrorModel
- PaginationModel
- PaginatedResponse
- BaseModel

---

## Best Practices

### 1. Always Inherit from TimestampedModel

```python
class MyModel(TimestampedModel):  # ✓ Correct
    ...

class MyModel(BaseModel):         # ✗ Avoid (unless no timestamps needed)
    ...
```

### 2. Use Descriptive Field Descriptions

```python
title: str = Field(description="Article title")  # ✓ Helpful
title: str                                        # ✗ No context
```

### 3. Provide Defaults for Optional Fields

```python
field: str | None = Field(default=None)  # ✓ Explicit
field: str | None                         # ✗ Ambiguous
```

### 4. Use Enums for Controlled Values

```python
class Status(str, Enum):                 # ✓ Type-safe
    ACTIVE = "active"
    INACTIVE = "inactive"

status: Status

status: str  # Could be any string       # ✗ Not validated
```

### 5. Validate Complex Fields

```python
@field_validator("url")
@classmethod
def validate_url(cls, v: str) -> str:
    if not v.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return v
```

---

## Migration Strategy

Watchtower does not use traditional database migrations. Instead:

1. **Schema Evolution:** Models evolve with optional fields and defaults
2. **Backward Compatibility:** New fields added as optional
3. **Data Validation:** Pydantic validates on read/write
4. **No Database:** File-based JSON storage (no SQL migrations needed)

**Adding New Fields:**
```python
# Old model
class Model(TimestampedModel):
    field1: str

# New model (backward compatible)
class Model(TimestampedModel):
    field1: str
    field2: str | None = Field(default=None)  # New optional field
```

**Reading Old Data:**
```python
# Old JSON: {"id": "...", "field1": "value"}
model = Model(**old_data)  # field2 will be None (default)
```

---

## Related Documentation

- [ETL Development Guide](./technical/ETL_DEVELOPMENT_GUIDE.md) - Using models in ETL pipelines
- [Architecture Overview](./technical/ARCHITECTURE_OVERVIEW.md) - Data flow architecture
- [API Reference](./technical/API_REFERENCE.md) - Model API methods _(To be generated)_

---

**Last Updated:** 2025-01-11
**Model Count:** 21 total (15 domain + 6 base)
**Framework:** Pydantic 2.11.5+
**Python Version:** 3.10+
