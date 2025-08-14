"""
Comprehensive unit tests for the configuration system.
Tests both settings.py and models.py functionality.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, Any

import pytest
from pydantic import ValidationError

from src.config.settings import Settings, get_settings
from src.config.models import (
    DatabaseConfig,
    ETLConfig,
    LoggingConfig,
    StreamlitConfig,
    SecurityConfig,
    APIConfig,
    WatcherConfig,
    ScrapingConfig,
    MonitoringConfig,
    NotificationConfig,
    GoogleDriveConfig,
)


class TestConfigurationModels(unittest.TestCase):
    """Test all configuration model classes."""

    def test_database_config_default_values(self):
        """Test DatabaseConfig with default values."""
        config = DatabaseConfig()

        self.assertEqual(config.url, "sqlite:///watchtower.db")
        self.assertFalse(config.echo)
        self.assertEqual(config.pool_size, 5)
        self.assertEqual(config.max_overflow, 10)

    def test_database_config_custom_values(self):
        """Test DatabaseConfig with custom values."""
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/testdb",
            echo=True,
            pool_size=10,
            max_overflow=20,
        )

        self.assertEqual(config.url, "postgresql://user:pass@localhost:5432/testdb")
        self.assertTrue(config.echo)
        self.assertEqual(config.pool_size, 10)
        self.assertEqual(config.max_overflow, 20)

    def test_etl_config_default_values(self):
        """Test ETLConfig with default values."""
        config = ETLConfig()

        self.assertEqual(config.batch_size, 1000)
        self.assertEqual(config.max_workers, 4)
        self.assertTrue(config.checkpoint_enabled)

    def test_google_drive_config_validation(self):
        """Test GoogleDriveConfig validation."""
        # Test valid configuration
        config = GoogleDriveConfig(
            credentials_file="/path/to/credentials.json",
            backup_folder_id="test_folder_id",
        )

        self.assertEqual(config.credentials_file, "/path/to/credentials.json")
        self.assertEqual(config.backup_folder_id, "test_folder_id")
        self.assertEqual(config.retention_days, 30)
        self.assertEqual(config.max_backup_size_mb, 100)

    def test_logging_config_levels(self):
        """Test LoggingConfig with different log levels."""
        config = LoggingConfig(level="DEBUG")
        self.assertEqual(config.level, "DEBUG")

        config = LoggingConfig(level="ERROR")
        self.assertEqual(config.level, "ERROR")

    def test_streamlit_config_default_values(self):
        """Test StreamlitConfig with default values."""
        config = StreamlitConfig()

        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 8501)
        self.assertFalse(config.debug)
        self.assertEqual(config.theme, "light")
        self.assertEqual(config.cache_ttl, 3600)

    def test_cache_config_validation(self):
        """Test CacheConfig validation."""
        config = CacheConfig(ttl=7200, max_size=1024, cleanup_interval=3600)

        self.assertEqual(config.ttl, 7200)
        self.assertEqual(config.max_size, 1024)
        self.assertEqual(config.cleanup_interval, 3600)

    def test_security_config_defaults(self):
        """Test SecurityConfig with default values."""
        config = SecurityConfig()

        self.assertEqual(config.rate_limit_per_minute, 60)
        self.assertEqual(config.max_request_size_mb, 10)
        self.assertTrue(config.enable_cors)
        self.assertEqual(config.session_timeout_minutes, 30)

    def test_api_keys_config_empty_defaults(self):
        """Test APIKeysConfig with empty defaults."""
        config = APIKeysConfig()

        self.assertIsNone(config.openai_api_key)
        self.assertIsNone(config.github_token)
        self.assertIsNone(config.news_api_key)
        self.assertIsNone(config.google_api_key)

    def test_project_structure_config_paths(self):
        """Test ProjectStructureConfig path handling."""
        config = ProjectStructureConfig(
            data_dir="custom_data",
            logs_dir="custom_logs",
            config_dir="custom_config",
            temp_dir="custom_temp",
        )

        self.assertEqual(config.data_dir, "custom_data")
        self.assertEqual(config.logs_dir, "custom_logs")
        self.assertEqual(config.config_dir, "custom_config")
        self.assertEqual(config.temp_dir, "custom_temp")

    def test_performance_config_defaults(self):
        """Test PerformanceConfig with default values."""
        config = PerformanceConfig()

        self.assertEqual(config.max_concurrent_requests, 10)
        self.assertEqual(config.request_timeout, 30)
        self.assertEqual(config.connection_pool_size, 100)
        self.assertEqual(config.max_retries, 3)


class TestSettings(unittest.TestCase):
    """Test the main Settings class and get_settings function."""

    def setUp(self):
        """Set up test environment."""
        # Clear the lru_cache for get_settings
        get_settings.cache_clear()

        # Create a temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_project_root = self.test_dir / "test_project"
        self.test_project_root.mkdir(parents=True, exist_ok=True)

        # Create pyproject.toml to simulate project root discovery
        pyproject_content = """[tool.watchtower]
