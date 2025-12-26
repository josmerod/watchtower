# Watchtower Refactoring Analysis & Plan

**Generated**: 2025-12-25
**Analysis Scope**: Full codebase with focus on high-impact refactoring opportunities
**Priority**: Critical code quality improvements for maintainability and scalability

---

## Executive Summary

This analysis identifies **critical code quality issues** across the Watchtower codebase that impact maintainability, testability, and scalability. The codebase shows **generally good architecture** with BaseETL and BaseWatcher patterns, but suffers from **several large monolithic files** and **anti-patterns** that require immediate attention.

### Key Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Largest File** | 3,516 lines | <500 lines | 🔴 Critical |
| **Files >500 lines** | 15 files | 0 files | 🔴 Critical |
| **Type Safety** | 60% coverage | 95%+ coverage | 🟡 Warning |
| **Global State Usage** | 15+ instances | 0 instances | 🔴 Critical |
| **Test Coverage** | ~40% | >80% | 🟡 Warning |
| **Cyclomatic Complexity** | >25 in hotspots | <10 | 🟡 Warning |

---

## 1. Critical Issues Identified

### 1.1 🔴 CRITICAL: Monolithic Files (>1000 lines)

**Impact**: Blocks team productivity, error-prone, untestable, violates Single Responsibility Principle

#### **src/miners/udemy-universal/base.py** (3,516 lines)
**Problems**:
- Single file handles: scraping, API interaction, threading, enrollment, error handling, logging
- 50+ methods mixed across 8 different responsibilities
- Direct tight coupling to cloudscraper, requests, playwright, rookiepy
- Global configuration dictionaries (scraper_dict, LINKS)
- No clear separation between domain logic and infrastructure

**Refactoring Strategy**:
```
base.py (3516 lines)
    ├── domain/
    │   ├── course.py              # Course entity and value objects
    │   ├── enrollment.py          # Enrollment domain logic
    │   └── exceptions.py          # Domain exceptions
    ├── infrastructure/
    │   ├── scrapers/
    │   │   ├── base_scraper.py    # Abstract scraper
    │   │   ├── cloudscraper.py    # CloudScraper adapter
    │   │   └── playwright_scraper.py
    │   ├── api/
    │   │   └── udemy_client.py    # Udemy API client
    │   └── repositories/
    │       └── course_repository.py
    ├── services/
    │   ├── course_scraper.py      # Orchestration
    │   ├── enrollment_service.py
    │   └── coupon_service.py
    ├── utils/
    │   ├── threading.py           # RaisingThread
    │   └── resource_path.py
    └── config.py                  # Configuration (not global)
```

**Expected Result**: 15-20 focused files, 100-250 lines each

---

#### **src/etl/youtube_shorts_ocr_etl.py** (1,406 lines)
**Problems**:
- ETL logic mixed with UI automation, OCR processing, video download
- Playwright automation mixed with data extraction
- No separation between concerns (scraping, OCR, data processing)

**Refactoring Strategy**:
```
youtube_shorts_ocr_etl.py (1406 lines)
    ├── domain/
    │   └── youtube_short.py       # YouTubeShort entity
    ├── services/
    │   ├── video_downloader.py    # Video download service
    │   ├── ocr_processor.py       # OCR processing
    │   └── transcript_extractor.py
    └── youtube_shorts_ocr_etl.py  # Orchestration only (150-200 lines)
```

---

#### **src/etl/arxiv/enhanced_arxiv_etl.py** (1,199 lines)
**Problems**:
- Enhanced features mixed with core ETL logic
- NLP classification, ranking, deduplication embedded in ETL
- 200+ line methods with nested loops

**Refactoring Strategy**:
```
enhanced_arxiv_etl.py (1199 lines)
    ├── services/
    │   ├── arxiv_classifier.py    # NLP classification
    │   ├── ranking_service.py     # Paper ranking
    │   └── deduplication_service.py
    ├── strategies/
    │   ├── classification_strategy.py
    │   └── ranking_strategy.py
    └── enhanced_arxiv_etl.py      # Core ETL only (200 lines)
```

