from __future__ import annotations

import logging
from enum import Enum
from http import HTTPMethod
from typing import TYPE_CHECKING

from core.config import settings
from services.base import BaseAPIClient, ResponseFormat

if TYPE_CHECKING:
    from core.cache import CacheManager

logger = logging.getLogger(__name__)


class PowerCommand(str, Enum):
    """Valid Proxmox power commands."""

    SHUTDOWN = "shutdown"
    REBOOT = "reboot"


class ProxmoxService(BaseAPIClient):
    """
    Service for interacting with the Proxmox VE API.

    Docs:
        https://pve.proxmox.com/wiki/Proxmox_VE_API
        https://pve.proxmox.com/pve-docs/api-viewer/index.html
    """

    def __init__(self, cache_manager: CacheManager) -> None:
        """
        Initializes the class.

        Args:
            cache_manager: An injected instance of the cache manager.
        """
        auth_token: str = f"PVEAPIToken={settings.PROXMOX_USER}!{settings.PROXMOX_TOKEN_ID}={settings.PROXMOX_TOKEN_SECRET}"
        headers: dict[str, str] = {
            "Authorization": auth_token,
            "Accept": "application/json",
        }
        super().__init__(cache_manager, settings.PROXMOX_URL, headers=headers)

        self.node: str = settings.PROXMOX_NODE

    async def send_node_power_action(self, command: PowerCommand) -> None:
        """
        Sends a command to shutdown or reboot the Proxmox host node.

        Args:
            command: Power command to send.
        """
        await self._request(
            HTTPMethod.POST,
            f"/api2/json/nodes/{self.node}/status",
            json={"command": command},
            response_format=ResponseFormat.NONE,
        )
