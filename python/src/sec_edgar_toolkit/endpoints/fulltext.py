"""
Full-text search endpoints (EDGAR full-text search, efts.sec.gov).

Searches the text of filings themselves, not just metadata, covering
filings from 2001 onward. Supports exact phrases (quote the query),
form-type filters, date ranges, and company filters.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from ..utils import HttpClient

logger = logging.getLogger(__name__)


class FullTextSearchEndpoints:
    """Client for the EDGAR full-text search API."""

    SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

    def __init__(self, http_client: HttpClient) -> None:
        self.http_client = http_client

    def search(
        self,
        query: str,
        forms: Optional[Union[str, List[str]]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        cik: Optional[Union[str, int]] = None,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search the full text of filings.

        Args:
            query: Search terms. Quote a phrase for exact matching
                (``'"substantial doubt"'``).
            forms: Form type(s) to filter by (e.g., "10-K", ["10-K", "10-Q"])
            start_date: Earliest filing date (YYYY-MM-DD)
            end_date: Latest filing date (YYYY-MM-DD)
            cik: Restrict to one company
            offset: Result offset for paging (10 hits per page)

        Returns:
            ``{"total": int, "hits": [hit, ...]}`` where each hit has
            ``accession_number``, ``cik``, ``company_name``, ``form_type``,
            ``filing_date``, ``file_type``, ``file_description``,
            ``document``, and ``score``.

        Example:
            >>> results = endpoints.search('"going concern"', forms="10-K")
            >>> print(results["total"], "matching filings")
        """
        params: Dict[str, str] = {"q": query}
        if forms:
            form_list = [forms] if isinstance(forms, str) else list(forms)
            params["forms"] = ",".join(form_list)
        if start_date or end_date:
            params["dateRange"] = "custom"
            if start_date:
                params["startdt"] = start_date
            if end_date:
                params["enddt"] = end_date
        if cik is not None:
            params["ciks"] = str(cik).zfill(10)
        if offset:
            params["from"] = str(offset)

        data = self.http_client.get(self.SEARCH_URL, params=params)

        raw_hits = data.get("hits", {})
        total = raw_hits.get("total", {}).get("value", 0)

        hits: List[Dict[str, Any]] = []
        for entry in raw_hits.get("hits", []):
            source = entry.get("_source", {})
            accession, _, document = str(entry.get("_id", "")).partition(":")
            ciks = source.get("ciks") or []
            display_names = source.get("display_names") or []
            hits.append(
                {
                    "accession_number": accession,
                    "document": document,
                    "cik": ciks[0].lstrip("0").zfill(10) if ciks else "",
                    "company_name": display_names[0].split("  (CIK")[0]
                    if display_names
                    else "",
                    "form_type": source.get("form", ""),
                    "root_forms": source.get("root_forms", []),
                    "filing_date": source.get("file_date", ""),
                    "period_ending": source.get("period_ending", ""),
                    "file_type": source.get("file_type", ""),
                    "file_description": source.get("file_description", ""),
                    "score": entry.get("_score"),
                }
            )

        return {"total": total, "hits": hits}
