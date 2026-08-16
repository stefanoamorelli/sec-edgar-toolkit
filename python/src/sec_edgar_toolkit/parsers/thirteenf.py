"""
Parser for Form 13F institutional holdings reports.

A 13F filing has two XML documents: the information table (one
``infoTable`` entry per position) and the primary document (cover page
with the filing manager, report period, and summary totals). Both are
parsed with the standard library; matching is namespace-agnostic so
schema-version changes don't break it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from xml.etree import ElementTree as ET


def _local(tag: Any) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _find(elem: ET.Element, name: str) -> Optional[ET.Element]:
    for child in elem.iter():
        if _local(child.tag) == name:
            return child
    return None


def _text(elem: Optional[ET.Element]) -> str:
    return elem.text.strip() if elem is not None and elem.text else ""


def _number(elem: Optional[ET.Element]) -> float:
    text = _text(elem).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


class ThirteenFParser:
    """Parses the 13F information table and cover page."""

    def __init__(self, information_table_xml: Union[str, bytes]) -> None:
        if isinstance(information_table_xml, str):
            information_table_xml = information_table_xml.encode(
                "utf-8", errors="ignore"
            )
        self.root = ET.fromstring(information_table_xml)

    def parse_holdings(self) -> List[Dict[str, Any]]:
        """
        Parse every position in the information table.

        Returns:
            One record per ``infoTable`` entry with ``name_of_issuer``,
            ``title_of_class``, ``cusip``, ``value`` (USD),
            ``shares_or_principal_amount``, ``shares_or_principal_type``,
            ``put_call``, ``investment_discretion``, ``other_manager``,
            and ``voting_authority`` (sole/shared/none).
        """
        holdings: List[Dict[str, Any]] = []
        for entry in self.root.iter():
            if _local(entry.tag) != "infoTable":
                continue

            children = {_local(child.tag): child for child in entry}

            shares_elem = children.get("shrsOrPrnAmt")
            shares = 0.0
            shares_type = ""
            if shares_elem is not None:
                shares = _number(_find(shares_elem, "sshPrnamt"))
                shares_type = _text(_find(shares_elem, "sshPrnamtType"))

            voting = {"sole": 0.0, "shared": 0.0, "none": 0.0}
            voting_elem = children.get("votingAuthority")
            if voting_elem is not None:
                voting = {
                    "sole": _number(_find(voting_elem, "Sole")),
                    "shared": _number(_find(voting_elem, "Shared")),
                    "none": _number(_find(voting_elem, "None")),
                }

            holdings.append(
                {
                    "name_of_issuer": _text(children.get("nameOfIssuer")),
                    "title_of_class": _text(children.get("titleOfClass")),
                    "cusip": _text(children.get("cusip")),
                    "value": _number(children.get("value")),
                    "shares_or_principal_amount": shares,
                    "shares_or_principal_type": shares_type,
                    "put_call": _text(children.get("putCall")),
                    "investment_discretion": _text(
                        children.get("investmentDiscretion")
                    ),
                    "other_manager": _text(children.get("otherManager")),
                    "voting_authority": voting,
                }
            )
        return holdings

    @staticmethod
    def parse_cover_page(primary_doc_xml: Union[str, bytes]) -> Dict[str, Any]:
        """
        Parse the primary document's cover page.

        Returns:
            ``manager_name``, ``period_of_report``, ``report_type``,
            ``is_amendment``, ``table_entry_total``, and
            ``table_value_total``.
        """
        if isinstance(primary_doc_xml, str):
            primary_doc_xml = primary_doc_xml.encode("utf-8", errors="ignore")
        root = ET.fromstring(primary_doc_xml)

        def find_text(name: str) -> str:
            return _text(_find(root, name))

        manager = _find(root, "filingManager")
        manager_name = _text(_find(manager, "name")) if manager is not None else ""

        return {
            "manager_name": manager_name,
            "period_of_report": find_text("periodOfReport"),
            "report_type": find_text("reportType"),
            "is_amendment": find_text("isAmendment").lower() == "true",
            "table_entry_total": _number(_find(root, "tableEntryTotal")),
            "table_value_total": _number(_find(root, "tableValueTotal")),
        }
