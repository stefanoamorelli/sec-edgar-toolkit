/**
 * Pure parser for rendered report files (`R<n>.htm`).
 *
 * The files are machine-generated and highly regular, so a regex-based
 * parser is reliable here and keeps the dependency footprint at zero.
 * No I/O happens in this module.
 */

export interface StatementLineItem {
  concept: string;
  label: string;
  baseLabel: string;
  section: string;
  /** period label (ISO date when parseable) -> reported value */
  values: Record<string, number>;
  units: Record<string, string>;
  hasValues: boolean;
}

const NUMBER_RE = /^[\s$]*\(?\s*-?[\d,]+(?:\.\d+)?\s*\)?[\s%]*$/;

const MONTHS: Record<string, number> = {
  jan: 1,
  feb: 2,
  mar: 3,
  apr: 4,
  may: 5,
  jun: 6,
  jul: 7,
  aug: 8,
  sep: 9,
  oct: 10,
  nov: 11,
  dec: 12,
};

const PERIOD_DATE_RE = /([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})\s*$/;

/** Normalize a report period header ("Sep. 27, 2025") to ISO (2025-09-27). */
export function normalizePeriodLabel(label: string): string {
  const match = label.match(PERIOD_DATE_RE);
  if (!match) {
    return label;
  }
  const month = MONTHS[match[1].toLowerCase().slice(0, 3)];
  if (!month) {
    return label;
  }
  const day = String(parseInt(match[2], 10)).padStart(2, "0");
  const monthStr = String(month).padStart(2, "0");
  return `${match[3]}-${monthStr}-${day}`;
}

/** Parse a rendered report cell like `$ (1,234.5)` into a number. */
export function parseReportNumber(text: string): number | null {
  if (!text) {
    return null;
  }
  const cleaned = text.trim();
  if (!NUMBER_RE.test(cleaned)) {
    return null;
  }
  const negative = cleaned.includes("(");
  const digits = cleaned.replace(/[^\d.-]/g, "");
  if (!digits || digits === "-" || digits === ".") {
    return null;
  }
  const value = parseFloat(digits);
  if (Number.isNaN(value)) {
    return null;
  }
  return negative ? -value : value;
}

function stripTags(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;|&#160;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function parseMultipliers(headerText: string): {
  value: number;
  shares: number;
} {
  let multiplier = 1;
  if (/in\s+Millions/i.test(headerText)) {
    multiplier = 1e6;
  } else if (/in\s+Thousands/i.test(headerText)) {
    multiplier = 1e3;
  } else if (/in\s+Billions/i.test(headerText)) {
    multiplier = 1e9;
  }
  let sharesMultiplier = multiplier;
  if (/shares\s+in\s+Millions/i.test(headerText)) {
    sharesMultiplier = 1e6;
  } else if (/shares\s+in\s+Thousands/i.test(headerText)) {
    sharesMultiplier = 1e3;
  }
  return { value: multiplier, shares: sharesMultiplier };
}

function parsePeriodHeaders(rows: string[]): string[] {
  const headerRows = rows.filter((row) => /<th[\s>]/i.test(row));
  if (headerRows.length === 0) {
    return [];
  }
  const lastHeader = headerRows[headerRows.length - 1];
  let texts = Array.from(
    lastHeader.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/gi),
  ).map((m) => stripTags(m[1]));
  // Drop the leading label-column header when present
  if (texts.length > 0 && !/\d{4}/.test(texts[0])) {
    texts = texts.slice(1);
  }
  return texts.filter(Boolean).map(normalizePeriodLabel);
}

/** Parse an R<n>.htm rendered report table into line items. */
export function parseReportHtml(raw: string): StatementLineItem[] {
  const tableMatch =
    raw.match(/<table[^>]*class="report"[^>]*>([\s\S]*?)<\/table>/i) ||
    raw.match(/<table[^>]*>([\s\S]*?)<\/table>/i);
  if (!tableMatch) {
    return [];
  }
  const table = tableMatch[1];

  const rows = Array.from(table.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/gi)).map(
    (m) => m[1],
  );

  const headerText = rows
    .map((row) =>
      Array.from(row.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/gi))
        .map((m) => stripTags(m[1]))
        .join(" "),
    )
    .join(" ");
  const multipliers = parseMultipliers(headerText);
  const periods = parsePeriodHeaders(rows);

  const items: StatementLineItem[] = [];
  // Dimensional reports group measure rows under axis-member rows
  // ("Americas | Operating segments"); carry that grouping onto the
  // measure rows so labels stay meaningful on their own.
  let currentSection = "";
  for (const row of rows) {
    const cells = Array.from(row.matchAll(/<td([^>]*)>([\s\S]*?)<\/td>/gi));
    if (cells.length === 0) {
      continue;
    }
    const labelCell = cells.find((cell) => /class="[^"]*pl/i.test(cell[1]));
    if (!labelCell) {
      continue;
    }

    const label = stripTags(labelCell[2]);

    let concept = "";
    const defrefMatch = labelCell[2].match(/defref_([A-Za-z0-9_-]+)/);
    if (defrefMatch) {
      concept = defrefMatch[1].replace("_", ":");
    }

    const values: Record<string, number> = {};
    const units: Record<string, string> = {};
    let column = 0;
    for (const cell of cells) {
      const cellClass = (cell[1].match(/class="([^"]*)"/i) || [])[1] || "";
      const isNumeric = cellClass.includes("num");
      const isTextFiller = !isNumeric && cellClass.includes("text");
      if (!isNumeric) {
        if (isTextFiller) {
          column += 1;
        }
        continue;
      }
      const text = stripTags(cell[2])
        .replace(/\[\d+\]/g, "")
        .trim();
      const number = parseReportNumber(text);
      if (number !== null) {
        const period =
          column < periods.length ? periods[column] : `col_${column}`;
        const isShares =
          label.toLowerCase().includes("shares") ||
          concept.toLowerCase().includes("shares");
        const isPerShare =
          label.toLowerCase().includes("per share") ||
          concept.toLowerCase().replace(/-/g, "").includes("pershare");
        const scale = isPerShare
          ? 1
          : isShares
            ? multipliers.shares
            : multipliers.value;
        values[period] = number * scale;
        units[period] = isShares ? "shares" : isPerShare ? "USD/shares" : "USD";
      }
      column += 1;
    }

    const hasValues = Object.keys(values).length > 0;
    if (!hasValues && concept.endsWith("Axis")) {
      currentSection = label;
    }

    const section = hasValues ? currentSection : "";
    items.push({
      concept,
      label: section ? `${section} | ${label}` : label,
      baseLabel: label,
      section,
      values,
      units,
      hasValues,
    });
  }

  return items;
}
