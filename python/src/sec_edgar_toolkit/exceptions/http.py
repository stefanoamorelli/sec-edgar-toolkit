"""HTTP-related exception classes."""

from .base import SecEdgarApiError


class RateLimitError(SecEdgarApiError):
    """Raised when API rate limit is exceeded."""

    pass


class AuthenticationError(SecEdgarApiError):
    """Raised when API authentication fails (missing User-Agent)."""

    pass


class NotFoundError(SecEdgarApiError):
    """Raised when requested resource is not found."""

    pass
