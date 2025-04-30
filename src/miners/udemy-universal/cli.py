# TODO: Standardize the code with the other projects. Current code has been migrated from other project.


import threading
import time
import traceback
import sys
import os
import json

from tqdm import tqdm

from base import VERSION, Scraper, scraper_dict # Removed Udemy, LoginException
from colors import bw, by, fb, fg, fr, fy
from logger import get_logger, LoggerAdapter

# DUCE-CLI Extractor - Discounted Udemy Course Enroller (Extraction Part)

OUTPUT_FILE = "courses_to_enroll.json"
logger = get_logger(__name__)

def create_scraping_thread(site: str, scraper):
    """
    Creates and monitors a thread for scraping a specific site.

    Args:
        site (str): The name of the site to scrape
        scraper: The scraper instance to use
    """
    # Create a logger specific to this site's scraping process
    thread_logger = LoggerAdapter(get_logger(f"scraper.{site}"), {'site': site})
    code_name = scraper_dict[site]
    try:
        # Start the scraping thread
        t = threading.Thread(target=getattr(scraper, code_name), daemon=True)
        t.start()

        # Wait for the scraper to initialize
        timeout = 180  # Increased timeout to 180 seconds (from 120) for initialization
        start_time = time.time()
        
        # Add a check interval to avoid busy waiting
        check_interval = 0.5  # Check status every 0.5 seconds
        
        while getattr(scraper, f"{code_name}_length") == 0:
            if time.time() - start_time > timeout:
                thread_logger.error(f"Timeout waiting for {site} scraper to initialize")
                setattr(scraper, f"{code_name}_length", -1) # Mark as failed
                setattr(scraper, f"{code_name}_done", True)
                return # Exit thread function on timeout
            
            # Sleep for the check interval to avoid busy waiting
            time.sleep(check_interval)
            
            # Check if the scraper has finished with an error during initialization
            if getattr(scraper, f"{code_name}_done", False) and getattr(scraper, f"{code_name}_length", 0) == -1:
                thread_logger.error(f"Scraper for {site} failed during initialization")
                return

        # Check if initialization failed (marked by scraper itself)
        if getattr(scraper, f"{code_name}_length") == -1:
            thread_logger.error(f"Error initializing scraper for: {site}")
            return # Exit thread function on init error

        # Create and update progress bar
        progress_bar = tqdm(
            total=getattr(scraper, f"{code_name}_length"), desc=site, leave=True # leave=True to see finished bars
        )
        prev_progress = 0

        # Monitor progress
        while not getattr(scraper, f"{code_name}_done"):
            time.sleep(check_interval)  # Use same check interval for consistency
            current_progress = getattr(scraper, f"{code_name}_progress")
            if current_progress > prev_progress:  # Only update if progress increased
                progress_bar.update(current_progress - prev_progress)
                prev_progress = current_progress
                
            # Add a timeout for the entire scraping process
            if time.time() - start_time > timeout * 2:  # Double the initialization timeout
                thread_logger.error(f"Timeout during scraping process for {site}")
                setattr(scraper, f"{code_name}_done", True)
                setattr(scraper, f"{code_name}_length", prev_progress)  # Set final length to current progress
                break

        # Ensure progress bar reaches 100%
        final_length = getattr(scraper, f"{code_name}_length")
        if final_length > 0 and prev_progress < final_length: # Avoid update if length is 0 or -1
            progress_bar.update(final_length - prev_progress)

        # Process potential partial results
        courses = getattr(scraper, f"{code_name}_data", [])
        # Even if we only got partial results, save them
        if courses and len(courses) > 0:
            thread_logger.info(f"Scraping completed for {site} with {len(courses)} courses")
        else:
            thread_logger.warning(f"No courses found for {site}")
            
        progress_bar.close()

    except Exception as e:
        # Catch exceptions within the thread to prevent crashing the main process
        error = getattr(scraper, f"{code_name}_error", traceback.format_exc())
        thread_logger.error(f"Error in {site} scraper thread: {error}")
        thread_logger.info(f"Version: {VERSION}")
        setattr(scraper, f"{code_name}_length", -1) # Mark as failed if exception occurs
        setattr(scraper, f"{code_name}_done", True)


def main_extract():
    """Main function to handle the course extraction process"""
    logger.info(f"Starting DUCE-CLI Extractor v{VERSION}")

    # Load basic settings to know which sites to scrape (optional, can be hardcoded or simplified)
    # We don't need login/enrollment settings here.
    sites_to_scrape = list(scraper_dict.keys()) # Default: scrape all
    try:
        # Attempt to load settings to get the list of sites if specified by user
        settings_file = "duce-cli-settings.json" # Assume standard settings file name
        if os.path.exists(settings_file):
             with open(settings_file, 'r') as f:
                settings = json.load(f)
                # Use sites enabled in settings if available
                if "sites" in settings and isinstance(settings["sites"], dict):
                    sites_to_scrape = [site for site, enabled in settings["sites"].items() if enabled]
                    if not sites_to_scrape:
                        logger.warning("No sites enabled in settings file. Defaulting to all sites.")
                        sites_to_scrape = list(scraper_dict.keys())
                else:
                    logger.warning("'sites' key not found or invalid in settings. Defaulting to all sites.")
    except Exception as e:
        logger.error(f"Error loading settings to determine sites: {str(e)}")
        logger.warning("Defaulting to scrape all sites.")

    if not sites_to_scrape:
        logger.error("No sites selected for scraping. Exiting.")
        return

    logger.info(f"Selected sites for scraping: {', '.join(sites_to_scrape)}")

    # Initialize scraper and start extraction process
    scraper = Scraper(sites_to_scrape, debug=True) # Enable debug output
    scraped_data = {}
    try:
        # Get courses from scrapers using the threading function
        logger.info("Starting course extraction from selected sites...")
        scraped_data = scraper.get_scraped_courses(
            lambda site: create_scraping_thread(site, scraper)
        )
        # Wait a moment for progress bars to finish visually
        time.sleep(1)
        logger.info("Extraction process finished.")

        # Accept sites with partial results (length > 0) instead of just filtering out failures
        successful_data = {site: data for site, data in scraped_data.items() 
                          if len(data) > 0 and getattr(scraper, f"{scraper_dict[site]}_length", 0) != -1}
        
        # Sites that failed completely (no courses extracted)
        failed_sites = [site for site, data in scraped_data.items() 
                       if len(data) == 0 or getattr(scraper, f"{scraper_dict[site]}_length", 0) == -1]

        if failed_sites:
            logger.error(f"Extraction failed for sites: {', '.join(failed_sites)}")

        # Save successful results to JSON file
        if successful_data:
            total_courses_found = sum(len(courses) for courses in successful_data.values())
            logger.info(f"Found {total_courses_found} potential courses.")
            try:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(successful_data, f, indent=4, ensure_ascii=False)
                logger.info(f"Successfully saved course list to '{OUTPUT_FILE}'")
            except IOError as e:
                logger.error(f"Error saving course list to '{OUTPUT_FILE}': {e}")
        else:
            logger.warning("No courses found or all scrapers failed. Output file not created.")


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
        main_extract() # Renamed main to main_extract
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user.")
        sys.exit(0)
