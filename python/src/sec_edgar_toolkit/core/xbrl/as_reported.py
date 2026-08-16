"""
As-reported statements assembled from the filing's own XBRL fileset.

Combines the instance document (facts, contexts, units) with the
presentation and label linkbases (concept order, hierarchy, display
labels) to produce statements exactly as the company reported them:
properly ordered line items, per-period columns, and dimensional rows
such as segment members.

This works for any filing that carries XBRL, whether or not the SEC
renderer produced ``FilingSummary.xml`` and R-files for it.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .instance_document import InstanceDocument, InstanceFact
from .linkbases import LabelLinkbase, PresentationLinkbase, PresentationNode

logger = logging.getLogger(__name__)


class AsReportedStatements:
    """
    Statement access backed by the filing's XBRL fileset.

    Fetches ``<base>_htm.xml`` (or ``<base>.xml`` on older filings),
    ``<base>_pre.xml``, and ``<base>_lab.xml`` from the filing's archive
    folder and assembles ordered line items per statement role.
    """

    def __init__(
        self, archive_base: str, http_client: Any, file_names: List[str]
    ) -> None:
        self._archive_base = archive_base
        self._http = http_client
        self._file_names = file_names

        self._document: Optional[InstanceDocument] = None
        self._presentation: Optional[PresentationLinkbase] = None
        self._labels: Optional[LabelLinkbase] = None
        self._loaded = False
        self._available: Optional[bool] = None

    # ------------------------------------------------------------------
    # Fileset discovery and loading
    # ------------------------------------------------------------------

    def _base_name(self) -> Optional[str]:
        for name in self._file_names:
            if name.lower().endswith(".xsd"):
                return name[:-4]
        return None

    def _instance_name(self) -> Optional[str]:
        base = self._base_name()
        if base is None:
            return None
        for candidate in (f"{base}_htm.xml", f"{base}.xml"):
            if candidate in self._file_names:
                return candidate
        return None

    @property
    def is_available(self) -> bool:
        """True when the filing ships an XBRL fileset we can read."""
        if self._available is None:
            self._available = self._instance_name() is not None
        return self._available

    def _fetch(self, name: str) -> Optional[bytes]:
        try:
            raw = self._http.get_raw(f"{self._archive_base}/{name}")
        except Exception as exc:
            logger.warning(f"Could not fetch {name}: {exc}")
            return None
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="ignore")
        return raw

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        base = self._base_name()
        instance_name = self._instance_name()
        if base is None or instance_name is None:
            return

        raw_instance = self._fetch(instance_name)
        if raw_instance is None:
            return
        try:
            self._document = InstanceDocument.parse(raw_instance)
        except Exception as exc:
            logger.warning(f"Could not parse instance document: {exc}")
            return

        pre_name = f"{base}_pre.xml"
        if pre_name in self._file_names:
            raw_pre = self._fetch(pre_name)
            if raw_pre is not None:
                try:
                    self._presentation = PresentationLinkbase.parse(raw_pre)
                except Exception as exc:
                    logger.warning(f"Could not parse presentation linkbase: {exc}")

        lab_name = f"{base}_lab.xml"
        if lab_name in self._file_names:
            raw_lab = self._fetch(lab_name)
            if raw_lab is not None:
                try:
                    self._labels = LabelLinkbase.parse(raw_lab)
                except Exception as exc:
                    logger.warning(f"Could not parse label linkbase: {exc}")

    @property
    def document(self) -> Optional[InstanceDocument]:
        """The parsed instance document."""
        self._load()
        return self._document

    @property
    def presentation(self) -> Optional[PresentationLinkbase]:
        """The parsed presentation linkbase."""
        self._load()
        return self._presentation

    @property
    def labels(self) -> Optional[LabelLinkbase]:
        """The parsed label linkbase."""
        self._load()
        return self._labels

    # ------------------------------------------------------------------
    # Statement assembly
    # ------------------------------------------------------------------

    def list_roles(self) -> List[str]:
        """Statement roles defined by the presentation linkbase."""
        presentation = self.presentation
        return list(presentation.roles.keys()) if presentation else []

    def get_statement(self, role: str) -> List[Dict[str, Any]]:
        """
        Assemble one statement in presentation order.

        Line items keep the same shape as the rendered-report parser
        (``concept``, ``label``, ``section``, ``values``, ``units``,
        ``has_values``) plus ``depth``, ``order``, ``abstract``, and
        ``dimensions``. Dimensional facts become their own rows with the
        member labels joined into ``section``.
        """
        document = self.document
        presentation = self.presentation
        if document is None or presentation is None:
            return []

        resolved = presentation.find_role(role)
        if resolved is None:
            return []

        nodes = presentation.ordered_concepts(resolved)
        # Facts are not scoped to roles in the instance, so a concept like
        # revenue carries every dimensional breakdown from every
        # disclosure. The role's own presentation tree names the axes and
        # members it presents, and that set scopes which dimensional rows
        # belong in this statement.
        role_concepts = {node.concept for node in nodes}

        items: List[Dict[str, Any]] = []
        for node in nodes:
            items.extend(self._items_for_node(node, document, role_concepts))
        return items

    def _display_label(self, node: PresentationNode) -> str:
        if self.labels is not None:
            label = self.labels.label_for(node.concept, node.preferred_label)
            if label:
                return label
        return node.concept.split(":")[-1]

    def _member_label(self, member_qname: str) -> str:
        if self.labels is not None:
            label = self.labels.label_for(member_qname)
            if label:
                return label
        return member_qname.split(":")[-1]

    def _items_for_node(
        self,
        node: PresentationNode,
        document: InstanceDocument,
        role_concepts: set,
    ) -> List[Dict[str, Any]]:
        base_label = self._display_label(node)
        facts = document.facts_for(node.concept)

        if not facts:
            # Abstract heading or a concept with no reported facts
            return [
                {
                    "concept": node.concept,
                    "label": base_label,
                    "base_label": base_label,
                    "section": "",
                    "values": {},
                    "units": {},
                    "has_values": False,
                    "abstract": True,
                    "depth": node.depth,
                    "order": node.order,
                    "dimensions": {},
                }
            ]

        # Group the concept's facts by their dimensional signature so the
        # consolidated row and each member breakdown become separate rows.
        grouped: Dict[tuple, List[InstanceFact]] = {}
        for fact in facts:
            context = document.context_of(fact)
            if context is None:
                continue
            signature = tuple(sorted(context.dimensions.items()))
            grouped.setdefault(signature, []).append(fact)

        items: List[Dict[str, Any]] = []
        for signature in sorted(grouped, key=len):
            if any(member not in role_concepts for _dimension, member in signature):
                continue
            group = grouped[signature]
            values: Dict[str, float] = {}
            units: Dict[str, str] = {}
            for fact in group:
                context = document.context_of(fact)
                number = fact.numeric_value()
                if context is None or number is None:
                    continue
                period = context.period_key
                if not period:
                    continue
                values[period] = number
                unit = document.unit_of(fact)
                if unit:
                    units[period] = unit

            if not values:
                continue

            dimensions = dict(signature)
            section = " | ".join(
                self._member_label(member) for member in dimensions.values()
            )
            items.append(
                {
                    "concept": node.concept,
                    "label": f"{section} | {base_label}" if section else base_label,
                    "base_label": base_label,
                    "section": section,
                    "values": values,
                    "units": units,
                    "has_values": True,
                    "abstract": False,
                    "depth": node.depth,
                    "order": node.order,
                    "dimensions": dimensions,
                }
            )
        return items
