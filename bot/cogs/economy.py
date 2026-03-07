from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db

    @app_commands.command(name="balance", description="Show your coin balance.")
    async def balance(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        balance = self.db.get_balance(user_id)
        await interaction.response.send_message(
            f"You have **{balance}** coins.",
            ephemeral=True,
        )

    @app_commands.command(name="leaderboard", description="Show top coin holders.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        rows = self.db.get_top_users(limit=10)
        if not rows:
            await interaction.response.send_message("No users found yet.", ephemeral=True)
            return

        lines = []
        for idx, row in enumerate(rows, start=1):
            lines.append(f"{idx}. <@{row['user_id']}> - {row['coins']} coins")

        embed = discord.Embed(title="Coin Leaderboard", description="\n".join(lines))
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(EconomyCog(bot, db))
