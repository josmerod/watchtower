"""Watcher-specific exception classes."""

from __future__ import annotations

from typing import Any

from exceptions.base import WatchtowerError


class WatcherError(WatchtowerError):
    """Base exception for watcher-related errors."""

    def __init__(
        self,
        message: str,
        watcher_name: str | None = None,
        **kwargs,
    ):
        """Initialize watcher error.

        Args:
            message: Error message.
            watcher_name: Name of the watcher that failed.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if watcher_name:
            context["watcher_name"] = watcher_name

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_WATCHER_ERROR")

        super().__init__(message, **kwargs)


class WatcherConfigurationError(WatcherError):
    """Exception raised for watcher configuration errors."""

    def __init__(
        self,
        message: str,
        config_parameter: str | None = None,
        **kwargs,
    ):
        """Initialize watcher configuration error.

        Args:
            message: Error message.
            config_parameter: Configuration parameter that caused the error.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if config_parameter:
            context["config_parameter"] = config_parameter

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_WATCHER_CONFIG_ERROR")

        super().__init__(message, **kwargs)


class WatcherRuntimeError(WatcherError):
    """Exception raised during watcher runtime execution."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        **kwargs,
    ):
        """Initialize watcher runtime error.

        Args:
            message: Error message.
            operation: Watcher operation that failed.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if operation:
            context["operation"] = operation

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_WATCHER_RUNTIME_ERROR")

        super().__init__(message, **kwargs)


class WatcherTimeoutError(WatcherError):
    """Exception raised when watcher operations timeout."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        timeout: int | None = None,
        **kwargs,
    ):
        """Initialize watcher timeout error.

        Args:
            message: Error message.
            url: URL that timed out.
            timeout: Timeout value in seconds.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        if timeout:
            context["timeout"] = timeout

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_WATCHER_TIMEOUT")

        super().__init__(message, **kwargs)

        # Store timeout-specific attributes
        self.url = url
        self.timeout = timeout


class WatcherValidationError(WatcherError):
    """Exception raised when watcher data validation fails."""

    def __init__(
        self,
        message: str,
        value: Any = None,
        expected_type: str | None = None,
        **kwargs,
    ):
        """Initialize watcher validation error.

        Args:
            message: Error message.
            value: The invalid value.
            expected_type: Expected data type.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if value is not None:
            context["value"] = str(value)
        if expected_type:
            context["expected_type"] = expected_type

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_WATCHER_VALIDATION")

        super().__init__(message, **kwargs)

        # Store validation-specific attributes
        self.value = value
        self.expected_type = expected_type


class WatcherConnectionError(WatcherError):
    """Exception raised when watcher cannot connect to target."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        **kwargs,
    ):
        """Initialize watcher connection error.

        Args:
            message: Error message.
            url: URL that failed to connect.
            status_code: HTTP status code if applicable.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        if status_code:
            context["status_code"] = status_code

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_WATCHER_CONNECTION")

        super().__init__(message, **kwargs)

        # Store connection-specific attributes
        self.url = url
        self.status_code = status_code
