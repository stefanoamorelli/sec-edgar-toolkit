"""HTTP client utilities for SEC EDGAR API."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SecEdgarApiError,
)

# Configure module logger
logger = logging.getLogger(__name__)


class HttpClient:
    """
    HTTP client with rate limiting and error handling for SEC EDGAR API.

    This client handles:
    - Rate limiting to comply with SEC's 10 requests per second limit
    - Automatic retry logic for transient failures
    - Proper error handling and status code management
    - Required headers for SEC EDGAR API access

    Args:
        user_agent: Required user agent string with contact information
        rate_limit_delay: Minimum delay between requests in seconds
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds

    Example:
        >>> client = HttpClient("MyApp/1.0 (contact@example.com)")
        >>> data = client.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json")
    """

    def __init__(
        self,
        user_agent: str,
        rate_limit_delay: float = 0.1,
        max_retries: int = 3,
        timeout: int = 30,
    ) -> None:
        """Initialize HTTP client."""
        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self._last_request_time = 0.0

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set required headers
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
        )

        logger.info(f"HTTP client initialized with User-Agent: {user_agent}")

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f} seconds")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Make HTTP GET request with rate limiting and error handling.

        Args:
            url: The URL to request
            params: Optional query parameters
            **kwargs: Additional arguments to pass to requests

        Returns:
            Parsed JSON response

        Raises:
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            NotFoundError: If resource is not found
            SecEdgarApiError: For other API errors
        """
        self._rate_limit()

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                **kwargs,
            )

            if response.status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded. Please reduce request frequency."
                )
            elif response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Ensure User-Agent header is set correctly."
                )
            elif response.status_code == 404:
                raise NotFoundError(f"Resource not found: {url}")

            response.raise_for_status()

            return response.json()  # type: ignore[no-any-return]

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            raise SecEdgarApiError(f"API request failed: {str(e)}") from e

    def get_raw(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> bytes:
        """
        Make HTTP GET request and return raw content.

        Args:
            url: The URL to request
            params: Optional query parameters
            **kwargs: Additional arguments to pass to requests

        Returns:
            Raw response content as bytes

        Raises:
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            NotFoundError: If resource is not found
            SecEdgarApiError: For other API errors
        """
        self._rate_limit()

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                **kwargs,
            )

            if response.status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded. Please reduce request frequency."
                )
            elif response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Ensure User-Agent header is set correctly."
                )
            elif response.status_code == 404:
                raise NotFoundError(f"Resource not found: {url}")

            response.raise_for_status()

            return response.content

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            raise SecEdgarApiError(f"API request failed: {str(e)}") from e
