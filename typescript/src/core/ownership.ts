/**
 * Attribute-style wrappers for parsed Section 16 ownership forms (3, 4, 5).
 *
 * `OwnershipFormParser` returns nested structures; the classes here expose
 * the same data flat, with the names downstream consumers rely on:
 * `ownerName`, `isDirector`, `transactions[].transactionCode`,
 * `holdings[].ownershipNature`, and so on. The raw parsed form stays
 * available as `.raw`.
 */

import type {
  DerivativeTransaction,
  NonDerivativeHolding,
  NonDerivativeTransaction,
  ParsedOwnershipForm,
} from "../types/ownership-forms";

function isoDate(value: Date | string | null | undefined): string | null {
  if (value == null) {
    return null;
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime())
      ? null
      : value.toISOString().slice(0, 10);
  }
  return String(value);
}

export class OwnershipTransaction {
  public readonly securityTitle: string;
  public readonly transactionDate: string | null;
  public readonly transactionCode: string | null;
  public readonly shares: number | null;
  public readonly pricePerShare: number | null;
  public readonly acquisitionOrDisposition: string | null;
  public readonly sharesOwnedAfter: number | null;
  public readonly ownershipType: string | null;
  public readonly natureOfOwnership: string | null;
  public readonly totalValue: number | null;
  public readonly transactionAmount: number | null;
  public readonly isDerivative: boolean;

  constructor(
    data: NonDerivativeTransaction | DerivativeTransaction,
    derivative: boolean = false,
  ) {
    const record = data as unknown as Record<string, unknown>;
    this.securityTitle = (record.securityTitle as string) || "";
    this.transactionDate = isoDate(record.transactionDate as Date | null);
    this.transactionCode = (record.code as string) || null;
    this.shares = (record.shares as number) ?? null;
    this.pricePerShare = (record.pricePerShare as number) ?? null;
    this.acquisitionOrDisposition =
      (record.acquiredDisposedCode as string) || null;
    this.sharesOwnedAfter =
      (record.sharesOwnedFollowingTransaction as number) ?? null;
    this.ownershipType = (record.directOrIndirectOwnership as string) || null;
    this.natureOfOwnership = (record.natureOfOwnership as string) || null;
    this.isDerivative = derivative;

    let total = (record.totalValue as number) ?? null;
    if (total == null && this.shares != null && this.pricePerShare) {
      total = this.shares * this.pricePerShare;
    }
    this.totalValue = total;
    this.transactionAmount = total;
  }

  toObject(): Record<string, unknown> {
    return { ...(this as unknown as Record<string, unknown>) };
  }
}

export class OwnershipHolding {
  public readonly securityTitle: string;
  public readonly sharesOwned: number | null;
  public readonly ownershipType: string | null;
  public readonly ownershipNature: string | null;

  constructor(data: NonDerivativeHolding) {
    this.securityTitle = data.securityTitle || "";
    this.sharesOwned = data.sharesOwned ?? null;
    this.ownershipType = data.directOrIndirectOwnership || null;
    this.ownershipNature =
      data.natureOfOwnership || data.directOrIndirectOwnership || null;
  }

  toObject(): Record<string, unknown> {
    return { ...(this as unknown as Record<string, unknown>) };
  }
}

/** One reporting owner on the form. */
export class OwnershipOwner {
  public readonly cik: string;
  public readonly name: string;
  public readonly title: string;
  public readonly isDirector: boolean;
  public readonly isOfficer: boolean;
  public readonly isTenPercentOwner: boolean;
  public readonly isOther: boolean;

  constructor(data: Record<string, any>) {
    const relationship = data?.relationship || {};
    this.cik = data?.cik || "";
    this.name = data?.name || "";
    this.title = relationship.officerTitle || "";
    this.isDirector = Boolean(relationship.isDirector);
    this.isOfficer = Boolean(relationship.isOfficer);
    this.isTenPercentOwner = Boolean(relationship.isTenPercentOwner);
    this.isOther = Boolean(relationship.isOther);
  }
}

/** Parsed Form 3/4/5 with flat, attribute-style access. */
export class OwnershipForm {
  public readonly raw: ParsedOwnershipForm;

  public readonly ownerName: string;
  public readonly ownerTitle: string;
  public readonly isDirector: boolean;
  public readonly isOfficer: boolean;
  public readonly isTenPercentOwner: boolean;
  public readonly isOther: boolean;

  public readonly formType: string;
  public readonly periodOfReport: string | null;
  public readonly issuerName: string;
  public readonly issuerCik: string;

  public readonly transactions: OwnershipTransaction[];
  public readonly holdings: OwnershipHolding[];
  public readonly derivativeHoldings: OwnershipHolding[];
  /** Joint filings name several owners; ownerName above is the first. */
  public readonly owners: OwnershipOwner[];
  /** footnote id ("F1", ...) -> text */
  public readonly footnotes: Record<string, string>;

  constructor(parsed: ParsedOwnershipForm) {
    this.raw = parsed;

    const owner = parsed.reportingOwnerInfo;
    const relationship = owner?.relationship;

    this.ownerName = owner?.name || "";
    this.ownerTitle = relationship?.officerTitle || "";
    this.isDirector = Boolean(relationship?.isDirector);
    this.isOfficer = Boolean(relationship?.isOfficer);
    this.isTenPercentOwner = Boolean(relationship?.isTenPercentOwner);
    this.isOther = Boolean(relationship?.isOther);

    this.formType = parsed.documentInfo?.formType || "";
    this.periodOfReport = isoDate(parsed.documentInfo?.periodOfReport);
    this.issuerName = parsed.issuerInfo?.name || "";
    this.issuerCik = parsed.issuerInfo?.cik || "";

    this.transactions = [
      ...(parsed.nonDerivativeTransactions || []).map(
        (tx) => new OwnershipTransaction(tx),
      ),
      ...(parsed.derivativeTransactions || []).map(
        (tx) => new OwnershipTransaction(tx, true),
      ),
    ];
    this.holdings = (parsed.nonDerivativeHoldings || []).map(
      (holding) => new OwnershipHolding(holding),
    );
    this.derivativeHoldings = (parsed.derivativeHoldings || []).map(
      (holding) => new OwnershipHolding(holding as any),
    );
    const reportingOwners = parsed.reportingOwners || [];
    this.owners =
      reportingOwners.length > 0
        ? reportingOwners.map((data) => new OwnershipOwner(data))
        : owner
          ? [new OwnershipOwner(owner)]
          : [];
    this.footnotes = parsed.footnotes || {};
  }
}
