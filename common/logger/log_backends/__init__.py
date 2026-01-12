# public/common/logger/log_backends/__init__.py
"""
Log persistence backends.

Supports multiple backends: file, datadog, prometheus, etc.
Configure via LOG_BACKENDS environment variable (comma-separated).

Example:
    LOG_BACKENDS=file,datadog
"""

from .base import *
from .file_backend import *
from .registry import *
