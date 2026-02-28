from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from core.bot import DiscordBot

logger = logging.getLogger(__name__)

INVALID_STATES = {
    "start": {
        "running": ("❌ Сервер уже працює", "Можете під'єднуватися!"),
        "starting": ("❌ Сервер ще запускається", "Зачекайте кілька хвилин!"),
        "stopping": (
            "❌ Сервер зупиняється",
            "Зачекайте повної зупинки сервера перед його запуском.",
        ),
    },
    "stop": {
        "offline": ("❌ Сервер уже зупинено", "Неможливо зупинити те, що не працює."),
        "stopping": ("❌ Сервер ще зупиняється", "Зачекайте кілька хвилин!"),
        "starting": (
            "❌ Сервер запускається",
            "Зачекайте повного запуску сервер перед його зупинкою.",
        ),
    },
    "restart": {
        "offline": (
            "❌ Сервер зупинено",
            "Використайте команду `/power start` для запуску.",
        ),
        "starting": (
            "❌ Сервер уже запускається",
            "Дочекайтеся доки він запуститься.",
        ),
        "stopping": ("❌ Сервер зупиняється", "Дочекайтеся доки він зупинеться."),
    },
    "kill": {
        "offline": (
            "❌ Сервер уже зупинено",
            "Неможливо зупинити те, що не працює.",
        ),
    },
}
MESSAGES = {
    "start": {
        "process": ("🚀 Запускаю сервер...", "Це може зайняти кілька хвилин."),
        "success": ("✅ Сервер успішно запущено!", "Можете під'єднуватися та грати!"),
    },
    "stop": {
        "process": ("🛑 Зупиняю сервер...", "Зберігаю світ і зупиняю сервер."),
        "success": ("✅ Сервер успішно зупинено!", "Усі дані збережено."),
    },
    "restart": {
        "process": ("🔄 Перезапускаю сервер...", "Це може зайняти кілька хвилин."),
        "success": (
            "✅ Сервер успішно перезапущено!",
            "Можете під'єднуватися та грати!",
        ),
    },
    "kill": {
        "process": (
            "☠️ Примусово зупиняю сервер...",
            "Увага: можлива втрата незбережених даних!",
        ),
        "success": (
            "✅  Сервер успішно зупинено!",
            "Можлива втрата незбережених даних.",
        ),
    },
}


class MinecraftCog(commands.Cog):
    """Cog for fetching information and status of the Minecraft server."""

    def __init__(self, bot: DiscordBot) -> None:
        """
        Initializes the class.

        Args:
            bot: A Discord bot.
        """
        self.bot = bot

    async def _handle_power_action(
        self,
        inter: disnake.ApplicationCommandInteraction,
        action: Literal["start", "stop", "restart", "kill"],
    ) -> None:
        logger.info(
            f"User '{inter.author}' (ID: {inter.author.id}) requested action: {action}"
        )

        # Checks for invalid server states
        state = await self.bot.ptero_service.get_current_state_str()
        if state in INVALID_STATES[action]:
            error_title, error_desc = INVALID_STATES[action][state]
            logger.warning(f"Action '{action}' rejected. Server is in state '{state}'.")
            embed = disnake.Embed(
                title=error_title, description=error_desc, color=disnake.Color.red()
            )
            await inter.edit_original_response(embed=embed)
            return

        # Sends feedback to the user
        process_title, process_desc = MESSAGES[action]["process"]
        embed = disnake.Embed(
            title=process_title, description=process_desc, color=disnake.Color.yellow()
        )
        await inter.edit_original_response(embed=embed)

        # Interacts with Pterodactyl and sends feedback to the user
        success = await self.bot.ptero_service.send_power_action(action)
        if success:
            success_title, success_desc = MESSAGES[action]["success"]
            embed = disnake.Embed(
                title=success_title,
                description=success_desc,
                color=disnake.Color.green(),
            )
            await inter.edit_original_response(embed=embed)
        else:
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося виконати дію.",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)

    @commands.cooldown(1, 60.0, commands.BucketType.guild)
    @commands.slash_command(name="start", description="🚀 Запустити Minecraft сервер")
    async def start_server(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Allows any user to safely send a start signal to the server."""
        await inter.response.defer()
        await self._handle_power_action(inter, "start")

    @commands.is_owner()
    @commands.cooldown(1, 60.0, commands.BucketType.guild)
    @commands.slash_command(name="power", description="🔌 Надіслати команду живлення.")
    async def power_server(
        self,
        inter: disnake.ApplicationCommandInteraction,
        command: Literal["start", "stop", "restart", "kill"] = commands.Param(
            description="Команда живлення", choices=("start", "stop", "restart", "kill")
        ),
    ) -> None:
        await inter.response.defer()
        await self._handle_power_action(inter, command)

    @start_server.error  # pyright: ignore
    @power_server.error  # pyright: ignore
    async def timeout_error(
        self, inter: disnake.ApplicationCommandInteraction, exception: Exception
    ) -> None:
        if isinstance(exception, commands.CommandOnCooldown):
            await inter.send(
                f"⏳ Спробуйте знову через {exception.retry_after:.0f} секунд.",
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

        # Checks for invalid server states
        state = await self.bot.ptero_service.get_current_state_str()
        if state != "running":
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося надіслати команду, бо сервер не запущено.",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)

        clean_command = command.lstrip("/")
        logger.info(
            f"User '{inter.author}' (ID: {inter.author.id}) executed console command: '/{clean_command}'."
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
