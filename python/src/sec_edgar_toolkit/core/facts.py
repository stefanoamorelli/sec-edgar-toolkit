"""
Company facts wrapper exposing the high-level facts API.

Wraps the raw ``data.sec.gov/api/xbrl/companyfacts`` JSON with:
- ``.data`` — the ``facts`` mapping (``{"us-gaap": {...}, "dei": {...}}``)
- ``.get_fact(concept)`` — history for one concept as a pandas DataFrame
  with columns ``fy, fp, value, unit, form, end, filed``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class CompanyFacts:
    """XBRL company facts with convenient accessors."""

    def __init__(self, raw: Dict[str, Any]) -> None:
        self._raw = raw or {}
        # The raw payload nests taxonomies under "facts"; ``.data`` exposes
        # that mapping directly (``data["us-gaap"][concept]["units"]``).
        self.data: Dict[str, Any] = self._raw.get("facts", {}) or {}
        self.cik = self._raw.get("cik")
        self.entity_name = self._raw.get("entityName")

    def __bool__(self) -> bool:
        return bool(self.data)

    def _find_concept(self, concept: str) -> Optional[Dict[str, Any]]:
        for taxonomy in ("us-gaap", "dei", "ifrs-full", "srt"):
            taxonomy_facts = self.data.get(taxonomy) or {}
            if concept in taxonomy_facts:
                return taxonomy_facts[concept]
        # Fall back to any remaining taxonomy
        for taxonomy_facts in self.data.values():
            if isinstance(taxonomy_facts, dict) and concept in taxonomy_facts:
                return taxonomy_facts[concept]
        return None

    def get_fact(self, concept: str):
        """
        Return the reported history of ``concept`` as a pandas DataFrame
        (columns: fy, fp, value, unit, form, end, filed, start, accn),
        sorted by period end ascending. Returns None when the concept is
        not reported.
        """
        from ..utils.optional_deps import require_pandas

        pd = require_pandas()

        concept_data = self._find_concept(concept)
        if not concept_data:
            return None

        rows: List[Dict[str, Any]] = []
        for unit, unit_facts in (concept_data.get("units") or {}).items():
            for fact in unit_facts:
                rows.append(
                    {
                        "fy": fact.get("fy"),
                        "fp": fact.get("fp"),
                        "value": fact.get("val"),
                        "unit": unit,
                        "form": fact.get("form"),
                        "end": fact.get("end"),
                        "start": fact.get("start"),
                        "filed": fact.get("filed"),
                        "accn": fact.get("accn"),
                    }
                )

        if not rows:
            return None

        df = pd.DataFrame(rows)
        return df.sort_values(by=["end", "filed"], na_position="first").reset_index(
            drop=True
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style access to the raw companyfacts payload."""
        return self._raw.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._raw[key]

    def __contains__(self, key: str) -> bool:
        return key in self._raw
