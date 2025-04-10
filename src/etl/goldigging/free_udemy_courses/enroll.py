# TODO: Standardize the code with the other projects. Current code has been migrated from other project.

import json
import traceback
import sys
import os
import time

from base import VERSION, LoginException, Udemy, scraper_dict # Import Udemy and LoginException
from colors import bw, by, fb, fg, fr, fy
from logger import get_logger, LoggerAdapter

# DUCE-CLI Enroller - Discounted Udemy Course Enroller (Enrollment Part)

INPUT_FILE = "courses_to_enroll.json"
logger = get_logger(__name__)

def handle_login(udemy):
    """
    Handle the login process with multiple methods

    Args:
        udemy: The Udemy client instance

    Returns:
        bool: True if login successful, False otherwise
    """
    login_logger = LoggerAdapter(get_logger("login"), {'user': getattr(udemy, 'display_name', None)})
    max_attempts = 3
    attempts = 0

    while attempts < max_attempts:
        try:
            # Determine login method based on loaded settings
            if udemy.settings.get("use_browser_cookies", False): # Use .get for safety
                login_logger.info("Trying to login using Browser Cookies")
                try:
                    udemy.fetch_cookies()
                    login_method = "Browser Cookies"
                except Exception as cookie_error:
                     login_logger.error(f"Failed to load browser cookies: {cookie_error}")
                     login_logger.warning("Ensure browser is supported and cookies exist. Trying other methods...")
                     udemy.settings["use_browser_cookies"] = False # Disable for this run
                     attempts += 1 # Count as an attempt
                     if attempts >= max_attempts: return False
                     continue # Skip to next attempt/method
            elif udemy.settings.get("email") and udemy.settings.get("password"):
                email, password = udemy.settings["email"], udemy.settings["password"]
                login_method = "Saved Email and Password"
                login_logger.info(f"Trying to login using {login_method}")
                udemy.manual_login(email, password)
            else:
                login_logger.info("Login required (credentials not found/saved).")
                email = input("Email: ")
                password = input("Password: ")
                login_method = "Manual Email and Password"
                login_logger.info(f"Trying to login using {login_method}")
                udemy.manual_login(email, password)

            # Verify login status
            udemy.get_session_info()

            # Save credentials if login successful and they were entered manually
            if "Manual Email" in login_method:
                 # Ask user if they want to save credentials
                save_choice = input(f"Login successful as {udemy.display_name}. Save credentials? (y/n): ").lower()
                if save_choice == 'y':
                    udemy.settings["email"] = email
                    udemy.settings["password"] = password # Consider security implications of saving passwords
                    udemy.save_settings()
                    login_logger.info("Credentials saved.")
                else:
                    # Ensure they are not saved if user declines
                    udemy.settings["email"] = ""
                    udemy.settings["password"] = ""

            # Update logger with username after successful login
            login_logger.extra['user'] = getattr(udemy, 'display_name', None)
            login_logger.info(f"Login successful for {udemy.display_name}")
            return True # Login successful

        except LoginException as e:
            attempts += 1
            login_logger.error(f"Login failed: {str(e)}")

            # Handle specific login method failures
            if "Browser" in login_method:
                login_logger.warning("Login via browser cookies failed. Trying credential login if available.")
                udemy.settings["use_browser_cookies"] = False # Don't retry cookies this session
            elif "Email" in login_method:
                # Clear potentially incorrect saved credentials
                login_logger.warning("Login via saved/manual credentials failed.")
                udemy.settings["email"], udemy.settings["password"] = "", ""

            if attempts < max_attempts:
                login_logger.info(f"Retrying... (Attempt {attempts + 1}/{max_attempts})")
            else:
                login_logger.error("Maximum login attempts reached.")

        except Exception as e:
             attempts += 1
             login_logger.error(f"An unexpected error occurred during login: {e}")
             login_logger.debug(traceback.format_exc())  # Log full traceback at debug level
             if attempts < max_attempts:
                 login_logger.info(f"Retrying... (Attempt {attempts + 1}/{max_attempts})")
             else:
                 login_logger.error("Maximum login attempts reached due to errors.")

    return False # Failed to login after all attempts


def display_results(udemy):
    """
    Display enrollment results

    Args:
        udemy: The Udemy client instance
    """
    results_logger = LoggerAdapter(get_logger("results"), 
                                  {'user': getattr(udemy, 'display_name', None)})
    
    results_logger.info("--- Enrollment Summary ---")
    results_logger.info(f"Successfully Enrolled: {udemy.successfully_enrolled_c}")
    results_logger.info(
        f"Amount Saved: {round(udemy.amount_saved_c, 2)} {udemy.currency.upper() if hasattr(udemy, 'currency') else 'N/A'}"
    )
    results_logger.info(f"Already Enrolled: {udemy.already_enrolled_c}")
    results_logger.info(f"Excluded Courses: {udemy.excluded_c}")
    results_logger.info(f"Expired/Failed Courses: {udemy.expired_c}")

    # Calculate total enrolled ONLY if login was successful and courses were processed
    if hasattr(udemy, 'enrolled_courses'):
        total_courses = len(udemy.enrolled_courses)
        results_logger.info(f"Total Enrolled Courses (including previously owned): {total_courses}")
    else:
        results_logger.warning("Could not determine total enrolled courses (Login might have failed).")


