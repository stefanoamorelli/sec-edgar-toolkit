"""SEC filing endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

from ..utils import FilingFilter, HttpClient


class FilingsEndpoints:
    """
    Endpoints for SEC filing data and submissions.

    This class handles all filing-related API endpoints including:
    - Company submissions (all filings for a company)
    - Individual filing details
    - Filing document retrieval
    - Filtering and search capabilities

    Args:
        http_client: HTTP client instance for making requests

    Example:
        >>> client = HttpClient("MyApp/1.0 (contact@example.com)")
        >>> endpoints = FilingsEndpoints(client)
        >>> submissions = endpoints.get_company_submissions("0000320193")
    """

    DATA_URL = "https://data.sec.gov/"

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
        cik_str = str(cik).zfill(10)
        accession = accession_number.replace("-", "")

        url = urljoin(
            self.DATA_URL,
            f"Archives/edgar/data/{cik_str}/{accession}/{accession_number}-index.json",
        )

        return self.http_client.get(url)
