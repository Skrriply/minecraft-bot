from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import disnake
from config import settings
from disnake.ext import commands, tasks

if TYPE_CHECKING:
    from discord.client import DiscordBot

logger = logging.getLogger("TasksCog")


class TasksCog(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        """
        Initializes the class.

        Args:
            bot: A Discord bot.
        """
        self.bot: DiscordBot = bot
        self._warn_sent_for_slot: str | None = None
        self._shutdown_sent_for_slot: str | None = None

        self.status_updater.start()
        self.monitor_outage.start()

    def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        self.status_updater.cancel()
        self.monitor_outage.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        await asyncio.sleep(5)
        await self.notify_about_start()

    async def notify_about_start(self) -> None:
        """Turns on the server and notifies about it."""
        channel = self.bot.get_channel(settings.DISCORD_CHANNEL_ID)

        if not channel or not hasattr(channel, "send"):
            logger.error(
                f"Cannot send messages to channel with ID {settings.DISCORD_CHANNEL_ID}. Check that the channel ID is correct."
            )
            return

        await channel.send(  # pyright: ignore
            embed=disnake.Embed(
                title="⚡ Живлення відновлено",
                description="Сервер завантажено. Бот онлайн.",
                color=disnake.Color.blue(),
            )
        )

    @tasks.loop(seconds=30)
    async def status_updater(self) -> None:
        """Updating the bot's status."""
        state = await self.bot.ptero.get_server_state()
        icon = "🔴"
        if state == "running":
            icon = "🟢"
        elif state == "starting":
            icon = "🟡"

        await self.bot.change_presence(
            activity=disnake.Activity(
                name=f"{icon} Status: {state.capitalize()}",
                type=disnake.ActivityType.playing,
            )
        )

    @tasks.loop(seconds=60)
    async def monitor_outage(self) -> None:
        """Checks power outage schedule."""
        tz = ZoneInfo(settings.TIMEZONE)
        now = datetime.now(tz)
        channel = self.bot.get_channel(settings.DISCORD_CHANNEL_ID)

        if not channel or not hasattr(channel, "send"):
            logger.error(
                f"Cannot send messages to channel with ID {settings.DISCORD_CHANNEL_ID}. Check that the channel ID is correct."
            )
            return

        shutdown_time = now + timedelta(minutes=settings.SHUTDOWN_OFFSET_MINUTES)
        current_slot = f"{shutdown_time.hour}:{shutdown_time.minute // 30}"
        warn_time = now + timedelta(
            minutes=settings.SHUTDOWN_OFFSET_MINUTES + settings.WARN_OFFSET_MINUTES
        )

        # Sends a warning to players
        if await self.bot.outage.check_outage_at(warn_time):
            if self._warn_sent_for_slot == current_slot:
                return

            state = await self.bot.ptero.get_server_state()
            if state == "running":
                message = f"Увага! Відключення світла. Сервер вимкнеться через {settings.WARN_OFFSET_MINUTES} хв."
                await self.bot.ptero.send_command(f"say {message}")
                await self.bot.ptero.send_command(
                    f'title @a actionbar {{"text":"{message}","color":"red"}}'
                )
                await channel.send(  # pyright: ignore
                    embed=disnake.Embed(
                        description=message, color=disnake.Color.orange()
                    )
                )
                self._warn_sent_for_slot = current_slot

        # Stops the server
        if await self.bot.outage.check_outage_at(shutdown_time):
            if self._shutdown_sent_for_slot == current_slot:
                return

            await channel.send(  # pyright: ignore
                embed=disnake.Embed(
                    title="🛑 Вимкнення сервера",
                    description="Відключення за графіком. Бот також скоро вимкнеться.",
                    color=disnake.Color.red(),
                )
            )

            state = await self.bot.ptero.get_server_state()
            if state in ("running", "starting"):
                logger.info("Schedule shutdown initiated.")
                await self.bot.ptero.send_command(
                    "kick @a Сервер вимикається за графіком відключень!"
                )
                await asyncio.sleep(5)
                await self.bot.ptero.set_power_state("stop")
                await self.bot.ptero.wait_until_state(
                    "offline", settings.STOP_TIMEOUT_SECONDS
                )

            is_success = await self.bot.proxmox.shutdown_host()

            if is_success:
                logger.info("Proxmox shutdown signal sent.")
            else:
                logger.error("Proxmox shutdown error.")

                if self.bot.owner:
                    await self.bot.owner.send(
                        "⚠️ Помилка при спробі вимкнути Proxmox! Перевірте логи."
                    )

            self._shutdown_sent_for_slot = current_slot

    @status_updater.before_loop
    @monitor_outage.before_loop
    async def before_tasks(self) -> None:
        await self.bot.wait_until_ready()


def setup(bot: DiscordBot) -> None:
    """
    Adds the cog to the bot.

    Args:
        bot: A Discord bot.
    """
    bot.add_cog(TasksCog(bot))
