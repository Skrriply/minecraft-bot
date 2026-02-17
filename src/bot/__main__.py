import logging

from config import settings
from discord.client import DiscordBot


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = DiscordBot(settings.COGS_DIR, settings.DISCORD_OWNER_ID)
    bot.run(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
