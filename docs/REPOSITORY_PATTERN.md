# Repository Pattern Implementation

> Trimmed on 2026-11-24. The sections on the `RepositoryManager`-based dashboard integration, the migration path for the dashboard tabs, the benefits and SOLID discussion, the performance figures, the metrics, the sample tests, the next steps and the related Strategy and Dependency Injection patterns were removed: they described deleted code, together with figures, tests and plans that the repository does not contain. The dependency-injection layer that wired up the repository managers, the dashboard `managers/` package and ten dashboard components that used this pattern were deleted in the September 2026 cleanup.

## Overview

The repository pattern gives a dashboard component a cached, typed view of one data file. The component subclasses `BaseRepository`, says how the raw file becomes the data it needs, and calls `get()`.

Everything lives in `src/repositories/`:

| File | Contents | Used outside the package by |
| :-- | :-- | :-- |
| `base_repository.py` | `BaseRepository`, `RepositoryError`, `CacheEntry`, `DataFrameRepository` | Seven dashboard components, all through `BaseRepository` |
| `repository_manager.py` | `RepositoryManager`, `AggregatedRepository`, three `create_*_repository_manager()` functions | Nothing |
| `__init__.py` | Re-exports of the names above | The seven components |

## `BaseRepository`

`BaseRepository` is an abstract generic class; `T` is the type `get()` returns.

```python
class BaseRepository(ABC, Generic[T]):
    def __init__(self, data_path: Path, cache_ttl_seconds: int = 3600, enable_cache: bool = True): ...

    @abstractmethod
    def transform_data(self, raw_data: Any) -> T: ...

    def get(self, force_refresh: bool = False) -> T: ...
    def load_data(self) -> T: ...
    def clear_cache(self) -> None: ...
    def is_available(self) -> bool: ...
    def get_last_modified(self) -> datetime | None: ...
```

- **`transform_data()`** is the only abstract method. It receives the parsed file (what `json.load` returned for a `.json` file, a pandas DataFrame for `.csv` and `.tsv`) and returns it in the shape the component wants.
- **`get()`** is the entry point the components call. It returns the cached value while the time-to-live is valid and the file has not changed since it was read, and reloads the file otherwise; `force_refresh=True` skips the cache. Any failure, a missing file included, is raised as `RepositoryError`.
- **`load_data()`** reads and transforms the file on every call, without touching the cache, and a missing file raises `FileNotFoundError` instead of `RepositoryError`.
- **`is_available()`** reports whether the data file exists, and **`get_last_modified()`** returns its modification time.
- **`clear_cache()`** drops the cached value.

`RepositoryError` and `CacheEntry`, the object that holds the cached value, are defined in the same module. File extensions other than `.json`, `.csv` and `.tsv` are rejected with `RepositoryError`.

## Usage in the dashboard

Seven dashboard components under `src/web/dashboard/components/` use the pattern, with ten subclasses between them:

| Component | Subclass of `BaseRepository` | Data |
| :-- | :-- | :-- |
| `cinema_tab.py` | `CinemaSessionsRepository`, `CinemaStatusRepository` | Cinema sessions (one record per screening) and the status of the last run |
| `fourchan_tab.py` | `FourChanRepository` | 4chan generals |
| `games_tab.py` | `GamesRepository` | Game deals, bundles and itch.io trending |
| `knowledge_garden_tab.py` | `KnowledgeGardenRepository` | One instance per configured source |
| `shortcuts_tab.py` | `ShortcutsRepository` | Predefined and custom shortcuts |
| `spanish_public_aid_tab.py` | `SpanishAidRepository`, `SpanishAidStatsRepository`, `BdnsConvocatoriasRepository` | Aid items, aid statistics and BDNS convocatorias |
| `valencia_events_new_tab.py` | `ValenciaEventsNewRepository` | Valencia events |

This is the Valencia events repository, shortened, from `valencia_events_new_tab.py`:

