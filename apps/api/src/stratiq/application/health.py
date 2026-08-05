from __future__ import annotations

from stratiq.domain.enums import HealthLabel
from stratiq.domain.entities import DecisionCard


def label_for_score(score: int) -> str:
    if score < 40:
        return HealthLabel.CRITICAL
    if score < 70:
        return HealthLabel.WATCH
    return HealthLabel.HEALTHY


def compute_health_score(
    cards: list[DecisionCard],
    ready_documents: int,
    failed_documents: int,
    llm_score: int | None = None,
) -> tuple[int, str]:
    score = 65
    score += min(ready_documents, 3) * 5
    score -= failed_documents * 8
    critical = sum(1 for c in cards if c.health == HealthLabel.CRITICAL)
    watch = sum(1 for c in cards if c.health == HealthLabel.WATCH)
    healthy = sum(1 for c in cards if c.health == HealthLabel.HEALTHY)
    score -= critical * 12
    score -= watch * 4
    score += healthy * 3
    if llm_score is not None:
        score = int(round((score * 0.55) + (max(0, min(100, llm_score)) * 0.45)))
    score = max(0, min(100, score))
    return score, label_for_score(score)
