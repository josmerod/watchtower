#!/usr/bin/env python3
"""Basic test script for core Watchtower features."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_configuration():
    """Test configuration system."""
    print("Testing Configuration System...")
    try:
        from src.config.settings import get_settings
        
        settings = get_settings()
        print(f"Settings loaded: {settings.app_name} v{settings.app_version}")
        print(f"Environment: {settings.environment}")
        print(f"Project root: {settings.project_root}")
        return True
    except Exception as e:
        print(f"Configuration error: {e}")
        return False

def test_logging():
    """Test logging system."""
    print("\nTesting Logging System...")
    try:
        from src.utils.logging import get_logger
        
        logger = get_logger("test_basic")
        logger.info("Test log message from basic features")
        print("Basic logging working")
        return True
    except Exception as e:
        print(f"Logging error: {e}")
        return False

def test_exceptions():
    """Test exception handling."""
    print("\nTesting Exception Handling...")
    try:
        from src.exceptions.base import WatchtowerError
        from src.exceptions.watcher import WatcherTimeoutError
        
        # Test basic exception
        try:
            raise WatchtowerError(
                message="Test error",
                error_code="TEST_ERROR",
                context={"test": "context"}
            )
        except WatchtowerError as e:
            print(f"Basic exception handling: {e.error_code}")
        
        print("Exception handling working")
        return True
    except Exception as e:
        print(f"Exception handling error: {e}")
        return False

def test_data_models():
    """Test data models."""
    print("\nTesting Data Models...")
    try:
        from src.models.base import TimestampedModel
        
        model = TimestampedModel()
        print(f"Timestamped model created with ID: {model.id}")
        return True
    except Exception as e:
        print(f"Data models error: {e}")
        return False

def test_file_system():
    """Test file system utilities."""
    print("\nTesting File System Utilities...")
    try:
        from src.utils.file_system import get_file_system_manager
        
        fs_manager = get_file_system_manager()
        print(f"File system manager initialized: {fs_manager.project_root}")
        
        # Test directory creation
        test_dir = "data/test_basic"
        dir_info = fs_manager.ensure_directory(test_dir)
        print(f"Directory created: {dir_info.path}")
        return True
    except Exception as e:
        print(f"File system error: {e}")
        return False

def main():
    """Run all tests."""
    print("Basic Features Test Suite")
    print("=" * 40)
    
    tests = [
        test_configuration,
        test_logging,
        test_exceptions,
        test_data_models,
        test_file_system,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("PASSED")
            else:
                failed += 1
                print("FAILED")
        except Exception as e:
            failed += 1
            print(f"ERROR: {e}")
        print("-" * 40)
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("All basic features tests passed!")

if __name__ == "__main__":
    main() 