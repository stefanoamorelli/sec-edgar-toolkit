"""
Fact-level query primitives over the company-facts payload.

- ``FactsData`` — the raw company-facts payload with a history helper
- ``FactQuery`` — a list of fact records with chainable helpers
- ``build_fact_records`` — normalize one concept's raw facts into records
- ``parse_filter_expression`` — parse "concept=Assets&unit=USD" strings
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


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


def parse_filter_expression(
    expression: str, taxonomy: str, unit: Optional[str], period: Optional[str]
) -> Tuple[Optional[str], str, Optional[str], Optional[str]]:
    """
    Parse a "key=value&key=value" filter expression.

    Returns the (concept, taxonomy, unit, period) tuple with explicit
    keyword arguments taking precedence over the expression.
    """
    parsed: Dict[str, str] = {}
    for part in expression.split("&"):
        if "=" in part:
            key, _, value = part.partition("=")
            parsed[key.strip()] = value.strip()
    return (
        parsed.get("concept"),
        parsed.get("taxonomy", taxonomy),
        unit or parsed.get("unit"),
        period or parsed.get("period"),
    )


def build_fact_records(
    concept_name: str,
    concept_data: Dict[str, Any],
    taxonomy: str,
    unit_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Normalize one concept's raw company-facts entries into fact records."""
    results: List[Dict[str, Any]] = []

    units = concept_data.get("units", {})
    for unit, unit_data in units.items():
        if unit_filter and unit != unit_filter:
            continue

        for fact in unit_data:
            if period_filter:
                fact_period = fact.get("fy") or fact.get("fp") or fact.get("frame", "")
                if period_filter not in str(fact_period):
                    continue

            start = fact.get("start")
            end = fact.get("end")
            results.append(
                {
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
            )

    return results
