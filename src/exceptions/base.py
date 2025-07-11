"""Base exception classes for Watchtower."""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any


class WatchtowerError(Exception):
    """Base exception for all Watchtower errors.

    This provides a rich exception with context information,
    error codes, and structured error data.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
        user_message: str | None = None,
    ):
        """Initialize the exception.

        Args:
            message: Technical error message for developers.
            error_code: Unique error code for this error type.
            context: Additional context about the error.
            cause: The underlying exception that caused this error.
            user_message: User-friendly error message.
        """
        super().__init__(message)

        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.context = context or {}
        self.cause = cause
        self.user_message = user_message or message
        self.timestamp = datetime.utcnow()
        self.traceback_str = traceback.format_exc()

        # Chain the exception if cause is provided
        if cause:
            self.__cause__ = cause

    def _generate_error_code(self) -> str:
        """Generate a default error code based on class name.

        Returns:
            Generated error code.
        """
        return f"WT_{self.__class__.__name__.upper()}"

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary representation.

        Returns:
            Dictionary representation of the exception.
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "exception_type": self.__class__.__name__,
            "traceback": self.traceback_str,
            "cause": str(self.cause) if self.cause else None,
        }

    def add_context(self, key: str, value: Any) -> WatchtowerError:
        """Add context information to the exception.

        Args:
            key: Context key.
            value: Context value.

        Returns:
            Self for method chaining.
        """
        self.context[key] = value
        return self

    def with_user_message(self, message: str) -> WatchtowerError:
        """Set a user-friendly message.

        Args:
            message: User-friendly error message.

        Returns:
            Self for method chaining.
        """
        self.user_message = message
        return self


class WatchtowerWarning(UserWarning):
    """Base warning class for Watchtower warnings."""

    def __init__(
        self,
        message: str,
        category: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize the warning.

        Args:
            message: Warning message.
            category: Warning category.
            context: Additional context.
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.context = context or {}
        self.timestamp = datetime.utcnow()


class ConfigurationError(WatchtowerError):
    """Exception raised for configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_value: Any | None = None,
        **kwargs,
    ):
        """Initialize configuration error.

        Args:
            message: Error message.
            config_key: Configuration key that caused the error.
            config_value: Configuration value that caused the error.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        if config_value is not None:
            context["config_value"] = str(config_value)

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_CONFIG_ERROR")

        super().__init__(message, **kwargs)


class ValidationError(WatchtowerError):
    """Exception raised for data validation errors."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        field_value: Any | None = None,
        validation_rule: str | None = None,
        **kwargs,
    ):
        """Initialize validation error.

        Args:
            message: Error message.
            field_name: Name of the field that failed validation.
            field_value: Value that failed validation.
            validation_rule: Validation rule that was violated.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            context["field_value"] = str(field_value)
        if validation_rule:
            context["validation_rule"] = validation_rule

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_VALIDATION_ERROR")

        super().__init__(message, **kwargs)


class AuthenticationError(WatchtowerError):
    """Exception raised for authentication-related errors."""

    def __init__(self, message: str, **kwargs):
        """Initialize authentication error.

        Args:
            message: Error message.
            **kwargs: Additional arguments for base class.
        """
        kwargs["error_code"] = kwargs.get("error_code", "WT_AUTH_ERROR")
        kwargs["user_message"] = "Authentication failed. Please check your credentials."
        super().__init__(message, **kwargs)


class AuthorizationError(WatchtowerError):
    """Exception raised for authorization-related errors."""

    def __init__(
        self, message: str, required_permission: str | None = None, **kwargs
    ):
        """Initialize authorization error.

        Args:
            message: Error message.
            required_permission: Permission that was required.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if required_permission:
            context["required_permission"] = required_permission

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_AUTHZ_ERROR")
        kwargs["user_message"] = "You don't have permission to perform this action."
        super().__init__(message, **kwargs)


class ResourceNotFoundError(WatchtowerError):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        **kwargs,
    ):
        """Initialize resource not found error.

        Args:
            message: Error message.
            resource_type: Type of resource that was not found.
            resource_id: ID of the resource that was not found.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if resource_type:
            context["resource_type"] = resource_type
        if resource_id:
            context["resource_id"] = resource_id

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_RESOURCE_NOT_FOUND")
        kwargs["user_message"] = (
            f"The requested {resource_type or 'resource'} was not found."
        )
        super().__init__(message, **kwargs)


class DependencyError(WatchtowerError):
    """Exception raised for dependency-related errors."""

    def __init__(
        self,
        message: str,
        dependency_name: str | None = None,
        dependency_version: str | None = None,
        **kwargs,
    ):
        """Initialize dependency error.

        Args:
            message: Error message.
            dependency_name: Name of the missing/incompatible dependency.
            dependency_version: Required version of the dependency.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if dependency_name:
            context["dependency_name"] = dependency_name
        if dependency_version:
            context["dependency_version"] = dependency_version

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_DEPENDENCY_ERROR")
        super().__init__(message, **kwargs)


def handle_exception(
    exception: Exception,
    logger=None,
    reraise: bool = True,
    add_context: dict[str, Any] | None = None,
) -> WatchtowerError | None:
    """Handle and optionally convert exceptions to WatchtowerError.

    Args:
        exception: The exception to handle.
        logger: Logger to use for logging the exception.
        reraise: Whether to reraise the exception.
        add_context: Additional context to add to the exception.

    Returns:
        WatchtowerError if not reraising, None otherwise.

    Raises:
        The original exception or a WatchtowerError.
    """
    # Convert to WatchtowerError if not already
    if isinstance(exception, WatchtowerError):
        watchtower_error = exception
    else:
        watchtower_error = WatchtowerError(
            message=str(exception),
            cause=exception,
            context=add_context or {},
        )

    # Add additional context if provided
    if add_context:
        for key, value in add_context.items():
            watchtower_error.add_context(key, value)

    # Log the exception if logger is provided
    if logger:
        logger.error(
            f"Exception occurred: {watchtower_error.message}",
            extra={"extra_fields": watchtower_error.to_dict()},
        )

    if reraise:
        raise watchtower_error

    return watchtower_error
