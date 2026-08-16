"""Structured view of an 8-K current report, returned by ``Filing.obj()``."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..parsers.item_extractor import EightKItem
from .attachments import Attachment

_DATE_OF_REPORT_RE = re.compile(
    r"Date\s+of\s+Report[^:]{0,80}:?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})"
)

_ITEM_CODE_RE = re.compile(r"\bItem\s+(\d\.\d{2})", re.IGNORECASE)


class EightK:
    """8-K current report: reported items, date of report, press releases."""

    def __init__(self, filing) -> None:
        self._filing = filing
        text = filing.text(format="raw")
        clean = filing.text()

        # Items present in the report body (skip cover-page/TOC noise by
        # requiring the canonical "Item N.NN" marker).
        codes: List[str] = []
        for match in _ITEM_CODE_RE.finditer(clean):
            code = match.group(1)
            if code not in codes:
                codes.append(code)
        self.items: List[str] = codes

        self.date_of_report: Optional[str] = self._extract_date_of_report(clean, text)

        self.attachments: List[Attachment] = filing.attachments
        press = [a for a in self.attachments if a.is_press_release]
        self.press_releases: List[Dict[str, Any]] = [a.to_dict() for a in press]
        self.has_press_release: bool = bool(press)

    def _extract_date_of_report(self, clean: str, raw: str) -> Optional[str]:
        for source in (clean, raw):
            match = _DATE_OF_REPORT_RE.search(source)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
        # Fall back to the reporting period from filing metadata.
        period = getattr(self._filing, "period_of_report", None)
        if period:
            try:
                parsed = datetime.fromisoformat(str(period))
                return f"{parsed:%B} {parsed.day}, {parsed.year}"
            except ValueError:
                return str(period)
        return None

    def has_item(self, item_code: Union[str, EightKItem]) -> bool:
        """
        True when the given item is present.

        Accepts an ``EightKItem`` or a string (``"2.02"`` / ``"Item 2.02"``).
        """
        code = str(item_code.value if isinstance(item_code, EightKItem) else item_code)
        code = code.replace("Item", "").strip()
        return code in self.items

    def __repr__(self) -> str:
        return f"EightK(items={self.items}, date_of_report='{self.date_of_report}')"
