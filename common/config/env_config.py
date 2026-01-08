# public/common/config/env_config.py
import os
from typing import Optional
from common.api_error import ConfigurationError


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get Env variable with optional default
    """
    return os.getenv(name, default=default)


def require_env(name: str) -> str:
    """
    Get required environment variable or raise immediately.
    """
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(f"Missing required env variables: {name}")
    return value


__all__ = ["require_env", "get_env"]
