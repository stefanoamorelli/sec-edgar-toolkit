"""Helpers for optional dependencies."""

from __future__ import annotations


def require_pandas():
    """Import pandas or fail with an actionable message."""
    try:
        import pandas
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "pandas is required for DataFrame output. "
            "Install it with: pip install 'sec-edgar-toolkit[pandas]'"
        ) from exc
    return pandas
