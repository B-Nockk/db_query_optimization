# public/common/structlog_config.py
import sys
import logging
import structlog
from rich.traceback import install as install_rich_traceback

from .logging_config import logger_config

# Install Rich tracebacks globally for better exception display
install_rich_traceback(show_locals=True, width=None, extra_lines=3)

LOG_LEVEL = getattr(logging, logger_config.log_level.upper())

# Configure structlog with Rich
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        # ConsoleRenderer handles the final formatting
        structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.RichTracebackFormatter(
                show_locals=False,
                width=None,
                suppress=[
                    "starlette",
                    "uvicorn",
                    "fastapi",
                ],  # Filter framework noise
            ),
        ),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(LOG_LEVEL),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()

__all__ = ["log"]
