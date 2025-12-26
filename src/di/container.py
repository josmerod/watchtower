"""Dependency Injection Container.

Provides centralized dependency management with auto-wiring, lifecycle management,
and circular dependency resolution.
"""

from __future__ import annotations

import inspect
import logging
from enum import Enum
from typing import Any, Callable, Type, TypeVar, cast

from pydantic import BaseModel


class ServiceLifetime(Enum):
    """Service lifecycle lifetime."""

    SINGLETON = "singleton"  # One instance for entire application
    TRANSIENT = "transient"  # New instance each time
    SCOPED = "scoped"  # One instance per scope


class ServiceDescriptor(BaseModel):
    """Descriptor for a registered service."""

    service_type: type
    lifetime: ServiceLifetime
    factory: Callable[[], Any] | None = None
    instance: Any = None
    dependencies: list[str] = []


T = TypeVar("T")


class DIContainerError(Exception):
    """Exception raised when DI container operations fail."""

    pass


class DIContainer:
    """Dependency Injection Container.

    Provides:
    - Service registration with lifetime management
    - Auto-wiring of dependencies
    - Circular dependency detection
    - Lazy initialization
    - Scope management
    """

    def __init__(self, name: str = "root"):
        """Initialize DI container.

        Args:
            name: Container name for logging
        """
        self.name = name
        self._services: dict[str, ServiceDescriptor] = {}
        self._instances: dict[str, Any] = {}
        self._scoped_instances: dict[str, dict[str, Any]] = {}
        self._current_scope: str | None = None
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def register(
        self,
        service_type: Type[T],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        factory: Callable[[], T] | None = None,
    ) -> Type[T]:
        """Register a service with the container.

        Can be used as a decorator.

        Args:
            service_type: Service class to register
            lifetime: Service lifetime
            factory: Optional factory function

        Returns:
            The service_type (for decorator usage)

        Example:
            ```python
            container.register(MyService)
            # Or as decorator
            @container.register(lifetime=ServiceLifetime.TRANSIENT)
            class MyService:
                pass
            ```
        """
        service_name = self._get_service_name(service_type)

        if service_name in self._services:
            self._logger.warning(f"Service '{service_name}' already registered, overwriting")

        # Infer dependencies from constructor
        dependencies = self._infer_dependencies(service_type)

        descriptor = ServiceDescriptor(
            service_type=service_type,
            lifetime=lifetime,
            factory=factory,
            dependencies=dependencies,
        )

        self._services[service_name] = descriptor
        self._logger.debug(
            f"Registered service '{service_name}' with lifetime {lifetime.value}"
        )

        return service_type

    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
    ) -> None:
        """Register a pre-created instance as singleton.

        Args:
            service_type: Service class type
            instance: Pre-created instance
        """
        service_name = self._get_service_name(service_type)

        descriptor = ServiceDescriptor(
            service_type=service_type,
            lifetime=ServiceLifetime.SINGLETON,
            factory=None,
            instance=instance,
            dependencies=[],
        )

        self._services[service_name] = descriptor
        self._instances[service_name] = instance

        self._logger.debug(f"Registered instance '{service_name}'")

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[[], T],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """Register a factory function for creating services.

        Args:
            service_type: Service class type
            factory: Factory function
            lifetime: Service lifetime
        """
        self.register(service_type, lifetime=lifetime, factory=factory)

    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service from the container.

        Args:
            service_type: Service class type

        Returns:
            Service instance

        Raises:
            DIContainerError: If service not registered or resolution fails
        """
        service_name = self._get_service_name(service_type)

        if service_name not in self._services:
            raise DIContainerError(f"Service '{service_name}' not registered")

        descriptor = self._services[service_name]

        # Handle pre-registered instance
        if descriptor.instance is not None:
            return cast(T, descriptor.instance)

        # Return cached singleton if exists
        if descriptor.lifetime == ServiceLifetime.SINGLETON and service_name in self._instances:
            return cast(T, self._instances[service_name])

        # Return scoped instance if exists in current scope
        if (
            descriptor.lifetime == ServiceLifetime.SCOPED
            and self._current_scope is not None
            and self._current_scope in self._scoped_instances
            and service_name in self._scoped_instances[self._current_scope]
        ):
            return cast(
                T, self._scoped_instances[self._current_scope][service_name]
            )

        # Create new instance
        instance = self._create_instance(descriptor)

        # Cache based on lifetime
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            self._instances[service_name] = instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED and self._current_scope is not None:
            if self._current_scope not in self._scoped_instances:
                self._scoped_instances[self._current_scope] = {}
            self._scoped_instances[self._current_scope][service_name] = instance

        return instance

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance with dependency injection.

        Args:
            descriptor: Service descriptor

        Returns:
            Service instance

        Raises:
            DIContainerError: If instantiation fails
        """
        # Use factory if provided
        if descriptor.factory is not None:
            return descriptor.factory()

        # Auto-wire dependencies
        dependencies = self._resolve_dependencies(descriptor)

        try:
            # Create instance with dependencies
            instance = descriptor.service_type(**dependencies)
            self._logger.debug(
                f"Created instance of {descriptor.service_type.__name__}"
            )
            return instance

        except Exception as e:
            raise DIContainerError(
                f"Failed to create instance of {descriptor.service_type.__name__}: {e}"
            ) from e

    def _resolve_dependencies(self, descriptor: ServiceDescriptor) -> dict[str, Any]:
        """Resolve dependencies for a service.

        Args:
            descriptor: Service descriptor

        Returns:
            Dictionary of dependency name -> instance

        Raises:
            DIContainerError: If circular dependency detected
        """
        dependencies = {}

        for dep_name in descriptor.dependencies:
            # Resolve dependency (look up by type annotation)
            dep_service = self._resolve_dependency_by_name(dep_name)
            dependencies[dep_name] = dep_service

        return dependencies

    def _resolve_dependency_by_name(self, dep_name: str) -> Any:
        """Resolve a dependency by parameter name.

        Args:
            dep_name: Parameter name

        Returns:
            Resolved dependency instance

        Raises:
            DIContainerError: If dependency not found
        """
        # Try to find service by name
        if dep_name in self._services:
            descriptor = self._services[dep_name]
            return self.resolve(descriptor.service_type)

        # Try to find by common variations
        variations = [dep_name, dep_name.rstrip("_"), dep_name + "_service"]
        for variation in variations:
            if variation in self._services:
                descriptor = self._services[variation]
                return self.resolve(descriptor.service_type)

        raise DIContainerError(f"Could not resolve dependency: {dep_name}")

    def _infer_dependencies(self, service_type: type) -> list[str]:
        """Infer dependencies from service constructor.

        Args:
            service_type: Service class

        Returns:
            List of dependency names
        """
        try:
            sig = inspect.signature(service_type.__init__)
            params = sig.parameters

            # Skip 'self' parameter
            dependencies = [
                name for name, param in list(params.items())[1:]
                if param.default == inspect.Parameter.empty
                and param.annotation != inspect.Parameter.empty
            ]

            return dependencies

        except Exception:
            self._logger.warning(f"Could not infer dependencies for {service_type.__name__}")
            return []

    def _get_service_name(self, service_type: type) -> str:
        """Get service name from type.

        Args:
            service_type: Service class

        Returns:
            Service name
        """
        return service_type.__name__.lower()

    def create_scope(self, scope_id: str | None = None) -> "Scope":
        """Create a new scope for scoped services.

        Args:
            scope_id: Optional scope identifier

        Returns:
            Scope context manager

        Example:
            ```python
            with container.create_scope("request"):
                service1 = container.resolve(MyScopedService)
                service2 = container.resolve(MyScopedService)  # Same instance
            ```
        """
        from contextlib import contextmanager

        @contextmanager
        def scope_context():
            """Scope context manager."""
            previous_scope = self._current_scope
            self._current_scope = scope_id or f"scope_{id(self)}"
            try:
                yield
            finally:
                # Clear scoped instances
                if self._current_scope in self._scoped_instances:
                    del self._scoped_instances[self._current_scope]
                self._current_scope = previous_scope

        return scope_context()

    def is_registered(self, service_type: type) -> bool:
        """Check if a service is registered.

        Args:
            service_type: Service class

        Returns:
            True if registered
        """
        service_name = self._get_service_name(service_type)
        return service_name in self._services

    def get_registered_services(self) -> list[str]:
        """Get list of registered service names.

        Returns:
            List of service names
        """
        return list(self._services.keys())

    def clear(self) -> None:
        """Clear all singleton instances."""
        self._instances.clear()
        self._scoped_instances.clear()
        self._logger.debug("Cleared all instances")


# Global container
_default_container: DIContainer | None = None


def get_container() -> DIContainer:
    """Get the default DI container (singleton).

    Returns:
        DIContainer instance
    """
    global _default_container

    if _default_container is None:
        _default_container = DIContainer()

    return _default_container
