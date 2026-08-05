from __future__ import annotations

import logging
from uuid import UUID

from stratiq.application.decisions import DecisionIntelligenceService
from stratiq.application.ports import AuditRepository, DecisionRepository
from stratiq.domain.enums import AuditAction
from stratiq.domain.exceptions import NotFoundError
from stratiq.infrastructure.reporting.pdf_export import build_executive_pdf

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(
        self,
        decisions: DecisionRepository,
        decision_service: DecisionIntelligenceService,
        audit: AuditRepository,
    ) -> None:
        self._decisions = decisions
        self._decision_service = decision_service
        self._audit = audit

    async def export_executive_pdf(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> bytes:
        report = await self._decisions.get_latest_executive_report(owner_id, document_id)
        if not report:
            raise NotFoundError("Executive report not found. Generate decisions first.")
        cards = await self._decisions.list_cards(owner_id, document_id)
        pdf = build_executive_pdf(report, cards)
        await self._audit.record(
            AuditAction.REPORT_EXPORTED,
            owner_id,
            "executive_report",
            str(report.id),
            {"bytes": len(pdf)},
        )
        logger.info("executive_pdf_exported owner=%s bytes=%s", owner_id, len(pdf))
        return pdf
