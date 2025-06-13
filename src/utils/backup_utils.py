import datetime
import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Tuple

# Ensure PyDrive2 is installed. If not, this will fail at runtime.
# It should be in requirements.txt
try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    from pydrive2.files import GoogleDriveFile # For type hinting
except ImportError:
    # This allows the module to be imported and potentially used for other things
    # if pydrive2 is missing, but gdrive functions will fail.
    # A better approach is to ensure dependencies are met.
    GoogleAuth = None
    GoogleDrive = None
    GoogleDriveFile = None
    print("ERROR: PyDrive2 library is not installed. Google Drive functionality will not work.")
    print("Please install it using: pip install PyDrive2")


# Assuming Settings can be imported like this.
# This might need adjustment based on actual project structure and how settings are accessed.
# e.g., from src.config import get_settings
# For now, we'll assume a direct import is possible for the class definition.
from src.config.settings import Settings
from src.config.models import GoogleDriveConfig # Assuming GoogleDriveConfig is here

# Configure basic logging
# Using a named logger is better practice
module_logger = logging.getLogger(f"watchtower.{__name__}")
# Ensure basicConfig is called only once, preferably at application entry point.
# If not, this might interfere with existing logging setups.
# For a utility module, it's often better to just get the logger and let the app configure it.
# However, for standalone testing (if __name__ == '__main__'), basicConfig is useful.

class BackupManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not GoogleAuth or not GoogleDrive: # Check if PyDrive2 loaded
            module_logger.error("PyDrive2 not loaded. Cannot initialize BackupManager for Google Drive.")
            # Or raise an error: raise ImportError("PyDrive2 is required for BackupManager but not found.")
            self.drive = None # Ensure drive is None if auth fails
            self.gauth = None
            self.backup_folder_id = None
            return

        self.gauth = GoogleAuth()
        # Ensure google_drive settings are present
        if not hasattr(self.settings, 'google_drive') or not isinstance(self.settings.google_drive, GoogleDriveConfig):
            module_logger.error("GoogleDriveConfig not found in settings.")
            raise ValueError("GoogleDriveConfig not found or misconfigured in settings.")

        self.backup_folder_id = self.settings.google_drive.backup_folder_id
        if not self.backup_folder_id:
            module_logger.error("Google Drive backup_folder_id is not set in settings.")
            raise ValueError("Google Drive backup_folder_id is not set in settings.")

        self.drive = self._authenticate_gdrive()


    def _authenticate_gdrive(self) -> GoogleDrive:
        """Authenticates with Google Drive."""
        if not self.gauth: # Should not happen if constructor checks PyDrive2 import
             module_logger.error("GoogleAuth not initialized.")
             raise RuntimeError("GoogleAuth not initialized, cannot authenticate.")

        credentials_file_path_str = self.settings.google_drive.credentials_file
        credentials_file = Path(credentials_file_path_str)

        if not credentials_file.is_absolute():
            # Assuming project_root is an absolute path
            if not self.settings.project_root or not Path(self.settings.project_root).is_absolute():
                module_logger.error("Project root is not an absolute path or not set. Cannot resolve relative credentials_file path.")
                raise ValueError("Project root is not an absolute path or not set.")
            credentials_file = Path(self.settings.project_root) / credentials_file_path_str

        if not credentials_file.exists():
            module_logger.error(f"Google Drive client_secrets file not found at {credentials_file}")
            raise FileNotFoundError(f"Google Drive client_secrets file not found at {credentials_file}")

        self.gauth.settings['client_config_file'] = str(credentials_file)

        # Path for saving/loading OAuth 2.0 credentials after first authorization
        # Store it in the same directory as client_secrets.json for organization
        saved_credentials_path = credentials_file.parent / "pydrive_credentials.json"
        self.gauth.settings['save_credentials_file'] = str(saved_credentials_path)
        self.gauth.settings['save_credentials'] = True
        self.gauth.settings['save_credentials_backend'] = 'file'
        self.gauth.settings['get_refresh_token'] = True # Important for non-interactive refresh

        try:
            self.gauth.LoadCredentialsFile(saved_credentials_path) # Try to load saved credentials
        except Exception as e: # PyDrive2 might raise various errors here
            module_logger.info(f"Could not load saved credentials from {saved_credentials_path}: {e}. Will attempt new auth.")
            self.gauth.credentials = None # Ensure it's None if loading failed

        if self.gauth.credentials is None:
            module_logger.info("No valid saved credentials found. Attempting local web server authentication.")
            try:
                self.gauth.LocalWebserverAuth() # Opens browser for user authorization
            except Exception as e:
                module_logger.error(f"LocalWebserverAuth failed: {e}. This requires user interaction or a pre-generated '{saved_credentials_path}'.")
                module_logger.error(f"For server environments, ensure '{saved_credentials_path}' is present and valid, or use a service account.")
                raise RuntimeError(f"Google Drive authentication failed: {e}")
        elif self.gauth.access_token_expired:
            module_logger.info("Google Drive credentials expired. Refreshing token.")
            try:
                self.gauth.Refresh()
            except Exception as e: # Catch specific refresh errors if known
                module_logger.error(f"Failed to refresh Google Drive token: {e}")
                module_logger.error(f"Consider re-authenticating by removing '{saved_credentials_path}' and running interactively once.")
                raise RuntimeError(f"Google Drive token refresh failed: {e}")
        else:
            module_logger.info("Google Drive credentials loaded successfully and are valid.")
            # Authorize should not be needed if LoadCredentials or Refresh worked
            # self.gauth.Authorize() # This is implicitly done by PyDrive2 if credentials exist

        # Save credentials if they were obtained or refreshed.
        # PyDrive2 should handle this if 'save_credentials': True and 'save_credentials_file' is set.
        # self.gauth.SaveCredentialsFile(saved_credentials_path) # Explicit save if needed

        return GoogleDrive(self.gauth)

    def _get_archive_basename(self) -> str:
        # This method seems unused in the current main logic, consider removing if not needed.
        # The base name "backup_data_logs" is hardcoded in run_backup_process.
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_data_logs_{timestamp}"

    def compress_folders(self, folders_to_backup: List[str], archive_name_base: str) -> Path:
        """Compresses specified folders into a zip file.
        Args:
            folders_to_backup: List of folder paths (absolute or relative to project root).
            archive_name_base: The base name for the archive (e.g., 'backup_data_logs_local_temp').
                               The '.zip' extension will be added.
        Returns:
            Path to the created zip file.
        """
        project_root = Path(self.settings.project_root)
        # Store temporary zip in project_root or a designated temp subfolder
        # For simplicity, using project_root for now.
        zip_file_path = project_root / f"{archive_name_base}.zip"

        module_logger.info(f"Starting compression of {folders_to_backup} into {zip_file_path}")
        try:
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
                for folder_path_str in folders_to_backup:
                    folder_path = Path(folder_path_str)
                    if not folder_path.is_absolute():
                        folder_path = project_root / folder_path_str

                    if not folder_path.exists() or not folder_path.is_dir():
                        module_logger.warning(f"Folder {folder_path} does not exist or is not a directory. Skipping.")
                        continue

                    module_logger.info(f"Adding folder {folder_path} to archive.")
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            file_abs_path = Path(root) / file
                            # Arcname determines the path inside the zip file.
                            # Relative to project_root to get 'data/file.txt' or 'logs/log.txt'
                            arcname = file_abs_path.relative_to(project_root)
                            zipf.write(file_abs_path, arcname)
            module_logger.info(f"Successfully created archive: {zip_file_path} (Size: {zip_file_path.stat().st_size} bytes)")
            return zip_file_path
        except Exception as e:
            module_logger.error(f"Failed to create archive {zip_file_path}: {e}", exc_info=True)
            if zip_file_path.exists():
                try:
                    os.remove(zip_file_path) # Clean up partial archive
                except OSError as ose:
                    module_logger.error(f"Failed to remove partial archive {zip_file_path}: {ose}")
            raise

    def _upload_single_file(self, local_file_path: Path, file_name_on_drive: str) -> str:
        """
        Uploads a single file to Google Drive. If a file with the same name exists, it's deleted first.
        This is intended for uploading the 'latest' backup.
        Returns:
            The ID of the uploaded file on Google Drive.
        """
        if not self.drive:
            module_logger.error("Google Drive not authenticated. Cannot upload.")
            raise ConnectionError("Google Drive not authenticated.")

        module_logger.info(f"Uploading {local_file_path} as '{file_name_on_drive}' to Drive folder ID {self.backup_folder_id}...")
        try:
            # Check for and delete existing file with the same name (for 'latest' overwrite behavior)
            existing_files = self.drive.ListFile(
                {'q': f"'{self.backup_folder_id}' in parents and title='{file_name_on_drive}' and trashed=false"}
            ).GetList()

            for old_file in existing_files:
                module_logger.info(f"Deleting existing file '{old_file['title']}' (ID: {old_file['id']}) in Drive to replace with new version.")
                old_file.Delete() # PyDrive Delete() permanently deletes

            gfile = self.drive.CreateFile({
                'title': file_name_on_drive,
                'parents': [{'id': self.backup_folder_id}]
                # 'mimeType': 'application/zip' # Optional: set MIME type
            })
            gfile.SetContentFile(str(local_file_path))
            gfile.Upload({'convert': False}) # convert=False for zip files
            module_logger.info(f"Successfully uploaded '{file_name_on_drive}' to Google Drive. File ID: {gfile['id']}")
            return gfile['id']
        except Exception as e:
            module_logger.error(f"Failed to upload {local_file_path} as '{file_name_on_drive}' to Google Drive: {e}", exc_info=True)
            raise

    def _rename_drive_file(self, file_id: str, new_title: str):
        """Renames a file on Google Drive."""
        if not self.drive:
            module_logger.error("Google Drive not authenticated. Cannot rename.")
            raise ConnectionError("Google Drive not authenticated.")
        try:
            file_to_rename = self.drive.CreateFile({'id': file_id})
            file_to_rename['title'] = new_title
            file_to_rename.Upload() # Updates metadata including title
            module_logger.info(f"Successfully renamed file ID {file_id} to '{new_title}'.")
        except Exception as e:
            module_logger.error(f"Failed to rename file ID {file_id} to '{new_title}': {e}", exc_info=True)
            raise

    def _get_drive_file_modified_date(self, file_id: str) -> datetime.datetime:
        """Gets the modifiedDate of a file on Google Drive and returns as datetime object."""
        if not self.drive:
            module_logger.error("Google Drive not authenticated. Cannot get modified date.")
            raise ConnectionError("Google Drive not authenticated.")
        try:
            gfile_meta = self.drive.CreateFile({'id': file_id})
            gfile_meta.FetchMetadata(fields='modifiedDate') # Fetch only specific field
            modified_date_str = gfile_meta['modifiedDate'] # e.g., '2023-05-15T12:45:30.123Z'
            # Convert ISO 8601 string to datetime object
            # In Python 3.11+, fromisoformat directly supports 'Z'. For older, replace 'Z'.
            if modified_date_str.endswith('Z'):
                modified_date_str = modified_date_str[:-1] + '+00:00'
            return datetime.datetime.fromisoformat(modified_date_str)
        except Exception as e:
            module_logger.error(f"Failed to get modified date for file ID {file_id}: {e}", exc_info=True)
            raise

    def _prepare_latest_in_drive(self, latest_filename_base: str):
        """
        Finds the current "{base}_latest.zip" in Drive.
        If found, renames it to "{base}_{timestamp}.zip" using its Drive modifiedDate.
        """
        if not self.drive:
            module_logger.error("Google Drive not authenticated. Cannot prepare latest.")
            raise ConnectionError("Google Drive not authenticated.")

        latest_file_title_on_drive = f"{latest_filename_base}_latest.zip"
        module_logger.info(f"Preparing for new 'latest' backup. Checking for existing '{latest_file_title_on_drive}'.")

        try:
            existing_latest_files = self.drive.ListFile(
                {'q': f"'{self.backup_folder_id}' in parents and title='{latest_file_title_on_drive}' and trashed=false"}
            ).GetList()

            for old_latest in existing_latest_files: # Should typically be at most one
                module_logger.info(f"Found existing latest file: {old_latest['title']} (ID: {old_latest['id']}). Renaming it.")
                try:
                    modified_date = self._get_drive_file_modified_date(old_latest['id'])
                    timestamp_str = modified_date.strftime("%Y%m%d_%H%M%S")

                    new_historical_title = f"{latest_filename_base}_{timestamp_str}.zip"

                    # Check if a file with this new_historical_title already exists (collision)
                    # This is rare but possible if backups happen very close to a previous manual naming or error.
                    collision_check = self.drive.ListFile(
                        {'q': f"'{self.backup_folder_id}' in parents and title='{new_historical_title}' and trashed=false"}
                    ).GetList()
                    if collision_check:
                        timestamp_str = modified_date.strftime("%Y%m%d_%H%M%S_%f") # Add microseconds
                        new_historical_title = f"{latest_filename_base}_{timestamp_str}.zip"
                        module_logger.warning(f"Timestamp collision for historical rename. Using microseconds: {new_historical_title}")

                    self._rename_drive_file(old_latest['id'], new_historical_title)
                    module_logger.info(f"Renamed previous latest file (ID: {old_latest['id']}) to '{new_historical_title}'.")
                except Exception as e:
                    module_logger.error(f"Could not rename previous latest file {old_latest['title']} (ID: {old_latest['id']}): {e}", exc_info=True)
                    raise # Re-raise to halt the backup process to avoid data loss or inconsistent state

            if not existing_latest_files:
                module_logger.info(f"No existing '{latest_file_title_on_drive}' found. Safe to upload new one.")
        except Exception as e:
            module_logger.error(f"Error while preparing for new latest backup (listing existing latest): {e}", exc_info=True)
            raise

    def _enforce_retention_policy(self, latest_filename_base: str, max_historical_copies: int = 5):
        """
        Ensures no more than `max_historical_copies` are kept, deleting the oldest.
        This considers files matching "{base}_{timestamp}.zip".
        """
        if not self.drive:
            module_logger.error("Google Drive not authenticated. Cannot enforce retention.")
            raise ConnectionError("Google Drive not authenticated.")

        module_logger.info(f"Enforcing retention policy for base '{latest_filename_base}' (max {max_historical_copies} historical copies).")
        try:
            # List all files that look like historical backups (not the 'latest' one)
            query = f"'{self.backup_folder_id}' in parents and title contains '{latest_filename_base}_' and not title contains '_latest.zip' and trashed=false"
            file_list = self.drive.ListFile({'q': query}).GetList()

            historical_backups: List[Tuple[datetime.datetime, GoogleDriveFile]] = []

            for file_item in file_list:
                title = file_item['title']
                # Example title: backup_data_logs_20230101_120000.zip or backup_data_logs_20230101_120000_123456.zip
                if title.startswith(f"{latest_filename_base}_") and title.endswith(".zip"):
                    try:
                        # Extract timestamp part: YYYYMMDD_HHMMSS or YYYYMMDD_HHMMSS_ffffff
                        ts_part_match = title[len(latest_filename_base)+1 : -4] # Remove prefix and .zip

                        # Try parsing with microseconds, then without
                        try:
                            ts_obj = datetime.datetime.strptime(ts_part_match, "%Y%m%d_%H%M%S_%f")
                        except ValueError:
                            ts_obj = datetime.datetime.strptime(ts_part_match, "%Y%m%d_%H%M%S")

                        historical_backups.append((ts_obj, file_item))
                    except ValueError:
                        module_logger.warning(f"Could not parse timestamp from historical backup filename: {title}. Skipping this file for retention.")

            historical_backups.sort(key=lambda x: x[0], reverse=True) # Sort newest first (most recent timestamp)

            if len(historical_backups) > max_historical_copies:
                files_to_delete_count = len(historical_backups) - max_historical_copies
                module_logger.info(f"Found {len(historical_backups)} historical backups. Deleting {files_to_delete_count} oldest ones.")
                files_to_delete = historical_backups[max_historical_copies:] # The tail end of the sorted list

                for ts_obj, file_to_delete in files_to_delete:
                    module_logger.info(f"Deleting old backup: {file_to_delete['title']} (ID: {file_to_delete['id']}, Timestamp: {ts_obj.isoformat()})")
                    try:
                        file_to_delete.Delete() # PyDrive Delete() permanently deletes
                    except Exception as e_del:
                        module_logger.error(f"Failed to delete old backup {file_to_delete['title']} (ID: {file_to_delete['id']}): {e_del}", exc_info=True)
            else:
                module_logger.info(f"Found {len(historical_backups)} historical backups. No deletion needed (max {max_historical_copies}).")

        except Exception as e:
            module_logger.error(f"Error during backup retention policy enforcement: {e}", exc_info=True)
            # Don't re-raise here usually, as the primary backup might have succeeded.
            # However, failing retention is also a problem. Decide based on severity.

    def run_backup_process(self, folders_to_backup: List[str]):
        """Main method to orchestrate the backup process."""
        if not self.drive: # Check if authentication failed in constructor
            module_logger.error("BackupManager not properly initialized (Google Drive auth failed). Aborting backup.")
            return False # Indicate failure

        latest_filename_base = "backup_data_logs" # Consistent base name for this type of backup
        local_temp_archive_base = f"{latest_filename_base}_local_temp" # Temporary local archive name
        latest_zip_name_on_drive = f"{latest_filename_base}_latest.zip"

        compressed_archive_path = None
        success = False
        try:
            # 1. Compress specified folders to a local temporary zip file
            module_logger.info(f"Step 1: Compressing folders: {folders_to_backup}")
            compressed_archive_path = self.compress_folders(
                folders_to_backup,
                archive_name_base=local_temp_archive_base
            )
            module_logger.info(f"Compression complete. Archive: {compressed_archive_path}")

            # 2. Prepare Drive: Find current "{base}_latest.zip" on Drive, rename it to historical with timestamp
            module_logger.info(f"Step 2: Preparing Google Drive for new '{latest_zip_name_on_drive}'.")
            self._prepare_latest_in_drive(latest_filename_base)
            module_logger.info("Google Drive preparation complete.")

            # 3. Upload the new compressed file as "{base}_latest.zip" to Drive
            module_logger.info(f"Step 3: Uploading {compressed_archive_path} to Google Drive as '{latest_zip_name_on_drive}'.")
            self._upload_single_file(compressed_archive_path, latest_zip_name_on_drive)
            module_logger.info("Upload of new latest backup complete.")

            # 4. Enforce retention policy for historical backups (e.g., keep max 5)
            module_logger.info(f"Step 4: Enforcing retention policy for historical backups based on '{latest_filename_base}'.")
            self._enforce_retention_policy(latest_filename_base, max_historical_copies=5)
            module_logger.info("Backup rotation and retention policy enforced.")

            module_logger.info("Backup process completed successfully.")
            success = True

        except FileNotFoundError as e:
            module_logger.error(f"Backup process failed due to a missing file: {e}", exc_info=True)
        except ConnectionError as e: # For auth/network issues with GDrive
            module_logger.error(f"Backup process failed due to a connection or authentication error: {e}", exc_info=True)
        except Exception as e:
            module_logger.error(f"An unexpected error occurred during the backup process: {e}", exc_info=True)
        finally:
            # Clean up the local temporary zip file
            if compressed_archive_path and compressed_archive_path.exists():
                try:
                    module_logger.info(f"Cleaning up local archive: {compressed_archive_path}")
                    os.remove(compressed_archive_path)
                    module_logger.info(f"Successfully cleaned up local archive.")
                except OSError as e_os:
                    module_logger.error(f"Failed to clean up local archive {compressed_archive_path}: {e_os}", exc_info=True)
        return success


