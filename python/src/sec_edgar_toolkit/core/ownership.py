"""
Attribute-style wrappers for parsed Section 16 ownership forms (3, 4, 5).

``OwnershipFormParser`` returns nested dictionaries; the classes here expose
the same data with the attribute names downstream consumers
rely on: ``owner_name``, ``is_director``, ``transactions[].transaction_code``,
``holdings[].ownership_nature`` and so on.

``OwnershipForm`` subclasses ``dict`` so existing code that treats the result
of ``Filing.obj()`` as the raw ``parse_all()`` dictionary keeps working.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional


def _iso(value: Any) -> Optional[str]:
    """Normalize datetimes/dates to ISO date strings."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


class OwnershipTransaction:
    """A single (non-)derivative transaction with attribute-style access."""

    def __init__(self, data: Dict[str, Any], derivative: bool = False) -> None:
        self.security_title = data.get("security_title")
        self.transaction_date = _iso(data.get("transaction_date"))
        self.transaction_code = data.get("code")
        self.transaction_type = data.get("code")
        self.shares = data.get("shares")
        self.price_per_share = data.get("price_per_share")
        self.acquisition_or_disposition = data.get("acquired_disposed_code")
        self.acquired_disposed = data.get("acquired_disposed_code")
        self.shares_owned_after = data.get("shares_owned_following_transaction")
        self.ownership_type = data.get("direct_or_indirect_ownership")
        self.nature_of_ownership = data.get("nature_of_ownership")
        self.is_derivative = derivative

        total = data.get("total_value")
        if total is None and self.shares is not None and self.price_per_share:
            try:
                total = float(self.shares) * float(self.price_per_share)
            except (TypeError, ValueError):
                total = None
        self.total_value = total
        self.transaction_amount = total

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class OwnershipHolding:
    """A reported holding with attribute-style access."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.security_title = data.get("security_title")
        self.shares_owned = data.get("shares_owned")
        self.ownership_type = data.get("direct_or_indirect_ownership")
        self.ownership_nature = data.get("nature_of_ownership") or data.get(
            "direct_or_indirect_ownership"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class OwnershipForm(dict):
    """
    Parsed Form 3/4/5 exposing both the raw ``parse_all()`` dictionary
    (dict access) and attribute-style access.
    """

    def __init__(self, parsed: Dict[str, Any]) -> None:
        super().__init__(parsed)

        owner = parsed.get("reporting_owner_info") or {}
        relationship = owner.get("relationship") or {}

        self.owner_name: str = owner.get("name") or ""
        self.owner_title: str = relationship.get("officer_title") or ""
        self.is_director: bool = bool(relationship.get("is_director"))
        self.is_officer: bool = bool(relationship.get("is_officer"))
        self.is_ten_percent_owner: bool = bool(relationship.get("is_ten_percent_owner"))
        self.is_other: bool = bool(relationship.get("is_other"))

        document = parsed.get("document_info") or {}
        self.form_type: str = document.get("form_type") or ""
        self.period_of_report = _iso(document.get("period_of_report"))

        issuer = parsed.get("issuer_info") or {}
        self.issuer_name: str = issuer.get("name") or ""
        self.issuer_cik: str = issuer.get("cik") or ""

        self.transactions: List[OwnershipTransaction] = [
            OwnershipTransaction(tx)
            for tx in parsed.get("non_derivative_transactions") or []
        ] + [
            OwnershipTransaction(tx, derivative=True)
            for tx in parsed.get("derivative_transactions") or []
        ]
        self.holdings: List[OwnershipHolding] = [
            OwnershipHolding(h) for h in parsed.get("non_derivative_holdings") or []
        ]

    def to_dataframe(self):
        """Transactions as a pandas DataFrame (requires pandas)."""
        import pandas as pd

        return pd.DataFrame([tx.to_dict() for tx in self.transactions])
