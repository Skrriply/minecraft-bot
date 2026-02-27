import logging
from time import monotonic
from typing import Any

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, default_ttl: int = 15):
        """
        Initializes the class.

        Args:
            default_ttl (optional): The default expiration time in seconds
                                    for cached items if no specific TTL is provided.
                                    Defaults to 15 seconds.
        """
        self.default_ttl: int = default_ttl

        # { "key": {"data": Any, "time": float, "ttl": int} }
        self._storage: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Any | None:
        """
        Retrieves a value from the cache.

        Args:
            key: The unique identifier for the cached item.

        Returns:
            The cached data if valid, or `None` if the key doesn't exist or has expired.
        """
        cached = self._storage.get(key)

        if cached and monotonic() - cached["time"] < cached["ttl"]:
            return cached["data"]
        elif cached:
            del self._storage[key]

        return None

    def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        """
        Stores data in the cache with the current timestamp and a specified TTL.

        Args:
            key: The unique identifier for the item.
            data: The payload to be cached.
            ttl (optional): Custom expiration time in seconds for this specific item.
                            If `None`, uses the instance's `default_ttl`. Defaults to `None`.
        """
        self._storage[key] = {
            "data": data,
            "time": monotonic(),
            "ttl": ttl if not ttl else self.default_ttl,
        }

    def clear(self) -> None:
        """Completely empties the cache."""
        self._storage.clear()
