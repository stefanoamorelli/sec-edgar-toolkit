"""Filtering utilities for SEC EDGAR data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class FilingFilter:
    """Utility class for filtering SEC filing data."""

    @staticmethod
    def filter_filings(
        filings: Dict[str, List[Any]],
        form_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, List[Any]]:
        """
        Filter filings based on criteria.

        Args:
            filings: Raw filings data from SEC API
            form_type: Filter by form type (e.g., '10-K', '10-Q')
            from_date: Start date filter (YYYY-MM-DD format)
            to_date: End date filter (YYYY-MM-DD format)

        Returns:
            Filtered filings data

        Example:
            >>> filter = FilingFilter()
            >>> filtered = filter.filter_filings(
            ...     filings, form_type="10-K", from_date="2023-01-01"
            ... )
        """
        if not any([form_type, from_date, to_date]):
            return filings

        # Get the length of the first array to determine number of filings
        if not filings or not filings.get("accessionNumber"):
            return filings

        num_filings = len(filings["accessionNumber"])
        filtered_indices = []

        for i in range(num_filings):
            include = True

            # Filter by form type
            if form_type and filings["form"][i] != form_type:
                include = False

            # Filter by date range
            if include and (from_date or to_date):
                filing_date = filings["filingDate"][i]
                if from_date and filing_date < from_date:
                    include = False
                if to_date and filing_date > to_date:
                    include = False

            if include:
                filtered_indices.append(i)

        # Create filtered result
        result = {}
        for key, values in filings.items():
            if isinstance(values, list) and len(values) == num_filings:
                result[key] = [values[i] for i in filtered_indices]
            else:
                result[key] = values

        return result
