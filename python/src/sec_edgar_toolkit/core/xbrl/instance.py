"""
XBRL instance of the high-level API.

``XBRLInstance`` composes two data sources for one filing:

- fact-level queries served from the company-facts API
  (:mod:`.queries`), and
- filing-scoped statement structure parsed from the filing's rendered
  reports (:mod:`.rendered_reports`).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ...client import SecEdgarApi
from .queries import FactQuery, FactsData, build_fact_records, parse_filter_expression
from .rendered_reports import RenderedReportReader
from .statements import STATEMENT_CONCEPTS, normalize_statement_type

if TYPE_CHECKING:
    from ..filing import Filing

logger = logging.getLogger(__name__)


class XBRLInstance:
    """
    XBRL data for one filing.

    Attributes:
        filing: Associated Filing object
        cik: Company's Central Index Key
        facts: Raw company-facts payload (with ``facts_history()`` helper)
    """

    def __init__(
        self,
        filing: "Filing",
        api: Optional[SecEdgarApi] = None,
    ) -> None:
        if api is None:
            from ..global_functions import _get_api

            api = _get_api()

        self._api = api
        self.filing = filing
        self.cik = filing.cik

        self._facts: Optional[FactsData] = None
        self._us_gaap_facts: Optional[Dict[str, Any]] = None
        self._dei_facts: Optional[Dict[str, Any]] = None
        self._reports_reader: Optional[RenderedReportReader] = None

    @property
    def facts(self) -> FactsData:
        """All XBRL facts for the company."""
        if self._facts is None:
            self._facts = FactsData(self._api.get_company_facts(self.cik))
        return self._facts

    @property
    def us_gaap(self) -> Dict[str, Any]:
        """Get US-GAAP facts."""
        if self._us_gaap_facts is None:
            self._us_gaap_facts = self.facts.get("facts", {}).get("us-gaap", {})
        return self._us_gaap_facts

    @property
    def dei(self) -> Dict[str, Any]:
        """Get DEI (Document Entity Information) facts."""
        if self._dei_facts is None:
            self._dei_facts = self.facts.get("facts", {}).get("dei", {})
        return self._dei_facts

    @property
    def reports(self) -> RenderedReportReader:
        """Reader for the filing's rendered reports."""
        if self._reports_reader is None:
            self._reports_reader = RenderedReportReader(
                self.filing._archive_base, self._api.http_client
            )
        return self._reports_reader

    # ------------------------------------------------------------------
    # Fact queries
    # ------------------------------------------------------------------

    def query(
        self,
        concept: Optional[str] = None,
        taxonomy: str = "us-gaap",
        unit: Optional[str] = None,
        period: Optional[str] = None,
        **kwargs: Any,
    ) -> FactQuery:
        """
        Query XBRL facts with filtering.

        The first argument accepts either a concept name ("Assets") or a
        filter expression ("concept=Assets&unit=USD"; the empty string
        selects everything).

        Returns:
            FactQuery (a list of fact records with ``to_dataframe()`` and
            ``by_concept()`` helpers)
        """
        # Filter-expression form: "concept=Assets" / ""
        if isinstance(concept, str):
            if concept == "":
                concept = None
            elif "=" in concept:
                concept, taxonomy, unit, period = parse_filter_expression(
                    concept, taxonomy, unit, period
                )

        if taxonomy == "us-gaap":
            taxonomy_facts = self.us_gaap
        elif taxonomy == "dei":
            taxonomy_facts = self.dei
        else:
            taxonomy_facts = self.facts.get("facts", {}).get(taxonomy, {})

        results: List[Dict[str, Any]] = []
        if concept:
            if concept in taxonomy_facts:
                results.extend(
                    build_fact_records(
                        concept, taxonomy_facts[concept], taxonomy, unit, period
                    )
                )
        else:
            for concept_name, concept_data in taxonomy_facts.items():
                results.extend(
                    build_fact_records(
                        concept_name, concept_data, taxonomy, unit, period
                    )
                )

        return FactQuery(results)

    # ------------------------------------------------------------------
    # Filing-scoped statements (rendered reports)
    # ------------------------------------------------------------------

    def get_all_statements(self) -> List[Dict[str, Any]]:
        """
        List all rendered reports in the filing.

        Returns:
            List of dicts with ``definition``, ``short_name``, ``role``,
            and ``r_file`` keys.
        """
        return self.reports.list_reports()

    def get_statement(self, role: str) -> List[Dict[str, Any]]:
        """
        Parse one rendered report into line items.

        Args:
            role: The report's role URI (from ``get_all_statements()``),
                its R-file name, or its short name.

        Returns:
            List of line-item dicts with ``concept``, ``label``,
            ``values`` (period -> number), ``units`` (period -> unit),
            and ``has_values`` keys.
        """
        return self.reports.read_statement(role)

    def find_statement(
        self,
        statement_type: str = "balance_sheet",
        period: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find and extract a specific financial statement.

        Args:
            statement_type: "balance_sheet", "income_statement", or
                "cash_flow" (common CamelCase spellings are accepted too)
            period: Period filter (e.g., "2023", "CY2023Q4")

        Returns:
            Dictionary containing the financial statement data
        """
        statement_type = normalize_statement_type(statement_type)
        concepts = STATEMENT_CONCEPTS.get(statement_type)
        if concepts is None:
            logger.warning(f"Unknown statement type: {statement_type}")
            return None

        statement_data = {}
        for concept in concepts:
            facts = self.query(concept=concept, unit="USD", period=period)
            if not facts:
                facts = self.query(concept=concept, period=period)
            if facts:
                latest_fact = max(facts, key=lambda x: x.get("filed", "") or "")
                statement_data[concept] = latest_fact

        return {
            "statement_type": statement_type,
            "period": period,
            "data": statement_data,
        }

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def to_dataframe(
        self,
        concept: Optional[str] = None,
        taxonomy: str = "us-gaap",
        unit: Optional[str] = None,
    ):
        """Convert XBRL facts to a pandas DataFrame."""
        return self.query(concept=concept, taxonomy=taxonomy, unit=unit).to_dataframe()

    def to_dict(
        self,
        concept: Optional[str] = None,
        taxonomy: str = "us-gaap",
        unit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert XBRL facts to dictionary format."""
        facts = self.query(concept=concept, taxonomy=taxonomy, unit=unit)
        return {
            "metadata": {
                "cik": self.cik,
                "filing_date": str(self.filing.filing_date),
                "form_type": self.filing.form_type,
            },
            "facts": list(facts),
        }

    def get_concept_value(
        self,
        concept: str,
        taxonomy: str = "us-gaap",
        unit: str = "USD",
        period: Optional[str] = None,
    ) -> Optional[float]:
        """Get the most recent value for a specific concept."""
        facts = self.query(concept=concept, taxonomy=taxonomy, unit=unit, period=period)
        if facts:
            latest_fact = max(facts, key=lambda x: x.get("filed", "") or "")
            return latest_fact.get("value")
        return None

    def list_concepts(self, taxonomy: str = "us-gaap") -> List[str]:
        """List all available concepts in a taxonomy."""
        if taxonomy == "us-gaap":
            return list(self.us_gaap.keys())
        elif taxonomy == "dei":
            return list(self.dei.keys())
        else:
            facts = self.facts.get("facts", {})
            return list(facts.get(taxonomy, {}).keys())

    def __str__(self) -> str:
        """String representation of the XBRL instance."""
        return f"XBRL instance for {self.filing.form_type} filing (CIK: {self.cik})"

    def __repr__(self) -> str:
        """Detailed string representation of the XBRL instance."""
        return (
            f"XBRLInstance(cik='{self.cik}', form='{self.filing.form_type}', "
            f"date='{self.filing.filing_date}')"
        )
