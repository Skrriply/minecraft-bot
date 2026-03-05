from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from pathlib import Path

    from services.dtek import DTEKScraperService
    from services.minecraft import MinecraftService
    from services.proxmox import ProxmoxService
    from services.pterodactyl import PterodactylService

logger = logging.getLogger(__name__)


class DiscordBot(commands.InteractionBot):
    """Bot class."""

    def __init__(
        self,
        owner_id: int,
        proxmox_service: ProxmoxService,
        ptero_service: PterodactylService,
        minecraft_service: MinecraftService,
        dtek_service: DTEKScraperService,
    ) -> None:
        """
        Initializes the class.

        Args:
            id: Bot owner ID.
        """
        super().__init__(
            owner_id=owner_id, intents=disnake.Intents.default(), max_messages=None
        )
        self.proxmox_service: ProxmoxService = proxmox_service
        self.ptero_service: PterodactylService = ptero_service
        self.minecraft_service: MinecraftService = minecraft_service
        self.dtek_service: DTEKScraperService = dtek_service

    async def on_ready(self) -> None:
        """
        Event listener triggered when the bot connects to Discord.
        """
        logger.info(f"Bot authorized as '{self.user}' (ID: {self.user.id}).")

    def load_cogs(self, cogs_dir: Path) -> None:
        """
        Discovers and loads all cogs from a directory.

        Args:
            cogs_dir: The absolute path to the cogs directory.
        """
        logger.info(f"Loading cogs from '{cogs_dir}'...")

        if not cogs_dir.exists():
            logger.info("The directory doesn't exist! Skipping loading...")
            return

        for filename in cogs_dir.iterdir():
            if not filename.name.endswith(".py") or filename.name.startswith("_"):
                continue

            try:
                cog_name = filename.name[:-3]
                logger.info(f"Cog '{cog_name}' has been loaded!")
                self.load_extension(f"cogs.{cog_name}")
            except Exception:
                logger.exception(f"Failed to load the cog: '{filename}'.")
