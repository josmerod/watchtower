"""Enhanced logging utilities for Watchtower with structured logging support."""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _get_settings():
    """Lazy import of settings to avoid circular imports."""
    try:
        from config.settings import get_settings
        return get_settings()
    except ImportError:
        # Fallback for basic logging configuration
        return None


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON.

        Args:
            record: The log record to format.

        Returns:
            Formatted JSON string.
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add process and thread info
        log_data["process_id"] = record.process
        log_data["thread_id"] = record.thread

        return json.dumps(log_data, ensure_ascii=False)


class WatchtowerLogger:
    """Enhanced logger for Watchtower with better configuration and features."""

    _loggers: dict[str, logging.Logger] = {}
    _configured = False

    @classmethod
    def configure_logging(cls, settings=None) -> None:
        """Configure global logging settings.

        Args:
            settings: Optional settings override.
        """
        if cls._configured:
            return

        if settings is None:
            settings = _get_settings()

        # If no settings available, use basic configuration
        if settings is None:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            cls._configured = True
            return

        # Ensure log directory exists
        settings.create_directories()

        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.logging.level.value))

        # Clear existing handlers
        root_logger.handlers.clear()

        # Add console handler if enabled
        if settings.logging.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, settings.logging.level.value))

            if settings.logging.structured:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(
                    logging.Formatter(settings.logging.format)
                )

            root_logger.addHandler(console_handler)

        # Add file handler if enabled
        if settings.logging.file_enabled:
            log_file = Path(settings.logging.file_path) / "watchtower.log"

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=settings.logging.file_max_bytes,
                backupCount=settings.logging.file_backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, settings.logging.level.value))

            if settings.logging.structured:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(settings.logging.format)
                )

            root_logger.addHandler(file_handler)

        cls._configured = True

    @classmethod
    def get_logger(
        cls,
        name: str | None = None,
        extra_fields: dict[str, Any] | None = None
    ) -> logging.Logger:
        """Get a logger with optional extra fields.

        Args:
            name: Logger name. If None, uses the calling module's name.
            extra_fields: Additional fields to include in structured logs.

        Returns:
            Configured logger instance.
        """
        if not cls._configured:
            cls.configure_logging()

        if name is None:
            # Auto-detect caller's module name
            import inspect
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            name = module.__name__ if module else "watchtower"

        # Use cached logger if available
        if name in cls._loggers:
            logger = cls._loggers[name]
        else:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger

        # Add extra fields adapter if provided
        if extra_fields:
            logger = LoggerAdapter(logger, extra_fields)

        return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds extra fields to log records."""

    def __init__(self, logger: logging.Logger, extra_fields: dict[str, Any]):
        """Initialize the adapter.

        Args:
            logger: The base logger.
            extra_fields: Extra fields to add to log records.
        """
        super().__init__(logger, {})
        self.extra_fields = extra_fields

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple:
        """Process the log record to add extra fields.

        Args:
            msg: Log message.
            kwargs: Keyword arguments.

        Returns:
            Processed message and kwargs.
        """
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"]["extra_fields"] = self.extra_fields

        return msg, kwargs


class PerformanceLogger:
    """Logger for performance monitoring."""

    def __init__(self, logger: logging.Logger):
        """Initialize performance logger.

        Args:
            logger: Base logger to use.
        """
        self.logger = logger
        self.start_time = None

    def start(self, operation: str) -> None:
        """Start timing an operation.

        Args:
            operation: Name of the operation being timed.
        """
        self.start_time = datetime.now()
        self.operation = operation
        self.logger.info(f"Starting operation: {operation}")

    def end(self, success: bool = True, extra_data: dict[str, Any] | None = None) -> None:
        """End timing an operation.

        Args:
            success: Whether the operation was successful.
            extra_data: Additional data to log.
        """
        if self.start_time is None:
            self.logger.warning("Performance timer was not started")
            return

        duration = (datetime.now() - self.start_time).total_seconds()

        log_data = {
            "operation": self.operation,
            "duration_seconds": duration,
            "success": success,
        }

        if extra_data:
            log_data.update(extra_data)

        level = logging.INFO if success else logging.ERROR
        self.logger.log(
            level,
            f"Operation {self.operation} completed in {duration:.3f}s",
            extra={"extra_fields": log_data},
        )

        self.start_time = None


def get_logger(
    name: str | None = None,
    extra_fields: dict[str, Any] | None = None
) -> logging.Logger:
    """Get a configured logger instance.

    This is the main function to use for getting loggers in the application.

    Args:
        name: Logger name. If None, auto-detects from calling module.
        extra_fields: Additional fields for structured logging.

    Returns:
        Configured logger instance.
    """
    return WatchtowerLogger.get_logger(name, extra_fields)


def get_performance_logger(name: str | None = None) -> PerformanceLogger:
    """Get a performance logger for timing operations.

    Args:
        name: Logger name. If None, auto-detects from calling module.

    Returns:
        Performance logger instance.
    """
    base_logger = get_logger(name)
    return PerformanceLogger(base_logger)


def configure_logging(settings=None) -> None:
    """Configure global logging settings.

    Args:
        settings: Optional settings override.
    """
    WatchtowerLogger.configure_logging(settings)


def log_function_call(func):
    """Decorator to log function calls with timing.

    Args:
        func: Function to decorate.

    Returns:
        Decorated function.
    """
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        perf_logger = PerformanceLogger(logger)

        func_name = f"{func.__module__}.{func.__name__}"
        perf_logger.start(func_name)

        try:
            result = func(*args, **kwargs)
            perf_logger.end(success=True)
            return result
        except Exception as e:
            perf_logger.end(
                success=False,
                extra_data={"error": str(e), "error_type": type(e).__name__}
            )
            raise

    return wrapper


# Backward compatibility
def get_logger_legacy(name=None) -> logging.Logger:
    """Legacy function for backward compatibility.

    Args:
        name: Logger name.

    Returns:
        Logger instance.
    """
    return get_logger(name)