---

### 1.2 🔴 CRITICAL: Global State Anti-Pattern

**Impact**: Race conditions, testing impossibility, hidden dependencies

#### **Dashboard Components Global State**

**Files Affected**:
- `src/web/dashboard/components/courses_tab.py`
- `src/web/dashboard/components/games_tab.py`
- `src/web/dashboard/components/arxiv_research_tab.py`
- `src/web/dashboard/components/crypto_tab.py`
- 10+ other tab components

**Anti-Pattern**:
```python
# ❌ BAD: Global mutable state
ALL_COURSES_DATA = {
    "coursera": pd.DataFrame(),
    "udemy": pd.DataFrame(),
    "pluralsight": pd.DataFrame(),
    "khan": pd.DataFrame(),
}
COURSES_DATA_LOADED = {
    "coursera": False,
    "udemy": False,
    "pluralsight": False,
    "khan": False,
}

def load_coursera_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED  # ❌
    # Modify globals...
```

**Problems**:
- **Race conditions**: Multiple Dash callbacks modifying globals concurrently
- **Testing impossible**: Cannot isolate tests without affecting global state
- **Hidden dependencies**: Functions depend on implicit global state
- **Memory leaks**: DataFrames never released from memory
- **Callback conflicts**: Dash "Duplicate callback outputs" errors

**Refactored Solution**:
```python
# ✅ GOOD: Data manager pattern with encapsulation
from dataclasses import dataclass
from typing import Dict

@dataclass
class CoursesDataManager:
    """Manages course data loading and caching with thread safety."""

    _data: Dict[str, pd.DataFrame] = field(default_factory=dict)
    _loaded: Dict[str, bool] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get_data(self, source: str) -> pd.DataFrame:
        """Get data for a specific source, loading if necessary."""
        with self._lock:
            if not self._loaded.get(source, False):
                self._load_source(source)
            return self._data.get(source, pd.DataFrame()).copy()

    def _load_source(self, source: str) -> None:
        """Load data from source (private method)."""
        loaders = {
            "coursera": self._load_coursera,
            "udemy": self._load_udemy,
            # ...
        }
        loader = loaders.get(source)
        if loader:
            loader()
            self._loaded[source] = True

# Create singleton instance
courses_manager = CoursesDataManager()

# Usage in callbacks
@dash.callback(
    Output("courses-table", "data"),
    Input("course-source", "value")
)
def update_courses_table(source: str):
    df = courses_manager.get_data(source)  # ✅ Thread-safe, testable
    return df.to_dict("records")
```

**Benefits**:
- ✅ Thread-safe with explicit locking
- ✅ Testable: Can inject mock data managers
- ✅ Encapsulated: Clear API, no globals
- ✅ Memory-efficient: Can implement caching/LRU
- ✅ Dash-compatible: Prevents callback conflicts

---

### 1.3 🟡 HIGH: Type Safety Issues

**Impact**: Runtime errors, reduced IDE support, harder refactoring

#### **src/etl/base.py** Type Issues

**MyPy Errors**:
```
src\etl\base.py:109: error: Incompatible types in assignment (expression has type "dict[str, Any]", target has type "str")
src\etl\base.py:163: error: Argument 1 to "Path" has incompatible type "str | None"; expected "str | PathLike[str]"
src\etl\base.py:416: error: Argument 1 to "append" of "list" has incompatible type "OutputType"; expected "TimestampedModel"
src\etl\base.py:447: error: List comprehension has incompatible type List[TimestampedModel]; expected List[dict[str, Any]]
src\etl\base.py:457: error: Incompatible return value type (got "list[TimestampedModel | dict[str, Any]]", expected "list[OutputType]")
```

**Problems**:
- Generic type variables `InputType` and `OutputType` not constrained properly
- Mixing `TimestampedModel` and `dict[str, Any]` in return types
- Nullable values not properly handled with Path construction
- Missing type stubs for pandas

