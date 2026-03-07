from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ACHIEVEMENTS_CATALOG: list[dict[str, Any]] = [
    {
        "name": "FrostArena",
        "arena": "FrostArena",
        "mods": (),
        "difficulties": ("Easy", "Normal", "Hard", "Painfull", "Brutal", "Torment", "Infernal"),
    },
    {
        "name": "Dicey",
        "arena": "FrostArena",
        "mods": ("Random",),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },
    {
        "name": "FrozenHeart",
        "arena": "FrostArena",
        "mods": ("NoDeath",),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },
    {
        "name": "HardCold",
        "arena": "FrostArena",
        "mods": ("HardCore",),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },
    {
        "name": "LegendOfTheNorth",
        "arena": "FrostArena",
        "mods": ("HardCore", "NoDeath", "Random"),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },

    {
        "name": "Eternal Menagerie",
        "arena": "EternalMenagerie",
        "mods": (),
        "difficulties": ("Easy", "Normal", "Hard", "Painfull", "Brutal", "Torment", "Infernal"),
    },
    {
        "name": "Randomicon",
        "arena": "EternalMenagerie",
        "mods": ("Random",),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },
    {
        "name": "CorruptedHeart",
        "arena": "EternalMenagerie",
        "mods": ("NoDeath",),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },
    {
        "name": "HardlyHuman",
        "arena": "EternalMenagerie",
        "mods": ("HardCore",),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },
    {
        "name": "ConquereorOfTheEternal",
        "arena": "EternalMenagerie",
        "mods": ("HardCore", "NoDeath", "Random"),
        "difficulties": ("Brutal", "Torment", "Infernal"),
    },
]

ACHIEVEMENT_NAME_BY_KEY = {
    (
        str(item["arena"]),
        tuple(sorted(str(mod) for mod in item["mods"])),
    ): str(item["name"])
    for item in ACHIEVEMENTS_CATALOG
}

VALID_ARENAS = {str(item["arena"]) for item in ACHIEVEMENTS_CATALOG}

ARENA_LABELS = {
    "FrostArena": "Frost Arena",
    "EternalMenagerie": "Eternal Menagerie",
}

# Reward table keyed by achievement name then difficulty.
BASE_REWARDS: dict[str, dict[str, dict[int, int]]] = {
    "FrostArena": {
        "Easy":     {1: 2, 3: 5, 5: 8, 10: 11},
        "Normal":   {1: 2, 3: 6, 5: 9, 10: 12},
        "Hard":     {1: 3, 3: 7, 5: 11, 10: 15},
        "Painfull": {1: 5, 3: 10, 5: 15, 10: 30},
        "Brutal":   {1: 10, 3: 20, 5: 30, 10: 60},
        "Torment":  {1: 20, 3: 30, 5: 40, 10: 80},
        "Infernal": {1: 30, 3: 45, 5: 60, 10: 120},
    },
    "Dicey": {
        "Brutal":   {1: 25, 3: 40, 5: 55, 10: 110},
        "Torment":  {1: 40, 3: 60, 5: 80, 10: 160},
        "Infernal": {1: 60, 3: 85, 5: 110, 10: 220},
    },
    "FrozenHeart": {
        "Brutal":   {1: 25, 3: 40, 5: 55, 10: 110},
        "Torment":  {1: 40, 3: 60, 5: 80, 10: 160},
        "Infernal": {1: 60, 3: 85, 5: 110, 10: 220},
    },
    "HardCold": {
        "Brutal":   {1: 25, 3: 40, 5: 55, 10: 110},
        "Torment":  {1: 40, 3: 60, 5: 80, 10: 160},
        "Infernal": {1: 60, 3: 85, 5: 110, 10: 220},
    },
    "LegendOfTheNorth": {
        "Brutal":   {1: 100, 3: 200, 5: 300, 10: 600},
        "Torment":  {1: 200, 3: 300, 5: 400, 10: 800},
        "Infernal": {1: 300, 3: 400, 5: 500, 10: 1000},
    },

    "Eternal Menagerie": {
        "Easy":     {1: 5,  3: 10, 5: 15, 10: 30},
        "Normal":   {1: 10, 3: 20, 5: 30, 10: 60},
        "Hard":     {1: 20, 3: 30, 5: 40, 10: 80},
        "Painfull": {1: 30, 3: 45, 5: 60, 10: 120},
        "Brutal":   {1: 45, 3: 65, 5: 80, 10: 160},
        "Torment":  {1: 65, 3: 90, 5: 110, 10: 220},
        "Infernal": {1: 90, 3: 120, 5: 150, 10: 300},
    },
    "Randomicon": {
        "Brutal":   {1: 75,  3: 100, 5: 125, 10: 250},
        "Torment":  {1: 100, 3: 150, 5: 200, 10: 400},
        "Infernal": {1: 150, 3: 225, 5: 300, 10: 600},
    },
    "CorruptedHeart": {
        "Brutal":   {1: 75,  3: 100, 5: 125, 10: 250},
        "Torment":  {1: 100, 3: 150, 5: 200, 10: 400},
        "Infernal": {1: 150, 3: 225, 5: 300, 10: 600},
    },
    "HardlyHuman": {
        "Brutal":   {1: 75,  3: 100, 5: 125, 10: 250},
        "Torment":  {1: 100, 3: 150, 5: 200, 10: 400},
        "Infernal": {1: 150, 3: 225, 5: 300, 10: 600},
    },
    "ConquereorOfTheEternal": {
        "Brutal":   {1: 100, 3: 200, 5: 300, 10: 600},
        "Torment":  {1: 200, 3: 300, 5: 400, 10: 800},
        "Infernal": {1: 300, 3: 400, 5: 500, 10: 1000},
    },
}

