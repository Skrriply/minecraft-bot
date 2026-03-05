# ./bot/services/minecraft.py
from __future__ import annotations

import logging
from typing import Tuple

from core.config import settings
from mcstatus import BedrockServer, JavaServer

logger = logging.getLogger(__name__)


class MinecraftService:
    """Service for pinging and fetching data directly from the Minecraft server."""

    def __init__(self) -> None:
        """Initializes the class."""
        self.address: str = f"{settings.MINECRAFT_HOST}:{settings.MINECRAFT_PORT}"
        self.server: JavaServer | BedrockServer = (
            JavaServer.lookup(self.address)
            if settings.MINECRAFT_EDITION == "java"
            else BedrockServer.lookup(self.address)
        )

    async def fetch_status(self) -> Tuple[int, int] | None:
        """
        Pings the Minecraft server to get the current player count.

        Returns:
            A tuple of (online_players, max_players) if successful, otherwise None.
        """
        try:
            status = await self.server.async_status()
            return status.players.online, status.players.max
        except Exception:
            return None
