import asyncio
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

import aiohttp
from config import settings
from discord.client import DiscordBot
from services.outage import OutageService
from services.proxmox import ProxmoxService
from services.pterodactyl import PterodactylService


def setup_logging() -> None:
    if not settings.LOGS_DIR.exists():
        settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler = TimedRotatingFileHandler(
        filename=settings.LOGS_DIR / "bot.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


async def main() -> None:
    setup_logging()

    async with aiohttp.ClientSession() as session:
        ptero_service = PterodactylService(session)
        proxmox_service = ProxmoxService(session)
        outage_service = OutageService(session)
        bot = DiscordBot(
            settings.COGS_DIR,
            ptero_service,
            proxmox_service,
            outage_service,
            settings.DISCORD_OWNER_ID,
        )
        bot.load_cogs()
        await bot.start(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
