/**
 * Attachments: the documents inside a filing's archive folder.
 */

const PRESS_RELEASE_RE = /(ex[-_]?99|press[-_]?release)/i;

export class Attachment {
  public readonly document: string;
  public readonly name: string;
  public readonly url: string;
  public readonly size?: number;

  constructor(name: string, url: string, size?: number) {
    this.document = name;
    this.name = name;
    this.url = url;
    this.size = size;
  }

  get isPressRelease(): boolean {
    return PRESS_RELEASE_RE.test(this.document);
  }

  toObject(): { document: string; url: string; size?: number } {
    return { document: this.document, url: this.url, size: this.size };
  }
}
