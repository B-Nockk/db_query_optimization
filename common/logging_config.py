# public/common/logging_config.py
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LoggerConfig:
    log_level: str


logger_config = LoggerConfig(
    log_level=os.getenv("LOG_LEVEL") or "INFO",
)

__all__ = ["LoggerConfig", "logger_config"]