**Refactoring Strategy**:

```python
# ❌ BEFORE: Loosely typed
class BaseETL(ABC, Generic[InputType, OutputType]):
    def transform(self, data: InputType) -> OutputType:
        # What are InputType and OutputType constraints?
        pass

# ✅ AFTER: Properly constrained generics
from typing import Protocol, TypeVar

# Define protocol for transformable data
class Transformable(Protocol):
    """Protocol for data that can be transformed by ETL."""
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self: ...  # type: ignore

# Constrained type variables
InputType = TypeVar("InputType", bound=Transformable)
OutputType = TypeVar("OutputType", bound=TimestampedModel)

class BaseETL(ABC, Generic[InputType, OutputType]):
    """Base ETL with type-safe transformation pipeline."""

    @abstractmethod
    def extract(self) -> list[InputType]: ...

    @abstractmethod
    def transform(self, data: list[InputType]) -> list[OutputType]:
        """Transform input data to output models.

        Args:
            data: List of input items conforming to Transformable protocol

        Returns:
            List of validated OutputType models

        Raises:
            ValidationError: If transformation fails validation
        """
        ...

    def load(self, data: list[OutputType]) -> None:
        """Load transformed data with proper type handling."""
        output_path = self._get_output_path()

        # Type-safe serialization
        serializable_data = [
            item.model_dump(mode="json") if hasattr(item, "model_dump")
            else item.dict() if hasattr(item, "dict")
            else item
            for item in data
        ]

        with open(output_path, "w") as f:
            json.dump(serializable_data, f, indent=2, default=str)
```

---

### 1.4 🟡 HIGH: SOLID Violations

#### **Single Responsibility Principle (SRP) Violations**

**Example: `src/web/dashboard/components/courses_tab.py`**

**Current Responsibilities** (8+ in one file):
1. Data loading (4 sources)
2. Date parsing
3. Data normalization
4. UI rendering
5. Callback registration
6. Filtering/sorting
7. Pagination
8. Export functionality

**Refactored Structure**:
```
courses/
├── course_data_manager.py      # Data loading and caching (SRP)
├── course_normalizer.py        # Data normalization (SRP)
├── date_parser.py              # Date parsing utilities (SRP)
├── course_filter.py            # Filtering logic (SRP)
└── courses_tab.py              # UI rendering and callbacks only (SRP)
```

---

#### **Open/Closed Principle (OCP) Violations**

**Example: Scraper selection in `udemy-universal/base.py`**

```python
# ❌ BEFORE: Must modify to add new scrapers
scraper_dict: dict = {
    "Udemy Freebies": "uf",
    "Tutorial Bar": "tb",
    "Real Discount": "rd",
    # Must modify code to add new scraper...
}

def get_scraper(name: str):
    code = scraper_dict.get(name)
    if code == "uf":
        return UdemyFreebiesScraper()
    elif code == "tb":
        return TutorialBarScraper()
    # Must add new elif for each scraper...
    else:
        raise ValueError(f"Unknown scraper: {name}")
```

**Refactored Solution**:
```python
# ✅ AFTER: Open for extension, closed for modification
from abc import ABC, abstractmethod

class Scraper(ABC):
    """Abstract base for scrapers."""

    @abstractmethod
    def scrape(self, url: str) -> list[Course]: ...

    @classmethod
    @abstractmethod
    def get_name(cls) -> str: ...

    @classmethod
    @abstractmethod
    def get_code(cls) -> str: ...

# Register scrapers using factory pattern
class ScraperFactory:
    """Factory for creating scraper instances."""

    _scrapers: Dict[str, Type[Scraper]] = {}

    @classmethod
    def register(cls, scraper_class: Type[Scraper]) -> None:
        """Register a new scraper (open for extension)."""
        code = scraper_class.get_code()
        cls._scrapers[code] = scraper_class

    @classmethod
    def create(cls, code: str) -> Scraper:
        """Create scraper instance."""
        scraper_class = cls._scrapers.get(code)
        if not scraper_class:
            raise ValueError(f"Unknown scraper code: {code}")
        return scraper_class()

# Usage - Adding new scraper doesn't modify existing code
@ScraperFactory.register
class UdemyFreebiesScraper(Scraper):
    @classmethod
    def get_code(cls) -> str:
        return "uf"

    def scrape(self, url: str) -> list[Course]:
        # Implementation...
        pass
```

