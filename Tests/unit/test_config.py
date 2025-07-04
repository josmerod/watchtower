#!/usr/bin/env python3

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
try:
    from config.settings import get_settings
    from utils.logging import get_logger

    print("Testing configuration system...")

    # Test settings
    settings = get_settings()
    print(f"Settings loaded: {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Project root: {settings.project_root}")

    # Test logging
    logger = get_logger("test")
    logger.info("Test log message")
    print("Logging system working")

    # Test directory creation
    settings.create_directories()
    print("Directories created")

    print("\nAll configuration tests passed!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