# Example usage for direct testing (requires user setup for client_secrets.json and folder ID)
if __name__ == '__main__':
    # Configure logging for direct script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    module_logger.info("Running backup_utils.py directly for testing.")

    # --- USER SETUP REQUIRED FOR THIS TEST BLOCK ---
    # 1. Place `client_secrets.json` from Google Cloud Console in the project root.
    #    It should be for an "OAuth 2.0 Client ID" of type "Desktop app".
    # 2. Specify the Google Drive Folder ID below where backups should go.
    # 3. Run this script once interactively to authorize PyDrive2. It will create `pydrive_credentials.json`.
    #    Future runs (e.g., by ETL) can then be non-interactive if `pydrive_credentials.json` is valid.

    TEST_GDRIVE_BACKUP_FOLDER_ID = "YOUR_ACTUAL_GDRIVE_FOLDER_ID_HERE" # <--- REPLACE THIS
    # --- END USER SETUP ---

    # Mock settings for direct testing
    # Assuming this script is in src/utils/backup_utils.py
    # Project root is then three levels up from this file's directory.
    current_file_path = Path(__file__).resolve()
    project_root_path = current_file_path.parent.parent.parent

    class MockTestGoogleDriveConfig:
        credentials_file: str = str(project_root_path / "client_secrets.json")
        backup_folder_id: str = TEST_GDRIVE_BACKUP_FOLDER_ID

    class MockTestSettings:
        project_root: str = str(project_root_path)
        google_drive = MockTestGoogleDriveConfig()
        # These are relative to project_root as per Settings class intention
        data_dir: str = "data"
        logs_dir: str = "logs"

    mock_settings_instance = MockTestSettings()

    # Create dummy data/ and logs/ folders with some files in the project root for testing
    test_data_dir = project_root_path / mock_settings_instance.data_dir
    test_logs_dir = project_root_path / mock_settings_instance.logs_dir

    try:
        test_data_dir.mkdir(parents=True, exist_ok=True)
        (test_data_dir / "sample_data1.txt").write_text("This is some sample data for backup testing.")
        (test_data_dir / "sample_data2.txt").write_text("Another piece of data here.")
        test_logs_dir.mkdir(parents=True, exist_ok=True)
        (test_logs_dir / "sample_log1.txt").write_text("Log entry: ETL process started.")
        (test_logs_dir / "sample_log2.txt").write_text("Log entry: ETL process finished.")
        module_logger.info(f"Created dummy data in {test_data_dir} and {test_logs_dir} for testing.")
    except Exception as e:
        module_logger.error(f"Could not create dummy data/logs for testing: {e}")


    if not mock_settings_instance.google_drive.backup_folder_id or \
       mock_settings_instance.google_drive.backup_folder_id == "YOUR_ACTUAL_GDRIVE_FOLDER_ID_HERE":
        module_logger.warning("Skipping direct execution: `TEST_GDRIVE_BACKUP_FOLDER_ID` is not set for testing in `backup_utils.py`.")
        module_logger.warning("Please set a valid Google Drive Folder ID to test `BackupManager` directly.")
    else:
        try:
            module_logger.info(f"Attempting backup test with BackupManager...")
            module_logger.info(f"Using project root: {mock_settings_instance.project_root}")
            module_logger.info(f"Using data_dir (relative): {mock_settings_instance.data_dir}")
            module_logger.info(f"Using logs_dir (relative): {mock_settings_instance.logs_dir}")
            module_logger.info(f"Credentials file: {mock_settings_instance.google_drive.credentials_file}")
            module_logger.info(f"Backup Folder ID: {mock_settings_instance.google_drive.backup_folder_id}")

            manager = BackupManager(mock_settings_instance)

            # Folders to backup are specified relative to project_root for consistency with settings
            folders_to_backup_list = [
                mock_settings_instance.data_dir, # e.g., "data"
                mock_settings_instance.logs_dir  # e.g., "logs"
            ]

            module_logger.info(f"Calling manager.run_backup_process with folders: {folders_to_backup_list}")
            backup_succeeded = manager.run_backup_process(folders_to_backup_list)
            if backup_succeeded:
                module_logger.info("Direct test run of BackupManager completed successfully.")
            else:
                module_logger.error("Direct test run of BackupManager failed.")

        except Exception as e:
            module_logger.error(f"Error during direct test run of BackupManager: {e}", exc_info=True)