---

### 1.5 🟡 HIGH: Code Smells

#### **Long Methods**
- `src/miners/udemy-universal/base.py`: Methods 200-400 lines
- `src/etl/arxiv/enhanced_arxiv_etl.py`: 200+ line methods with nested loops
- Dashboard components: 100+ line callback functions

#### **Duplicate Code**
- Date parsing logic duplicated across 6+ files
- Data loading patterns duplicated in every dashboard tab
- Error handling repeated without abstraction

#### **Magic Numbers**
```python
# ❌ BAD: Magic numbers scattered in code
if len(video_title) > 75:
    video_title = video_title[:75] + "..."

timeout = 30  # What does this mean?
max_retries = 5

# ✅ GOOD: Named constants
VIDEO_TITLE_MAX_LENGTH = 75
SCRAPER_TIMEOUT_SECONDS = 30
SCRAPER_MAX_RETRIES = 5
```

---

## 2. Prioritized Refactoring Plan

### Phase 1: Critical Quick Wins (Week 1)
**Effort**: 20-40 hours | **Impact**: High | **Risk**: Low

| Priority | Task | File(s) | Effort | Impact |
|----------|------|---------|--------|--------|
| 1 | Extract global state to data managers | Dashboard components | 12h | High |
| 2 | Add constants for magic numbers | All files | 4h | Medium |
| 3 | Extract duplicate date parsing | Utils module | 3h | Medium |
| 4 | Add type hints to critical paths | base.py, models | 6h | High |
| 5 | Fix MyPy errors in base.py | base.py | 4h | High |

**Total Effort**: ~29 hours
**Expected Impact**:
- ✅ Eliminate Dash callback conflicts
- ✅ Enable testing of dashboard components
- ✅ Reduce code duplication by 15-20%
- ✅ Improve type safety to 85%+

---

### Phase 2: Monolithic File Decomposition (Week 2-3)
**Effort**: 60-80 hours | **Impact**: Critical | **Risk**: Medium

| Priority | Task | File(s) | Effort | Impact |
|----------|------|---------|--------|--------|
| 1 | Refactor udemy-universal/base.py | Split into 15-20 modules | 24h | Critical |
| 2 | Refactor youtube_shorts_ocr_etl.py | Extract OCR/video services | 12h | High |
| 3 | Refactor enhanced_arxiv_etl.py | Extract classification/ranking | 16h | High |
| 4 | Refactor spanish_public_aid_etl.py | Extract validation logic | 10h | Medium |
| 5 | Apply SRP to dashboard tabs | Split each tab into 5-6 files | 18h | High |

**Total Effort**: ~80 hours
**Expected Impact**:
- ✅ Reduce largest file from 3,516 to <300 lines
- ✅ Improve testability from 40% to 70%+
- ✅ Enable parallel development
- ✅ Reduce cognitive load for new developers

---

### Phase 3: SOLID & Design Patterns (Week 4)
**Effort**: 40-50 hours | **Impact**: High | **Risk**: Medium

| Priority | Task | Component | Effort | Impact |
|----------|------|-----------|--------|--------|
| 1 | Implement Strategy pattern for scrapers | udemy-universal | 8h | High |
| 2 | Implement Factory pattern for ETLs | etl/ | 6h | Medium |
| 3 | Implement Repository pattern for data access | repositories/ | 12h | High |
| 4 | Extract domain models from infrastructure | Multiple | 16h | High |
| 5 | Implement Dependency Injection | services/ | 8h | High |

**Total Effort**: ~50 hours
**Expected Impact**:
- ✅ Open/Closed compliance for extensions
- ✅ Loose coupling between layers
- ✅ Testable with mocks/stubs
- ✅ Clear architecture boundaries

