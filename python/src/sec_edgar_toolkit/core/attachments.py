"""Attachments: the documents inside a filing's archive folder."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_PRESS_RELEASE_RE = re.compile(r"(ex[-_]?99|press[-_]?release)", re.IGNORECASE)


class Attachment:
    """A document inside a filing's archive folder."""

    def __init__(
        self,
        name: str,
        url: str,
        size: Optional[int] = None,
        type: str = "",
        description: str = "",
        sequence: str = "",
    ) -> None:
        self.document = name
        self.name = name
        self.url = url
        self.size = size
        #: SEC document type ("10-K", "EX-99.1", "GRAPHIC", ...)
        self.type = type
        self.description = description
        self.sequence = sequence

    @property
    def is_press_release(self) -> bool:
        if self.type:
            return self.type.upper().startswith("EX-99")
        return bool(_PRESS_RELEASE_RE.search(self.document))

    @property
    def is_exhibit(self) -> bool:
        return self.type.upper().startswith("EX-")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document": self.document,
            "url": self.url,
            "size": self.size,
            "type": self.type,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"Attachment(document='{self.document}')"
