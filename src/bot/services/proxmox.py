import logging
from typing import Any

from core.config import settings
from services.base import BaseAPIClient

logger = logging.getLogger(__name__)


class ProxmoxService(BaseAPIClient):
    """
    Service for interacting with the Proxmox VE API.

    Docs:
        https://pve.proxmox.com/wiki/Proxmox_VE_API
        https://pve.proxmox.com/pve-docs/api-viewer/index.html
    """

    def __init__(self) -> None:
        """Initializes the class."""
        self.node: str = settings.PROXMOX_NODE
        auth_token: str = f"PVEAPIToken={settings.PROXMOX_USER}!{settings.PROXMOX_TOKEN_ID}={settings.PROXMOX_TOKEN_SECRET}"
        headers: dict[str, str] = {
            "Authorization": auth_token,
            "Accept": "application/json",
        }
        super().__init__(base_url=settings.PROXMOX_URL, headers=headers, cache_ttl=30)

    async def send_node_power_action(self, command: str) -> None:
        """
        Sends a command to shutdown or reboot the Proxmox host node.

        Args:
            command: Either "shutdown" or "reboot".
        """
        if command not in ["shutdown", "reboot"]:
            logger.error(f"Invalid command: '{command}'.")
            return

        endpoint = f"/api2/json/nodes/{self.node}/status"
        payload = {"command": command}
        await self._request("POST", endpoint, json=payload)

    async def get_node_status(self) -> dict[str, Any] | None:
        """
        Fetches CPU, RAM, and disk metrics for the Proxmox host node.

        Returns:
            API response as a dictionary, or `None` if request fails.
        """
        endpoint = f"/api2/json/nodes/{self.node}/status"
        return await self._request("GET", endpoint, use_cache=True)
