from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from stratiq.application.ports import DecisionRepository, DocumentRepository, KPIRepository
from stratiq.domain.entities import KPI
from stratiq.domain.enums import DocumentStatus


class KPIService:
    def __init__(self, kpis: KPIRepository) -> None:
        self._kpis = kpis

    async def list_for_owner(self, owner_id: UUID, document_id: UUID | None = None) -> list[KPI]:
        return await self._kpis.list_for_owner(owner_id, document_id)


class DashboardService:
    def __init__(
        self,
        kpis: KPIRepository,
        documents: DocumentRepository,
        decisions: DecisionRepository | None = None,
    ) -> None:
        self._kpis = kpis
        self._documents = documents
        self._decisions = decisions

    async def build(self, owner_id: UUID) -> dict:
        documents = await self._documents.list_for_owner(owner_id)
        kpis = await self._kpis.list_for_owner(owner_id)
        by_domain: dict[str, list[KPI]] = defaultdict(list)
        for kpi in kpis:
            by_domain[kpi.domain or "General"].append(kpi)

        ready = sum(1 for d in documents if d.status == DocumentStatus.READY)
        failed = sum(1 for d in documents if d.status == DocumentStatus.FAILED)
        processing = sum(1 for d in documents if d.status == DocumentStatus.PROCESSING)

        cards = []
        report = None
        if self._decisions is not None:
            cards = await self._decisions.list_cards(owner_id)
            report = await self._decisions.get_latest_executive_report(owner_id)

        return {
            "summary": {
                "document_count": len(documents),
                "ready_documents": ready,
                "processing_documents": processing,
                "failed_documents": failed,
                "kpi_count": len(kpis),
                "domains": sorted(by_domain.keys()),
                "health_score": report.health_score if report else None,
                "health_label": report.health_label if report else None,
                "decision_card_count": len(cards),
            },
            "executive_summary": report.summary if report else None,
            "timeline": report.timeline if report else [],
            "decision_cards": [
                {
                    "id": str(c.id),
                    "kpi_name": c.kpi_name,
                    "current_value": c.current_value,
                    "unit": c.unit,
                    "trend": c.trend,
                    "health": c.health,
                    "recommendation": c.recommendation,
                }
                for c in cards[:8]
            ],
            "kpis": [
                {
                    "id": str(k.id),
                    "document_id": str(k.document_id),
                    "name": k.name,
                    "value": k.value,
                    "unit": k.unit,
                    "period": k.period,
                    "domain": k.domain,
                    "evidence_chunk_ids": k.evidence_chunk_ids,
                }
                for k in kpis
            ],
            "documents": [
                {
                    "id": str(d.id),
                    "filename": d.filename,
                    "status": d.status,
                    "domain": d.domain,
                    "domain_confidence": d.domain_confidence,
                }
                for d in documents
            ],
        }
