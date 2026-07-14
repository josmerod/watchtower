"""Repository pattern implementation for data access layer."""

from src.repositories.base_repository import (
    BaseRepository,
    CacheEntry,
    DataFrameRepository,
    RepositoryError,
)
from src.repositories.repository_manager import (
    AggregatedRepository,
    RepositoryManager,
    create_courses_repository_manager,
    create_games_repository_manager,
    create_news_repository_manager,
)

__all__ = [
    "AggregatedRepository",
    # Base
    "BaseRepository",
    "CacheEntry",
    "DataFrameRepository",
    "RepositoryError",
    # Manager
    "RepositoryManager",
    # Factories
    "create_courses_repository_manager",
    "create_games_repository_manager",
    "create_news_repository_manager",
]
