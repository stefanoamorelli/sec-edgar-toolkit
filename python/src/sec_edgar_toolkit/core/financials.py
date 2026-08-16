"""
Financial statements built from XBRL company facts.

``Financials.extract(filing)`` builds statement views for one filing;
``income_statement()`` / ``balance_sheet()`` / ``cash_flow()`` return
pandas DataFrames (rows = concepts, columns = period end dates).

The data source is the company-facts API filtered to the filing's form
type, which yields as-reported values for the periods the filing covers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

INCOME_STATEMENT_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "GrossProfit",
    "ResearchAndDevelopmentExpense",
    "SellingGeneralAndAdministrativeExpense",
    "OperatingExpenses",
    "OperatingIncomeLoss",
    "NonoperatingIncomeExpense",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeTaxExpenseBenefit",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
]

BALANCE_SHEET_CONCEPTS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "MarketableSecuritiesCurrent",
    "AccountsReceivableNetCurrent",
    "InventoryNet",
    "AssetsCurrent",
    "PropertyPlantAndEquipmentNet",
    "Goodwill",
    "MarketableSecuritiesNoncurrent",
    "AssetsNoncurrent",
    "Assets",
    "AccountsPayableCurrent",
    "LiabilitiesCurrent",
    "LongTermDebtNoncurrent",
    "LiabilitiesNoncurrent",
    "Liabilities",
    "CommonStocksIncludingAdditionalPaidInCapital",
    "RetainedEarningsAccumulatedDeficit",
    "StockholdersEquity",
]

# IFRS equivalents let annual reports from foreign private issuers
# (20-F, 40-F) build statements from the ifrs-full taxonomy.
IFRS_INCOME_STATEMENT_CONCEPTS = [
    "Revenue",
    "CostOfSales",
    "GrossProfit",
    "ProfitLossFromOperatingActivities",
    "ProfitLossBeforeTax",
    "IncomeTaxExpenseContinuingOperations",
    "ProfitLoss",
    "BasicEarningsLossPerShare",
    "DilutedEarningsLossPerShare",
]

IFRS_BALANCE_SHEET_CONCEPTS = [
    "CurrentAssets",
    "NoncurrentAssets",
    "Assets",
    "CurrentLiabilities",
    "NoncurrentLiabilities",
    "Liabilities",
    "Equity",
]

IFRS_CASH_FLOW_CONCEPTS = [
    "CashFlowsFromUsedInOperatingActivities",
    "CashFlowsFromUsedInInvestingActivities",
    "CashFlowsFromUsedInFinancingActivities",
    "CashAndCashEquivalents",
]

ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A")
QUARTERLY_FORMS = ("10-Q", "10-Q/A", "6-K")

CASH_FLOW_CONCEPTS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsOfDividends",
    "PaymentsForRepurchaseOfCommonStock",
    "DepreciationDepletionAndAmortization",
    "ShareBasedCompensation",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]


class Financials:
    """Financial statements for one filing, backed by company facts."""

    def __init__(
        self,
        facts_data: Dict[str, Any],
        form_type: str = "10-K",
        accession_number: Optional[str] = None,
    ) -> None:
        self._facts = (facts_data or {}).get("facts", facts_data or {})
        self.form_type = form_type
        self.accession_number = accession_number

    @classmethod
    def extract(cls, filing) -> "Financials":
        """Build Financials for a Filing (high-level entry point)."""
        raw = filing._api.get_company_facts(filing.cik)
        return cls(
            raw,
            form_type=getattr(filing, "form_type", "10-K"),
            accession_number=getattr(filing, "accession_number", None),
        )

    def _collect(self, concepts: List[str], ifrs_concepts: Optional[List[str]] = None):
        """
        Build a DataFrame: rows = concepts, columns = period end dates
        (most recent first), using facts reported on this form type.
        """
        from ..utils.optional_deps import require_pandas

        pd = require_pandas()

        gaap = self._facts.get("us-gaap") or {}
        ifrs = self._facts.get("ifrs-full") or {}
        annual = self.form_type.upper().startswith(("10-K", "20-F", "40-F"))

        candidates: List[tuple] = [(concept, gaap) for concept in concepts]
        if ifrs:
            candidates += [(concept, ifrs) for concept in ifrs_concepts or []]

        # concept -> {end_date: value}
        table: Dict[str, Dict[str, float]] = {}
        for concept, taxonomy_facts in candidates:
            concept_data = taxonomy_facts.get(concept)
            if not concept_data:
                continue
            for _unit, unit_facts in (concept_data.get("units") or {}).items():
                series: Dict[str, float] = {}
                for fact in unit_facts:
                    form = fact.get("form", "")
                    if annual and form not in ANNUAL_FORMS:
                        continue
                    if not annual and form not in QUARTERLY_FORMS + ANNUAL_FORMS:
                        continue
                    if annual and fact.get("fp") not in (None, "FY"):
                        continue
                    end = fact.get("end")
                    if not end:
                        continue
                    # Prefer the latest-filed value for a period
                    series[end] = fact.get("val")
                if series:
                    table[concept] = series
                    break  # first unit with data wins (USD before shares)

        if not table:
            return pd.DataFrame()

        all_periods = sorted({p for s in table.values() for p in s}, reverse=True)
        periods = all_periods[:4]
        df = pd.DataFrame({p: {c: table[c].get(p) for c in table} for p in periods})
        df = df.dropna(how="all")
        return df

    def income_statement(self):
        return self._collect(INCOME_STATEMENT_CONCEPTS, IFRS_INCOME_STATEMENT_CONCEPTS)

    def balance_sheet(self):
        return self._collect(BALANCE_SHEET_CONCEPTS, IFRS_BALANCE_SHEET_CONCEPTS)

    def cash_flow(self):
        return self._collect(CASH_FLOW_CONCEPTS, IFRS_CASH_FLOW_CONCEPTS)

    # Common aliases
    def cash_flow_statement(self):
        return self.cash_flow()

    def __bool__(self) -> bool:
        return bool(self._facts)
