"""KPIs router: list, get, evidence."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from stratiq.application.kpis import KPIService
from stratiq.domain.enums import KPIDomain
from stratiq.domain.exceptions import AuthorizationError, NotFoundError
from stratiq.interface.deps import CurrentUser, get_chunk_repo, get_kpi_service
from stratiq.interface.schemas.kpis import ChunkResponse, KPIListResponse, KPIResponse

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("", response_model=KPIListResponse)
async def list_kpis(
    current_user: CurrentUser,
    document_id: uuid.UUID | None = Query(default=None),
    domain: KPIDomain | None = Query(default=None),
    kpi_svc: KPIService = Depends(get_kpi_service),
) -> KPIListResponse:
    kpis = await kpi_svc.list_kpis(current_user.id, document_id=document_id, domain=domain)
    return KPIListResponse(items=[_kpi_response(k) for k in kpis], total=len(kpis))


@router.get("/{kpi_id}", response_model=KPIResponse)
async def get_kpi(
    kpi_id: uuid.UUID,
    current_user: CurrentUser,
    kpi_svc: KPIService = Depends(get_kpi_service),
) -> KPIResponse:
    try:
        kpi = await kpi_svc.get_kpi(kpi_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _kpi_response(kpi)


@router.get("/{kpi_id}/evidence", response_model=list[ChunkResponse])
async def get_kpi_evidence(
    kpi_id: uuid.UUID,
    current_user: CurrentUser,
    kpi_svc: KPIService = Depends(get_kpi_service),
    chunk_repo=Depends(get_chunk_repo),
) -> list[ChunkResponse]:
    try:
        chunks = await kpi_svc.get_evidence_chunks(kpi_id, current_user.id, chunk_repo)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [
        ChunkResponse(
            id=c.id,
            document_id=c.document_id,
            content=c.content,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            metadata=c.metadata,
        )
        for c in chunks
    ]


def _kpi_response(k: object) -> KPIResponse:
    from stratiq.domain.entities import KPI

    assert isinstance(k, KPI)
    return KPIResponse(
        id=k.id,
        document_id=k.document_id,
        domain=k.domain,
        name=k.name,
        value=k.value,
        unit=k.unit,
        period=k.period,
        evidence_chunk_ids=k.evidence_chunk_ids,
        created_at=k.created_at,
        updated_at=k.updated_at,
        business_meaning=k.business_meaning,
        confidence=k.confidence,
        dimensions=k.dimensions or {},
        previous_value=k.previous_value,
        previous_period=k.previous_period,
        trend=k.trend.value if hasattr(k.trend, "value") else str(k.trend),
        delta_label=k.delta_label,
    )
