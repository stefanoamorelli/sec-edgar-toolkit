"""
Filing class providing edgartools-compatible API.

This class represents a SEC filing and provides methods to access its content,
structured data, and XBRL information.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Union

from ..client import SecEdgarApi
from ..parsers import FinancialFormParser, OwnershipFormParser
from ..parsers.item_extractor import ItemExtractor

logger = logging.getLogger(__name__)


class Filing:
    """
    Represents a SEC filing with content and metadata.

    This class provides an edgartools-compatible interface for working with
    filing data, including raw text, structured data, and XBRL content.

    Attributes:
        cik: Company's Central Index Key
        accession_number: Filing accession number
        form_type: Type of SEC form (e.g., "10-K", "10-Q")
        filing_date: Date the filing was submitted
        company_name: Name of the filing company
        url: URL to the filing on SEC website
    """

    def __init__(
        self,
        cik: Union[str, int],
        accession_number: str,
        form_type: str,
        filing_date: str,
        api: Optional[SecEdgarApi] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a Filing object.

        Args:
            cik: Company CIK
            accession_number: Filing accession number
            form_type: Form type (e.g., "10-K")
            filing_date: Filing date
            api: SEC Edgar API client instance
            **kwargs: Additional filing metadata
        """
        if api is None:
            from .global_functions import _get_api

            api = _get_api()

        self._api = api
        self.cik = str(cik).zfill(10)
        self.accession_number = accession_number
        self.form_type = form_type
        self.filing_date = filing_date

        # Additional metadata
        self.company_name = kwargs.get("company_name", "")
        self.period_of_report = kwargs.get("period_of_report", "")
        self.accepted_date = kwargs.get("accepted_date", "")
        self.size = kwargs.get("size", 0)

        # Cache for filing details and content
        self._filing_details: Optional[Dict[str, Any]] = None
        self._text_content: Optional[str] = None
        self._obj_content: Optional[Dict[str, Any]] = None
        self._xbrl_instance: Optional[XBRLInstance] = None
        self._extracted_items: Optional[Dict[str, str]] = None
        self._item_extractor = ItemExtractor()

        # Construct URLs
        self.url = self._construct_filing_url()

    def _construct_filing_url(self) -> str:
        """Construct the SEC filing URL."""
        accession_clean = self.accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{accession_clean}/{self.accession_number}-index.htm"

    def _get_filing_details(self) -> Dict[str, Any]:
        """Get detailed filing information from SEC API."""
        if self._filing_details is None:
            try:
                self._filing_details = self._api.get_filing(
                    self.cik, self.accession_number
                )
            except Exception as e:
                logger.warning(f"Failed to get filing details: {e}")
                self._filing_details = {}
        return self._filing_details

    def text(self, format: str = "text") -> str:
        """
        Get the raw text content of the filing.

        Args:
            format: Format type ("text", "html", or "raw")

        Returns:
            Raw filing content as string

        Example:
            >>> filing = Filing("0000320193", "0000320193-23-000077", "10-K", "2023-11-03")
            >>> content = filing.text()
        """
        if self._text_content is None:
            self._text_content = self._fetch_filing_content()

        if format == "html" or format == "raw":
            return self._text_content
        else:  # text format
            return self._clean_text_content(self._text_content)

    def _fetch_filing_content(self) -> str:
        """Fetch the raw filing content from SEC archives."""
        # Get filing details to find the main document
        details = self._get_filing_details()

        # Find the main document
        main_document = None
        directory = details.get("directory", {})
        items = directory.get("item", [])

        if isinstance(items, list):
            for item in items:
                # Look for the main filing document
                name = item.get("name", "")
                if (
                    name.endswith(".htm") or name.endswith(".txt")
                ) and not name.endswith("-index.htm"):
                    # Priority: .htm files, then form type in name
                    if name.endswith(".htm") and (
                        self.form_type.lower() in name.lower()
                        or "filing" in name.lower()
                    ):
                        main_document = name
                        break
                    elif main_document is None:
                        main_document = name

        if not main_document:
            # Fallback: try common naming patterns
            accession_clean = self.accession_number.replace("-", "")
            main_document = f"{accession_clean}.txt"

        # Construct document URL
        document_url = f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{accession_clean}/{main_document}"

        try:
            # Use the HTTP client to fetch content
            content = self._api.http_client.get_raw(document_url)
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")
            return content
        except Exception as e:
            logger.error(f"Failed to fetch filing content from {document_url}: {e}")
            return ""

    def _clean_text_content(self, content: str) -> str:
        """Clean HTML/SGML content to plain text."""
        if not content:
            return ""

        # Remove HTML/SGML tags
        clean_content = re.sub(r"<[^>]+>", " ", content)

        # Clean up whitespace
        clean_content = re.sub(r"\s+", " ", clean_content)
        clean_content = clean_content.strip()

        return clean_content

    def obj(self) -> Dict[str, Any]:
        """
        Get structured data extracted from the filing.

        Returns:
            Dictionary containing parsed filing data

        Example:
            >>> filing = Filing("0000320193", "0000320193-23-000077", "10-K", "2023-11-03")
            >>> structured_data = filing.obj()
        """
        if self._obj_content is None:
            self._obj_content = self._parse_structured_content()
        return self._obj_content

    def _parse_structured_content(self) -> Dict[str, Any]:
        """Parse the filing content into structured data."""
        content = self.text(format="raw")

        try:
            # Use appropriate parser based on form type
            if self.form_type in ["3", "4", "5"]:
                # Ownership forms
                parser = OwnershipFormParser(content)
                return parser.parse_all()
            elif self.form_type in ["10-K", "10-Q", "8-K"]:
                # Financial forms
                parser = FinancialFormParser(content)
                return parser.parse_all().__dict__
            else:
                # Generic parsing for other forms
                return self._parse_generic_content(content)
        except Exception as e:
            logger.warning(f"Failed to parse structured content: {e}")
            return {"raw_content": content, "parse_error": str(e)}

    def _parse_generic_content(self, content: str) -> Dict[str, Any]:
        """Generic parsing for form types without specific parsers."""
        result = {
            "form_type": self.form_type,
            "filing_date": self.filing_date,
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

        # For 8-K forms, try to extract current event info
        if self.form_type == "8-K":
            result.update(self._parse_8k_events(content))

        return result

    def _parse_8k_events(self, content: str) -> Dict[str, Any]:
        """Parse 8-K current events information."""
        events = {}

        # Common 8-K item patterns
        item_patterns = {
            "item_1_01": r"Item 1\.01[^a-zA-Z]*([^\n\r]+)",
            "item_2_02": r"Item 2\.02[^a-zA-Z]*([^\n\r]+)",
            "item_3_02": r"Item 3\.02[^a-zA-Z]*([^\n\r]+)",
            "item_5_02": r"Item 5\.02[^a-zA-Z]*([^\n\r]+)",
            "item_7_01": r"Item 7\.01[^a-zA-Z]*([^\n\r]+)",
            "item_8_01": r"Item 8\.01[^a-zA-Z]*([^\n\r]+)",
        }

        for item, pattern in item_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                events[item] = match.group(1).strip()

        return {"current_events": events} if events else {}

    def extract_items(self, item_numbers: Optional[list[str]] = None) -> Dict[str, str]:
        """
        Extract individual items from the filing (e.g., Item 1, Item 1A, etc.).

        Args:
            item_numbers: Optional list of specific item numbers to extract.
                         If None, extracts all items.

        Returns:
            Dictionary mapping item numbers to their content

        Example:
            >>> filing = company.get_filing("10-K")
            >>> items = filing.extract_items()
            >>> print(items["1"])  # Business section
            >>> print(items["1A"]) # Risk Factors

            >>> # Extract specific items only
            >>> items = filing.extract_items(["1", "1A", "7"])
        """
        if self._extracted_items is None:
            # Get the filing content
            content = self.text()

            # Extract all items
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
            # Return only requested items
            return {k: v for k, v in self._extracted_items.items() if k in item_numbers}
        else:
            return self._extracted_items

    def get_item(self, item_number: str) -> Optional[str]:
        """
        Get a specific item from the filing.

        Args:
            item_number: The item number to retrieve (e.g., "1", "1A", "7")

        Returns:
            The item content or None if not found

        Example:
            >>> filing = company.get_filing("10-K")
            >>> risk_factors = filing.get_item("1A")
            >>> business = filing.get_item("1")
        """
        items = self.extract_items([item_number])
        return items.get(item_number)

    @property
    def items(self) -> Dict[str, str]:
        """
        Get all extracted items from the filing.

        This is a convenience property that extracts all items.

        Returns:
            Dictionary mapping item numbers to their content

        Example:
            >>> filing = company.get_filing("10-K")
            >>> all_items = filing.items
            >>> for item_num, content in all_items.items():
            ...     print(f"Item {item_num}: {len(content)} characters")
        """
        return self.extract_items()

    def xbrl(self) -> XBRLInstance:
        """
        Get XBRL instance for this filing.

        Returns:
            XBRLInstance object for querying financial data

        Example:
            >>> filing = Filing("0000320193", "0000320193-23-000077", "10-K", "2023-11-03")
            >>> xbrl = filing.xbrl()
            >>> facts = xbrl.query()
        """
        if self._xbrl_instance is None:
            self._xbrl_instance = XBRLInstance(self, api=self._api)
        return self._xbrl_instance

    def __getattr__(self, name: str) -> Any:
        """
        Dynamic attribute access for filing metadata.

        This allows accessing any field from the filing details data
        using dot notation, similar to edgartools.
        """
        details = self._get_filing_details()

        # Check if the attribute exists in filing details
        if name in details:
            return details[name]

        # Check common aliases
        field_mapping = {
            "date": "filing_date",
            "form": "form_type",
            "company": "company_name",
        }

        mapped_field = field_mapping.get(name)
        if mapped_field:
            return getattr(self, mapped_field, None)

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
