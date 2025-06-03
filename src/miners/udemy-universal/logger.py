"""Logging configuration for the Udemy Universal miner.

This module sets up custom logging for the DUCE (Discounted Udemy Course Enroller)
application, providing console and file handlers, debug formatting options,
and a TQDM-compatible handler.
"""
# TODO: Standardize the code with the other projects. Current code has been migrated from other project.


import logging
import os
import sys
from datetime import datetime
from pathlib import Path

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

    def process(self, msg, kwargs):
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
        def emit(self, record):
            try:
                msg = self.format(record)
                # Use tqdm.write which is compatible with tqdm progress bars
                from tqdm import tqdm

                tqdm.write(msg)
            except Exception:
                self.handleError(record)

    handler = TqdmLoggingHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    return handler
