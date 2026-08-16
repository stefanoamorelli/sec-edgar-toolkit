/**
 * Attachments: the documents inside a filing's archive folder.
 */

const PRESS_RELEASE_RE = /(ex[-_]?99|press[-_]?release)/i;

export class Attachment {
  public readonly document: string;
  public readonly name: string;
  public readonly url: string;
  public readonly size?: number;
  /** SEC document type ("10-K", "EX-99.1", "GRAPHIC", ...) */
  public readonly type: string;
  public readonly description: string;
  public readonly sequence: string;

  constructor(
    name: string,
    url: string,
    size?: number,
    type: string = "",
    description: string = "",
    sequence: string = "",
  ) {
    this.document = name;
    this.name = name;
    this.url = url;
    this.size = size;
    this.type = type;
    this.description = description;
    this.sequence = sequence;
  }

  get isPressRelease(): boolean {
    if (this.type) {
      return this.type.toUpperCase().startsWith("EX-99");
    }
    return PRESS_RELEASE_RE.test(this.document);
  }

  get isExhibit(): boolean {
    return this.type.toUpperCase().startsWith("EX-");
  }

  toObject(): {
    document: string;
    url: string;
    size?: number;
    type: string;
    description: string;
  } {
    return {
      document: this.document,
      url: this.url,
      size: this.size,
      type: this.type,
      description: this.description,
    };
  }
}
