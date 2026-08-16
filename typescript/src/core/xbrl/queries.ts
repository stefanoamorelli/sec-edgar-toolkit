/**
 * Fact-level query primitives over the company-facts payload.
 *
 * Pure functions that normalize raw company-facts entries into typed
 * fact records; no I/O happens in this module.
 */

import { XbrlFact } from "../../types/xbrl";

/** Query result: an array of fact records with chainable helpers. */
export class FactQuery extends Array<XbrlFact> {
  static get [Symbol.species](): ArrayConstructor {
    return Array;
  }

  static fromRecords(records: Iterable<XbrlFact>): FactQuery {
    const query = new FactQuery();
    for (const record of records) {
      query.push(record);
    }
    return query;
  }

  /** Narrow the results to a single concept name (substring match). */
  byConcept(concept: string): FactQuery {
    const needle = concept.toLowerCase();
    return FactQuery.fromRecords(
      this.filter((record) =>
        String(record.concept || "")
          .toLowerCase()
          .includes(needle),
      ),
    );
  }
}

export interface ParsedFilterExpression {
  concept?: string;
  taxonomy?: string;
  unit?: string;
  period?: string;
}

/** Parse a "concept=Assets&unit=USD" filter expression. */
export function parseFilterExpression(
  expression: string,
): ParsedFilterExpression {
  const parsed: Record<string, string> = {};
  for (const part of expression.split("&")) {
    const eq = part.indexOf("=");
    if (eq > 0) {
      parsed[part.slice(0, eq).trim()] = part.slice(eq + 1).trim();
    }
  }
  return parsed;
}

/** Normalize one concept's raw company-facts entries into fact records. */
export function buildFactRecords(
  conceptName: string,
  conceptData: Record<string, any>,
  taxonomy: string,
  unitFilter?: string,
  periodFilter?: string,
): XbrlFact[] {
  const results: XbrlFact[] = [];

  const units = conceptData.units || {};
  for (const [unit, unitData] of Object.entries(units)) {
    if (unitFilter && unit !== unitFilter) {
      continue;
    }
    if (!Array.isArray(unitData)) {
      continue;
    }

    for (const fact of unitData) {
      if (periodFilter) {
        const matchesEndDate = fact.end === periodFilter;
        const matchesInstant = fact.instant === periodFilter;
        const factPeriod = fact.fy || fact.fp || fact.frame || "";
        const matchesPeriod = String(factPeriod).includes(periodFilter);
        if (!matchesEndDate && !matchesInstant && !matchesPeriod) {
          continue;
        }
      }

      results.push({
        concept: conceptName,
        taxonomy,
        value: fact.val,
        unit,
        period: fact.frame || `FY${fact.fy || ""}${fact.fp || ""}`,
        fiscal_year: fact.fy,
        fiscal_period: fact.fp,
        start_date: fact.start,
        end_date: fact.end,
        period_end: fact.start ? fact.end : undefined,
        period_instant: fact.start ? undefined : fact.end,
        context: fact.accn,
        filed: fact.filed,
        accession_number: fact.accn,
        form: fact.form,
      });
    }
  }

  return results;
}

export interface FactHistoryRow {
  concept: string;
  value: number | string | null;
  unit: string;
  periodEnd: string | null;
  periodInstant: string | null;
  end: string | null;
  filed: string | null;
  form: string | null;
}

/** History of one concept from a raw company-facts payload, sorted by end. */
export function factsHistory(
  facts: Record<string, any>,
  concept: string,
  taxonomy: string = "us-gaap",
): FactHistoryRow[] {
  const conceptData = facts?.facts?.[taxonomy]?.[concept];
  if (!conceptData) {
    return [];
  }

  const rows: FactHistoryRow[] = [];
  for (const [unit, unitFacts] of Object.entries(conceptData.units || {})) {
    if (!Array.isArray(unitFacts)) {
      continue;
    }
    for (const fact of unitFacts) {
      rows.push({
        concept,
        value: fact.val ?? null,
        unit,
        periodEnd: fact.start ? fact.end || null : null,
        periodInstant: fact.start ? null : fact.end || null,
        end: fact.end ?? null,
        filed: fact.filed ?? null,
        form: fact.form ?? null,
      });
    }
  }

  rows.sort((a, b) => {
    const endCompare = (a.end || "").localeCompare(b.end || "");
    if (endCompare !== 0) {
      return endCompare;
    }
    return (a.filed || "").localeCompare(b.filed || "");
  });
  return rows;
}
