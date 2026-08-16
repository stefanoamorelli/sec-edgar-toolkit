"""
Form-specific report objects returned by ``Filing.obj()``.

- ``EightK`` — 8-K current report: reported items, date of report,
  press-release exhibits.
- ``TenK`` / ``TenQ`` — annual/quarterly report: named sections
  (``business``, ``risk_factors``, ``mda``) extracted from the document,
  plus ``financials`` backed by XBRL company facts.
- ``Attachment`` — one document in the filing's archive folder.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PRESS_RELEASE_RE = re.compile(r"(ex[-_]?99|press[-_]?release)", re.IGNORECASE)

_DATE_OF_REPORT_RE = re.compile(
    r"Date\s+of\s+Report[^:]{0,80}:?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})"
)

_ITEM_CODE_RE = re.compile(r"\bItem\s+(\d\.\d{2})", re.IGNORECASE)


class Attachment:
    """A document inside a filing's archive folder."""

    def __init__(self, name: str, url: str, size: Optional[int] = None) -> None:
        self.document = name
        self.name = name
        self.url = url
        self.size = size

    @property
    def is_press_release(self) -> bool:
        return bool(_PRESS_RELEASE_RE.search(self.document))

    def to_dict(self) -> Dict[str, Any]:
        return {"document": self.document, "url": self.url, "size": self.size}

    def __repr__(self) -> str:
        return f"Attachment(document='{self.document}')"


class EightK:
    """Structured view of an 8-K current report."""

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

    def has_item(self, item_code: str) -> bool:
        """True when the given item (e.g. ``"2.02"`` or ``"Item 2.02"``) is present."""
        code = item_code.replace("Item", "").strip()
        return code in self.items

    def __repr__(self) -> str:
        return f"EightK(items={self.items}, date_of_report='{self.date_of_report}')"


class _CompanyReport:
    """Shared behavior for 10-K / 10-Q report objects."""

    #: mapping of section attribute -> item key in the extracted-items dict
    SECTION_ITEMS: Dict[str, str] = {}

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


class TenK(_CompanyReport):
    """Structured view of a 10-K annual report."""

    SECTION_ITEMS = {"business": "1", "risk_factors": "1A", "mda": "7"}

    def __repr__(self) -> str:
        return f"TenK(sections={list(self._items.keys())})"


class TenQ(_CompanyReport):
    """Structured view of a 10-Q quarterly report."""

    SECTION_ITEMS = {"mda": "2", "risk_factors": "II-1A"}

    def __repr__(self) -> str:
        return f"TenQ(sections={list(self._items.keys())})"
