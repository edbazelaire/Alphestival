from __future__ import annotations

import json
from pathlib import Path

from bot.database import Database


class RouletteRewardsStore:
    def __init__(
        self,
        db: Database,
        file_path: str = "data/rewards.json",
        min_price: int = 2500,
    ) -> None:
        self.db = db
        self.path = Path(file_path)
        self.min_price = max(0, int(min_price))

    def _load(self) -> list[dict[str, str]]:
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            rewards_raw = data.get("rewards", [])
        elif isinstance(data, list):
            rewards_raw = data
        else:
            raise ValueError("data/rewards.json must contain a list or an object with `rewards`.")

        cleaned: list[dict[str, str]] = []
        if not isinstance(rewards_raw, list):
            return cleaned
        for item in rewards_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            try:
                price = int(item.get("price", 0))
            except (TypeError, ValueError):
                price = 0
            if name and price >= self.min_price:
                cleaned.append({"name": name, "code": ""})
        return cleaned

    def get_rewards(self) -> list[dict[str, str]]:
        return self._load()

    def get_current_index(self) -> int:
        return self.db.get_roulette_reward_cursor()

    def set_current_index(self, index: int) -> int:
        rewards = self._load()
        if not rewards:
            raise ValueError(
                f"No roulette rewards configured in data/rewards.json with price >= {self.min_price}."
            )
        normalized = index % len(rewards)
        self.db.set_roulette_reward_cursor(normalized)
        return normalized

    def get_current_reward(self) -> tuple[int, str, str]:
        rewards = self._load()
        if not rewards:
            raise ValueError(
                f"No roulette rewards configured in data/rewards.json with price >= {self.min_price}."
            )
        idx = self.db.get_roulette_reward_cursor() % len(rewards)
        reward = rewards[idx]
        return (idx, reward["name"], reward.get("code", ""))

    def advance_index(self) -> int:
        rewards = self._load()
        if not rewards:
            raise ValueError(
                f"No roulette rewards configured in data/rewards.json with price >= {self.min_price}."
            )
        current = self.db.get_roulette_reward_cursor() % len(rewards)
        next_index = (current + 1) % len(rewards)
        self.db.set_roulette_reward_cursor(next_index)
        return next_index