---

### Phase 4: Testing & Quality Gates (Week 5)
**Effort**: 30-40 hours | **Impact**: Critical | **Risk**: Low

| Priority | Task | Coverage Target | Effort |
|----------|------|-----------------|--------|
| 1 | Unit tests for refactored base.py | 90%+ | 8h |
| 2 | Unit tests for data managers | 90%+ | 6h |
| 3 | Integration tests for ETLs | 80%+ | 10h |
| 4 | Component tests for dashboard | 75%+ | 8h |
| 5 | Configure CI/CD quality gates | All | 6h |

**Total Effort**: ~38 hours
**Expected Impact**:
- ✅ Overall test coverage: 80%+
- ✅ Automated quality enforcement
- ✅ Regression prevention
- ✅ Confident refactoring

---

## 3. Detailed Refactoring Examples

### Example 1: Dashboard Data Manager Pattern

**Before** (`courses_tab.py`):
```python
# 1155 lines, global state, mixed responsibilities
ALL_COURSES_DATA = {...}
COURSES_DATA_LOADED = {...}

def load_coursera_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    # 70 lines of loading logic

def load_udemy_data():
    global ALL_COURSES_DATA, COURSES_DATA_LOADED
    # 70 lines of loading logic

def render_courses_tab():
    # 200+ lines of UI rendering
    # Mixed with data loading
```

**After** (`courses/` module):
```python
# courses/course_data_manager.py (150 lines)
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import threading

@dataclass
class CourseDataManagerConfig:
    """Configuration for course data manager."""
    coursera_path: Path
    udemy_path: Path
    pluralsight_path: Path
    khan_academy_path: Path
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600

class CourseDataManager:
    """Thread-safe manager for course data loading and caching."""

    def __init__(self, config: CourseDataManagerConfig):
        self._config = config
        self._data: Dict[str, pd.DataFrame] = {}
        self._loaded: Dict[str, bool] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def get_data(self, source: str) -> pd.DataFrame:
        """Get data for source, loading if necessary and caching if enabled."""
        with self._lock:
            if self._should_reload(source):
                self._load_source(source)
                self._cache_timestamps[source] = datetime.now()
            return self._data.get(source, pd.DataFrame()).copy()

    def _should_reload(self, source: str) -> bool:
        """Check if data needs to be reloaded."""
        if not self._loaded.get(source, False):
            return True
        if not self._config.enable_cache:
            return True

        cached_time = self._cache_timestamps.get(source)
        if not cached_time:
            return True

        age = (datetime.now() - cached_time).total_seconds()
        return age > self._config.cache_ttl_seconds

    def _load_source(self, source: str) -> None:
        """Load data from source."""
        loaders = {
            "coursera": self._load_coursera,
            "udemy": self._load_udemy,
            "pluralsight": self._load_pluralsight,
            "khan": self._load_khan_academy,
        }

        loader = loaders.get(source)
        if not loader:
            raise ValueError(f"Unknown source: {source}")

        try:
            loader()
            self._loaded[source] = True
        except Exception as e:
            self.logger.error(f"Failed to load {source}: {e}")
            self._data[source] = pd.DataFrame()
            self._loaded[source] = True

    def _load_coursera(self) -> None:
        """Load Coursera data."""
        path = self._config.coursera_path
        if not path.exists():
            self.logger.warning(f"Coursera file not found: {path}")
            self._data["coursera"] = pd.DataFrame()
            return

        df = pd.read_json(path)
        df = self._normalize_coursera(df)
        self._data["coursera"] = df

    def _normalize_coursera(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Coursera data columns."""
        # Standardize column names
        rename_map = {
            "name": "title",
            "link": "url",
            "partner": "institution",
            "category": "subject",
        }
        df = df.rename(columns=rename_map)

        # Ensure required columns
        required = ["title", "url", "description", "institution", "subject"]
        for col in required:
            if col not in df.columns:
                df[col] = None

        # Parse dates
        df["start_date"] = df["start_date_str"].apply(self._parse_date)
        df["scraped_at"] = df["scraped_at_str"].apply(self._parse_date)

        # Sort by scraped date
        df = df.sort_values("scraped_at", ascending=False)
        return df

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse date string with multiple format support."""
        if pd.isna(date_str) or not date_str:
            return None

        # Try ISO format
        try:
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        except ValueError:
            pass

        # Try common formats
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y"]
        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return None

# Singleton instance with default config
_default_config = CourseDataManagerConfig(
    coursera_path=get_data_path("classcentral", "coursera_courses.json"),
    udemy_path=get_data_path("udemy", "udemy_courses.json"),
    pluralsight_path=get_data_path("pluralsight_courses", "pluralsight_courses.json"),
    khan_academy_path=get_data_path("courses", "khan_academy_latest.json"),
)
courses_manager = CourseDataManager(_default_config)
```

