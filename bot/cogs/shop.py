from __future__ import annotations

import copy
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.utils.admin_checks import has_admin_role
from bot.utils.shop_rewards import ShopRewardsStore

MASTERY_CHARACTERS = [
    "Kahnan",
    "Alexander",
    "Srug",
    "Marcus",
    "Nagini",
    "Subrog",
    "NeedleJack",
    "Iztac",
    "Bulgor",
    "Oswen",
    "Lionel",
]


def _price_color(price: int) -> discord.Color:
    if price < 500:
        return discord.Color.blue()
    if price < 2000:
        return discord.Color.blurple()
    return discord.Color.orange()


def _is_mastery_choice_reward(reward: dict[str, Any]) -> bool:
    """True if this reward is Mastery I/II/III and has character 'any' (player must choose)."""
    payload = reward.get("payload") or {}
    mastery = payload.get("Mastery") if isinstance(payload, dict) else None
    if not isinstance(mastery, dict):
        return False
    return str(mastery.get("character", "")).strip().lower() == "any"


class MasteryCharacterSelectView(discord.ui.View):
    """View with a dropdown to choose character for Mastery reward, then completes purchase."""

    def __init__(self, cog: "ShopCog", reward: dict[str, Any], user_id: int, *, timeout: float = 300.0) -> None:
        super().__init__(timeout=timeout)
        self.cog = cog
        self.reward = reward
        self.user_id = user_id
        options = [
            discord.SelectOption(label=name, value=name, description=f"Mastery for {name}")
            for name in MASTERY_CHARACTERS
        ]
        select = discord.ui.Select(
            placeholder="Choose character for your Mastery",
            options=options,
            custom_id="mastery_character_select",
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This selection is not yours.",
                ephemeral=True,
            )
            return
        selected_character = interaction.data.get("values", [None])[0] if interaction.data else None
        if not selected_character or selected_character not in MASTERY_CHARACTERS:
            await interaction.response.send_message(
                "Invalid character. Please try again.",
                ephemeral=True,
            )
            return

        payload = copy.deepcopy(dict(self.reward["payload"]))
        if isinstance(payload.get("Mastery"), dict):
            payload["Mastery"] = {**payload["Mastery"], "character": selected_character}

        reward_name = str(self.reward["name"])
        status, balance, reward_id = self.cog.db.purchase_shop_reward(
            discord_user_id=int(interaction.user.id),
            reward_key=str(self.reward["key"]),
            price=int(self.reward["price"]),
            reward_payload=payload,
            mark_collected=False,
        )

        if status == "missing_link":
            await interaction.response.edit_message(
                content="You need to run `/join` first to get your `gamer_id`.",
                view=None,
            )
            return
        if status == "already_purchased":
            await interaction.response.edit_message(
                content="You already bought this reward. Only one purchase per player is allowed.",
                view=None,
            )
            return
        if status == "insufficient_coins":
            await interaction.response.edit_message(
                content=f"Not enough coins. Current balance: **{balance or 0}**.",
                view=None,
            )
            return
        if status != "purchased":
            await interaction.response.edit_message(
                content="Purchase is currently unavailable. Please try again later.",
                view=None,
            )
            return

        await interaction.response.edit_message(
            content=(
                f"Purchase confirmed for **{reward_name}** (character: **{selected_character}**).\n"
                f"Remaining balance: **{balance or 0}** coins.\n"
                f"Your reward was added to your game account (ID: `{reward_id}`)."
            ),
            view=None,
        )


