"""Enhanced file system utilities for Watchtower."""

import os
import shutil
from pathlib import Path

from pydantic import BaseModel, Field, validator

from src.exceptions.base import WatchtowerError


class PathError(WatchtowerError):
    """Exception raised for path-related errors."""

    pass


class DirectoryInfo(BaseModel):
    """Information about a directory."""

    path: Path = Field(..., description="Directory path")
    exists: bool = Field(description="Whether directory exists")
    is_writable: bool = Field(description="Whether directory is writable")
    size_bytes: int | None = Field(None, description="Directory size in bytes")
    file_count: int | None = Field(None, description="Number of files in directory")

    @validator("path", pre=True)
    def convert_to_path(cls, v):
        """Convert string to Path object."""
        return Path(v)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class FileSystemManager:
    """Enhanced file system manager with validation and error handling."""

    def __init__(self, project_root: str | Path | None = None):
        """Initialize file system manager.

        Args:
            project_root: Project root directory. If None, auto-detects.
        """
        self.project_root = self._find_project_root() if project_root is None else Path(project_root)

    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        current_path = Path(__file__).resolve()

        # Look for project markers
        markers = ["pyproject.toml", "README.md", ".git", "requirements.txt"]

        for parent in current_path.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent

        # Fallback to current working directory
        return Path.cwd()

    def get_absolute_path(self, relative_path: str | Path) -> Path:
        """Get absolute path from relative path.

        Args:
            relative_path: Path relative to project root.

        Returns:
            Absolute path.
        """
        path = Path(relative_path)
        if path.is_absolute():
            return path
        return self.project_root / path

    def ensure_directory(self, directory: str | Path, mode: int = 0o755) -> DirectoryInfo:
        """Ensure directory exists, creating it if necessary.

        Args:
            directory: Directory path (relative to project root).
            mode: Directory permissions (default: 0o755).

        Returns:
            DirectoryInfo object with directory information.

        Raises:
            PathError: If directory cannot be created.
        """
        abs_path = self.get_absolute_path(directory)

        try:
            abs_path.mkdir(parents=True, exist_ok=True, mode=mode)

            # Get directory information
            info = DirectoryInfo(
                path=abs_path,
                exists=abs_path.exists(),
                is_writable=os.access(abs_path, os.W_OK),
            )

            # Calculate size and file count if directory exists
            if info.exists:
                try:
                    info.file_count = len(list(abs_path.iterdir()))
                    info.size_bytes = sum(f.stat().st_size for f in abs_path.rglob("*") if f.is_file())
                except (OSError, PermissionError):
                    # Continue without size/count info if access denied
                    pass

            return info

        except OSError as e:
            raise PathError(
                message=f"Cannot create directory {abs_path}",
                error_code="DIRECTORY_CREATION_FAILED",
                context={"directory": str(abs_path), "error": str(e)},
            ) from e

    def ensure_directories(self, directories: list[str | Path], mode: int = 0o755) -> list[DirectoryInfo]:
        """Ensure multiple directories exist.

        Args:
            directories: List of directory paths.
            mode: Directory permissions.

        Returns:
            List of DirectoryInfo objects.
        """
        return [self.ensure_directory(directory, mode) for directory in directories]

    def clean_directory(self, directory: str | Path, keep_directory: bool = True) -> bool:
        """Clean directory contents.

        Args:
            directory: Directory to clean.
            keep_directory: Whether to keep the directory itself.

        Returns:
            True if successful, False otherwise.

        Raises:
            PathError: If directory cannot be cleaned.
        """
        abs_path = self.get_absolute_path(directory)

        if not abs_path.exists():
            return True

        try:
            if keep_directory:
                for item in abs_path.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            else:
                shutil.rmtree(abs_path)

            return True

        except OSError as e:
            raise PathError(
                message=f"Cannot clean directory {abs_path}",
                error_code="DIRECTORY_CLEAN_FAILED",
                context={"directory": str(abs_path), "error": str(e)},
            ) from e

    def copy_file(self, source: str | Path, destination: str | Path) -> bool:
        """Copy file with error handling.

        Args:
            source: Source file path.
            destination: Destination file path.

        Returns:
            True if successful.

        Raises:
            PathError: If file cannot be copied.
        """
        source_path = self.get_absolute_path(source)
        dest_path = self.get_absolute_path(destination)

        try:
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source_path, dest_path)
            return True

        except OSError as e:
            raise PathError(
                message=f"Cannot copy file {source_path} to {dest_path}",
                error_code="FILE_COPY_FAILED",
                context={
                    "source": str(source_path),
                    "destination": str(dest_path),
                    "error": str(e),
                },
            ) from e

    def get_directory_info(self, directory: str | Path) -> DirectoryInfo:
        """Get information about a directory.

        Args:
            directory: Directory path.

        Returns:
            DirectoryInfo object.
        """
        abs_path = self.get_absolute_path(directory)

        info = DirectoryInfo(
            path=abs_path,
            exists=abs_path.exists(),
            is_writable=os.access(abs_path, os.W_OK) if abs_path.exists() else False,
        )

        # Calculate size and file count if directory exists
        if info.exists:
            try:
                info.file_count = len(list(abs_path.iterdir()))
                info.size_bytes = sum(f.stat().st_size for f in abs_path.rglob("*") if f.is_file())
            except (OSError, PermissionError):
                # Continue without size/count info if access denied
                pass

        return info


