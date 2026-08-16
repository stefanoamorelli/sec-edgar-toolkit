"""
Structured view of a Form 13F holdings report, returned by ``Filing.obj()``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..parsers.thirteenf import ThirteenFParser

logger = logging.getLogger(__name__)


class Holding13F:
    """One position from the information table."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.name_of_issuer: str = data.get("name_of_issuer", "")
        self.title_of_class: str = data.get("title_of_class", "")
        self.cusip: str = data.get("cusip", "")
        self.value: float = data.get("value", 0.0)
        self.shares: float = data.get("shares_or_principal_amount", 0.0)
        self.shares_type: str = data.get("shares_or_principal_type", "")
        self.put_call: str = data.get("put_call", "")
        self.investment_discretion: str = data.get("investment_discretion", "")
        self.other_manager: str = data.get("other_manager", "")
        self.voting_authority: Dict[str, float] = data.get("voting_authority", {})

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class ThirteenF:
    """Parsed 13F report: cover-page metadata plus every position."""

    def __init__(
        self, holdings: List[Dict[str, Any]], cover: Optional[Dict[str, Any]] = None
    ) -> None:
        cover = cover or {}
        self.holdings: List[Holding13F] = [Holding13F(h) for h in holdings]
        self.manager_name: str = cover.get("manager_name", "")
        self.period_of_report: str = cover.get("period_of_report", "")
        self.report_type: str = cover.get("report_type", "")
        self.is_amendment: bool = bool(cover.get("is_amendment"))
        self.reported_entry_total: float = cover.get("table_entry_total", 0.0)
        self.reported_value_total: float = cover.get("table_value_total", 0.0)

    @property
    def holding_count(self) -> int:
        return len(self.holdings)

    @property
    def total_value(self) -> float:
        """Sum of position values as reported (USD)."""
        return sum(holding.value for holding in self.holdings)

    def by_issuer(self, name: str) -> List[Holding13F]:
        """Positions whose issuer name contains ``name`` (case-insensitive)."""
        needle = name.lower()
        return [h for h in self.holdings if needle in h.name_of_issuer.lower()]

    def top_holdings(self, n: int = 10) -> List[Holding13F]:
        """The ``n`` largest positions by reported value."""
        return sorted(self.holdings, key=lambda h: h.value, reverse=True)[:n]

    @classmethod
    def from_filing(cls, filing) -> "ThirteenF":
        """
        Build a ThirteenF from a filing by locating the information table
        and primary document in its archive folder.
        """
        table_xml: Optional[bytes] = None
        primary_xml: Optional[bytes] = None

        for attachment in filing.attachments:
            name = attachment.document.lower()
            if not name.endswith(".xml"):
                continue
            try:
                if name == "primary_doc.xml":
                    primary_xml = filing._api.http_client.get_raw(attachment.url)
                elif table_xml is None:
                    content = filing._api.http_client.get_raw(attachment.url)
                    if b"informationTable" in (
                        content if isinstance(content, bytes) else content.encode()
                    ):
                        table_xml = content
            except Exception as exc:
                logger.warning(f"Could not fetch {attachment.document}: {exc}")

        if table_xml is None:
            raise ValueError("No 13F information table found in the filing")

        holdings = ThirteenFParser(table_xml).parse_holdings()
        cover = (
            ThirteenFParser.parse_cover_page(primary_xml)
            if primary_xml is not None
            else None
        )
        return cls(holdings, cover)
