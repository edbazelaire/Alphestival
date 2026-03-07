from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.database import Database
from bot.utils.admin_checks import has_admin_role
from bot.utils.questions_store import DailyQuestion, QuestionsStore

ROTATION_HOURS = 24


class DailyQuestionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        self.store = QuestionsStore()
        self.scheduler_loop.start()

    def cog_unload(self) -> None:
        self.scheduler_loop.cancel()

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _poll_answer_text(answer: object) -> str:
        direct_text = getattr(answer, "text", None)
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()
        media = getattr(answer, "poll_media", None)
        media_text = getattr(media, "text", None)
        if isinstance(media_text, str) and media_text.strip():
            return media_text.strip()
        return ""

    async def _resolve_channel(self, channel_id: int) -> discord.TextChannel | None:
        if channel_id <= 0:
            return None
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _post_new_question(
        self,
        channel: discord.TextChannel,
        question_id: int,
        item: DailyQuestion,
        closes_at: datetime,
    ) -> int:
        closes_ts = int(closes_at.timestamp())
        poll = discord.Poll(
            question=item.question,
            duration=timedelta(hours=ROTATION_HOURS),
            multiple=False,
        )
        for option in item.options:
            poll.add_answer(text=option)
        message = await channel.send(
            content=(
                f"Daily Question #{question_id}\n"
                f"Reward: **+{item.reward}** coins per winner.\n"
                f"Closes <t:{closes_ts}:R>."
            ),
            poll=poll,
        )
        return int(message.id)

    async def _resolve_previous_poll(
        self,
        channel: discord.TextChannel,
        last_question_id: int,
        last_poll_message_id: int,
        correct_answer: str,
        reward_coins: int,
    ) -> tuple[int, int]:
        winner_ids: list[int] = []
        if last_poll_message_id > 0:
            try:
                poll_message = await channel.fetch_message(last_poll_message_id)
                poll = getattr(poll_message, "poll", None)
                if poll is not None:
                    target = self.db.normalize_answer(correct_answer)
                    selected_answer = None
                    for answer in list(getattr(poll, "answers", []) or []):
                        text = self._poll_answer_text(answer)
                        if self.db.normalize_answer(text) == target:
                            selected_answer = answer
                            break
                    if selected_answer is not None:
                        voters_method = getattr(selected_answer, "voters", None)
                        if voters_method is not None:
                            try:
                                async for user in voters_method(limit=None):
                                    if not user.bot:
                                        winner_ids.append(int(user.id))
                            except TypeError:
                                async for user in voters_method():
                                    if not user.bot:
                                        winner_ids.append(int(user.id))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                logging.warning(
                    "Failed to fetch/parse daily poll message %s for question %s.",
                    last_poll_message_id,
                    last_question_id,
                )

        unique_winners = list(dict.fromkeys(winner_ids))
        winner_count, total_payout = self.db.record_poll_reward(
            message_id=last_poll_message_id if last_poll_message_id > 0 else last_question_id,
            guild_id=int(channel.guild.id),
            channel_id=int(channel.id),
            winning_answer=correct_answer,
            reward_coins=reward_coins,
            winner_ids=unique_winners,
            awarded_by=int(self.bot.user.id) if self.bot.user is not None else 0,
        )
        return (winner_count, total_payout)

    async def _run_rotation(self, channel_id: int, force: bool = False) -> bool:
        questions = self.store.get_questions()
        if not questions:
            return False

        channel_id_cfg, is_active, current_index, last_question_id, last_poll_message_id, next_rotation_at = (
            self.db.get_daily_questions_scheduler_config()
        )
        if not force and not is_active:
            return False
        effective_channel_id = channel_id if channel_id > 0 else channel_id_cfg
        channel = await self._resolve_channel(effective_channel_id)
        if channel is None:
            return False

        if last_question_id > 0:
            with self.db.connection() as conn:
                row = conn.execute(
                    """
                    SELECT correct_answer, reward_coins, status
                    FROM questions
                    WHERE id = ?
                    """,
                    (last_question_id,),
                ).fetchone()
            if row is not None and str(row["status"]) == "open":
                correct_answer = str(row["correct_answer"] or "").strip()
                reward_coins = int(row["reward_coins"] or 0)
                self.db.resolve_question(last_question_id, correct_answer)
                winner_count, total_payout = await self._resolve_previous_poll(
                    channel=channel,
                    last_question_id=last_question_id,
                    last_poll_message_id=last_poll_message_id,
                    correct_answer=correct_answer,
                    reward_coins=reward_coins,
                )
                await channel.send(
                    f"Daily question #{last_question_id} closed.\n"
                    f"Correct answer: `{correct_answer}`\n"
                    f"Winners: **{winner_count}** | Total payout: **{total_payout}** coins."
                )

        idx = current_index % len(questions)
        item = questions[idx]
        question_id = self.db.create_question_with_answer(
            question_text=item.question,
            options=item.options,
            reward_coins=item.reward,
            correct_answer=item.answer,
        )
        next_rotation = self._now_utc() + timedelta(hours=ROTATION_HOURS)
        poll_message_id = await self._post_new_question(channel, question_id, item, next_rotation)
        self.db.set_daily_questions_scheduler_config(
            channel_id=int(channel.id),
            is_active=True,
            current_index=(idx + 1) % len(questions),
            last_question_id=question_id,
            last_poll_message_id=poll_message_id,
            next_rotation_at=next_rotation.isoformat(),
        )
        return True

    @tasks.loop(minutes=1)
    async def scheduler_loop(self) -> None:
        channel_id, is_active, _, _, _, next_rotation_at = self.db.get_daily_questions_scheduler_config()
        if not is_active:
            return
        next_rotation = self._parse_iso(next_rotation_at)
        if next_rotation is not None and self._now_utc() < next_rotation:
            return
        await self._run_rotation(channel_id=channel_id)

    @scheduler_loop.before_loop
    async def _before_scheduler_loop(self) -> None:
        await self.bot.wait_until_ready()

    async def start_in_channel(self, channel: discord.TextChannel) -> bool:
        """Start daily questions in the given channel (e.g. after reset_all). Returns True if started."""
        try:
            questions = self.store.get_questions()
        except (ValueError, OSError):
            return False
        if not questions:
            return False
        self.db.set_daily_questions_scheduler_config(
            channel_id=int(channel.id),
            is_active=True,
            current_index=0,
            last_question_id=0,
            last_poll_message_id=0,
            next_rotation_at=None,
        )
        return await self._run_rotation(channel_id=int(channel.id), force=True)

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="start_daily_questions",
        description="Start automatic daily questions in this channel (admin).",
    )
    async def start_daily_questions(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Use this command in a text channel.",
                ephemeral=True,
            )
            return

        try:
            questions = self.store.get_questions()
        except (ValueError, OSError) as exc:
            await interaction.response.send_message(
                f"Invalid `data/questions.json`: {exc}",
                ephemeral=True,
            )
            return
        if not questions:
            await interaction.response.send_message(
                "No valid entries found in `data/questions.json`.",
                ephemeral=True,
            )
            return

        _, _, current_index, last_question_id, last_poll_message_id, _ = (
            self.db.get_daily_questions_scheduler_config()
        )
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.db.set_daily_questions_scheduler_config(
            channel_id=int(interaction.channel.id),
            is_active=True,
            current_index=current_index,
            last_question_id=last_question_id,
            last_poll_message_id=last_poll_message_id,
            next_rotation_at=None,
        )
        rotated = await self._run_rotation(channel_id=int(interaction.channel.id), force=True)
        if not rotated:
            await interaction.followup.send(
                "Could not start daily questions. Check channel permissions and configuration.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            f"Daily questions started in {interaction.channel.mention} (rotation every {ROTATION_HOURS}h).",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="stop_daily_questions",
        description="Stop automatic daily questions scheduler (admin).",
    )
    async def stop_daily_questions(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        channel_id, _, current_index, last_question_id, last_poll_message_id, next_rotation_at = (
            self.db.get_daily_questions_scheduler_config()
        )
        self.db.set_daily_questions_scheduler_config(
            channel_id=channel_id,
            is_active=False,
            current_index=current_index,
            last_question_id=last_question_id,
            last_poll_message_id=last_poll_message_id,
            next_rotation_at=next_rotation_at,
        )
        await interaction.response.send_message(
            "Daily questions scheduler stopped.",
            ephemeral=True,
        )

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="reset_daily_questions",
        description="Stop daily questions and reset history to start from the beginning (admin).",
    )
    async def reset_daily_questions(self, interaction: discord.Interaction) -> None:
        if not has_admin_role(interaction):
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        self.db.set_daily_questions_scheduler_config(
            channel_id=0,
            is_active=False,
            current_index=0,
            last_question_id=0,
            last_poll_message_id=0,
            next_rotation_at=None,
        )
        await interaction.response.send_message(
            "Daily questions scheduler stopped and history reset. You can start from the beginning with `/start_daily_questions`.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(DailyQuestionsCog(bot, db))
