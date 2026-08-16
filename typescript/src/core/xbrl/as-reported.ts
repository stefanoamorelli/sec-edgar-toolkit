/**
 * As-reported statements assembled from the filing's own XBRL fileset.
 *
 * Combines the instance document (facts, contexts, units) with the
 * presentation and label linkbases (concept order, hierarchy, display
 * labels) to produce statements exactly as the company reported them:
 * properly ordered line items, per-period columns, and dimensional rows
 * such as segment members.
 *
 * This works for any filing that carries XBRL, whether or not the SEC
 * renderer produced `FilingSummary.xml` and R-files for it.
 */

import { StatementLineItem } from "./report-html-parser";
import { InstanceDocument, periodKey } from "./instance-document";
import {
  LabelLinkbase,
  PresentationLinkbase,
  PresentationNode,
} from "./linkbases";

interface RawHttpClient {
  getRaw(url: string): Promise<string>;
}

/** A statement line item with the extra as-reported fields. */
export interface AsReportedLineItem extends StatementLineItem {
  depth: number;
  order: number;
  abstract: boolean;
  dimensions: Record<string, string>;
}

export class AsReportedStatements {
  private readonly archiveBase: string;
  private readonly http: RawHttpClient;
  private readonly fileNames: string[];

  private document: InstanceDocument | null = null;
  private presentation: PresentationLinkbase | null = null;
  private labels: LabelLinkbase | null = null;
  private loaded = false;

  constructor(archiveBase: string, http: RawHttpClient, fileNames: string[]) {
    this.archiveBase = archiveBase;
    this.http = http;
    this.fileNames = fileNames;
  }

  private baseName(): string | null {
    for (const name of this.fileNames) {
      if (name.toLowerCase().endsWith(".xsd")) {
        return name.slice(0, -4);
      }
    }
    return null;
  }

  private instanceName(): string | null {
    const base = this.baseName();
    if (base === null) {
      return null;
    }
    for (const candidate of [`${base}_htm.xml`, `${base}.xml`]) {
      if (this.fileNames.includes(candidate)) {
        return candidate;
      }
    }
    return null;
  }

  get isAvailable(): boolean {
    return this.instanceName() !== null;
  }

  private async fetch(name: string): Promise<string | null> {
    try {
      return await this.http.getRaw(`${this.archiveBase}/${name}`);
    } catch {
      return null;
    }
  }

  private async load(): Promise<void> {
    if (this.loaded) {
      return;
    }
    this.loaded = true;

    const base = this.baseName();
    const instanceName = this.instanceName();
    if (base === null || instanceName === null) {
      return;
    }

    const rawInstance = await this.fetch(instanceName);
    if (rawInstance === null) {
      return;
    }
    try {
      this.document = InstanceDocument.parse(rawInstance);
    } catch {
      return;
    }

    if (this.fileNames.includes(`${base}_pre.xml`)) {
      const rawPre = await this.fetch(`${base}_pre.xml`);
      if (rawPre !== null) {
        try {
          this.presentation = PresentationLinkbase.parse(rawPre);
        } catch {
          this.presentation = null;
        }
      }
    }

    if (this.fileNames.includes(`${base}_lab.xml`)) {
      const rawLab = await this.fetch(`${base}_lab.xml`);
      if (rawLab !== null) {
        try {
          this.labels = LabelLinkbase.parse(rawLab);
        } catch {
          this.labels = null;
        }
      }
    }
  }

  async getDocument(): Promise<InstanceDocument | null> {
    await this.load();
    return this.document;
  }

  async getPresentation(): Promise<PresentationLinkbase | null> {
    await this.load();
    return this.presentation;
  }

  async getLabels(): Promise<LabelLinkbase | null> {
    await this.load();
    return this.labels;
  }

  async listRoles(): Promise<string[]> {
    const presentation = await this.getPresentation();
    return presentation ? Array.from(presentation.roles.keys()) : [];
  }

