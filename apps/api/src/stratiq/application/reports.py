from __future__ import annotations

import logging
import uuid

from stratiq.domain.exceptions import NotFoundError
from stratiq.infrastructure.reporting.pdf_export import build_executive_pdf

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(
        self,
        decision_repo: "DecisionRepository",  # noqa: F821
        audit: "AuditService",  # noqa: F821
    ) -> None:
        self._decisions = decision_repo
        self._audit = audit

    async def export_executive_pdf(
        self, owner_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> bytes:
        report = await self._decisions.get_latest_executive_report(owner_id, document_id)
        if not report:
            raise NotFoundError("ExecutiveReport", owner_id)
        cards = await self._decisions.list_cards(owner_id, document_id)
        pdf = build_executive_pdf(report, cards)
        await self._audit.log_report_exported(owner_id, report.id, bytes_len=len(pdf))
        logger.info("executive_pdf_exported owner=%s bytes=%s", owner_id, len(pdf))
        return pdf
