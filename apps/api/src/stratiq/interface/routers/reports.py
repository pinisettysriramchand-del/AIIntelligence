"""Executive report export router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from stratiq.application.reports import ReportService
from stratiq.interface.deps import CurrentUser, get_report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/executive.pdf")
async def export_executive_pdf(
    current_user: CurrentUser,
    document_id: uuid.UUID | None = Query(default=None),
    svc: ReportService = Depends(get_report_service),
) -> Response:
    pdf = await svc.export_executive_pdf(current_user.id, document_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="stratiq-executive-report.pdf"'},
    )
