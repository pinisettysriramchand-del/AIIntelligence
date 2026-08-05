"""Dashboard response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DomainSummary(BaseModel):
    domain: str
    kpi_count: int
    kpis: list[dict[str, Any]]


class DashboardResponse(BaseModel):
    total_kpis: int
    domains: list[DomainSummary]
