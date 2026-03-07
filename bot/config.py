from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    discord_token: str
    discord_guild_id: int | None = None
    database_path: str = "botcasino.db"
    starting_coins: int = 100
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_shared_secret: str = ""
    dev_disable_signature: bool = False
    achievements_events_channel_id: int = 0
    daily_rewards_events_channel_id: int = 0
    referral_percent: int = 10


def load_settings() -> Settings:
    # Don't override env vars (e.g. Railway/Render) with .env file contents
    load_dotenv(override=False)

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "DISCORD_TOKEN is missing. Set it in your .env file (local) or as an "
            "environment variable (e.g. Railway Variables / Render Environment)."
        )

    guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id = int(guild_id_raw) if guild_id_raw else None
    database_path = os.getenv("DATABASE_PATH", "botcasino.db").strip() or "botcasino.db"
    starting_coins = int(os.getenv("STARTING_COINS", "100").strip() or "100")
    api_host = os.getenv("API_HOST", "0.0.0.0").strip() or "0.0.0.0"
    # Railway, Render, etc. set PORT; prefer it when present
    port_str = os.getenv("PORT", "").strip() or os.getenv("API_PORT", "8080").strip() or "8080"
    api_port = int(port_str)
    api_shared_secret = os.getenv("API_SHARED_SECRET", "").strip()
    dev_disable_signature = os.getenv("DEV_DISABLE_SIGNATURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    achievements_events_channel_id = int(
        os.getenv("ACHIEVEMENTS_EVENTS_CHANNEL_ID", "0").strip() or "0"
    )
    daily_rewards_events_channel_id = int(
        os.getenv("DAILY_REWARDS_CHANNEL_ID", "0").strip()
        or os.getenv("DAILY_REWARDS_EVENTS_CHANNEL_ID", "0").strip()
        or "0"
    )
    referral_percent = int(os.getenv("REFERRAL_PERCENT", "10").strip() or "10")
    referral_percent = max(0, min(100, referral_percent))

    return Settings(
        discord_token=token,
        discord_guild_id=guild_id,
        database_path=database_path,
        starting_coins=starting_coins,
        api_host=api_host,
        api_port=api_port,
        api_shared_secret=api_shared_secret,
        dev_disable_signature=dev_disable_signature,
        achievements_events_channel_id=achievements_events_channel_id,
        daily_rewards_events_channel_id=daily_rewards_events_channel_id,
        referral_percent=referral_percent,
    )
