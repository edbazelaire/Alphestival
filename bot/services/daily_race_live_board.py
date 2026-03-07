from __future__ import annotations

import discord
from discord.ext import commands

from bot.database import Database


class DailyRaceLiveBoardService:
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db

    async def _resolve_channel(self) -> discord.TextChannel | None:
        channel_id, _, is_active = self.db.get_daily_race_live_board_config()
        if not is_active or channel_id <= 0:
            return None
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _player_name(self, game_player_id: str) -> str:
        discord_user_id = self.db.get_discord_user_id_by_game_player_id(game_player_id)
        if discord_user_id is None:
            return "Unknown player"
        user = self.bot.get_user(discord_user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(discord_user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return "Unknown player"
        return str(user.display_name)

    async def _build_live_board_embed(self) -> discord.Embed:
        rows = self.db.get_daily_race_top(limit=10)
        if not rows:
            description = "No racers yet. Be the first to collect your daily reward."
        else:
            lines: list[str] = []
            for idx, row in enumerate(rows, start=1):
                name = await self._player_name(str(row["game_player_id"]))
                lines.append(
                    f"{idx}. **{name}** - {int(row['points'])} pts "
                    f"(streak: {int(row['current_streak'])}, collects: {int(row['total_collects'])})"
                )
            description = "\n".join(lines)
        return discord.Embed(
            title="Daily Race - Top 10",
            description=description,
            color=discord.Color.blurple(),
        )

    async def start(self, channel: discord.TextChannel) -> int:
        message = await channel.send(
            content="Daily race is starting! Top 10 racers:",
            embed=await self._build_live_board_embed(),
        )
        try:
            await message.pin()
        except (discord.Forbidden, discord.HTTPException):
            pass
        self.db.set_daily_race_live_board_config(
            channel_id=int(channel.id),
            message_id=int(message.id),
            is_active=True,
        )
        return int(message.id)

    def reset(self) -> None:
        self.db.reset_daily_race()

    async def refresh_board(self) -> None:
        channel = await self._resolve_channel()
        if channel is None:
            return

        _, message_id, _ = self.db.get_daily_race_live_board_config()
        if message_id > 0:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(
                    content="Daily race is running! Top 10 racers:",
                    embed=await self._build_live_board_embed(),
                )
                return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        replacement = await channel.send(
            content="Daily race is running! Top 10 racers:",
            embed=await self._build_live_board_embed(),
        )
        self.db.set_daily_race_live_board_config(
            channel_id=int(channel.id),
            message_id=int(replacement.id),
            is_active=True,
        )

    async def announce_collection(
        self,
        game_player_id: str,
        points_awarded: int,
        coins_awarded: int,
        streak: int,
    ) -> None:
        channel = await self._resolve_channel()
        if channel is None:
            return
        player_name = await self._player_name(game_player_id)
        if streak > 0:
            line = f"{player_name} has collected his daily reward for {streak} weeks in a row"
        else:
            line = f"{player_name} has collected his daily reward"
        await channel.send(f"{line}\n+{points_awarded} point | +{coins_awarded} :coin:")
