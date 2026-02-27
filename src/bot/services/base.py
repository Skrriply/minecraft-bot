from __future__ import annotations

import logging
from enum import Enum
from http import HTTPMethod
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from core.cache import CacheManager

logger = logging.getLogger(__name__)


class ResponseFormat(str, Enum):
    """Strategies for parsing the HTTP response body."""

    JSON = "json"
    TEXT = "text"
    BYTES = "bytes"
    NONE = "none"


class BaseAPIClient:
    """
    Base asynchronous HTTP client with built-in TTL caching mechanism.
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
    ):
        """
        Initializes the class.

        Args:
            cache_manager: An injected instance of the cache manager.
            base_url: The root URL for the API.
            headers (optional): Default HTTP headers (e.g., Authorization). Default to `None`.
            timeout (optional): Timeout for the HTTP request. Default to 30 seconds.
        """
        self.cache: CacheManager = cache_manager
        self.base_url: str = base_url.rstrip("/")
        self.headers: dict[str, str] | None = headers
        self.timeout: aiohttp.ClientTimeout = timeout or aiohttp.ClientTimeout(total=30)
        self.session: aiohttp.ClientSession | None = None

    async def create_session(self) -> None:
        """Creates and initializes the HTTP session."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.headers, timeout=self.timeout
            )

    async def close_session(self) -> None:
        """Closes the active HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _parse_response(
        self, response: aiohttp.ClientResponse, format: ResponseFormat
    ) -> Any | None:
        """Parses the response body based on the requested format strategy."""
        if format == ResponseFormat.JSON:
            return await response.json()
        elif format == ResponseFormat.TEXT:
            return await response.text()
        elif format == ResponseFormat.BYTES:
            return await response.read()

        return None

    async def _request(
        self,
        method: HTTPMethod,
        endpoint: str,
        use_cache: bool = False,
        response_format: ResponseFormat = ResponseFormat.JSON,
        valid_statuses: list[int] | None = None,
        cache_ttl: int | None = None,
        **kwargs: Any,
    ) -> Any | None:
        """
        Executes an asynchronous HTTP request.

        Args:
            method: The HTTP method to use (e.g., HTTPMethod.GET).
            endpoint: The API endpoint path, appended to the base URL.
            use_cache (optional): Whether to check and store the result in the cache (for GET requests only). Defaults to `False`.
            response_format (optional): The expected format of the response body. Defaults to `ResponseFormat.JSON`.
            valid_statuses (optional): A list of HTTP status codes considered successful. If `None`, relies on `response.ok`. Defaults to `None`.
            cache_ttl (optional): Time-To-Live for cached response in seconds. Default to `CacheManager.default_ttl` seconds.
            **kwargs: Additional arguments passed to `aiohttp.ClientSession.request` (e.g., json, data, params).

        Returns:
            The parsed response data based on `response_format`, or `None` if the request fails.

        Raises:
            RuntimeError: If the HTTP session is not initialized before making a request.
        """
        if not self.session:
            raise RuntimeError("HTTP session is not initialized.")

        url = f"{self.base_url}{endpoint}"

        if use_cache and method == HTTPMethod.GET:
            cached_data = self.cache.get(url)

            if cached_data:
                return cached_data

        logger.debug(f"Executing {method} request to '{url}'...")
        try:
            async with self.session.request(method, url, **kwargs) as response:
                is_valid_status = (
                    response.status in valid_statuses if valid_statuses else response.ok
                )
                if not is_valid_status:
                    logger.error(
                        f"API Error [{response.status}] at '{url}': Expected a different status."
                    )
                    return None

                data = await self._parse_response(response, response_format)

                if use_cache and method == HTTPMethod.GET:
                    self.cache.set(url, data, cache_ttl)

                return data
        except Exception:
            logger.exception(f"Connection failed for '{url}'.")

        return None
