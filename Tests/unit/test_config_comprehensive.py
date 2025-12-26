"""Comprehensive unit tests for the configuration system.
Tests both settings.py and models.py functionality.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from src.config.models import (
    DatabaseConfig,
    ETLConfig,
    GoogleDriveConfig,
    LoggingConfig,
    SecurityConfig,
    StreamlitConfig,
    Environment,
    LLMProvider
)
from src.config.settings import Settings, get_settings


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
            credentials_file="credentials.json",
            backup_folder_id="test_folder_id",
        )

        self.assertEqual(config.credentials_file, "credentials.json")
        self.assertEqual(config.backup_folder_id, "test_folder_id")
        
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
        self.assertEqual(config.theme_base, "light")

    def test_security_config_defaults(self):
        """Test SecurityConfig with default values."""
        config = SecurityConfig()

        # Update checks based on actual default values in models.py
        # secret_key has default
        self.assertEqual(config.algorithm, "HS256")
        self.assertEqual(config.access_token_expire_minutes, 30)

    def test_llm_config_defaults(self):
        """Test LLMConfig with default values."""
        # Assuming LLMConfig is accessed via Settings usually, but we check model defaults here
        from src.config.models import LLMConfig
        config = LLMConfig()
        self.assertEqual(config.provider, LLMProvider.MOCK)
        self.assertEqual(config.model, "gpt-4o-mini")


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

        # Patch _find_project_root to return test_project_root by default
        self.root_patcher = patch("src.config.settings.Settings._find_project_root")
        self.mock_find_root = self.root_patcher.start()
        self.mock_find_root.return_value = str(self.test_project_root)

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        
        self.root_patcher.stop()

        shutil.rmtree(self.test_dir, ignore_errors=True)
        get_settings.cache_clear()

    @patch.dict("os.environ", {}, clear=True)
    def test_settings_default_values(self):
        """Test Settings with default values."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings(_env_file=None)

        self.assertEqual(Path(settings.project_root), self.test_project_root)
        self.assertEqual(settings.environment, Environment.DEVELOPMENT)
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
            "WATCHTOWER_DATABASE__URL": "postgresql://prod-db/watchtower",
            "WATCHTOWER_ETL__BATCH_SIZE": "500",
            "WATCHTOWER_STREAMLIT__PORT": "9000",
        },
        clear=True,
    )
    def test_settings_from_environment(self):
        """Test Settings loading from environment variables."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()
            
        self.assertEqual(settings.environment, Environment.PRODUCTION)
        self.assertTrue(settings.debug)
        self.assertEqual(settings.database.url, "postgresql://prod-db/watchtower")
        self.assertEqual(settings.etl.batch_size, 500)
        self.assertEqual(settings.streamlit.port, 9000)

    def test_settings_nested_config_access(self):
        """Test accessing nested configuration objects."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings(_env_file=None)

        # Test database config access
        self.assertEqual(settings.database.url, "sqlite:///watchtower.db")

        # Test ETL config access
        self.assertEqual(settings.etl.batch_size, 1000)

        # Test logging config access
        self.assertEqual(settings.logging.level, "INFO")
        self.assertEqual(
            settings.logging.format,
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def test_settings_project_root_discovery(self):
        """Test automatic project root discovery."""
        # This test is tricky because _find_project_root logic relies on __file__.
        # We've mocked _find_project_root in setUp, so we are checking the mock behavior here, 
        # or we verify that our manual override works effectively.
        # To truly test the logic, we'd need to unpatch and mock __file__, which is complex.
        # Instead, we verify that if _find_project_root returns X, project_root is X.
        
        settings = Settings(_env_file=None)
        self.assertEqual(Path(settings.project_root), self.test_project_root)
        
        # Verify find_project_root was called (by __init__ because project_root was None)
        self.mock_find_root.assert_called()

    def test_settings_path_resolution(self):
        """Test path resolution for data and logs directories."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings(_env_file=None)

        # Path resolution happens relative to project_root
        # settings.data_dir becomes absolute
        self.assertTrue(Path(settings.data_dir).is_absolute())
        self.assertTrue(Path(settings.logs_dir).is_absolute())
        
        self.assertEqual(Path(settings.data_dir), self.test_project_root / "data")
        self.assertEqual(Path(settings.logs_dir), self.test_project_root / "logs")

    def test_get_settings_singleton(self):
        """Test get_settings returns singleton instance."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings1 = get_settings()
            settings2 = get_settings()

        # Should be the same instance due to lru_cache
        self.assertIs(settings1, settings2)

    @patch.dict("os.environ", {"WATCHTOWER_LLM__OPENAI_API_KEY": "test-key"}, clear=True)
    def test_settings_api_keys_from_env(self):
        """Test API keys loading from environment."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        self.assertEqual(settings.llm.openai_api_key, "test-key")

    def test_settings_custom_project_root(self):
        """Test Settings with custom project root."""
        # Use a path that exists or mock exist
        # Pydantic validation might check path existence if defined as DirectoryPath, but here likely just str?
        # In settings.py: project_root: str | None
        custom_root = str(self.test_project_root / "custom_root")
        Path(custom_root).mkdir(parents=True, exist_ok=True)
        
        settings = Settings(project_root=custom_root)
        self.assertEqual(settings.project_root, custom_root)

    @patch.dict(
        "os.environ",
        {
            "WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE": "creds.json",
            "WATCHTOWER_GOOGLE_DRIVE__BACKUP_FOLDER_ID": "folder123",
        },
        clear=True,
    )
    def test_settings_google_drive_config(self):
        """Test Google Drive configuration loading."""
        with patch("src.config.settings.Path.cwd", return_value=self.test_project_root):
            settings = Settings()

        self.assertEqual(settings.google_drive.credentials_file, "creds.json")
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
            "WATCHTOWER_DATABASE__URL": "postgresql://user:pass@prod-db.example.com:5432/db",
            "WATCHTOWER_ETL__BATCH_SIZE": "1000",
            "WATCHTOWER_ETL__MAX_WORKERS": "8",
            "WATCHTOWER_LOGGING__LEVEL": "WARNING",
            "WATCHTOWER_STREAMLIT__HOST": "0.0.0.0",
            "WATCHTOWER_STREAMLIT__PORT": "8080",
            "WATCHTOWER_SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES": "60",
            "WATCHTOWER_LLM__OPENAI_API_KEY": "sk-test123",
            "WATCHTOWER_API__NEWS_API_KEY": "news-key-123",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            settings = get_settings()

        # Verify all configurations loaded correctly
        self.assertEqual(settings.environment, Environment.PRODUCTION)
        self.assertFalse(settings.debug)

        # Database config
        self.assertEqual(settings.database.url, "postgresql://user:pass@prod-db.example.com:5432/db")

        # ETL config
        self.assertEqual(settings.etl.batch_size, 1000)
        self.assertEqual(settings.etl.max_workers, 8)

        # Logging config
        self.assertEqual(settings.logging.level, "WARNING")

        # Streamlit config
        self.assertEqual(settings.streamlit.host, "0.0.0.0")
        self.assertEqual(settings.streamlit.port, 8080)

        # Security config
        self.assertEqual(settings.security.access_token_expire_minutes, 60)

        # API keys / LLM
        self.assertEqual(settings.llm.openai_api_key, "sk-test123")
        self.assertEqual(settings.api.news_api_key, "news-key-123")

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
        # Compare critical fields
        self.assertEqual(new_settings.environment, settings.environment)
        self.assertEqual(new_settings.database.url, settings.database.url)


if __name__ == "__main__":
    unittest.main()
