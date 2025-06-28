#!/usr/bin/env python3
"""Backup script for Watchtower data using UV-compatible imports."""

import os
import sys
import subprocess
from pathlib import Path
import logging
from datetime import datetime

# Attempt to set up project path for imports if needed.
# This depends on how the project is structured and run.
# If 'src' is not automatically in sys.path when run from root, this might be needed.
# import os
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.dirname(SCRIPT_DIR)) # Add project root to path

try:
    from src.config.settings import get_settings, Settings
    from src.utils.backup_utils import BackupManager
    from src.utils.logging import setup_logging # Assuming a central logging setup
except ImportError as e:
    # Fallback basic logging if custom setup fails or modules not found
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.error(f"Failed to import necessary modules: {e}. Ensure the project is properly set up with 'uv sync' or 'python install_dev.py'")
    sys.exit(1)

def setup_logging():
    """Set up logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "backup_process.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def check_uv_available():
    """Check if UV is available for running the backup utilities."""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_backup_with_uv():
    """Run backup using UV to ensure proper environment."""
    logger = setup_logging()
    logger.info("Starting Watchtower backup process with UV")
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if UV is available
    if not check_uv_available():
        logger.error("UV not available. Running backup without UV environment management.")
        # Fallback to direct import
        try:
            from src.utils.backup_utils import run_backup_process
            run_backup_process()
        except ImportError as e:
            logger.error(f"Failed to import backup utilities: {e}")
            return False
        return True
    
    # Run backup using UV
    try:
        logger.info("Running backup process with UV environment...")
        cmd = [
            "uv", "run", "python", "-c",
            "from src.utils.backup_utils import run_backup_process; run_backup_process()"
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if result.stdout:
            logger.info(f"Backup output: {result.stdout}")
        
        logger.info("Backup process completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup process failed: {e}")
        if e.stderr:
            logger.error(f"Error details: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during backup: {e}")
        return False

def run_backup_direct():
    """Run backup directly without UV (fallback method)."""
    logger = setup_logging()
    logger.info("Starting Watchtower backup process (direct mode)")
    
    try:
        # Try to import and run backup utilities directly
        from src.utils.backup_utils import run_backup_process
        run_backup_process()
        logger.info("Backup process completed successfully")
        return True
    except ImportError as e:
        logger.error(f"Failed to import backup utilities: {e}")
        logger.error("Please ensure the project is properly set up with 'uv sync' or 'python install_dev.py'")
        return False
    except Exception as e:
        logger.error(f"Backup process failed: {e}")
        return False

def main():
    """Main backup function."""
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("Watchtower Backup Process Starting")
    logger.info("=" * 50)

    # Try UV-based backup first, fallback to direct if needed
    success = run_backup_with_uv()
    
    if not success:
        logger.warning("UV-based backup failed, trying direct method...")
        success = run_backup_direct()

    if success:
        logger.info("✅ Backup completed successfully!")
    else:
        logger.error("❌ Backup failed. Check logs for details.")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("Backup Process Finished")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
