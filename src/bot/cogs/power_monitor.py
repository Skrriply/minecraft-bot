from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import disnake
from core.config import settings
from disnake.ext import commands, tasks
from services.proxmox import PowerCommand
from services.pterodactyl import PowerSignal

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from core.bot import DiscordBot

logger = logging.getLogger(__name__)


class PowerMonitorCog(commands.Cog):
    """
    Cog for background monitoring of DTEK power outage schedules."""

    # Time thresholds in minutes
    WARNING_THRESHOLD_MINUTES = 15
    SHUTDOWN_THRESHOLD_MINUTES = 10
    LOOP_TOLERANCE_MINUTES = 1.5

    def __init__(self, bot: DiscordBot) -> None:
        """
        Initializes the class.

        Args:
            bot: A Discord bot.
        """
        self.bot: DiscordBot = bot
        self.notified_outages: set[datetime] = set()
        self.shutdown_outages: set[datetime] = set()
        self.timezone: ZoneInfo = settings.TIMEZONE
        self.channel_id: int = settings.DISCORD_NOTIFICATION_CHANNEL_ID

    def cog_unload(self) -> None:
        """Cancels the background loop when the cog is unloaded."""
        self.power_monitor_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Starts the monitoring loop once the bot is ready."""
        await self._send_startup_notification()
        self.power_monitor_loop.start()

    async def _send_startup_notification(self) -> None:
        """
        Sends a notification to the Discord channel indicating that the bot (and server) is online.
        """
        logger.info("Sending startup (power restored) notification to Discord.")

        channel = self.bot.get_channel(self.channel_id)
        if isinstance(channel, disnake.TextChannel):
            embed = disnake.Embed(
                title="⚡ Живлення відновлено",
                description="Світло завантажено. Бот онлайн.",
                color=disnake.Color.blue(),
            )
            await channel.send(embed=embed)

    def _calculate_target_datetime(self, time_str: str) -> datetime:
        """
        Calculates the exact datetime of the upcoming outage based on a time string.

        Args:
            time_str: The target time as a string formatted as "HH:MM".

        Returns:
            A `datetime` object representing the exact future time of the outage today.
        """
        now = datetime.now(self.timezone)
        target_time = datetime.strptime(time_str, "%H:%M").time()
        return datetime.combine(now.date(), target_time, tzinfo=self.timezone)

    @staticmethod
    def _is_within_window(
        target_minutes: float, actual_minutes: float, tolerance: float
    ) -> bool:
        """
        Evaluates whether a given time delta falls within an acceptable execution window.

        Args:
            target_minutes: The ideal threshold minute mark (e.g., 15 for a 15-minute warning).
            actual_minutes: The current calculated time remaining in minutes.
            tolerance: The allowable deviation in minutes to account for loop delays.

        Returns:
            `True` if the actual time falls within the calculated tolerance window, `False` otherwise.
        """
        return abs(target_minutes - actual_minutes) <= tolerance

    @tasks.loop(minutes=1)
    async def power_monitor_loop(self) -> None:
        """
        Main asynchronous background loop that polls the DTEK schedule and triggers events.
        """
        schedule = await self.bot.dtek_service.get_schedule()
        if not schedule or not schedule.next_outage_time:
            return

        outage_dt = self._calculate_target_datetime(schedule.next_outage_time)
        now = datetime.now(self.timezone)
        delta_minutes = (outage_dt - now).total_seconds() / 60.0

        # 1. Send Warning
        if (
            self._is_within_window(
                self.WARNING_THRESHOLD_MINUTES,
                delta_minutes,
                self.LOOP_TOLERANCE_MINUTES,
            )
            and outage_dt not in self.notified_outages
        ):
            await self._send_warnings()
            self.notified_outages.add(outage_dt)

        # 2. Execute Shutdown
        if (
            self._is_within_window(
                self.SHUTDOWN_THRESHOLD_MINUTES,
                delta_minutes,
                self.LOOP_TOLERANCE_MINUTES,
            )
            and outage_dt not in self.shutdown_outages
        ):
            await self._execute_shutdown(schedule.next_power_on_time)
            self.shutdown_outages.add(outage_dt)

        self._cleanup_state(now)

    async def _send_warnings(self) -> None:
        """
        Sends a warning broadcast to the configured Discord channel and the Minecraft server console.
        """
        logger.info(
            f"Sending a {self.WARNING_THRESHOLD_MINUTES}-minute warning about upcoming power outage."
        )

        channel = self.bot.get_channel(self.channel_id)
        if isinstance(channel, disnake.TextChannel):
            embed = disnake.Embed(
                title="⚠️ Попередження про відключення",
                description=(
                    f"За графіком ДТЕК відключення електроенергії відбудеться через {self.WARNING_THRESHOLD_MINUTES} хвилин.\n"
                    f"Minecraft сервер і цей бот автоматично **вимкнуться через "
                    f"{self.WARNING_THRESHOLD_MINUTES - self.SHUTDOWN_THRESHOLD_MINUTES} хвилин** для збереження даних!"
                ),
                color=disnake.Color.orange(),
            )
            await channel.send(embed=embed)

        server_state = await self.bot.ptero_service.get_server_state()
        if server_state and server_state.attributes.current_state == "running":
            minutes_to_stop = (
                self.WARNING_THRESHOLD_MINUTES - self.SHUTDOWN_THRESHOLD_MINUTES
            )
            commands_to_send = [
                f'title @a actionbar {{"text":"Сервер вимкнеться через {minutes_to_stop} хв!","color":"red"}}',
                f"say [Система] Сервер вимкнеться через {minutes_to_stop} хвилин через відключення світла!",
            ]
            for cmd in commands_to_send:
                await self.bot.ptero_service.send_console_command(cmd)

    async def _execute_shutdown(self, next_power_on_time: str | None = None) -> None:
        """
        Executes the graceful shutdown of the Minecraft server and the Proxmox host node.

        Args:
            next_power_on_time: Optional string indicating the time power is expected to be restored,
                                used for the Discord notification embed.
        """
        logger.warning(
            f"Initiating automated shutdown sequence. Estimated power restoration: {next_power_on_time}"
        )

        channel = self.bot.get_channel(self.channel_id)
        if isinstance(channel, disnake.TextChannel):
            embed = disnake.Embed(
                title="🛑 Вимкнення сервера",
                description=f"Зберігаю дані та вимикаю сервер...\nСвітло з'явиться о {next_power_on_time or 'Невідомо'}.",
                color=disnake.Color.red(),
            )
            await channel.send(embed=embed)

        server_state = await self.bot.ptero_service.get_server_state()
        if server_state and server_state.attributes.current_state not in {
            "offline",
            "stopping",
        }:
            logger.info("Sending kick command to remaining Minecraft players...")
            await self.bot.ptero_service.send_console_command(
                "kick @a Сервер вимикається (відключення електроенергії)..."
            )

            logger.info("Dispatching stop signal to Pterodactyl...")
            success = await self.bot.ptero_service.send_power_action(PowerSignal.STOP)

            if not success:
                logger.error(
                    "Pterodactyl failed to stop the Minecraft server gracefully."
                )
            else:
                logger.info("Minecraft server stopped successfully.")

        logger.info("Dispatching shutdown signal to Proxmox host...")
        await self.bot.proxmox_service.send_node_power_action(PowerCommand.SHUTDOWN)

    def _cleanup_state(self, now: datetime) -> None:
        """
        Clears expired events from the state cache sets.

        Args:
            now: The current datetime.
        """
        cutoff_time = now - timedelta(hours=2)
        self.notified_outages = {dt for dt in self.notified_outages if dt > cutoff_time}
        self.shutdown_outages = {dt for dt in self.shutdown_outages if dt > cutoff_time}


def setup(bot: DiscordBot) -> None:
    """
    Adds the cog to the bot.

    Args:
        bot: A Discord bot.
    """
    bot.add_cog(PowerMonitorCog(bot))
