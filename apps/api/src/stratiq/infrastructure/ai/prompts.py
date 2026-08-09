"""Prompt template accessors — backed by the Stage 4I prompt registry."""

from __future__ import annotations

from stratiq.infrastructure.ai.prompt_registry import (
    REGISTRY_VERSION,
    decision_intelligence_user,
    get_prompt,
)

PROMPT_VERSION = REGISTRY_VERSION

_rag = get_prompt("rag.chat")
_di = get_prompt("di.decision_cards")

# Backward-compatible exports used by existing call sites / tests.
SYSTEM_ASSISTANT = (
    "You are StratIQ, an AI strategic intelligence assistant. "
    "You answer questions based solely on provided context. "
    "Always cite sources using [chunk_id] notation. "
    "If evidence is insufficient, say so clearly and do not invent facts."
)

DECISION_INTELLIGENCE_SYSTEM = _di.render_system()

__all__ = [
    "PROMPT_VERSION",
    "SYSTEM_ASSISTANT",
    "DECISION_INTELLIGENCE_SYSTEM",
    "decision_intelligence_user",
    "get_prompt",
]
