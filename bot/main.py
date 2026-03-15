from __future__ import annotations

import asyncio
import logging

import discord
import uvicorn
from discord import app_commands
from discord.ext import commands

from bot.api import create_api_app
from bot.config import load_settings
from bot.database import Database
from bot.services.event_announcer import IngameEventAnnouncer

COGS = [
    "bot.cogs.economy",
    "bot.cogs.betting",
    "bot.cogs.roulette",
    "bot.cogs.admin",
    "bot.cogs.shop",
    "bot.cogs.daily_questions",
    "bot.cogs.community",
    "bot.cogs.ingame",
]

ALLOWED_CATEGORY_NAME = "Alphestival"
COMMAND_CHANNEL_RULES: dict[str, str] = {
    "toss": "community-pool",
}


class CasinoCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        client = self.client
        if isinstance(client, CasinoBot):
            return await client._global_app_command_check(interaction)
        return True


class CasinoBot(commands.Bot):
    def __init__(self, db: Database, guild_id: int | None) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, tree_cls=CasinoCommandTree)
        self.db = db
        self.guild_id = guild_id

    @staticmethod
    def _resolve_category_name(channel: discord.abc.Snowflake | None) -> str:
        if isinstance(channel, discord.Thread):
            parent = channel.parent
            if isinstance(parent, discord.abc.GuildChannel) and parent.category is not None:
                return parent.category.name
            return ""
        if isinstance(channel, discord.abc.GuildChannel) and channel.category is not None:
            return channel.category.name
        return ""

    @staticmethod
    def _resolve_channel_name(channel: discord.abc.Snowflake | None) -> str:
        if isinstance(channel, discord.Thread):
            parent = channel.parent
            if isinstance(parent, discord.abc.GuildChannel):
                return parent.name
            return channel.name
        if isinstance(channel, discord.abc.GuildChannel):
            return channel.name
        return ""

    @staticmethod
    async def _deny_command(interaction: discord.Interaction, message: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
            return
        await interaction.response.send_message(message, ephemeral=True)

    async def _global_app_command_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.channel is None:
            await self._deny_command(
                interaction,
                "This bot can only be used inside the server, in the **Alphestival** section.",
            )
            return False

        category_name = self._resolve_category_name(interaction.channel)
        if category_name != ALLOWED_CATEGORY_NAME:
            await self._deny_command(
                interaction,
                "This bot is only accessible in the **Alphestival** section.",
            )
            return False

        command_name = interaction.command.qualified_name if interaction.command else ""
        required_channel = COMMAND_CHANNEL_RULES.get(command_name)
        if required_channel:
            channel_name = self._resolve_channel_name(interaction.channel)
            if channel_name != required_channel:
                await self._deny_command(
                    interaction,
                    f"The `/{command_name}` command is only available in **#{required_channel}**.",
                )
                return False

        return True

    async def setup_hook(self) -> None:
        for cog in COGS:
            await self.load_extension(cog)
        if self.guild_id is not None:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                await self.tree.sync(guild=guild)
                logging.info("Synced application commands to guild %s", self.guild_id)
                return
            except discord.Forbidden:
                logging.warning(
                    "Guild sync failed for guild %s (Missing Access). Falling back to global sync.",
                    self.guild_id,
                )
            except discord.HTTPException as exc:
                logging.warning(
                    "Guild sync failed for guild %s (%s). Falling back to global sync.",
                    self.guild_id,
                    exc,
                )
        await self.tree.sync()
        logging.info("Synced global application commands.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()

    db = Database(settings.database_path, starting_coins=settings.starting_coins)
    db.init_schema()
    if (
        db.get_ingame_event_channel_id("achievement_unlocked") <= 0
        and settings.achievements_events_channel_id > 0
    ):
        db.set_ingame_event_channel_id(
            "achievement_unlocked",
            settings.achievements_events_channel_id,
        )
    if (
        db.get_ingame_event_channel_id("daily_reward_collected") <= 0
        and settings.daily_rewards_events_channel_id > 0
    ):
        db.set_ingame_event_channel_id(
            "daily_reward_collected",
            settings.daily_rewards_events_channel_id,
        )
    bot = CasinoBot(db=db, guild_id=settings.discord_guild_id)
    announcer = IngameEventAnnouncer(
        bot=bot,
        db=db,
        achievement_channel_id=settings.achievements_events_channel_id,
    )
    app = create_api_app(db=db, settings=settings, announcer=announcer)
    api_config = uvicorn.Config(
        app=app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
    api_server = uvicorn.Server(config=api_config)

    bot_task = asyncio.create_task(bot.start(settings.discord_token))
    api_task = asyncio.create_task(api_server.serve())

    done, pending = await asyncio.wait(
        {bot_task, api_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    for task in done:
        exc = task.exception()
        if exc is not None:
            if task is api_task and (
                isinstance(exc, (OSError, SystemExit))
                or getattr(exc, "errno", None) == 10048
            ):
                logging.error(
                    "API server failed (often port in use). "
                    "Bind address: %s:%s — stop the other process or set API_PORT to another port.",
                    settings.api_host,
                    settings.api_port,
                )
            raise exc


if __name__ == "__main__":
    asyncio.run(main())
