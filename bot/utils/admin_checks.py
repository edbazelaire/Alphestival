"""Shared admin checks for BotCasino. Admin commands are restricted to the role named \"admin\"."""

from __future__ import annotations

import discord

ADMIN_ROLE_NAME = "admin"


def has_admin_role(interaction: discord.Interaction) -> bool:
    """Return True if the user has a role named 'admin' (case-insensitive)."""
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False
    return any(r.name.lower() == ADMIN_ROLE_NAME for r in interaction.user.roles)
