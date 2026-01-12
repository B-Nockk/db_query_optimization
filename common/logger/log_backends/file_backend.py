# public/common/logger/log_backends/file_backend.py
"""File-based log persistence backend using write_to_file."""
from datetime import date
from pathlib import Path
from typing import Any, Dict
from common.scripts import get_week_date_range, get_project_root
from .base import LogBackend


class FileBackend(LogBackend):
    """
    File-based log backend that writes to weekly JSON files.

    Uses the existing write_to_file function from process_log module.
    Automatically organizes logs into weekly files.
    """

    def __init__(self, **config: Any):
        """
        Initialize file backend.

        Args:
            **config: Optional configuration
                - log_dir: Custom log directory path (default: <project_root>/logs)
                - file_name_pattern: Custom file naming (default: week-based)
        """
        super().__init__(**config)

        self._log_dir = Path(config.get("log_dir", get_project_root() / "logs"))
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Metrics
        self._total_writes = 0
        self._failed_writes = 0

    @property
    def name(self) -> str:
        """Backend name."""
        return "file"

    def write(self, log_entry: Dict[str, Any]) -> bool:
        """
        Write log entry to weekly file using write_to_file.

        Args:
            log_entry: Log entry dictionary

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            # Extract date from log entry
            from datetime import date as date_type

            log_date_str = log_entry.get("date", date.today().isoformat())
            log_date = date_type.fromisoformat(log_date_str)

            # Get file path for this date
            file_path = self._log_dir / self._get_filename(log_date)

            # Convert log entry to JSON string
            import json

            payload = json.dumps(log_entry, ensure_ascii=False)

            # Write directly to file (simpler than env manipulation)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with file_path.open(mode="a", encoding="utf-8") as f:
                f.write(payload)
                f.write("\n")

            self._total_writes += 1
            return True

        except Exception as e:
            import sys

            print(f"FileBackend write failed: {e}", file=sys.stderr)
            self._failed_writes += 1
            return False

    def _get_filename(self, log_date: date) -> str:
        """Get the filename for a given date."""
        week_start, week_end, week_number = get_week_date_range(log_date)
        return f"wk{week_number:02d}_{week_start.isoformat()}--{week_end.isoformat()}.json"

    def get_metrics(self) -> Dict[str, Any]:
        """Get file backend metrics."""
        return {
            "backend": self.name,
            "total_writes": self._total_writes,
            "failed_writes": self._failed_writes,
            "log_directory": str(self._log_dir),
        }


__all__ = ["FileBackend"]
