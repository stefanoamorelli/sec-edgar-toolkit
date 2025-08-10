"""Filing-related type definitions."""

from __future__ import annotations

from typing import Optional, TypedDict


class FilingDocument(TypedDict, total=False):
    """Type definition for filing document information."""

    sequence: str
    filename: str
    description: str
    type: str
    size: Optional[int]


class FilingDetail(TypedDict):
    """Type definition for filing detail information."""

    accessionNumber: str
    filingDate: str
    reportDate: Optional[str]
    acceptanceDateTime: str
    act: Optional[str]
    form: str
    fileNumber: str
    filmNumber: Optional[str]
    items: Optional[str]
    size: int
    isXBRL: bool
    isInlineXBRL: bool
    primaryDocument: str
    primaryDocDescription: str
