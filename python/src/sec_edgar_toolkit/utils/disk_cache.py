"""
Optional on-disk cache for HTTP responses.

Archive content (``/Archives/`` URLs) never changes once filed, so it is
cached indefinitely. API responses (submissions, company facts, search)
are cached with a time-to-live. The cache is opt-in: pass ``cache_dir``
to :func:`~sec_edgar_toolkit.set_identity` or ``SecEdgarApi``, or set
``SEC_EDGAR_TOOLKIT_CACHE_DIR``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DiskCache:
    """File-backed response cache keyed by URL."""

    def __init__(self, cache_dir: "str | Path", ttl: int = 21600) -> None:
        """
        Args:
            cache_dir: Directory to store cached responses in
            ttl: Time-to-live in seconds for mutable API responses;
                archive content ignores the TTL
        """
        self.directory = Path(cache_dir).expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

    @staticmethod
    def _is_immutable(url: str) -> bool:
        return "/Archives/" in url

    def _paths(self, key: str) -> "tuple[Path, Path]":
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return (
            self.directory / f"{digest}.body",
            self.directory / f"{digest}.meta.json",
        )

    def get(self, key: str, url: str) -> Optional[bytes]:
        """Return the cached body for a request key, or None."""
        body_path, meta_path = self._paths(key)
        if not body_path.exists() or not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            return None
        if not self._is_immutable(url):
            if time.time() - meta.get("timestamp", 0) > self.ttl:
                return None
        try:
            return body_path.read_bytes()
        except OSError:
            return None

    def set(self, key: str, url: str, body: bytes) -> None:
        """Store a response body for a request key."""
        body_path, meta_path = self._paths(key)
        try:
            body_path.write_bytes(body)
            meta_path.write_text(json.dumps({"url": url, "timestamp": time.time()}))
        except OSError as exc:
            logger.warning(f"Could not write cache entry: {exc}")

    def clear(self) -> int:
        """Delete every cached entry. Returns the number of files removed."""
        removed = 0
        for path in self.directory.glob("*"):
            if path.suffix in (".body", ".json"):
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed
