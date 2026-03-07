from __future__ import annotations

import discord
from discord.ext import commands

from bot.database import Database
from bot.services.achievements import (
    BASE_REWARDS,
    GLOBAL_THRESHOLDS,
    get_achievement_difficulties,
    get_achievement_names,
)


class AchievementsLiveBoardService:
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db

    @staticmethod
    def _embed_color_for_count(count: int) -> discord.Color:
        if count >= 10:
            return discord.Color.orange()
        if count >= 5:
            return discord.Color.purple()
        if count >= 3:
            return discord.Color.blue()
        return discord.Color.light_grey()

    @staticmethod
    def _tier_color_emoji(count: int) -> str:
        # Color follows tier milestones:
        # 0 -> grey, 1+ -> blue, 3+ -> purple, 5+ -> orange (10+ stays orange)
        if count >= 5:
            return "🟧"
        if count >= 3:
            return "🟪"
        if count >= 1:
            return "🟦"
        return "⬜"

    @staticmethod
    def _next_threshold(count: int) -> int:
        for threshold in GLOBAL_THRESHOLDS:
            if count < threshold:
                return threshold
        return GLOBAL_THRESHOLDS[-1]

    async def _unlocker_label(self, game_id: str) -> str:
        discord_user_id = self.db.get_discord_user_id_by_game_player_id(game_id)
        if discord_user_id is None:
            return f"`{game_id}`"
        user = self.bot.get_user(discord_user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(discord_user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                user = None
        if user is None:
            return f"`{game_id}`"
        return f"`{user.display_name}`"

    async def _build_live_board_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Achievements Live Tracking",
            description=(
                "Unlock achievements as a community, so the entire community receives coins.\nThe more people unlocking the achievements, the bigger the rewards gets"
            ),
            color=discord.Color.blurple(),
        )
        for achievement_name in get_achievement_names():
            rows: list[str] = []
            difficulties = get_achievement_difficulties(achievement_name)
            for difficulty in difficulties:
                achievement_id = f"{achievement_name}:{difficulty}"
                completion_count = self.db.get_achievement_completion_count(achievement_id)
                unlockers = self.db.get_achievement_unlocker_game_ids(achievement_id)
                next_threshold = self._next_threshold(completion_count)
                next_reward = int(
                    BASE_REWARDS.get(achievement_name, {}).get(difficulty, {}).get(next_threshold, 0)
                )
                if unlockers:
                    labels = [await self._unlocker_label(game_id) for game_id in unlockers]
                    unlockers_line = ", ".join(labels)
                else:
                    unlockers_line = "None yet"
                rows.append(
                    f"{self._tier_color_emoji(completion_count)} **{difficulty}** | "
                    f"Current completions: **{completion_count}/{next_threshold}** | "
                    f"Next reward: 🪙 **{next_reward}** | "
                    f"Unlocked by: {unlockers_line}"
                )

            value = "\n".join(rows) if rows else "No configured difficulties."
            embed.add_field(
                name=f"{achievement_name}",
                value=value[:1024],
                inline=False,
            )
        return embed

    def _build_global_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Achievements Live Tracking",
            description="Preparing live achievements board...",
            color=discord.Color.blurple(),
        )

    async def _resolve_channel(self) -> discord.TextChannel | None:
        channel_id, _, is_active = self.db.get_achievements_live_board_config()
        if not is_active or channel_id <= 0:
            return None
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None
        return channel if isinstance(channel, discord.TextChannel) else None

    async def start(self, channel: discord.TextChannel) -> int:
        global_message = await channel.send(embed=self._build_global_embed())
        await global_message.edit(embed=await self._build_live_board_embed())
        try:
            await global_message.pin()
        except (discord.Forbidden, discord.HTTPException):
            pass
        self.db.clear_achievements_live_board_messages()
        self.db.set_achievements_live_board_config(
            channel_id=int(channel.id),
            global_message_id=int(global_message.id),
            is_active=True,
        )
        return int(global_message.id)

    def stop(self) -> None:
        channel_id, global_message_id, _ = self.db.get_achievements_live_board_config()
        self.db.set_achievements_live_board_config(
            channel_id=channel_id,
            global_message_id=global_message_id,
            is_active=False,
        )

    def reset(self) -> None:
        channel_id, _, is_active = self.db.get_achievements_live_board_config()
        self.db.reset_achievements_progress()
        self.db.clear_achievements_live_board_messages()
        self.db.set_achievements_live_board_config(
            channel_id=channel_id,
            global_message_id=0,
            is_active=is_active,
        )

    async def on_achievement_processed(
        self,
        achievement_id: str,
        game_player_id: str,
        completion_count: int,
    ) -> None:
        channel = await self._resolve_channel()
        if channel is None:
            return

        _, global_message_id, _ = self.db.get_achievements_live_board_config()
        if global_message_id > 0:
            try:
                global_message = await channel.fetch_message(global_message_id)
                await global_message.edit(embed=await self._build_live_board_embed())
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                replacement = await channel.send(embed=await self._build_live_board_embed())
                self.db.set_achievements_live_board_config(
                    channel_id=int(channel.id),
                    global_message_id=int(replacement.id),
                    is_active=True,
                )

        discord_user_id = self.db.get_discord_user_id_by_game_player_id(game_player_id)
        mention = f"<@{discord_user_id}>" if discord_user_id is not None else f"`{game_player_id}`"
        await channel.send(
            f"Congratulations {mention} for unlocking **{achievement_id}**! "
            f"(completion #{completion_count})"
        )