  /**
   * Assemble one statement in presentation order.
   *
   * Line items keep the same shape as the rendered-report parser plus
   * `depth`, `order`, `abstract`, and `dimensions`. Dimensional facts
   * become their own rows with the member labels joined into `section`.
   */
  async getStatement(role: string): Promise<AsReportedLineItem[]> {
    const document = await this.getDocument();
    const presentation = await this.getPresentation();
    if (document === null || presentation === null) {
      return [];
    }

    const resolved = presentation.findRole(role);
    if (resolved === null) {
      return [];
    }

    const nodes = presentation.orderedConcepts(resolved);
    // Facts are not scoped to roles in the instance; the role's own
    // presentation tree names the axes and members it presents, which
    // scopes the dimensional rows that belong in this statement.
    const roleConcepts = new Set(nodes.map((node) => node.concept));

    const items: AsReportedLineItem[] = [];
    for (const node of nodes) {
      items.push(...this.itemsForNode(node, document, roleConcepts));
    }
    return items;
  }

  private displayLabel(node: PresentationNode): string {
    if (this.labels) {
      const label = this.labels.labelFor(node.concept, node.preferredLabel);
      if (label) {
        return label;
      }
    }
    const colon = node.concept.indexOf(":");
    return colon >= 0 ? node.concept.slice(colon + 1) : node.concept;
  }

  private memberLabel(memberQname: string): string {
    if (this.labels) {
      const label = this.labels.labelFor(memberQname);
      if (label) {
        return label;
      }
    }
    const colon = memberQname.indexOf(":");
    return colon >= 0 ? memberQname.slice(colon + 1) : memberQname;
  }

  private itemsForNode(
    node: PresentationNode,
    document: InstanceDocument,
    roleConcepts: Set<string>,
  ): AsReportedLineItem[] {
    const baseLabel = this.displayLabel(node);
    const facts = document.factsFor(node.concept);

    if (facts.length === 0) {
      return [
        {
          concept: node.concept,
          label: baseLabel,
          baseLabel,
          section: "",
          values: {},
          units: {},
          hasValues: false,
          abstract: true,
          depth: node.depth,
          order: node.order,
          dimensions: {},
        },
      ];
    }

    // Group by dimensional signature: consolidated row plus one row per
    // member combination presented in this role.
    const grouped = new Map<string, typeof facts>();
    for (const fact of facts) {
      const context = document.contextOf(fact);
      if (!context) {
        continue;
      }
      const signature = Object.entries(context.dimensions)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([dimension, member]) => `${dimension}=${member}`)
        .join("|");
      const list = grouped.get(signature) || [];
      list.push(fact);
      grouped.set(signature, list);
    }

    const items: AsReportedLineItem[] = [];
    const signatures = Array.from(grouped.keys()).sort(
      (a, b) => a.length - b.length,
    );
    for (const signature of signatures) {
      const dimensions: Record<string, string> = {};
      if (signature) {
        let scoped = true;
        for (const pair of signature.split("|")) {
          const [dimension, member] = pair.split("=");
          dimensions[dimension] = member;
          if (!roleConcepts.has(member)) {
            scoped = false;
          }
        }
        if (!scoped) {
          continue;
        }
      }

      const values: Record<string, number> = {};
      const units: Record<string, string> = {};
      for (const fact of grouped.get(signature)!) {
        const context = document.contextOf(fact);
        const number = document.numericValue(fact);
        if (!context || number === null) {
          continue;
        }
        const period = periodKey(context);
        if (!period) {
          continue;
        }
        values[period] = number;
        const unit = document.unitOf(fact);
        if (unit) {
          units[period] = unit;
        }
      }

      if (Object.keys(values).length === 0) {
        continue;
      }

      const section = Object.values(dimensions)
        .map((member) => this.memberLabel(member))
        .join(" | ");
      items.push({
        concept: node.concept,
        label: section ? `${section} | ${baseLabel}` : baseLabel,
        baseLabel,
        section,
        values,
        units,
        hasValues: true,
        abstract: false,
        depth: node.depth,
        order: node.order,
        dimensions,
      });
    }
    return items;
  }
}