GLOBAL_THRESHOLDS = (1, 3, 5, 10)
# Second tier (1=first, 3=second, 5=third, 10=fourth)
PLAYER_UNLOCK_TIER = 3
ALLOWED_MODS = {"Random", "HardCore", "NoDeath"}


@dataclass(frozen=True)
class AchievementInfo:
    achievement_id: str  # per challenge + difficulty key
    achievement_name: str
    arena: str
    difficulty: str
    mods: tuple[str, ...]


def _normalize_arena(value: str) -> str:
    return value.strip()


def _normalize_difficulty(value: str) -> str:
    return value.strip()


def _normalize_mod(mod: str) -> str:
    return mod.strip()


def _normalize_mods(mods: list[str]) -> tuple[str, ...]:
    unique: list[str] = []
    for mod in mods:
        normalized = _normalize_mod(mod)
        if not normalized or normalized not in ALLOWED_MODS:
            continue
        if normalized not in unique:
            unique.append(normalized)
    unique.sort()
    return tuple(unique)


def _build_achievement_id(arena: str, difficulty: str, mods: tuple[str, ...]) -> str:
    key = (arena, tuple(sorted(mods)))
    achievement_name = ACHIEVEMENT_NAME_BY_KEY.get(key, "")
    if not achievement_name:
        return ""
    return f"{achievement_name}:{difficulty}"


def parse_achievement_info(event_data: dict[str, Any]) -> AchievementInfo:
    arena = _normalize_arena(str(event_data.get("arena", "")))
    difficulty = _normalize_difficulty(str(event_data.get("difficulty", "")))

    raw_mods = event_data.get("mods") or []
    mods: tuple[str, ...]
    if isinstance(raw_mods, list):
        mods = _normalize_mods([str(mod) for mod in raw_mods])
    else:
        mods = ()

    achievement_id_raw = str(event_data.get("achievement_id", "")).strip()
    if achievement_id_raw and (not arena or not difficulty):
        parts: list[str] = []
        if ":" in achievement_id_raw:
            p1, p2, tail = (achievement_id_raw.split(":", 2) + ["", ""])[:3]
            parts = [p1, p2, tail]
        elif "_" in achievement_id_raw:
            p1, p2, tail = (achievement_id_raw.split("_", 2) + ["", ""])[:3]
            parts = [p1, p2, tail]

        if len(parts) >= 2 and parts[0] and parts[1]:
            maybe_arena = _normalize_arena(parts[0])
            maybe_difficulty = _normalize_difficulty(parts[1])
            if not arena:
                arena = maybe_arena
            if not difficulty:
                difficulty = maybe_difficulty
            if not mods and len(parts) > 2 and parts[2]:
                parsed_mods = [piece for piece in parts[2].split("+") if piece.strip()]
                mods = _normalize_mods(parsed_mods)

    if arena not in VALID_ARENAS:
        raise ValueError("invalid_arena")
    canonical_id = _build_achievement_id(arena, difficulty, mods)
    if not canonical_id:
        raise ValueError("invalid_achievement_combo")
    achievement_name = canonical_id.split(":", 1)[0]
    allowed_difficulties = get_achievement_difficulties(achievement_name)
    if difficulty not in allowed_difficulties:
        raise ValueError("invalid_difficulty_for_achievement")

    return AchievementInfo(
        achievement_id=canonical_id,
        achievement_name=achievement_name,
        arena=arena,
        difficulty=difficulty,
        mods=mods,
    )


