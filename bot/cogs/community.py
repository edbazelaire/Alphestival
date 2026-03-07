from __future__ import annotations

import random
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.utils.admin_checks import has_admin_role
from bot.utils.prizes_store import PrizesStore


class TossDecisionView(discord.ui.View):
    def __init__(
        self,
        cog: "CommunityCog",
        user_id: int,
        base_amount: int,
        current_pot: int,
        toss_count: int,
        rewards: list[dict[str, str | int]],
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.cog = cog
        self.user_id = user_id
        self.base_amount = base_amount
        self.current_pot = current_pot
        self.toss_count = toss_count
        self.rewards = rewards

    async def _reject_other_user(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This toss game is not yours.",
                ephemeral=True,
            )
            return True
        return False

    @discord.ui.button(label="Donate to Community Pool", style=discord.ButtonStyle.success)
    async def donate(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if await self._reject_other_user(interaction):
            return
        await self.cog._toss_donate(
            interaction=interaction,
            user_id=self.user_id,
            amount=self.current_pot,
            toss_count=self.toss_count,
            rewards=self.rewards,
        )
        self.stop()

    @discord.ui.button(label="Toss Again", style=discord.ButtonStyle.primary)
    async def toss_again(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if await self._reject_other_user(interaction):
            return
        await self.cog._resolve_toss_round(
            interaction=interaction,
            user_id=self.user_id,
            base_amount=self.base_amount,
            pot=self.current_pot,
            toss_count=self.toss_count + 1,
            rewards=self.rewards,
            edit_message=True,
        )
        self.stop()

    async def on_timeout(self) -> None:
        # On timeout, return held pot to avoid accidental losses.
        self.cog.db.add_coins(self.user_id, self.current_pot)
        for child in self.children:
            child.disabled = True


class CommunityCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        self.prizes = PrizesStore()

    @staticmethod
    def _progress_bar(current: int, target: int, width: int = 20) -> str:
        if target <= 0:
            return "[]"
        ratio = max(0.0, min(1.0, current / target))
        filled = int(ratio * width)
        return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"

    @staticmethod
    def _tier_index_for_threshold(rewards: list[dict[str, str | int]], threshold: int) -> int:
        for idx, reward in enumerate(rewards, start=1):
            if int(reward["coins"]) == threshold:
                return idx
        return 0

    def _build_progress_embed(self, rewards: list[dict[str, str | int]]) -> discord.Embed:
        total = self.db.get_prize_total_coins()
        unlocked = self.db.get_unlocked_prize_thresholds()
        current_target = next((int(r["coins"]) for r in rewards if int(r["coins"]) > total), None)

        if current_target is None:
            next_prize_title = "All tiers unlocked"
            gauge_line = f"All tiers unlocked. Total contributed: **{total}** coins."
        else:
            bar = self._progress_bar(total, current_target)
            next_reward = next(r for r in rewards if int(r["coins"]) == current_target)
            next_prize_title = str(next_reward["name"])
            gauge_line = f"{bar} **{total}/{current_target}** coins"

        lines = []
        header = ""
        for idx, reward in enumerate(rewards, start=1):
            threshold = int(reward["coins"])
            if threshold in unlocked:
                code = str(reward["code"])
                lines.append(
                    f"{'✅':<2} | {f'Tier {idx}':<7} | {threshold:<7} |  {str(reward['name'])[:24]:<20} | {code[:16]:<9}"
                )
            else:
                lines.append(
                    f"{'🔒':<2} | {f'Tier {idx}':<7} | {threshold:<7} |  {str(reward['name'])[:24]:<20} | {'':<9}"
                )

        embed = discord.Embed(
            title="Community Prize Pool",
            description=f"**Next prize:** {next_prize_title}\n{gauge_line}",
            color=discord.Color.gold(),
        )
        tiers_block = "\n".join(lines) if lines else "No reward tiers configured."
        embed.add_field(
            name="Reward Tiers",
            value=f"```text\n{tiers_block}\n```",
            inline=False,
        )
        return embed

    async def _contributor_label(self, guild: discord.Guild | None, user_id: int) -> str:
        if guild is not None:
            member = guild.get_member(user_id)
            if member is not None:
                return member.display_name
        try:
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            return user.display_name
        except discord.HTTPException:
            return str(user_id)

    async def _top_contributors_lines(self, guild: discord.Guild | None) -> list[str]:
        rows = self.db.get_top_prize_contributors(limit=3)
        lines: list[str] = []
        for row in rows:
            user_id = int(row["user_id"])
            label = await self._contributor_label(guild, user_id)
            lines.append(f"- {label} : {row['total_contributed']} coins")
        return lines

    async def _ensure_and_update_pinned_messages(
        self,
        channel: Any,
        rewards: list[dict[str, str | int]],
    ) -> None:
        channel_id, unlocked_message_id, progress_message_id = self.db.get_prize_display_config()
        if channel_id != int(channel.id):
            progress_message_id = 0

        progress_message = None

        if progress_message_id:
            try:
                progress_message = await channel.fetch_message(progress_message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                progress_message = None

        if progress_message is None:
            progress_message = await channel.send(embed=self._build_progress_embed(rewards))
            try:
                await progress_message.pin()
            except (discord.Forbidden, discord.HTTPException):
                pass

        await progress_message.edit(content=None, embed=self._build_progress_embed(rewards))
        self.db.set_prize_display_config(
            channel_id=int(channel.id),
            unlocked_message_id=0,
            progress_message_id=int(progress_message.id),
        )

    async def _announce_new_unlocks(
        self,
        interaction: discord.Interaction,
        rewards: list[dict[str, str | int]],
        unlocked_now: list[dict[str, str | int]],
        total: int,
    ) -> None:
        for reward in unlocked_now:
            threshold = int(reward["coins"])
            tier_index = self._tier_index_for_threshold(rewards, threshold)
            code = str(reward.get("code", ""))
            unlock_message = (
                f"🎉🎉 Congratulations! You've unlocked a new reward for the community: "
                f"**{reward['name']}** (Tier {tier_index}).\n"
                f"Collect it using the code: `{code}`"
            )
            await interaction.followup.send(unlock_message)

    @staticmethod
    def _coin_icons(count: int, bad_last: bool = False) -> str:
        count = max(1, count)
        if count <= 12:
            if bad_last and count > 1:
                return ("🪙" * (count - 1)) + "🔴"
            if bad_last and count == 1:
                return "🔴"
            return "🪙" * count
        suffix = " (last roll failed)" if bad_last else ""
        return f"🪙 x{count}{suffix}"

    async def _toss_donate(
        self,
        interaction: discord.Interaction,
        user_id: int,
        amount: int,
        toss_count: int,
        rewards: list[dict[str, str | int]],
    ) -> None:
        total, unlocked_now = self.db.contribute_winnings_to_prize_pool(user_id, amount, rewards)
        user_total = self.db.get_user_prize_contribution(user_id)
        coins_icons = self._coin_icons(toss_count)

        await interaction.response.edit_message(
            content=(
                f"Congratulations <@{user_id}> adding **{amount}** coins to the pool! {coins_icons}\n"
                f"Pool total: **{total}** coins\n"
                f"Your total contribution: **{user_total}** coins"
            ),
            view=None,
        )

        if interaction.channel is not None:
            try:
                await self._ensure_and_update_pinned_messages(interaction.channel, rewards)
            except (discord.Forbidden, discord.HTTPException):
                pass

        await self._announce_new_unlocks(interaction, rewards, unlocked_now, total)

    async def _resolve_toss_round(
        self,
        interaction: discord.Interaction,
        user_id: int,
        base_amount: int,
        pot: int,
        toss_count: int,
        rewards: list[dict[str, str | int]],
        edit_message: bool,
    ) -> None:
        outcome = random.choice(("heads", "tails"))
        if outcome == "tails":
            total, unlocked_now = self.db.contribute_winnings_to_prize_pool(user_id, base_amount, rewards)
            if toss_count > 3:
                lose_line = f"Nice try <@{user_id}>, maybe next time... a bit too greedy 😅"
            else:
                lose_line = f"Nice try <@{user_id}>, maybe next time!"
            coins_icons = self._coin_icons(toss_count, bad_last=True)
            content = (
                f"⚫ Toss result: **TAILS**\n"
                f"{lose_line}\n"
                f"Initial amount **{base_amount}** coins is still donated to the pool.\n"
                f"{coins_icons}\n"
                f"Pool total: **{total}** coins"
            )
            if edit_message:
                await interaction.response.edit_message(content=content, view=None)
            else:
                await interaction.response.send_message(content)

            if interaction.channel is not None:
                try:
                    await self._ensure_and_update_pinned_messages(interaction.channel, rewards)
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await self._announce_new_unlocks(interaction, rewards, unlocked_now, total)
            return

        new_pot = pot * 2
        view = TossDecisionView(
            cog=self,
            user_id=user_id,
            base_amount=base_amount,
            current_pot=new_pot,
            toss_count=toss_count,
            rewards=rewards,
        )
        content = (
            f"🟡 Toss result: **HEADS**\n"
            f"Your pot is now **{new_pot}** coins.\n"
            "Choose to donate this amount to the community pool or toss again."
        )
        if edit_message:
            await interaction.response.edit_message(content=content, view=view)
        else:
            await interaction.response.send_message(content, view=view)

    @app_commands.command(name="toss", description="Heads/tails streak game for community pool donations.")
    @app_commands.describe(coins="Starting coins for the toss streak")
    async def toss(self, interaction: discord.Interaction, coins: int) -> None:
        if coins <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        rewards = self.prizes.get_rewards()
        if not rewards:
            await interaction.response.send_message(
                "No rewards configured in `data/community_prizes.json`.",
                ephemeral=True,
            )
            return

        if not self.db.remove_coins(interaction.user.id, coins):
            balance = self.db.get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"Not enough coins. You have **{balance}**.",
                ephemeral=True,
            )
            return

        await self._resolve_toss_round(
            interaction=interaction,
            user_id=interaction.user.id,
            base_amount=coins,
            pot=coins,
            toss_count=1,
            rewards=rewards,
            edit_message=False,
        )

    @app_commands.command(name="help", description="Show available commands for your role.")
    async def help(self, interaction: discord.Interaction) -> None:
        is_admin = has_admin_role(interaction)

        # Player categories (everyone)
        categories = [
            (
                "Economy",
                "• `/balance` — Show your coins\n• `/leaderboard` — Top coin holders",
            ),
            (
                "Account & in-game",
                "• `/join` — Generate your in-game player ID\n• `/set_parrain` — Set a sponsor code\n• `/daily_score` — Show your daily race score",
            ),
            (
                "Roulette",
                "• `/roulette_bet` — Place a bet in the current round\n• `/roulette_status` — Show pool and entries",
            ),
            (
                "Community",
                "• `/toss` — Heads/tails streak for community pool donations",
            ),
            (
                "General",
                "• `/help` — Show this command list",
            ),
        ]

        embed = discord.Embed(
            title="Bot Commands",
            description="Commands available to you, grouped by category.",
            color=discord.Color.blurple(),
        )
        for name, value in categories:
            embed.add_field(name=name, value=value, inline=False)

        if is_admin:
            admin_categories = [
                (
                    "Admin — Roulette",
                    "• `/roulette_open` — Open a new round\n• `/roulette_end` — Draw winner\n• `/roulette_set_index` — Set reward index",
                ),
                (
                    "Admin — Community & economy",
                    "• `/prize_reset` — Reset community prize pool\n• `/give_coins` — Add or remove coins from a user",
                ),
                (
                    "Admin — Rewards & shop",
                    "• `/clean_rewards` — Delete stored rewards for a player\n• `/start_rewards` — Publish shop rewards with buttons",
                ),
                (
                    "Admin — Daily questions",
                    "• `/start_daily_questions` — Start auto daily questions in channel\n• `/stop_daily_questions` — Stop scheduler\n• `/reset_daily_questions` — Stop and reset history (start from beginning)",
                ),
                (
                    "Admin — Moderation",
                    "• `/channel_clear` — Delete messages in this channel",
                ),
                (
                    "Admin — Polls",
                    "• `/poll_reward` — Reward winners of a Discord poll\n• `/poll_reward_last` — Reward from latest poll in channel",
                ),
                (
                    "Admin — Achievements",
                    "• `/achievements_publish` — Publish/refresh achievements board\n• `/achievements_refresh` — Refresh configured board\n• `/start_achievements` — Start live tracking\n• `/end_achievements` — Stop tracking\n• `/reset_achievements` — Reset progress",
                ),
                (
                    "Admin — Daily race",
                    "• `/start_daily_race` — Start daily race live board\n• `/reset_daily_race` — Reset scores and config",
                ),
            ]
            for name, value in admin_categories:
                embed.add_field(name=name, value=value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(CommunityCog(bot, db))