name = "test-project"
"""
        (self.test_project_root / "pyproject.toml").write_text(pyproject_content)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)
        get_settings.cache_clear()

    @patch.dict("os.environ", {}, clear=True)
    def test_settings_default_values(self):
        """Test Settings with default values."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        self.assertEqual(settings.project_root, str(self.test_project_root))
        self.assertEqual(settings.environment, "development")
        self.assertFalse(settings.debug)
        self.assertIsInstance(settings.database, DatabaseConfig)
        self.assertIsInstance(settings.etl, ETLConfig)
        self.assertIsInstance(settings.logging, LoggingConfig)
        self.assertIsInstance(settings.streamlit, StreamlitConfig)

    @patch.dict(
        "os.environ",
        {
            "WATCHTOWER_ENVIRONMENT": "production",
            "WATCHTOWER_DEBUG": "true",
            "WATCHTOWER_DATABASE__TYPE": "postgresql",
            "WATCHTOWER_DATABASE__HOST": "prod-db",
            "WATCHTOWER_ETL__BATCH_SIZE": "500",
            "WATCHTOWER_STREAMLIT__PORT": "9000",
        },
        clear=True,
    )
    def test_settings_from_environment(self):
        """Test Settings loading from environment variables."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        self.assertEqual(settings.environment, "production")
        self.assertTrue(settings.debug)
        self.assertEqual(settings.database.type, "postgresql")
        self.assertEqual(settings.database.host, "prod-db")
        self.assertEqual(settings.etl.batch_size, 500)
        self.assertEqual(settings.streamlit.port, 9000)

    def test_settings_nested_config_access(self):
        """Test accessing nested configuration objects."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        # Test database config access
        self.assertEqual(settings.database.type, "sqlite")
        self.assertEqual(settings.database.host, "localhost")

        # Test ETL config access
        self.assertEqual(settings.etl.batch_size, 100)
        self.assertEqual(settings.etl.retry_count, 3)

        # Test logging config access
        self.assertEqual(settings.logging.level, "INFO")
        self.assertEqual(
            settings.logging.format,
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def test_settings_project_root_discovery(self):
        """Test automatic project root discovery."""
        # Create nested directory structure
        nested_dir = self.test_project_root / "src" / "config"
        nested_dir.mkdir(parents=True, exist_ok=True)

        with patch("src.config.settings.Path.cwd", return_value=nested_dir):
            settings = Settings()

        # Should find the project root with pyproject.toml
        self.assertEqual(Path(settings.project_root), self.test_project_root)

    def test_settings_path_resolution(self):
        """Test path resolution for data and logs directories."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        # Test absolute path resolution
        data_path = settings.get_absolute_path(settings.project_structure.data_dir)
        logs_path = settings.get_absolute_path(settings.project_structure.logs_dir)

        self.assertEqual(data_path, self.test_project_root / "data")
        self.assertEqual(logs_path, self.test_project_root / "logs")

    def test_get_settings_singleton(self):
        """Test get_settings returns singleton instance."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings1 = get_settings()
            settings2 = get_settings()

        # Should be the same instance due to lru_cache
        self.assertIs(settings1, settings2)

    @patch.dict(
        "os.environ", {"WATCHTOWER_API_KEYS__OPENAI_API_KEY": "test-key"}, clear=True
    )
    def test_settings_api_keys_from_env(self):
        """Test API keys loading from environment."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        self.assertEqual(settings.api_keys.openai_api_key, "test-key")

    def test_settings_validation_error(self):
        """Test Settings validation with invalid values."""
        with self.assertRaises(ValidationError):
            # Invalid environment value
            Settings(environment="invalid_env")

    @patch("src.config.settings.Path.exists")
    def test_settings_missing_pyproject_toml(self, mock_exists):
        """Test Settings behavior when pyproject.toml is missing."""
        mock_exists.return_value = False

        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        # Should use current directory as fallback
        self.assertEqual(Path(settings.project_root), self.test_project_root)

    def test_settings_custom_project_root(self):
        """Test Settings with custom project root."""
        custom_root = "/custom/project/root"
        settings = Settings(project_root=custom_root)

        self.assertEqual(settings.project_root, custom_root)

    @patch.dict(
        "os.environ",
        {
            "WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE": "/path/to/creds.json",
            "WATCHTOWER_GOOGLE_DRIVE__BACKUP_FOLDER_ID": "folder123",
        },
        clear=True,
    )
    def test_settings_google_drive_config(self):
        """Test Google Drive configuration loading."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        self.assertEqual(settings.google_drive.credentials_file, "/path/to/creds.json")
        self.assertEqual(settings.google_drive.backup_folder_id, "folder123")


class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for the configuration system."""

    def setUp(self):
        """Set up integration test environment."""
        get_settings.cache_clear()

    def tearDown(self):
        """Clean up integration test environment."""
        get_settings.cache_clear()

    def test_full_configuration_loading(self):
        """Test loading a complete configuration with all components."""
        env_vars = {
            "WATCHTOWER_ENVIRONMENT": "production",
            "WATCHTOWER_DEBUG": "false",
            "WATCHTOWER_DATABASE__TYPE": "postgresql",
            "WATCHTOWER_DATABASE__HOST": "prod-db.example.com",
            "WATCHTOWER_DATABASE__PORT": "5432",
            "WATCHTOWER_DATABASE__USERNAME": "watchtower_user",
            "WATCHTOWER_DATABASE__PASSWORD": "secure_password",
            "WATCHTOWER_ETL__BATCH_SIZE": "1000",
            "WATCHTOWER_ETL__PARALLEL_PROCESSING": "true",
            "WATCHTOWER_ETL__MAX_WORKERS": "8",
            "WATCHTOWER_LOGGING__LEVEL": "WARNING",
            "WATCHTOWER_STREAMLIT__HOST": "0.0.0.0",
            "WATCHTOWER_STREAMLIT__PORT": "8080",
            "WATCHTOWER_CACHE__TTL": "7200",
            "WATCHTOWER_SECURITY__RATE_LIMIT_PER_MINUTE": "120",
            "WATCHTOWER_API_KEYS__OPENAI_API_KEY": "sk-test123",
            "WATCHTOWER_API_KEYS__GITHUB_TOKEN": "ghp_test456",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            settings = get_settings()

        # Verify all configurations loaded correctly
        self.assertEqual(settings.environment, "production")
        self.assertFalse(settings.debug)

        # Database config
        self.assertEqual(settings.database.type, "postgresql")
        self.assertEqual(settings.database.host, "prod-db.example.com")
        self.assertEqual(settings.database.username, "watchtower_user")

        # ETL config
        self.assertEqual(settings.etl.batch_size, 1000)
        self.assertTrue(settings.etl.parallel_processing)
        self.assertEqual(settings.etl.max_workers, 8)

        # Logging config
        self.assertEqual(settings.logging.level, "WARNING")

        # Streamlit config
        self.assertEqual(settings.streamlit.host, "0.0.0.0")
        self.assertEqual(settings.streamlit.port, 8080)

        # Cache config
        self.assertEqual(settings.cache.ttl, 7200)

        # Security config
        self.assertEqual(settings.security.rate_limit_per_minute, 120)

        # API keys
        self.assertEqual(settings.api_keys.openai_api_key, "sk-test123")
        self.assertEqual(settings.api_keys.github_token, "ghp_test456")

    def test_configuration_serialization(self):
        """Test configuration can be serialized and deserialized."""
        settings = get_settings()

        # Test dict conversion
        settings_dict = settings.model_dump()
        self.assertIsInstance(settings_dict, dict)
        self.assertIn("database", settings_dict)
        self.assertIn("etl", settings_dict)
        self.assertIn("logging", settings_dict)

        # Test JSON serialization
        settings_json = settings.model_dump_json()
        self.assertIsInstance(settings_json, str)

        # Test reconstruction from dict
        new_settings = Settings(**settings_dict)
        self.assertEqual(new_settings.environment, settings.environment)
        self.assertEqual(new_settings.database.type, settings.database.type)


if __name__ == "__main__":
    unittest.main()
