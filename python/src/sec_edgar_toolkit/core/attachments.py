"""Attachments: the documents inside a filing's archive folder."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_PRESS_RELEASE_RE = re.compile(r"(ex[-_]?99|press[-_]?release)", re.IGNORECASE)


class Attachment:
    """A document inside a filing's archive folder."""

    def __init__(self, name: str, url: str, size: Optional[int] = None) -> None:
        self.document = name
        self.name = name
        self.url = url
        self.size = size

    @property
    def is_press_release(self) -> bool:
        return bool(_PRESS_RELEASE_RE.search(self.document))

    def to_dict(self) -> Dict[str, Any]:
        return {"document": self.document, "url": self.url, "size": self.size}

    def __repr__(self) -> str:
        return f"Attachment(document='{self.document}')"
