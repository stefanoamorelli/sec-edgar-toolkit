/**
 * Parsers for XBRL presentation and label linkbases.
 *
 * The presentation linkbase (`<base>_pre.xml`) defines, per statement
 * role, which concepts appear and in what order and hierarchy. The label
 * linkbase (`<base>_lab.xml`) carries the human-readable labels,
 * including the preferred variants that the presentation arcs select.
 */

import { XMLParser } from "fast-xml-parser";

export const STANDARD_LABEL = "http://www.xbrl.org/2003/role/label";

export interface PresentationNode {
  concept: string;
  order: number;
  depth: number;
  preferredLabel: string | null;
  children: PresentationNode[];
}

function asArray<T>(value: T | T[] | undefined): T[] {
  if (value === undefined || value === null) {
    return [];
  }
  return Array.isArray(value) ? value : [value];
}

function localName(tag: string): string {
  return tag.includes(":") ? tag.slice(tag.indexOf(":") + 1) : tag;
}

function findKey(obj: Record<string, any>, local: string): any {
  for (const [key, value] of Object.entries(obj)) {
    if (localName(key) === local) {
      return value;
    }
  }
  return undefined;
}

function conceptFromHref(href: string): string {
  const fragment = href.split("#").pop() || "";
  const underscore = fragment.indexOf("_");
  if (underscore < 0) {
    return fragment;
  }
  return `${fragment.slice(0, underscore)}:${fragment.slice(underscore + 1)}`;
}

function parseXml(raw: string): Record<string, any> {
  const parser = new XMLParser({
    ignoreAttributes: false,
    parseTagValue: false,
    trimValues: true,
  });
  const document = parser.parse(raw);
  const rootKey = Object.keys(document).find(
    (k) => localName(k) === "linkbase",
  );
  if (!rootKey) {
    throw new Error("Not an XBRL linkbase");
  }
  return document[rootKey];
}

export class PresentationLinkbase {
  /** role URI -> root nodes in presentation order */
  public readonly roles: Map<string, PresentationNode[]>;

  private constructor(roles: Map<string, PresentationNode[]>) {
    this.roles = roles;
  }

  static parse(raw: string): PresentationLinkbase {
    const root = parseXml(raw);
    const roles = new Map<string, PresentationNode[]>();

    for (const link of asArray(findKey(root, "presentationLink"))) {
      const role = String(link["@_xlink:role"] || "");
      if (!role) {
        continue;
      }
      roles.set(role, PresentationLinkbase.parseLink(link));
    }
    return new PresentationLinkbase(roles);
  }

  private static parseLink(link: Record<string, any>): PresentationNode[] {
    const locators = new Map<string, string>();
    for (const loc of asArray(findKey(link, "loc"))) {
      const label = String(loc["@_xlink:label"] || "");
      const href = String(loc["@_xlink:href"] || "");
      if (label && href) {
        locators.set(label, conceptFromHref(href));
      }
    }

    const arcs = new Map<
      string,
      Array<{ order: number; child: string; preferred: string | null }>
    >();
    const childLabels = new Set<string>();
    for (const arc of asArray(findKey(link, "presentationArc"))) {
      const parent = String(arc["@_xlink:from"] || "");
      const child = String(arc["@_xlink:to"] || "");
      if (!parent || !child) {
        continue;
      }
      const order = Number(arc["@_order"] || 0) || 0;
      const list = arcs.get(parent) || [];
      list.push({
        order,
        child,
        preferred: arc["@_preferredLabel"]
          ? String(arc["@_preferredLabel"])
          : null,
      });
      arcs.set(parent, list);
      childLabels.add(child);
    }

    const build = (
      label: string,
      depth: number,
      preferred: string | null,
    ): PresentationNode => {
      const node: PresentationNode = {
        concept: locators.get(label) || label,
        order: 0,
        depth,
        preferredLabel: preferred,
        children: [],
      };
      const children = (arcs.get(label) || [])
        .slice()
        .sort((a, b) => a.order - b.order);
      for (const entry of children) {
        const child = build(entry.child, depth + 1, entry.preferred);
        child.order = entry.order;
        node.children.push(child);
      }
      return node;
    };

    const roots: PresentationNode[] = [];
    for (const label of locators.keys()) {
      if (!childLabels.has(label) && arcs.has(label)) {
        roots.push(build(label, 0, null));
      }
    }
    return roots;
  }

  orderedConcepts(role: string): PresentationNode[] {
    const flattened: PresentationNode[] = [];
    const walk = (node: PresentationNode): void => {
      flattened.push(node);
      for (const child of node.children) {
        walk(child);
      }
    };
    for (const node of this.roles.get(role) || []) {
      walk(node);
    }
    return flattened;
  }

  findRole(roleOrSuffix: string): string | null {
    if (this.roles.has(roleOrSuffix)) {
      return roleOrSuffix;
    }
    const needle = roleOrSuffix.toLowerCase();
    for (const role of this.roles.keys()) {
      if (role.toLowerCase().endsWith(needle)) {
        return role;
      }
    }
    return null;
  }
}

export class LabelLinkbase {
  /** concept qname -> {label role URI: text} */
  public readonly labels: Map<string, Record<string, string>>;

  private constructor(labels: Map<string, Record<string, string>>) {
    this.labels = labels;
  }

  static parse(raw: string): LabelLinkbase {
    const root = parseXml(raw);
    const labels = new Map<string, Record<string, string>>();

    for (const link of asArray(findKey(root, "labelLink"))) {
      const locators = new Map<string, string>();
      for (const loc of asArray(findKey(link, "loc"))) {
        const label = String(loc["@_xlink:label"] || "");
        const href = String(loc["@_xlink:href"] || "");
        if (label && href) {
          locators.set(label, conceptFromHref(href));
        }
      }

      const resources = new Map<string, Record<string, string>>();
      for (const resource of asArray(findKey(link, "label"))) {
        const resourceLabel = String(resource["@_xlink:label"] || "");
        const role = String(resource["@_xlink:role"] || STANDARD_LABEL);
        const value =
          typeof resource === "object"
            ? String(resource["#text"] ?? "")
            : String(resource);
        if (resourceLabel && value) {
          const entry = resources.get(resourceLabel) || {};
          entry[role] = value;
          resources.set(resourceLabel, entry);
        }
      }

      for (const arc of asArray(findKey(link, "labelArc"))) {
        const concept = locators.get(String(arc["@_xlink:from"] || ""));
        const labelTexts = resources.get(String(arc["@_xlink:to"] || ""));
        if (concept && labelTexts) {
          const entry = labels.get(concept) || {};
          Object.assign(entry, labelTexts);
          labels.set(concept, entry);
        }
      }
    }

    return new LabelLinkbase(labels);
  }

  labelFor(concept: string, preferred?: string | null): string | null {
    const conceptLabels = this.labels.get(concept);
    if (!conceptLabels) {
      return null;
    }
    if (preferred && conceptLabels[preferred]) {
      return conceptLabels[preferred];
    }
    if (conceptLabels[STANDARD_LABEL]) {
      return conceptLabels[STANDARD_LABEL];
    }
    const first = Object.values(conceptLabels)[0];
    return first ?? null;
  }
}
