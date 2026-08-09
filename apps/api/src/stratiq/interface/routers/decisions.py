"""Decision Intelligence and forecast routers."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from stratiq.application.decisions import DecisionIntelligenceService
from stratiq.domain.entities import DecisionCard, ExecutiveReport
from stratiq.interface.deps import CurrentUser, get_decision_service
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
        trend=card.trend.value,
        health=card.health.value,
        what_happened=card.what_happened,
        why_it_happened=card.why_it_happened,
        business_impact=card.business_impact,
        risks=card.risks,
        opportunities=card.opportunities,
        recommendation=card.recommendation,
        forecast_value=card.forecast_value,
        forecast_horizon=card.forecast_horizon,
        forecast_explanation=card.forecast_explanation,
        confidence=card.confidence,
        evidence_mode=card.evidence_mode.value,
        evidence_chunk_ids=[str(x) for x in card.evidence_chunk_ids],
        related_kpi_ids=[str(x) for x in card.related_kpi_ids],
    )


def _report(report: ExecutiveReport) -> ExecutiveReportResponse:
    return ExecutiveReportResponse(
        id=str(report.id),
        summary=report.summary,
        health_score=report.health_score,
        health_label=report.health_label.value,
        timeline=report.timeline,
        document_id=str(report.document_id) if report.document_id else None,
        confidence=report.confidence,
    )


@router.post(
    "/decisions/generate",
    response_model=GenerateDecisionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_decisions(
    body: GenerateDecisionsRequest,
    current_user: CurrentUser,
    svc: DecisionIntelligenceService = Depends(get_decision_service),
) -> GenerateDecisionsResponse:
    result = await svc.generate(
        current_user.id,
        uuid.UUID(body.document_id) if body.document_id else None,
    )
    return GenerateDecisionsResponse(
        report=_report(result["report"]),
        cards=[_card(c) for c in result["cards"]],
    )


@router.get("/decisions/cards", response_model=list[DecisionCardResponse])
async def list_cards(
    current_user: CurrentUser,
    document_id: uuid.UUID | None = Query(default=None),
    svc: DecisionIntelligenceService = Depends(get_decision_service),
) -> list[DecisionCardResponse]:
    cards = await svc.list_cards(current_user.id, document_id)
    return [_card(c) for c in cards]


@router.get("/decisions/cards/{card_id}", response_model=DecisionCardResponse)
async def get_card(
    card_id: uuid.UUID,
    current_user: CurrentUser,
    svc: DecisionIntelligenceService = Depends(get_decision_service),
) -> DecisionCardResponse:
    card = await svc.get_card(card_id, current_user.id)
    return _card(card)


@router.get("/decisions/executive", response_model=ExecutiveReportResponse)
async def get_executive(
    current_user: CurrentUser,
    document_id: uuid.UUID | None = Query(default=None),
    svc: DecisionIntelligenceService = Depends(get_decision_service),
) -> ExecutiveReportResponse:
    report = await svc.get_executive(current_user.id, document_id)
    return _report(report)


@router.get("/forecasts", response_model=list[ForecastResponse])
async def list_forecasts(
    current_user: CurrentUser,
    document_id: uuid.UUID | None = Query(default=None),
    svc: DecisionIntelligenceService = Depends(get_decision_service),
) -> list[ForecastResponse]:
    items = await svc.list_forecasts(current_user.id, document_id)
    return [ForecastResponse(**item) for item in items]
