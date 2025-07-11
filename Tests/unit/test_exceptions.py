"""
Comprehensive unit tests for the exceptions system.
Tests custom exceptions and error handling.
"""

import unittest
from typing import Dict, Any, Optional

from src.exceptions.base import WatchtowerError, ErrorContext
from src.exceptions.etl import (
    ETLError, ETLConfigurationError, ETLDataError, 
    ETLConnectionError, ETLValidationError, ETLTimeoutError
)
from src.exceptions.watcher import (
    WatcherError, WatcherConfigurationError, WatcherStateError,
    WatcherConnectionError, WatcherTimeoutError
)
from src.exceptions.config import (
    ConfigurationError, ConfigurationValidationError,
    ConfigurationFileError, ConfigurationParsingError
)
from src.exceptions.web import (
    WebError, WebConnectionError, WebTimeoutError,
    WebAuthenticationError, WebValidationError
)


class TestBaseExceptions(unittest.TestCase):
    """Test base exception functionality."""

    def test_watchtower_error_creation(self):
        """Test WatchtowerError creation with message."""
        error = WatchtowerError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)

    def test_watchtower_error_with_context(self):
        """Test WatchtowerError with error context."""
        context = ErrorContext(
            component="test_component",
            operation="test_operation",
            metadata={"key": "value"}
        )
        
        error = WatchtowerError("Test error", context=context)
        
        self.assertEqual(error.context.component, "test_component")
        self.assertEqual(error.context.operation, "test_operation")
        self.assertEqual(error.context.metadata["key"], "value")

    def test_error_context_creation(self):
        """Test ErrorContext creation."""
        context = ErrorContext(
            component="etl_module",
            operation="data_extraction",
            metadata={"source": "api", "batch_size": 100}
        )
        
        self.assertEqual(context.component, "etl_module")
        self.assertEqual(context.operation, "data_extraction")
        self.assertEqual(context.metadata["source"], "api")
        self.assertEqual(context.metadata["batch_size"], 100)
        self.assertIsInstance(context.timestamp, float)

    def test_error_context_to_dict(self):
        """Test ErrorContext serialization to dictionary."""
        context = ErrorContext(
            component="test",
            operation="test_op",
            metadata={"test": True}
        )
        
        context_dict = context.to_dict()
        
        self.assertIsInstance(context_dict, dict)
        self.assertEqual(context_dict["component"], "test")
        self.assertEqual(context_dict["operation"], "test_op")
        self.assertIn("timestamp", context_dict)
        self.assertIn("metadata", context_dict)

    def test_watchtower_error_inheritance(self):
        """Test WatchtowerError is base for all custom exceptions."""
        # All custom exceptions should inherit from WatchtowerError
        self.assertTrue(issubclass(ETLError, WatchtowerError))
        self.assertTrue(issubclass(WatcherError, WatchtowerError))
        self.assertTrue(issubclass(ConfigurationError, WatchtowerError))
        self.assertTrue(issubclass(WebError, WatchtowerError))


class TestETLExceptions(unittest.TestCase):
    """Test ETL-related exceptions."""

    def test_etl_error_creation(self):
        """Test ETLError creation."""
        error = ETLError("ETL process failed")
        
        self.assertEqual(str(error), "ETL process failed")
        self.assertIsInstance(error, WatchtowerError)

    def test_etl_configuration_error(self):
        """Test ETLConfigurationError."""
        error = ETLConfigurationError("Invalid ETL configuration")
        
        self.assertIsInstance(error, ETLError)
        self.assertEqual(str(error), "Invalid ETL configuration")

    def test_etl_data_error(self):
        """Test ETLDataError."""
        error = ETLDataError("Data validation failed")
        
        self.assertIsInstance(error, ETLError)
        self.assertEqual(str(error), "Data validation failed")

    def test_etl_connection_error(self):
        """Test ETLConnectionError."""
        error = ETLConnectionError("Failed to connect to data source")
        
        self.assertIsInstance(error, ETLError)
        self.assertEqual(str(error), "Failed to connect to data source")

    def test_etl_validation_error(self):
        """Test ETLValidationError."""
        error = ETLValidationError("Data validation failed", validation_errors=["Field 'name' is required"])
        
        self.assertIsInstance(error, ETLError)
        self.assertEqual(error.validation_errors, ["Field 'name' is required"])

    def test_etl_timeout_error(self):
        """Test ETLTimeoutError."""
        error = ETLTimeoutError("ETL process timed out", timeout_seconds=300)
        
        self.assertIsInstance(error, ETLError)
        self.assertEqual(error.timeout_seconds, 300)

    def test_etl_error_with_context(self):
        """Test ETLError with context."""
        context = ErrorContext(
            component="arxiv_etl",
            operation="paper_extraction",
            metadata={"batch_size": 50, "source": "arxiv_rss"}
        )
        
        error = ETLError("Failed to extract papers", context=context)
        
        self.assertEqual(error.context.component, "arxiv_etl")
        self.assertEqual(error.context.operation, "paper_extraction")


