import logging
import sys

# Attempt to set up project path for imports if needed.
# This depends on how the project is structured and run.
# If 'src' is not automatically in sys.path when run from root, this might be needed.
# import os
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.dirname(SCRIPT_DIR)) # Add project root to path

try:
    from src.config.settings import Settings, get_settings
    from src.utils.backup_utils import BackupManager
    from src.utils.logging import setup_logging  # Assuming a central logging setup
except ImportError as e:
    # Fallback basic logging if custom setup fails or modules not found
    logging.basicConfig(
        level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.error(
        f"Failed to import necessary modules: {e}. Ensure PYTHONPATH is set correctly or script is run from project root."
    )
    sys.exit(1)


def main():
    # Setup centralized logging if available
    # This might need adjustment based on how your logging is configured.
    # If setup_logging() takes arguments or settings, pass them.
    try:
        # Assuming setup_logging configures root logger or specific loggers.
        # If it returns a logger, you might want to use that.
        setup_logging()
        logger = logging.getLogger("watchtower.run_backup")  # Use a named logger
    except Exception as log_e:
        # Fallback if setup_logging fails
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Could not initialize custom logging due to: {log_e}. Using basic logging."
        )

    logger.info("Starting backup process...")

    try:
        settings: Settings = get_settings()

        # Validate essential settings for backup
        if (
            not hasattr(settings, "google_drive")
            or not settings.google_drive.backup_folder_id
            or not settings.google_drive.credentials_file
        ):
            logger.error(
                "Google Drive configuration (backup_folder_id, credentials_file) is missing or incomplete in settings."
            )
            logger.error(
                "Please ensure WATCHTOWER_GOOGLE_DRIVE__BACKUP_FOLDER_ID and WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE are set in your .env file or environment variables."
            )
            sys.exit(1)

        if not settings.project_root:
            logger.error(
                "Project root is not defined in settings. Cannot determine paths for data/logs."
            )
            sys.exit(1)

        # Define folders to back up using paths from settings
        # These should be relative paths from project_root, as BackupManager expects them.
        # The Settings class should ideally resolve these to absolute paths or provide them as such.
        # For BackupManager, we give paths relative to project_root if they are not absolute.
        # Example: settings.data_dir could be "data" or "/path/to/project/data"
        # BackupManager's compress_folders will handle making them absolute if needed.

        folders_to_backup = []
        if settings.data_dir:
            folders_to_backup.append(settings.data_dir)
        else:
            logger.warning(
                "settings.data_dir is not defined. Skipping data folder backup."
            )

        if settings.logs_dir:
            folders_to_backup.append(settings.logs_dir)
        else:
            logger.warning(
                "settings.logs_dir is not defined. Skipping logs folder backup."
            )

        if not folders_to_backup:
            logger.error(
                "No folders specified for backup (data_dir and logs_dir are not set in settings). Aborting."
            )
            sys.exit(1)

        logger.info(f"Target folders for backup: {folders_to_backup}")
        logger.info(f"Using project root: {settings.project_root}")
        logger.info(
            f"Google Drive Credentials File: {settings.google_drive.credentials_file}"
        )
        logger.info(
            f"Google Drive Backup Folder ID: {settings.google_drive.backup_folder_id}"
        )

        backup_manager = BackupManager(settings)
        success = backup_manager.run_backup_process(folders_to_backup)

        if success:
            logger.info("Backup process completed successfully.")
            sys.exit(0)
        else:
            logger.error("Backup process failed. Check logs for details.")
            sys.exit(1)

    except FileNotFoundError as fnf_error:
        logger.error(
            f"Backup initialization failed: {fnf_error}. This often means the client_secrets.json file is missing or misconfigured."
        )
        logger.error(
            "Ensure the path in WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE is correct and the file exists."
        )
        sys.exit(1)
    except (
        ValueError
    ) as val_error:  # Catch specific errors from BackupManager or settings
        logger.error(
            f"Backup initialization failed due to a configuration value error: {val_error}"
        )
        sys.exit(1)
    except ImportError as imp_error:  # Should be caught above, but as a safeguard
        logger.error(f"Import error during backup script execution: {imp_error}")
        sys.exit(1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during the backup script execution: {e}",
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
