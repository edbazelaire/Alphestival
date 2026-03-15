from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from bot.database import Database
from bot.services.achievements import (
    GLOBAL_THRESHOLDS,
    PLAYER_UNLOCK_REWARD_MULTIPLIER,
    compute_global_reward_for_achievement_id,
    get_achievement_ids_to_increment,
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

        # Sub-contexts: base (arena + difficulty) + each single mod; always increment all.
        to_increment = get_achievement_ids_to_increment(
            achievement.arena,
            achievement.difficulty,
            achievement.mods,
        )
        if not to_increment:
            return {"accepted": False, "event_id": event_id, "error": "no_achievement_context"}

        total_earned = 0
        total_referral = 0
        all_crossed: list[int] = []
        all_newly_unlocked: list[int] = []
        total_threshold_reward = 0
        completion_counts: dict[str, int] = {}

        for achievement_id, _achievement_name, tier_1_reward in to_increment:
            # First time for this player for this achievement_id: unlock reward = first tier × 10
            if not self.db.has_claimed_achievement(achievement_id, game_player_id):
                unlock_reward = tier_1_reward * PLAYER_UNLOCK_REWARD_MULTIPLIER
                earned, referral_bonus = self._award_with_referral(game_player_id, unlock_reward)
                total_earned += earned
                total_referral += referral_bonus
                self.db.mark_achievement_claimed(achievement_id, game_player_id)

            # Always increment global counter (even if player already did this before).
            previous_count, completion_count = self.db.increment_achievement_completion_by(
                achievement_id,
                1,
            )
            completion_counts[achievement_id] = completion_count

            crossed_thresholds = [
                t for t in GLOBAL_THRESHOLDS if previous_count < t <= completion_count
            ]
            newly_unlocked_thresholds: list[int] = []
            for tier in crossed_thresholds:
                if self.db.mark_global_threshold_unlocked(achievement_id, tier):
                    newly_unlocked_thresholds.append(tier)

            threshold_reward = sum(
                compute_global_reward_for_achievement_id(achievement_id, tier)
                for tier in newly_unlocked_thresholds
            )
            total_threshold_reward += threshold_reward
            all_crossed.extend(crossed_thresholds)
            all_newly_unlocked.extend(newly_unlocked_thresholds)

        # Grant global threshold rewards to everyone (once per linked player).
        global_reward_recipients = 0
        if total_threshold_reward > 0:
            for linked_game_id in self.db.get_all_game_player_ids():
                linked_discord_user = self.db.get_discord_user_id_by_game_player_id(linked_game_id)
                if linked_discord_user is None:
                    continue
                self.db.add_coins(linked_discord_user, total_threshold_reward)
                global_reward_recipients += 1

        primary_completion = completion_counts.get(achievement.achievement_id, 0)
        return {
            "accepted": True,
            "event_id": event_id,
            "achievement_id": achievement.achievement_id,
            "achievement_ids_updated": [aid for aid, _, _ in to_increment],
            "arena": achievement.arena,
            "difficulty": achievement.difficulty,
            "mods": list(achievement.mods),
            "completion_count": primary_completion,
            "completion_counts": completion_counts,
            "coins_awarded": total_earned,
            "referral_bonus_awarded": total_referral,
            "global_threshold_reward": total_threshold_reward,
            "global_reward_recipients": global_reward_recipients,
            "crossed_thresholds": all_crossed,
            "newly_unlocked_thresholds": all_newly_unlocked,
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

        # Award at least 25 coins per collect
        daily_coins = 25 * 2**(current_streak)

        earned, referral_bonus = self._award_with_referral(game_player_id, daily_coins)
        discord_linked = self.db.get_discord_user_id_by_game_player_id(game_player_id) is not None

        return {
            "accepted": True,
            "event_id": event_id,
            "collect_day_utc": collect_day,
            "current_streak": current_streak,
            "points_awarded": points_awarded,
            "total_points": total_points,
            "daily_coins_awarded": earned,
            "referral_bonus_awarded": referral_bonus,
            "discord_linked": discord_linked,
        }
