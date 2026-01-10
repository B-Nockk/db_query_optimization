# public/common/scripts/get_project_root.py
import inspect
from pathlib import Path


def get_project_root() -> Path:
    """
    Get the project root directory by finding the calling module's package root.

    This function traverses up the directory tree from the calling module until
    it finds a directory that doesn't contain an __init__.py file, which indicates
    the package root.

    Returns:
        Path object pointing to the project root directory.

    Example:
        If called from /project/app/services/logger.py:
        - Checks /project/app/services/ (has __init__.py, continue)
        - Checks /project/app/ (has __init__.py, continue)
        - Checks /project/ (no __init__.py, return this)
    """
    # Get the calling module's file path using inspect (public API)
    frame = inspect.currentframe()
    if frame is None:
        return Path.cwd()

    caller_frame = frame.f_back
    if caller_frame is None:
        return Path.cwd()

    caller_file = caller_frame.f_globals.get("__file__")

    if not caller_file:
        return Path.cwd()

    current_path = Path(caller_file).resolve().parent

    # Traverse up until we find a directory without __init__.py
    # This indicates we've left the package structure
    while current_path != current_path.parent:
        if not (current_path / "__init__.py").exists():
            return current_path
        current_path = current_path.parent

    # If we've reached the filesystem root, return the directory of the caller
    return Path(caller_file).resolve().parent


__all__ = ["get_project_root"]
