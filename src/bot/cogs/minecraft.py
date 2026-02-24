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

    @commands.cooldown(1, 60.0, commands.BucketType.guild)
    @commands.slash_command(name="start", description="🚀 Запустити Minecraft сервер")
    async def start_server(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Allows any user to safely send a start signal to the server."""
        await inter.response.defer()

        logger.info(
            f"User '{inter.author}' (ID: {inter.author.id}) requested to start the server."
        )

        # Checks the current server state
        state = await self.bot.ptero_service.get_current_state_str()
        if state == "running":
            logger.info("Failed to start the server. The server is already running!")
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Сервер уже працює.\nМожете під'єднуватися!",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return
        elif state == "starting":
            logger.info("Failed to start the server. The server is starting!")
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Сервер запускається.\nЗачейкайте кілька хвилин!",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return
        elif state == "stopping":
            logger.info("Failed to start the server. The server is stopping!")
            embed = disnake.Embed(
                title="❌ Помилка",
                description=(
                    "Сервер наразі вимикається.\n"
                    "Зачейкайте, поки сервер вимкнеться та застосйте команду ще раз!"
                ),
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return

        embed = disnake.Embed(
            title="🚀 Запускаю сервер...",
            description="Будь ласка, зачекайте кілька хвилин, поки сервер завантажиться.",
            color=disnake.Color.green(),
        )
        await inter.edit_original_response(embed=embed)

        success = await self.bot.ptero_service.send_power_action("start")
        if success:
            embed = disnake.Embed(
                title="✅ Сервер успішно запущено!",
                description="Можете під'єднуватися та насолоджуватися грою!",
                color=disnake.Color.green(),
            )
        else:
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося запустити сервер.",
                color=disnake.Color.red(),
            )

        await inter.edit_original_response(embed=embed)

    @start_server.error  # pyright: ignore
    async def start_server_error(
        self, inter: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await inter.send(
                f"⏳ Спробуйте знову через {error.retry_after:.0f} секунд.",
                ephemeral=True,
            )

    @commands.is_owner()
    @commands.cooldown(1, 60.0, commands.BucketType.guild)
    @commands.slash_command(name="stop", description="🛑 Зупинити Minecraft сервер")
    async def stop_server(self, inter: disnake.ApplicationCommandInteraction) -> None:
        await inter.response.defer()

        logger.info(
            f"User '{inter.author}' (ID: {inter.author.id}) requested to stop the server."
        )

        # Checks the current server state
        state = await self.bot.ptero_service.get_current_state_str()
        if state == "offline":
            logger.info("Failed to stop the server. The server is already offline!")
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Сервер уже вимкнено.",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return
        elif state == "stopping":
            logger.info("Failed to stop the server. The server is stopping!")
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Сервер вимикається.\nЗачейкайте кілька хвилин!",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return

        embed = disnake.Embed(
            title="🛑 Вимикаю сервер...",
            description="Будь ласка, зачекайте кілька хвилин, поки сервер вимкнеться.",
            color=disnake.Color.green(),
        )
        await inter.edit_original_response(embed=embed)

        await self.bot.ptero_service.send_console_command("save-all")
        success = await self.bot.ptero_service.send_power_action("stop")
        if success:
            embed = disnake.Embed(
                title="✅ Сервер успішно вимкнено!",
                description="Сервер вимкнено та збережено.",
                color=disnake.Color.green(),
            )
        else:
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося вимкнути сервер.",
                color=disnake.Color.red(),
            )

        await inter.edit_original_response(embed=embed)

    @stop_server.error  # pyright: ignore
    async def stop_server_error(
        self, inter: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await inter.send(
                f"⏳ Спробуйте знову через {error.retry_after:.0f} секунд.",
                ephemeral=True,
            )

    @commands.is_owner()
    @commands.slash_command(name="cmd", description="🛠️ Надіслати команду в консоль")
    async def remote_console(
        self,
        inter: disnake.ApplicationCommandInteraction,
        command: str = commands.Param(
            description='Команда без "/" (наприклад: say Hello)'
        ),
    ) -> None:
        await inter.response.defer(ephemeral=False)

        clean_command = command.lstrip("/")
        logger.info(
            f"User '{inter.author}' (ID: {inter.author.id}) executed console command: '{clean_command}'."
        )

        await self.bot.ptero_service.send_console_command(clean_command)
        await inter.edit_original_response(
            content=f"✅ Команду `/{clean_command}` успішно надіслано в консоль."
        )

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
