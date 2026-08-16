"""Structured view of a 10-Q quarterly report, returned by ``Filing.obj()``."""

from __future__ import annotations

from ..parsers.items import TenQItem
from .periodic_report import PeriodicReport


class TenQ(PeriodicReport):
    """10-Q quarterly report: named sections and XBRL-backed financials."""

    SECTION_ITEMS = {
        "mda": TenQItem.MANAGEMENT_DISCUSSION_AND_ANALYSIS,
        "risk_factors": TenQItem.RISK_FACTORS,
    }

    def __repr__(self) -> str:
        return f"TenQ(sections={list(self._items.keys())})"
