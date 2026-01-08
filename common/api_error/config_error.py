# public/common/api_error/config_error.py
class ConfigurationError(RuntimeError):
    """
    Raised when application configuration is invalid.
    """

    pass


__all__ = ["ConfigurationError"]
