"""Dashboard response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DomainSummary(BaseModel):
    domain: str
    kpi_count: int
    kpis: list[dict[str, Any]]


class DashboardResponse(BaseModel):
    total_kpis: int
    domains: list[DomainSummary]
    data_quality_warnings: list[dict[str, Any]] = Field(default_factory=list)
