from __future__ import annotations

import asyncio
import logging
from enum import Enum
from http import HTTPMethod
from typing import TYPE_CHECKING

from core.config import settings
from pydantic import BaseModel, ValidationError
from services.base import BaseAPIClient, ResponseFormat

if TYPE_CHECKING:
    from core.cache import CacheManager

logger = logging.getLogger(__name__)


class PowerSignal(str, Enum):
    """Valid Pterodactyl power signals."""

    START = "start"
    STOP = "stop"
    RESTART = "restart"
    KILL = "kill"


class ResourceUsage(BaseModel):
    """Server resource usage metrics."""

    memory_bytes: int = 0
    cpu_absolute: float = 0.0
    disk_bytes: int = 0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    uptime: int = 0


class ServerAttributes(BaseModel):
    """Server state attributes."""

    current_state: str = "unknown"
    is_suspended: bool = False
    resources: ResourceUsage | None = None


class ServerResourceResponse(BaseModel):
    """The Pterodactyl server resource API response."""

    object: str = "stats"
    attributes: ServerAttributes


class PterodactylService(BaseAPIClient):
    """
    Service for interacting with the Pterodactyl Client API.

    Docs:
        https://pterodactyl-api-docs.netvpx.com/docs/api/client
    """

    def __init__(self, cache_manager: CacheManager) -> None:
        """
        Initializes the class.

        Args:
            cache_manager: An injected instance of the cache manager.
        """
        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.PTERODACTYL_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        super().__init__(cache_manager, settings.PTERODACTYL_URL, headers=headers)

        self.server_id: str = settings.PTERODACTYL_SERVER_ID

    async def get_server_state(self) -> ServerResourceResponse | None:
        """
        Fetches the current resource usage and state of the Minecraft server.

        Returns:
            API response as a `ServerResourceResponse`, or `None` if request fails.
        """
        logger.debug(f"Fetching status for Pterodactyl server ID: {self.server_id}.")
        data = await self._request(
            HTTPMethod.GET,
            f"/api/client/servers/{self.server_id}/resources",
            use_cache=True,
        )

        if not data:
            return None

        try:
            return ServerResourceResponse.model_validate(data)
        except ValidationError:
            logger.exception("Failed to parse Pterodactyl API response.")

        return None

    async def send_console_command(self, command: str) -> None:
        """
        Sends a command to the Minecraft server console.

        Args:
            command: The command that will be sent.
        """
        await self._request(
            HTTPMethod.POST,
            f"/api/client/servers/{self.server_id}/command",
            json={"command": command},
            response_format=ResponseFormat.NONE,
            valid_statuses=[204],
        )

    async def _wait_until_state(
        self, target_state: str, timeout_seconds: int = 300
    ) -> bool:
        """
        Polls the API until the server reaches the target state or times out.

        Returns:
            `True` if target state is setted, otherwise `False`.
        """
        iterations = timeout_seconds // 5
        for _ in range(iterations):
            await asyncio.sleep(5)
            data = await self.get_server_state()

            if data and data.attributes.current_state == target_state:
                return True

        return False

    async def send_power_action(self, action: PowerSignal) -> bool:
        """
        Sends a power command to the server

        Args:
            action: Power action to send.

        Returns:
            `True` if operation is succesfull, otherwise `False`.
        """
        logger.info(
            f"Sending power action '{action}' to server ID: '{self.server_id}'."
        )
        await self._request(
            HTTPMethod.POST,
            f"/api/client/servers/{self.server_id}/power",
            json={"signal": action},
            response_format=ResponseFormat.NONE,
            valid_statuses=[204],
        )

        return await self._wait_until_state(
            "running" if action in {"start", "restart"} else "offline"
        )
