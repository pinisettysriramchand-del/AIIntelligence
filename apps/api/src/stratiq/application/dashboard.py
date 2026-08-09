"""Dashboard use-case: aggregate KPIs by domain with period comparisons."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from stratiq.domain.entities import KPI
from stratiq.domain.enums import KPIDomain


class DashboardService:
    def __init__(self, kpi_repo: "KPIRepository") -> None:  # noqa: F821
        self._repo = kpi_repo

    async def get_summary(self, owner_id: uuid.UUID) -> dict[str, Any]:
        kpis = await self._repo.list_by_owner(owner_id)
        comparisons = self._build_comparisons(kpis)

        by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for kpi in kpis:
            comparison = None
            if kpi.previous_value is not None or kpi.trend.value != "unknown":
                comparison = {
                    "previous_period": kpi.previous_period,
                    "previous_value": kpi.previous_value,
                    "delta_label": kpi.delta_label or "n/a",
                    "trend": kpi.trend.value,
                }
            else:
                comparison = comparisons.get(kpi.id)
            by_domain[kpi.domain.value].append(
                {
                    "id": str(kpi.id),
                    "name": kpi.name,
                    "value": kpi.value,
                    "unit": kpi.unit,
                    "period": kpi.period,
                    "document_id": str(kpi.document_id),
                    "evidence_count": len(kpi.evidence_chunk_ids),
                    "business_meaning": kpi.business_meaning,
                    "confidence": kpi.confidence,
                    "dimensions": kpi.dimensions,
                    "trend": (comparison["trend"] if comparison else kpi.trend.value),
                    "comparison": comparison,
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

    @staticmethod
    def _build_comparisons(kpis: list[KPI]) -> dict[uuid.UUID, dict[str, Any]]:
        """Compare same-name/unit KPIs across periods when multiple rows exist."""
        groups: dict[tuple[str, str], list[KPI]] = defaultdict(list)
        for kpi in kpis:
            groups[(kpi.name.strip().lower(), (kpi.unit or "").strip().lower())].append(kpi)

        comparisons: dict[uuid.UUID, dict[str, Any]] = {}
        for group in groups.values():
            if len(group) < 2:
                continue
            ordered = sorted(group, key=lambda k: (k.period or "", str(k.id)))
            for idx, kpi in enumerate(ordered):
                if idx == 0:
                    continue
                prev = ordered[idx - 1]
                trend = "unknown"
                delta_label = "n/a"
                try:
                    delta = float(str(kpi.value).replace(",", "")) - float(
                        str(prev.value).replace(",", "")
                    )
                    if delta > 0:
                        trend = "up"
                    elif delta < 0:
                        trend = "down"
                    else:
                        trend = "flat"
                    delta_label = f"{delta:+.4g}"
                except ValueError:
                    pass
                comparisons[kpi.id] = {
                    "previous_period": prev.period,
                    "previous_value": prev.value,
                    "delta_label": delta_label,
                    "trend": trend,
                }
        return comparisons
