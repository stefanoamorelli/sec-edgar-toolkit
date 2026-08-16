/**
 * Optional on-disk cache for HTTP responses.
 *
 * Archive content (`/Archives/` URLs) never changes once filed, so it is
 * cached indefinitely. API responses (submissions, company facts, search)
 * are cached with a time-to-live. The cache is opt-in: pass
 * `diskCacheDir` in the client config or set
 * `SEC_EDGAR_TOOLKIT_CACHE_DIR`.
 */

import { createHash } from "crypto";
import * as fs from "fs";
import * as path from "path";

export class DiskCache {
  public readonly directory: string;
  public readonly ttl: number;

  /**
   * @param directory Directory to store cached responses in
   * @param ttl Time-to-live in milliseconds for mutable API responses;
   *   archive content ignores the TTL
   */
  constructor(directory: string, ttl: number = 21600000) {
    this.directory = directory;
    this.ttl = ttl;
    fs.mkdirSync(directory, { recursive: true });
  }

  private static isImmutable(url: string): boolean {
    return url.includes("/Archives/");
  }

  private paths(key: string): { body: string; meta: string } {
    const digest = createHash("sha256").update(key).digest("hex");
    return {
      body: path.join(this.directory, `${digest}.body`),
      meta: path.join(this.directory, `${digest}.meta.json`),
    };
  }

  get(key: string, url: string): string | null {
    const { body, meta } = this.paths(key);
    try {
      const metadata = JSON.parse(fs.readFileSync(meta, "utf-8"));
      if (!DiskCache.isImmutable(url)) {
        if (Date.now() - (metadata.timestamp || 0) > this.ttl) {
          return null;
        }
      }
      return fs.readFileSync(body, "utf-8");
    } catch {
      return null;
    }
  }

  set(key: string, url: string, bodyText: string): void {
    const { body, meta } = this.paths(key);
    try {
      fs.writeFileSync(body, bodyText, "utf-8");
      fs.writeFileSync(meta, JSON.stringify({ url, timestamp: Date.now() }));
    } catch {
      // A failed cache write never fails the request
    }
  }

  /** Delete every cached entry. Returns the number of files removed. */
  clear(): number {
    let removed = 0;
    for (const name of fs.readdirSync(this.directory)) {
      if (name.endsWith(".body") || name.endsWith(".meta.json")) {
        try {
          fs.unlinkSync(path.join(this.directory, name));
          removed += 1;
        } catch {
          continue;
        }
      }
    }
    return removed;
  }
}
