from __future__ import annotations

import random
from typing import Sequence


def pick_weighted_winner(weighted_entries: Sequence[tuple[int, int]]) -> int | None:
    """
    Pick a user_id from (user_id, weight) entries.
    Returns None if no valid positive weights are present.
    """
    filtered = [(user_id, weight) for user_id, weight in weighted_entries if weight > 0]
    if not filtered:
        return None

    ids = [entry[0] for entry in filtered]
    weights = [entry[1] for entry in filtered]
    return random.choices(ids, weights=weights, k=1)[0]
