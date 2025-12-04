#!/usr/bin/env python3
"""Unified CLI for the Enhanced Udemy Universal Miner.

This script provides a comprehensive command-line interface that integrates
all the enhanced features including update checking, statistics reporting,
advanced filtering, cookie management, and configuration validation.
"""

import argparse
import json
import os
import sys
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import enhanced modules
try:
    # Import original modules
    from base import VERSION, Scraper, Udemy, scraper_dict
    from cli import create_scraping_thread, main_extract
    from config_validator import ConfigValidator, load_and_validate_config
    from cookie_manager import CookieManager, detect_browsers
    from enhanced_filtering import EnhancedFilter
    from enroll import display_results, handle_login, main_enroll
    from logger import create_metrics_logger, get_logger, setup_structured_logging
    from statistics_reporter import StatisticsReporter, end_session, start_session
    from update_checker import UpdateChecker, display_update_notification

    ENHANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some enhanced features not available: {e}")
    ENHANCED_FEATURES_AVAILABLE = False

    # Import basic modules
    from base import VERSION, Scraper, Udemy, scraper_dict
    from cli import create_scraping_thread
    from enroll import display_results, handle_login
    from logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class UnifiedCLI:
    """Unified command-line interface for the Enhanced Udemy Universal Miner."""

    def __init__(self):
        """Initialize the unified CLI."""
        self.version = VERSION
        self.config_file = None
        self.config = {}
        self.enhanced_features = ENHANCED_FEATURES_AVAILABLE

        # Initialize enhanced components if available
        if self.enhanced_features:
            self.update_checker = UpdateChecker(VERSION)
            self.stats_reporter = StatisticsReporter()
            self.config_validator = ConfigValidator()
            self.cookie_manager = CookieManager()
            self.metrics_logger = create_metrics_logger()

        # Setup argument parser
        self.parser = self._create_argument_parser()

    def _create_argument_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all options.

        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            prog="udemy-universal-miner",
            description="Enhanced Udemy Universal Miner - Extract and enroll in discounted Udemy courses",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"""
Examples:
  {sys.argv[0]} extract                          # Extract courses from all sites
  {sys.argv[0]} enroll                           # Enroll in previously extracted courses
  {sys.argv[0]} run                              # Extract and enroll in one step
  {sys.argv[0]} --config settings.json extract  # Use custom configuration
  {sys.argv[0]} --update-check                   # Check for updates
  {sys.argv[0]} --stats --days 7                 # Show statistics for last 7 days
  {sys.argv[0]} --validate-config settings.json # Validate configuration file
  {sys.argv[0]} --test-cookies                   # Test cookie extraction
  {sys.argv[0]} --create-default-config          # Create default configuration

Version: {VERSION}
Enhanced Features: {"Available" if self.enhanced_features else "Limited"}
            """,
        )

        # Main commands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Extract command
        extract_parser = subparsers.add_parser("extract", help="Extract courses from scraping sites")
        extract_parser.add_argument(
            "--sites",
            nargs="+",
            choices=list(scraper_dict.keys()),
            help="Specific sites to scrape",
        )
        extract_parser.add_argument("--max-pages", type=int, default=5, help="Maximum pages to scrape per site")
        extract_parser.add_argument(
            "--output",
            default="courses_to_enroll.json",
            help="Output file for extracted courses",
        )

        # Enroll command
        enroll_parser = subparsers.add_parser("enroll", help="Enroll in extracted courses")
        enroll_parser.add_argument(
            "--input",
            default="courses_to_enroll.json",
            help="Input file with courses to enroll",
        )
        enroll_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be enrolled without actual enrollment",
        )

        # Run command (extract + enroll)
        run_parser = subparsers.add_parser("run", help="Extract and enroll in one step")
        run_parser.add_argument(
            "--sites",
            nargs="+",
            choices=list(scraper_dict.keys()),
            help="Specific sites to scrape",
        )
        run_parser.add_argument("--max-pages", type=int, default=5, help="Maximum pages to scrape per site")
        run_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be enrolled without actual enrollment",
        )

        # Global options
        parser.add_argument(
            "--config",
            "-c",
            help="Configuration file path",
            default="duce-cli-settings.json",
        )
        parser.add_argument("--debug", action="store_true", help="Enable debug mode")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
        parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
        parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

        # Enhanced features (only if available)
        if self.enhanced_features:
            parser.add_argument("--update-check", action="store_true", help="Check for updates and exit")
            parser.add_argument("--stats", action="store_true", help="Show enrollment statistics")
            parser.add_argument(
                "--days",
                type=int,
                default=30,
                help="Number of days for statistics (default: 30)",
            )
            parser.add_argument(
                "--validate-config",
                metavar="FILE",
                help="Validate configuration file and exit",
            )
            parser.add_argument(
                "--create-default-config",
                metavar="FILE",
                help="Create default configuration file and exit",
            )
            parser.add_argument(
                "--test-cookies",
                action="store_true",
                help="Test cookie extraction and exit",
            )
            parser.add_argument(
                "--browser",
                choices=["chrome", "firefox", "edge", "safari", "opera", "brave"],
                help="Preferred browser for cookie extraction",
            )
            parser.add_argument(
                "--structured-logging",
                action="store_true",
                help="Enable structured JSON logging",
            )
            parser.add_argument("--metrics", action="store_true", help="Enable metrics collection")

        return parser

    def load_configuration(self, config_path: str = None) -> bool:
        """Load configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            True if configuration loaded successfully
        """
        # Try to find configuration file
        config_paths = []
        if config_path:
            config_paths.append(config_path)

        # Default configuration files
        config_paths.extend(
            [
                "duce-cli-settings.json",
                "settings.json",
                "config.json",
                "default-duce-cli-settings.json",
            ]
        )

        for path in config_paths:
            if os.path.exists(path):
                try:
                    if self.enhanced_features:
                        is_valid, config, results = load_and_validate_config(path)
                        if not is_valid:
                            logger.error(f"Configuration validation failed for {path}")
                            logger.error(self.config_validator.format_validation_results(results))
                            return False
                        self.config = config
                    else:
                        with open(path) as f:
                            self.config = json.load(f)

                    self.config_file = path
                    logger.info(f"Configuration loaded from {path}")
                    return True
                except Exception as e:
                    logger.error(f"Error loading configuration from {path}: {e}")
                    continue

        logger.warning("No configuration file found, using defaults")
        return True

    def handle_update_check(self) -> int:
        """Handle update check command.

        Returns:
            Exit code
        """
        if not self.enhanced_features:
            logger.error("Update check feature not available")
            return 1

        try:
            update_info = self.update_checker.get_update_info()
            if update_info:
                self.update_checker.display_update_notification(update_info)
            else:
                logger.info("Update check completed successfully")
            return 0
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            return 1

    def handle_statistics(self, days: int = 30) -> int:
        """Handle statistics display command.

        Args:
            days: Number of days to include in statistics

        Returns:
            Exit code
        """
        if not self.enhanced_features:
            logger.error("Statistics feature not available")
            return 1

        try:
            self.stats_reporter.display_overall_statistics(days)
            return 0
        except Exception as e:
            logger.error(f"Statistics display failed: {e}")
            return 1

    def handle_config_validation(self, config_path: str) -> int:
        """Handle configuration validation command.

        Args:
            config_path: Path to configuration file

        Returns:
            Exit code
        """
        if not self.enhanced_features:
            logger.error("Configuration validation feature not available")
            return 1

        try:
            is_valid, config, results = load_and_validate_config(config_path)

            if is_valid:
                logger.info("✅ Configuration is valid!")
            else:
                logger.error("❌ Configuration validation failed!")

            if results:
                print(self.config_validator.format_validation_results(results))

            return 0 if is_valid else 1
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return 1

    def handle_create_default_config(self, config_path: str) -> int:
        """Handle create default configuration command.

        Args:
            config_path: Path for new configuration file

        Returns:
            Exit code
        """
        if not self.enhanced_features:
            logger.error("Default configuration creation feature not available")
            return 1

        try:
            default_config = self.config_validator.generate_default_config()

            with open(config_path, "w") as f:
                json.dump(default_config, f, indent=2)

            logger.info(f"Default configuration created at {config_path}")
            return 0
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
            return 1

    def handle_test_cookies(self, browser: str = None) -> int:
        """Handle cookie testing command.

        Args:
            browser: Preferred browser for testing

        Returns:
            Exit code
        """
        if not self.enhanced_features:
            logger.error("Cookie testing feature not available")
            return 1

        try:
            if browser:
                self.cookie_manager.preferred_browser = browser

            # Test cookie extraction
            test_results = self.cookie_manager.test_cookie_extraction()

            logger.info("🍪 Cookie Extraction Test Results")
            logger.info("=" * 40)
            logger.info(f"Detected Browsers: {len(test_results['browsers'])}")
            logger.info(f"Successful Extractions: {test_results['summary']['successful']}")
            logger.info(f"Failed Extractions: {test_results['summary']['failed']}")
            logger.info("")

            for browser_name, results in test_results["browsers"].items():
                status = "✅" if results["overall_success"] else "❌"
                logger.info(f"{status} {browser_name}")
                logger.info(f"  Browser Cookie3: {'✅' if results['browser_cookie3']['success'] else '❌'}")
                logger.info(f"  SQLite Method: {'✅' if results['sqlite']['success'] else '❌'}")
                logger.info(f"  Required Cookies: {'✅' if results['browser_cookie3']['has_required'] or results['sqlite']['has_required'] else '❌'}")

            return 0
        except Exception as e:
            logger.error(f"Cookie testing failed: {e}")
            return 1

    def handle_extract(self, args) -> int:
        """Handle course extraction command.

        Args:
            args: Parsed command line arguments

        Returns:
            Exit code
        """
        try:
            # Start metrics collection if enabled
            if self.enhanced_features and args.metrics:
                self.metrics_logger.start_timer("extraction")

            # Start statistics session if enhanced features available
            session_id = None
            if self.enhanced_features:
                session_id = start_session(f"extract_{int(time.time())}")
                logger.info(f"Started extraction session: {session_id}")

            # Run extraction
            if args.sites:
                # Filter sites
                sites_to_scrape = [site for site in args.sites if site in scraper_dict]
                logger.info(f"Scraping specific sites: {sites_to_scrape}")
            else:
                sites_to_scrape = list(scraper_dict.keys())

            # Update configuration if provided
            if hasattr(args, "max_pages") and args.max_pages:
                if "filters" not in self.config:
                    self.config["filters"] = {}
                self.config["filters"]["max_pages"] = args.max_pages

            # Initialize scraper
            scraper = Scraper(sites_to_scrape, debug=args.debug)

            # Get courses
            scraped_data = scraper.get_scraped_courses(lambda site: create_scraping_thread(site, scraper))

            # Save results
            output_file = args.output
            successful_data = {}

            for site, data in scraped_data.items():
                if len(data) > 0:
                    successful_data[site] = data
                    if self.enhanced_features:
                        # Record site activity
                        from statistics_reporter import record_site_activity

                        record_site_activity(site, len(data), 0.0, 0)

            if successful_data:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(successful_data, f, indent=2, ensure_ascii=False)

                total_courses = sum(len(courses) for courses in successful_data.values())
                logger.info(f"Extracted {total_courses} courses from {len(successful_data)} sites")
                logger.info(f"Results saved to {output_file}")
            else:
                logger.warning("No courses extracted")

            # End metrics and session
            if self.enhanced_features:
                if args.metrics:
                    self.metrics_logger.end_timer("extraction")
                    self.metrics_logger.log_metric("courses_extracted", total_courses)

                if session_id:
                    end_session()
                    logger.info(f"Ended extraction session: {session_id}")

            return 0

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return 1

    def handle_enroll(self, args) -> int:
        """Handle course enrollment command.

        Args:
            args: Parsed command line arguments

        Returns:
            Exit code
        """
        try:
            # Start metrics collection if enabled
            if self.enhanced_features and args.metrics:
                self.metrics_logger.start_timer("enrollment")

            # Start statistics session if enhanced features available
            session_id = None
            if self.enhanced_features:
                session_id = start_session(f"enroll_{int(time.time())}")
                logger.info(f"Started enrollment session: {session_id}")

            # Load courses
            input_file = args.input
            if not os.path.exists(input_file):
                logger.error(f"Input file not found: {input_file}")
                return 1

            with open(input_file, encoding="utf-8") as f:
                scraped_data = json.load(f)

            # Dry run check
            if args.dry_run:
                total_courses = sum(len(courses) for courses in scraped_data.values())
                logger.info(f"DRY RUN: Would attempt to enroll in {total_courses} courses")
                for site, courses in scraped_data.items():
                    logger.info(f"  {site}: {len(courses)} courses")
                return 0

            # Initialize Udemy client
            udemy = Udemy("cli", debug=args.debug)

            # Load settings
            if self.config:
                udemy.settings = self.config
            else:
                udemy.load_settings()

            # Handle login
            if not handle_login(udemy):
                logger.error("Login failed")
                return 1

            # Set scraped data
            udemy.scraped_data = scraped_data

            # Start enrollment
            udemy.start_enrolling()

            # Display results
            display_results(udemy)

            # End metrics and session
            if self.enhanced_features:
                if args.metrics:
                    self.metrics_logger.end_timer("enrollment")
                    self.metrics_logger.log_metric("courses_enrolled", udemy.successfully_enrolled_c)

                if session_id:
                    end_session()
                    logger.info(f"Ended enrollment session: {session_id}")

            return 0

        except Exception as e:
            logger.error(f"Enrollment failed: {e}")
            return 1

    def handle_run(self, args) -> int:
        """Handle combined extract and enroll command.

        Args:
            args: Parsed command line arguments

        Returns:
            Exit code
        """
        try:
            logger.info("Running combined extract and enroll process")

            # Extract courses
            extract_result = self.handle_extract(args)
            if extract_result != 0:
                return extract_result

            # Enroll in courses
            args.input = "courses_to_enroll.json"  # Use default output from extract
            return self.handle_enroll(args)

        except Exception as e:
            logger.error(f"Combined run failed: {e}")
            return 1

    def run(self, args: list[str] = None) -> int:
        """Run the unified CLI.

        Args:
            args: Command line arguments (defaults to sys.argv)

        Returns:
            Exit code
        """
        try:
            # Parse arguments
            parsed_args = self.parser.parse_args(args)

            # Setup logging
            if parsed_args.structured_logging and self.enhanced_features:
                setup_structured_logging("udemy-miner")

            # Load configuration
            if not self.load_configuration(parsed_args.config):
                return 1

            # Handle special commands first
            if self.enhanced_features:
                if parsed_args.update_check:
                    return self.handle_update_check()

                if parsed_args.stats:
                    return self.handle_statistics(parsed_args.days)

                if parsed_args.validate_config:
                    return self.handle_config_validation(parsed_args.validate_config)

                if parsed_args.create_default_config:
                    return self.handle_create_default_config(parsed_args.create_default_config)

                if parsed_args.test_cookies:
                    return self.handle_test_cookies(parsed_args.browser)

            # Handle main commands
            if parsed_args.command == "extract":
                return self.handle_extract(parsed_args)
            elif parsed_args.command == "enroll":
                return self.handle_enroll(parsed_args)
            elif parsed_args.command == "run":
                return self.handle_run(parsed_args)
            else:
                # No command specified, show help
                self.parser.print_help()
                return 0

        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if parsed_args.debug:
                import traceback

                traceback.print_exc()
            return 1


def main():
    """Main entry point for the unified CLI."""
    cli = UnifiedCLI()
    return cli.run()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
