from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from bot.database import Database
from bot.services.achievements import (
    GLOBAL_THRESHOLDS,
    PLAYER_UNLOCK_TIER,
    completion_increment_for,
    compute_reward,
    parse_achievement_info,
)


class IngameEventService:
    def __init__(self, db: Database, referral_percent: int = 10) -> None:
        self.db = db
        self.referral_percent = max(0, min(100, referral_percent))

    def _award_with_referral(self, game_player_id: str, coins: int) -> tuple[int, int]:
        if coins <= 0:
            return (0, 0)
        discord_user_id = self.db.get_discord_user_id_by_game_player_id(game_player_id)
        if discord_user_id is None:
            return (0, 0)

        self.db.add_coins(discord_user_id, coins)

        referral_bonus = 0
        referrer_game_id = self.db.get_referrer_game_player_id(game_player_id)
        if referrer_game_id:
            referrer_discord_id = self.db.get_discord_user_id_by_game_player_id(referrer_game_id)
            if referrer_discord_id is not None:
                referral_bonus = (coins * self.referral_percent) // 100
                if referral_bonus > 0:
                    self.db.add_coins(referrer_discord_id, referral_bonus)
        return (coins, referral_bonus)

    def process_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = str(payload.get("event_id", "")).strip()
        event_type = str(payload.get("event_type", "")).strip().lower()
        game_player_id = str(payload.get("player_game_id", "")).strip().upper()
        event_data = dict(payload.get("payload") or {})
        # Fallback: some games send event-specific data at top level
        for key in ("streak", "collect_day_utc"):
            if key not in event_data and key in payload:
                event_data[key] = payload[key]

        if not event_id or not event_type or not game_player_id:
            return {"accepted": False, "error": "missing_required_fields"}

        inserted = self.db.record_ingame_event(
            event_id=event_id,
            event_type=event_type,
            game_player_id=game_player_id,
            payload_json=json.dumps(event_data, separators=(",", ":"), ensure_ascii=True),
        )
        if not inserted:
            return {
                "accepted": True,
                "already_processed": True,
                "event_id": event_id,
            }

        if event_type == "achievement_unlocked":
            return self._process_achievement_event(event_id, game_player_id, event_data)
        if event_type == "daily_reward_collected":
            return self._process_daily_event(event_id, game_player_id, event_data)
        return {"accepted": True, "event_id": event_id, "event_type": event_type}

    def _process_achievement_event(
        self,
        event_id: str,
        game_player_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            achievement = parse_achievement_info(event_data)
        except ValueError as exc:
            return {"accepted": False, "event_id": event_id, "error": str(exc)}
        achievement_id = achievement.achievement_id

        if self.db.has_claimed_achievement(achievement_id, game_player_id):
            return {
                "accepted": True,
                "event_id": event_id,
                "already_claimed": True,
                "achievement_id": achievement_id,
            }

        final_reward = compute_reward(
            arena=achievement.arena,
            difficulty=achievement.difficulty,
            tier=PLAYER_UNLOCK_TIER,
            mods=achievement.mods,
        )

        earned, referral_bonus = self._award_with_referral(game_player_id, final_reward)
        self.db.mark_achievement_claimed(achievement_id, game_player_id)
        increment = completion_increment_for(
            difficulty=achievement.difficulty,
            mods=achievement.mods,
        )
        previous_count, completion_count = self.db.increment_achievement_completion_by(
            achievement_id,
            increment,
        )

        crossed_thresholds = [
            tier for tier in GLOBAL_THRESHOLDS if previous_count < tier <= completion_count
        ]

        newly_unlocked_thresholds: list[int] = []
        for tier in crossed_thresholds:
            if self.db.mark_global_threshold_unlocked(achievement_id, tier):
                newly_unlocked_thresholds.append(tier)

        threshold_reward = sum(
            compute_reward(
                arena=achievement.arena,
                difficulty=achievement.difficulty,
                tier=tier,
                mods=achievement.mods,
            )
            for tier in newly_unlocked_thresholds
        )
        global_reward_recipients = 0
        if threshold_reward > 0:
            # Reward everyone currently registered via /join (player_links).
            for linked_game_id in self.db.get_all_game_player_ids():
                linked_discord_user = self.db.get_discord_user_id_by_game_player_id(linked_game_id)
                if linked_discord_user is None:
                    continue
                self.db.add_coins(linked_discord_user, threshold_reward)
                global_reward_recipients += 1

        return {
            "accepted": True,
            "event_id": event_id,
            "achievement_id": achievement_id,
            "arena": achievement.arena,
            "difficulty": achievement.difficulty,
            "mods": list(achievement.mods),
            "count_increment": increment,
            "completion_count": completion_count,
            "coins_awarded": earned,
            "referral_bonus_awarded": referral_bonus,
            "global_threshold_reward": threshold_reward,
            "global_reward_recipients": global_reward_recipients,
            "crossed_thresholds": crossed_thresholds,
            "newly_unlocked_thresholds": newly_unlocked_thresholds,
        }

    def _process_daily_event(
        self,
        event_id: str,
        game_player_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        collect_day_raw = str(event_data.get("collect_day_utc") or "").strip()
        if not collect_day_raw:
            collect_day = datetime.now(timezone.utc).date().isoformat()
        else:
            try:
                # Support "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS" etc.
                parsed = datetime.fromisoformat(
                    collect_day_raw.replace("Z", "+00:00")
                )
                collect_day = parsed.date().isoformat()
            except ValueError:
                collect_day = datetime.now(timezone.utc).date().isoformat()

        raw_streak = event_data.get("streak", 1)
        try:
            current_streak = int(raw_streak)
        except (TypeError, ValueError):
            current_streak = 1
        current_streak = max(0, current_streak)

        inserted, current_streak, total_points, points_awarded = self.db.record_daily_collect(
            game_player_id,
            collect_day,
            current_streak,
        )
        if not inserted:
            return {
                "accepted": True,
                "event_id": event_id,
                "already_collected_today": True,
                "collect_day_utc": collect_day,
                "current_streak": current_streak,
                "total_points": total_points,
                "points_awarded": 0,
            }

        daily_coins = 15 * current_streak

        earned, referral_bonus = self._award_with_referral(game_player_id, daily_coins)

        return {
            "accepted": True,
            "event_id": event_id,
            "collect_day_utc": collect_day,
            "current_streak": current_streak,
            "points_awarded": points_awarded,
            "total_points": total_points,
            "daily_coins_awarded": earned,
            "referral_bonus_awarded": referral_bonus,
        }
