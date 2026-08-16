/**
 * Filing collection type with convenience helpers.
 */

import type { Filing } from "./filing";

/**
 * A list of Filing objects, newest first.
 *
 * Behaves like a plain array (iteration, length, indexing, slicing) and
 * adds the `latest()` accessor.
 */
export class Filings extends Array<Filing> {
  // Keep Array methods (map/filter/slice) returning plain arrays
  static get [Symbol.species](): ArrayConstructor {
    return Array;
  }

  static fromArray(filings: Iterable<Filing>): Filings {
    const collection = new Filings();
    for (const filing of filings) {
      collection.push(filing);
    }
    return collection;
  }

  /**
   * The most recent filing (or null when empty); with `n > 1`, the `n`
   * most recent filings as a Filings collection.
   */
  // eslint-disable-next-line no-dupe-class-members
  latest(): Filing | null;
  // eslint-disable-next-line no-dupe-class-members
  latest(n: number): Filings;
  // eslint-disable-next-line no-dupe-class-members
  latest(n: number = 1): Filing | null | Filings {
    if (n === 1) {
      return this.length > 0 ? this[0] : null;
    }
    return Filings.fromArray(this.slice(0, n));
  }

  /** A new collection narrowed to one form type. */
  filterByForm(form: string): Filings {
    return Filings.fromArray(this.filter((filing) => filing.formType === form));
  }
}
