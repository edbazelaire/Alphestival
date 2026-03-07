from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.utils.admin_checks import has_admin_role
from bot.utils.helpers import pick_weighted_winner


class RouletteCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db

    @app_commands.command(name="roulette_bet", description="Place a bet in the current roulette round.")
    async def roulette_bet(self, interaction: discord.Interaction, amount: int) -> None:
        current_round = self.db.get_latest_open_roulette_round()
        if current_round is None:
            await interaction.response.send_message(
                "No open roulette round. Ask an admin to open one.",
                ephemeral=True,
            )
            return
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        success = self.db.place_roulette_bet(current_round["id"], interaction.user.id, amount)
        if not success:
            await interaction.response.send_message(
                "Bet failed. Check your balance.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Roulette bet placed: **{amount}** coins in round #{current_round['id']}.",
            ephemeral=True,
        )

    @app_commands.command(name="roulette_status", description="Show current roulette pool and entries.")
    async def roulette_status(self, interaction: discord.Interaction) -> None:
        current_round = self.db.get_latest_open_roulette_round()
        if current_round is None:
            await interaction.response.send_message("No open roulette round.", ephemeral=True)
            return

        rows = self.db.get_roulette_round_bets(current_round["id"])
        if not rows:
            await interaction.response.send_message(
                f"Round #{current_round['id']} has no bets yet.",
                ephemeral=True,
            )
            return

        total = sum(int(row["total_bet"]) for row in rows)
        lines = [
            f"<@{row['user_id']}>: {row['total_bet']} coins ({(int(row['total_bet']) / total) * 100:.1f}%)"
            for row in rows
        ]
        embed = discord.Embed(
            title=f"Roulette Round #{current_round['id']}",
            description=(
                f"Reward: **{current_round['reward_name'] or 'N/A'}**\n"
                f"Total pool: **{total}** coins\n\n" + "\n".join(lines)
            ),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="roulette_end", description="Draw a winner for the current roulette round (admin).")
    async def roulette_draw(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return

        current_round = self.db.get_latest_open_roulette_round()
        if current_round is None:
            await interaction.response.send_message("No open roulette round.", ephemeral=True)
            return

        rows = self.db.get_roulette_round_bets(current_round["id"])
        entries = [(int(row["user_id"]), int(row["total_bet"])) for row in rows]
        winner_id = pick_weighted_winner(entries)
        if winner_id is None:
            await interaction.response.send_message("No valid bets in this round.", ephemeral=True)
            return

        pool = sum(weight for _, weight in entries)
        self.db.close_roulette_round(current_round["id"])

        dm_status = ""
        reward_name = str(current_round["reward_name"] or "").strip()
        reward_code = str(current_round["reward_code"] or "").strip()
        if reward_code:
            try:
                winner_user = self.bot.get_user(winner_id) or await self.bot.fetch_user(winner_id)
                await winner_user.send(
                    f"Congrats! You won Roulette round #{current_round['id']}.\n"
                    f"Reward: **{reward_name or 'Gift reward'}**\n"
                    f"Gift code: `{reward_code}`"
                )
                dm_status = " Gift code sent by DM."
            except discord.Forbidden:
                dm_status = " Could not DM gift code (DMs closed)."
            except discord.HTTPException:
                dm_status = " Could not DM gift code due to a Discord error."

        await interaction.response.send_message(
            f"Roulette round #{current_round['id']} winner: <@{winner_id}> "
            f"with **{pool}** coins bet.\n"
            f"Reward: **{reward_name or 'N/A'}**.{dm_status}"
        )


async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(RouletteCog(bot, db))
