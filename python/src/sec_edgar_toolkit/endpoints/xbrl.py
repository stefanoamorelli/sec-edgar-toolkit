"""XBRL data endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

from ..utils import HttpClient


class XbrlEndpoints:
    """
    Endpoints for XBRL (eXtensible Business Reporting Language) data.

    This class handles all XBRL-related API endpoints including:
    - Company facts (structured financial data)
    - Company concepts (specific accounting metrics)
    - Frames (market-wide aggregated data)
    - XBRL taxonomies and tags

    Args:
        http_client: HTTP client instance for making requests

    Example:
        >>> client = HttpClient("MyApp/1.0 (contact@example.com)")
        >>> endpoints = XbrlEndpoints(client)
        >>> facts = endpoints.get_company_facts("0000320193")
    """

    BASE_URL = "https://data.sec.gov/api/xbrl/"
    DATA_URL = "https://data.sec.gov/"

    def __init__(self, http_client: HttpClient) -> None:
        """Initialize XBRL endpoints."""
        self.http_client = http_client

    def get_company_facts(self, cik: Union[str, int]) -> Dict[str, Any]:
        """
        Get XBRL facts data for a company.

        This endpoint provides structured financial data extracted
        from company XBRL filings.

        Args:
            cik: Company CIK number

        Returns:
            Dictionary containing company facts organized by taxonomy

        Example:
            >>> facts = endpoints.get_company_facts("0000789019")
            >>> gaap = facts['facts']['us-gaap']
            >>> print(f"Available GAAP items: {len(gaap)}")
        """
        cik_str = str(cik).zfill(10)
        url = urljoin(self.DATA_URL, f"api/xbrl/companyfacts/CIK{cik_str}.json")
        return self.http_client.get(url)

    def get_company_concept(
        self,
        cik: Union[str, int],
        taxonomy: str,
        tag: str,
        unit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get specific XBRL concept data for a company.

        This endpoint returns all historical values for a specific
        accounting concept.

        Args:
            cik: Company CIK number
            taxonomy: Taxonomy name (e.g., 'us-gaap', 'dei')
            tag: XBRL tag name (e.g., 'Assets', 'Revenues')
            unit: Unit of measurement (e.g., 'USD', 'shares')

        Returns:
            Historical data for the specified concept

        Example:
            >>> data = endpoints.get_company_concept("0000320193", "us-gaap", "Assets", "USD")
            >>> for item in data['units']['USD'][-5:]:
            ...     print(f"{item['fy']}: ${item['val']:,.0f}")
        """
        cik_str = str(cik).zfill(10)
        url = urljoin(
            self.BASE_URL, f"companyconcept/CIK{cik_str}/{taxonomy}/{tag}.json"
        )

        data = self.http_client.get(url)

        # Filter by unit if specified
        if (
            unit
            and "units" in data
            and isinstance(data["units"], dict)
            and unit in data["units"]
        ):
            data["units"] = {unit: data["units"][unit]}

        return data

    def get_frames(
        self,
        taxonomy: str,
        tag: str,
        unit: str,
        year: int,
        quarter: Optional[int] = None,
        instantaneous: bool = False,
    ) -> Dict[str, Any]:
        """
        Get aggregated XBRL data for all companies for a specific period.

        This endpoint provides a snapshot of a specific metric across
        all reporting companies for a given period.

        Args:
            taxonomy: Taxonomy name (e.g., 'us-gaap')
            tag: XBRL tag name (e.g., 'Assets')
            unit: Unit of measurement (e.g., 'USD')
            year: Calendar year (e.g., 2023)
            quarter: Quarter number (1-4), or None for annual
            instantaneous: Whether to get instantaneous values

        Returns:
            Aggregated data for all companies

        Example:
            >>> frame = endpoints.get_frames("us-gaap", "Assets", "USD", 2023, 4)
            >>> print(f"Total companies: {len(frame['data'])}")
        """
        if quarter:
            period = f"CY{year}Q{quarter}"
            if instantaneous:
                period += "I"
        else:
            period = f"CY{year}"

        url = urljoin(self.BASE_URL, f"frames/{taxonomy}/{tag}/{unit}/{period}.json")

        return self.http_client.get(url)
