import logging
from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger("DiscordBot")


class DiscordBot(commands.InteractionBot):
    """A Discord bot for managing self-hosted Minecraft server."""

    def __init__(self, cogs_dir: Path, owner_id: int | None = None) -> None:
        """
        Initializes the class.

        Args:
            cogs_dir: The path to the directory from which cogs will be loaded.
            owner_id: Bot owner ID.
        """
        super().__init__(owner_id=owner_id, intents=disnake.Intents.default())
        self.cogs_dir: Path = cogs_dir

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        self.load_cogs()
        logger.info(f'Bot "{self.user.name or "Unknown"}" is now online and ready!')

    def load_cogs(self) -> None:
        """Loads all cogs from the directory."""
        logger.info(f'Loading cogs from "{self.cogs_dir}"...')
        for filename in self.cogs_dir.iterdir():
            if filename.name.endswith(".py") and not filename.name.startswith("_"):
                cog_name = filename.name[:-3]
                logging.info(f'Cog "{cog_name}" has been loaded!')
                self.load_extension(f"cogs.{cog_name}")