class RewardBuyButton(discord.ui.Button["RewardBuyView"]):
    def __init__(self, reward_key: str) -> None:
        super().__init__(
            label="Buy",
            style=discord.ButtonStyle.success,
            custom_id=f"shop_buy:{reward_key}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not isinstance(self.view, RewardBuyView):
            await interaction.response.send_message(
                "Shop view unavailable. Please retry.",
                ephemeral=True,
            )
            return
        await self.view.handle_buy(interaction)


class RewardBuyView(discord.ui.View):
    def __init__(self, cog: "ShopCog", reward: dict[str, Any]) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.reward = reward
        self.add_item(RewardBuyButton(str(reward["key"])))

    async def handle_buy(self, interaction: discord.Interaction) -> None:
        reward_name = str(self.reward["name"])
        is_unique_style_reward = reward_name.lower().startswith("unique ")
        is_mastery_choice = _is_mastery_choice_reward(self.reward)

        if is_mastery_choice:
            if self.cog.db.get_game_player_id(interaction.user.id) is None:
                await interaction.response.send_message(
                    "You need to run `/join` first to get your `gamer_id`.",
                    ephemeral=True,
                )
                return
            if self.cog.db.has_purchased_shop_reward(interaction.user.id, str(self.reward["key"])):
                await interaction.response.send_message(
                    "You already bought this reward. Only one purchase per player is allowed.",
                    ephemeral=True,
                )
                return
            price = int(self.reward["price"])
            if self.cog.db.get_balance(interaction.user.id) < price:
                await interaction.response.send_message(
                    f"Not enough coins. Current balance: **{self.cog.db.get_balance(interaction.user.id)}**.",
                    ephemeral=True,
                )
                return
            view = MasteryCharacterSelectView(
                self.cog,
                self.reward,
                interaction.user.id,
            )
            await interaction.response.send_message(
                f"Choose the character for **{reward_name}**:",
                view=view,
                ephemeral=True,
            )
            return

        status, balance, reward_id = self.cog.db.purchase_shop_reward(
            discord_user_id=int(interaction.user.id),
            reward_key=str(self.reward["key"]),
            price=int(self.reward["price"]),
            reward_payload=dict(self.reward["payload"]),
            mark_collected=is_unique_style_reward,
        )

        if status == "missing_link":
            await interaction.response.send_message(
                "You need to run `/join` first to get your `gamer_id`.",
                ephemeral=True,
            )
            return
        if status == "already_purchased":
            await interaction.response.send_message(
                "You already bought this reward. Only one purchase per player is allowed.",
                ephemeral=True,
            )
            return
        if status == "insufficient_coins":
            await interaction.response.send_message(
                f"Not enough coins. Current balance: **{balance or 0}**.",
                ephemeral=True,
            )
            return
        if status != "purchased":
            await interaction.response.send_message(
                "Purchase is currently unavailable. Please try again later.",
                ephemeral=True,
            )
            return

        if is_unique_style_reward:
            await interaction.response.send_message(
                f"Congratulations {interaction.user.mention}: you've earned **{reward_name}** — "
                "please contact @edebaze to discuss the kind of reward you would like.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Purchase confirmed for **{reward_name}**.\n"
            f"Remaining balance: **{balance or 0}** coins.\n"
            f"Your reward was added to your game account (ID: `{reward_id}`).",
            ephemeral=True,
        )


class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database) -> None:
        self.bot = bot
        self.db = db
        self.store = ShopRewardsStore()
        self._reward_by_key: dict[str, dict[str, Any]] = {}
        self._register_shop_views()

    def _load_rewards(self) -> list[dict[str, Any]]:
        rewards = self.store.get_rewards()
        self._reward_by_key = {str(item["key"]): item for item in rewards}
        return rewards

    def _register_shop_views(self) -> None:
        try:
            rewards = self._load_rewards()
        except (ValueError, OSError):
            return
        for reward in rewards:
            self.bot.add_view(RewardBuyView(self, reward))

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(
        name="start_rewards",
        description="Publish shop rewards with purchase buttons (admin).",
    )
    async def start_rewards(self, interaction: discord.Interaction) -> None:
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
            rewards = self._load_rewards()
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        except OSError as exc:
            await interaction.response.send_message(
                f"Unable to read data/rewards.json: {exc}",
                ephemeral=True,
            )
            return

        if not rewards:
            await interaction.response.send_message(
                "No rewards found in `data/rewards.json`.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        intro = discord.Embed(
            title="Shop Rewards",
            description=(
                "Click **Buy** to purchase a reward.\n"
                "Each reward is unique: one purchase maximum per player."
            ),
            color=discord.Color.blurple(),
        )
        intro_message = await interaction.channel.send(embed=intro)
        try:
            await intro_message.pin()
        except (discord.Forbidden, discord.HTTPException):
            pass

        for reward in rewards:
            price = int(reward["price"])
            embed = discord.Embed(
                title=str(reward["name"]),
                description=str(reward["description"]),
                color=_price_color(price),
            )
            embed.add_field(name="Price", value=f"**{price}** coins", inline=True)
            embed.add_field(name="Type", value="Unique purchase", inline=True)
            await interaction.channel.send(embed=embed, view=RewardBuyView(self, reward))

        await interaction.followup.send(
            f"Shop published in {interaction.channel.mention} with **{len(rewards)}** rewards.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    db: Database = bot.db
    await bot.add_cog(ShopCog(bot, db))
