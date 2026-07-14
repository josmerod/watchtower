"""Dependency Injection module.

Provides DI container and service registration.
"""

from src.di.container import DIContainer, DIContainerError, ServiceLifetime, get_container
from src.di.service_registry import (
    auto_register_containers,
    register_core_services,
    register_etl_services,
)

__all__ = [
    # Container
    "DIContainer",
    "DIContainerError",
    "ServiceLifetime",
    "auto_register_containers",
    "get_container",
    # Registration
    "register_core_services",
    "register_etl_services",
]
