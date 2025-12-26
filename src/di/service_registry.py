"""Service Registry - Common service registrations.

Registers core services with the DI container.
"""

from src.di.container import DIContainer, ServiceLifetime, get_container


def register_core_services(container: DIContainer | None = None) -> DIContainer:
    """Register core application services.

    Args:
        container: DI container (uses default if None)

    Returns:
        Configured container

    Example:
        ```python
        container = register_core_services()
        etl_factory = container.resolve(ETLFactory)
        ```
    """
    if container is None:
        container = get_container()

    # Register ETL Factory as singleton
    try:
        from src.etl.factory.etl_factory import ETLFactory

        container.register(
            ETLFactory,
            lifetime=ServiceLifetime.SINGLETON,
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register ETLFactory: {e}")

    # Register Scraper Manager as singleton
    try:
        from src.scraping.scraper_manager import ScraperManager

        container.register(
            ScraperManager,
            lifetime=ServiceLifetime.SINGLETON,
        )
    except Exception as e:
        import logging

        logging.warning(f"Failed to register ScraperManager: {e}")

    # Register Repository Managers as singletons
    try:
        from src.repositories.repository_manager import (
            RepositoryManager,
            create_courses_repository_manager,
            create_news_repository_manager,
            create_games_repository_manager,
        )

        # Register factory function
        container.register_factory(
            RepositoryManager,
            factory=create_courses_repository_manager,
            lifetime=ServiceLifetime.SINGLETON,
        )

    except Exception as e:
        import logging

        logging.warning(f"Failed to register RepositoryManager: {e}")

    # Register configuration service
    try:
        from src.config.settings import get_settings

        container.register_instance(
            type(get_settings()),
            get_settings(),
        )

    except Exception as e:
        import logging

        logging.warning(f"Failed to register settings: {e}")

    return container


def register_etl_services(container: DIContainer) -> None:
    """Register ETL-specific services.

    Args:
        container: DI container
    """
    # Register logger service
    import logging

    class LoggerService:
        """Service for providing loggers."""

        def get_logger(self, name: str) -> logging.Logger:
            return logging.getLogger(name)

    container.register(
        LoggerService,
        lifetime=ServiceLifetime.SINGLETON,
    )


def auto_register_containers() -> None:
    """Auto-register all services with default container.

    Called during application initialization.
    """
    container = get_container()
    register_core_services(container)
    register_etl_services(container)


# Auto-register on import
auto_register_containers()
