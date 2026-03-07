from __future__ import annotations

import secrets

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.utils.admin_checks import has_admin_role
from bot.services.achievements import (
    ARENA_LABELS,
    GLOBAL_THRESHOLDS,
    PLAYER_UNLOCK_TIER,
    build_arena_reward_lines,
    compute_global_reward_for_achievement_id,
)
from bot.services.achievements_live_board import AchievementsLiveBoardService
from bot.services.daily_race_live_board import DailyRaceLiveBoardService

GAME_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
GAME_ID_LENGTH = 8


def _generate_game_player_id() -> str:
    return "".join(secrets.choice(GAME_ID_ALPHABET) for _ in range(GAME_ID_LENGTH))


class IngameCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        self.achievements_live_board = AchievementsLiveBoardService(bot=bot, db=db)
        self.daily_race_live_board = DailyRaceLiveBoardService(bot=bot, db=db)

    def _create_unique_game_id(self) -> str:
        for _ in range(20):
            candidate = _generate_game_player_id()
            if self.db.get_discord_user_id_by_game_player_id(candidate) is None:
                return candidate
        raise RuntimeError("Unable to generate a unique game id.")

    @staticmethod
    def _build_achievements_embeds() -> list[discord.Embed]:
        intro = discord.Embed(
            title="Achievements Overview",
            description=(
                "Rewards for **FrostArena** and **EternalMenagerie**.\n"
                f"- Player unlock reward tier: **T{PLAYER_UNLOCK_TIER}**\n"
                f"- Global thresholds: **{' / '.join(str(t) for t in GLOBAL_THRESHOLDS)}** completions\n"
                "- Supported mods: Random, HardCore, NoDeath."
            ),
            color=discord.Color.blurple(),
        )

        arena_embeds: list[discord.Embed] = []
        for arena_key in ("FrostArena", "EternalMenagerie"):
            arena_title = ARENA_LABELS.get(arena_key, arena_key.upper())
            lines = build_arena_reward_lines(arena_key)
            rewards_embed = discord.Embed(
                title=f"{arena_key.upper()} - {arena_title}",
                description="\n".join(f"- {line}" for line in lines),
                color=discord.Color.gold(),
            )
            rewards_embed.set_footer(
                text="Format: T1 / T3 / T5 / T10 base rewards before mod multipliers."
            )
            arena_embeds.append(rewards_embed)

        return [intro, *arena_embeds]

    async def _upsert_achievements_board(
        self,
        channel: discord.TextChannel,
    ) -> discord.Message:
        _, message_id = self.db.get_achievements_display_config()
        embeds = self._build_achievements_embeds()

        message: discord.Message | None = None
        if message_id:
            try:
                maybe_message = await channel.fetch_message(message_id)
                message = maybe_message
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                message = None

        if message is None:
            message = await channel.send(content="Achievement rewards board", embeds=embeds)
            try:
                await message.pin()
            except (discord.Forbidden, discord.HTTPException):
                pass
        else:
            await message.edit(content="Achievement rewards board", embeds=embeds)

        self.db.set_achievements_display_config(
            channel_id=int(channel.id),
            message_id=int(message.id),
        )
        return message

    @app_commands.command(name="join", description="Generate your in-game ID for BotCasino.")
    async def join(self, interaction: discord.Interaction) -> None:
        existing = self.db.get_game_player_id(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"Your in-game ID is already set: `{existing}`",
                ephemeral=True,
            )
            return

        game_player_id = self._create_unique_game_id()
        created = self.db.create_player_link(interaction.user.id, game_player_id)
        if not created:
            current = self.db.get_game_player_id(interaction.user.id)
            if current:
                await interaction.response.send_message(
                    f"Your in-game ID is already set: `{current}`",
                    ephemeral=True,
                )
                return
            await interaction.response.send_message(
                "Could not create your in-game ID. Please retry.",
                ephemeral=True,
            )
            return

        retroactive_total = 0
        for row in self.db.get_all_unlocked_global_thresholds():
            achievement_id = str(row["achievement_id"])
            tier = int(row["threshold"])
            retroactive_total += compute_global_reward_for_achievement_id(achievement_id, tier)
        if retroactive_total > 0:
            self.db.add_coins(interaction.user.id, retroactive_total)

        await interaction.response.send_message(
            "Welcome! Use this ID in your Unity game:\n"
            f"`{game_player_id}`\n\n"
            "Keep it private if you don't want someone else to claim rewards for your account.\n"
            f"Retroactive global rewards granted: **+{retroactive_total}** coins.",
            ephemeral=True,
        )

    @app_commands.command(
        name="set_parrain",
        description="Set your referral sponsor using their in-game ID (one-time action).",
    )
    @app_commands.describe(referrer_game_id="The in-game ID shared by your sponsor")
    async def set_parrain(self, interaction: discord.Interaction, referrer_game_id: str) -> None:
        referrer_game_id = referrer_game_id.strip().upper()
        if len(referrer_game_id) < 4:
            await interaction.response.send_message("Invalid sponsor code.", ephemeral=True)
            return
        ok = self.db.set_referrer_for_user(interaction.user.id, referrer_game_id)
        if not ok:
            await interaction.response.send_message(
                "Unable to set sponsor. Check that:\n"
                "- you already ran `/join`\n"
                "- the code exists\n"
                "- this is not your own code\n"
                "- you did not already set a sponsor",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Sponsor set to `{referrer_game_id}`.",
            ephemeral=True,
        )

    @app_commands.command(
        name="daily_score",
        description="Show your daily race score.",
    )
    async def daily_score(self, interaction: discord.Interaction) -> None:
        game_player_id = self.db.get_game_player_id(interaction.user.id)
        if not game_player_id:
            await interaction.response.send_message(
                "You need to run `/join` first.",
                ephemeral=True,
            )
            return
        score = self.db.get_daily_race_score(game_player_id)
        if score is None:
            await interaction.response.send_message(
                "No daily race score yet. Collect your first daily reward in-game.",
                ephemeral=True,
            )
            return
        rank = self.db.get_daily_race_rank(game_player_id)
        await interaction.response.send_message(
            f"Your daily race stats:\n"
            f"- Points: **{int(score['points'])}**\n"
            f"- Rank: **#{rank or 1}**\n"
            f"- Current streak: **{int(score['current_streak'])}**\n"
            f"- Best streak: **{int(score['best_streak'])}**\n"
            f"- Total collects: **{int(score['total_collects'])}**",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="start_daily_race",
        description="Start daily race live board in this channel (admin).",
    )
    async def start_daily_race(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Use this command in a text channel.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        message_id = await self.daily_race_live_board.start(interaction.channel)
        await interaction.followup.send(
            f"Daily race live board started in {interaction.channel.mention} "
            f"(message `{message_id}`).",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="reset_daily_race",
        description="Reset daily race scores and board config (admin).",
    )
    async def reset_daily_race(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        self.daily_race_live_board.reset()
        await interaction.response.send_message(
            "Daily race scores and live board configuration were reset.",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="achievements_publish",
        description="Publish or refresh the achievements board in a channel (admin).",
    )
    @app_commands.describe(channel="Channel to host the achievements board")
    async def achievements_publish(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            message = await self._upsert_achievements_board(channel)
        except discord.Forbidden:
            await interaction.followup.send(
                "I do not have permission to post in that channel.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            f"Achievements board is now in {channel.mention} (message `{message.id}`).",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="achievements_refresh",
        description="Refresh the configured achievements board message (admin).",
    )
    async def achievements_refresh(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        channel_id, _ = self.db.get_achievements_display_config()
        if channel_id <= 0:
            await interaction.response.send_message(
                "No achievements board configured yet. Use `/achievements_publish` first.",
                ephemeral=True,
            )
            return
        channel = interaction.guild.get_channel(channel_id) if interaction.guild else None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Configured channel is unavailable. Run `/achievements_publish` again.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            message = await self._upsert_achievements_board(channel)
        except discord.Forbidden:
            await interaction.followup.send(
                "I do not have permission to update the configured channel.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            f"Achievements board refreshed (message `{message.id}`).",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="start_achievements",
        description="Start live achievements tracking in this channel (admin).",
    )
    async def start_achievements(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Use this command in a text channel.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        global_message_id = await self.achievements_live_board.start(interaction.channel)
        await interaction.followup.send(
            f"Live achievements started in {interaction.channel.mention} "
            f"(global message `{global_message_id}`).",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="end_achievements",
        description="Stop live achievements tracking (admin).",
    )
    async def end_achievements(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        self.achievements_live_board.stop()
        await interaction.response.send_message(
            "Live achievements tracking is now stopped.",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="reset_achievements",
        description="Reset live achievements progress and board pointers (admin).",
    )
    async def reset_achievements(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        self.achievements_live_board.reset()
        await interaction.response.send_message(
            "Achievements progress and live board message links were reset.",
            ephemeral=True,
        )

async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(IngameCog(bot, db))
