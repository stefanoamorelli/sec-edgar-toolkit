"""Filing collection type with convenience helpers."""

from __future__ import annotations

from typing import Optional


class Filings(list):
    """
    A list of Filing objects, newest first.

    Behaves like a plain list (iteration, truthiness, len, slicing) and adds
    the ``latest()`` accessor.
    """

    def latest(self, n: int = 1):
        """
        Return the most recent filing(s).

        Args:
            n: Number of filings to return. With ``n=1`` (default) a single
               Filing (or None when empty) is returned; otherwise a Filings
               slice of up to ``n`` entries.
        """
        if n == 1:
            return self[0] if self else None
        return Filings(self[:n])

    def filter(self, form: Optional[str] = None) -> "Filings":
        """Return a new Filings collection filtered by form type."""
        if form is None:
            return Filings(self)
        return Filings(f for f in self if getattr(f, "form_type", None) == form)

    def filter_by_form(self, form: str) -> "Filings":
        """Alias of :meth:`filter` (matches the TypeScript API)."""
        return self.filter(form)
