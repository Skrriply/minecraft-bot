import asyncio
import logging

import aiohttp
from config import settings
from discord.client import DiscordBot
from services.outage import OutageService
from services.proxmox import ProxmoxService
from services.pterodactyl import PterodactylService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

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
