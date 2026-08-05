from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from stratiq.domain.entities import DecisionCard, ExecutiveReport, User
from stratiq.domain.exceptions import NotFoundError, ValidationError
from stratiq.interface.deps import Services, get_current_user, get_services
from stratiq.interface.schemas.decisions import (
    DecisionCardResponse,
    ExecutiveReportResponse,
    ForecastResponse,
    GenerateDecisionsRequest,
    GenerateDecisionsResponse,
)

router = APIRouter(tags=["decisions"])


def _card(card: DecisionCard) -> DecisionCardResponse:
    return DecisionCardResponse(
        id=str(card.id),
        kpi_id=str(card.kpi_id),
        document_id=str(card.document_id),
        kpi_name=card.kpi_name,
        current_value=card.current_value,
        unit=card.unit,
        period=card.period,
        domain=card.domain,
        trend=card.trend,
        health=card.health,
        what_happened=card.what_happened,
        why_it_happened=card.why_it_happened,
        risks=card.risks,
        opportunities=card.opportunities,
        recommendation=card.recommendation,
        forecast_value=card.forecast_value,
        forecast_horizon=card.forecast_horizon,
        forecast_explanation=card.forecast_explanation,
        evidence_chunk_ids=card.evidence_chunk_ids,
        related_kpi_ids=card.related_kpi_ids,
    )


def _report(report: ExecutiveReport) -> ExecutiveReportResponse:
    return ExecutiveReportResponse(
        id=str(report.id),
        summary=report.summary,
        health_score=report.health_score,
        health_label=report.health_label,
        timeline=report.timeline,
        document_id=str(report.document_id) if report.document_id else None,
    )


@router.post(
    "/decisions/generate",
    response_model=GenerateDecisionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_decisions(
    body: GenerateDecisionsRequest,
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> GenerateDecisionsResponse:
    try:
        result = await services.decisions.generate(
            user.id,
            UUID(body.document_id) if body.document_id else None,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GenerateDecisionsResponse(
        report=_report(result["report"]),
        cards=[_card(c) for c in result["cards"]],
    )


@router.get("/decisions/cards", response_model=list[DecisionCardResponse])
async def list_cards(
    document_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> list[DecisionCardResponse]:
    cards = await services.decisions.list_cards(user.id, document_id)
    return [_card(c) for c in cards]


@router.get("/decisions/cards/{card_id}", response_model=DecisionCardResponse)
async def get_card(
    card_id: UUID,
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> DecisionCardResponse:
    try:
        card = await services.decisions.get_card(card_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _card(card)


@router.get("/decisions/executive", response_model=ExecutiveReportResponse)
async def get_executive(
    document_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ExecutiveReportResponse:
    try:
        report = await services.decisions.get_executive(user.id, document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _report(report)


@router.get("/forecasts", response_model=list[ForecastResponse])
async def list_forecasts(
    document_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> list[ForecastResponse]:
    items = await services.decisions.list_forecasts(user.id, document_id)
    return [ForecastResponse(**item) for item in items]
