from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import disnake
from core.config import settings
from disnake.ext import commands, tasks
from services.dtek import PowerStatus
from services.pterodactyl import PowerSignal

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from core.bot import DiscordBot

logger = logging.getLogger(__name__)

INVALID_STATES: dict[PowerSignal, dict[str, tuple[str, str]]] = {
    PowerSignal.START: {
        "running": ("❌ Сервер уже працює", "Можете під'єднуватися!"),
        "starting": ("❌ Сервер ще запускається", "Зачекайте кілька хвилин!"),
        "stopping": (
            "❌ Сервер зупиняється",
            "Зачекайте повної зупинки сервера перед його запуском.",
        ),
    },
    PowerSignal.STOP: {
        "offline": ("❌ Сервер уже зупинено", "Неможливо зупинити те, що не працює."),
        "stopping": ("❌ Сервер ще зупиняється", "Зачекайте кілька хвилин!"),
        "starting": (
            "❌ Сервер запускається",
            "Зачекайте повного запуску сервер перед його зупинкою.",
        ),
    },
    PowerSignal.RESTART: {
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
    PowerSignal.KILL: {
        "offline": (
            "❌ Сервер уже зупинено",
            "Неможливо зупинити те, що не працює.",
        ),
    },
}
MESSAGES: dict[PowerSignal, dict[str, tuple[str, str]]] = {
    PowerSignal.START: {
        "process": ("🚀 Запускаю сервер...", "Це може зайняти кілька хвилин."),
        "success": ("✅ Сервер успішно запущено!", "Можете під'єднуватися та грати!"),
    },
    PowerSignal.STOP: {
        "process": ("🛑 Зупиняю сервер...", "Зберігаю світ і зупиняю сервер."),
        "success": ("✅ Сервер успішно зупинено!", "Усі дані збережено."),
    },
    PowerSignal.RESTART: {
        "process": ("🔄 Перезапускаю сервер...", "Це може зайняти кілька хвилин."),
        "success": (
            "✅ Сервер успішно перезапущено!",
            "Можете під'єднуватися та грати!",
        ),
    },
    PowerSignal.KILL: {
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

    DTEK_STATUS_MAPPING: dict[PowerStatus | None, str] = {
        PowerStatus.YES: "🟢 Світло є",
        PowerStatus.NO: "🔴 Світла немає",
        PowerStatus.MAYBE: "🟡 Можливі відключення",
        None: "⚪ Невідомо",
    }
    STOP_THRESHOLD_MINUTES: int = 5

    def __init__(self, bot: DiscordBot) -> None:
        """
        Initializes the class.

        Args:
            bot: A Discord bot.
        """
        self.bot: DiscordBot = bot
        self.timezone: ZoneInfo = settings.TIMEZONE
        self.empty_since: datetime | None = None

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Starts the monitoring loop once the bot is ready."""
        self.auto_stop_task.start()

    @tasks.loop(minutes=1)
    async def auto_stop_task(self) -> None:
        """Automatically stops the server to save resources."""
        state = await self.bot.ptero_service.get_server_state()
        if not state or state.attributes.current_state != "running":
            self.empty_since = None
            return

        mc_status = await self.bot.minecraft_service.fetch_status()

        if not mc_status:
            return

        players_online, max_players = mc_status
        now = datetime.now(self.timezone)

        if players_online == 0:
            if not self.empty_since:
                self.empty_since = now
                logger.info(
                    f"The server is empty. Countdown to automatic stop in {self.STOP_THRESHOLD_MINUTES} minutes."
                )
            else:
                elapsed = (now - self.empty_since).total_seconds() / 60.0
                if elapsed >= self.STOP_THRESHOLD_MINUTES:
                    logger.info(
                        f"The server has been empty for more than {self.STOP_THRESHOLD_MINUTES} minutes. Stopping..."
                    )
                    await self.bot.ptero_service.send_power_action(PowerSignal.STOP)
                    self.empty_since = None
        else:
            if self.empty_since is not None:
                logger.info(
                    f"The player has joined the server ({players_online}/{max_players}). Auto-stopping canceled."
                )
            self.empty_since = None

    async def _handle_power_action(
        self,
        inter: disnake.ApplicationCommandInteraction,
        action: PowerSignal,
    ) -> None:
        logger.info(
            f"User '{inter.author}' (ID: {inter.author.id}) requested action: {action}"
        )

        # Checks for invalid server states
        data = await self.bot.ptero_service.get_server_state()

        if not data:
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося виконати дію.",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return

        state = data.attributes.current_state
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
        await self._handle_power_action(inter, PowerSignal.START)

    @commands.is_owner()
    @commands.cooldown(1, 60.0, commands.BucketType.guild)
    @commands.slash_command(name="power", description="🔌 Надіслати команду живлення.")
    async def power_server(
        self,
        inter: disnake.ApplicationCommandInteraction,
        command: PowerSignal = commands.Param(description="Команда живлення"),
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
        await inter.response.defer()

        # Checks for invalid server states
        data = await self.bot.ptero_service.get_server_state()

        if not data:
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося виконати дію.",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return

        state = data.attributes.current_state
        if state != "running":
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося надіслати команду, бо сервер не запущено.",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return

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

        server_data = await self.bot.ptero_service.get_server_state()
        schedule_data = await self.bot.dtek_service.get_schedule()

        if not server_data or not server_data.attributes.resources or not schedule_data:
            embed = disnake.Embed(
                title="❌ Помилка",
                description="Не вдалося виконати дію.",
                color=disnake.Color.red(),
            )
            await inter.edit_original_response(embed=embed)
            return

        state = server_data.attributes.current_state
        players_text = "Невідомо"
        cpu_usage = server_data.attributes.resources.cpu_absolute
        ram_mb = server_data.attributes.resources.memory_bytes / (1024 * 1024)
        disk_mb = server_data.attributes.resources.disk_bytes / (1024 * 1024)
        current_power = self.DTEK_STATUS_MAPPING.get(schedule_data.current_status)

        # Determines the color by the server status
        color = disnake.Color.red()
        if state == "running":
            color = disnake.Color.green()

            mc_status = await self.bot.minecraft_service.fetch_status()
            if mc_status:
                players_online, max_players = mc_status
                players_text = f"{players_online}/{max_players}"
        elif state == "starting":
            color = disnake.Color.yellow()

        if schedule_data.next_outage_time and schedule_data.next_power_on_time:
            schedule_text = f"📉 Вимкнення: **{schedule_data.next_outage_time}**\n💡 Увімкнення: **{schedule_data.next_power_on_time}**"
        elif schedule_data.next_outage_time:
            schedule_text = f"📉 Вимкнення: **{schedule_data.next_outage_time}**"
        elif (
            schedule_data.next_power_on_time
            and schedule_data.current_status != PowerStatus.YES
        ):
            schedule_text = f"💡 Увімкнення: **{schedule_data.next_power_on_time}**"
        else:
            schedule_text = "✅ Відключень не планується (або немає даних)"

        embed = disnake.Embed(title="📊 Статус сервера", color=color)
        embed.add_field(name="⛏️ Статус", value=f"**{state.upper()}**", inline=True)
        embed.add_field(name="👥 Гравці", value=f"**{players_text}**", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="💻 ЦПУ", value=f"{cpu_usage:.2f}%", inline=True)
        embed.add_field(name="🧠 ОЗУ", value=f"{ram_mb:.2f} MB", inline=True)
        embed.add_field(name="💽 Диск", value=f"{disk_mb:.2f} MB", inline=True)
        embed.add_field(
            name="⚡ Живлення",
            value=f"{current_power}\n{schedule_text}",
            inline=True,
        )

        await inter.edit_original_response(embed=embed)


def setup(bot: DiscordBot) -> None:
    """
    Adds the cog to the bot.

    Args:
        bot: A Discord bot.
    """
    bot.add_cog(MinecraftCog(bot))
