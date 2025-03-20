import os
import logging
from logging.handlers import RotatingFileHandler
import inspect
import datetime

from src.utils.file_system import ensure_directories, get_project_root


def get_logger(name=None):
    """
    Get a logger configured to write to both console and a file.

    Args:
        name (str, optional): Logger name. If None, it will use the calling module's name.

    Returns:
        logging.Logger: Configured logger instance
    """
    if name is None:
        # Get the calling module's name if not provided
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__ if module else "root"

    # Create logger
    logger = logging.getLogger(name)

    # Only configure the logger once
    if not logger.handlers:
        # Get project root and ensure logs directory exists
        project_root = get_project_root()
        logs_dir = os.path.join(project_root, "logs")
        ensure_directories(["logs"])

        logger.setLevel(logging.INFO)

        # Create a formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Create file handler
        # Use the module name to isolate logs by execution class
        module_name = name.split(".")[-1]
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(logs_dir, f"{module_name}_{today}.log")

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
