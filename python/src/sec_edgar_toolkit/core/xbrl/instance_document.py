"""
Parser for XBRL instance documents.

An instance document (``<base>_htm.xml`` on modern filings, ``<base>.xml``
on older ones) carries the filing's own facts: every reported value with
its context (period, entity, dimensions) and unit. Parsing it gives
as-reported data scoped to the filing, including dimensional breakdowns
that the aggregated company-facts API cannot provide.

Standard library only. No I/O happens in this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

XBRLI_NS = "http://www.xbrl.org/2003/instance"
LINK_NS = "http://www.xbrl.org/2003/linkbase"
XBRLDI_NS = "http://xbrl.org/2006/xbrldi"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

_XMLNS_RE = re.compile(r'xmlns:([\w.-]+)="([^"]+)"')


@dataclass
class Context:
    """One xbrli:context: entity, period, and dimensional qualifiers."""

    id: str
    entity: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    instant: Optional[str] = None
    #: dimension qname -> member qname
    dimensions: Dict[str, str] = field(default_factory=dict)

    @property
    def is_duration(self) -> bool:
        return self.end_date is not None

    @property
    def period_key(self) -> str:
        """The period the context reports on (end date or instant)."""
        return self.end_date or self.instant or ""

    @property
    def is_dimensional(self) -> bool:
        return bool(self.dimensions)


@dataclass
class InstanceFact:
    """One reported fact from the instance document."""

    concept: str
    value: Optional[str]
    context_ref: str
    unit_ref: Optional[str] = None
    decimals: Optional[str] = None
    fact_id: Optional[str] = None

    def numeric_value(self) -> Optional[float]:
        if self.value is None:
            return None
        try:
            return float(self.value)
        except ValueError:
            return None


class InstanceDocument:
    """
    A parsed XBRL instance document.

    Attributes:
        contexts: context id -> :class:`Context`
        units: unit id -> human unit string ("USD", "shares", "USD/shares")
        facts: every reported fact, in document order
    """

    def __init__(
        self,
        contexts: Dict[str, Context],
        units: Dict[str, str],
        facts: List[InstanceFact],
    ) -> None:
        self.contexts = contexts
        self.units = units
        self.facts = facts
        self._by_concept: Optional[Dict[str, List[InstanceFact]]] = None

    @classmethod
    def parse(cls, raw: "bytes | str") -> "InstanceDocument":
        """Parse the raw XML of an instance document."""
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="ignore")

        # ElementTree resolves tags to {uri}local; recover the document's
        # prefixes from the xmlns declarations so concepts keep their
        # familiar qnames ("us-gaap:Revenues").
        header = raw[:8192].decode("utf-8", errors="ignore")
        uri_to_prefix = {uri: prefix for prefix, uri in _XMLNS_RE.findall(header)}

        root = ET.fromstring(raw)

        contexts = cls._parse_contexts(root)
        units = cls._parse_units(root)
        facts = cls._parse_facts(root, uri_to_prefix)
        return cls(contexts, units, facts)

    # ------------------------------------------------------------------

    @staticmethod
    def _qname(tag: str, uri_to_prefix: Dict[str, str]) -> Optional[str]:
        if not tag.startswith("{"):
            return tag
        uri, _, local = tag[1:].partition("}")
        prefix = uri_to_prefix.get(uri)
        if prefix is None:
            return None
        return f"{prefix}:{local}"

    @classmethod
    def _parse_contexts(cls, root: ET.Element) -> Dict[str, Context]:
        contexts: Dict[str, Context] = {}
        for elem in root.findall(f"{{{XBRLI_NS}}}context"):
            context = Context(id=elem.get("id", ""))

            identifier = elem.find(f"{{{XBRLI_NS}}}entity/{{{XBRLI_NS}}}identifier")
            if identifier is not None and identifier.text:
                context.entity = identifier.text.strip()

            period = elem.find(f"{{{XBRLI_NS}}}period")
            if period is not None:
                start = period.find(f"{{{XBRLI_NS}}}startDate")
                end = period.find(f"{{{XBRLI_NS}}}endDate")
                instant = period.find(f"{{{XBRLI_NS}}}instant")
                if start is not None and start.text:
                    context.start_date = start.text.strip()
                if end is not None and end.text:
                    context.end_date = end.text.strip()
                if instant is not None and instant.text:
                    context.instant = instant.text.strip()

            # Dimensions live under entity/segment or under scenario
            for container in ("entity/{ns}segment", "{ns}scenario"):
                path = container.replace("{ns}", f"{{{XBRLI_NS}}}").replace(
                    "entity/", f"{{{XBRLI_NS}}}entity/"
                )
                holder = elem.find(path)
                if holder is None:
                    continue
                for member in holder.findall(f"{{{XBRLDI_NS}}}explicitMember"):
                    dimension = member.get("dimension", "")
                    if dimension and member.text:
                        context.dimensions[dimension] = member.text.strip()

            contexts[context.id] = context
        return contexts

    @classmethod
    def _parse_units(cls, root: ET.Element) -> Dict[str, str]:
        units: Dict[str, str] = {}
        for elem in root.findall(f"{{{XBRLI_NS}}}unit"):
            unit_id = elem.get("id", "")

            def measure_text(node: Optional[ET.Element]) -> str:
                if node is None or not node.text:
                    return ""
                # "iso4217:USD" -> "USD"
                return node.text.strip().split(":")[-1]

            divide = elem.find(f"{{{XBRLI_NS}}}divide")
            if divide is not None:
                numerator = divide.find(
                    f"{{{XBRLI_NS}}}unitNumerator/{{{XBRLI_NS}}}measure"
                )
                denominator = divide.find(
                    f"{{{XBRLI_NS}}}unitDenominator/{{{XBRLI_NS}}}measure"
                )
                units[unit_id] = (
                    f"{measure_text(numerator)}/{measure_text(denominator)}"
                )
            else:
                units[unit_id] = measure_text(elem.find(f"{{{XBRLI_NS}}}measure"))
        return units

    @classmethod
    def _parse_facts(
        cls, root: ET.Element, uri_to_prefix: Dict[str, str]
    ) -> List[InstanceFact]:
        skip_namespaces = (f"{{{XBRLI_NS}}}", f"{{{LINK_NS}}}")
        facts: List[InstanceFact] = []
        seen: set = set()

        for elem in root:
            tag = elem.tag
            if not isinstance(tag, str) or tag.startswith(skip_namespaces):
                continue
            context_ref = elem.get("contextRef")
            if not context_ref:
                continue

            concept = cls._qname(tag, uri_to_prefix)
            if concept is None:
                continue

            nil = elem.get(f"{{{XSI_NS}}}nil")
            value = None if nil == "true" else (elem.text or "").strip()

            unit_ref = elem.get("unitRef")
            key = (concept, context_ref, unit_ref)
            if key in seen:
                continue
            seen.add(key)

            facts.append(
                InstanceFact(
                    concept=concept,
                    value=value,
                    context_ref=context_ref,
                    unit_ref=unit_ref,
                    decimals=elem.get("decimals"),
                    fact_id=elem.get("id"),
                )
            )
        return facts

    # ------------------------------------------------------------------

    def facts_for(self, concept: str) -> List[InstanceFact]:
        """All facts reported for one concept qname."""
        if self._by_concept is None:
            index: Dict[str, List[InstanceFact]] = {}
            for fact in self.facts:
                index.setdefault(fact.concept, []).append(fact)
            self._by_concept = index
        return self._by_concept.get(concept, [])

    def concepts(self) -> List[str]:
        """Every concept qname reported in the document."""
        if self._by_concept is None:
            self.facts_for("")
        assert self._by_concept is not None
        return list(self._by_concept.keys())

    def unit_of(self, fact: InstanceFact) -> Optional[str]:
        if fact.unit_ref is None:
            return None
        return self.units.get(fact.unit_ref, fact.unit_ref)

    def context_of(self, fact: InstanceFact) -> Optional[Context]:
        return self.contexts.get(fact.context_ref)