def reward_for_tier(arena: str, difficulty: str, tier: int) -> int:
    achievement_name = ACHIEVEMENT_NAME_BY_KEY.get((arena, tuple()))
    if achievement_name is None:
        return 0
    rewards = BASE_REWARDS.get(achievement_name, {}).get(difficulty, {})
    return int(rewards.get(tier, 0))


def compute_reward(arena: str, difficulty: str, tier: int, mods: tuple[str, ...]) -> int:
    achievement_name = ACHIEVEMENT_NAME_BY_KEY.get((arena, tuple(sorted(mods))))
    if achievement_name is None:
        return 0
    rewards = BASE_REWARDS.get(achievement_name, {}).get(difficulty, {})
    return int(rewards.get(tier, 0))


def completion_increment_for(difficulty: str, mods: tuple[str, ...]) -> int:
    _ = difficulty
    _ = mods
    return 1


def parse_achievement_id(achievement_id: str) -> tuple[str, str] | None:
    if ":" not in achievement_id:
        return None
    name, difficulty = achievement_id.rsplit(":", 1)
    if not name or not difficulty:
        return None
    return (name, difficulty)


def compute_global_reward_for_achievement_id(achievement_id: str, tier: int) -> int:
    parsed = parse_achievement_id(achievement_id)
    if parsed is None:
        return 0
    achievement_name, difficulty = parsed
    meta = get_achievement_meta(achievement_name)
    if meta is None:
        return 0
    arena = str(meta["arena"])
    mods = tuple(str(mod) for mod in (meta.get("mods") or ()))
    return compute_reward(arena=arena, difficulty=difficulty, tier=tier, mods=mods)


def build_arena_reward_lines(arena: str) -> list[str]:
    challenge_name = "FrostArena" if arena == "FrostArena" else "Eternal Menagerie"
    difficulties = BASE_REWARDS.get(challenge_name, {})
    lines: list[str] = []
    for difficulty, rewards in difficulties.items():
        lines.append(
            f"`{difficulty}` | "
            f"T1:+{rewards.get(1, 0)} | "
            f"T3:+{rewards.get(3, 0)} | "
            f"T5:+{rewards.get(5, 0)} | "
            f"T10:+{rewards.get(10, 0)}"
        )
    return lines


def build_achievements_board_text() -> str:
    lines: list[str] = []
    lines.append("## Achievements Rewards")
    lines.append("Unlock tier for achiever: **Tier 5 reward**.")
    lines.append("Global rewards trigger at completions: **1 / 3 / 5 / 10**.")
    lines.append("Supported mods: **Random**, **HardCore**, **NoDeath**.")
    lines.append("")

    for arena_key, difficulties in BASE_REWARDS.items():
        arena_title = ARENA_LABELS.get(arena_key, arena_key)
        lines.append(f"### {arena_key} - {arena_title}")
        for _difficulty, rewards in difficulties.items():
            lines.append(
                f"- `{_difficulty}` -> "
                f"T1:+{rewards.get(1, 0)} | "
                f"T3:+{rewards.get(3, 0)} | "
                f"T5:+{rewards.get(5, 0)} | "
                f"T10:+{rewards.get(10, 0)}"
            )
        lines.append("")

    return "\n".join(lines).strip()


def get_achievement_names() -> list[str]:
    return [str(item["name"]) for item in ACHIEVEMENTS_CATALOG]


def get_achievement_meta(achievement_name: str) -> dict[str, Any] | None:
    for item in ACHIEVEMENTS_CATALOG:
        if str(item["name"]) == achievement_name:
            return item
    return None


def get_achievement_difficulties(achievement_name: str) -> tuple[str, ...]:
    meta = get_achievement_meta(achievement_name)
    if meta is None:
        return ()
    values = meta.get("difficulties", ())
    return tuple(str(value) for value in values)
