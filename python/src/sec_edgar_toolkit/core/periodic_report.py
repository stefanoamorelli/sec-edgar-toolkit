"""Shared base for periodic report objects (10-K, 10-Q)."""

from __future__ import annotations

import logging
from typing import Dict, Union

from ..parsers.items import TenKItem, TenQItem

logger = logging.getLogger(__name__)


class PeriodicReport:
    """Shared behavior for 10-K / 10-Q report objects."""

    #: mapping of section attribute -> item key in the extracted-items dict
    SECTION_ITEMS: Dict[str, Union[str, TenKItem, TenQItem]] = {}

    def __init__(self, filing) -> None:
        self._filing = filing
        try:
            items = filing.extract_items()
        except Exception as exc:  # pragma: no cover - network/parse failures
            logger.warning("Item extraction failed: %s", exc)
            items = {}
        self._items = items

        # Only expose sections that were actually found, so callers can
        # feature-detect with hasattr().
        for attr, item_key in self.SECTION_ITEMS.items():
            content = items.get(item_key)
            if content:
                setattr(self, attr, content)

    @property
    def items(self) -> Dict[str, str]:
        return self._items

    @property
    def financials(self):
        from .financials import Financials

        return Financials.extract(self._filing)
