"""Command-Line Interface for Discounted Udemy Course Enroller (DUCE) - Extractor.

This script provides a CLI to extract Udemy course information from various
scraping sources. It uses threading to scrape multiple sites concurrently
and saves the collected course data to a JSON file.
"""
# TODO: Standardize the code with the other projects. Current code has been migrated from other project.


import json
import os
import sys
import threading
import time
import traceback

from base import VERSION, Scraper, scraper_dict  # Removed Udemy, LoginException
from logger import LoggerAdapter, get_logger
from tqdm import tqdm

# DUCE-CLI Extractor - Discounted Udemy Course Enroller (Extraction Part)

OUTPUT_FILE = "courses_to_enroll.json"
logger = get_logger(__name__)


def check_dependencies():
    """Check if required dependencies are installed and provide installation guidance."""
    missing_deps = []

    # Check for Playwright
    try:
        import playwright
        try:
            from playwright.sync_api import sync_playwright
            # Try to see if browsers are installed
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                except Exception:
                    logger.warning("Playwright is installed but browsers are missing.")
                    logger.warning("Run: playwright install")
                    logger.warning("Some scrapers (Real Discount, Udemy Free Courses, Udemy Freebies) may fail without Playwright browsers.")
        except ImportError:
            missing_deps.append("playwright")
    except ImportError:
        missing_deps.append("playwright")

    # Check for other optional dependencies
    try:
        import cloudscraper
    except ImportError:
        missing_deps.append("cloudscraper")

    if missing_deps:
        logger.warning(f"Optional dependencies missing: {', '.join(missing_deps)}")
        logger.warning("Install with: pip install " + " ".join(missing_deps))
        logger.warning("Then run: playwright install (if playwright was missing)")
        logger.warning("Some scrapers may fail or have reduced functionality.")

    return len(missing_deps) == 0


