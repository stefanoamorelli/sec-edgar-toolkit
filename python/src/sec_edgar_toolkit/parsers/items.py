"""
SEC filing item definitions.

Typed item enums (``TenKItem``, ``TenQItem``, ``EightKItem``), the
``FormType`` enum, and the per-form item definition tables used by the
extraction engine in :mod:`.item_extractor`.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class FormType(Enum):
    """Supported SEC form types for item extraction."""

    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_20F = "20-F"
    FORM_40F = "40-F"


class TenKItem(str, Enum):
    """10-K items by name; each value is the SEC item number."""

    BUSINESS = "1"
    RISK_FACTORS = "1A"
    UNRESOLVED_STAFF_COMMENTS = "1B"
    CYBERSECURITY = "1C"
    PROPERTIES = "2"
    LEGAL_PROCEEDINGS = "3"
    MINE_SAFETY_DISCLOSURES = "4"
    MARKET_FOR_COMMON_EQUITY = "5"
    RESERVED = "6"
    MANAGEMENT_DISCUSSION_AND_ANALYSIS = "7"
    MARKET_RISK_DISCLOSURES = "7A"
    FINANCIAL_STATEMENTS = "8"
    ACCOUNTANT_CHANGES_AND_DISAGREEMENTS = "9"
    CONTROLS_AND_PROCEDURES = "9A"
    OTHER_INFORMATION = "9B"
    FOREIGN_JURISDICTION_DISCLOSURES = "9C"
    DIRECTORS_AND_GOVERNANCE = "10"
    EXECUTIVE_COMPENSATION = "11"
    SECURITY_OWNERSHIP = "12"
    RELATED_TRANSACTIONS = "13"
    ACCOUNTANT_FEES = "14"
    EXHIBITS = "15"

    def __str__(self) -> str:
        return self.value


class TenQItem(str, Enum):
    """10-Q items by name; Part II items carry the ``II-`` prefix."""

    FINANCIAL_STATEMENTS = "1"
    MANAGEMENT_DISCUSSION_AND_ANALYSIS = "2"
    MARKET_RISK_DISCLOSURES = "3"
    CONTROLS_AND_PROCEDURES = "4"
    LEGAL_PROCEEDINGS = "II-1"
    RISK_FACTORS = "II-1A"
    UNREGISTERED_SALES = "II-2"
    DEFAULTS_UPON_SENIOR_SECURITIES = "II-3"
    MINE_SAFETY_DISCLOSURES = "II-4"
    OTHER_INFORMATION = "II-5"
    EXHIBITS = "II-6"

    def __str__(self) -> str:
        return self.value


class EightKItem(str, Enum):
    """8-K items by name; each value is the SEC item number."""

    MATERIAL_AGREEMENT = "1.01"
    MATERIAL_AGREEMENT_TERMINATION = "1.02"
    ACQUISITION_OR_DISPOSITION = "2.01"
    RESULTS_OF_OPERATIONS = "2.02"
    DIRECT_FINANCIAL_OBLIGATION = "2.03"
    DELISTING_NOTICE = "3.01"
    UNREGISTERED_SALES = "3.02"
    ACCOUNTANT_CHANGES = "4.01"
    NON_RELIANCE_ON_FINANCIALS = "4.02"
    CONTROL_CHANGES = "5.01"
    OFFICER_AND_DIRECTOR_CHANGES = "5.02"
    BYLAW_AMENDMENTS = "5.03"
    REGULATION_FD_DISCLOSURE = "7.01"
    OTHER_EVENTS = "8.01"
    FINANCIAL_STATEMENTS_AND_EXHIBITS = "9.01"

    def __str__(self) -> str:
        return self.value


@dataclass
class ItemDefinition:
    """Definition of an SEC filing item."""

    number: str
    title: str
    aliases: List[str] = field(default_factory=list)
    required: bool = True
    # Result-dict key when the plain item number is ambiguous within a form
    # (10-Q Part I and Part II reuse the same item numbers).
    key: str = ""

    def result_key(self) -> str:
        return self.key or self.number


@dataclass
class ExtractedItem:
    """Represents an extracted item from a filing."""

    item_number: str
    title: str
    content: str
    start_position: int
    end_position: int


# 10-K Item definitions
FORM_10K_ITEMS = [
    ItemDefinition("1", "Business"),
    ItemDefinition("1A", "Risk Factors"),
    ItemDefinition("1B", "Unresolved Staff Comments"),
    ItemDefinition("1C", "Cybersecurity", required=False),  # Added in 2023
    ItemDefinition("2", "Properties"),
    ItemDefinition("3", "Legal Proceedings"),
    ItemDefinition("4", "Mine Safety Disclosures", required=False),
    ItemDefinition("5", "Market for Registrant's Common Equity"),
    ItemDefinition("6", "Reserved", required=False),
    ItemDefinition("7", "Management's Discussion and Analysis", aliases=["MD&A"]),
    ItemDefinition("7A", "Quantitative and Qualitative Disclosures About Market Risk"),
    ItemDefinition("8", "Financial Statements and Supplementary Data"),
    ItemDefinition("9", "Changes in and Disagreements with Accountants"),
    ItemDefinition("9A", "Controls and Procedures"),
    ItemDefinition("9B", "Other Information"),
    ItemDefinition("9C", "Disclosure Regarding Foreign Jurisdictions", required=False),
    ItemDefinition("10", "Directors, Executive Officers and Corporate Governance"),
    ItemDefinition("11", "Executive Compensation"),
    ItemDefinition("12", "Security Ownership"),
    ItemDefinition("13", "Certain Relationships and Related Transactions"),
    ItemDefinition("14", "Principal Accountant Fees and Services"),
    ItemDefinition("15", "Exhibits and Financial Statement Schedules"),
]

# 10-Q Item definitions. Part I and Part II reuse the same item numbers,
# so Part II entries carry a distinct result key ("II-<n>").
FORM_10Q_ITEMS = [
    ItemDefinition("1", "Financial Statements"),
    ItemDefinition("2", "Management's Discussion and Analysis", aliases=["MD&A"]),
    ItemDefinition("3", "Quantitative and Qualitative Disclosures About Market Risk"),
    ItemDefinition("4", "Controls and Procedures"),
    ItemDefinition("1", "Legal Proceedings", aliases=["Part II, Item 1"], key="II-1"),
    ItemDefinition("1A", "Risk Factors", aliases=["Part II, Item 1A"], key="II-1A"),
    ItemDefinition(
        "2",
        "Unregistered Sales of Equity Securities",
        aliases=["Part II, Item 2"],
        key="II-2",
    ),
    ItemDefinition(
        "3",
        "Defaults Upon Senior Securities",
        aliases=["Part II, Item 3"],
        key="II-3",
    ),
    ItemDefinition(
        "4",
        "Mine Safety Disclosures",
        aliases=["Part II, Item 4"],
        required=False,
        key="II-4",
    ),
    ItemDefinition("5", "Other Information", aliases=["Part II, Item 5"], key="II-5"),
    ItemDefinition("6", "Exhibits", aliases=["Part II, Item 6"], key="II-6"),
]

# 8-K Item definitions (most common items)
FORM_8K_ITEMS = [
    ItemDefinition("1.01", "Entry into a Material Definitive Agreement"),
    ItemDefinition("1.02", "Termination of a Material Definitive Agreement"),
    ItemDefinition("2.01", "Completion of Acquisition or Disposition of Assets"),
    ItemDefinition("2.02", "Results of Operations and Financial Condition"),
    ItemDefinition("2.03", "Creation of a Direct Financial Obligation"),
    ItemDefinition("3.01", "Notice of Delisting or Failure to Satisfy"),
    ItemDefinition("3.02", "Unregistered Sales of Equity Securities"),
    ItemDefinition("4.01", "Changes in Registrant's Certifying Accountant"),
    ItemDefinition("4.02", "Non-Reliance on Previously Issued Financial Statements"),
    ItemDefinition("5.01", "Changes in Control of Registrant"),
    ItemDefinition("5.02", "Departure of Directors or Certain Officers"),
    ItemDefinition("5.03", "Amendments to Articles of Incorporation or Bylaws"),
    ItemDefinition("7.01", "Regulation FD Disclosure"),
    ItemDefinition("8.01", "Other Events"),
    ItemDefinition("9.01", "Financial Statements and Exhibits"),
]


FORM_ITEM_DEFINITIONS = {
    FormType.FORM_10K: FORM_10K_ITEMS,
    FormType.FORM_10Q: FORM_10Q_ITEMS,
    FormType.FORM_8K: FORM_8K_ITEMS,
}
