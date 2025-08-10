"""
Global functions providing edgartools-compatible API.

These functions provide the main entry points for working with SEC data,
matching the interface expected by applications using edgartools.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Union

from ..client import SecEdgarApi
from .company import Company
from .filing import Filing

logger = logging.getLogger(__name__)

# Global API client instance
_global_api: Optional[SecEdgarApi] = None


def set_identity(user_agent: str) -> None:
    """
    Set the user agent for SEC API requests.

    This function is equivalent to edgar.set_identity() in edgartools.

    Args:
        user_agent: User agent string with contact information

    Example:
        >>> set_identity("MyCompany/1.0 (contact@example.com)")
    """
    global _global_api
    _global_api = SecEdgarApi(user_agent=user_agent)
    logger.info(f"Set global identity: {user_agent}")


def _get_api() -> SecEdgarApi:
    """Get the global API instance, creating one if needed."""
    global _global_api
    if _global_api is None:
        # Try to get from environment variable
        user_agent = os.getenv("SEC_EDGAR_TOOLKIT_USER_AGENT")
        if not user_agent:
            raise RuntimeError(
                "No user agent set. Call set_identity() first or set SEC_EDGAR_TOOLKIT_USER_AGENT environment variable."
            )
        _global_api = SecEdgarApi(user_agent=user_agent)
    return _global_api


def find_company(identifier: Union[str, int]) -> Optional[Company]:
    """
    Find a company by ticker or CIK.

    This function is equivalent to edgar.find_company() in edgartools.

    Args:
        identifier: Company ticker symbol or CIK number

    Returns:
        Company object if found, None otherwise

    Example:
        >>> company = find_company("AAPL")
        >>> company = find_company("0000320193")
    """
    api = _get_api()

    # Try as ticker first
    if isinstance(identifier, str) and not identifier.isdigit():
        company_data = api.get_company_by_ticker(identifier)
        if company_data:
            return Company(company_data["cik_str"], api=api, _company_data=company_data)

    # Try as CIK
    cik = str(identifier).zfill(10) if str(identifier).isdigit() else None
    if cik:
        company_data = api.get_company_by_cik(cik)
        if company_data:
            return Company(cik, api=api, _company_data=company_data)

    return None


def search(query: str) -> List[Company]:
    """
    Search for companies by name.

    This function is equivalent to edgar.search() in edgartools.

    Args:
        query: Search query (company name)

    Returns:
        List of Company objects matching the query

    Example:
        >>> companies = search("Apple")
        >>> for company in companies:
        ...     print(f"{company.ticker}: {company.name}")
    """
    api = _get_api()
    results = api.search_companies(query)

    return [
        Company(result["cik_str"], api=api, _company_data=result) for result in results
    ]


def get_filings(
    form: Optional[Union[str, List[str]]] = None,
    cik: Optional[Union[str, int]] = None,
    ticker: Optional[str] = None,
    since: Optional[str] = None,
    before: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Filing]:
    """
    Get filings with flexible filtering options.

    This function is equivalent to edgar.get_filings() in edgartools.

    Args:
        form: Form type(s) to filter by (e.g., "10-K", ["10-K", "10-Q"])
        cik: Company CIK to filter by
        ticker: Company ticker to filter by
        since: Start date (YYYY-MM-DD format)
        before: End date (YYYY-MM-DD format)
        limit: Maximum number of filings to return

    Returns:
        List of Filing objects

    Example:
        >>> filings = get_filings(form="10-K", limit=5)
        >>> filings = get_filings(ticker="AAPL", form=["10-K", "10-Q"])
    """
    api = _get_api()

    # Convert ticker to CIK if provided
    target_cik = None
    if ticker:
        company_data = api.get_company_by_ticker(ticker)
        if company_data:
            target_cik = company_data["cik_str"]
        else:
            return []
    elif cik:
        target_cik = str(cik).zfill(10)

    # Convert form to list if string
    form_types = []
    if form:
        if isinstance(form, str):
            form_types = [form]
        else:
            form_types = list(form)

    filings = []

    if target_cik:
        # Get filings for specific company
        submissions = api.get_company_submissions(
            target_cik,
            submission_type=form_types[0] if len(form_types) == 1 else None,
            from_date=since,
            to_date=before,
        )

        recent_filings = submissions.get("filings", {}).get("recent", {})
        if recent_filings:
            # Process recent filings
            accession_numbers = recent_filings.get("accessionNumber", [])
            form_list = recent_filings.get("form", [])
            filing_dates = recent_filings.get("filingDate", [])

            for i, accession in enumerate(accession_numbers):
                if i >= len(form_list) or i >= len(filing_dates):
                    break

                filing_form = form_list[i]
                filing_date = filing_dates[i]

                # Filter by form types if specified
                if form_types and filing_form not in form_types:
                    continue

                filing = Filing(
                    cik=target_cik,
                    accession_number=accession,
                    form_type=filing_form,
                    filing_date=filing_date,
                    api=api,
                )
                filings.append(filing)

                if limit and len(filings) >= limit:
                    break
    else:
        # Global filings search would require significant additional work
        # For now, return empty list if no company specified
        logger.warning(
            "Global filings search without company filter not yet implemented"
        )

    return filings[:limit] if limit else filings
