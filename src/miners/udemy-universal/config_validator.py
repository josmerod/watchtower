"""Configuration validation for Udemy Universal miner.

This module provides comprehensive validation for configuration settings
with detailed error messages and suggestions for fixes.
"""

import json
import os
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from logger import get_logger

logger = get_logger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    level: ValidationLevel
    field: str
    message: str
    suggestion: Optional[str] = None
    current_value: Any = None
    expected_type: str = None


class ConfigValidator:
    """Comprehensive configuration validator."""
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.logger = logger
        self.validation_results: List[ValidationResult] = []
        
        # Define validation schemas
        self.schema = self._get_validation_schema()
        
        # Define valid options
        self.valid_options = self._get_valid_options()
    
    def _get_validation_schema(self) -> Dict[str, Any]:
        """Get the validation schema for configuration.
        
        Returns:
            Dictionary containing validation rules
        """
        return {
            "email": {
                "type": str,
                "required": False,
                "pattern": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                "description": "Valid email address for Udemy account"
            },
            "password": {
                "type": str,
                "required": False,
                "min_length": 1,
                "description": "Password for Udemy account"
            },
            "use_browser_cookies": {
                "type": bool,
                "required": False,
                "default": True,
                "description": "Whether to use browser cookies for authentication"
            },
            "browser_type": {
                "type": str,
                "required": False,
                "choices": ["chrome", "firefox", "edge", "safari", "opera", "brave", "chromium"],
                "default": "chrome",
                "description": "Preferred browser for cookie extraction"
            },
            "sites": {
                "type": dict,
                "required": True,
                "description": "Dictionary of sites to scrape with boolean values",
                "nested_schema": {
                    "type": bool,
                    "required": False,
                    "default": True
                }
            },
            "categories": {
                "type": dict,
                "required": True,
                "description": "Dictionary of course categories to include",
                "nested_schema": {
                    "type": bool,
                    "required": False,
                    "default": True
                }
            },
            "languages": {
                "type": dict,
                "required": True,
                "description": "Dictionary of languages to include",
                "nested_schema": {
                    "type": bool,
                    "required": False,
                    "default": False
                }
            },
            "filters": {
                "type": dict,
                "required": True,
                "description": "Filtering options",
                "nested_schema": {
                    "min_rating": {
                        "type": float,
                        "min_value": 0.0,
                        "max_value": 5.0,
                        "default": 0.0,
                        "description": "Minimum course rating"
                    },
                    "min_reviews": {
                        "type": int,
                        "min_value": 0,
                        "default": 0,
                        "description": "Minimum number of reviews"
                    },
                    "max_pages": {
                        "type": int,
                        "min_value": 1,
                        "max_value": 100,
                        "default": 5,
                        "description": "Maximum pages to scrape"
                    },
                    "course_update_threshold_months": {
                        "type": int,
                        "min_value": 1,
                        "max_value": 120,
                        "default": 24,
                        "description": "Course update threshold in months"
                    },
                    "exclude_expired_coupons": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to exclude expired coupons"
                    },
                    "skip_already_enrolled": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to skip already enrolled courses"
                    },
                    "discounted_only": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to only include discounted courses"
                    },
                    "free_only": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to only include free courses"
                    }
                }
            },
            "exclusions": {
                "type": dict,
                "required": False,
                "description": "Course exclusion settings",
                "nested_schema": {
                    "title_exclude": {
                        "type": list,
                        "item_type": str,
                        "default": [],
                        "description": "List of title keywords to exclude"
                    },
                    "instructor_exclude": {
                        "type": list,
                        "item_type": str,
                        "default": [],
                        "description": "List of instructors to exclude"
                    },
                    "keyword_exclude": {
                        "type": list,
                        "item_type": str,
                        "default": [],
                        "description": "List of keywords to exclude"
                    }
                }
            },
            "output": {
                "type": dict,
                "required": False,
                "description": "Output settings",
                "nested_schema": {
                    "save_txt": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to save results to text file"
                    },
                    "save_json": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to save results to JSON file"
                    },
                    "courses_directory": {
                        "type": str,
                        "default": "Courses",
                        "description": "Directory to save course files"
                    },
                    "logs_directory": {
                        "type": str,
                        "default": "logs",
                        "description": "Directory to save log files"
                    },
                    "show_progress": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to show progress information"
                    },
                    "show_statistics": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to show statistics"
                    },
                    "verbose": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to enable verbose output"
                    },
                    "quiet": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to suppress output"
                    }
                }
            },
            "automation": {
                "type": dict,
                "required": False,
                "description": "Automation settings",
                "nested_schema": {
                    "max_retries": {
                        "type": int,
                        "min_value": 1,
                        "max_value": 10,
                        "default": 3,
                        "description": "Maximum number of retries"
                    },
                    "retry_delay": {
                        "type": int,
                        "min_value": 1,
                        "max_value": 60,
                        "default": 2,
                        "description": "Delay between retries in seconds"
                    },
                    "request_timeout": {
                        "type": int,
                        "min_value": 5,
                        "max_value": 300,
                        "default": 30,
                        "description": "Request timeout in seconds"
                    },
                    "batch_size": {
                        "type": int,
                        "min_value": 1,
                        "max_value": 100,
                        "default": 10,
                        "description": "Batch size for processing"
                    },
                    "concurrent_scrapers": {
                        "type": int,
                        "min_value": 1,
                        "max_value": 20,
                        "default": 5,
                        "description": "Number of concurrent scrapers"
                    },
                    "rate_limit_delay": {
                        "type": float,
                        "min_value": 0.1,
                        "max_value": 10.0,
                        "default": 1.0,
                        "description": "Rate limit delay in seconds"
                    },
                    "auto_enroll": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to automatically enroll in courses"
                    },
                    "skip_confirmation": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to skip confirmation prompts"
                    }
                }
            },
            "advanced": {
                "type": dict,
                "required": False,
                "description": "Advanced settings",
                "nested_schema": {
                    "user_agent": {
                        "type": str,
                        "default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "description": "User agent string for requests"
                    },
                    "use_proxy": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to use proxy"
                    },
                    "proxy_url": {
                        "type": str,
                        "default": "",
                        "description": "Proxy URL (if using proxy)"
                    },
                    "debug_mode": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to enable debug mode"
                    },
                    "log_level": {
                        "type": str,
                        "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        "default": "INFO",
                        "description": "Logging level"
                    },
                    "save_debug_pages": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to save debug pages"
                    },
                    "headless_browser": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to run browser in headless mode"
                    },
                    "browser_timeout": {
                        "type": int,
                        "min_value": 10,
                        "max_value": 300,
                        "default": 60,
                        "description": "Browser timeout in seconds"
                    },
                    "check_for_updates": {
                        "type": bool,
                        "default": True,
                        "description": "Whether to check for updates"
                    },
                    "auto_update": {
                        "type": bool,
                        "default": False,
                        "description": "Whether to auto-update"
                    }
                }
            }
        }
    
    def _get_valid_options(self) -> Dict[str, List[str]]:
        """Get valid options for specific fields.
        
        Returns:
            Dictionary of valid options
        """
        return {
            "browser_type": ["chrome", "firefox", "edge", "safari", "opera", "brave", "chromium"],
            "log_level": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "sites": [
                "Udemy Freebies", "Tutorial Bar", "Real Discount", "Course Vania",
                "IDownloadCoupons", "E-next", "Discudemy", "Course Joiner",
                "Cursos Dev", "Udemy Free Courses"
            ],
            "categories": [
                "development", "business", "design", "marketing", "it-software",
                "photography", "music", "health-fitness", "teaching", "lifestyle",
                "personal-development", "finance", "office-productivity"
            ],
            "languages": [
                "en", "es", "fr", "de", "pt", "it", "ja", "ko", "zh", "ru",
                "ar", "hi", "tr", "pl", "nl"
            ]
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[ValidationResult]]:
        """Validate entire configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, validation_results)
        """
        self.validation_results.clear()
        
        # Validate each section
        self._validate_section(config, self.schema, "")
        
        # Perform cross-field validation
        self._validate_cross_fields(config)
        
        # Check for unknown fields
        self._check_unknown_fields(config, self.schema, "")
        
        # Determine overall validity
        has_errors = any(result.level == ValidationLevel.ERROR for result in self.validation_results)
        
        return not has_errors, self.validation_results
    
    def _validate_section(self, config: Dict[str, Any], schema: Dict[str, Any], prefix: str):
        """Validate a configuration section.
        
        Args:
            config: Configuration dictionary
            schema: Schema dictionary
            prefix: Field prefix for nested validation
        """
        for field, rules in schema.items():
            field_path = f"{prefix}.{field}" if prefix else field
            
            # Check if field exists
            if field not in config:
                if rules.get("required", False):
                    self.validation_results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        field=field_path,
                        message=f"Required field '{field}' is missing",
                        suggestion=f"Add '{field}' to configuration",
                        expected_type=str(rules.get("type", "unknown"))
                    ))
                elif "default" in rules:
                    self.validation_results.append(ValidationResult(
                        level=ValidationLevel.INFO,
                        field=field_path,
                        message=f"Field '{field}' not found, using default value",
                        suggestion=f"Consider adding '{field}' to configuration",
                        current_value=rules["default"]
                    ))
                continue
            
            value = config[field]
            self._validate_field(field_path, value, rules)
    
    def _validate_field(self, field_path: str, value: Any, rules: Dict[str, Any]):
        """Validate a single field.
        
        Args:
            field_path: Full field path
            value: Field value
            rules: Validation rules
        """
        # Type validation
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field=field_path,
                message=f"Expected {expected_type.__name__}, got {type(value).__name__}",
                suggestion=f"Change value to {expected_type.__name__}",
                current_value=value,
                expected_type=expected_type.__name__
            ))
            return
        
        # String validations
        if isinstance(value, str):
            self._validate_string(field_path, value, rules)
        
        # Numeric validations
        elif isinstance(value, (int, float)):
            self._validate_numeric(field_path, value, rules)
        
        # List validations
        elif isinstance(value, list):
            self._validate_list(field_path, value, rules)
        
        # Dictionary validations
        elif isinstance(value, dict):
            self._validate_dict(field_path, value, rules)
        
        # Choice validation
        if "choices" in rules:
            if value not in rules["choices"]:
                self.validation_results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    field=field_path,
                    message=f"Invalid choice '{value}'. Must be one of: {rules['choices']}",
                    suggestion=f"Choose from: {', '.join(rules['choices'])}",
                    current_value=value
                ))
    
    def _validate_string(self, field_path: str, value: str, rules: Dict[str, Any]):
        """Validate string field.
        
        Args:
            field_path: Full field path
            value: String value
            rules: Validation rules
        """
        # Length validation
        if "min_length" in rules and len(value) < rules["min_length"]:
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field=field_path,
                message=f"String too short. Minimum length: {rules['min_length']}",
                suggestion=f"Provide string with at least {rules['min_length']} characters",
                current_value=value
            ))
        
        if "max_length" in rules and len(value) > rules["max_length"]:
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field=field_path,
                message=f"String too long. Maximum length: {rules['max_length']}",
                suggestion=f"Provide string with at most {rules['max_length']} characters",
                current_value=value
            ))
        
        # Pattern validation
        if "pattern" in rules:
            if not re.match(rules["pattern"], value):
                self.validation_results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    field=field_path,
                    message=f"String does not match required pattern",
                    suggestion=f"Provide string matching pattern: {rules['pattern']}",
                    current_value=value
                ))
    
    def _validate_numeric(self, field_path: str, value: Union[int, float], rules: Dict[str, Any]):
        """Validate numeric field.
        
        Args:
            field_path: Full field path
            value: Numeric value
            rules: Validation rules
        """
        # Range validation
        if "min_value" in rules and value < rules["min_value"]:
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field=field_path,
                message=f"Value too small. Minimum: {rules['min_value']}",
                suggestion=f"Provide value >= {rules['min_value']}",
                current_value=value
            ))
        
        if "max_value" in rules and value > rules["max_value"]:
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field=field_path,
                message=f"Value too large. Maximum: {rules['max_value']}",
                suggestion=f"Provide value <= {rules['max_value']}",
                current_value=value
            ))
    
    def _validate_list(self, field_path: str, value: List[Any], rules: Dict[str, Any]):
        """Validate list field.
        
        Args:
            field_path: Full field path
            value: List value
            rules: Validation rules
        """
        # Length validation
        if "min_items" in rules and len(value) < rules["min_items"]:
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field=field_path,
                message=f"List too short. Minimum items: {rules['min_items']}",
                suggestion=f"Provide list with at least {rules['min_items']} items",
                current_value=value
            ))
        
        if "max_items" in rules and len(value) > rules["max_items"]:
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field=field_path,
                message=f"List too long. Maximum items: {rules['max_items']}",
                suggestion=f"Provide list with at most {rules['max_items']} items",
                current_value=value
            ))
        
        # Item type validation
        if "item_type" in rules:
            for i, item in enumerate(value):
                if not isinstance(item, rules["item_type"]):
                    self.validation_results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        field=f"{field_path}[{i}]",
                        message=f"Expected {rules['item_type'].__name__}, got {type(item).__name__}",
                        suggestion=f"Ensure all items are of type {rules['item_type'].__name__}",
                        current_value=item
                    ))
    
    def _validate_dict(self, field_path: str, value: Dict[str, Any], rules: Dict[str, Any]):
        """Validate dictionary field.
        
        Args:
            field_path: Full field path
            value: Dictionary value
            rules: Validation rules
        """
        # Nested schema validation
        if "nested_schema" in rules:
            nested_schema = rules["nested_schema"]
            
            # If nested_schema is a dict of rules, validate each key-value pair
            if isinstance(nested_schema, dict) and "type" in nested_schema:
                # All values should follow the same schema
                for key, val in value.items():
                    self._validate_field(f"{field_path}.{key}", val, nested_schema)
            else:
                # Nested schema is a full schema dict
                self._validate_section(value, nested_schema, field_path)
        
        # Valid keys validation
        if field_path in ["sites", "categories", "languages"]:
            valid_keys = self.valid_options.get(field_path.split('.')[-1], [])
            if valid_keys:
                for key in value.keys():
                    if key not in valid_keys:
                        self.validation_results.append(ValidationResult(
                            level=ValidationLevel.WARNING,
                            field=f"{field_path}.{key}",
                            message=f"Unknown key '{key}' in {field_path}",
                            suggestion=f"Valid keys are: {', '.join(valid_keys)}",
                            current_value=key
                        ))
    
    def _validate_cross_fields(self, config: Dict[str, Any]):
        """Validate relationships between fields.
        
        Args:
            config: Configuration dictionary
        """
        # Email and password validation
        if config.get("use_browser_cookies", True) is False:
            email = config.get("email", "")
            password = config.get("password", "")
            
            if not email or not password:
                self.validation_results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    field="authentication",
                    message="Email and password required when not using browser cookies",
                    suggestion="Set 'use_browser_cookies' to true or provide email/password",
                    current_value={"email": email, "password": bool(password)}
                ))
        
        # Conflicting filter options
        filters = config.get("filters", {})
        if filters.get("free_only", False) and filters.get("discounted_only", False):
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                field="filters",
                message="Cannot enable both 'free_only' and 'discounted_only'",
                suggestion="Choose either 'free_only' or 'discounted_only', not both",
                current_value={"free_only": True, "discounted_only": True}
            ))
        
        # Output directory validation
        output = config.get("output", {})
        if output.get("quiet", False) and output.get("verbose", False):
            self.validation_results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                field="output",
                message="Both 'quiet' and 'verbose' are enabled",
                suggestion="Choose either 'quiet' or 'verbose', not both",
                current_value={"quiet": True, "verbose": True}
            ))
    
    def _check_unknown_fields(self, config: Dict[str, Any], schema: Dict[str, Any], prefix: str):
        """Check for unknown fields in configuration.
        
        Args:
            config: Configuration dictionary
            schema: Schema dictionary
            prefix: Field prefix
        """
        for field in config:
            if field not in schema:
                field_path = f"{prefix}.{field}" if prefix else field
                self.validation_results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    field=field_path,
                    message=f"Unknown field '{field}'",
                    suggestion=f"Remove '{field}' or check spelling",
                    current_value=config[field]
                ))
    
    def load_and_validate_config(self, config_path: str) -> Tuple[bool, Dict[str, Any], List[ValidationResult]]:
        """Load and validate configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (is_valid, config, validation_results)
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            is_valid, results = self.validate_config(config)
            return is_valid, config, results
            
        except FileNotFoundError:
            return False, {}, [ValidationResult(
                level=ValidationLevel.ERROR,
                field="config_file",
                message=f"Configuration file not found: {config_path}",
                suggestion="Create configuration file or check path"
            )]
        except json.JSONDecodeError as e:
            return False, {}, [ValidationResult(
                level=ValidationLevel.ERROR,
                field="config_file",
                message=f"Invalid JSON in configuration file: {e}",
                suggestion="Fix JSON syntax errors"
            )]
        except Exception as e:
            return False, {}, [ValidationResult(
                level=ValidationLevel.ERROR,
                field="config_file",
                message=f"Error loading configuration: {e}",
                suggestion="Check file permissions and format"
            )]
    
    def generate_default_config(self) -> Dict[str, Any]:
        """Generate default configuration based on schema.
        
        Returns:
            Dictionary containing default configuration
        """
        def extract_defaults(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for field, rules in schema_dict.items():
                if isinstance(rules, dict):
                    if "default" in rules:
                        result[field] = rules["default"]
                    elif "nested_schema" in rules:
                        if isinstance(rules["nested_schema"], dict) and "type" not in rules["nested_schema"]:
                            result[field] = extract_defaults(rules["nested_schema"])
                        else:
                            result[field] = {}
                    elif rules.get("type") == dict:
                        result[field] = {}
                    elif rules.get("type") == list:
                        result[field] = []
            return result
        
        return extract_defaults(self.schema)
    
    def format_validation_results(self, results: List[ValidationResult]) -> str:
        """Format validation results for display.
        
        Args:
            results: List of validation results
            
        Returns:
            Formatted string
        """
        if not results:
            return "✅ Configuration is valid!"
        
        lines = []
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        infos = [r for r in results if r.level == ValidationLevel.INFO]
        
        if errors:
            lines.append("❌ ERRORS:")
            for error in errors:
                lines.append(f"  • {error.field}: {error.message}")
                if error.suggestion:
                    lines.append(f"    💡 {error.suggestion}")
            lines.append("")
        
        if warnings:
            lines.append("⚠️ WARNINGS:")
            for warning in warnings:
                lines.append(f"  • {warning.field}: {warning.message}")
                if warning.suggestion:
                    lines.append(f"    💡 {warning.suggestion}")
            lines.append("")
        
        if infos:
            lines.append("ℹ️ INFO:")
            for info in infos:
                lines.append(f"  • {info.field}: {info.message}")
                if info.suggestion:
                    lines.append(f"    💡 {info.suggestion}")
        
        return "\n".join(lines)


# Global instance
config_validator = ConfigValidator()


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[ValidationResult]]:
    """Convenience function to validate configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, validation_results)
    """
    return config_validator.validate_config(config)


def load_and_validate_config(config_path: str) -> Tuple[bool, Dict[str, Any], List[ValidationResult]]:
    """Convenience function to load and validate configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Tuple of (is_valid, config, validation_results)
    """
    return config_validator.load_and_validate_config(config_path)


def generate_default_config() -> Dict[str, Any]:
    """Convenience function to generate default configuration.
    
    Returns:
        Default configuration dictionary
    """
    return config_validator.generate_default_config()


if __name__ == "__main__":
    # Test the configuration validator
    print("Testing configuration validator...")
    
    # Generate and validate default config
    default_config = generate_default_config()
    is_valid, results = validate_config(default_config)
    
    print(f"Default config is valid: {is_valid}")
    if results:
        print(config_validator.format_validation_results(results))
    
    # Test with invalid config
    invalid_config = {
        "email": "invalid-email",
        "filters": {
            "min_rating": 6.0,  # Invalid rating
            "free_only": True,
            "discounted_only": True  # Conflicting options
        },
        "unknown_field": "value"
    }
    
    is_valid, results = validate_config(invalid_config)
    print(f"\nInvalid config is valid: {is_valid}")
    print(config_validator.format_validation_results(results)) 