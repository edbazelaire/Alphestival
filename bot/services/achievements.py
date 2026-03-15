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
        "Brutal":   {1: 10, 3: 20, 5: 30, 10: 60, 15: 90, 25: 120, 50: 150, 100: 200},
        "Torment":  {1: 20, 3: 30, 5: 40, 10: 80, 15: 120, 25: 150, 50: 200, 100: 250},
        "Infernal": {1: 30, 3: 45, 5: 60, 10: 120, 15: 180, 25: 225, 50: 275, 100: 325},
    },
    "Dicey": {
        "Brutal":   {1: 25, 3: 40, 5: 55, 10: 110, 15: 165, 25: 220, 50: 275, 100: 330},
        "Torment":  {1: 40, 3: 60, 5: 80, 10: 160, 15: 240, 25: 300, 50: 350, 100: 400},
        "Infernal": {1: 60, 3: 85, 5: 110, 10: 220, 15: 330, 25: 400, 50: 450, 100: 500},
    },
    "FrozenHeart": {
        "Brutal":   {1: 25, 3: 40, 5: 55, 10: 110, 15: 165, 25: 220, 50: 275, 100: 330},
        "Torment":  {1: 40, 3: 60, 5: 80, 10: 160, 15: 240, 25: 300, 50: 350, 100: 400},
        "Infernal": {1: 60, 3: 85, 5: 110, 10: 220, 15: 330, 25: 400, 50: 450, 100: 500},
    },
    "HardCold": {
        "Brutal":   {1: 25, 3: 40, 5: 55, 10: 110, 25: 165, 50: 220},
        "Torment":  {1: 40, 3: 60, 5: 80, 10: 160, 25: 240, 50: 300},
        "Infernal": {1: 60, 3: 85, 5: 110, 10: 220, 25: 330, 50: 400},
    },
    "LegendOfTheNorth": {
        "Brutal":   {1: 100, 3: 200, 5: 300, 10: 500, 25: 800, 50: 1000},
        "Torment":  {1: 200, 3: 300, 5: 400, 10: 800, 25: 1200, 50: 1500},
        "Infernal": {1: 300, 3: 400, 5: 500, 10: 1000, 25: 1500, 50: 2000},
    },

    "Eternal Menagerie": {
        "Brutal":   {1: 45, 3: 65, 5: 80, 10: 160, 15: 240, 25: 300, 50: 450, 100: 600},
        "Torment":  {1: 65, 3: 90, 5: 110, 10: 220, 15: 330, 25: 400, 50: 550, 100: 700},
        "Infernal": {1: 90, 3: 120, 5: 150, 10: 300, 15: 450, 25: 550, 50: 700, 100: 850},
    },
    "Randomicon": {
        "Brutal":   {1: 75,  3: 100, 5: 125, 10: 250, 25: 375, 50: 500},
        "Torment":  {1: 100, 3: 150, 5: 200, 10: 400, 25: 600, 50: 800},
        "Infernal": {1: 150, 3: 225, 5: 300, 10: 600, 25: 900, 50: 1200},
    },
    "CorruptedHeart": {
        "Brutal":   {1: 75,  3: 100, 5: 125, 10: 250, 25: 375, 50: 500},
        "Torment":  {1: 100, 3: 150, 5: 200, 10: 400, 25: 600, 50: 800},
        "Infernal": {1: 150, 3: 225, 5: 300, 10: 600, 25: 900, 50: 1200},
    },  
    "HardlyHuman": {
        "Brutal":   {1: 75,  3: 100, 5: 125, 10: 250, 25: 375, 50: 500},
        "Torment":  {1: 100, 3: 150, 5: 200, 10: 400, 25: 600, 50: 800},
        "Infernal": {1: 150, 3: 225, 5: 300, 10: 600, 25: 900, 50: 1200},
    },
    "ConquereorOfTheEternal": {
        "Brutal":   {1: 200, 3: 300, 5: 500, 10: 800, 25: 1000, 50: 1500},
        "Torment":  {1: 300, 3: 400, 5: 600, 10: 1000, 25: 1200, 50: 2000},
        "Infernal": {1: 400, 3: 500, 5: 700, 10: 1200, 25: 1500, 50: 3500},
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


# First tier reward (tier 1) in BASE_REWARDS; used as base for "unlock reward" (x10).
PLAYER_UNLOCK_REWARD_TIER = 1
PLAYER_UNLOCK_REWARD_MULTIPLIER = 10


def get_achievement_ids_to_increment(
    arena: str,
    difficulty: str,
    mods: tuple[str, ...],
) -> list[tuple[str, str, int]]:
    """
    Return achievement contexts to update for an event (arena, difficulty, mods).
    Includes base (arena, no mods) and each sub-context (arena, single mod) that
    exists in the catalog. Each item is (achievement_id, achievement_name, tier_1_reward).
    """
    if arena not in VALID_ARENAS:
        return []
    result: list[tuple[str, str, int]] = []
    seen_ids: set[str] = set()

    def add_if_valid(mods_key: tuple[str, ...]) -> None:
        name = ACHIEVEMENT_NAME_BY_KEY.get((arena, mods_key))
        if not name:
            return
        allowed = get_achievement_difficulties(name)
        if difficulty not in allowed:
            return
        aid = f"{name}:{difficulty}"
        if aid in seen_ids:
            return
        seen_ids.add(aid)
        tier_1 = int(BASE_REWARDS.get(name, {}).get(difficulty, {}).get(1, 0))
        result.append((aid, name, tier_1))

    add_if_valid(())  # base: arena + difficulty, no mods
    for mod in mods:
        add_if_valid((mod,))  # sub-context: arena + difficulty + single mod
    return result


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
    if canonical_id:
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
    # Full (arena, mods) not in catalog: use base (arena, no mods) as primary
    base_name = ACHIEVEMENT_NAME_BY_KEY.get((arena, ()))
    if not base_name:
        raise ValueError("invalid_achievement_combo")
    allowed_difficulties = get_achievement_difficulties(base_name)
    if difficulty not in allowed_difficulties:
        raise ValueError("invalid_difficulty_for_achievement")
    primary_id = f"{base_name}:{difficulty}"
    return AchievementInfo(
        achievement_id=primary_id,
        achievement_name=base_name,
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
    lines.append(
        "First-time unlock for achiever: **first reward (tier 1) × 10** (per achievement context)."
    )
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