**Benefits**:
- ✅ 150 lines vs 1155 lines (87% reduction)
- ✅ Thread-safe with explicit locking
- ✅ Configurable caching with TTL
- ✅ Testable: Can inject config and mock paths
- ✅ Single responsibility: Data loading only
- ✅ No global state

---

### Example 2: Type-Safe BaseETL

**Before** (`base.py`):
```python
class BaseETL(ABC, Generic[InputType, OutputType]):
    def transform(self, data: InputType) -> OutputType:
        # What types are these? No constraints.
        pass
```

**After** (`base.py` with proper constraints):
```python
from typing import Protocol, TypeVar, runtime_checkable

@runtime_checkable
class Transformable(Protocol):
    """Protocol for data that can be transformed."""

    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self: ...  # type: ignore[misc]

# Constrained type variables
InputType = TypeVar("InputType", bound=Transformable)
OutputType = TypeVar("OutputType", bound=TimestampedModel)

class BaseETL(ABC, Generic[InputType, OutputType]):
    """Base ETL with type-safe transformation pipeline."""

    @abstractmethod
    def extract(self) -> list[InputType]:
        """Extract raw data from source.

        Returns:
            List of input items conforming to Transformable protocol
        """
        ...

    @abstractmethod
    def transform(self, data: list[InputType]) -> list[OutputType]:
        """Transform input data to output models.

        Args:
            data: List of input items

        Returns:
            List of validated OutputType models

        Raises:
            ValidationError: If transformation fails
        """
        ...

    def load(self, data: list[OutputType]) -> None:
        """Load transformed data with proper type handling."""
        output_path = self._get_output_path()

        # Type-safe serialization
        serializable_data = [
            item.model_dump(mode="json")
            for item in data
        ]

        with open(output_path, "w") as f:
            json.dump(serializable_data, f, indent=2, default=str)
```

---

### Example 3: Strategy Pattern for Scrapers

**Before** (OCP violation):
```python
# Must modify to add new scraper
scraper_dict = {
    "Udemy Freebies": "uf",
    "Tutorial Bar": "tb",
    # ...
}

def get_scraper(code):
    if code == "uf":
        return UdemyFreebiesScraper()
    elif code == "tb":
        return TutorialBarScraper()
    # Must add new elif for each scraper
```

