# Google Drive Backup Configuration

This document outlines the steps to configure the automated backup system that archives the `/data` and `/logs` folders to a specified Google Drive folder after all ETL processes are completed.

## Overview

The backup mechanism performs the following actions:
- Compresses the `data/` and `logs/` directories into a single `.zip` file.
- Uploads this archive to your Google Drive.
- Maintains a `backup_data_logs_latest.zip` file for the most recent backup.
- Keeps up to 5 historical, timestamped backups (e.g., `backup_data_logs_YYYYMMDD_HHMMSS.zip`).
- Automatically deletes the oldest historical backup when a new one is created beyond the 5-copy limit.

## Setup Steps

Follow these steps carefully to enable Google Drive backups:

### 1. Google Cloud Project & API Setup

1.  **Create/Select a Google Cloud Project:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   If you don't have an existing project, create a new one.

2.  **Enable the Google Drive API:**
    *   In the Google Cloud Console, navigate to "APIs & Services" > "Library".
    *   Search for "Google Drive API" and select it.
    *   Click the "Enable" button. If it's already enabled, you're all set for this part.

### 2. Create OAuth 2.0 Credentials

The backup script needs OAuth 2.0 credentials to access your Google Drive.

1.  **Go to Credentials Page:**
    *   In the Google Cloud Console, navigate to "APIs & Services" > "Credentials".

2.  **Create Credentials:**
    *   Click on "+ CREATE CREDENTIALS" and select "OAuth client ID".

3.  **Configure OAuth Consent Screen (if not already done):**
    *   You might be prompted to configure the consent screen first.
    *   Choose "External" or "Internal" based on your organization. For personal use, "External" is common.
    *   Fill in the required fields (App name, User support email, Developer contact information). For a simple internal tool, the names can be straightforward (e.g., "Watchtower Backup").
    *   Scopes: You generally don't need to add scopes here; the application will request them.
    *   Test users: Add your Google account email as a test user, especially if the app is in "testing" mode.
    *   Save and continue.

4.  **Create OAuth Client ID:**
    *   Back on the "Create OAuth client ID" page:
        *   Select "Desktop app" as the Application type.
        *   Give it a name (e.g., "WatchtowerBackupClient").
        *   Click "CREATE".

5.  **Download `client_secrets.json`:**
    *   A dialog will appear showing your Client ID and Client secret. Click "DOWNLOAD JSON".
    *   Rename the downloaded file to `client_secrets.json`.
    *   **Security:** This file grants access to your Google Drive. Treat it like a password.
        *   Place it in a secure location. For this project, you can place it in the project's root directory.
        *   Ensure it's listed in your `.gitignore` file if you don't want to commit it to your repository (though for this project, its path is configured via environment variables).

### 3. Prepare Google Drive Folder

1.  **Create a Folder in Google Drive:**
    *   Go to your [Google Drive](https://drive.google.com/).
    *   Create a new folder where you want the backups to be stored (e.g., "WatchtowerAppBackups").

2.  **Get the Folder ID:**
    *   Open the newly created folder in Google Drive.
    *   The URL in your browser will look something like: `https://drive.google.com/drive/folders/YOUR_FOLDER_ID_HERE`
    *   Copy the `YOUR_FOLDER_ID_HERE` part. This is your Backup Folder ID.

### 4. Configure Environment Variables

The application uses environment variables to find the credentials file and the target Drive folder. Add the following to your `.env` file in the project root (or set them as system environment variables):

```env
# Google Drive Backup Configuration
WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE="client_secrets.json"  # Or the path to your client_secrets.json if not in root
WATCHTOWER_GOOGLE_DRIVE__BACKUP_FOLDER_ID="YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE" # Replace with the ID from Step 3.2
```

*   Make sure `client_secrets.json` is placed at the path specified by `WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE`. If it's in the project root, just `"client_secrets.json"` is fine.

### 5. First-Time Authorization

The very first time the backup script runs (either via `run_all_etl.sh` or by manually running `python run_backup.py`), it needs your permission to access Google Drive.

1.  **Run the script.**
2.  The script will attempt to open a web browser on the machine it's running on. If it's a headless server, it will print a URL to the console.
3.  **Copy the URL** from the console and paste it into a browser on any machine.
4.  **Log in** with the Google account that has access to the Google Drive folder you created in Step 3.
5.  **Grant permissions** to the application (the name you set up in the OAuth consent screen).
6.  After authorization, the browser might show a success message or redirect to a localhost URL. The script should then proceed.
7.  The script will save authentication tokens (including a refresh token) in a new file named `pydrive_credentials.json` (by default, this file is created in the same directory as your `client_secrets.json`). This allows future runs to be non-interactive.
    *   **Security for `pydrive_credentials.json`:** This file also contains sensitive tokens and should be protected.

## Running the Backup

*   **Automated:** The backup process is configured to run automatically after all ETL jobs complete when you execute `./run_all_etl.sh` (or `run_all_etl.bat`). Logs for the backup process itself can be found in `logs/backup_process.log`.
*   **Manual:** You can trigger the backup process manually by running `python run_backup.py` from the project root directory.

## Troubleshooting
*   **`FileNotFoundError: [Errno 2] No such file or directory: 'client_secrets.json'`**: Ensure `WATCHTOWER_GOOGLE_DRIVE__CREDENTIALS_FILE` in your `.env` file correctly points to your `client_secrets.json` file and the file exists at that location.
*   **`TokenRefreshError` or Authentication Issues After First Run**:
    *   The `pydrive_credentials.json` might be corrupted or outdated. Try deleting it and re-running the script to go through the interactive authorization again.
    *   Ensure the Google Drive API is still enabled and the OAuth consent screen configuration hasn't been drastically changed.
    *   If your app was in "testing" mode on the consent screen and your user was not added to "test users", or if the refresh token expired (e.g. user removed access), you might need to re-auth.
*   **Backup files not appearing in Drive**:
    *   Check `logs/backup_process.log` for any error messages from the backup script.
    *   Verify the `WATCHTOWER_GOOGLE_DRIVE__BACKUP_FOLDER_ID` is correct.
    *   Ensure the Google account used for authorization has write permissions to that folder.
