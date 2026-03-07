from __future__ import annotations

import logging
from typing import Any

import discord
from discord.ext import commands

from bot.database import Database
from bot.services.achievements_live_board import AchievementsLiveBoardService
from bot.services.daily_race_live_board import DailyRaceLiveBoardService


class IngameEventAnnouncer:
    def __init__(
        self,
        bot: commands.Bot,
        db: Database,
        achievement_channel_id: int = 0,
    ) -> None:
        self.bot = bot
        self.db = db
        self.achievement_channel_id = max(0, achievement_channel_id)
        self.live_board = AchievementsLiveBoardService(bot=bot, db=db)
        self.daily_race_board = DailyRaceLiveBoardService(bot=bot, db=db)

    async def _resolve_channel(self, channel_id: int) -> discord.TextChannel | None:
        if channel_id <= 0:
            return None
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None
        if isinstance(channel, discord.TextChannel):
            return channel
        return None

    async def announce(
        self,
        event_type: str,
        game_player_id: str,
        result: dict[str, Any],
    ) -> None:
        try:
            if event_type == "achievement_unlocked":
                if bool(result.get("already_claimed", False)):
                    return
                if str(result.get("achievement_id", "")).strip() and int(
                    result.get("completion_count", 0) or 0
                ) > 0:
                    await self.live_board.on_achievement_processed(
                        achievement_id=str(result["achievement_id"]),
                        game_player_id=game_player_id,
                        completion_count=int(result.get("completion_count", 0) or 0),
                    )
                channel_id = (
                    self.db.get_ingame_event_channel_id("achievement_unlocked")
                    or self.achievement_channel_id
                )
                channel = await self._resolve_channel(channel_id)
                if channel is None:
                    return
                coins_awarded = int(result.get("coins_awarded", 0) or 0)
                global_reward = int(result.get("global_threshold_reward", 0) or 0)
                mods = result.get("mods") or []
                mods_label = "none" if not mods else ", ".join(str(mod) for mod in mods)

                embed = discord.Embed(
                    title="Achievement Unlocked",
                    description=f"A new achievement has been completed.",
                    color=discord.Color.green(),
                )
                embed.add_field(name="Arena", value=str(result.get("arena", "unknown")), inline=True)
                embed.add_field(name="Difficulty", value=str(result.get("difficulty", "unknown")), inline=True)
                if (mods_label != "none"):
                    embed.add_field(name="Mods", value=str(mods_label), inline=True)
                embed.add_field(name="Player Reward", value=f"+{coins_awarded} :coin:", inline=False)
                if global_reward > 0:
                    embed.add_field(
                        name="Global Reward",
                        value=f"+{global_reward} :coin: to everyone",
                        inline=True,
                    )
                await channel.send(embed=embed)
                return

            if event_type == "daily_reward_collected":
                if bool(result.get("already_collected_today", False)):
                    return

                points_awarded = int(result.get("points_awarded", 0) or 0)
                daily_coins = int(result.get("daily_coins_awarded", 0) or 0)
                streak = int(result.get("current_streak", 0) or 0)

                await self.daily_race_board.announce_collection(
                    game_player_id=game_player_id,
                    points_awarded=points_awarded,
                    coins_awarded=daily_coins,
                    streak=streak,
                )
                await self.daily_race_board.refresh_board()
                return
        except (discord.Forbidden, discord.HTTPException):
            logging.exception("Failed to send in-game event announcement.")