def create_scraping_thread(site: str, scraper):
    """Creates and monitors a thread for scraping a specific site.

    Args:
        site (str): The name of the site to scrape
        scraper: The scraper instance to use
    """
    # Create a logger specific to this site's scraping process
    thread_logger = LoggerAdapter(get_logger(f"scraper.{site}"), {"site": site})
    code_name = scraper_dict[site]

    try:
        # Start the scraping thread
        t = threading.Thread(target=getattr(scraper, code_name), daemon=True)
        t.start()

        # Wait for the scraper to initialize
        timeout = 240  # Increased timeout to 240 seconds for slower sites
        start_time = time.time()

        # Add a check interval to avoid busy waiting
        check_interval = 1.0  # Check status every 1 second (reduced frequency)

        # Wait for initialization with better error handling
        initialization_complete = False
        while not initialization_complete:
            if time.time() - start_time > timeout:
                thread_logger.error(f"Timeout waiting for {site} scraper to initialize")
                setattr(scraper, f"{code_name}_length", -1)  # Mark as failed
                setattr(scraper, f"{code_name}_done", True)
                return  # Exit thread function on timeout

            # Sleep for the check interval to avoid busy waiting
            time.sleep(check_interval)

            # Check if the scraper has finished with an error during initialization
            if getattr(scraper, f"{code_name}_done", False):
                if getattr(scraper, f"{code_name}_length", 0) == -1:
                    thread_logger.error(f"Scraper for {site} failed during initialization")
                    return
                else:
                    # Scraper completed during initialization - this is normal for some sites
                    initialization_complete = True
                    break

            # Check if length was set (indicates successful initialization)
            current_length = getattr(scraper, f"{code_name}_length", 0)
            if current_length > 0:
                initialization_complete = True
                break

        # Check if initialization failed (marked by scraper itself)
        final_length = getattr(scraper, f"{code_name}_length", 0)
        if final_length == -1:
            thread_logger.error(f"Error initializing scraper for: {site}")
            return  # Exit thread function on init error

        # If scraper completed during initialization, no need for progress monitoring
        if getattr(scraper, f"{code_name}_done", False):
            courses = getattr(scraper, f"{code_name}_data", [])
            if courses and len(courses) > 0:
                thread_logger.info(
                    f"Scraping completed for {site} with {len(courses)} courses"
                )
            else:
                thread_logger.warning(f"No courses found for {site}")
            return

        # Create and update progress bar with better error handling
        try:
            progress_bar = tqdm(
                total=max(1, final_length),  # Ensure total is at least 1 to avoid division by zero
                desc=site,
                leave=True,  # leave=True to see finished bars
                unit="items",
                dynamic_ncols=True,  # Adjust width dynamically
            )
        except Exception as e:
            thread_logger.warning(f"Could not create progress bar for {site}: {e}")
            progress_bar = None

        prev_progress = 0

        # Monitor progress with improved timeout handling
        scraping_timeout = timeout * 2  # Double the initialization timeout for scraping
        while not getattr(scraper, f"{code_name}_done"):
            time.sleep(check_interval)  # Use same check interval for consistency
            current_progress = getattr(scraper, f"{code_name}_progress", 0)

            # Update progress bar safely
            if progress_bar and current_progress > prev_progress:
                try:
                    progress_bar.update(current_progress - prev_progress)
                    prev_progress = current_progress
                except Exception as e:
                    thread_logger.warning(f"Progress bar update failed for {site}: {e}")

            # Add a timeout for the entire scraping process
            elapsed_time = time.time() - start_time
            if elapsed_time > scraping_timeout:
                thread_logger.error(f"Timeout during scraping process for {site} after {elapsed_time:.1f}s")
                setattr(scraper, f"{code_name}_done", True)
                setattr(
                    scraper, f"{code_name}_length", max(prev_progress, 1)
                )  # Set final length to current progress
                break

        # Ensure progress bar reaches 100% safely
        if progress_bar:
            try:
                final_length = getattr(scraper, f"{code_name}_length", 0)
                if final_length > 0 and prev_progress < final_length:
                    progress_bar.update(final_length - prev_progress)
                progress_bar.close()
            except Exception as e:
                thread_logger.warning(f"Error closing progress bar for {site}: {e}")

        # Process potential partial results
        courses = getattr(scraper, f"{code_name}_data", [])
        # Even if we only got partial results, save them
        if courses and len(courses) > 0:
            thread_logger.info(
                f"Scraping completed for {site} with {len(courses)} courses"
            )
        else:
            thread_logger.warning(f"No courses found for {site}")

    except Exception as exc:
        # Catch exceptions within the thread to prevent crashing the main process
        error_msg = str(exc)
        error_traceback = traceback.format_exc()

        # Store the error for later retrieval
        setattr(scraper, f"{code_name}_error", error_traceback)

        thread_logger.error(f"Error in {site} scraper thread: {error_msg}")
        thread_logger.debug(f"Full traceback for {site}: {error_traceback}")
        thread_logger.info(f"Version: {VERSION}")

        # Mark as failed
        setattr(scraper, f"{code_name}_length", -1)
        setattr(scraper, f"{code_name}_done", True)

        # Close progress bar if it exists
        try:
            if 'progress_bar' in locals() and progress_bar:
                progress_bar.close()
        except:
            pass


