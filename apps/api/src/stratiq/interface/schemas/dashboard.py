from typing import Any

from pydantic import BaseModel, Field


class DashboardResponse(BaseModel):
    summary: dict[str, Any]
    kpis: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    executive_summary: str | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    decision_cards: list[dict[str, Any]] = Field(default_factory=list)