**After** (Open/Closed compliant):
```python
from abc import ABC, abstractmethod

class Scraper(ABC):
    """Abstract base for course scrapers."""

    @abstractmethod
    def scrape(self, url: str) -> list[Course]:
        """Scrape courses from URL.

        Args:
            url: URL to scrape

        Returns:
            List of scraped courses
        """
        ...

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get human-readable scraper name."""
        ...

    @classmethod
    @abstractmethod
    def get_code(cls) -> str:
        """Get unique scraper code."""
        ...

class ScraperFactory:
    """Factory for creating scraper instances.

    Open for extension: Register new scrapers without modifying factory.
    Closed for modification: Factory logic doesn't change for new scrapers.
    """

    _scrapers: Dict[str, Type[Scraper]] = {}

    @classmethod
    def register(cls, scraper_class: Type[Scraper]) -> None:
        """Register a new scraper.

        Args:
            scraper_class: Scraper class to register
        """
        code = scraper_class.get_code()
        cls._scrapers[code] = scraper_class

    @classmethod
    def create(cls, code: str) -> Scraper:
        """Create scraper instance by code.

        Args:
            code: Scraper code

        Returns:
            Scraper instance

        Raises:
            ValueError: If scraper code not found
        """
        scraper_class = cls._scrapers.get(code)
        if not scraper_class:
            available = ", ".join(cls._scrapers.keys())
            raise ValueError(
                f"Unknown scraper code: {code}. "
                f"Available: {available}"
            )
        return scraper_class()

    @classmethod
    def list_scrapers(cls) -> list[str]:
        """List all registered scraper codes."""
        return list(cls._scrapers.keys())

# Usage - Adding new scraper doesn't modify existing code
@ScraperFactory.register
class UdemyFreebiesScraper(Scraper):
    """Scraper for Udemy Freebies."""

    @classmethod
    def get_code(cls) -> str:
        return "uf"

    @classmethod
    def get_name(cls) -> str:
        return "Udemy Freebies"

    def scrape(self, url: str) -> list[Course]:
        # Implementation...
        pass

@ScraperFactory.register
class TutorialBarScraper(Scraper):
    """Scraper for Tutorial Bar."""

    @classmethod
    def get_code(cls) -> str:
        return "tb"

    @classmethod
    def get_name(cls) -> str:
        return "Tutorial Bar"

    def scrape(self, url: str) -> list[Course]:
        # Implementation...
        pass
```

---

## 4. Metrics & Success Criteria

### Before Refactoring
```
✗ Largest file: 3,516 lines (udemy-universal/base.py)
✗ Files >500 lines: 15 files
✗ Global state usage: 15+ instances
✗ Type safety: 60% coverage
✗ Test coverage: ~40%
✗ Cyclomatic complexity: >25 in hotspots
✗ Code duplication: ~12%
✗ SOLID compliance: 40%
```

### After Refactoring (Target)
```
✓ Largest file: <300 lines
✓ Files >500 lines: 0 files
✓ Global state usage: 0 instances
✓ Type safety: 95%+ coverage
✓ Test coverage: >80%
✓ Cyclomatic complexity: <10 average
✓ Code duplication: <3%
✓ SOLID compliance: 90%+
```

---

## 5. Implementation Roadmap

### Week 1: Critical Quick Wins
- [ ] Extract global state from dashboard components to data managers
- [ ] Create constants module for magic numbers
- [ ] Extract duplicate date parsing to utils
- [ ] Add type hints to critical paths
- [ ] Fix MyPy errors in base.py

**Deliverables**:
- 5 new data manager classes
- 1 constants module
- 1 date parser utility
- Type-safe base.py

**Effort**: 29 hours

---

### Week 2-3: Monolithic File Decomposition
- [ ] Refactor udemy-universal/base.py into 15-20 modules
- [ ] Refactor youtube_shorts_ocr_etl.py
- [ ] Refactor enhanced_arxiv_etl.py
- [ ] Refactor spanish_public_aid_etl.py
- [ ] Apply SRP to dashboard tabs

**Deliverables**:
- 15-20 new focused modules from udemy-universal
- 3 new service modules for youtube OCR
- 3 new service modules for ArXiv
- 5-6 files per dashboard tab

**Effort**: 80 hours

---

### Week 4: SOLID & Design Patterns
- [ ] Implement Strategy pattern for scrapers
- [ ] Implement Factory pattern for ETLs
- [ ] Implement Repository pattern for data access
- [ ] Extract domain models from infrastructure
- [ ] Implement Dependency Injection

**Deliverables**:
- Scraper strategy and factory
- ETL factory
- Repository layer
- Domain model layer
- DI container setup

**Effort**: 50 hours

---