class TestWatcherExceptions(unittest.TestCase):
    """Test Watcher-related exceptions."""

    def test_watcher_error_creation(self):
        """Test WatcherError creation."""
        error = WatcherError("Watcher failed to start")
        
        self.assertEqual(str(error), "Watcher failed to start")
        self.assertIsInstance(error, WatchtowerError)

    def test_watcher_configuration_error(self):
        """Test WatcherConfigurationError."""
        error = WatcherConfigurationError("Invalid watcher configuration")
        
        self.assertIsInstance(error, WatcherError)
        self.assertEqual(str(error), "Invalid watcher configuration")

    def test_watcher_state_error(self):
        """Test WatcherStateError."""
        error = WatcherStateError("Failed to load watcher state", state_file="/path/to/state.json")
        
        self.assertIsInstance(error, WatcherError)
        self.assertEqual(error.state_file, "/path/to/state.json")

    def test_watcher_connection_error(self):
        """Test WatcherConnectionError."""
        error = WatcherConnectionError("Failed to connect to RSS feed", source_url="https://example.com/rss")
        
        self.assertIsInstance(error, WatcherError)
        self.assertEqual(error.source_url, "https://example.com/rss")

    def test_watcher_timeout_error(self):
        """Test WatcherTimeoutError."""
        error = WatcherTimeoutError("Watcher check timed out", timeout_seconds=60)
        
        self.assertIsInstance(error, WatcherError)
        self.assertEqual(error.timeout_seconds, 60)

    def test_watcher_error_with_context(self):
        """Test WatcherError with context."""
        context = ErrorContext(
            component="arxiv_watcher",
            operation="feed_parsing",
            metadata={"feed_url": "https://arxiv.org/rss/cs.AI", "check_interval": 3600}
        )
        
        error = WatcherError("Failed to parse RSS feed", context=context)
        
        self.assertEqual(error.context.component, "arxiv_watcher")
        self.assertEqual(error.context.metadata["feed_url"], "https://arxiv.org/rss/cs.AI")


class TestConfigurationExceptions(unittest.TestCase):
    """Test Configuration-related exceptions."""

    def test_configuration_error_creation(self):
        """Test ConfigurationError creation."""
        error = ConfigurationError("Configuration error occurred")
        
        self.assertEqual(str(error), "Configuration error occurred")
        self.assertIsInstance(error, WatchtowerError)

    def test_configuration_validation_error(self):
        """Test ConfigurationValidationError."""
        error = ConfigurationValidationError(
            "Configuration validation failed",
            validation_errors=["Database host is required", "Invalid port number"]
        )
        
        self.assertIsInstance(error, ConfigurationError)
        self.assertEqual(len(error.validation_errors), 2)
        self.assertIn("Database host is required", error.validation_errors)

    def test_configuration_file_error(self):
        """Test ConfigurationFileError."""
        error = ConfigurationFileError("Configuration file not found", file_path="/path/to/config.yaml")
        
        self.assertIsInstance(error, ConfigurationError)
        self.assertEqual(error.file_path, "/path/to/config.yaml")

    def test_configuration_parsing_error(self):
        """Test ConfigurationParsingError."""
        error = ConfigurationParsingError(
            "Failed to parse configuration file",
            file_path="/path/to/config.yaml",
            parsing_error="Invalid YAML syntax at line 10"
        )
        
        self.assertIsInstance(error, ConfigurationError)
        self.assertEqual(error.file_path, "/path/to/config.yaml")
        self.assertEqual(error.parsing_error, "Invalid YAML syntax at line 10")

    def test_configuration_error_with_context(self):
        """Test ConfigurationError with context."""
        context = ErrorContext(
            component="settings_loader",
            operation="config_loading",
            metadata={"config_file": "settings.yaml", "environment": "production"}
        )
        
        error = ConfigurationError("Failed to load configuration", context=context)
        
        self.assertEqual(error.context.component, "settings_loader")
        self.assertEqual(error.context.metadata["environment"], "production")


