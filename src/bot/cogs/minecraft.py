from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from core.bot import DiscordBot

logger = logging.getLogger(__name__)


class MinecraftCog(commands.Cog):
    """Cog for fetching information and status of the Minecraft server."""

    def __init__(self, bot: DiscordBot) -> None:
        """
        Initializes the class.

        Args:
            bot: A Discord bot.
        """
        self.bot = bot

    @commands.slash_command(
        name="status",
        description="📊 Перевірити статус Minecraft сервера",
    )
    async def server_status(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Fetches and displays the current status of the Pterodactyl server."""
        await inter.response.defer()

        status_data = await self.bot.ptero_service.get_server_state()
        if not status_data:
            await inter.edit_original_response(
                content="❌ Не вдалося отримати статус сервера."
            )
            return

        attrs = status_data.get("attributes", {})
        state: str = attrs.get("current_state", "unknown")
        resources: dict = attrs.get("resources", {})

        cpu_usage = resources.get("cpu_absolute", 0.0)
        ram_mb = resources.get("memory_bytes", 0) / (1024 * 1024)
        disk_mb = resources.get("disk_bytes", 0) / (1024 * 1024)

        # Determines the color by the server status
        color = disnake.Color.red()
        if state == "running":
            color = disnake.Color.green()
        elif state == "starting":
            color = disnake.Color.yellow()

        embed = disnake.Embed(title="📊 Статус сервера", color=color)
        embed.add_field(name="Статус", value=f"**{state.upper()}**", inline=False)
        embed.add_field(name="💻 ЦПУ", value=f"{cpu_usage:.2f}%", inline=True)
        embed.add_field(name="🧠 ОЗУ", value=f"{ram_mb:.2f} MB", inline=True)
        embed.add_field(name="💽 Диск", value=f"{disk_mb:.2f} MB", inline=True)

        await inter.edit_original_response(embed=embed)


def setup(bot: DiscordBot) -> None:
    """
    Adds the cog to the bot.

    Args:
        bot: A Discord bot.
    """
    bot.add_cog(MinecraftCog(bot))
