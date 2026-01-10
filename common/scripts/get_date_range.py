# public/common/scripts/get_date_range.py
from datetime import date, timedelta
from typing import Optional


def get_week_date_range(target_date: Optional[date] = None) -> tuple[date, date, int]:
    """
    Calculate the start and end dates of the week containing the target date.

    Weeks are defined as Monday through Sunday (ISO week definition).

    Args:
        target_date: The date to find the week for. Defaults to today if not provided.

    Returns:
        A tuple of (week_start, week_end, week_number) as date objects and int.
        Week number follows ISO 8601 standard (1-53).

    Example:
        >>> get_week_date_range(date(2024, 1, 10))  # Wednesday
        (date(2024, 1, 8), date(2024, 1, 14), 2)  # Monday to Sunday, week 2
    """
    _date = target_date or date.today()
    week_start = _date - timedelta(days=_date.weekday())
    week_end = week_start + timedelta(days=6)
    week_number = _date.isocalendar()[1]
    return week_start, week_end, week_number


__all__ = ["get_week_date_range"]
