from __future__ import annotations

import json
from pathlib import Path

DEFAULT_DATA = {
    "rewards": [
        {"name": "Avatar Dragon", "coins": 150, "code": "DSQEAZED"},
        {"name": "Banner Phoenix", "coins": 400, "code": "PHX-2026-BANNER"},
    ]
}


class PrizesStore:
    def __init__(self, file_path: str = "data/community_prizes.json") -> None:
        self.path = Path(file_path)

    def ensure_exists(self) -> None:
        if self.path.exists():
            return
        self._save(DEFAULT_DATA)

    def _save(self, data: dict) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> dict:
        self.ensure_exists()
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("data/community_prizes.json must contain an object.")
        return data

    def get_rewards(self) -> list[dict[str, str | int]]:
        data = self._load()
        rewards_raw = data.get("rewards", [])
        if not isinstance(rewards_raw, list):
            return []

        rewards: list[dict[str, str | int]] = []
        for item in rewards_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            code = str(item.get("code", "")).strip()
            try:
                coins = int(item.get("coins", 0))
            except (TypeError, ValueError):
                coins = 0
            if name and coins > 0:
                rewards.append({"name": name, "coins": coins, "code": code})

        rewards.sort(key=lambda r: int(r["coins"]))
        return rewards
