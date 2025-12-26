"""ETL Factory for dynamic ETL instantiation.

Implements Factory pattern for creating ETL instances with dependency injection
and configuration management.
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any, Callable, TypeVar

from src.config.settings import get_settings
from src.etl.base import BaseETL, SimpleETL

# Type variable for ETL classes
T = TypeVar("T", bound=BaseETL)


class ETLFactoryError(Exception):
    """Exception raised when ETL factory operations fail."""

    pass


class ETLRegistry:
    """Registry for ETL classes and their metadata.

    Maintains a mapping of ETL names to their corresponding classes
    and configuration requirements.
    """

    def __init__(self) -> None:
        self._etls: dict[str, type[BaseETL]] = {}
        self._configs: dict[str, dict[str, Any]] = {}
        self._dependencies: dict[str, dict[str, str]] = {}

    def register(
        self,
        name: str,
        etl_class: type[BaseETL],
        config: dict[str, Any] | None = None,
        dependencies: dict[str, str] | None = None,
    ) -> None:
        """Register an ETL class with the factory.

        Args:
            name: Unique identifier for the ETL
            etl_class: ETL class to register
            config: Default configuration for the ETL
            dependencies: Dependency mapping for injection

        Raises:
            ETLFactoryError: If ETL already registered or class invalid
        """
        if name in self._etls:
            raise ETLFactoryError(f"ETL '{name}' already registered")

        if not issubclass(etl_class, BaseETL):
            raise ETLFactoryError(f"ETL class must inherit from BaseETL")

        self._etls[name] = etl_class
        self._configs[name] = config or {}
        self._dependencies[name] = dependencies or {}

        logging.debug(f"Registered ETL: {name} -> {etl_class.__name__}")

    def unregister(self, name: str) -> None:
        """Remove an ETL from the registry.

        Args:
            name: ETL identifier to unregister
        """
        self._etls.pop(name, None)
        self._configs.pop(name, None)
        self._dependencies.pop(name, None)

        logging.debug(f"Unregistered ETL: {name}")

    def get(self, name: str) -> type[BaseETL] | None:
        """Get ETL class by name.

        Args:
            name: ETL identifier

        Returns:
            ETL class or None if not found
        """
        return self._etls.get(name)

    def list_registered(self) -> list[str]:
        """List all registered ETL names.

        Returns:
            List of ETL identifiers
        """
        return list(self._etls.keys())

    @property
    def etl_classes(self) -> dict[str, type[BaseETL]]:
        """Get all registered ETL classes."""
        return self._etls.copy()

    @property
    def configs(self) -> dict[str, dict[str, Any]]:
        """Get all default configurations."""
        return self._configs.copy()

    @property
    def dependencies(self) -> dict[str, dict[str, str]]:
        """Get all dependency mappings."""
        return self._dependencies.copy()


class ETLFactory:
    """Factory for creating ETL instances with dependency injection.

    Implements the Factory pattern to decouple ETL creation from usage.
    Supports:
    - Dynamic ETL instantiation by name
    - Configuration injection
    - Dependency resolution
    - Singleton instances (optional)
    """

    _registry: ETLRegistry | None = None
    _singletons: dict[str, BaseETL] = {}

    @classmethod
    def get_registry(cls) -> ETLRegistry:
        """Get the global ETL registry.

        Returns:
            ETLRegistry instance
        """
        if cls._registry is None:
            cls._registry = ETLRegistry()
            cls._register_default_etls()

        return cls._registry

    @classmethod
    def _register_default_etls(cls) -> None:
        """Register default ETLs from the codebase.

        Auto-discovers and registers common ETLs.
        """
        registry = cls.get_registry()

        # Auto-register commonly used ETLs
        # This is a placeholder - actual registration happens via @register_etl decorator
        # or explicit calls to register()
        pass

    @classmethod
    def register(
        cls,
        name: str,
        etl_class: type[BaseETL],
        config: dict[str, Any] | None = None,
        dependencies: dict[str, str] | None = None,
    ) -> None:
        """Register an ETL with the factory.

        Args:
            name: Unique ETL identifier
            etl_class: ETL class (must inherit from BaseETL)
            config: Default configuration
            dependencies: Dependency mapping for injection
        """
        cls.get_registry().register(name, etl_class, config, dependencies)

    @classmethod
    def create(
        cls,
        name: str,
        config: dict[str, Any] | None = None,
        use_singleton: bool = False,
        **kwargs: Any,
    ) -> BaseETL:
        """Create an ETL instance.

        Args:
            name: ETL identifier
            config: Configuration override (merged with defaults)
            use_singleton: Return singleton instance if exists
            **kwargs: Additional arguments passed to ETL constructor

        Returns:
            ETL instance

        Raises:
            ETLFactoryError: If ETL not registered or instantiation fails
        """
        registry = cls.get_registry()

        # Check for singleton
        if use_singleton and name in cls._singletons:
            return cls._singletons[name]

        # Get ETL class
        etl_class = registry.get(name)
        if etl_class is None:
            raise ETLFactoryError(f"ETL '{name}' not registered")

        # Merge configurations
        default_config = registry.configs.get(name, {})
        merged_config = {**default_config, **(config or {}), **kwargs}

        try:
            # Resolve dependencies
            resolved_deps = cls._resolve_dependencies(
                registry.dependencies.get(name, {}),
                merged_config,
            )

            # Create instance with resolved dependencies
            instance = etl_class(**{**merged_config, **resolved_deps})

            # Store singleton if requested
            if use_singleton:
                cls._singletons[name] = instance

            logging.info(f"Created ETL instance: {name} -> {etl_class.__name__}")
            return instance

        except Exception as e:
            raise ETLFactoryError(f"Failed to create ETL '{name}': {e}") from e

    @classmethod
    def _resolve_dependencies(
        cls,
        dependencies: dict[str, str],
        config: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve dependency injections.

        Args:
            dependencies: Dependency mapping (param_name -> dependency_key)
            config: Current configuration

        Returns:
            Resolved dependencies dictionary
        """
        resolved: dict[str, Any] = {}

        for param_name, dep_key in dependencies.items():
            if dep_key == "settings":
                resolved[param_name] = get_settings()
            elif dep_key == "logger":
                resolved[param_name] = logging.getLogger(param_name)
            elif dep_key in config:
                resolved[param_name] = config[dep_key]
            else:
                logging.warning(f"Could not resolve dependency: {param_name} -> {dep_key}")

        return resolved

    @classmethod
    def create_batch(
        cls,
        etl_configs: list[dict[str, Any]],
        use_singletons: bool = False,
    ) -> dict[str, BaseETL]:
        """Create multiple ETL instances in batch.

        Args:
            etl_configs: List of config dicts with 'name' and optional 'config'
            use_singletons: Use singleton pattern

        Returns:
            Dictionary mapping ETL names to instances
        """
        instances: dict[str, BaseETL] = {}

        for etl_config in etl_configs:
            name = etl_config.get("name")
            if not name:
                continue

            config = etl_config.get("config")
            instances[name] = cls.create(name, config, use_singletons)

        return instances

    @classmethod
    def list_etls(cls) -> list[str]:
        """List all registered ETL names.

        Returns:
            List of ETL identifiers
        """
        return cls.get_registry().list_registered()

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an ETL is registered.

        Args:
            name: ETL identifier

        Returns:
            True if registered
        """
        return cls.get_registry().get(name) is not None

    @classmethod
    def clear_singletons(cls) -> None:
        """Clear all singleton instances."""
        cls._singletons.clear()
        logging.debug("Cleared all singleton ETL instances")


def register_etl(
    name: str,
    config: dict[str, Any] | None = None,
    dependencies: dict[str, str] | None = None,
) -> Callable[[type[T]], type[T]]:
    """Decorator to register an ETL class with the factory.

    Usage:
        @register_etl("arxiv", {"batch_size": 20})
        class ArxivETL(BaseETL):
            pass

    Args:
        name: ETL identifier
        config: Default configuration
        dependencies: Dependency mapping

    Returns:
        Decorator function
    """

    def decorator(etl_class: type[T]) -> type[T]:
        ETLFactory.register(name, etl_class, config, dependencies)
        return etl_class

    return decorator