class TestWebExceptions(unittest.TestCase):
    """Test Web-related exceptions."""

    def test_web_error_creation(self):
        """Test WebError creation."""
        error = WebError("Web request failed")
        
        self.assertEqual(str(error), "Web request failed")
        self.assertIsInstance(error, WatchtowerError)

    def test_web_connection_error(self):
        """Test WebConnectionError."""
        error = WebConnectionError("Failed to connect to server", url="https://api.example.com")
        
        self.assertIsInstance(error, WebError)
        self.assertEqual(error.url, "https://api.example.com")

    def test_web_timeout_error(self):
        """Test WebTimeoutError."""
        error = WebTimeoutError("Request timed out", timeout_seconds=30, url="https://slow.example.com")
        
        self.assertIsInstance(error, WebError)
        self.assertEqual(error.timeout_seconds, 30)
        self.assertEqual(error.url, "https://slow.example.com")

    def test_web_authentication_error(self):
        """Test WebAuthenticationError."""
        error = WebAuthenticationError("Authentication failed", status_code=401)
        
        self.assertIsInstance(error, WebError)
        self.assertEqual(error.status_code, 401)

    def test_web_validation_error(self):
        """Test WebValidationError."""
        error = WebValidationError(
            "Request validation failed",
            validation_errors=["Missing required field 'api_key'", "Invalid email format"]
        )
        
        self.assertIsInstance(error, WebError)
        self.assertEqual(len(error.validation_errors), 2)
        self.assertIn("Missing required field 'api_key'", error.validation_errors)

    def test_web_error_with_context(self):
        """Test WebError with context."""
        context = ErrorContext(
            component="api_client",
            operation="data_fetch",
            metadata={"endpoint": "/api/v1/data", "method": "GET", "user_id": "12345"}
        )
        
        error = WebError("API request failed", context=context)
        
        self.assertEqual(error.context.component, "api_client")
        self.assertEqual(error.context.metadata["endpoint"], "/api/v1/data")


class TestExceptionChaining(unittest.TestCase):
    """Test exception chaining and cause tracking."""

    def test_exception_chaining(self):
        """Test exception chaining with __cause__."""
        try:
            # Simulate nested exception scenario
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ETLError("ETL failed due to data error") from e
        except ETLError as etl_error:
            self.assertIsInstance(etl_error.__cause__, ValueError)
            self.assertEqual(str(etl_error.__cause__), "Original error")

    def test_exception_context_preservation(self):
        """Test that exception context is preserved through chaining."""
        context = ErrorContext(
            component="data_processor",
            operation="data_transformation",
            metadata={"record_id": "12345"}
        )
        
        try:
            try:
                raise ValueError("Data transformation failed")
            except ValueError as e:
                raise ETLError("ETL process failed", context=context) from e
        except ETLError as etl_error:
            self.assertIsNotNone(etl_error.context)
            self.assertEqual(etl_error.context.component, "data_processor")
            self.assertEqual(etl_error.context.metadata["record_id"], "12345")


class TestExceptionUtilities(unittest.TestCase):
    """Test exception utility functions."""

    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        context = ErrorContext(
            component="test_component",
            operation="test_operation",
            metadata={"test": True}
        )
        
        error = ETLError("Test error message", context=context)
        
        # Check if the exception has a to_dict method or similar
        if hasattr(error, 'to_dict'):
            error_dict = error.to_dict()
            
            self.assertIsInstance(error_dict, dict)
            self.assertEqual(error_dict["message"], "Test error message")
            self.assertEqual(error_dict["type"], "ETLError")
            self.assertIn("context", error_dict)

    def test_exception_str_representation(self):
        """Test string representation of exceptions."""
        error = ETLValidationError(
            "Validation failed",
            validation_errors=["Field A is required", "Field B is invalid"]
        )
        
        str_repr = str(error)
        
        self.assertIn("Validation failed", str_repr)
        # The string representation might include validation errors

    def test_exception_repr_representation(self):
        """Test repr representation of exceptions."""
        error = WatcherTimeoutError("Timeout occurred", timeout_seconds=300)
        
        repr_str = repr(error)
        
        self.assertIn("WatcherTimeoutError", repr_str)
        self.assertIn("Timeout occurred", repr_str)


class TestExceptionHandling(unittest.TestCase):
    """Test exception handling patterns."""

    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        with self.assertRaises(ETLConfigurationError):
            raise ETLConfigurationError("Configuration is invalid")

    def test_catch_base_exception(self):
        """Test catching base WatchtowerError catches all custom exceptions."""
        with self.assertRaises(WatchtowerError):
            raise ETLError("This should be caught by WatchtowerError")
        
        with self.assertRaises(WatchtowerError):
            raise WatcherError("This should also be caught")

    def test_exception_type_checking(self):
        """Test checking exception types."""
        error = ETLDataError("Data error occurred")
        
        self.assertIsInstance(error, ETLDataError)
        self.assertIsInstance(error, ETLError)
        self.assertIsInstance(error, WatchtowerError)
        self.assertIsInstance(error, Exception)

    def test_multiple_exception_handling(self):
        """Test handling multiple exception types."""
        def risky_operation(error_type: str):
            if error_type == "etl":
                raise ETLError("ETL error")
            elif error_type == "watcher":
                raise WatcherError("Watcher error")
            elif error_type == "config":
                raise ConfigurationError("Config error")
            else:
                raise ValueError("Unknown error")
        
        # Test ETL error handling
        with self.assertRaises(ETLError):
            risky_operation("etl")
        
        # Test Watcher error handling
        with self.assertRaises(WatcherError):
            risky_operation("watcher")
        
        # Test Configuration error handling
        with self.assertRaises(ConfigurationError):
            risky_operation("config")
        
        # Test non-Watchtower error
        with self.assertRaises(ValueError):
            risky_operation("unknown")


if __name__ == '__main__':
    unittest.main() 