# Refactoring Quick Start Guide

**Purpose**: Adopt the new refactored patterns in your code
**Audience**: Developers working on Watchtower
**Time Required**: 15-30 minutes per component

---

## Overview

This guide shows you how to **quickly adopt** the new refactored patterns to eliminate anti-patterns in your code. Each pattern adoption takes 15-30 minutes and immediately improves code quality.

---

## Pattern 1: Data Manager Pattern (Replace Global State)

**When to Use**: Your module uses global dictionaries/DataFrames for data storage

**Time Required**: 20-30 minutes

### Before (Global State Anti-Pattern)

```python
# ❌ BAD: Global mutable state
ALL_DATA = {"source1": pd.DataFrame(), "source2": pd.DataFrame()}
DATA_LOADED = {"source1": False, "source2": False}

def load_source1():
    global ALL_DATA, DATA_LOADED
    # 50 lines of loading logic
    ALL_DATA["source1"] = df
    DATA_LOADED["source1"] = True

def get_data():
    global ALL_DATA
    return ALL_DATA["source1"]
```

**Problems**:
- ❌ Not thread-safe (race conditions in Dash callbacks)
- ❌ Impossible to test (can't isolate)
- ❌ Memory leaks (never released)
- ❌ Dash "Duplicate callback outputs" errors

### After (Data Manager Pattern)

```python
# ✅ GOOD: Encapsulated data manager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import pandas as pd
import threading
from src.utils.logging import get_logger

@dataclass
class MyDataManagerConfig:
    """Configuration for data manager."""
    source1_path: Path
    source2_path: Path
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600

class MyDataManager:
    """Thread-safe data manager."""

    def __init__(self, config: MyDataManagerConfig):
        self._config = config
        self._data: Dict[str, pd.DataFrame] = {}
        self._loaded: Dict[str, bool] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self.logger = get_logger(self.__class__.__name__)

    def get_data(self, source: str) -> pd.DataFrame:
        """Get data for source (thread-safe)."""
        with self._lock:
            if self._should_reload(source):
                self._load_source(source)
                self._cache_timestamps[source] = datetime.now(timezone.utc)
            return self._data.get(source, pd.DataFrame()).copy()

    def _should_reload(self, source: str) -> bool:
        """Check if cache needs refresh."""
        if not self._loaded.get(source, False):
            return True
        if not self._config.enable_cache:
            return True

        cached_time = self._cache_timestamps.get(source)
        if not cached_time:
            return True

        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        return age > self._config.cache_ttl_seconds

    def _load_source(self, source: str) -> None:
        """Load data from source."""
        loaders = {
            "source1": self._load_source1,
            "source2": self._load_source2,
        }

        loader = loaders.get(source)
        if loader:
            try:
                loader()
                self._loaded[source] = True
            except Exception as e:
                self.logger.error(f"Failed to load {source}: {e}")
                self._data[source] = pd.DataFrame()
                self._loaded[source] = True

    def _load_source1(self) -> None:
        """Load source1 data."""
        path = self._config.source1_path
        if not path.exists():
            self.logger.warning(f"Source1 file not found: {path}")
            self._data["source1"] = pd.DataFrame()
            return

        df = pd.read_json(path)
        self._data["source1"] = df

    def _load_source2(self) -> None:
        """Load source2 data (similar to source1)."""
        path = self._config.source2_path
        if not path.exists():
            self.logger.warning(f"Source2 file not found: {path}")
            self._data["source2"] = pd.DataFrame()
            return

        df = pd.read_json(path)
        self._data["source2"] = df

# Create singleton instance
config = MyDataManagerConfig(
    source1_path=Path("data/source1.json"),
    source2_path=Path("data/source2.json"),
)
my_manager = MyDataManager(config)

# Usage in callbacks
@dash.callback(
    Output("my-table", "data"),
    Input("source-selector", "value")
)
def update_table(source):
    df = my_manager.get_data(source)  # ✅ Thread-safe, cached
    return df.to_dict("records")
```

**Benefits**:
- ✅ Thread-safe (prevents Dash callback conflicts)
- ✅ Testable (can inject mock config)
- ✅ Configurable caching (memory-efficient)
- ✅ Clear API (encapsulated)

---

## Pattern 2: Unified Date Parsing

**When to Use**: Your module has custom date parsing logic

**Time Required**: 10-15 minutes

### Before (Duplicated Date Parsing)

```python
# ❌ BAD: 40+ lines duplicated in every file
from datetime import datetime, timezone
import pandas as pd

def parse_date(date_str):
    if pd.isna(date_str) or not date_str:
        return None
    try:
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    common_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y"]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(str(date_str), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        ts = float(date_str)
        if ts > 10000000000:
            ts /= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except ValueError:
        pass

    print(f"Warning: Could not parse date: {date_str}")
    return None
```

### After (Unified Date Parser)

```python
# ✅ GOOD: Use centralized date parser
from src.utils.date_parser import parse_date, format_date, DateParser

# Simple usage
def parse_date_wrapper(date_str):
    return parse_date(date_str)

# Advanced usage (custom configuration)
parser = DateParser(
    default_timezone=timezone.utc,
    raise_on_error=False,  # Return None on error instead of raising
)

def parse_dates_batch(date_strings):
    """Parse multiple dates efficiently."""
    return parser.parse_batch(date_strings)

# Format dates
def format_for_display(dt):
    return format_date(dt, format_str="%B %d, %Y")
```

**Migration Steps**:
1. Add import: `from src.utils.date_parser import parse_date`
2. Replace your parsing function with `parse_date(date_str)`
3. Remove your old parsing code (40+ lines)
4. Test with various date formats

---

## Pattern 3: Centralized Constants

**When to Use**: Your code has magic numbers

**Time Required**: 5-10 minutes

### Before (Magic Numbers)

```python
# ❌ BAD: Magic numbers scattered in code
def process_video(video_title):
    if len(video_title) > 75:  # What is 75?
        video_title = video_title[:75] + "..."
    return video_title

def fetch_data():
    timeout = 30  # Seconds? Minutes?
    max_retries = 5
    # ...
```

### After (Centralized Constants)

```python
# ✅ GOOD: Named constants
from src.constants.etl import (
    VIDEO_TITLE_MAX_LENGTH,
    SCRAPER_DEFAULT_TIMEOUT_SECONDS,
    SCRAPER_DEFAULT_MAX_RETRIES,
)

def process_video(video_title):
    if len(video_title) > VIDEO_TITLE_MAX_LENGTH:
        video_title = video_title[:VIDEO_TITLE_MAX_LENGTH] + "..."
    return video_title

def fetch_data():
    timeout = SCRAPER_DEFAULT_TIMEOUT_SECONDS  # Self-documenting
    max_retries = SCRAPER_DEFAULT_MAX_RETRIES
    # ...
```

**Benefits**:
- ✅ Self-documenting code
- ✅ Single source of truth
- ✅ Easy to adjust thresholds

---

## Pattern 4: Strategy Pattern (Replace Conditional Logic)

**When to Use**: You have multiple conditional branches for different behaviors

**Time Required**: 30-45 minutes

### Before (OCP Violation)

```python
# ❌ BAD: Must modify to add new scraper
class ScraperFactory:
    def get_scraper(self, scraper_type):
        if scraper_type == "web":
            return WebScraper()
        elif scraper_type == "api":
            return ApiScraper()
        elif scraper_type == "rss":
            return RssScraper()
        # Must add new elif for each scraper ❌
        else:
            raise ValueError(f"Unknown scraper: {scraper_type}")
```

### After (Strategy Pattern)

```python
# ✅ GOOD: Open for extension, closed for modification
from abc import ABC, abstractmethod

class Scraper(ABC):
    """Abstract scraper strategy."""

    @abstractmethod
    def scrape(self, url: str) -> list[dict]:
        """Scrape data from URL."""
        pass

    @classmethod
    @abstractmethod
    def get_type(cls) -> str:
        """Get scraper type identifier."""
        pass

class ScraperFactory:
    """Factory for scraper strategies."""

    _scrapers: Dict[str, Type[Scraper]] = {}

    @classmethod
    def register(cls, scraper_class: Type[Scraper]) -> None:
        """Register a new scraper (open for extension)."""
        scraper_type = scraper_class.get_type()
        cls._scrapers[scraper_type] = scraper_class

    @classmethod
    def create(cls, scraper_type: str) -> Scraper:
        """Create scraper instance."""
        scraper_class = cls._scrapers.get(scraper_type)
        if not scraper_class:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        return scraper_class()

# Usage - Adding new scraper doesn't modify factory code ✅
@ScraperFactory.register
class WebScraper(Scraper):
    @classmethod
    def get_type(cls) -> str:
        return "web"

    def scrape(self, url: str) -> list[dict]:
        # Implementation
        pass

@ScraperFactory.register
class ApiScraper(Scraper):
    @classmethod
    def get_type(cls) -> str:
        return "api"

    def scrape(self, url: str) -> list[dict]:
        # Implementation
        pass

# Add new scraper without modifying existing code ✅
@ScraperFactory.register
class DatabaseScraper(Scraper):
    @classmethod
    def get_type(cls) -> str:
        return "database"

    def scrape(self, url: str) -> list[dict]:
        # Implementation
        pass
```

**Benefits**:
- ✅ Open/Closed Principle compliant
- ✅ Add new scrapers without modifying existing code
- ✅ Easy to test (can register mock scrapers)

---

## Pattern 5: Extract Method (Break Down Long Methods)

**When to Use**: Your method is >20 lines or does multiple things

**Time Required**: 15-30 minutes

### Before (Long Method)

```python
# ❌ BAD: 150-line method doing 8 different things
def process_order(order_data):
    # Validation (20 lines)
    if not order_data.get('customer_id'):
        return {'error': 'No customer'}
    if not order_data.get('items'):
        return {'error': 'No items'}
    # ... more validation

    # Database operations (50 lines)
    conn = mysql.connector.connect(...)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders...")
    # ... more database code

    # Business logic (40 lines)
    total = 0
    for item in order_data['items']:
        total += item['price'] * item['quantity']
    # ... more business logic

    # Email notifications (30 lines)
    smtp = smtplib.SMTP('smtp.gmail.com')
    smtp.sendmail(...)
    # ... more email code

    # Logging (10 lines)
    log_file.write(...)
```

### After (Extracted Methods)

```python
# ✅ GOOD: Each method does one thing
class OrderProcessor:
    def process_order(self, order_data: dict) -> dict:
        """Process order with validation, persistence, and notification."""
        # Validate
        validation_result = self.validate_order(order_data)
        if not validation_result['valid']:
            return {'error': validation_result['error']}

        # Persist
        order_id = self.save_order(order_data)

        # Calculate total
        total = self.calculate_total(order_data['items'])

        # Notify
        self.send_confirmation_email(order_data, order_id, total)

        # Log
        self.log_order_processed(order_id, total)

        return {'success': True, 'order_id': order_id, 'total': total}

    def validate_order(self, order_data: dict) -> dict:
        """Validate order data."""
        if not order_data.get('customer_id'):
            return {'valid': False, 'error': 'No customer'}
        if not order_data.get('items'):
            return {'valid': False, 'error': 'No items'}
        return {'valid': True}

    def save_order(self, order_data: dict) -> int:
        """Save order to database."""
        # 20 lines of database code
        pass

    def calculate_total(self, items: list) -> float:
        """Calculate order total."""
        return sum(item['price'] * item['quantity'] for item in items)

    def send_confirmation_email(self, order_data: dict, order_id: int, total: float) -> None:
        """Send confirmation email."""
        # 20 lines of email code
        pass

    def log_order_processed(self, order_id: int, total: float) -> None:
        """Log order processing."""
        # 5 lines of logging code
        pass
```

**Benefits**:
- ✅ Single Responsibility Principle
- ✅ Easy to test each method
- ✅ Easy to understand
- ✅ Reusable methods

---

## Pattern 6: Parameter Object (Reduce Parameter Count)

**When to Use**: Your method has >3 parameters

**Time Required**: 10-15 minutes

### Before (Long Parameter List)

```python
# ❌ BAD: 8 parameters, hard to remember order
def create_user(
    first_name,
    last_name,
    email,
    phone,
    address,
    city,
    state,
    zip_code
):
    pass

# Usage is error-prone
create_user("John", "Doe", "john@example.com", "555-1234", "123 Main St", "Springfield", "IL", "62701")
```

### After (Parameter Object)

```python
# ✅ GOOD: Parameter object with clear structure
from dataclasses import dataclass
from typing import Optional

@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str

@dataclass
class CreateUserRequest:
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[Address] = None

    def validate(self) -> None:
        """Validate request data."""
        if not self.email:
            raise ValueError("Email is required")
        # ... more validation

def create_user(request: CreateUserRequest) -> int:
    """Create user with validated request."""
    request.validate()
    # Create user logic
    return user_id

# Usage is clear and self-documenting
request = CreateUserRequest(
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    phone="555-1234",
    address=Address(
        street="123 Main St",
        city="Springfield",
        state="IL",
        zip_code="62701"
    )
)
user_id = create_user(request)
```

**Benefits**:
- ✅ Self-documenting
- ✅ Easy to extend (add fields without breaking calls)
- ✅ Validation can be encapsulated
- ✅ Easier to test

---

## Quick Adoption Checklist

For each component you want to refactor:

### Step 1: Identify Anti-Patterns (5 minutes)
- [ ] Global state (global dicts/DataFrames)
- [ ] Magic numbers (unexplained constants)
- [ ] Duplicated date parsing logic
- [ ] Long methods (>20 lines)
- [ ] Long parameter lists (>3 parameters)
- [ ] Conditional logic for multiple behaviors

### Step 2: Choose Pattern (2 minutes)
- Global state → Data Manager Pattern
- Magic numbers → Centralized Constants
- Duplicated date parsing → Unified Date Parser
- Long methods → Extract Method
- Long parameter lists → Parameter Object
- Multiple behaviors → Strategy Pattern

### Step 3: Implement (10-30 minutes)
- [ ] Copy pattern template from this guide
- [ ] Adapt to your specific use case
- [ ] Replace old code with new pattern
- [ ] Test thoroughly

### Step 4: Verify (5 minutes)
- [ ] Code compiles/runs without errors
- [ ] All tests pass
- [ ] No regressions in functionality
- [ ] Code is more readable

---

## Example: Full Migration (20 minutes)

### Before (Global State + Magic Numbers + Long Method)

```python
# ❌ BAD: Multiple anti-patterns
ALL_GAMES = {"steam": pd.DataFrame(), "epic": pd.DataFrame()}
GAMES_LOADED = {"steam": False, "epic": False}

def load_steam_games():
    global ALL_GAMES, GAMES_LOADED
    # 50 lines of loading logic with magic numbers
    timeout = 30
    max_retries = 5
    # ...

def render_games_tab():
    # 200+ lines of UI rendering mixed with data loading
    global ALL_GAMES, GAMES_LOADED
    if not GAMES_LOADED["steam"]:
        load_steam_games()
    # ... more mixed concerns
```

### After (Clean Architecture)

**Step 1: Create data manager (10 minutes)**
```python
# ✅ GOOD: games_data_manager.py
from src.web.dashboard.managers.course_data_manager import CourseDataManager

class GamesDataManager(CourseDataManager):
    """Specialized manager for games data."""
    pass  # Inherits all thread-safe caching logic

# Singleton instance
games_manager = GamesDataManager(config)
```

**Step 2: Extract constants (2 minutes)**
```python
# ✅ GOOD: Use existing constants
from src.constants.etl import SCRAPER_DEFAULT_TIMEOUT_SECONDS, SCRAPER_DEFAULT_MAX_RETRIES

timeout = SCRAPER_DEFAULT_TIMEOUT_SECONDS
max_retries = SCRAPER_DEFAULT_MAX_RETRIES
```

**Step 3: Simplify rendering (8 minutes)**
```python
# ✅ GOOD: Clean UI rendering
def render_games_tab():
    """Render games tab (UI only, no data loading)."""
    return html.Div([
        html.H1("Games"),
        dcc.Dropdown(
            id="game-source",
            options=[
                {"label": "Steam", "value": "steam"},
                {"label": "Epic", "value": "epic"},
            ],
            value="steam"
        ),
        dash.dash_table.DataTable(
            id="games-table",
            columns=[{"name": "Title", "id": "title"}],
        )
    ])

@dash.callback(
    Output("games-table", "data"),
    Input("game-source", "value")
)
def update_games_table(source):
    """Update games table (thread-safe data access)."""
    df = games_manager.get_data(source)
    return df.to_dict("records")
```

**Result**:
- ✅ 200+ lines → 50 lines
- ✅ Thread-safe
- ✅ Testable
- ✅ No global state
- ✅ Clear separation of concerns

---

## Get Help

- **Full Analysis**: See `docs/REFACTORING_ANALYSIS.md`
- **Summary Report**: See `docs/REFACTORING_SUMMARY.md`
- **Example Code**: See `src/web/dashboard/managers/course_data_manager.py`
- **Date Parser**: See `src/utils/date_parser.py`
- **Constants**: See `src/constants/etl.py`

---

**Remember**: Each pattern adoption takes 15-30 minutes and immediately improves code quality. Start with the highest-impact patterns (Data Manager, Date Parser, Constants) and work incrementally.

**Estimated ROI**: 1 hour of refactoring saves 5-10 hours of maintenance over the next 6 months.
