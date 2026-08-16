"""
XBRL instance class of the high-level API.

Provides fact queries backed by the company-facts API, plus filing-scoped
financial statements parsed from the filing's rendered reports
(``FilingSummary.xml`` and the ``R<n>.htm`` report files), which include
statement roles, line-item concepts, and dimensional detail such as
segment breakdowns.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from ..client import SecEdgarApi

logger = logging.getLogger(__name__)

_NUMBER_RE = re.compile(r"^[\s$]*\(?\s*-?[\d,]+(?:\.\d+)?\s*\)?[\s%]*$")

_STATEMENT_ALIASES = {
    "balancesheet": "balance_sheet",
    "consolidatedbalancesheets": "balance_sheet",
    "incomestatement": "income_statement",
    "statementsofincome": "income_statement",
    "consolidatedstatementsofoperations": "income_statement",
    "cashflow": "cash_flow",
    "consolidatedstatementsofcashflows": "cash_flow",
}


_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_PERIOD_DATE_RE = re.compile(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})\s*$")


def _normalize_period_label(label: str) -> str:
    """Normalize a report period header ("Sep. 27, 2025") to ISO (2025-09-27)."""
    match = _PERIOD_DATE_RE.search(label)
    if not match:
        return label
    month = _MONTHS.get(match.group(1).lower()[:3])
    if not month:
        return label
    return f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(2)):02d}"


def _parse_report_number(text: str) -> Optional[float]:
    """Parse a rendered report cell like ``$ (1,234.5)`` into a float."""
    if not text:
        return None
    cleaned = text.strip()
    if not _NUMBER_RE.match(cleaned):
        return None
    negative = "(" in cleaned
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


class FactsData(dict):
    """Raw company-facts payload with a concept-history helper."""

    def facts_history(self, concept: str, taxonomy: str = "us-gaap"):
        """
        History of one concept as a pandas DataFrame with columns
        ``value, unit, period_end, period_instant, filed, form``.
        """
        import pandas as pd

        concept_data = (self.get("facts", {}) or {}).get(taxonomy, {}).get(concept)
        if not concept_data:
            return pd.DataFrame()

        rows = []
        for unit, unit_facts in (concept_data.get("units") or {}).items():
            for fact in unit_facts:
                start = fact.get("start")
                end = fact.get("end")
                rows.append(
                    {
                        "concept": concept,
                        "value": fact.get("val"),
                        "unit": unit,
                        "period_end": end if start else None,
                        "period_instant": None if start else end,
                        "end": end,
                        "filed": fact.get("filed"),
                        "form": fact.get("form"),
                    }
                )
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=["end", "filed"], na_position="first").reset_index(
                drop=True
            )
        return df


class FactQuery(list):
    """Query result: a list of fact records with chainable helpers."""

    def by_concept(self, concept: str) -> "FactQuery":
        """Narrow the results to a single concept name."""
        needle = concept.lower()
        return FactQuery(
            record
            for record in self
            if needle in str(record.get("concept", "")).lower()
        )

    def to_dataframe(self):
        """Results as a pandas DataFrame."""
        import pandas as pd

        return pd.DataFrame(list(self))


class XBRLInstance:
    """
    XBRL data for one filing.

    Fact-level queries are served from the company-facts API; statement
    structure (roles, line items, segment detail) is parsed from the
    filing's rendered reports.

    Attributes:
        filing: Associated Filing object
        cik: Company's Central Index Key
        facts: Raw company-facts payload (with ``facts_history()`` helper)
    """

    def __init__(
        self,
        filing: Filing,
        api: Optional[SecEdgarApi] = None,
    ) -> None:
        if api is None:
            from .global_functions import _get_api

            api = _get_api()

        self._api = api
        self.filing = filing
        self.cik = filing.cik

        self._facts: Optional[FactsData] = None
        self._us_gaap_facts: Optional[Dict[str, Any]] = None
        self._dei_facts: Optional[Dict[str, Any]] = None
        self._reports: Optional[List[Dict[str, Any]]] = None
        self._statement_cache: Dict[str, List[Dict[str, Any]]] = {}

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
                parsed: Dict[str, str] = {}
                for part in concept.split("&"):
                    if "=" in part:
                        key, _, value = part.partition("=")
                        parsed[key.strip()] = value.strip()
                concept = parsed.get("concept")
                taxonomy = parsed.get("taxonomy", taxonomy)
                unit = unit or parsed.get("unit")
                period = period or parsed.get("period")

        results: List[Dict[str, Any]] = []

        if taxonomy == "us-gaap":
            taxonomy_facts = self.us_gaap
        elif taxonomy == "dei":
            taxonomy_facts = self.dei
        else:
            taxonomy_facts = self.facts.get("facts", {}).get(taxonomy, {})

        if concept:
            if concept in taxonomy_facts:
                results.extend(
                    self._process_concept_data(
                        concept, taxonomy_facts[concept], taxonomy, unit, period
                    )
                )
        else:
            for concept_name, concept_data in taxonomy_facts.items():
                results.extend(
                    self._process_concept_data(
                        concept_name, concept_data, taxonomy, unit, period
                    )
                )

        return FactQuery(results)

    def _process_concept_data(
        self,
        concept_name: str,
        concept_data: Dict[str, Any],
        taxonomy: str,
        unit_filter: Optional[str],
        period_filter: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Process concept data and apply filters."""
        results = []

        units = concept_data.get("units", {})
        for unit, unit_data in units.items():
            if unit_filter and unit != unit_filter:
                continue

            for fact in unit_data:
                if period_filter:
                    fact_period = (
                        fact.get("fy") or fact.get("fp") or fact.get("frame", "")
                    )
                    if period_filter not in str(fact_period):
                        continue

                start = fact.get("start")
                end = fact.get("end")
                fact_record = {
                    "concept": concept_name,
                    "taxonomy": taxonomy,
                    "value": fact.get("val"),
                    "unit": unit,
                    "period": fact.get("frame")
                    or f"FY{fact.get('fy', '')}{fact.get('fp', '')}",
                    "fiscal_year": fact.get("fy"),
                    "fiscal_period": fact.get("fp"),
                    "start_date": start,
                    "end_date": end,
                    "period_end": end if start else None,
                    "period_instant": None if start else end,
                    "context": fact.get("accn"),
                    "filed": fact.get("filed"),
                    "accession_number": fact.get("accn"),
                    "form": fact.get("form"),
                }
                results.append(fact_record)

        return results

    # ------------------------------------------------------------------
    # Filing-scoped statements (rendered reports)
    # ------------------------------------------------------------------

    def _get_reports(self) -> List[Dict[str, Any]]:
        """Parse FilingSummary.xml into a list of report descriptors."""
        if self._reports is not None:
            return self._reports

        import xml.etree.ElementTree as ET

        url = f"{self.filing._archive_base}/FilingSummary.xml"
        try:
            raw = self._api.http_client.get_raw(url)
        except Exception as e:
            logger.warning(
                f"No FilingSummary.xml for {self.filing.accession_number}: {e}"
            )
            self._reports = []
            return self._reports

        reports: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(raw)
            for report in root.iter("Report"):
                descriptor = {
                    "definition": (report.findtext("LongName") or "").strip(),
                    "short_name": (report.findtext("ShortName") or "").strip(),
                    "role": (report.findtext("Role") or "").strip(),
                    "r_file": (report.findtext("HtmlFileName") or "").strip(),
                    "report_type": (report.findtext("ReportType") or "").strip(),
                }
                if descriptor["role"] or descriptor["r_file"]:
                    reports.append(descriptor)
        except ET.ParseError as e:
            logger.warning(f"Could not parse FilingSummary.xml: {e}")

        self._reports = reports
        return reports

    def get_all_statements(self) -> List[Dict[str, Any]]:
        """
        List all rendered reports in the filing.

        Returns:
            List of dicts with ``definition``, ``short_name``, ``role``,
            and ``r_file`` keys.
        """
        return self._get_reports()

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
        report = self._find_report(role)
        if not report or not report.get("r_file"):
            return []

        cache_key = report["r_file"]
        if cache_key in self._statement_cache:
            return self._statement_cache[cache_key]

        url = f"{self.filing._archive_base}/{report['r_file']}"
        try:
            raw = self._api.http_client.get_raw(url)
        except Exception as e:
            logger.warning(f"Could not fetch report {url}: {e}")
            return []

        items = self._parse_report_html(raw)
        self._statement_cache[cache_key] = items
        return items

    def _find_report(self, role: str) -> Optional[Dict[str, Any]]:
        for report in self._get_reports():
            if role in (report["role"], report["r_file"], report["short_name"]):
                return report
        # Loose match on the role suffix
        role_lower = role.lower()
        for report in self._get_reports():
            if report["role"].lower().endswith(role_lower):
                return report
        return None

    def _parse_report_html(self, raw: bytes) -> List[Dict[str, Any]]:
        """Parse an R<n>.htm rendered report table into line items."""
        try:
            from lxml import html as lxml_html
        except ImportError:
            logger.warning("lxml is required to parse rendered reports")
            return []

        try:
            tree = lxml_html.fromstring(raw)
        except Exception as e:
            logger.warning(f"Could not parse report HTML: {e}")
            return []

        tables = tree.xpath("//table[contains(@class, 'report')]") or tree.xpath(
            "//table"
        )
        if not tables:
            return []
        table = tables[0]

        # Unit multiplier from the report title cell (e.g. "$ in Millions")
        multiplier = 1.0
        header_text = " ".join(table.xpath(".//th//text()"))
        if re.search(r"in\s+Millions", header_text, re.IGNORECASE):
            multiplier = 1e6
        elif re.search(r"in\s+Thousands", header_text, re.IGNORECASE):
            multiplier = 1e3
        elif re.search(r"in\s+Billions", header_text, re.IGNORECASE):
            multiplier = 1e9
        shares_multiplier = multiplier
        if re.search(r"shares\s+in\s+Millions", header_text, re.IGNORECASE):
            shares_multiplier = 1e6
        elif re.search(r"shares\s+in\s+Thousands", header_text, re.IGNORECASE):
            shares_multiplier = 1e3

        # Period labels: last header row's th cells (skipping the label column)
        header_rows = [row for row in table.xpath(".//tr") if row.xpath("./th")]
        periods: List[str] = []
        if header_rows:
            last_header = header_rows[-1]
            cells = last_header.xpath("./th")
            texts = [" ".join(c.itertext()).strip() for c in cells]
            # Drop the leading label-column header when present
            if texts and not re.search(r"\d{4}", texts[0]):
                texts = texts[1:]
            periods = [_normalize_period_label(t) for t in texts if t]

        items: List[Dict[str, Any]] = []
        # Dimensional reports group measure rows under axis-member rows
        # ("Americas | Operating segments"); carry that grouping onto the
        # measure rows so labels stay meaningful on their own.
        current_section = ""
        for row in table.xpath(".//tr"):
            label_cells = row.xpath("./td[contains(@class, 'pl')]")
            if not label_cells:
                continue
            label_cell = label_cells[0]
            label = " ".join(label_cell.itertext()).strip()
            label = re.sub(r"\s+", " ", label)

            concept = ""
            onclick_nodes = label_cell.xpath(".//a/@onclick")
            if onclick_nodes:
                match = re.search(r"defref_([A-Za-z0-9_-]+)", onclick_nodes[0])
                if match:
                    concept = match.group(1).replace("_", ":", 1)

            values: Dict[str, float] = {}
            units: Dict[str, str] = {}
            value_cells = row.xpath(
                "./td[contains(@class, 'nump') or contains(@class, 'num')"
                " or contains(@class, 'text')]"
            )
            column = 0
            for cell in value_cells:
                cell_class = cell.get("class", "")
                if "num" not in cell_class:
                    column += 1
                    continue
                text = " ".join(cell.itertext()).strip()
                # Strip footnote markers like [1]
                text = re.sub(r"\[\d+\]", "", text).strip()
                number = _parse_report_number(text)
                if number is not None and column < max(len(periods), column + 1):
                    period = (
                        periods[column] if column < len(periods) else f"col_{column}"
                    )
                    is_shares = "shares" in label.lower() or (
                        concept and "shares" in concept.lower()
                    )
                    is_per_share = "per share" in label.lower() or (
                        concept and "pershare" in concept.lower().replace("-", "")
                    )
                    if is_per_share:
                        scale = 1.0
                    elif is_shares:
                        scale = shares_multiplier
                    else:
                        scale = multiplier
                    values[period] = number * scale
                    units[period] = (
                        "shares"
                        if is_shares
                        else "USD/shares"
                        if is_per_share
                        else "USD"
                    )
                column += 1

            if not values and concept.endswith("Axis"):
                current_section = label

            section = current_section if values else ""
            items.append(
                {
                    "concept": concept,
                    "label": f"{section} | {label}" if section else label,
                    "base_label": label,
                    "section": section,
                    "values": values,
                    "units": units,
                    "has_values": bool(values),
                }
            )

        return items

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
        normalized = statement_type.strip().lower().replace(" ", "").replace("_", "")
        statement_type = _STATEMENT_ALIASES.get(
            normalized,
            statement_type if "_" in statement_type else normalized,
        )

        if statement_type == "balance_sheet":
            return self._extract_statement_from_facts(
                "balance_sheet",
                [
                    "Assets",
                    "AssetsCurrent",
                    "AssetsNoncurrent",
                    "Liabilities",
                    "LiabilitiesCurrent",
                    "LiabilitiesNoncurrent",
                    "StockholdersEquity",
                    "RetainedEarningsAccumulatedDeficit",
                ],
                period,
            )
        elif statement_type == "income_statement":
            return self._extract_statement_from_facts(
                "income_statement",
                [
                    "Revenues",
                    "RevenueFromContractWithCustomerExcludingAssessedTax",
                    "CostOfRevenue",
                    "GrossProfit",
                    "OperatingIncomeLoss",
                    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                    "NetIncomeLoss",
                    "EarningsPerShareBasic",
                    "EarningsPerShareDiluted",
                ],
                period,
            )
        elif statement_type == "cash_flow":
            return self._extract_statement_from_facts(
                "cash_flow",
                [
                    "NetCashProvidedByUsedInOperatingActivities",
                    "NetCashProvidedByUsedInInvestingActivities",
                    "NetCashProvidedByUsedInFinancingActivities",
                    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                ],
                period,
            )
        else:
            logger.warning(f"Unknown statement type: {statement_type}")
            return None

    def _extract_statement_from_facts(
        self, statement_type: str, concepts: List[str], period: Optional[str]
    ) -> Dict[str, Any]:
        """Build a statement snapshot from company facts."""
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
    ) -> pd.DataFrame:
        """Convert XBRL facts to a pandas DataFrame."""
        if not PANDAS_AVAILABLE:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install pandas"
            )

        facts = self.query(concept=concept, taxonomy=taxonomy, unit=unit)
        return pd.DataFrame(list(facts))

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
        return f"XBRLInstance(cik='{self.cik}', form='{self.filing.form_type}', date='{self.filing.filing_date}')"


# Import at the end to avoid circular imports
from .filing import Filing
