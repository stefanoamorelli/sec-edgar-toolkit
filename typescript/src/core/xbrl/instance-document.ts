/**
 * Parser for XBRL instance documents.
 *
 * An instance document (`<base>_htm.xml` on modern filings, `<base>.xml`
 * on older ones) carries the filing's own facts: every reported value
 * with its context (period, entity, dimensions) and unit. Parsing it
 * gives as-reported data scoped to the filing, including dimensional
 * breakdowns that the aggregated company-facts API cannot provide.
 */

import { XMLParser } from "fast-xml-parser";

export interface InstanceContext {
  id: string;
  entity: string;
  startDate: string | null;
  endDate: string | null;
  instant: string | null;
  /** dimension qname -> member qname */
  dimensions: Record<string, string>;
}

export interface InstanceFact {
  concept: string;
  value: string | null;
  contextRef: string;
  unitRef: string | null;
  decimals: string | null;
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

function text(value: any): string {
  if (value === undefined || value === null) {
    return "";
  }
  if (typeof value === "object") {
    return String(value["#text"] ?? "").trim();
  }
  return String(value).trim();
}

export function periodKey(context: InstanceContext): string {
  return context.endDate || context.instant || "";
}

export class InstanceDocument {
  public readonly contexts: Map<string, InstanceContext>;
  public readonly units: Map<string, string>;
  public readonly facts: InstanceFact[];
  private byConceptIndex: Map<string, InstanceFact[]> | null = null;

  private constructor(
    contexts: Map<string, InstanceContext>,
    units: Map<string, string>,
    facts: InstanceFact[],
  ) {
    this.contexts = contexts;
    this.units = units;
    this.facts = facts;
  }

  static parse(raw: string): InstanceDocument {
    const parser = new XMLParser({
      ignoreAttributes: false,
      parseTagValue: false,
      trimValues: true,
    });
    const document = parser.parse(raw);

    const rootKey = Object.keys(document).find((k) => localName(k) === "xbrl");
    if (!rootKey) {
      throw new Error("Not an XBRL instance document");
    }
    const root = document[rootKey];

    const contexts = InstanceDocument.parseContexts(root);
    const units = InstanceDocument.parseUnits(root);
    const facts = InstanceDocument.parseFacts(root);
    return new InstanceDocument(contexts, units, facts);
  }

  private static parseContexts(
    root: Record<string, any>,
  ): Map<string, InstanceContext> {
    const contexts = new Map<string, InstanceContext>();
    for (const elem of asArray(findKey(root, "context"))) {
      const context: InstanceContext = {
        id: String(elem["@_id"] || ""),
        entity: "",
        startDate: null,
        endDate: null,
        instant: null,
        dimensions: {},
      };

      const entity = findKey(elem, "entity");
      if (entity) {
        context.entity = text(findKey(entity, "identifier"));
        const segment = findKey(entity, "segment");
        if (segment) {
          for (const member of asArray(findKey(segment, "explicitMember"))) {
            const dimension = String(member["@_dimension"] || "");
            const value = text(member);
            if (dimension && value) {
              context.dimensions[dimension] = value;
            }
          }
        }
      }
      const scenario = findKey(elem, "scenario");
      if (scenario) {
        for (const member of asArray(findKey(scenario, "explicitMember"))) {
          const dimension = String(member["@_dimension"] || "");
          const value = text(member);
          if (dimension && value) {
            context.dimensions[dimension] = value;
          }
        }
      }

      const period = findKey(elem, "period");
      if (period) {
        context.startDate = text(findKey(period, "startDate")) || null;
        context.endDate = text(findKey(period, "endDate")) || null;
        context.instant = text(findKey(period, "instant")) || null;
      }

      contexts.set(context.id, context);
    }
    return contexts;
  }

  private static parseUnits(root: Record<string, any>): Map<string, string> {
    const units = new Map<string, string>();
    const measureText = (value: any): string => {
      const raw = text(value);
      return raw.includes(":") ? raw.slice(raw.indexOf(":") + 1) : raw;
    };

    for (const elem of asArray(findKey(root, "unit"))) {
      const id = String(elem["@_id"] || "");
      const divide = findKey(elem, "divide");
      if (divide) {
        const numerator = measureText(
          findKey(findKey(divide, "unitNumerator") || {}, "measure"),
        );
        const denominator = measureText(
          findKey(findKey(divide, "unitDenominator") || {}, "measure"),
        );
        units.set(id, `${numerator}/${denominator}`);
      } else {
        units.set(id, measureText(findKey(elem, "measure")));
      }
    }
    return units;
  }

  private static parseFacts(root: Record<string, any>): InstanceFact[] {
    const skip = new Set(["context", "unit", "schemaRef", "footnoteLink"]);
    const facts: InstanceFact[] = [];
    const seen = new Set<string>();

    for (const [tag, value] of Object.entries(root)) {
      if (tag.startsWith("@_") || skip.has(localName(tag))) {
        continue;
      }
      for (const entry of asArray(value)) {
        if (typeof entry !== "object" || entry === null) {
          continue;
        }
        const contextRef = entry["@_contextRef"];
        if (!contextRef) {
          continue;
        }
        const unitRef = entry["@_unitRef"] ?? null;
        const key = `${tag}|${contextRef}|${unitRef}`;
        if (seen.has(key)) {
          continue;
        }
        seen.add(key);

        const nil = entry["@_xsi:nil"];
        facts.push({
          concept: tag,
          value: nil === "true" ? null : text(entry),
          contextRef: String(contextRef),
          unitRef: unitRef === null ? null : String(unitRef),
          decimals: entry["@_decimals"] ?? null,
        });
      }
    }
    return facts;
  }

  factsFor(concept: string): InstanceFact[] {
    if (this.byConceptIndex === null) {
      this.byConceptIndex = new Map();
      for (const fact of this.facts) {
        const list = this.byConceptIndex.get(fact.concept) || [];
        list.push(fact);
        this.byConceptIndex.set(fact.concept, list);
      }
    }
    return this.byConceptIndex.get(concept) || [];
  }

  concepts(): string[] {
    this.factsFor("");
    return Array.from(this.byConceptIndex!.keys());
  }

  unitOf(fact: InstanceFact): string | null {
    if (fact.unitRef === null) {
      return null;
    }
    return this.units.get(fact.unitRef) || fact.unitRef;
  }

  contextOf(fact: InstanceFact): InstanceContext | undefined {
    return this.contexts.get(fact.contextRef);
  }

  numericValue(fact: InstanceFact): number | null {
    if (fact.value === null || fact.value === "") {
      return null;
    }
    const value = Number(fact.value);
    return Number.isNaN(value) ? null : value;
  }
}
