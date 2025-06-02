"""Base exception classes for the MEGALITH framework."""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union


class MegalithError(Exception):
    """Base exception class for MEGALITH-related errors.
    
    This is the root exception class for all errors that occur within
    the MEGALITH framework. It provides enhanced error handling with
    context and error codes.
    
    Attributes:
        message: Human-readable error message
        error_code: Optional error code for categorization
        context: Additional context information
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the MEGALITH error.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        error_parts = [self.message]
        
        if self.error_code:
            error_parts.append(f"Error Code: {self.error_code}")
            
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            error_parts.append(f"Context: {context_str}")
            
        return " | ".join(error_parts)
    
    def __repr__(self) -> str:
        """Return detailed representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"context={self.context!r})"
        )


# Alias for backward compatibility with Watchtower codebase
WatchtowerError = MegalithError


class MegalithWarning(UserWarning):
    """Base warning class for MEGALITH warnings."""
    
    def __init__(
        self,
        message: str,
        category: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
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


# Alias for backward compatibility with Watchtower codebase
WatchtowerWarning = MegalithWarning


class ConfigurationError(MegalithError):
    """Raised when there's a configuration-related error."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: The configuration key that caused the error
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
            
        super().__init__(
            message,
            error_code="CONFIG_ERROR",
            context=context,
        )


class ValidationError(MegalithError):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize validation error.
        
        Args:
            message: Error message
            field_name: The field that failed validation
            field_value: The value that failed validation
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get("context", {})
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            context["field_value"] = str(field_value)
            
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            context=context,
        )


class AuthenticationError(MegalithError):
    """Exception raised for authentication-related errors."""
    
    def __init__(self, message: str, **kwargs):
        """Initialize authentication error.
        
        Args:
            message: Error message.
            **kwargs: Additional arguments for base class.
        """
        super().__init__(
            message,
            error_code="AUTH_ERROR",
            context=kwargs.get("context", {}),
        )


class AuthorizationError(MegalithError):
    """Exception raised for authorization-related errors."""
    
    def __init__(self, message: str, required_permission: Optional[str] = None, **kwargs):
        """Initialize authorization error.
        
        Args:
            message: Error message.
            required_permission: Permission that was required.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if required_permission:
            context["required_permission"] = required_permission
            
        super().__init__(
            message,
            error_code="AUTHZ_ERROR",
            context=context,
        )


class ResourceNotFoundError(MegalithError):
    """Exception raised when a resource is not found."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
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
            
        super().__init__(
            message,
            error_code="RESOURCE_NOT_FOUND",
            context=context,
        )


class DependencyError(MegalithError):
    """Exception raised for dependency-related errors."""
    
    def __init__(
        self,
        message: str,
        dependency_name: Optional[str] = None,
        dependency_version: Optional[str] = None,
        **kwargs,
    ):
        """Initialize dependency error.
        
        Args:
            message: Error message.
            dependency_name: Name of the dependency.
            dependency_version: Version of the dependency.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if dependency_name:
            context["dependency_name"] = dependency_name
        if dependency_version:
            context["dependency_version"] = dependency_version
            
        super().__init__(
            message,
            error_code="DEPENDENCY_ERROR",
            context=context,
        )


def handle_exception(
    exception: Exception,
    logger=None,
    reraise: bool = True,
    add_context: Optional[Dict[str, Any]] = None,
) -> Optional[MegalithError]:
    """Handle and optionally convert exceptions to MegalithError.
    
    Args:
        exception: The exception to handle.
        logger: Logger to use for logging the exception.
        reraise: Whether to reraise the exception.
        add_context: Additional context to add to the exception.
        
    Returns:
        MegalithError if not reraising, None otherwise.
        
    Raises:
        The original exception or a MegalithError.
    """
    # Convert to MegalithError if not already
    if isinstance(exception, MegalithError):
        megalith_error = exception
    else:
        megalith_error = MegalithError(
            message=str(exception),
            cause=exception,
            context=add_context or {},
        )
    
    # Add additional context if provided
    if add_context:
        for key, value in add_context.items():
            megalith_error.add_context(key, value)
    
    # Log the exception if logger is provided
    if logger:
        logger.error(
            f"Exception occurred: {megalith_error.message}",
            extra={"extra_fields": megalith_error.to_dict()},
        )
    
    if reraise:
        raise megalith_error
    
    return megalith_error 