import logging
from time import monotonic
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """
    Base asynchronous HTTP client with built-in TTL caching mechanism.
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
        cache_ttl: int = 15,
    ):
        """
        Initializes the class.

        Args:
            base_url: The root URL for the API.
            headers (optional): Default HTTP headers (e.g., Authorization). Default `None`.
            timeout (optional): Timeout for the HTTP request. Default 30 seconds.
            cache_ttl (optional): Time-To-Live for cached responses in seconds. Default 15 seconds.
        """
        self.base_url: str = base_url.rstrip("/")
        self.headers: dict[str, str] | None = headers
        self.timeout: aiohttp.ClientTimeout = timeout or aiohttp.ClientTimeout(total=30)
        self.cache_ttl: int = cache_ttl
        self.session: aiohttp.ClientSession | None = None

        # In-memory cache storage:
        # { "url": {"data": response_json, "time": timestamp} }
        self._cache: dict[str, dict[str, Any]] = {}

    async def create_session(self) -> None:
        """Creates the HTTP session."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close_session(self) -> None:
        """Closes the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        use_cache: bool = False,
        ignored_statuses: list[int] = [],
        **kwargs: Any,
    ) -> Any | None:
        """
        Sends an HTTP request.

        Args:
            method: HTTP method ("GET", "POST", etc.).
            endpoint: API endpoint path.
            use_cache (optional): Whether to check and store the result in cache.
            ignored_statuses (optional): Request statuses that will be ignored.
            **kwargs: Additional arguments for aiohttp (json, params, etc.).

        Returns:
            Parsed JSON response as a dictionary, or `None` if request fails.
        """
        if not self.session:
            raise RuntimeError("HTTP session is not initialized.")

        url = f"{self.base_url}{endpoint}"

        # Checks cache (only for GET requests)
        if use_cache and method.upper() == "GET":
            cached_item = self._cache.get(url)
            if cached_item and (monotonic() - cached_item["time"] < self.cache_ttl):
                return cached_item["data"]

        # Sends request
        logger.debug(f"Executing {method} request to '{url}'...")
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status not in ignored_statuses:
                    response.raise_for_status()

                data = await response.json() if response.text else None

                # Stores response in cache
                if use_cache and method.upper() == "GET":
                    self._cache[url] = {"data": data, "time": monotonic()}

                return data
        except aiohttp.ClientResponseError as e:
            logger.error(f"API Error [{e.status}] at '{url}': {e.message}")
        except Exception:
            logger.exception(f"Connection failed for '{url}'.")

        return None
