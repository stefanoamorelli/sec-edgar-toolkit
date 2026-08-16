"""Structured view of a 10-K annual report, returned by ``Filing.obj()``."""

from __future__ import annotations

from ..parsers.items import TenKItem
from .periodic_report import PeriodicReport


class TenK(PeriodicReport):
    """10-K annual report: named sections and XBRL-backed financials."""

    SECTION_ITEMS = {
        "business": TenKItem.BUSINESS,
        "risk_factors": TenKItem.RISK_FACTORS,
        "mda": TenKItem.MANAGEMENT_DISCUSSION_AND_ANALYSIS,
    }

    def __repr__(self) -> str:
        return f"TenK(sections={list(self._items.keys())})"