def main_enroll():
    """Main function to handle the enrollment process"""
    logger.info(f"Starting DUCE-CLI Enroller v{VERSION}")

    # Load scraped courses
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        course_count = sum(len(v) for v in scraped_data.values())
        if course_count == 0:
            logger.warning(f"No courses found in {INPUT_FILE}. Nothing to enroll.")
            return
        logger.info(f"Loaded {course_count} courses from {INPUT_FILE}")
        
        # Log details of courses by source
        for site, courses in scraped_data.items():
            logger.info(f"Found {len(courses)} courses from {site}")
    except FileNotFoundError:
        logger.error(f"Error: Input file '{INPUT_FILE}' not found.")
        logger.warning("Please run the extractor script (cli.py) first.")
        return
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON from '{INPUT_FILE}'. It might be corrupted.")
        return
    except Exception as e:
        logger.error(f"Error loading courses file: {e}")
        logger.debug(traceback.format_exc())  # Log the full traceback at debug level
        return

    # Initialize Udemy client
    udemy = Udemy("cli", debug=False) # Set debug=True for verbose enrollment output

    try:
        udemy.load_settings()
        logger.info("Settings loaded.")
        
        # Log important settings for debugging
        log_settings = {
            "use_browser_cookies": udemy.settings.get("use_browser_cookies", False),
            "has_saved_credentials": bool(udemy.settings.get("email") and udemy.settings.get("password")),
            "enabled_sites": [site for site, enabled in udemy.settings.get("sites", {}).items() if enabled],
            "enabled_languages": [lang for lang, enabled in udemy.settings.get("languages", {}).items() if enabled],
            "min_rating": udemy.settings.get("min_rating", 0),
            "save_txt": udemy.settings.get("save_txt", True),
            "discounted_only": udemy.settings.get("discounted_only", False),
            "course_update_threshold_months": udemy.settings.get("course_update_threshold_months", 24)
        }
        logger.info(f"Active settings: {json.dumps(log_settings, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        logger.debug(traceback.format_exc())  # Log the full traceback at debug level
        logger.warning("Proceeding with default or potentially empty settings.")
        # Provide default structure if necessary, though base.py might handle this
        if not hasattr(udemy, 'settings'):
            udemy.settings = {
                "email": "", "password": "", "use_browser_cookies": False,
                "sites": {site: True for site in scraper_dict.keys()}, # Default all sites enabled in settings context
                "categories": {}, "languages": {"en": True}, # Example defaults
                "min_rating": 0, "max_price": 0, "min_reviews": 0,
                "title_exclude": [], "instructor_exclude": [],
                "save_txt": True, "discounted_only": False,
                "course_update_threshold_months": 24
            }

    # Check for updates (optional, can be done before or after login)
    try:
        login_title, main_title = udemy.check_for_update()
        if "Update" in login_title:
            logger.warning(f"{login_title} available. Please update!")
        else:
            logger.info(f"Version: {VERSION} (Up-to-date)")
    except Exception as e:
        logger.warning(f"Could not check for updates: {e}")
        logger.debug(traceback.format_exc())  # Log the full traceback at debug level

    # Handle login process
    logger.info("Attempting login...")
    login_successful = handle_login(udemy)

    if not login_successful:
        logger.error("Failed to login. Cannot proceed with enrollment.")
        return # Exit if login fails

    # If login was successful, save potentially updated settings (like saved credentials)
    udemy.save_settings()
    logger.info(f"Logged in as {udemy.display_name}")
    
    # Log account details for debugging
    if hasattr(udemy, 'user_id'):
        logger.info(f"Account ID: {udemy.user_id}")
    if hasattr(udemy, 'currency'):
        logger.info(f"Account Currency: {udemy.currency.upper()}")

    # Check user settings for validity (e.g., selected categories/languages)
    # This uses the loaded settings, not the sites from scraping phase
    if udemy.is_user_dumb(): # Checks categories, languages etc.
        logger.error("Invalid configuration detected in settings (e.g., no languages or categories selected). Please check your settings file!")
        logger.warning("Enrollment might skip many courses based on current settings.")
        # Decide whether to proceed or exit
        proceed = input("Proceed anyway? (y/n): ").lower()
        if proceed != 'y':
            logger.info("User chose not to proceed with potentially invalid settings.")
            return
        logger.warning("Proceeding with potentially invalid settings as per user's request.")

    # Set the loaded data for enrollment processing
    udemy.scraped_data = scraped_data

    try:
        # Enroll in courses
        logger.info("Starting enrollment process...")
        
        # Record start time for performance logging
        start_time = time.time()
        
        udemy.start_enrolling()
        
        # Log performance metrics
        elapsed_time = time.time() - start_time
        courses_processed = (udemy.successfully_enrolled_c + udemy.already_enrolled_c + 
                            udemy.excluded_c + udemy.expired_c)
        logger.info(f"Enrollment process completed in {elapsed_time:.2f} seconds")
        logger.info(f"Average processing time per course: {elapsed_time/max(1, courses_processed):.2f} seconds")

        # Display results
        display_results(udemy)

    except Exception:
        e = traceback.format_exc()
        error_msg = f"Error during enrollment:\n{e}"
        if hasattr(udemy, "link") and hasattr(udemy, "title"):
            error_msg += f"\nLast attempted Course: {getattr(udemy, 'title', 'N/A')}\nURL: {getattr(udemy, 'link', 'N/A')}"
        error_msg += f"\nVersion: {VERSION}"
        logger.error(error_msg)

    finally:
        logger.info("Enrollment script finished.")
        input("Press Enter to exit...")


# Execute main function if script is run directly
if __name__ == "__main__":
    try:
        main_enroll()
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user.")
        sys.exit(0)

