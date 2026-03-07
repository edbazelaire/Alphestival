from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DailyQuestion:
    question: str
    options: list[str]
    answer: str
    reward: int


class QuestionsStore:
    def __init__(self, file_path: str = "data/questions.json") -> None:
        self.path = Path(file_path)

    def get_questions(self) -> list[DailyQuestion]:
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("data/questions.json must contain a list.")

        questions: list[DailyQuestion] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            options_raw = item.get("options", [])
            if not isinstance(options_raw, list):
                continue
            options = [str(opt).strip() for opt in options_raw if str(opt).strip()]
            try:
                reward = int(item.get("reward", 0))
            except (TypeError, ValueError):
                reward = 0
            if question and answer and len(options) >= 2 and reward > 0:
                questions.append(
                    DailyQuestion(
                        question=question,
                        options=options,
                        answer=answer,
                        reward=reward,
                    )
                )
        return questions
