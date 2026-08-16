"""
Parsers for XBRL presentation and label linkbases.

The presentation linkbase (``<base>_pre.xml``) defines, per statement
role, which concepts appear and in what order and hierarchy. The label
linkbase (``<base>_lab.xml``) carries the human-readable labels,
including the preferred variants (terse, total, negated) that the
presentation arcs select.

Standard library only. No I/O happens in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

LINK_NS = "http://www.xbrl.org/2003/linkbase"
XLINK_NS = "http://www.w3.org/1999/xlink"

STANDARD_LABEL = "http://www.xbrl.org/2003/role/label"


def _concept_from_href(href: str) -> str:
    """``...us-gaap-2025.xsd#us-gaap_Revenues`` -> ``us-gaap:Revenues``."""
    fragment = href.rsplit("#", 1)[-1]
    return fragment.replace("_", ":", 1)


@dataclass
class PresentationNode:
    """One concept's position within a statement role."""

    concept: str
    order: float = 0.0
    depth: int = 0
    preferred_label: Optional[str] = None
    children: List["PresentationNode"] = field(default_factory=list)


class PresentationLinkbase:
    """Per-role concept ordering parsed from ``<base>_pre.xml``."""

    def __init__(self, roles: Dict[str, List[PresentationNode]]) -> None:
        #: role URI -> root nodes in presentation order
        self.roles = roles

    @classmethod
    def parse(cls, raw: "bytes | str") -> "PresentationLinkbase":
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="ignore")
        root = ET.fromstring(raw)

        roles: Dict[str, List[PresentationNode]] = {}
        for link in root.findall(f"{{{LINK_NS}}}presentationLink"):
            role = link.get(f"{{{XLINK_NS}}}role", "")
            if not role:
                continue
            roles[role] = cls._parse_link(link)
        return cls(roles)

    @classmethod
    def _parse_link(cls, link: ET.Element) -> List[PresentationNode]:
        locators: Dict[str, str] = {}
        for loc in link.findall(f"{{{LINK_NS}}}loc"):
            label = loc.get(f"{{{XLINK_NS}}}label", "")
            href = loc.get(f"{{{XLINK_NS}}}href", "")
            if label and href:
                locators[label] = _concept_from_href(href)

        #: parent locator label -> [(order, child locator label, preferred)]
        arcs: Dict[str, List[Tuple[float, str, Optional[str]]]] = {}
        children_labels: set = set()
        for arc in link.findall(f"{{{LINK_NS}}}presentationArc"):
            parent = arc.get(f"{{{XLINK_NS}}}from", "")
            child = arc.get(f"{{{XLINK_NS}}}to", "")
            if not parent or not child:
                continue
            try:
                order = float(arc.get("order", "0"))
            except ValueError:
                order = 0.0
            arcs.setdefault(parent, []).append(
                (order, child, arc.get("preferredLabel"))
            )
            children_labels.add(child)

        def build(label: str, depth: int, preferred: Optional[str]) -> PresentationNode:
            node = PresentationNode(
                concept=locators.get(label, label),
                depth=depth,
                preferred_label=preferred,
            )
            for order, child_label, child_preferred in sorted(
                arcs.get(label, []), key=lambda entry: entry[0]
            ):
                child = build(child_label, depth + 1, child_preferred)
                child.order = order
                node.children.append(child)
            return node

        roots = [
            build(label, 0, None)
            for label in locators
            if label not in children_labels and label in arcs
        ]
        return roots

    def ordered_concepts(self, role: str) -> List[PresentationNode]:
        """Depth-first, presentation-ordered nodes for one role."""
        flattened: List[PresentationNode] = []

        def walk(node: PresentationNode) -> None:
            flattened.append(node)
            for child in node.children:
                walk(child)

        for node in self.roles.get(role, []):
            walk(node)
        return flattened

    def find_role(self, role_or_suffix: str) -> Optional[str]:
        """Resolve a full role URI or a suffix of one."""
        if role_or_suffix in self.roles:
            return role_or_suffix
        needle = role_or_suffix.lower()
        for role in self.roles:
            if role.lower().endswith(needle):
                return role
        return None


class LabelLinkbase:
    """Concept labels parsed from ``<base>_lab.xml``."""

    def __init__(self, labels: Dict[str, Dict[str, str]]) -> None:
        #: concept qname -> {label role URI: text}
        self.labels = labels

    @classmethod
    def parse(cls, raw: "bytes | str") -> "LabelLinkbase":
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="ignore")
        root = ET.fromstring(raw)

        labels: Dict[str, Dict[str, str]] = {}
        for link in root.findall(f"{{{LINK_NS}}}labelLink"):
            locators: Dict[str, str] = {}
            for loc in link.findall(f"{{{LINK_NS}}}loc"):
                label = loc.get(f"{{{XLINK_NS}}}label", "")
                href = loc.get(f"{{{XLINK_NS}}}href", "")
                if label and href:
                    locators[label] = _concept_from_href(href)

            resources: Dict[str, Dict[str, str]] = {}
            for resource in link.findall(f"{{{LINK_NS}}}label"):
                resource_label = resource.get(f"{{{XLINK_NS}}}label", "")
                role = resource.get(f"{{{XLINK_NS}}}role", STANDARD_LABEL)
                if resource_label and resource.text:
                    resources.setdefault(resource_label, {})[role] = resource.text

            for arc in link.findall(f"{{{LINK_NS}}}labelArc"):
                concept = locators.get(arc.get(f"{{{XLINK_NS}}}from", ""))
                label_texts = resources.get(arc.get(f"{{{XLINK_NS}}}to", ""))
                if concept and label_texts:
                    labels.setdefault(concept, {}).update(label_texts)

        return cls(labels)

    def label_for(self, concept: str, preferred: Optional[str] = None) -> Optional[str]:
        """The label for a concept, honoring a preferred label role."""
        concept_labels = self.labels.get(concept)
        if not concept_labels:
            return None
        if preferred and preferred in concept_labels:
            return concept_labels[preferred]
        if STANDARD_LABEL in concept_labels:
            return concept_labels[STANDARD_LABEL]
        return next(iter(concept_labels.values()))
