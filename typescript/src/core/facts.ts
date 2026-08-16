/**
 * Company facts wrapper exposing the high-level facts API.
 *
 * Wraps the raw `data.sec.gov/api/xbrl/companyfacts` JSON with:
 * `.data` holds the `facts` mapping (`{"us-gaap": {...}, "dei": {...}}`).
 * `.getFact(concept)` returns the history for one concept as typed rows
 * sorted by period end ascending.
 */

export interface FactRow {
  fy: number | null;
  fp: string | null;
  value: number | string | null;
  unit: string;
  form: string | null;
  end: string | null;
  start: string | null;
  filed: string | null;
  accn: string | null;
}

export class CompanyFacts {
  public readonly raw: Record<string, any>;
  /** The taxonomy mapping (`data["us-gaap"][concept].units`). */
  public readonly data: Record<string, any>;
  public readonly cik?: number;
  public readonly entityName?: string;

  constructor(raw: Record<string, any>) {
    this.raw = raw || {};
    this.data = this.raw.facts || {};
    this.cik = this.raw.cik;
    this.entityName = this.raw.entityName;
  }

  get isEmpty(): boolean {
    return Object.keys(this.data).length === 0;
  }

  private findConcept(concept: string): Record<string, any> | null {
    for (const taxonomy of ["us-gaap", "dei", "ifrs-full", "srt"]) {
      const taxonomyFacts = this.data[taxonomy];
      if (taxonomyFacts && concept in taxonomyFacts) {
        return taxonomyFacts[concept];
      }
    }
    for (const taxonomyFacts of Object.values(this.data)) {
      if (
        taxonomyFacts &&
        typeof taxonomyFacts === "object" &&
        concept in (taxonomyFacts as Record<string, any>)
      ) {
        return (taxonomyFacts as Record<string, any>)[concept];
      }
    }
    return null;
  }

  /**
   * The reported history of `concept`, sorted by period end ascending,
   * or null when the concept is not reported.
   */
  getFact(concept: string): FactRow[] | null {
    const conceptData = this.findConcept(concept);
    if (!conceptData) {
      return null;
    }

    const rows: FactRow[] = [];
    for (const [unit, unitFacts] of Object.entries(conceptData.units || {})) {
      if (!Array.isArray(unitFacts)) {
        continue;
      }
      for (const fact of unitFacts) {
        rows.push({
          fy: fact.fy ?? null,
          fp: fact.fp ?? null,
          value: fact.val ?? null,
          unit,
          form: fact.form ?? null,
          end: fact.end ?? null,
          start: fact.start ?? null,
          filed: fact.filed ?? null,
          accn: fact.accn ?? null,
        });
      }
    }

    if (rows.length === 0) {
      return null;
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
}
