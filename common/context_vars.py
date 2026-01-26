# common/context_vars.py
from contextvars import ContextVar
from typing import Optional, Any

# This variable is unique to each async task (each request)
request_timer_context_var: ContextVar[Optional[Any]] = ContextVar(
    "request_timer",
    default=None,
)

__all__ = ["request_timer_context_var"]
