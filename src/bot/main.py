import asyncio

from core.bot import DiscordBot
from core.config import settings
from core.logger import setup_logging
from services.proxmox import ProxmoxService
from services.pterodactyl import PterodactylService


async def main() -> None:
    """Main entry point for the bot."""
    setup_logging(settings.LOGS_DIR)

    # Setups services
    proxmox_service = ProxmoxService()
    ptero_service = PterodactylService()
    await proxmox_service.create_session()
    await ptero_service.create_session()

    # Initializes and starts the bot
    try:
        bot = DiscordBot(settings.DISCORD_OWNER_ID, proxmox_service, ptero_service)
        bot.load_cogs(settings.COGS_DIR)
        await bot.start(settings.DISCORD_TOKEN)
    finally:
        await proxmox_service.close_session()
        await ptero_service.close_session()


if __name__ == "__main__":
    asyncio.run(main())
