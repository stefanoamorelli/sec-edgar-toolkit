"""
Statement definitions: canonical names, aliases, and concept lists used
to assemble statement snapshots from company facts.
"""

from __future__ import annotations

from typing import Dict, List

STATEMENT_ALIASES: Dict[str, str] = {
    "balancesheet": "balance_sheet",
    "consolidatedbalancesheets": "balance_sheet",
    "incomestatement": "income_statement",
    "statementsofincome": "income_statement",
    "consolidatedstatementsofoperations": "income_statement",
    "cashflow": "cash_flow",
    "consolidatedstatementsofcashflows": "cash_flow",
}

STATEMENT_CONCEPTS: Dict[str, List[str]] = {
    "balance_sheet": [
        "Assets",
        "AssetsCurrent",
        "AssetsNoncurrent",
        "Liabilities",
        "LiabilitiesCurrent",
        "LiabilitiesNoncurrent",
        "StockholdersEquity",
        "RetainedEarningsAccumulatedDeficit",
    ],
    "income_statement": [
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
    "cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInInvestingActivities",
        "NetCashProvidedByUsedInFinancingActivities",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
}


def normalize_statement_type(statement_type: str) -> str:
    """Map free-form statement names ("BalanceSheet") to canonical keys."""
    normalized = statement_type.strip().lower().replace(" ", "").replace("_", "")
    return STATEMENT_ALIASES.get(
        normalized,
        statement_type if "_" in statement_type else normalized,
    )