```python
from pathlib import Path
from typing import Any

from src.repositories import BaseRepository
from src.web.dashboard.utils import get_data_path

VALENCIA_EVENTS_FILE = Path(get_data_path("valencia_events", "valencia_events.json"))

class ValenciaEventsNewRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for Valencia events data (new tab)."""

    def __init__(self):
        super().__init__(
            data_path=VALENCIA_EVENTS_FILE,
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        if isinstance(raw_data, list):
            return raw_data
        elif isinstance(raw_data, dict):
            return [raw_data]
        else:
            return []

valencia_events_new_repo = ValenciaEventsNewRepository()

def load_valencia_events() -> list[dict[str, Any]]:
    try:
        return valencia_events_new_repo.get()
    except Exception:
        return []
```

Two components go one step further:

- `knowledge_garden_tab.py` creates one `KnowledgeGardenRepository` for each source in `KNOWLEDGE_SOURCES_CONFIG` (14 instances today), and `_load_all_knowledge_data()` calls `get()` on every one of them.
- `spanish_public_aid_tab.py` passes `force_refresh=True` when its refresh button triggers the table callback, and `shortcuts_tab.py` calls `clear_cache()` on its custom-shortcuts repository after saving the user's edits.

## Adding a repository to a component

1. Subclass `BaseRepository[T]` in the component module and implement `transform_data()`.
2. Create the instance at module level, building the path with `get_data_path()` from `src/web/dashboard/utils.py`.
3. Call `get()` inside a `try`/`except` and fall back to an empty value, so the tab still renders before the ETL has produced its file.

## Defined but not used outside the package

These are complete and exported from `src.repositories`, but nothing outside the package references them today.

- **`DataFrameRepository`** (`BaseRepository[pd.DataFrame]`) turns the file into a pandas DataFrame, fills missing `default_columns` with `None`, and adds `filter()`, `search()`, `sort()`, `get_unique_values()` and `get_summary()`.
- **`RepositoryManager`** holds several repositories by key: `register()`, `unregister()`, `get(key, force_refresh=False)`, `get_all(force_refresh=False)`, `refresh_all()`, `clear_cache_all()`, `get_available_repositories()`, `is_available(key)` and `get_summary_all()`.
- **`AggregatedRepository`** is a `DataFrameRepository` whose `load_data()` concatenates the DataFrames of several repositories and adds a `source` column.
- **`create_courses_repository_manager()`**, **`create_news_repository_manager()`** and **`create_games_repository_manager()`** build a `RepositoryManager` over a fixed list of files (four course files, three news files, two games files). Five of the nine files they read are referenced nowhere else in `src/`.

Right before the September 2026 cleanup, the only consumer of `RepositoryManager` and of the factory functions was the dependency-injection layer (`src/di/service_registry.py`), which no longer exists.

## Caveats

- The `BaseRepository` docstring lists thread-safe operations, but nothing in the package takes a lock. Dash can serve callbacks concurrently, so do not rely on that claim.
- Every live subclass passes `cache_ttl_seconds=3600`, and the cache lives in the dashboard process. The hour is the upper bound: since 2026-11-27 (T-197) the cache also ends when the file on disk is not the one that was read (it keeps the modification time in nanoseconds and the size), so fresh ETL output shows at the next request instead of an hour later. A file that is gone keeps the last copy until the hour is over. `knowledge_garden_tab.py` keeps a second, time-only cache on top of its repositories (`TTLDataCache`, 60 seconds), which is how long a change can take to show there. `tech_radar_tab.py` does not use the pattern: it reads its files with `json.load` under its own `TTLDataCache` (300 seconds).
- `Tests/unit/test_repository_cache.py` covers `get()` and the cache through `BaseRepository` and `DataFrameRepository`. The operations of `DataFrameRepository` (`filter()`, `search()`, `sort()`, `get_unique_values()`, `get_summary()`) and `RepositoryManager` have no tests.
