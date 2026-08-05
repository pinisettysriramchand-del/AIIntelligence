"""Dashboard use-case: aggregate KPIs by domain."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from stratiq.domain.enums import KPIDomain


class DashboardService:
    def __init__(self, kpi_repo: "KPIRepository") -> None:  # noqa: F821
        self._repo = kpi_repo

    async def get_summary(self, owner_id: uuid.UUID) -> dict[str, Any]:
        kpis = await self._repo.list_by_owner(owner_id)

        by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for kpi in kpis:
            by_domain[kpi.domain.value].append(
                {
                    "id": str(kpi.id),
                    "name": kpi.name,
                    "value": kpi.value,
                    "unit": kpi.unit,
                    "period": kpi.period,
                    "document_id": str(kpi.document_id),
                    "evidence_count": len(kpi.evidence_chunk_ids),
                }
            )

        domain_summaries: list[dict[str, Any]] = []
        for domain in KPIDomain:
            items = by_domain.get(domain.value, [])
            domain_summaries.append(
                {
                    "domain": domain.value,
                    "kpi_count": len(items),
                    "kpis": items,
                }
            )

        return {
            "total_kpis": len(kpis),
            "domains": domain_summaries,
        }
