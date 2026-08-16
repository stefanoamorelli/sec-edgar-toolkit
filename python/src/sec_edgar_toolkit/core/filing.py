"""
Filing class of the high-level API.

Represents a single SEC filing and provides access to its content,
documents, structured data, and XBRL information.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from ..client import SecEdgarApi
from ..parsers import OwnershipFormParser
from ..parsers.item_extractor import (
    EightKItem,
    ItemExtractor,
    TenKItem,
    TenQItem,
)

logger = logging.getLogger(__name__)

# Any of the typed item identifiers accepted alongside plain strings
FilingItem = Union[TenKItem, TenQItem, EightKItem]

ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


def _parse_date(value: Any) -> Any:
    """Parse ISO date strings to ``datetime.date``; leave other values as-is."""
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return value
    return value


class Filing:
    """
    Represents a SEC filing with content and metadata.

    Attributes:
        cik: Company's Central Index Key (10-digit, zero-padded)
        accession_number: Filing accession number (dashed)
        form_type: Type of SEC form (e.g., "10-K", "10-Q")
        filing_date: Date the filing was submitted (``datetime.date``)
        company_name: Name of the filing company
        url: URL to the filing index on the SEC website
    """

    def __init__(
        self,
        cik: Union[str, int],
        accession_number: str,
        form_type: str,
        filing_date: Union[str, date],
        api: Optional[SecEdgarApi] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a Filing object.

        Args:
            cik: Company CIK
            accession_number: Filing accession number
            form_type: Form type (e.g., "10-K")
            filing_date: Filing date (ISO string or date)
            api: SEC EDGAR API client instance
            **kwargs: Additional filing metadata (company_name,
                period_of_report, accepted_date, acceptance_datetime,
                file_number, primary_document, size)
        """
        if api is None:
            from .global_functions import _get_api

            api = _get_api()

        self._api = api
        self.cik = str(cik).zfill(10)
        self.accession_number = accession_number
        self.form_type = form_type
        self.filing_date = _parse_date(filing_date)

        # Additional metadata
        self.company_name = kwargs.get("company_name", "")
        self.period_of_report = kwargs.get("period_of_report", "")
        self.accepted_date = kwargs.get("accepted_date", "")
        self.acceptance_datetime = kwargs.get(
            "acceptance_datetime", kwargs.get("accepted_date", "")
        )
        self.file_number = kwargs.get("file_number", "")
        self.primary_document = kwargs.get("primary_document", "")
        self.size = kwargs.get("size", 0)

        # Cache for filing details and content
        self._filing_details: Optional[Dict[str, Any]] = None
        self._text_content: Optional[str] = None
        self._obj_content: Optional[Any] = None
        self._xbrl_instance: Optional[XBRLInstance] = None
        self._extracted_items: Optional[Dict[str, str]] = None
        self._attachments: Optional[List[Any]] = None
        self._item_extractor = ItemExtractor()

        # Construct URLs
        self.url = self._construct_filing_url()

    @property
    def _archive_base(self) -> str:
        accession_clean = self.accession_number.replace("-", "")
        return f"{ARCHIVES_BASE}/{int(self.cik)}/{accession_clean}"

    def _construct_filing_url(self) -> str:
        """Construct the SEC filing index URL."""
        return f"{self._archive_base}/{self.accession_number}-index.htm"

    def _get_filing_details(self) -> Dict[str, Any]:
        """Get detailed filing information from the SEC API."""
        if self._filing_details is None:
            try:
                self._filing_details = self._api.get_filing(
                    self.cik, self.accession_number
                )
            except Exception as e:
                logger.warning(f"Failed to get filing details: {e}")
                self._filing_details = {}
        return self._filing_details

    def _directory_items(self) -> List[Dict[str, Any]]:
        """List documents in the filing's archive folder."""
        details = self._get_filing_details()
        items = details.get("directory", {}).get("item", [])
        return items if isinstance(items, list) else []

    @property
    def attachments(self) -> List[Any]:
        """All documents in the filing's archive folder as Attachment objects."""
        from .attachments import Attachment

        if self._attachments is None:
            self._attachments = [
                Attachment(
                    name=item.get("name", ""),
                    url=f"{self._archive_base}/{item.get('name', '')}",
                    size=item.get("size"),
                )
                for item in self._directory_items()
                if item.get("name") and not item.get("name", "").endswith("/")
            ]
        return self._attachments

    def text(self, format: str = "text") -> str:
        """
        Get the content of the filing's main document.

        Args:
            format: "text" (tags stripped), "html", or "raw"

        Returns:
            Filing content as a string
        """
        if self._text_content is None:
            self._text_content = self._fetch_filing_content()

        if format == "html" or format == "raw":
            return self._text_content
        else:  # text format
            return self._clean_text_content(self._text_content)

    def _pick_main_document(self) -> str:
        """Choose the filing's main document from the archive folder."""
        if self.primary_document:
            return self.primary_document

        main_document = None
        for item in self._directory_items():
            name = item.get("name", "")
            lower = name.lower()
            if not (lower.endswith(".htm") or lower.endswith(".txt")):
                continue
            if lower.endswith("-index.htm") or "/" in name:
                continue
            if lower.endswith(".htm") and (
                self.form_type.lower().replace("-", "") in lower.replace("-", "")
                or "filing" in lower
            ):
                return name
            if main_document is None:
                main_document = name

        if main_document:
            return main_document

        # Fallback: the full-submission text file
        return f"{self.accession_number}.txt"

    def _fetch_filing_content(self) -> str:
        """Fetch the raw content of the filing's main document."""
        document_url = f"{self._archive_base}/{self._pick_main_document()}"

        try:
            content = self._api.http_client.get_raw(document_url)
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")
            return content
        except Exception as e:
            logger.error(f"Failed to fetch filing content from {document_url}: {e}")
            return ""

    def _fetch_ownership_xml(self) -> Optional[str]:
        """Fetch the ownership-form XML document (Forms 3/4/5)."""
        for item in self._directory_items():
            name = item.get("name", "")
            if name.lower().endswith(".xml") and "xsl" not in name.lower():
                url = f"{self._archive_base}/{name}"
                try:
                    content = self._api.http_client.get_raw(url)
                    if isinstance(content, bytes):
                        content = content.decode("utf-8", errors="ignore")
                    return content
                except Exception as e:
                    logger.warning(f"Failed to fetch ownership XML {url}: {e}")

        # Fallback: extract the embedded XML from the full submission file
        raw = self.text(format="raw")
        match = re.search(r"<ownershipDocument>.*?</ownershipDocument>", raw, re.DOTALL)
        if match:
            return match.group(0)
        return None

    def _clean_text_content(self, content: str) -> str:
        """Clean HTML/SGML content to plain text."""
        if not content:
            return ""

        # Drop non-content blocks before stripping tags
        content = re.sub(
            r"<(script|style)\b.*?</\1>", " ", content, flags=re.DOTALL | re.IGNORECASE
        )
        clean_content = re.sub(r"<[^>]+>", " ", content)
        clean_content = re.sub(r"&nbsp;|&#160;", " ", clean_content)
        clean_content = re.sub(r"\s+", " ", clean_content)

        return clean_content.strip()

    def obj(self) -> Any:
        """
        Get a structured, form-specific view of the filing.

        Returns:
            - Forms 3/4/5: ``OwnershipForm`` (attribute access to owner,
              transactions, and holdings; also behaves as the parsed dict)
            - 8-K: ``EightK`` (items, date of report, press releases)
            - 10-K/10-Q: ``TenK``/``TenQ`` (sections and financials)
            - Other forms: dictionary with header metadata
        """
        if self._obj_content is None:
            self._obj_content = self._parse_structured_content()
        return self._obj_content

    def _parse_structured_content(self) -> Any:
        """Parse the filing content into a structured object."""
        try:
            if self.form_type in ["3", "4", "5", "3/A", "4/A", "5/A"]:
                from .ownership import OwnershipForm

                xml_content = self._fetch_ownership_xml()
                if not xml_content:
                    return {"parse_error": "No ownership XML document found"}
                parser = OwnershipFormParser(xml_content)
                return OwnershipForm(parser.parse_all())
            elif self.form_type in ("8-K", "8-K/A"):
                from .form_8k import EightK

                return EightK(self)
            elif self.form_type in ("10-K", "10-K/A"):
                from .form_10k import TenK

                return TenK(self)
            elif self.form_type in ("10-Q", "10-Q/A"):
                from .form_10q import TenQ

                return TenQ(self)
            else:
                return self._parse_generic_content(self.text(format="raw"))
        except Exception as e:
            logger.warning(f"Failed to parse structured content: {e}")
            return {"parse_error": str(e)}

    def _parse_generic_content(self, content: str) -> Dict[str, Any]:
        """Generic parsing for form types without specific parsers."""
        result = {
            "form_type": self.form_type,
            "filing_date": str(self.filing_date),
            "cik": self.cik,
            "accession_number": self.accession_number,
        }

        # Extract basic metadata from SGML headers
        patterns = {
            "company_name": r"COMPANY CONFORMED NAME:\s*([^\n\r]+)",
            "sic": r"STANDARD INDUSTRIAL CLASSIFICATION:\s*([^\n\r]+)",
            "state_of_incorporation": r"STATE OF INCORPORATION:\s*([^\n\r]+)",
            "fiscal_year_end": r"FISCAL YEAR END:\s*([^\n\r]+)",
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()

        return result

    def extract_items(
        self, item_numbers: Optional[List[Union[str, "FilingItem"]]] = None
    ) -> Dict[str, str]:
        """
        Extract individual items from the filing (e.g., Item 1, Item 1A).

        Args:
            item_numbers: Optional list of specific items to extract, as
                strings ("1A") or item enums (``TenKItem.RISK_FACTORS``).
                If None, extracts all items.

        Returns:
            Dictionary mapping item numbers to their content
        """
        if self._extracted_items is None:
            content = self.text()

            try:
                self._extracted_items = self._item_extractor.extract_items(
                    content, self.form_type
                )
            except ValueError as e:
                logger.warning(
                    f"Item extraction not supported for {self.form_type}: {e}"
                )
                self._extracted_items = {}

        if item_numbers:
            return {k: v for k, v in self._extracted_items.items() if k in item_numbers}
        else:
            return self._extracted_items

    def get_item(self, item_number: Union[str, "FilingItem"]) -> Optional[str]:
        """
        Get a specific item from the filing.

        Accepts a string ("1A") or an item enum
        (``TenKItem.RISK_FACTORS``, ``TenQItem.MDA``, ``EightKItem...``).
        """
        items = self.extract_items([item_number])
        return items.get(item_number)

    @property
    def items(self) -> Dict[str, str]:
        """All extracted items from the filing."""
        return self.extract_items()

    def xbrl(self) -> XBRLInstance:
        """
        Get the XBRL instance for this filing.

        Returns:
            XBRLInstance object for querying financial data
        """
        if self._xbrl_instance is None:
            self._xbrl_instance = XBRLInstance(self, api=self._api)
        return self._xbrl_instance

    def __getattr__(self, name: str) -> Any:
        """
        Dynamic attribute access for filing metadata.

        Falls back to the filing-details payload and common aliases.
        """
        # Common aliases first — they need no network round-trip.
        field_mapping = {
            "date": "filing_date",
            "form": "form_type",
            "company": "company_name",
        }
        mapped_field = field_mapping.get(name)
        if mapped_field:
            return getattr(self, mapped_field, None)

        details = self._get_filing_details()
        if name in details:
            return details[name]

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def __str__(self) -> str:
        """String representation of the filing."""
        return f"{self.form_type} filing for CIK {self.cik} on {self.filing_date}"

    def __repr__(self) -> str:
        """Detailed string representation of the filing."""
        return f"Filing(cik='{self.cik}', accession='{self.accession_number}', form='{self.form_type}', date='{self.filing_date}')"


# Import at the end to avoid circular imports
from .xbrl import XBRLInstance
