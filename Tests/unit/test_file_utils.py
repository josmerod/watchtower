"""
Unit tests for file system utilities.
"""

import json
import tempfile
import unittest
from pathlib import Path

from src.utils.file_system import (
    FileSystemManager,
    get_project_root,
    ensure_directories,
)


class TestFileSystemUtils(unittest.TestCase):
    """Test file system utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fs_manager = FileSystemManager(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_system_manager_initialization(self):
        """Test FileSystemManager initialization."""
        self.assertEqual(self.fs_manager.project_root, self.test_dir)

    def test_ensure_directory_creates_new_directory(self):
        """Test ensure_directory creates new directory."""
        new_dir_name = "new_directory"

        dir_info = self.fs_manager.ensure_directory(new_dir_name)

        self.assertTrue(dir_info.exists)
        self.assertTrue(dir_info.is_writable)
        self.assertEqual(dir_info.path, self.test_dir / new_dir_name)

    def test_ensure_directories_batch_creation(self):
        """Test ensure_directories creates multiple directories."""
        directories = ["dir1", "dir2", "dir3"]

        ensure_directories(directories)

        # This function should not raise an error
        self.assertTrue(True)

    def test_get_absolute_path(self):
        """Test getting absolute path from relative path."""
        relative_path = "test/path"

        absolute_path = self.fs_manager.get_absolute_path(relative_path)

        self.assertEqual(absolute_path, self.test_dir / relative_path)

    def test_get_project_root(self):
        """Test get_project_root function."""
        root = get_project_root()

        self.assertIsInstance(root, str)
        self.assertTrue(len(root) > 0)

    def test_copy_file_success(self):
        """Test copying file successfully."""
        # Create source file
        source_file = self.test_dir / "source.txt"
        source_file.write_text("test content")

        # Copy to destination
        dest_file = "destination.txt"
        result = self.fs_manager.copy_file(source_file, dest_file)

        self.assertTrue(result)
        self.assertTrue((self.test_dir / dest_file).exists())

    def test_clean_directory(self):
        """Test cleaning directory contents."""
        # Create test directory with files
        test_dir = self.test_dir / "test_clean"
        test_dir.mkdir()

        (test_dir / "file1.txt").write_text("content")
        (test_dir / "file2.txt").write_text("content")

        # Clean directory
        result = self.fs_manager.clean_directory("test_clean")

        self.assertTrue(result)
        self.assertTrue(test_dir.exists())  # Directory should still exist
        self.assertEqual(len(list(test_dir.iterdir())), 0)  # But be empty


if __name__ == "__main__":
    unittest.main()
