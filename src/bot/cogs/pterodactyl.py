from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import disnake
from config import settings
from disnake.ext import commands

if TYPE_CHECKING:
    from discord.client import DiscordBot


class PterodactylCog(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        """
        Initializes the class.

        Args:
            bot: A Discord bot.
        """
        self.bot: DiscordBot = bot

    @commands.slash_command(name="status", description="📊 Перевірити статус сервера")
    async def status(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        """
        Sends the server status.

        Args:
            interaction: A Discord interaction.
        """
        await interaction.response.defer()

        state = await self.bot.ptero.get_server_state()

        tz = ZoneInfo(settings.TIMEZONE)
        now = datetime.now(tz)
        is_outage = await self.bot.outage.check_outage_at(now)
        next_shutdown = await self.bot.outage.check_outage_at(
            now + timedelta(minutes=settings.SHUTDOWN_OFFSET_MINUTES)
        )

        # Determines the color by the server status
        color = disnake.Color.red()
        if state == "running":
            color = disnake.Color.green()
        elif state == "starting":
            color = disnake.Color.yellow()

        embed = disnake.Embed(title="📊 Статус сервера", color=color)
        embed.add_field(name="Minecraft", value=f"`{state.upper()}`", inline=True)
        embed.add_field(
            name="Світло (зараз)",
            value="🔴 Немає" if is_outage else "🟢 Є",
            inline=True,
        )
        embed.add_field(
            name="Ризик вимкнення",
            value="⚠️ Високий" if next_shutdown else "✅ Низький",
            inline=False,
        )

        await interaction.edit_original_response(embed=embed)

    @commands.slash_command(name="start", description="🚀 Запустити Minecraft сервер.")
    async def start(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        """
        Starts Minecraft server.

        Args:
            interaction: A Discord interaction.
        """
        await interaction.response.defer()

        # Checks the current server state
        state = await self.bot.ptero.get_server_state()
        if state == "running":
            await interaction.edit_original_response(content="✅ Сервер уже працює!")
            return
        elif state == "starting":
            await interaction.edit_original_response(
                content="⚠️ Сервер уже запускається! Зачекайте."
            )
            return

        # Checks the availability of electricity
        tz = ZoneInfo(settings.TIMEZONE)
        if await self.bot.outage.check_outage_at(datetime.now(tz)):
            await interaction.edit_original_response(
                content="🚫 **Помилка:** За графіком зараз немає світла."
            )
            return

        await interaction.edit_original_response(
            "🚀 Запускаю сервер... Це може зайняти кілька хвилин."
        )
        await self.bot.ptero.set_power_state("start")

        # Monitors the server status
        is_running = await self.bot.ptero.wait_until_state(
            "running", settings.STOP_TIMEOUT_SECONDS
        )
        if is_running:
            await interaction.edit_original_response(
                content="✅ **Сервер успішно вимкнено!**"
            )
        else:
            await interaction.edit_original_response(
                content="⚠️ Час очікування вичерпано. Скоріше за все, сервер ще вимикається."
            )

    @commands.is_owner()
    @commands.slash_command(name="stop", description="🛑 Зупинити Minecraft сервер.")
    async def stop(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        """
        Stops Minecraft server.

        Args:
            interaction: A Discord interaction.
        """
        await interaction.response.defer()

        # Checks the current server state
        state = await self.bot.ptero.get_server_state()
        if state == "offline":
            await interaction.edit_original_response(
                content="🚫 **Помилка:** Сервер уже вимкнено."
            )
            return
        elif state == "stopping":
            await interaction.edit_original_response(
                content="⚠️ Сервер уже вимикається! Зачекайте."
            )
            return

        await interaction.edit_original_response("🛑 Вимикаю сервер...")
        await self.bot.ptero.set_power_state("stop")

        # Monitors the server status
        is_offline = await self.bot.ptero.wait_until_state(
            "offline", settings.STOP_TIMEOUT_SECONDS
        )
        if is_offline:
            await interaction.edit_original_response(
                content="✅ **Сервер успішно вимкнено!**"
            )
        else:
            await interaction.edit_original_response(
                content="⚠️ Час очікування вичерпано. Скоріше за все, сервер ще вимикається."
            )


def setup(bot: DiscordBot) -> None:
    """
    Adds the cog to the bot.

    Args:
        bot: A Discord bot.
    """
    bot.add_cog(PterodactylCog(bot))
