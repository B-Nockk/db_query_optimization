# public/common/scripts/write_to_file.py
"""
Logging utilities for writing structured log files with automatic week-based naming.

This module provides functionality to write log entries to files with automatic
directory creation and week-based file naming conventions.
"""

from pathlib import Path
from typing import Any
from .get_date_range import get_week_date_range
from .get_project_root import get_project_root
from common.config import get_env


# Module-level defaults
week_start, week_end, week_number = get_week_date_range()
_DEFAULT_LOG_FILE_NAME = (
    f"wk{week_number:02d}_{week_start.isoformat()}--{week_end.isoformat()}.json"
)
_DEFAULT_LOGS_FOLDER_PATH = get_project_root() / "logs"


def write_to_file(
    payload: str,
    folder_path_env_key: str = "LOG_FOLDER_PATH",
    file_name_env_key: str = "LOG_FILE_NAME",
) -> bool:
    """
    Write content to a file with automatic directory creation.

    This function is primarily designed for logging purposes with week-based file
    naming, but can be used for general file writing. The function will:
    - Create the directory structure if it doesn't exist
    - Append content to the file (creates if doesn't exist)
    - Add a newline after each write operation

    Args:
        payload: The content to write to the file. Must not be empty.
        folder_path_env_key: Environment variable key for the folder path.
            Defaults to "LOG_FOLDER_PATH". If not set in env, uses
            "<project_root>/logs".
        file_name_env_key: Environment variable key for the file name.
            Defaults to "LOG_FILE_NAME". If not set in env, uses
            "<week_start>--<week_end>.json".

    Returns:
        True if the write operation was successful.

    Raises:
        ValueError: If payload is empty or None.
        OSError: If file operations fail (permissions, disk space, etc.).

    Example:
        >>> write_to_file('{"event": "user_login", "timestamp": "2024-01-10"}')
        True

        # With custom environment variables
        >>> os.environ['LOG_FOLDER_PATH'] = '/var/logs/myapp'
        >>> os.environ['LOG_FILE_NAME'] = 'application.log'
        >>> write_to_file('Log entry')
        True
    """
    if not payload:
        raise ValueError("payload must not be empty")

    # Get folder path from environment or use default
    folder_path_str = get_env(folder_path_env_key)
    if folder_path_str:
        log_dir = Path(folder_path_str)
    else:
        log_dir = _DEFAULT_LOGS_FOLDER_PATH

    # Get file name from environment or use default
    file_name = get_env(file_name_env_key) or _DEFAULT_LOG_FILE_NAME

    # Create directory structure if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    file_path = log_dir / file_name

    try:
        with file_path.open(mode="a", encoding="utf-8") as f:
            f.write(payload)
            f.write("\n")
        return True
    except OSError as e:
        # Re-raise with more context
        raise OSError(f"Failed to write to log file {file_path}: {e}") from e


def write_log_entry(entry: dict[str, Any], **kwargs: Any) -> bool:
    """
    Convenience function to write a dictionary as a JSON log entry.

    Args:
        entry: Dictionary to write as JSON.
        **kwargs: Additional arguments to pass to write_to_file.

    Returns:
        True if the write operation was successful.

    Example:
        >>> write_log_entry({"event": "login", "user_id": 123})
        True
    """
    import json

    payload = json.dumps(entry, ensure_ascii=False)
    return write_to_file(payload, **kwargs)


__all__ = [
    "write_log_entry",
    "write_log_entry",
]
