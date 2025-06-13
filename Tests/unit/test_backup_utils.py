import datetime
import logging
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Make sure 'src' is in the Python path for imports
# This might be handled by a pytest configuration (e.g., conftest.py) or environment setup
# For simplicity in this subtask, we assume direct import will work or path is already set.
# import sys
# sys.path.insert(0, str(Path(__file__).resolve().parents[2])) # Add project root to path

from src.utils.backup_utils import BackupManager
from src.config.models import GoogleDriveConfig
from src.config.settings import Settings # Assuming Settings can be imported

# Disable verbose logging from the module under test during unit tests
logging.getLogger('watchtower.src.utils.backup_utils').setLevel(logging.CRITICAL)

class TestBackupManager(unittest.TestCase):

    def setUp(self):
        """Set up for each test method."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.project_root = self.test_dir
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create some dummy files
        (self.data_dir / "d1.txt").write_text("data1")
        (self.data_dir / "d2.txt").write_text("data2")
        (self.logs_dir / "l1.log").write_text("log1")

        # Mock settings
        self.mock_gdrive_config = GoogleDriveConfig(
            credentials_file=str(self.project_root / "fake_client_secrets.json"),
            backup_folder_id="test_gdrive_folder_id"
        )
        # Create the fake client_secrets.json
        (self.project_root / "fake_client_secrets.json").write_text("{}")

        self.mock_settings = MagicMock(spec=Settings)
        self.mock_settings.project_root = str(self.project_root)
        self.mock_settings.google_drive = self.mock_gdrive_config
        self.mock_settings.data_dir = "data" # Relative path as BackupManager might expect
        self.mock_settings.logs_dir = "logs" # Relative path

        # Patch PyDrive2 classes and GoogleAuth methods
        self.mock_google_auth = MagicMock()
        self.mock_google_drive_instance = MagicMock()

        # Mock GoogleAuth instance methods
        self.mock_google_auth.LoadCredentialsFile = MagicMock()
        self.mock_google_auth.LocalWebserverAuth = MagicMock()
        self.mock_google_auth.Refresh = MagicMock()
        self.mock_google_auth.SaveCredentialsFile = MagicMock()
        self.mock_google_auth.access_token_expired = False
        self.mock_google_auth.credentials = MagicMock() # Simulate existing credentials

        # Patch the GoogleAuth constructor to return our mock
        self.patch_google_auth_constructor = patch('src.utils.backup_utils.GoogleAuth', return_value=self.mock_google_auth)
        # Patch the GoogleDrive constructor to return our mock instance
        self.patch_google_drive_constructor = patch('src.utils.backup_utils.GoogleDrive', return_value=self.mock_google_drive_instance)

        self.mock_gauth_constructor_started = self.patch_google_auth_constructor.start()
        self.mock_gdrive_constructor_started = self.patch_google_drive_constructor.start()

        # Mock PyDrive2 GoogleDriveFile, for when drive.ListFile().GetList() or drive.CreateFile() is called
        self.mock_gdrive_file = MagicMock()
        self.mock_gdrive_file.Upload = MagicMock()
        self.mock_gdrive_file.Delete = MagicMock()
        self.mock_gdrive_file.__getitem__.side_effect = lambda key: getattr(self.mock_gdrive_file, key, None)


    def tearDown(self):
        """Clean up after each test method."""
        shutil.rmtree(self.test_dir)
        self.patch_google_auth_constructor.stop()
        self.patch_google_drive_constructor.stop()

    def test_init_success_with_credentials(self):
        """Test successful initialization with existing credentials."""
        self.mock_google_auth.credentials = MagicMock() # Simulate valid credentials
        self.mock_google_auth.access_token_expired = False

        manager = BackupManager(self.mock_settings)

        self.mock_gauth_constructor_started.assert_called_once()
        self.mock_google_auth.LoadCredentialsFile.assert_called_once()
        self.mock_google_auth.LocalWebserverAuth.assert_not_called() # Should not be called if creds load
        self.mock_google_auth.Refresh.assert_not_called()
        self.mock_gdrive_constructor_started.assert_called_once_with(self.mock_google_auth)
        self.assertEqual(manager.drive, self.mock_google_drive_instance)

    def test_init_auth_new_credentials(self):
        """Test initialization triggering new LocalWebserverAuth."""
        self.mock_google_auth.credentials = None # Simulate no saved credentials

        manager = BackupManager(self.mock_settings)

        self.mock_google_auth.LoadCredentialsFile.assert_called_once()
        self.mock_google_auth.LocalWebserverAuth.assert_called_once() # Should be called
        self.mock_google_auth.Refresh.assert_not_called()

    def test_init_auth_refresh_token(self):
        """Test initialization triggering token refresh."""
        self.mock_google_auth.credentials = MagicMock()
        self.mock_google_auth.access_token_expired = True # Simulate expired token

        manager = BackupManager(self.mock_settings)

        self.mock_google_auth.LoadCredentialsFile.assert_called_once()
        self.mock_google_auth.LocalWebserverAuth.assert_not_called()
        self.mock_google_auth.Refresh.assert_called_once() # Should be called

    def test_init_missing_credentials_file(self):
        """Test initialization failure if client_secrets.json is missing."""
        Path(self.mock_settings.google_drive.credentials_file).unlink() # Remove the fake file
        with self.assertRaisesRegex(FileNotFoundError, "client_secrets file not found"):
            BackupManager(self.mock_settings)

    def test_compress_folders_success(self):
        """Test successful compression of folders."""
        manager = BackupManager(self.mock_settings) # Init to setup drive mocks, not strictly needed for this test part
        archive_base_name = "test_backup"

        # Folders are relative to project_root in settings
        folders_to_backup = [self.mock_settings.data_dir, self.mock_settings.logs_dir]

        compressed_path = manager.compress_folders(folders_to_backup, archive_base_name)

        self.assertTrue(compressed_path.exists())
        self.assertEqual(compressed_path.name, f"{archive_base_name}.zip")

        # Verify content of the zip file
        with zipfile.ZipFile(compressed_path, 'r') as zf:
            zip_contents = zf.namelist()
            # Paths in zip should be relative to project_root
            self.assertIn("data/d1.txt", zip_contents)
            self.assertIn("data/d2.txt", zip_contents)
            self.assertIn("logs/l1.log", zip_contents)

        # Clean up the created zip file
        if compressed_path.exists():
            compressed_path.unlink()

    def test_compress_folders_empty_or_missing(self):
        """Test compression with one folder missing and one empty."""
        manager = BackupManager(self.mock_settings)
        empty_dir = self.project_root / "empty_data"
        empty_dir.mkdir()

        folders_to_backup = ["non_existent_folder", "empty_data"]
        archive_base_name = "test_empty_backup"

        with self.assertLogs(f'watchtower.src.utils.backup_utils', level='WARNING') as log_watcher:
            compressed_path = manager.compress_folders(folders_to_backup, archive_base_name)

        self.assertTrue(any("Folder" in msg and "non_existent_folder does not exist" in msg for msg in log_watcher.output))

        self.assertTrue(compressed_path.exists())
        with zipfile.ZipFile(compressed_path, 'r') as zf:
            # empty_data/ should not be explicitly in namelist unless it had files,
            # but the zip file itself should be created.
            self.assertEqual(len(zf.namelist()), 0) # Or check if it contains the empty_data directory entry

        if compressed_path.exists():
            compressed_path.unlink()


    def test_upload_single_file(self):
        """Test uploading a single file, ensuring existing is deleted."""
        manager = BackupManager(self.mock_settings)
        manager.drive = self.mock_google_drive_instance # Ensure it's using the mock

        local_file = self.project_root / "upload_me.txt"
        local_file.write_text("upload content")
        drive_filename = "uploaded_latest.zip"

        # Mock ListFile().GetList()
        # First call (checking existing): return one file to be deleted
        mock_existing_gdrive_file = MagicMock(spec=self.mock_gdrive_file)
        mock_existing_gdrive_file.Delete = MagicMock()
        mock_existing_gdrive_file.get.side_effect = lambda k: {'id': 'old_id', 'title': drive_filename}[k]
        mock_existing_gdrive_file.id = 'old_id'
        mock_existing_gdrive_file.title = drive_filename


        # Mock CreateFile()
        mock_new_gdrive_file = MagicMock(spec=self.mock_gdrive_file)
        mock_new_gdrive_file.Upload = MagicMock()
        mock_new_gdrive_file.get.side_effect = lambda k: {'id': 'new_id', 'title': drive_filename}[k]
        mock_new_gdrive_file.id = 'new_id'

        self.mock_google_drive_instance.ListFile.return_value.GetList.return_value = [mock_existing_gdrive_file]
        self.mock_google_drive_instance.CreateFile.return_value = mock_new_gdrive_file

        uploaded_file_id = manager._upload_single_file(local_file, drive_filename)

        self.mock_google_drive_instance.ListFile.assert_called_once_with(
            {'q': f"'{self.mock_settings.google_drive.backup_folder_id}' in parents and title='{drive_filename}' and trashed=false"}
        )
        mock_existing_gdrive_file.Delete.assert_called_once()

        self.mock_google_drive_instance.CreateFile.assert_called_once_with({
            'title': drive_filename,
            'parents': [{'id': self.mock_settings.google_drive.backup_folder_id}]
        })
        mock_new_gdrive_file.SetContentFile.assert_called_once_with(str(local_file))
        mock_new_gdrive_file.Upload.assert_called_once_with({'convert': False})
        self.assertEqual(uploaded_file_id, "new_id")


    @patch('src.utils.backup_utils.datetime') # Mock datetime for predictable timestamps
    def test_prepare_latest_in_drive_renames_existing(self, mock_datetime):
        """Test that an existing _latest.zip is renamed to a timestamped version."""
        manager = BackupManager(self.mock_settings)
        manager.drive = self.mock_google_drive_instance

        latest_filename_base = "backup_data_logs"
        latest_title_on_drive = f"{latest_filename_base}_latest.zip"

        mock_old_latest_file = MagicMock(spec=self.mock_gdrive_file)
        mock_old_latest_file.id = "id_old_latest"
        mock_old_latest_file.title = latest_title_on_drive
        # mock_old_latest_file['modifiedDate'] = '2023-01-01T10:00:00.000Z' # PyDrive uses dict access
        mock_old_latest_file.get.side_effect = lambda k: {'id': 'id_old_latest', 'title': latest_title_on_drive, 'modifiedDate': '2023-01-01T10:00:00.000Z'}[k]


        self.mock_google_drive_instance.ListFile.return_value.GetList.side_effect = [
            [mock_old_latest_file], # First call for finding existing latest
            []                      # Second call for collision check (no collision)
        ]

        # Mock datetime.datetime.fromisoformat and strftime
        fixed_datetime = datetime.datetime(2023, 1, 1, 10, 0, 0)
        mock_datetime.datetime.fromisoformat.return_value = fixed_datetime
        mock_datetime.datetime.strptime.return_value = fixed_datetime # For strptime fallback
        fixed_timestamp_str = "20230101_100000"
        # Side effect for strftime: first for fromisoformat, then for strptime if needed
        # We directly control fromisoformat return, so strftime on that
        type(fixed_datetime).strftime = MagicMock(return_value=fixed_timestamp_str)


        # Mock the CreateFile used by _rename_drive_file and _get_drive_file_modified_date
        # Need to handle multiple calls to CreateFile
        def create_file_side_effect(options):
            file_mock = MagicMock(spec=self.mock_gdrive_file) # Create a new mock for each call
            file_id_option = options.get('id')

            if file_id_option == 'id_old_latest':
                file_mock.id = 'id_old_latest'
                if 'fields' in options and options['fields'] == 'modifiedDate': # Call from _get_drive_file_modified_date
                    file_mock.FetchMetadata = MagicMock()
                    # __getitem__ is used by PyDrive2 to access metadata like file_mock['modifiedDate']
                    file_mock.__getitem__.side_effect = lambda k: '2023-01-01T10:00:00.000Z' if k == 'modifiedDate' else None
                else: # Call from _rename_drive_file
                    file_mock.title = latest_title_on_drive # Original title before it's changed by SUT
                    file_mock.Upload = MagicMock() # This is the rename action
                return file_mock
            return file_mock # Default mock for other calls (e.g. if CreateFile is called for new uploads)

        self.mock_google_drive_instance.CreateFile.side_effect = create_file_side_effect

        manager._prepare_latest_in_drive(latest_filename_base)

        # Check ListFile calls
        self.assertEqual(self.mock_google_drive_instance.ListFile.call_count, 2)
        self.mock_google_drive_instance.ListFile.assert_any_call(
            {'q': f"'{self.mock_settings.google_drive.backup_folder_id}' in parents and title='{latest_title_on_drive}' and trashed=false"}
        )

        # Check that the old latest file was "renamed"
        # The mock_gdrive_file.Upload is on the object returned by CreateFile for rename
        # We need to verify the 'Upload' on the mock that was configured for renaming.

        # Find the mock that was used for renaming. Its 'Upload' method should have been called.
        # And its 'title' attribute should have been updated.
        found_rename_mock = None
        for call_args in self.mock_google_drive_instance.CreateFile.call_args_list:
            created_mock = self.mock_google_drive_instance.CreateFile.side_effect(call_args[0][0]) # re-evaluate side_effect to get the mock
            if created_mock.id == 'id_old_latest' and hasattr(created_mock, 'Upload') and created_mock.Upload.called:
                 found_rename_mock = created_mock
                 break

        self.assertIsNotNone(found_rename_mock, "Rename operation mock not found or Upload not called.")
        self.assertEqual(found_rename_mock.title, f"{latest_filename_base}_{fixed_timestamp_str}.zip")
        found_rename_mock.Upload.assert_called_once()


    def test_enforce_retention_policy_deletes_oldest(self):
        """Test retention policy correctly identifies and deletes oldest backups."""
        manager = BackupManager(self.mock_settings)
        manager.drive = self.mock_google_drive_instance
        latest_filename_base = "backup_data_logs"
        max_historical = 2 # Keep 2 historical, so 3rd oldest should be deleted

        # Create mock historical files with different timestamps in their titles
        # Timestamps are YYYYMMDD_HHMMSS
        files_data = [
            ("id1", f"{latest_filename_base}_20230101_100000.zip", datetime.datetime(2023,1,1,10,0,0)), # Oldest
            ("id2", f"{latest_filename_base}_20230102_100000.zip", datetime.datetime(2023,1,2,10,0,0)),
            ("id3", f"{latest_filename_base}_20230103_100000.zip", datetime.datetime(2023,1,3,10,0,0)), # Newest of these three
        ]

        mock_drive_files = []
        for id_val, title_val, _ in files_data:
            mf = MagicMock(spec=self.mock_gdrive_file)
            mf.id = id_val
            mf.title = title_val
            # mf['title'] = title_val # PyDrive uses dict access for title
            # mf['id'] = id_val
            mf.get.side_effect = lambda k, i=id_val, t=title_val: {'id': i, 'title': t}[k] # Allows mf['id'] or mf['title']
            mf.__getitem__.side_effect = lambda k, i=id_val, t=title_val: {'id': i, 'title': t}[k] # For file_item['title']
            mf.Delete = MagicMock()
            mock_drive_files.append(mf)

        self.mock_google_drive_instance.ListFile.return_value.GetList.return_value = mock_drive_files

        manager._enforce_retention_policy(latest_filename_base, max_historical_copies=max_historical)

        # Check which files were deleted
        # Files are sorted by date derived from title, newest first.
        # mock_drive_files[0] (id1, 20230101) is oldest, should be deleted.
        # mock_drive_files[1] (id2, 20230102) should be kept.
        # mock_drive_files[2] (id3, 20230103) should be kept.

        mock_drive_files[0].Delete.assert_called_once()  # Oldest (id1)
        mock_drive_files[1].Delete.assert_not_called() # Kept
        mock_drive_files[2].Delete.assert_not_called() # Kept


    @patch('src.utils.backup_utils.os.remove')
    def test_run_backup_process_full_flow_success(self, mock_os_remove):
        """Test the full backup process orchestration on success."""
        manager = BackupManager(self.mock_settings)
        manager.drive = self.mock_google_drive_instance # Ensure using mock

        # Mock manager's own methods that are complex or have external calls
        manager.compress_folders = MagicMock(return_value=self.project_root / "temp_archive.zip")
        manager._prepare_latest_in_drive = MagicMock()
        manager._upload_single_file = MagicMock(return_value="new_gdrive_file_id")
        manager._enforce_retention_policy = MagicMock()

        # Create the dummy temp_archive.zip so os.remove doesn't fail if called
        (self.project_root / "temp_archive.zip").write_text("dummy zip content")

        folders_to_backup = [self.mock_settings.data_dir, self.mock_settings.logs_dir]
        result = manager.run_backup_process(folders_to_backup)

        self.assertTrue(result)
        manager.compress_folders.assert_called_once_with(folders_to_backup, "backup_data_logs_local_temp")
        manager._prepare_latest_in_drive.assert_called_once_with("backup_data_logs")
        manager._upload_single_file.assert_called_once_with(
            self.project_root / "temp_archive.zip",
            "backup_data_logs_latest.zip"
        )
        manager._enforce_retention_policy.assert_called_once_with("backup_data_logs", max_historical_copies=5)
        mock_os_remove.assert_called_once_with(self.project_root / "temp_archive.zip")


    @patch('src.utils.backup_utils.os.remove')
    def test_run_backup_process_compression_fails(self, mock_os_remove):
        """Test full flow when compression fails."""
        manager = BackupManager(self.mock_settings)
        manager.drive = self.mock_google_drive_instance

        manager.compress_folders = MagicMock(side_effect=zipfile.BadZipFile("Compression failed"))
        manager._prepare_latest_in_drive = MagicMock() # Won't be called
        manager._upload_single_file = MagicMock()    # Won't be called
        manager._enforce_retention_policy = MagicMock() # Won't be called

        folders_to_backup = [self.mock_settings.data_dir]
        result = manager.run_backup_process(folders_to_backup)

        self.assertFalse(result)
        manager.compress_folders.assert_called_once()
        manager._prepare_latest_in_drive.assert_not_called()
        manager._upload_single_file.assert_not_called()
        manager._enforce_retention_policy.assert_not_called()
        # If compress_folders creates a partial archive and then fails,
        # its internal error handling should try to remove it.
        # So, mock_os_remove might be called by compress_folders' own cleanup.
        # For this test, we assume compress_folders either doesn't create the file
        # or cleans it up itself if it partially creates it before raising error.
        # Thus, the finally block in run_backup_process might not find a file to remove.
        # If compress_folders guarantees no file exists after it errors, then this is fine:
        # mock_os_remove.assert_not_called()
        # However, if run_backup_process's finally block *always* tries to remove based on
        # the path returned (even if None or non-existent), then behavior changes.
        # Given the code, compress_folders raises, so compressed_archive_path remains None or points to a cleaned file.
        # The current code for compress_folders has its own try-except-finally for os.remove.
        # So, the os.remove in run_backup_process's finally block would only be called if compress_folders *succeeded*
        # but a later step failed. If compress_folders itself fails, its own cleanup runs.
        # This depends on whether `compressed_archive_path` is assigned before erroring.
        # In the SUT, `compressed_archive_path` is assigned *after* `compress_folders` returns.
        # If `compress_folders` errors, `compressed_archive_path` in `run_backup_process` is not yet (re)assigned.
        # This test seems okay, the main os.remove in run_backup_process's finally won't be called.

    def test_get_drive_file_modified_date(self):
        """Test parsing of modifiedDate from Google Drive file metadata."""
        manager = BackupManager(self.mock_settings)
        manager.drive = self.mock_google_drive_instance

        mock_file_meta = MagicMock(spec=self.mock_gdrive_file)
        # PyDrive file objects behave like dictionaries for metadata
        mock_file_meta.__getitem__.side_effect = lambda key: '2023-10-27T10:30:45.123Z' if key == 'modifiedDate' else None
        mock_file_meta.FetchMetadata = MagicMock()

        self.mock_google_drive_instance.CreateFile.return_value = mock_file_meta

        file_id = "some_file_id"
        expected_datetime = datetime.datetime(2023, 10, 27, 10, 30, 45, 123000, tzinfo=datetime.timezone.utc)

        # Python 3.10 and older fromisoformat doesn't like 'Z' directly
        # The code in backup_utils replaces 'Z' with '+00:00'
        # For this test, we ensure the string processing in the SUT is correct

        actual_datetime = manager._get_drive_file_modified_date(file_id)

        self.mock_google_drive_instance.CreateFile.assert_called_once_with({'id': file_id})
        mock_file_meta.FetchMetadata.assert_called_once_with(fields='modifiedDate')
        self.assertEqual(actual_datetime.replace(tzinfo=datetime.timezone.utc), expected_datetime)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
