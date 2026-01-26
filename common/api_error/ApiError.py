# common/api_error/ApiError.py
class AppError(Exception):
    """Base error for all application-specific issues."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "INTERNAL_ERROR",
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(self.message)


class DatabaseError(AppError):
    """Specific for DB issues."""

    pass


__all__ = ["AppError", "DatabaseError"]