# Global instance for backward compatibility
_global_fs_manager = None


def get_file_system_manager() -> FileSystemManager:
    """Get global file system manager instance.

    Returns:
        FileSystemManager instance.
    """
    global _global_fs_manager
    if _global_fs_manager is None:
        _global_fs_manager = FileSystemManager()
    return _global_fs_manager


def get_project_root() -> str:
    """Get the absolute path to the project root directory.

    Returns:
        str: Absolute path to the project root directory.
    """
    return str(get_file_system_manager().project_root)


def ensure_directories(directories: list[str]) -> None:
    """Ensure that the specified directories exist, creating them if necessary.

    All paths are relative to the project root.

    Args:
        directories: A list of directory paths to check and create if they don't exist.

    Example:
        ensure_directories(['data/games', 'logs'])
    """
    get_file_system_manager().ensure_directories(directories)


def ensure_directory(directory: str | Path, mode: int = 0o755) -> DirectoryInfo:
    """Ensure directory exists, creating it if necessary.

    Args:
        directory: Directory path.
        mode: Directory permissions.

    Returns:
        DirectoryInfo object.
    """
    return get_file_system_manager().ensure_directory(directory, mode)


def read_json_file(file_path: str | Path):
    """Read JSON file.

    Args:
        file_path: Path to JSON file.

    Returns:
        Parsed JSON data.
    """
    import json

    path = Path(file_path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json_file(file_path: str | Path, data, indent: int | None = None) -> None:
    """Write data to JSON file.

    Args:
        file_path: Path to JSON file.
        data: Data to write.
        indent: Indentation level.
    """
    import json

    path = Path(file_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def backup_file(file_path: str | Path) -> Path:
    """Create a backup of a file.

    Args:
        file_path: Path to file to backup.

    Returns:
        Path to backup file.
    """
    import datetime

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.stem}_{timestamp}_backup{path.suffix}")
    shutil.copy2(path, backup_path)
    return backup_path


def get_file_size(file_path: str | Path) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to file.

    Returns:
        File size in bytes, or 0 if file doesn't exist.
    """
    path = Path(file_path)
    if not path.exists():
        return 0
    return path.stat().st_size


def clean_filename(filename: str) -> str:
    """Clean filename by removing invalid characters.

    Args:
        filename: Original filename.

    Returns:
        Cleaned filename.
    """
    import re

    # Remove invalid chars: < > : " / \ | ? *
    cleaned = re.sub(r'[<>:"/\\|?*]', "", filename)
    return cleaned


def batch_process_files(files: list[str | Path], process_func):
    """Process a batch of files.

    Args:
        files: List of files to process.
        process_func: Function to apply to each file.

    Returns:
        List of results.
    """
    return [process_func(Path(f)) for f in files]