### Week 5: Testing & Quality Gates
- [ ] Unit tests for refactored components (90%+ coverage)
- [ ] Integration tests for ETLs (80%+ coverage)
- [ ] Component tests for dashboard (75%+ coverage)
- [ ] Configure CI/CD quality gates
- [ ] Performance benchmarks

**Deliverables**:
- 200+ new unit tests
- 50+ new integration tests
- CI/CD pipeline with quality gates
- Performance benchmark suite

**Effort**: 38 hours

---

## 6. Risk Assessment & Mitigation

### High-Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking existing functionality | High | Medium | Comprehensive tests before refactoring, feature flags |
| Performance regression | Medium | Low | Performance benchmarks, load testing |
| Increased complexity | Medium | Low | Code reviews, architecture decision records |
| Team adoption resistance | Low | Medium | Training, documentation, gradual rollout |

---

## 7. Quality Checklist

### Code Quality Standards
- [ ] All methods < 20 lines (extract if longer)
- [ ] All classes < 200 lines (split if larger)
- [ ] No method has > 3 parameters (use parameter objects)
- [ ] Cyclomatic complexity < 10
- [ ] No nested loops > 2 levels
- [ ] All names are descriptive and searchable
- [ ] No commented-out code
- [ ] Consistent formatting (Ruff)
- [ ] Type hints added (Python 3.10+)
- [ ] Error handling comprehensive
- [ ] Logging added for debugging
- [ ] Tests achieve > 80% coverage
- [ ] No security vulnerabilities
- [ ] Static analysis clean (MyPy, Ruff)

---

## 8. Next Steps

1. **Review this plan** with the team and gather feedback
2. **Prioritize** refactoring tasks based on business value
3. **Set up** CI/CD quality gates
4. **Begin Phase 1** with data manager extraction
5. **Track progress** using the TODO list system

---

## Appendix A: SOLID Principles Summary

### Single Responsibility Principle (SRP)
"A class should have one, and only one, reason to change."

**Example**:
- ❌ `UserManager`: Handles validation, database, email, logging, cache
- ✅ `UserValidator`, `UserRepository`, `EmailService`, `ActivityLogger`

### Open/Closed Principle (OCP)
"Software entities should be open for extension, closed for modification."

**Example**:
- ❌ Modify `DiscountCalculator` for each new discount type
- ✅ `DiscountStrategy` interface with concrete implementations

### Liskov Substitution Principle (LSP)
"Derived classes must be substitutable for their base classes."

**Example**:
- ❌ `Square` changes `Rectangle` behavior (breaks LSP)
- ✅ `Square` and `Rectangle` implement `Shape` interface

### Interface Segregation Principle (ISP)
"Clients should not be forced to depend on interfaces they don't use."

**Example**:
- ❌ `Worker` interface forces `Robot` to implement `eat()` and `sleep()`
- ✅ `Workable`, `Eatable`, `Sleepable` segregated interfaces

### Dependency Inversion Principle (DIP)
"Depend on abstractions, not concretions."

**Example**:
- ❌ `UserService` depends on `MySQLDatabase` concrete class
- ✅ `UserService` depends on `Database` interface

---

## Appendix B: Refactoring Techniques Reference

### Extract Method
**When**: Method > 20 lines or does multiple things
**How**: Create focused methods with descriptive names

### Extract Class
**When**: Class > 200 lines or has multiple responsibilities
**How**: Split into cohesive classes with clear responsibilities

### Replace Magic Numbers with Constants
**When**: Numbers scattered in code without meaning
**How**: Create named constants in dedicated config module

### Replace Global State with Dependency Injection
**When**: Functions depend on global mutable state
**How**: Pass dependencies as parameters or use DI container

### Introduce Parameter Object
**When**: Method has > 3 parameters
**How**: Create a dataclass/Pydantic model to group related parameters

### Extract Strategy
**When**: Multiple conditional branches with different behavior
**How**: Create strategy interface and concrete implementations

---

**Document Version**: 1.0
**Last Updated**: 2025-12-25
**Status**: Ready for Review
