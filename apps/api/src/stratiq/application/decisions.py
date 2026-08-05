from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from stratiq.application.health import compute_health_score
from stratiq.application.ports import (
    AuditRepository,
    ChunkRepository,
    DecisionRepository,
    DocumentRepository,
    KPIRepository,
    LLMPort,
)
from stratiq.domain.entities import DecisionCard, ExecutiveReport, KPI
from stratiq.domain.enums import AuditAction, DocumentStatus, HealthLabel, TrendDirection
from stratiq.domain.exceptions import NotFoundError, ValidationError
from stratiq.infrastructure.ai import prompts

logger = logging.getLogger(__name__)


def _normalize_trend(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in {TrendDirection.UP, TrendDirection.DOWN, TrendDirection.FLAT}:
        return raw
    return TrendDirection.UNKNOWN


def _normalize_health(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in {HealthLabel.CRITICAL, HealthLabel.WATCH, HealthLabel.HEALTHY}:
        return raw
    return HealthLabel.WATCH


def validate_card_payload(raw: dict[str, Any], kpi: KPI) -> None:
    if not str(raw.get("what_happened") or "").strip():
        raise ValidationError(f"Card for {kpi.name} missing what_happened")
    if not str(raw.get("why_it_happened") or "").strip():
        raise ValidationError(f"Card for {kpi.name} missing why_it_happened")
    if not str(raw.get("recommendation") or "").strip():
        raise ValidationError(f"Card for {kpi.name} missing recommendation")
    evidence = raw.get("evidence_chunk_ids") or kpi.evidence_chunk_ids
    if not evidence:
        raise ValidationError(f"Card for {kpi.name} missing evidence")


class DecisionIntelligenceService:
    def __init__(
        self,
        kpis: KPIRepository,
        documents: DocumentRepository,
        chunks: ChunkRepository,
        decisions: DecisionRepository,
        llm: LLMPort,
        audit: AuditRepository,
    ) -> None:
        self._kpis = kpis
        self._documents = documents
        self._chunks = chunks
        self._decisions = decisions
        self._llm = llm
        self._audit = audit

    async def generate(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> dict[str, Any]:
        kpi_list = await self._kpis.list_for_owner(owner_id, document_id)
        if not kpi_list:
            raise ValidationError("No KPIs available. Process documents first.")

        if document_id is not None:
            document = await self._documents.get(document_id, owner_id)
            if not document:
                raise NotFoundError("Document not found")

        evidence_map = await self._evidence_for_kpis(kpi_list)
        payload = await self._llm.complete_json(
            prompts.DECISION_INTELLIGENCE_SYSTEM,
            prompts.decision_intelligence_user(kpi_list, evidence_map),
        )
        card_items = payload.get("cards") if isinstance(payload, dict) else None
        if not isinstance(card_items, list):
            raise ValidationError("Decision intelligence response missing cards")

        by_id = {str(k.id): k for k in kpi_list}
        by_name = {k.name.lower(): k for k in kpi_list}
        cards: list[DecisionCard] = []
        for item in card_items:
            if not isinstance(item, dict):
                continue
            kpi = None
            if item.get("kpi_id") and str(item["kpi_id"]) in by_id:
                kpi = by_id[str(item["kpi_id"])]
            elif item.get("kpi_name"):
                kpi = by_name.get(str(item["kpi_name"]).strip().lower())
            if not kpi:
                continue
            try:
                validate_card_payload(item, kpi)
            except ValidationError as exc:
                logger.warning("skipping_invalid_card reason=%s", exc)
                continue
            evidence = [
                str(e)
                for e in (item.get("evidence_chunk_ids") or kpi.evidence_chunk_ids)
                if str(e) in set(kpi.evidence_chunk_ids)
            ] or list(kpi.evidence_chunk_ids)
            cards.append(
                DecisionCard(
                    id=uuid4(),
                    owner_id=owner_id,
                    kpi_id=kpi.id,
                    document_id=kpi.document_id,
                    kpi_name=kpi.name,
                    current_value=kpi.value,
                    unit=kpi.unit,
                    period=kpi.period,
                    domain=kpi.domain,
                    trend=_normalize_trend(item.get("trend")),
                    health=_normalize_health(item.get("health")),
                    what_happened=str(item["what_happened"]).strip(),
                    why_it_happened=str(item["why_it_happened"]).strip(),
                    risks=[str(r).strip() for r in (item.get("risks") or []) if str(r).strip()],
                    opportunities=[
                        str(o).strip() for o in (item.get("opportunities") or []) if str(o).strip()
                    ],
                    recommendation=str(item["recommendation"]).strip(),
                    forecast_value=(
                        str(item["forecast_value"]).strip() if item.get("forecast_value") else None
                    ),
                    forecast_horizon=(
                        str(item["forecast_horizon"]).strip()
                        if item.get("forecast_horizon")
                        else None
                    ),
                    forecast_explanation=(
                        str(item["forecast_explanation"]).strip()
                        if item.get("forecast_explanation")
                        else None
                    ),
                    evidence_chunk_ids=evidence,
                    related_kpi_ids=[
                        str(r) for r in (item.get("related_kpi_ids") or []) if str(r) in by_id
                    ],
                )
            )

        if not cards:
            raise ValidationError("No valid decision cards were produced")

        saved_cards = await self._decisions.replace_cards(owner_id, cards, document_id)
        documents = await self._documents.list_for_owner(owner_id)
        ready = sum(1 for d in documents if d.status == DocumentStatus.READY)
        failed = sum(1 for d in documents if d.status == DocumentStatus.FAILED)
        llm_score = payload.get("health_score") if isinstance(payload, dict) else None
        llm_score_int = int(llm_score) if isinstance(llm_score, (int, float)) else None
        health_score, health_label = compute_health_score(
            saved_cards, ready, failed, llm_score_int
        )

        summary = str(payload.get("executive_summary") or "").strip()
        if not summary:
            summary = self._fallback_summary(saved_cards, health_score, health_label)

        timeline = payload.get("timeline") if isinstance(payload, dict) else None
        if not isinstance(timeline, list) or not timeline:
            timeline = self._fallback_timeline(saved_cards)

        normalized_timeline = []
        for event in timeline:
            if not isinstance(event, dict):
                continue
            title = str(event.get("title") or "").strip()
            detail = str(event.get("detail") or "").strip()
            if not title or not detail:
                continue
            normalized_timeline.append(
                {
                    "title": title,
                    "detail": detail,
                    "severity": str(event.get("severity") or "medium").lower(),
                }
            )

        report = await self._decisions.save_executive_report(
            ExecutiveReport(
                id=uuid4(),
                owner_id=owner_id,
                summary=summary,
                health_score=health_score,
                health_label=health_label,
                timeline=normalized_timeline,
                document_id=document_id,
            )
        )
        await self._audit.record(
            AuditAction.DECISIONS_GENERATED,
            owner_id,
            "executive_report",
            str(report.id),
            {"card_count": len(saved_cards), "health_score": health_score},
        )
        return {
            "report": report,
            "cards": saved_cards,
        }

    async def list_cards(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> list[DecisionCard]:
        return await self._decisions.list_cards(owner_id, document_id)

    async def get_card(self, card_id: UUID, owner_id: UUID) -> DecisionCard:
        card = await self._decisions.get_card(card_id, owner_id)
        if not card:
            raise NotFoundError("Decision card not found")
        return card

    async def get_executive(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> ExecutiveReport:
        report = await self._decisions.get_latest_executive_report(owner_id, document_id)
        if not report:
            raise NotFoundError("Executive report not found. Generate decisions first.")
        return report

    async def list_forecasts(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        cards = await self._decisions.list_cards(owner_id, document_id)
        return [
            {
                "kpi_id": str(c.kpi_id),
                "kpi_name": c.kpi_name,
                "current_value": c.current_value,
                "unit": c.unit,
                "forecast_value": c.forecast_value,
                "forecast_horizon": c.forecast_horizon,
                "forecast_explanation": c.forecast_explanation,
                "trend": c.trend,
            }
            for c in cards
            if c.forecast_value or c.forecast_explanation
        ]

    async def _evidence_for_kpis(self, kpis: list[KPI]) -> dict[str, str]:
        result: dict[str, str] = {}
        for kpi in kpis:
            chunk_ids = []
            for raw in kpi.evidence_chunk_ids:
                try:
                    chunk_ids.append(UUID(raw))
                except ValueError:
                    continue
            chunks = await self._chunks.get_many(chunk_ids)
            result[str(kpi.id)] = "\n\n".join(
                f"[chunk:{c.id}]\n{c.content[:500]}" for c in chunks
            )
        return result

    @staticmethod
    def _fallback_summary(cards: list[DecisionCard], score: int, label: str) -> str:
        top = ", ".join(c.kpi_name for c in cards[:3])
        return (
            f"Business health is {label} ({score}/100). "
            f"Priority KPIs under review: {top}. "
            f"{len(cards)} decision cards generated with evidence-backed recommendations."
        )

    @staticmethod
    def _fallback_timeline(cards: list[DecisionCard]) -> list[dict[str, str]]:
        events = []
        for card in cards[:5]:
            events.append(
                {
                    "title": f"{card.kpi_name}: {card.trend}",
                    "detail": card.recommendation[:240],
                    "severity": "high" if card.health == HealthLabel.CRITICAL else "medium",
                }
            )
        return events
