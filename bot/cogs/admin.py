from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.utils.admin_checks import has_admin_role
from bot.utils.roulette_rewards import RouletteRewardsStore


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        self.roulette_rewards = RouletteRewardsStore(db=db)

    def _poll_answer_text(self, answer: Any) -> str:
        direct_text = getattr(answer, "text", None)
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()
        media = getattr(answer, "poll_media", None)
        media_text = getattr(media, "text", None)
        if isinstance(media_text, str) and media_text.strip():
            return media_text.strip()
        return ""

    async def _reward_poll_message(
        self,
        interaction: discord.Interaction,
        poll_message: discord.Message,
        winning_option: str,
        reward: int,
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server channel.",
                ephemeral=True,
            )
            return

        poll = getattr(poll_message, "poll", None)
        if poll is None and poll_message.reference and poll_message.reference.message_id:
            try:
                referenced = await interaction.channel.fetch_message(int(poll_message.reference.message_id))
            except (discord.NotFound, discord.Forbidden):
                referenced = None
            if referenced is not None:
                poll = getattr(referenced, "poll", None)
                if poll is not None:
                    poll_message = referenced

        poll_message_id = int(poll_message.id)
        if self.db.has_poll_reward(poll_message_id):
            await interaction.response.send_message(
                "Rewards were already granted for this poll.",
                ephemeral=True,
            )
            return

        if poll is None:
            await interaction.response.send_message(
                "This message does not contain a native Discord poll. "
                "Use the ID of the original poll message (not a result/system message).",
                ephemeral=True,
            )
            return

        normalized_winning = self.db.normalize_answer(winning_option)
        answers = list(getattr(poll, "answers", []) or [])
        selected_answer = None
        available = []
        for answer in answers:
            text = self._poll_answer_text(answer)
            if text:
                available.append(text)
                if self.db.normalize_answer(text) == normalized_winning:
                    selected_answer = answer

        if selected_answer is None:
            options_text = ", ".join(f"`{opt}`" for opt in available) if available else "none"
            await interaction.response.send_message(
                f"Winning option not found. Available options: {options_text}",
                ephemeral=True,
            )
            return

        winner_ids: list[int] = []
        voters_method = getattr(selected_answer, "voters", None)
        if voters_method is None:
            await interaction.response.send_message(
                "This discord.py version cannot fetch poll voters. Upgrade and retry.",
                ephemeral=True,
            )
            return

        try:
            async for user in voters_method(limit=None):
                if not user.bot:
                    winner_ids.append(int(user.id))
        except TypeError:
            async for user in voters_method():
                if not user.bot:
                    winner_ids.append(int(user.id))

        winner_count, total_payout = self.db.record_poll_reward(
            message_id=poll_message_id,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            winning_answer=winning_option,
            reward_coins=reward,
            winner_ids=winner_ids,
            awarded_by=interaction.user.id,
        )

        await interaction.response.send_message(
            f"Poll rewards granted for message `{poll_message_id}`.\n"
            f"Winning option: `{winning_option}`\n"
            f"Winners: **{winner_count}**\n"
            f"Reward: **+{reward}** each\n"
            f"Total payout: **{total_payout}** coins"
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="roulette_open", description="Open a new roulette round (admin).")
    async def roulette_open(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return

        current_round = self.db.get_latest_open_roulette_round()
        if current_round is not None:
            await interaction.response.send_message(
                f"Round #{current_round['id']} is already open.",
                ephemeral=True,
            )
            return

        try:
            reward_index, reward_name, reward_code = self.roulette_rewards.get_current_reward()
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        round_id = self.db.create_roulette_round(
            reward_name=reward_name,
            reward_code=reward_code,
            reward_index=reward_index,
        )
        next_index = self.roulette_rewards.advance_index()
        await interaction.response.send_message(
            f"#{reward_name}\n"
            f"New Roulette round has started with reward: **{reward_name}**.\n"
            f"To participate, use the /roulette_bet command and bet coins on the reward. The more you bet, the higher your chance of winning."
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="roulette_set_index", description="Set current roulette reward index (admin).")
    async def roulette_set_index(self, interaction: discord.Interaction, index: int) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        try:
            new_index = self.roulette_rewards.set_current_index(index)
            _, reward_name, _ = self.roulette_rewards.get_current_reward()
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        await interaction.response.send_message(
            f"Roulette index set to **{new_index}**. Current reward is **{reward_name}**."
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="prize_reset",
        description="Reset community prize contributions and unlocks (admin).",
    )
    async def prize_reset(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return

        self.db.reset_prize_pool()
        await interaction.response.send_message(
            "Community prize pool has been reset to a fresh state."
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="give_coins",
        description="Add or remove coins from a user (admin).",
    )
    @app_commands.describe(
        member="User to adjust",
        amount="Signed amount, e.g. 50 or -25",
    )
    async def give_coins(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
    ) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if amount == 0:
            await interaction.response.send_message(
                "Amount cannot be 0.",
                ephemeral=True,
            )
            return

        ok, new_balance = self.db.adjust_user_coins(member.id, amount)
        if not ok:
            await interaction.response.send_message(
                f"Adjustment failed: {member.mention} would go below 0 coins. "
                f"Current balance is **{new_balance}**.",
                ephemeral=True,
            )
            return

        sign = "+" if amount > 0 else ""
        await interaction.response.send_message(
            f"Adjusted {member.mention} by **{sign}{amount}** coins. "
            f"New balance: **{new_balance}**."
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="clean_rewards",
        description="Delete all stored rewards for a player (admin).",
    )
    @app_commands.describe(player="Discord player to clean rewards for")
    async def clean_rewards(self, interaction: discord.Interaction, player: discord.Member) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return

        gamer_id = self.db.get_game_player_id(player.id)
        if not gamer_id:
            await interaction.response.send_message(
                f"{player.mention} has no linked gamer ID (`/join` not done).",
                ephemeral=True,
            )
            return

        rewards_deleted, purchases_deleted = self.db.clear_player_rewards(gamer_id)
        await interaction.response.send_message(
            f"Rewards cleaned for {player.mention} (gamer_id `{gamer_id}`).\n"
            f"- Deleted rewards: **{rewards_deleted}**\n"
            f"- Deleted purchase locks: **{purchases_deleted}**"
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="channel_clear",
        description="Delete all messages in this channel (admin).",
    )
    async def channel_clear(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server channel.",
                ephemeral=True,
            )
            return
        if not isinstance(
            interaction.channel,
            (discord.TextChannel, discord.Thread),
        ):
            await interaction.response.send_message(
                "This channel type cannot be cleared with this command.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        deleted_count = 0

        try:
            recent_deleted = await interaction.channel.purge(
                limit=None,
                check=lambda message: message.created_at >= cutoff,
                bulk=True,
            )
            deleted_count += len(recent_deleted)

            old_messages = []
            async for message in interaction.channel.history(limit=None, before=cutoff):
                old_messages.append(message)

            for message in old_messages:
                try:
                    await message.delete()
                    deleted_count += 1
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    continue
        except discord.Forbidden:
            await interaction.followup.send(
                "I do not have permission to manage messages in this channel.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.followup.send(
                f"Failed to clear channel due to Discord error: {exc}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Channel clear completed. Deleted approximately **{deleted_count}** messages.",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="poll_reward",
        description="Reward winners of a native Discord poll (admin).",
    )
    @app_commands.describe(
        message_id="The Discord message ID containing the native poll",
        winning_option="Exact text of the winning option",
        reward="Coins to grant each winner",
    )
    async def poll_reward(
        self,
        interaction: discord.Interaction,
        message_id: str,
        winning_option: str,
        reward: int,
    ) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if reward <= 0:
            await interaction.response.send_message(
                "Reward must be a positive number of coins.",
                ephemeral=True,
            )
            return
        if not message_id.isdigit():
            await interaction.response.send_message(
                "message_id must be a numeric Discord message ID.",
                ephemeral=True,
            )
            return

        if interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server channel.",
                ephemeral=True,
            )
            return

        poll_message_id = int(message_id)
        try:
            poll_message = await interaction.channel.fetch_message(poll_message_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "Poll message not found in this channel.",
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to read this message.",
                ephemeral=True,
            )
            return

        await self._reward_poll_message(interaction, poll_message, winning_option, reward)

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="poll_reward_last",
        description="Reward winners from the latest native poll in this channel (admin).",
    )
    @app_commands.describe(
        winning_option="Exact text of the winning option",
        reward="Coins to grant each winner",
        scan_limit="How many recent messages to scan (10-200)",
    )
    async def poll_reward_last(
        self,
        interaction: discord.Interaction,
        winning_option: str,
        reward: int,
        scan_limit: app_commands.Range[int, 10, 200] = 100,
    ) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if reward <= 0:
            await interaction.response.send_message(
                "Reward must be a positive number of coins.",
                ephemeral=True,
            )
            return
        if interaction.channel is None:
            await interaction.response.send_message(
                "This command must be used in a server channel.",
                ephemeral=True,
            )
            return

        try:
            async for msg in interaction.channel.history(limit=scan_limit):
                if getattr(msg, "poll", None) is not None:
                    await self._reward_poll_message(interaction, msg, winning_option, reward)
                    return
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to read message history in this channel.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"No native poll found in the last {scan_limit} messages of this channel.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(AdminCog(bot, db))
