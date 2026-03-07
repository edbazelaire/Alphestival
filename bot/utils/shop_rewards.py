from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_SECTION_PRICES = [250, 1000, 2500]
DEFAULT_DESCRIPTION = "Exclusive community event reward."


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "reward"


class ShopRewardsStore:
    def __init__(self, file_path: str = "data/rewards.json") -> None:
        self.path = Path(file_path)

    def _load(self) -> list[Any]:
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("data/rewards.json must contain a list.")
        return data

    @staticmethod
    def _section_default_price(section_index: int) -> int:
        if section_index < len(DEFAULT_SECTION_PRICES):
            return DEFAULT_SECTION_PRICES[section_index]
        return DEFAULT_SECTION_PRICES[-1]

    @staticmethod
    def _build_payload(raw_payload: Any, reward_name: str) -> dict[str, Any]:
        if isinstance(raw_payload, dict):
            return raw_payload
        return {"ShopReward": [reward_name]}

    def get_rewards(self) -> list[dict[str, Any]]:
        raw_sections = self._load()
        rewards: list[dict[str, Any]] = []
        used_keys: set[str] = set()

        for section_index, section in enumerate(raw_sections):
            section_items = section if isinstance(section, list) else [section]
            default_price = self._section_default_price(section_index)

            for item in section_items:
                if isinstance(item, dict):
                    name = str(item.get("name", "")).strip()
                    if not name:
                        continue
                    try:
                        price = int(item.get("price", default_price))
                    except (TypeError, ValueError):
                        price = default_price
                    if price < 0:
                        price = 0
                    description = str(item.get("description", DEFAULT_DESCRIPTION)).strip()
                    if not description:
                        description = DEFAULT_DESCRIPTION
                    payload = self._build_payload(item.get("rewards"), name)
                elif isinstance(item, str):
                    name = item.strip()
                    if not name:
                        continue
                    price = default_price
                    description = DEFAULT_DESCRIPTION
                    payload = self._build_payload(None, name)
                else:
                    continue

                base_key = _slugify(name)
                key = base_key
                suffix = 2
                while key in used_keys:
                    key = f"{base_key}-{suffix}"
                    suffix += 1
                used_keys.add(key)

                rewards.append(
                    {
                        "key": key,
                        "name": name,
                        "price": price,
                        "description": description,
                        "payload": payload,
                    }
                )

        return rewards
