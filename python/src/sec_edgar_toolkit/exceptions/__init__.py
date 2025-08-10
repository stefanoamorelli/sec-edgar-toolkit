"""Exception classes for SEC EDGAR API."""

from .base import SecEdgarApiError
from .http import AuthenticationError, NotFoundError, RateLimitError

__all__ = [
    "SecEdgarApiError",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
]
