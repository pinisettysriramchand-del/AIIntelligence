from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from stratiq.domain.entities import User
from stratiq.domain.exceptions import NotFoundError
from stratiq.interface.deps import Services, get_current_user, get_services

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/executive.pdf")
async def export_executive_pdf(
    document_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> Response:
    try:
        pdf = await services.reports.export_executive_pdf(user.id, document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="stratiq-executive-report.pdf"'},
    )
