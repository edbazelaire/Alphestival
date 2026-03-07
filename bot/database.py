from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator
import json
import uuid


class Database:
    def __init__(self, path: str, starting_coins: int = 100) -> None:
        self.path = path
        self.starting_coins = starting_coins

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    coins INTEGER NOT NULL DEFAULT 100
                );

                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    correct_answer TEXT,
                    options TEXT NOT NULL DEFAULT '',
                    reward_coins INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    answer TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    FOREIGN KEY(question_id) REFERENCES questions(id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS question_votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(question_id, user_id),
                    FOREIGN KEY(question_id) REFERENCES questions(id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS roulette_rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'open',
                    reward_name TEXT NOT NULL DEFAULT '',
                    reward_code TEXT NOT NULL DEFAULT '',
                    reward_index INTEGER NOT NULL DEFAULT -1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS roulette_reward_cursor (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    current_index INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS roulette_bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    round_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    FOREIGN KEY(round_id) REFERENCES roulette_rounds(id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS poll_rewards (
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    winning_answer TEXT NOT NULL,
                    reward_coins INTEGER NOT NULL,
                    winner_count INTEGER NOT NULL,
                    total_payout INTEGER NOT NULL,
                    awarded_by INTEGER NOT NULL,
                    awarded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS community_prize_state (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    total_coins INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS community_prize_unlocks (
                    threshold_coins INTEGER PRIMARY KEY,
                    reward_name TEXT NOT NULL,
                    reward_code TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS community_prize_contributions (
                    user_id INTEGER PRIMARY KEY,
                    total_contributed INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS community_prize_display (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    channel_id INTEGER NOT NULL DEFAULT 0,
                    unlocked_message_id INTEGER NOT NULL DEFAULT 0,
                    progress_message_id INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS player_links (
                    discord_user_id INTEGER PRIMARY KEY,
                    game_player_id TEXT NOT NULL UNIQUE,
                    referrer_game_player_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ingame_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    game_player_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS achievement_progress (
                    achievement_id TEXT PRIMARY KEY,
                    completion_count INTEGER NOT NULL DEFAULT 0,
                    last_completed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS achievement_player_claims (
                    achievement_id TEXT NOT NULL,
                    game_player_id TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    PRIMARY KEY (achievement_id, game_player_id)
                );

                CREATE TABLE IF NOT EXISTS achievement_global_threshold_unlocks (
                    achievement_id TEXT NOT NULL,
                    threshold INTEGER NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    PRIMARY KEY (achievement_id, threshold)
                );

                CREATE TABLE IF NOT EXISTS daily_streaks (
                    game_player_id TEXT PRIMARY KEY,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    best_streak INTEGER NOT NULL DEFAULT 0,
                    last_collect_day TEXT,
                    total_collects INTEGER NOT NULL DEFAULT 0,
                    points INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS achievements_display (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    channel_id INTEGER NOT NULL DEFAULT 0,
                    message_id INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS achievements_live_board_config (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    channel_id INTEGER NOT NULL DEFAULT 0,
                    global_message_id INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS achievements_live_board_messages (
                    achievement_id TEXT PRIMARY KEY,
                    message_id INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS ingame_events_display (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    channel_id INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS ingame_event_channels (
                    event_type TEXT PRIMARY KEY,
                    channel_id INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS daily_race_live_board_config (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    channel_id INTEGER NOT NULL DEFAULT 0,
                    message_id INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS daily_questions_scheduler (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    channel_id INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    current_index INTEGER NOT NULL DEFAULT 0,
                    last_question_id INTEGER NOT NULL DEFAULT 0,
                    last_poll_message_id INTEGER NOT NULL DEFAULT 0,
                    next_rotation_at TEXT
                );

                CREATE TABLE IF NOT EXISTS player_rewards (
                    reward_id TEXT PRIMARY KEY,
                    gamer_id TEXT NOT NULL,
                    reward_json TEXT NOT NULL,
                    collected INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    collected_at TEXT
                );

                CREATE TABLE IF NOT EXISTS shop_reward_purchases (
                    gamer_id TEXT NOT NULL,
                    reward_key TEXT NOT NULL,
                    reward_id TEXT NOT NULL,
                    price_paid INTEGER NOT NULL DEFAULT 0,
                    purchased_at TEXT NOT NULL,
                    PRIMARY KEY (gamer_id, reward_key)
                );
                """
            )
            # Backward-compatible migration for older DBs created before options existed.
            question_columns = conn.execute("PRAGMA table_info(questions)").fetchall()
            if "options" not in {str(col["name"]) for col in question_columns}:
                conn.execute(
                    "ALTER TABLE questions ADD COLUMN options TEXT NOT NULL DEFAULT ''"
                )
            if "reward_coins" not in {str(col["name"]) for col in question_columns}:
                conn.execute(
                    "ALTER TABLE questions ADD COLUMN reward_coins INTEGER NOT NULL DEFAULT 0"
                )
            roulette_columns = conn.execute("PRAGMA table_info(roulette_rounds)").fetchall()
            roulette_column_names = {str(col["name"]) for col in roulette_columns}
            if "reward_name" not in roulette_column_names:
                conn.execute(
                    "ALTER TABLE roulette_rounds ADD COLUMN reward_name TEXT NOT NULL DEFAULT ''"
                )
            if "reward_code" not in roulette_column_names:
                conn.execute(
                    "ALTER TABLE roulette_rounds ADD COLUMN reward_code TEXT NOT NULL DEFAULT ''"
                )
            if "reward_index" not in roulette_column_names:
                conn.execute(
                    "ALTER TABLE roulette_rounds ADD COLUMN reward_index INTEGER NOT NULL DEFAULT -1"
                )
            daily_streak_columns = conn.execute("PRAGMA table_info(daily_streaks)").fetchall()
            if "points" not in {str(col["name"]) for col in daily_streak_columns}:
                conn.execute(
                    "ALTER TABLE daily_streaks ADD COLUMN points INTEGER NOT NULL DEFAULT 0"
                )
            daily_questions_scheduler_columns = conn.execute(
                "PRAGMA table_info(daily_questions_scheduler)"
            ).fetchall()
            if "last_poll_message_id" not in {
                str(col["name"]) for col in daily_questions_scheduler_columns
            }:
                conn.execute(
                    """
                    ALTER TABLE daily_questions_scheduler
                    ADD COLUMN last_poll_message_id INTEGER NOT NULL DEFAULT 0
                    """
                )
            conn.execute(
                "INSERT OR IGNORE INTO community_prize_state (id, total_coins) VALUES (1, 0)"
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO roulette_reward_cursor (id, current_index)
                VALUES (1, 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO community_prize_display (
                    id, channel_id, unlocked_message_id, progress_message_id
                )
                VALUES (1, 0, 0, 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO achievements_display (id, channel_id, message_id)
                VALUES (1, 0, 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO achievements_live_board_config (
                    id, channel_id, global_message_id, is_active
                )
                VALUES (1, 0, 0, 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO ingame_events_display (id, channel_id)
                VALUES (1, 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO ingame_event_channels (event_type, channel_id)
                VALUES ('achievement_unlocked', 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO ingame_event_channels (event_type, channel_id)
                VALUES ('daily_reward_collected', 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO daily_race_live_board_config (id, channel_id, message_id, is_active)
                VALUES (1, 0, 0, 0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO daily_questions_scheduler (
                    id, channel_id, is_active, current_index, last_question_id, last_poll_message_id, next_rotation_at
                )
                VALUES (1, 0, 0, 0, 0, 0, NULL)
                """
            )

    @staticmethod
    def normalize_answer(answer: str) -> str:
        return answer.strip().lower()

    @staticmethod
    def parse_options(options_raw: str) -> list[str]:
        if not options_raw.strip():
            return []
        return [opt for opt in (part.strip() for part in options_raw.split("|")) if opt]

    def ensure_user(self, user_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (user_id, coins)
                VALUES (?, ?)
                """,
                (user_id, self.starting_coins),
            )

    def get_balance(self, user_id: int) -> int:
        self.ensure_user(user_id)
        with self.connection() as conn:
            row = conn.execute(
                "SELECT coins FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return int(row["coins"])

    def add_coins(self, user_id: int, amount: int) -> None:
        if amount < 0:
            raise ValueError("Use remove_coins for negative amounts.")
        self.ensure_user(user_id)
        with self.connection() as conn:
            conn.execute(
                "UPDATE users SET coins = coins + ? WHERE user_id = ?",
                (amount, user_id),
            )

    def remove_coins(self, user_id: int, amount: int) -> bool:
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        self.ensure_user(user_id)
        with self.connection() as conn:
            row = conn.execute(
                "SELECT coins FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None or int(row["coins"]) < amount:
                return False
            conn.execute(
                "UPDATE users SET coins = coins - ? WHERE user_id = ?",
                (amount, user_id),
            )
            return True

    def get_top_users(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT user_id, coins
                FROM users
                ORDER BY coins DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return list(rows)

    def create_question(self, question_text: str, options: list[str], reward_coins: int) -> int:
        normalized_options = [self.normalize_answer(opt) for opt in options]
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO questions (question, status, options, reward_coins, created_at)
                VALUES (?, 'open', ?, ?, ?)
                """,
                (
                    question_text,
                    "|".join(normalized_options),
                    reward_coins,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def create_question_with_answer(
        self,
        question_text: str,
        options: list[str],
        reward_coins: int,
        correct_answer: str,
    ) -> int:
        normalized_options = [self.normalize_answer(opt) for opt in options]
        normalized_answer = self.normalize_answer(correct_answer)
        if normalized_options and normalized_answer not in normalized_options:
            raise ValueError("correct_answer must be one of options")
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO questions (
                    question, status, correct_answer, options, reward_coins, created_at
                )
                VALUES (?, 'open', ?, ?, ?, ?)
                """,
                (
                    question_text,
                    normalized_answer,
                    "|".join(normalized_options),
                    reward_coins,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def get_latest_open_question(self) -> sqlite3.Row | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM questions
                WHERE status = 'open'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        return row

    def set_question_status(self, question_id: int, status: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE questions SET status = ? WHERE id = ?",
                (status, question_id),
            )

    def resolve_question(self, question_id: int, correct_answer: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE questions
                SET status = 'resolved', correct_answer = ?
                WHERE id = ?
                """,
                (self.normalize_answer(correct_answer), question_id),
            )

    def place_vote(self, question_id: int, user_id: int, answer: str) -> bool:
        with self.connection() as conn:
            question = conn.execute(
                "SELECT status, options FROM questions WHERE id = ?",
                (question_id,),
            ).fetchone()
            if question is None or question["status"] != "open":
                return False

            normalized_answer = self.normalize_answer(answer)
            options = self.parse_options(str(question["options"]))
            if options and normalized_answer not in options:
                return False

            conn.execute(
                """
                INSERT OR IGNORE INTO users (user_id, coins)
                VALUES (?, ?)
                """,
                (user_id, self.starting_coins),
            )
            conn.execute(
                """
                INSERT INTO question_votes (question_id, user_id, answer, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(question_id, user_id)
                DO UPDATE SET answer = excluded.answer
                """,
                (question_id, user_id, normalized_answer, datetime.now(timezone.utc).isoformat()),
            )
        return True

    def get_question_vote_totals(self, question_id: int) -> tuple[int, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS votes,
                    COUNT(DISTINCT answer) AS used_options
                FROM question_votes
                WHERE question_id = ?
                """,
                (question_id,),
            ).fetchone()
            return (int(row["votes"]), int(row["used_options"]))

    def payout_question(self, question_id: int) -> tuple[int, int]:
        with self.connection() as conn:
            q = conn.execute(
                "SELECT correct_answer, reward_coins FROM questions WHERE id = ?",
                (question_id,),
            ).fetchone()
            if not q or not q["correct_answer"]:
                return (0, 0)
            reward_coins = int(q["reward_coins"])
            if reward_coins <= 0:
                return (0, 0)

            winners = conn.execute(
                """
                SELECT user_id
                FROM question_votes
                WHERE question_id = ? AND answer = ?
                """,
                (question_id, q["correct_answer"]),
            ).fetchall()
            if not winners:
                return (0, 0)

            for winner in winners:
                conn.execute(
                    "UPDATE users SET coins = coins + ? WHERE user_id = ?",
                    (reward_coins, int(winner["user_id"])),
                )

            return (len(winners), len(winners) * reward_coins)

    def resolve_open_question(self, question_id: int) -> tuple[bool, int, int, str]:
        with self.connection() as conn:
            question = conn.execute(
                """
                SELECT status, correct_answer, reward_coins
                FROM questions
                WHERE id = ?
                """,
                (question_id,),
            ).fetchone()
            if question is None:
                return (False, 0, 0, "")
            status = str(question["status"] or "").strip().lower()
            correct_answer = self.normalize_answer(str(question["correct_answer"] or ""))
            if status != "open":
                return (False, 0, 0, correct_answer)

            conn.execute(
                "UPDATE questions SET status = 'resolved' WHERE id = ?",
                (question_id,),
            )

            reward_coins = int(question["reward_coins"])
            if not correct_answer or reward_coins <= 0:
                return (True, 0, 0, correct_answer)

            winners = conn.execute(
                """
                SELECT user_id
                FROM question_votes
                WHERE question_id = ? AND answer = ?
                """,
                (question_id, correct_answer),
            ).fetchall()
            if not winners:
                return (True, 0, 0, correct_answer)

            for winner in winners:
                user_id = int(winner["user_id"])
                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, coins) VALUES (?, ?)",
                    (user_id, self.starting_coins),
                )
                conn.execute(
                    "UPDATE users SET coins = coins + ? WHERE user_id = ?",
                    (reward_coins, user_id),
                )
            winner_count = len(winners)
            return (True, winner_count, winner_count * reward_coins, correct_answer)

    def create_roulette_round(
        self,
        reward_name: str = "",
        reward_code: str = "",
        reward_index: int = -1,
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO roulette_rounds (status, reward_name, reward_code, reward_index, created_at)
                VALUES ('open', ?, ?, ?, ?)
                """,
                (
                    reward_name,
                    reward_code,
                    reward_index,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def get_roulette_reward_cursor(self) -> int:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT current_index
                FROM roulette_reward_cursor
                WHERE id = 1
                """
            ).fetchone()
            return int(row["current_index"]) if row else 0

    def set_roulette_reward_cursor(self, current_index: int) -> int:
        normalized = max(0, int(current_index))
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE roulette_reward_cursor
                SET current_index = ?
                WHERE id = 1
                """,
                (normalized,),
            )
            return normalized

    def get_latest_open_roulette_round(self) -> sqlite3.Row | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM roulette_rounds
                WHERE status = 'open'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        return row

    def place_roulette_bet(self, round_id: int, user_id: int, amount: int) -> bool:
        if amount <= 0:
            return False
        if not self.remove_coins(user_id, amount):
            return False
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO roulette_bets (round_id, user_id, amount)
                VALUES (?, ?, ?)
                """,
                (round_id, user_id, amount),
            )
        return True

    def get_roulette_round_bets(self, round_id: int) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT user_id, SUM(amount) as total_bet
                FROM roulette_bets
                WHERE round_id = ?
                GROUP BY user_id
                ORDER BY total_bet DESC
                """,
                (round_id,),
            ).fetchall()
        return list(rows)

    def close_roulette_round(self, round_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE roulette_rounds SET status = 'closed' WHERE id = ?",
                (round_id,),
            )

    def has_poll_reward(self, message_id: int) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM poll_rewards WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            return row is not None

    def record_poll_reward(
        self,
        message_id: int,
        guild_id: int,
        channel_id: int,
        winning_answer: str,
        reward_coins: int,
        winner_ids: list[int],
        awarded_by: int,
    ) -> tuple[int, int]:
        if reward_coins <= 0:
            return (0, 0)
        unique_winners = list(dict.fromkeys(winner_ids))

        with self.connection() as conn:
            existing = conn.execute(
                "SELECT 1 FROM poll_rewards WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if existing is not None:
                return (0, 0)

            for user_id in unique_winners:
                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, coins) VALUES (?, ?)",
                    (user_id, self.starting_coins),
                )
                conn.execute(
                    "UPDATE users SET coins = coins + ? WHERE user_id = ?",
                    (reward_coins, user_id),
                )

            winner_count = len(unique_winners)
            total_payout = winner_count * reward_coins
            conn.execute(
                """
                INSERT INTO poll_rewards (
                    message_id, guild_id, channel_id, winning_answer, reward_coins,
                    winner_count, total_payout, awarded_by, awarded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    guild_id,
                    channel_id,
                    self.normalize_answer(winning_answer),
                    reward_coins,
                    winner_count,
                    total_payout,
                    awarded_by,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return (winner_count, total_payout)

    def get_prize_total_coins(self) -> int:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT total_coins FROM community_prize_state WHERE id = 1"
            ).fetchone()
            return int(row["total_coins"]) if row else 0

    def get_user_prize_contribution(self, user_id: int) -> int:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT total_contributed
                FROM community_prize_contributions
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return int(row["total_contributed"]) if row else 0

    def contribute_to_prize_pool(
        self, user_id: int, amount: int, rewards: list[dict[str, str | int]]
    ) -> tuple[int, list[dict[str, str | int]]]:
        if amount <= 0:
            return (self.get_prize_total_coins(), [])

        with self.connection() as conn:
            self.ensure_user(user_id)
            row = conn.execute(
                "SELECT coins FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None or int(row["coins"]) < amount:
                return (int(row["coins"]) if row else 0, [])

            conn.execute(
                "UPDATE users SET coins = coins - ? WHERE user_id = ?",
                (amount, user_id),
            )
            conn.execute(
                "UPDATE community_prize_state SET total_coins = total_coins + ? WHERE id = 1",
                (amount,),
            )
            conn.execute(
                """
                INSERT INTO community_prize_contributions (user_id, total_contributed)
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET total_contributed = total_contributed + excluded.total_contributed
                """,
                (user_id, amount),
            )

            total_row = conn.execute(
                "SELECT total_coins FROM community_prize_state WHERE id = 1"
            ).fetchone()
            total_coins = int(total_row["total_coins"]) if total_row else 0

            unlocked_rows = conn.execute(
                "SELECT threshold_coins FROM community_prize_unlocks"
            ).fetchall()
            unlocked_thresholds = {int(row["threshold_coins"]) for row in unlocked_rows}

            newly_unlocked: list[dict[str, str | int]] = []
            for reward in rewards:
                threshold = int(reward["coins"])
                if threshold <= total_coins and threshold not in unlocked_thresholds:
                    conn.execute(
                        """
                        INSERT INTO community_prize_unlocks (
                            threshold_coins, reward_name, reward_code, unlocked_at
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            threshold,
                            str(reward["name"]),
                            str(reward.get("code", "")),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    unlocked_thresholds.add(threshold)
                    newly_unlocked.append(reward)

            return (total_coins, newly_unlocked)

    def contribute_winnings_to_prize_pool(
        self, user_id: int, amount: int, rewards: list[dict[str, str | int]]
    ) -> tuple[int, list[dict[str, str | int]]]:
        if amount <= 0:
            return (self.get_prize_total_coins(), [])

        with self.connection() as conn:
            self.ensure_user(user_id)
            conn.execute(
                "UPDATE community_prize_state SET total_coins = total_coins + ? WHERE id = 1",
                (amount,),
            )
            conn.execute(
                """
                INSERT INTO community_prize_contributions (user_id, total_contributed)
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET total_contributed = total_contributed + excluded.total_contributed
                """,
                (user_id, amount),
            )

            total_row = conn.execute(
                "SELECT total_coins FROM community_prize_state WHERE id = 1"
            ).fetchone()
            total_coins = int(total_row["total_coins"]) if total_row else 0

            unlocked_rows = conn.execute(
                "SELECT threshold_coins FROM community_prize_unlocks"
            ).fetchall()
            unlocked_thresholds = {int(row["threshold_coins"]) for row in unlocked_rows}

            newly_unlocked: list[dict[str, str | int]] = []
            for reward in rewards:
                threshold = int(reward["coins"])
                if threshold <= total_coins and threshold not in unlocked_thresholds:
                    conn.execute(
                        """
                        INSERT INTO community_prize_unlocks (
                            threshold_coins, reward_name, reward_code, unlocked_at
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            threshold,
                            str(reward["name"]),
                            str(reward.get("code", "")),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    unlocked_thresholds.add(threshold)
                    newly_unlocked.append(reward)

            return (total_coins, newly_unlocked)

    def get_unlocked_prize_thresholds(self) -> set[int]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT threshold_coins FROM community_prize_unlocks"
            ).fetchall()
            return {int(row["threshold_coins"]) for row in rows}

    def get_unlocked_prizes(self) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT threshold_coins, reward_name, reward_code, unlocked_at
                FROM community_prize_unlocks
                ORDER BY threshold_coins ASC
                """
            ).fetchall()
            return list(rows)

    def get_top_prize_contributors(self, limit: int = 3) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT user_id, total_contributed
                FROM community_prize_contributions
                ORDER BY total_contributed DESC, user_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return list(rows)

    def get_prize_display_config(self) -> tuple[int, int, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, unlocked_message_id, progress_message_id
                FROM community_prize_display
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                return (0, 0, 0)
            return (
                int(row["channel_id"]),
                int(row["unlocked_message_id"]),
                int(row["progress_message_id"]),
            )

    def set_prize_display_config(
        self,
        channel_id: int,
        unlocked_message_id: int,
        progress_message_id: int,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE community_prize_display
                SET channel_id = ?, unlocked_message_id = ?, progress_message_id = ?
                WHERE id = 1
                """,
                (channel_id, unlocked_message_id, progress_message_id),
            )

    def reset_prize_pool(self) -> None:
        with self.connection() as conn:
            conn.execute("UPDATE community_prize_state SET total_coins = 0 WHERE id = 1")
            conn.execute("DELETE FROM community_prize_unlocks")
            conn.execute("DELETE FROM community_prize_contributions")
            conn.execute(
                """
                UPDATE community_prize_display
                SET channel_id = 0, unlocked_message_id = 0, progress_message_id = 0
                WHERE id = 1
                """
            )

    def reset_all(self) -> None:
        """Wipe all data and reset config tables to defaults (brand-new state)."""
        with self.connection() as conn:
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM bets")
            conn.execute("DELETE FROM question_votes")
            conn.execute("DELETE FROM questions")
            conn.execute("DELETE FROM roulette_bets")
            conn.execute("DELETE FROM roulette_rounds")
            conn.execute("DELETE FROM poll_rewards")
            conn.execute("DELETE FROM community_prize_unlocks")
            conn.execute("DELETE FROM community_prize_contributions")
            conn.execute("DELETE FROM community_prize_state")
            conn.execute("DELETE FROM community_prize_display")
            conn.execute("DELETE FROM player_links")
            conn.execute("DELETE FROM ingame_events")
            conn.execute("DELETE FROM achievement_progress")
            conn.execute("DELETE FROM achievement_player_claims")
            conn.execute("DELETE FROM achievement_global_threshold_unlocks")
            conn.execute("DELETE FROM daily_streaks")
            conn.execute("DELETE FROM achievements_display")
            conn.execute("DELETE FROM achievements_live_board_config")
            conn.execute("DELETE FROM achievements_live_board_messages")
            conn.execute("DELETE FROM ingame_events_display")
            conn.execute("DELETE FROM ingame_event_channels")
            conn.execute("DELETE FROM daily_race_live_board_config")
            conn.execute("DELETE FROM daily_questions_scheduler")
            conn.execute("DELETE FROM player_rewards")
            conn.execute("DELETE FROM shop_reward_purchases")
            conn.execute("DELETE FROM roulette_reward_cursor")

            conn.execute(
                "INSERT INTO roulette_reward_cursor (id, current_index) VALUES (1, 0)"
            )
            conn.execute(
                "INSERT INTO community_prize_state (id, total_coins) VALUES (1, 0)"
            )
            conn.execute(
                """
                INSERT INTO community_prize_display (
                    id, channel_id, unlocked_message_id, progress_message_id
                )
                VALUES (1, 0, 0, 0)
                """
            )
            conn.execute(
                "INSERT INTO achievements_display (id, channel_id, message_id) VALUES (1, 0, 0)"
            )
            conn.execute(
                """
                INSERT INTO achievements_live_board_config (
                    id, channel_id, global_message_id, is_active
                )
                VALUES (1, 0, 0, 0)
                """
            )
            conn.execute(
                "INSERT INTO ingame_events_display (id, channel_id) VALUES (1, 0)"
            )
            conn.execute(
                "INSERT INTO ingame_event_channels (event_type, channel_id) VALUES ('achievement_unlocked', 0)"
            )
            conn.execute(
                "INSERT INTO ingame_event_channels (event_type, channel_id) VALUES ('daily_reward_collected', 0)"
            )
            conn.execute(
                """
                INSERT INTO daily_race_live_board_config (id, channel_id, message_id, is_active)
                VALUES (1, 0, 0, 0)
                """
            )
            conn.execute(
                """
                INSERT INTO daily_questions_scheduler (
                    id, channel_id, is_active, current_index, last_question_id, last_poll_message_id, next_rotation_at
                )
                VALUES (1, 0, 0, 0, 0, 0, NULL)
                """
            )

    def get_game_player_id(self, discord_user_id: int) -> str | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT game_player_id
                FROM player_links
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()
            return str(row["game_player_id"]) if row else None

    def get_discord_user_id_by_game_player_id(self, game_player_id: str) -> int | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT discord_user_id
                FROM player_links
                WHERE game_player_id = ?
                """,
                (game_player_id,),
            ).fetchone()
            return int(row["discord_user_id"]) if row else None

    def create_player_link(self, discord_user_id: int, game_player_id: str) -> bool:
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT game_player_id FROM player_links WHERE discord_user_id = ?",
                (discord_user_id,),
            ).fetchone()
            if existing is not None:
                return False
            conn.execute(
                """
                INSERT INTO player_links (discord_user_id, game_player_id, referrer_game_player_id, created_at)
                VALUES (?, ?, NULL, ?)
                """,
                (discord_user_id, game_player_id, datetime.now(timezone.utc).isoformat()),
            )
            return True

    def set_referrer_for_user(self, discord_user_id: int, referrer_game_player_id: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT game_player_id, referrer_game_player_id
                FROM player_links
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()
            if row is None:
                return False
            if row["referrer_game_player_id"]:
                return False
            own_game_id = str(row["game_player_id"])
            if own_game_id == referrer_game_player_id:
                return False
            ref_exists = conn.execute(
                "SELECT 1 FROM player_links WHERE game_player_id = ?",
                (referrer_game_player_id,),
            ).fetchone()
            if ref_exists is None:
                return False
            conn.execute(
                """
                UPDATE player_links
                SET referrer_game_player_id = ?
                WHERE discord_user_id = ?
                """,
                (referrer_game_player_id, discord_user_id),
            )
            return True

    def get_referrer_game_player_id(self, game_player_id: str) -> str | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT referrer_game_player_id
                FROM player_links
                WHERE game_player_id = ?
                """,
                (game_player_id,),
            ).fetchone()
            if row is None or not row["referrer_game_player_id"]:
                return None
            return str(row["referrer_game_player_id"])

    def get_daily_race_top(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT game_player_id, points, total_collects, current_streak, best_streak
                FROM daily_streaks
                ORDER BY points DESC, current_streak DESC, total_collects DESC, game_player_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return list(rows)

    def get_daily_race_score(self, game_player_id: str) -> sqlite3.Row | None:
        with self.connection() as conn:
            return conn.execute(
                """
                SELECT game_player_id, points, total_collects, current_streak, best_streak
                FROM daily_streaks
                WHERE game_player_id = ?
                """,
                (game_player_id,),
            ).fetchone()

    def get_daily_race_rank(self, game_player_id: str) -> int | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT points, current_streak, total_collects
                FROM daily_streaks
                WHERE game_player_id = ?
                """,
                (game_player_id,),
            ).fetchone()
            if row is None:
                return None
            rank_row = conn.execute(
                """
                SELECT COUNT(*) AS better_count
                FROM daily_streaks
                WHERE
                    points > ?
                    OR (points = ? AND current_streak > ?)
                    OR (points = ? AND current_streak = ? AND total_collects > ?)
                    OR (points = ? AND current_streak = ? AND total_collects = ? AND game_player_id < ?)
                """,
                (
                    int(row["points"]),
                    int(row["points"]),
                    int(row["current_streak"]),
                    int(row["points"]),
                    int(row["current_streak"]),
                    int(row["total_collects"]),
                    int(row["points"]),
                    int(row["current_streak"]),
                    int(row["total_collects"]),
                    game_player_id,
                ),
            ).fetchone()
            return int(rank_row["better_count"]) + 1 if rank_row else 1

    def get_all_game_player_ids(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT game_player_id
                FROM player_links
                ORDER BY created_at ASC
                """
            ).fetchall()
            return [str(row["game_player_id"]) for row in rows]

    def get_achievements_display_config(self) -> tuple[int, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, message_id
                FROM achievements_display
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                return (0, 0)
            return (int(row["channel_id"]), int(row["message_id"]))

    def set_achievements_display_config(self, channel_id: int, message_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE achievements_display
                SET channel_id = ?, message_id = ?
                WHERE id = 1
                """,
                (channel_id, message_id),
            )

    def get_achievements_live_board_config(self) -> tuple[int, int, bool]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, global_message_id, is_active
                FROM achievements_live_board_config
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                return (0, 0, False)
            return (
                int(row["channel_id"]),
                int(row["global_message_id"]),
                bool(int(row["is_active"])),
            )

    def set_achievements_live_board_config(
        self,
        channel_id: int,
        global_message_id: int,
        is_active: bool,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE achievements_live_board_config
                SET channel_id = ?, global_message_id = ?, is_active = ?
                WHERE id = 1
                """,
                (channel_id, global_message_id, 1 if is_active else 0),
            )

    def clear_achievements_live_board_messages(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM achievements_live_board_messages")

    def get_achievements_live_board_message_id(self, achievement_id: str) -> int:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT message_id
                FROM achievements_live_board_messages
                WHERE achievement_id = ?
                """,
                (achievement_id,),
            ).fetchone()
            if row is None:
                return 0
            return int(row["message_id"])

    def set_achievements_live_board_message_id(self, achievement_id: str, message_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO achievements_live_board_messages (achievement_id, message_id)
                VALUES (?, ?)
                ON CONFLICT(achievement_id)
                DO UPDATE SET message_id = excluded.message_id
                """,
                (achievement_id, message_id),
            )

    def get_ingame_events_channel_id(self) -> int:
        # Legacy method kept for backward compatibility.
        return self.get_ingame_event_channel_id("achievement_unlocked")

    def set_ingame_events_channel_id(self, channel_id: int) -> None:
        # Legacy method kept for backward compatibility.
        self.set_ingame_event_channel_id("achievement_unlocked", channel_id)

    def get_ingame_event_channel_id(self, event_type: str) -> int:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id
                FROM ingame_event_channels
                WHERE event_type = ?
                """,
                (event_type,),
            ).fetchone()
            if row is None:
                return 0
            return int(row["channel_id"])

    def set_ingame_event_channel_id(self, event_type: str, channel_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO ingame_event_channels (event_type, channel_id)
                VALUES (?, ?)
                ON CONFLICT(event_type)
                DO UPDATE SET channel_id = excluded.channel_id
                """,
                (event_type, channel_id),
            )

    def record_ingame_event(
        self,
        event_id: str,
        event_type: str,
        game_player_id: str,
        payload_json: str,
    ) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM ingame_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if row is not None:
                return False
            conn.execute(
                """
                INSERT INTO ingame_events (
                    event_id, event_type, game_player_id, payload_json, processed_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event_type,
                    game_player_id,
                    payload_json,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return True

    def increment_achievement_completion(self, achievement_id: str) -> int:
        _, new_count = self.increment_achievement_completion_by(achievement_id, 1)
        return new_count

    def increment_achievement_completion_by(
        self,
        achievement_id: str,
        delta: int,
    ) -> tuple[int, int]:
        if delta <= 0:
            current = self.get_achievement_completion_count(achievement_id)
            return (current, current)
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT completion_count
                FROM achievement_progress
                WHERE achievement_id = ?
                """,
                (achievement_id,),
            ).fetchone()
            now = datetime.now(timezone.utc).isoformat()
            if row is None:
                new_count = delta
                conn.execute(
                    """
                    INSERT INTO achievement_progress (
                        achievement_id, completion_count, last_completed_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (achievement_id, new_count, now),
                )
                return (0, new_count)
            previous_count = int(row["completion_count"])
            new_count = previous_count + delta
            conn.execute(
                """
                UPDATE achievement_progress
                SET completion_count = ?, last_completed_at = ?
                WHERE achievement_id = ?
                """,
                (new_count, now, achievement_id),
            )
            return (previous_count, new_count)

    def get_achievement_completion_count(self, achievement_id: str) -> int:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT completion_count
                FROM achievement_progress
                WHERE achievement_id = ?
                """,
                (achievement_id,),
            ).fetchone()
            return int(row["completion_count"]) if row else 0

    def has_claimed_achievement(self, achievement_id: str, game_player_id: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM achievement_player_claims
                WHERE achievement_id = ? AND game_player_id = ?
                """,
                (achievement_id, game_player_id),
            ).fetchone()
            return row is not None

    def mark_achievement_claimed(self, achievement_id: str, game_player_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO achievement_player_claims (
                    achievement_id, game_player_id, claimed_at
                )
                VALUES (?, ?, ?)
                """,
                (achievement_id, game_player_id, datetime.now(timezone.utc).isoformat()),
            )

    def get_achievement_unlocker_game_ids(self, achievement_id: str) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT game_player_id
                FROM achievement_player_claims
                WHERE achievement_id = ?
                ORDER BY claimed_at ASC
                """,
                (achievement_id,),
            ).fetchall()
            return [str(row["game_player_id"]) for row in rows]

    def reset_achievements_progress(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM achievement_progress")
            conn.execute("DELETE FROM achievement_player_claims")
            conn.execute("DELETE FROM achievement_global_threshold_unlocks")

    def get_unlocked_global_thresholds(self, achievement_id: str) -> set[int]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT threshold
                FROM achievement_global_threshold_unlocks
                WHERE achievement_id = ?
                """,
                (achievement_id,),
            ).fetchall()
            return {int(row["threshold"]) for row in rows}

    def mark_global_threshold_unlocked(self, achievement_id: str, threshold: int) -> bool:
        with self.connection() as conn:
            existing = conn.execute(
                """
                SELECT 1
                FROM achievement_global_threshold_unlocks
                WHERE achievement_id = ? AND threshold = ?
                """,
                (achievement_id, threshold),
            ).fetchone()
            if existing is not None:
                return False
            conn.execute(
                """
                INSERT INTO achievement_global_threshold_unlocks (
                    achievement_id, threshold, unlocked_at
                )
                VALUES (?, ?, ?)
                """,
                (achievement_id, threshold, datetime.now(timezone.utc).isoformat()),
            )
            return True

    def get_all_unlocked_global_thresholds(self) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT achievement_id, threshold
                FROM achievement_global_threshold_unlocks
                ORDER BY unlocked_at ASC
                """
            ).fetchall()
            return list(rows)

    def record_daily_collect(
        self,
        game_player_id: str,
        collect_day_utc: str,
        streak: int,
    ) -> tuple[bool, int, int, int]:
        normalized_streak = max(0, int(streak))
        points_awarded = 2 ** normalized_streak
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT current_streak, best_streak, last_collect_day, total_collects, points
                FROM daily_streaks
                WHERE game_player_id = ?
                """,
                (game_player_id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO daily_streaks (
                        game_player_id, current_streak, best_streak, last_collect_day, total_collects, points
                    )
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (
                        game_player_id,
                        normalized_streak,
                        normalized_streak,
                        collect_day_utc,
                        points_awarded,
                    ),
                )
                return (True, normalized_streak, points_awarded, points_awarded)
            last_collect_day = str(row["last_collect_day"]) if row["last_collect_day"] else ""
            if last_collect_day == collect_day_utc:
                return (False, int(row["current_streak"]), int(row["points"]), 0)
            new_streak = normalized_streak
            best_streak = max(int(row["best_streak"]), new_streak)
            total_collects = int(row["total_collects"]) + 1
            total_points = int(row["points"]) + points_awarded
            conn.execute(
                """
                UPDATE daily_streaks
                SET current_streak = ?, best_streak = ?, last_collect_day = ?, total_collects = ?, points = ?
                WHERE game_player_id = ?
                """,
                (new_streak, best_streak, collect_day_utc, total_collects, total_points, game_player_id),
            )
            return (True, new_streak, total_points, points_awarded)

    def get_daily_race_live_board_config(self) -> tuple[int, int, bool]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, message_id, is_active
                FROM daily_race_live_board_config
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                return (0, 0, False)
            return (int(row["channel_id"]), int(row["message_id"]), bool(int(row["is_active"])))

    def get_daily_questions_scheduler_config(self) -> tuple[int, bool, int, int, int, str | None]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, is_active, current_index, last_question_id, last_poll_message_id, next_rotation_at
                FROM daily_questions_scheduler
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                return (0, False, 0, 0, 0, None)
            return (
                int(row["channel_id"]),
                bool(int(row["is_active"])),
                int(row["current_index"]),
                int(row["last_question_id"]),
                int(row["last_poll_message_id"]),
                str(row["next_rotation_at"]) if row["next_rotation_at"] else None,
            )

    def set_daily_questions_scheduler_config(
        self,
        channel_id: int,
        is_active: bool,
        current_index: int,
        last_question_id: int,
        last_poll_message_id: int,
        next_rotation_at: str | None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE daily_questions_scheduler
                SET channel_id = ?, is_active = ?, current_index = ?, last_question_id = ?, last_poll_message_id = ?, next_rotation_at = ?
                WHERE id = 1
                """,
                (
                    channel_id,
                    1 if is_active else 0,
                    max(0, current_index),
                    max(0, last_question_id),
                    max(0, last_poll_message_id),
                    next_rotation_at,
                ),
            )

    def set_daily_race_live_board_config(self, channel_id: int, message_id: int, is_active: bool) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE daily_race_live_board_config
                SET channel_id = ?, message_id = ?, is_active = ?
                WHERE id = 1
                """,
                (channel_id, message_id, 1 if is_active else 0),
            )

    def reset_daily_race(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM daily_streaks")
            conn.execute(
                """
                UPDATE daily_race_live_board_config
                SET channel_id = 0, message_id = 0, is_active = 0
                WHERE id = 1
                """
            )

    def adjust_user_coins(self, user_id: int, delta: int) -> tuple[bool, int]:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (user_id, coins)
                VALUES (?, ?)
                """,
                (user_id, self.starting_coins),
            )
            row = conn.execute(
                "SELECT coins FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            current = int(row["coins"]) if row else self.starting_coins
            new_balance = current + delta
            if new_balance < 0:
                return (False, current)
            conn.execute(
                "UPDATE users SET coins = ? WHERE user_id = ?",
                (new_balance, user_id),
            )
            return (True, new_balance)

    def create_player_reward(self, reward_id: str, gamer_id: str, reward: dict[str, object]) -> bool:
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT 1 FROM player_rewards WHERE reward_id = ?",
                (reward_id,),
            ).fetchone()
            if existing is not None:
                return False
            conn.execute(
                """
                INSERT INTO player_rewards (
                    reward_id, gamer_id, reward_json, collected, created_at, collected_at
                )
                VALUES (?, ?, ?, 0, ?, NULL)
                """,
                (
                    reward_id,
                    gamer_id,
                    json.dumps(reward, separators=(",", ":"), ensure_ascii=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return True

    def get_player_rewards(self, gamer_id: str, collected: bool | None = None) -> list[sqlite3.Row]:
        with self.connection() as conn:
            query = (
                "SELECT reward_id, gamer_id, reward_json, collected, created_at, collected_at "
                "FROM player_rewards WHERE gamer_id = ?"
            )
            params: list[object] = [gamer_id]
            if collected is not None:
                query += " AND collected = ?"
                params.append(1 if collected else 0)
            query += " ORDER BY created_at ASC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return list(rows)

    def mark_player_reward_collected(self, gamer_id: str, reward_id: str) -> str:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT gamer_id, collected
                FROM player_rewards
                WHERE reward_id = ?
                """,
                (reward_id,),
            ).fetchone()
            if row is None:
                return "not_found"
            if str(row["gamer_id"]) != gamer_id:
                return "wrong_owner"
            if int(row["collected"]) == 1:
                return "already_collected"

            conn.execute(
                """
                UPDATE player_rewards
                SET collected = 1, collected_at = ?
                WHERE reward_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), reward_id),
            )
            return "collected"

    def clear_player_rewards(self, gamer_id: str) -> tuple[int, int]:
        with self.connection() as conn:
            rewards_count_row = conn.execute(
                "SELECT COUNT(*) AS count FROM player_rewards WHERE gamer_id = ?",
                (gamer_id,),
            ).fetchone()
            purchases_count_row = conn.execute(
                "SELECT COUNT(*) AS count FROM shop_reward_purchases WHERE gamer_id = ?",
                (gamer_id,),
            ).fetchone()
            rewards_count = int(rewards_count_row["count"]) if rewards_count_row else 0
            purchases_count = int(purchases_count_row["count"]) if purchases_count_row else 0

            conn.execute("DELETE FROM player_rewards WHERE gamer_id = ?", (gamer_id,))
            conn.execute("DELETE FROM shop_reward_purchases WHERE gamer_id = ?", (gamer_id,))
            return (rewards_count, purchases_count)

    def has_purchased_shop_reward(self, discord_user_id: int, reward_key: str) -> bool:
        """Return True if this user has already purchased the given shop reward_key."""
        with self.connection() as conn:
            link = conn.execute(
                "SELECT game_player_id FROM player_links WHERE discord_user_id = ?",
                (discord_user_id,),
            ).fetchone()
            if link is None:
                return False
            gamer_id = str(link["game_player_id"])
            row = conn.execute(
                "SELECT 1 FROM shop_reward_purchases WHERE gamer_id = ? AND reward_key = ?",
                (gamer_id, reward_key),
            ).fetchone()
            return row is not None

    def purchase_shop_reward(
        self,
        discord_user_id: int,
        reward_key: str,
        price: int,
        reward_payload: dict[str, object],
        *,
        mark_collected: bool = False,
    ) -> tuple[str, int | None, str | None]:
        normalized_price = max(0, int(price))
        with self.connection() as conn:
            link = conn.execute(
                """
                SELECT game_player_id
                FROM player_links
                WHERE discord_user_id = ?
                """,
                (discord_user_id,),
            ).fetchone()
            if link is None:
                return ("missing_link", None, None)
            gamer_id = str(link["game_player_id"])

            existing = conn.execute(
                """
                SELECT reward_id
                FROM shop_reward_purchases
                WHERE gamer_id = ? AND reward_key = ?
                """,
                (gamer_id, reward_key),
            ).fetchone()
            if existing is not None:
                return ("already_purchased", None, str(existing["reward_id"]))

            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, coins) VALUES (?, ?)",
                (discord_user_id, self.starting_coins),
            )
            row = conn.execute(
                "SELECT coins FROM users WHERE user_id = ?",
                (discord_user_id,),
            ).fetchone()
            current_coins = int(row["coins"]) if row else self.starting_coins
            if current_coins < normalized_price:
                return ("insufficient_coins", current_coins, None)

            new_balance = current_coins - normalized_price
            conn.execute(
                "UPDATE users SET coins = ? WHERE user_id = ?",
                (new_balance, discord_user_id),
            )

            reward_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            collected_val = 1 if mark_collected else 0
            collected_at_val = now_iso if mark_collected else None
            conn.execute(
                """
                INSERT INTO player_rewards (
                    reward_id, gamer_id, reward_json, collected, created_at, collected_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    reward_id,
                    gamer_id,
                    json.dumps(reward_payload, separators=(",", ":"), ensure_ascii=True),
                    collected_val,
                    now_iso,
                    collected_at_val,
                ),
            )
            conn.execute(
                """
                INSERT INTO shop_reward_purchases (
                    gamer_id, reward_key, reward_id, price_paid, purchased_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (gamer_id, reward_key, reward_id, normalized_price, now_iso),
            )
            return ("purchased", new_balance, reward_id)
