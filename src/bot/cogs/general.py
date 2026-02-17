import platform
from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from discord.client import DiscordBot


class General(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot: DiscordBot = bot

    @commands.is_owner()
    @commands.slash_command(name="info", description="🏓 Pings the bot.")
    async def info(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        """
        Sends an embedded message with technical information.

        Args:
            interaction: A Discord interaction.
        """

        # Retrieves information
        python_version = platform.python_version()
        discord_version = disnake.__version__
        bot_latency = round(self.bot.latency * 1000, 2)
        os_name = platform.system()
        os_version = platform.version()

        # Creates a Discord embed
        embed = disnake.Embed(title="ℹ️ Інформація про бота")
        embed.add_field(name="🐍 Версія Python", value=python_version)
        embed.add_field(name="📦 Версія disnake", value=discord_version)
        embed.add_field(name="🏓 Затримка", value=f"{bot_latency} мс")
        embed.add_field(name="🏠 Хост", value=f"{os_name} {os_version}")

        await interaction.response.send_message(embed=embed)


def setup(bot: DiscordBot) -> None:
    """
    Adds the cog to the bot.

    Args:
        bot: A Discord bot.
    """
    bot.add_cog(General(bot))
