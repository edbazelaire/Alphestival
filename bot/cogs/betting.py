from __future__ import annotations

from discord.ext import commands

from bot.database import Database


class BettingCog(commands.Cog):
    """Reserved for future betting-related commands."""

    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db


async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(BettingCog(bot, db))
