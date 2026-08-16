/**
 * Typed document metadata from a filing's index page.
 *
 * The archive folder listing (index.json) only carries file names and
 * sizes. The filing index page lists every document with its sequence,
 * description, and SEC document type (10-K, EX-99.1, GRAPHIC, ...),
 * which is what identifies exhibits reliably.
 */

export interface FilingIndexRecord {
  sequence: string;
  description: string;
  document: string;
  type: string;
  size: string;
}

const ROW_RE = /<tr[^>]*>([\s\S]*?)<\/tr>/gi;
const CELL_RE = /<td[^>]*>([\s\S]*?)<\/td>/gi;

function stripTags(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function documentName(cellHtml: string): string {
  const match = cellHtml.match(/href="([^"]+)"/);
  if (match) {
    const href = match[1].split("/ix?doc=").pop() || match[1];
    return href.split("/").pop() || "";
  }
  return stripTags(cellHtml);
}

/** Parse a filing index page into typed document records. */
export function parseFilingIndexHtml(html: string): FilingIndexRecord[] {
  const records: FilingIndexRecord[] = [];
  let rowMatch;
  ROW_RE.lastIndex = 0;
  while ((rowMatch = ROW_RE.exec(html)) !== null) {
    const cells = Array.from(rowMatch[1].matchAll(CELL_RE)).map((m) => m[1]);
    if (cells.length < 5) {
      continue;
    }
    const document = documentName(cells[2]);
    if (!document) {
      continue;
    }
    records.push({
      sequence: stripTags(cells[0]),
      description: stripTags(cells[1]),
      document,
      type: stripTags(cells[3]),
      size: stripTags(cells[4]),
    });
  }
  return records;
}
