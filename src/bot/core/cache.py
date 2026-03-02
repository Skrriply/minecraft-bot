import logging
from time import monotonic
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


class CacheEntry(TypedDict):
    """Represents a single item stored in the cache."""

    data: Any
    expires_at: float


class CacheManager:
    def __init__(self, default_ttl: int = 30):
        """
        Initializes the class.

        Args:
            default_ttl (optional): The default expiration time in seconds
                                    for cached items if no specific TTL is provided.
                                    Defaults to 30 seconds.
        """
        self.default_ttl: int = default_ttl
        self._storage: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        """
        Retrieves a value from the cache.

        Args:
            key: The unique identifier for the cached item.

        Returns:
            The cached data if valid, or `None` if the key doesn't exist or has expired.
        """
        entry = self._storage.get(key)

        if not entry:
            return None

        if monotonic() < entry["expires_at"]:
            return entry["data"]

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
        actual_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = monotonic() + actual_ttl

        self._storage[key] = CacheEntry(data=data, expires_at=expires_at)

    def clear(self) -> None:
        """Completely empties the cache."""
        self._storage.clear()