def main_extract():
    """Main function to handle the course extraction process."""
    logger.info(f"Starting DUCE-CLI Extractor v{VERSION}")

    # Check dependencies first
    logger.info("Checking dependencies...")
    check_dependencies()

    # Load basic settings to know which sites to scrape (optional, can be hardcoded or simplified)
    # We don't need login/enrollment settings here.
    sites_to_scrape = list(scraper_dict.keys())  # Default: scrape all
    try:
        # Attempt to load settings to get the list of sites if specified by user
        settings_file = "duce-cli-settings.json"  # Assume standard settings file name
        if os.path.exists(settings_file):
            with open(settings_file, encoding="utf-8") as f:
                settings = json.load(f)
                # Use sites enabled in settings if available
                if "sites" in settings and isinstance(settings["sites"], dict):
                    sites_to_scrape = [
                        site for site, enabled in settings["sites"].items() if enabled
                    ]
                    if not sites_to_scrape:
                        logger.warning(
                            "No sites enabled in settings file. Defaulting to all sites."
                        )
                        sites_to_scrape = list(scraper_dict.keys())
                else:
                    logger.warning(
                        "'sites' key not found or invalid in settings. Defaulting to all sites."
                    )
    except Exception as e:
        logger.error(f"Error loading settings to determine sites: {e!s}")
        logger.warning("Defaulting to scrape all sites.")

    if not sites_to_scrape:
        logger.error("No sites selected for scraping. Exiting.")
        return

    logger.info(f"Selected sites for scraping: {', '.join(sites_to_scrape)}")

    # Initialize scraper and start extraction process
    scraper = Scraper(sites_to_scrape, debug=True)  # Enable debug output
    scraped_data = {}
    try:
        # Get courses from scrapers using the threading function
        logger.info("Starting course extraction from selected sites...")
        scraped_data = scraper.get_scraped_courses(
            lambda site: create_scraping_thread(site, scraper)
        )
        # Wait a moment for progress bars to finish visually
        time.sleep(2)
        logger.info("Extraction process finished.")

        # Accept sites with partial results (length > 0) instead of just filtering out failures
        successful_data = {}
        failed_sites = []

        for site, data in scraped_data.items():
            site_length = getattr(scraper, f"{scraper_dict[site]}_length", 0)
            site_error = getattr(scraper, f"{scraper_dict[site]}_error", "")

            if len(data) > 0 and site_length != -1:
                successful_data[site] = data
                logger.info(f"✓ {site}: {len(data)} courses extracted")
            else:
                failed_sites.append(site)
                if site_error:
                    logger.error(f"✗ {site}: Failed with error - {site_error.split(chr(10))[0]}")  # First line of error
                else:
                    logger.error(f"✗ {site}: Failed - no courses found")

        if failed_sites:
            logger.warning(f"Extraction failed for sites: {', '.join(failed_sites)}")

        # Save successful results to JSON file
        if successful_data:
            total_courses_found = sum(
                len(courses) for courses in successful_data.values()
            )
            logger.info(f"Found {total_courses_found} potential courses from {len(successful_data)} sites.")
            try:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(successful_data, f, indent=4, ensure_ascii=False)
                logger.info(f"Successfully saved course list to '{OUTPUT_FILE}'")

                # Provide summary statistics
                for site, courses in successful_data.items():
                    logger.info(f"  {site}: {len(courses)} courses")

            except OSError as e:
                logger.error(f"Error saving course list to '{OUTPUT_FILE}': {e}")
        else:
            logger.warning(
                "No courses found or all scrapers failed. Output file not created."
            )
            logger.warning("This might be due to:")
            logger.warning("  1. Network connectivity issues")
            logger.warning("  2. Missing dependencies (run: pip install playwright cloudscraper)")
            logger.warning("  3. Missing Playwright browsers (run: playwright install)")
            logger.warning("  4. Sites being temporarily unavailable")

    except Exception:
        # Catch unexpected errors during the main scraping coordination
        e = traceback.format_exc()
        logger.error(f"An unexpected error occurred during extraction: {e}")
        logger.info(f"Version: {VERSION}")

    finally:
        # Removed the input prompt to allow for easier scripting if needed
        logger.info("Extraction script finished.")
        # input("Press Enter to exit...") # Optional: uncomment if you want to pause


# Removed handle_login function
# Removed display_results function

# Execute main_extract function if script is run directly
if __name__ == "__main__":
    try:
        main_extract()  # Renamed main to main_extract
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user.")
        sys.exit(0)
