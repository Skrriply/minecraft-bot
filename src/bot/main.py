import asyncio

from core.bot import DiscordBot
from core.config import settings
from core.logger import setup_logging


async def main() -> None:
    """Main entry point for the bot."""
    setup_logging(settings.LOGS_DIR)
    bot = DiscordBot(settings.DISCORD_OWNER_ID)
    bot.load_cogs(settings.COGS_DIR)
    await bot.start(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
