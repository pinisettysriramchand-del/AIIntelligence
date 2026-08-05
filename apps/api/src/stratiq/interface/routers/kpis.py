from uuid import UUID

from fastapi import APIRouter, Depends, Query

from stratiq.domain.entities import User
from stratiq.interface.deps import Services, get_current_user, get_services
from stratiq.interface.schemas.kpis import KPIListResponse, KPIResponse

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("", response_model=KPIListResponse)
async def list_kpis(
    document_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> KPIListResponse:
    items = await services.kpis.list_for_owner(user.id, document_id)
    return KPIListResponse(
        items=[
            KPIResponse(
                id=str(k.id),
                document_id=str(k.document_id),
                name=k.name,
                value=k.value,
                unit=k.unit,
                period=k.period,
                domain=k.domain,
                evidence_chunk_ids=k.evidence_chunk_ids,
            )
            for k in items
        ]
    )
