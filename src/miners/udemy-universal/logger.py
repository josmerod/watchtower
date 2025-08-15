"""Logging configuration for the Udemy Universal miner.

This module sets up custom logging for the DUCE (Discounted Udemy Course Enroller)
application, providing console and file handlers, debug formatting options,
and a TQDM-compatible handler.
"""

# TODO: Standardize the code with the other projects. Current code has been migrated from other project.

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
LOG_DIR = "logs"
LOG_LEVEL = logging.INFO  # Default log level
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEBUG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Ensure log directory exists
Path(LOG_DIR).mkdir(exist_ok=True)

# Generate log filenames
log_date = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(LOG_DIR, f"duce-{log_date}.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, f"duce-errors-{log_date}.log")

# Loggers cache to avoid duplicate handlers
_loggers = {}


def get_logger(name: str, debug: bool = False) -> logging.Logger:
    """Get a properly configured logger by name.

    Args:
        name (str): The logger name (usually __name__ from the calling module)
        debug (bool): Whether to enable debug mode with more verbose output

    Returns:
        logging.Logger: A configured logger instance
    """
    # Return cached logger if it exists
    if name in _loggers:
        return _loggers[name]

    # Set log level based on debug flag
    log_level = logging.DEBUG if debug else LOG_LEVEL

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Prevent adding handlers multiple times
    if logger.handlers:
        return logger

    # Formatter selection based on debug mode
    formatter = logging.Formatter(DEBUG_FORMAT if debug else LOG_FORMAT, DATE_FORMAT)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    logger.addHandler(console_handler)

    # Console handler (stderr) for errors
    error_console_handler = logging.StreamHandler(sys.stderr)
    error_console_handler.setLevel(logging.ERROR)
    error_console_handler.setFormatter(formatter)
    logger.addHandler(error_console_handler)

    # File handler for all logs
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # File handler for error logs only
    error_file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    logger.addHandler(error_file_handler)

    # Cache the configured logger
    _loggers[name] = logger

    return logger


def set_global_log_level(level: int) -> None:
    """Set the log level for all loggers.

    Args:
        level (int): A logging level (e.g., logging.DEBUG, logging.INFO)
    """
    global LOG_LEVEL
    LOG_LEVEL = level

    # Update existing loggers
    for logger_name, logger in _loggers.items():
        logger.setLevel(level)
        for handler in logger.handlers:
            if handler.level < logging.ERROR:  # Don't change error handlers
                handler.setLevel(level)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding context to log messages.
    Usage: logger = LoggerAdapter(get_logger(__name__), {'site': 'example'})
    """

    def process(self, msg, kwargs) -> tuple[str, dict]:
        # Add extra context from self.extra to the message
        context_str = " ".join(
            f"[{k}={v}]" for k, v in self.extra.items() if v is not None
        )
        if context_str:
            msg = f"{msg} {context_str}"
        return msg, kwargs


def get_tqdm_handler():
    """Create a log handler that's compatible with tqdm progress bars.

    Returns:
        TqdmLoggingHandler: A handler that doesn't interfere with tqdm
    """

    class TqdmLoggingHandler(logging.Handler):
        def emit(self, record) -> None:
            try:
                msg = self.format(record)
                # Use tqdm.write which is compatible with tqdm progress bars
                from tqdm import tqdm

                tqdm.write(msg)
            except Exception as e:
                # Log to stderr to avoid recursion
                import sys

                print(f"TqdmLoggingHandler error: {e}", file=sys.stderr)
                self.handleError(record)

    handler = TqdmLoggingHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    return handler


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for detailed logging."""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields if available
        if self.include_extra and hasattr(record, "__dict__"):
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                    "message",
                ]:
                    extra_fields[key] = value

            if extra_fields:
                log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class MetricsLogger:
    """Logger for tracking metrics and performance data."""

    def __init__(self, logger_name: str = "metrics"):
        self.logger = get_logger(logger_name)
        self.metrics: dict[str, Any] = {}
        self.start_times: dict[str, float] = {}

    def start_timer(self, name: str) -> None:
        """Start a timer for measuring duration."""
        import time

        self.start_times[name] = time.time()

    def end_timer(self, name: str) -> float:
        """End a timer and return duration."""
        import time

        if name in self.start_times:
            duration = time.time() - self.start_times[name]
            self.metrics[f"{name}_duration"] = duration
            del self.start_times[name]
            self.logger.info(f"Timer '{name}' completed in {duration:.2f}s")
            return duration
        return 0.0

    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        if name not in self.metrics:
            self.metrics[name] = 0
        self.metrics[name] += value
        self.logger.debug(f"Counter '{name}' incremented to {self.metrics[name]}")

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric."""
        self.metrics[name] = value
        self.logger.debug(f"Gauge '{name}' set to {value}")

    def log_metric(
        self, name: str, value: Any, tags: dict[str, str] | None = None
    ) -> None:
        """Log a custom metric."""
        metric_data = {
            "metric": name,
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        if tags:
            metric_data["tags"] = tags

        self.logger.info(f"Metric: {json.dumps(metric_data)}")

    def get_metrics(self) -> dict[str, Any]:
        """Get all current metrics."""
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.start_times.clear()
        self.logger.info("Metrics reset")


def setup_structured_logging(
    logger_name: str, log_file: str | None = None
) -> logging.Logger:
    """Setup structured JSON logging for a specific logger.

    Args:
        logger_name: Name of the logger
        log_file: Optional log file path

    Returns:
        Configured logger with structured formatting
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)

    return logger


def create_metrics_logger(name: str = "metrics") -> MetricsLogger:
    """Create a metrics logger instance.

    Args:
        name: Logger name

    Returns:
        MetricsLogger instance
    """
    return MetricsLogger(name)


# Global metrics logger instance
metrics_logger = create_metrics_logger()
