"""SEC filing endpoints."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

from ..utils import FilingFilter, HttpClient

logger = logging.getLogger(__name__)


class FilingsEndpoints:
    """
    Endpoints for SEC filing data and submissions.

    This class handles all filing-related API endpoints including:
    - Company submissions (all filings for a company)
    - Individual filing details
    - Filing document retrieval
    - Recent filings across all companies via EDGAR RSS
    - Filtering and search capabilities

    Args:
        http_client: HTTP client instance for making requests

    Example:
        >>> client = HttpClient("MyApp/1.0 (contact@example.com)")
        >>> endpoints = FilingsEndpoints(client)
        >>> submissions = endpoints.get_company_submissions("0000320193")
    """

    DATA_URL = "https://data.sec.gov/"
    ARCHIVES_URL = "https://www.sec.gov/"
    CURRENT_FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

    def __init__(self, http_client: HttpClient) -> None:
        """Initialize filings endpoints."""
        self.http_client = http_client

    def get_company_submissions(
        self,
        cik: Union[str, int],
        submission_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all submissions for a specific company.

        This endpoint returns detailed company information along with
        all their filing history.

        Args:
            cik: Company CIK number
            submission_type: Filter by form type (e.g., '10-K', '10-Q')
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)

        Returns:
            Company submissions data including all filings

        Raises:
            NotFoundError: If company CIK is not found

        Example:
            >>> subs = endpoints.get_company_submissions("0000320193")
            >>> print(f"Company: {subs['name']}")
            >>> print(f"Total filings: {len(subs['filings']['recent'])}")
        """
        # Normalize CIK to 10-digit string
        cik_str = str(cik).zfill(10)

        url = urljoin(self.DATA_URL, f"submissions/CIK{cik_str}.json")
        data = self.http_client.get(url)

        return self._filter_submissions(data, submission_type, from_date, to_date)

    def get_company_submissions_page(self, page_name: str) -> Dict[str, Any]:
        """
        Fetch one older-history submissions page.

        The main submissions payload lists additional filing history in
        ``filings.files`` (e.g. ``CIK0000320193-submissions-001.json``);
        this fetches one of those pages. The returned payload has the
        same columnar shape as ``filings.recent``.

        Args:
            page_name: The ``name`` entry from ``filings.files``

        Returns:
            Columnar filings data (``accessionNumber``, ``form``, ...)
        """
        url = urljoin(self.DATA_URL, f"submissions/{page_name}")
        return self.http_client.get(url)

    def _filter_submissions(
        self,
        data: Dict[str, Any],
        submission_type: Optional[str],
        from_date: Optional[str],
        to_date: Optional[str],
    ) -> Dict[str, Any]:

        # Apply filters if provided
        if submission_type or from_date or to_date:
            filings_data = data.get("filings", {})
            if isinstance(filings_data, dict) and "recent" in filings_data:
                filtered_filings = FilingFilter.filter_filings(
                    filings_data["recent"],
                    submission_type,
                    from_date,
                    to_date,
                )
                filings_data["recent"] = filtered_filings

        return data

    def get_filing(
        self,
        cik: Union[str, int],
        accession_number: str,
    ) -> Dict[str, Any]:
        """
        Get specific filing details and documents.

        Args:
            cik: Company CIK number
            accession_number: Accession number of the filing

        Returns:
            Filing details including document list

        Example:
            >>> filing = endpoints.get_filing("0000320193", "0000320193-23-000077")
            >>> print(f"Form type: {filing['form']}")
            >>> print(f"Filed on: {filing['filingDate']}")
        """
        # Archive folders live on www.sec.gov and use the unpadded CIK;
        # the folder listing is served as index.json
        cik_str = str(int(str(cik)))
        accession = accession_number.replace("-", "")

        url = urljoin(
            self.ARCHIVES_URL,
            f"Archives/edgar/data/{cik_str}/{accession}/index.json",
        )

        return self.http_client.get(url)

    def get_recent_filings(
        self,
        form_type: Optional[Union[str, List[str]]] = None,
        limit: int = 40,
        owner: str = "include",
        start: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get recent filings across all companies using the SEC EDGAR Atom feed.

        This endpoint queries the SEC EDGAR current filings feed to retrieve
        recently filed documents without requiring a specific company identifier.

        Args:
            form_type: Filter by form type(s) (e.g., "10-K", ["10-K", "10-Q"]).
                       When a list is provided, multiple requests are made and
                       results are merged.
            limit: Maximum number of filings to return (default: 40, max: 100)
            owner: Ownership filter - "include", "exclude", or "only" (default: "include")
            start: Starting offset for pagination (default: 0)

        Returns:
            List of filing dicts with keys: cik, accession_number, form_type,
            filing_date, company_name, url

        Example:
            >>> filings = endpoints.get_recent_filings(form_type="10-K", limit=10)
            >>> for f in filings:
            ...     print(f"{f['company_name']}: {f['form_type']} ({f['filing_date']})")
        """
        if isinstance(form_type, list):
            # Merge results from multiple form types
            all_filings: List[Dict[str, Any]] = []
            per_type_limit = max(limit // len(form_type), 10)
            for ft in form_type:
                type_filings = self._fetch_current_filings_feed(
                    form_type=ft, count=per_type_limit, owner=owner, start=start
                )
                all_filings.extend(type_filings)

            # Sort by filing date descending and trim to limit
            all_filings.sort(key=lambda x: x.get("filing_date", ""), reverse=True)
            return all_filings[:limit]

        return self._fetch_current_filings_feed(
            form_type=form_type, count=min(limit, 100), owner=owner, start=start
        )

    def _fetch_current_filings_feed(
        self,
        form_type: Optional[str] = None,
        count: int = 40,
        owner: str = "include",
        start: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent filings from the SEC EDGAR Atom feed.

        Args:
            form_type: Form type filter (e.g., "10-K")
            count: Number of results to fetch
            owner: Ownership filter
            start: Pagination offset

        Returns:
            List of filing dicts parsed from the Atom feed
        """
        params = {
            "action": "getcurrent",
            "type": form_type or "",
            "dateb": "",
            "owner": owner,
            "count": str(count),
            "search_text": "",
            "start": str(start),
            "output": "atom",
        }

        try:
            content = self.http_client.get_raw(self.CURRENT_FILINGS_URL, params=params)
            return self._parse_atom_feed(content)
        except Exception as e:
            logger.error(f"Failed to fetch current filings feed: {e}")
            return []

    @staticmethod
    def _parse_atom_feed(content: bytes) -> List[Dict[str, Any]]:
        """
        Parse an Atom feed of SEC filings into structured dicts.

        Args:
            content: Raw XML bytes of the Atom feed

        Returns:
            List of filing dicts with keys: cik, accession_number, form_type,
            filing_date, company_name, url
        """
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        filings: List[Dict[str, Any]] = []

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse Atom feed: {e}")
            return filings

        for entry in root.findall("atom:entry", ns):
            try:
                title_el = entry.find("atom:title", ns)
                title = (title_el.text or "") if title_el is not None else ""

                link_el = entry.find("atom:link", ns)
                url = link_el.get("href", "") if link_el is not None else ""

                summary_el = entry.find("atom:summary", ns)
                summary = (
                    summary_el.text.strip()
                    if summary_el is not None and summary_el.text
                    else ""
                )

                category_el = entry.find("atom:category", ns)
                form = category_el.get("term", "") if category_el is not None else ""

                # Parse CIK from title: "10-K - Company Name (0000946644) (Filer)"
                cik = ""
                cik_match = re.search(r"\((\d{7,10})\)", title)
                if cik_match:
                    cik = cik_match.group(1).zfill(10)

                # Parse accession number from summary: "AccNo: 0001493152-26-013301"
                accession = ""
                acc_match = re.search(r"AccNo.*?(\d{10}-\d{2}-\d{6})", summary)
                if acc_match:
                    accession = acc_match.group(1)

                # Parse filing date from summary: "Filed: 2026-03-27"
                filing_date = ""
                date_match = re.search(r"Filed.*?(\d{4}-\d{2}-\d{2})", summary)
                if date_match:
                    filing_date = date_match.group(1)

                # Parse company name from title: "10-K - Company Name (CIK) (Filer)"
                company_name = ""
                name_match = re.match(r"[\w\-/]+ - (.+?)\s*\(\d+\)", title)
                if name_match:
                    company_name = name_match.group(1).strip()

                filings.append(
                    {
                        "cik": cik,
                        "accession_number": accession,
                        "form_type": form,
                        "filing_date": filing_date,
                        "company_name": company_name,
                        "url": url,
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to parse feed entry: {e}")
                continue

        return filings
