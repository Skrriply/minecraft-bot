import asyncio
import logging
from typing import Any

from core.config import settings
from services.base import BaseAPIClient

logger = logging.getLogger(__name__)


class PterodactylService(BaseAPIClient):
    """
    Service for interacting with the Pterodactyl Client API.

    Docs:
        https://pterodactyl-api-docs.netvpx.com/docs/api/client
    """

    STATES_MAPPING: dict[str, list[str]] = {
        "start": ["starting", "running"],
    }

    def __init__(self) -> None:
        """Initializes the class."""
        self.server_id: str = settings.PTERODACTYL_SERVER_ID
        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.PTERODACTYL_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        super().__init__(
            base_url=settings.PTERODACTYL_URL, headers=headers, cache_ttl=10
        )

    async def get_server_state(self) -> dict[str, Any] | None:
        """
        Fetches the current resource usage and state of the Minecraft server.

        Returns:
            API response as a dictionary, or `None` if request fails.
        """
        logger.debug(f"Fetching status for Pterodactyl server ID: {self.server_id}.")
        endpoint = f"/api/client/servers/{self.server_id}/resources"
        return await self._request("GET", endpoint)

    async def send_console_command(self, command: str) -> None:
        """
        Sends a command to the Minecraft server console.

        Args:
            command: The command that will be sent.
        """
        endpoint = f"/api/client/servers/{self.server_id}/command"
        payload = {"command": command}
        return await self._request(
            "POST", endpoint, json=payload, ignored_statuses=[204]
        )

    async def get_current_state_str(self) -> str:
        """
        Helper method to parse and return the current state.

        Returns:
            Returns the current state as string.
        """
        data = await self.get_server_state()
        if data and "attributes" in data:
            return data["attributes"].get("current_state", "unknown")

        return "unknown"

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
            current_state = await self.get_current_state_str()

            if current_state == target_state:
                return True

        return False

    async def send_power_action(self, action: str) -> bool:
        """
        Sends a power command to the server

        Args:
            action: Power action to send (e.g. "start", "stop", "restart", "kill").

        Returns:
            `True` if operation is succesfull, otherwise `False`.
        """
        valid_actions = ["start", "stop", "restart", "kill"]
        if action not in valid_actions:
            logger.error(f"Invalid power action attempted: '{action}'.")
            return False

        logger.info(
            f"Sending power action '{action}' to server ID: '{self.server_id}'."
        )
        endpoint = f"/api/client/servers/{self.server_id}/power"
        payload = {"signal": action}
        await self._request("POST", endpoint, json=payload)

        return await self._wait_until_state(
            "running" if action in ["start", "restart"] else "offline"
        )
