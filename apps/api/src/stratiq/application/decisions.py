"""Decision Intelligence use-cases — Stage 2 reconciled to Stage 1 domain + Part 3 governance."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from stratiq.application.health import compute_health_score
from stratiq.application.ports import LLMClient
from stratiq.domain.entities import DecisionCard, ExecutiveReport, KPI
from stratiq.domain.enums import DocumentStatus, EvidenceMode, HealthLabel, TrendDirection
from stratiq.domain.exceptions import NotFoundError, ValidationError
from stratiq.infrastructure.ai import prompts

logger = logging.getLogger(__name__)


def _normalize_trend(value: str | None) -> TrendDirection:
    raw = (value or "").strip().lower()
    try:
        return TrendDirection(raw)
    except ValueError:
        return TrendDirection.unknown


def _normalize_health(value: str | None) -> HealthLabel:
    raw = (value or "").strip().lower()
    try:
        return HealthLabel(raw)
    except ValueError:
        return HealthLabel.watch


def _normalize_evidence_mode(value: str | None) -> EvidenceMode:
    raw = (value or "").strip().lower()
    try:
        return EvidenceMode(raw)
    except ValueError:
        return EvidenceMode.inference


def _clamp_confidence(value: Any) -> float:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        conf = 0.5
    return max(0.0, min(1.0, conf))


def validate_card_payload(raw: dict[str, Any], kpi: KPI) -> None:
    if not str(raw.get("what_happened") or "").strip():
        raise ValidationError(f"Card for {kpi.name} missing what_happened")
    if not str(raw.get("why_it_happened") or "").strip():
        raise ValidationError(f"Card for {kpi.name} missing why_it_happened")
    if not str(raw.get("recommendation") or "").strip():
        raise ValidationError(f"Card for {kpi.name} missing recommendation")
    evidence = raw.get("evidence_chunk_ids") or [str(x) for x in kpi.evidence_chunk_ids]
    if not evidence:
        raise ValidationError(f"Card for {kpi.name} missing evidence")


class DecisionIntelligenceService:
    def __init__(
        self,
        kpi_repo: "KPIRepository",  # noqa: F821
        doc_repo: "DocumentRepository",  # noqa: F821
        chunk_repo: "ChunkRepository",  # noqa: F821
        decision_repo: "DecisionRepository",  # noqa: F821
        llm: LLMClient,
        audit: "AuditService",  # noqa: F821
    ) -> None:
        self._kpis = kpi_repo
        self._docs = doc_repo
        self._chunks = chunk_repo
        self._decisions = decision_repo
        self._llm = llm
        self._audit = audit

    async def generate(
        self, owner_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        kpi_list = await self._kpis.list_by_owner(owner_id, document_id=document_id)
        if not kpi_list:
            raise ValidationError("No KPIs available. Process documents first.")

        if document_id is not None:
            document = await self._docs.get_by_id(document_id)
            if document is None or document.owner_id != owner_id:
                raise NotFoundError("Document", document_id)

        evidence_map = await self._evidence_for_kpis(kpi_list)
        payload = await self._llm.json_completion(
            messages=[
                {"role": "system", "content": prompts.DECISION_INTELLIGENCE_SYSTEM},
                {"role": "user", "content": prompts.decision_intelligence_user(kpi_list, evidence_map)},
            ],
            temperature=0.1,
            max_tokens=3000,
        )
        card_items = payload.get("cards") if isinstance(payload, dict) else None
        if not isinstance(card_items, list):
            raise ValidationError("Decision intelligence response missing cards")

        by_id = {str(k.id): k for k in kpi_list}
        by_name = {k.name.lower(): k for k in kpi_list}
        cards: list[DecisionCard] = []
        now = datetime.now(UTC)

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

            known = {str(x) for x in kpi.evidence_chunk_ids}
            evidence_raw = item.get("evidence_chunk_ids") or [str(x) for x in kpi.evidence_chunk_ids]
            evidence_ids = []
            for raw_id in evidence_raw:
                sid = str(raw_id)
                if sid in known:
                    evidence_ids.append(uuid.UUID(sid))
            if not evidence_ids:
                evidence_ids = list(kpi.evidence_chunk_ids)

            mode = _normalize_evidence_mode(item.get("evidence_mode"))
            if not evidence_ids:
                mode = EvidenceMode.insufficient

            related = []
            for rid in item.get("related_kpi_ids") or []:
                if str(rid) in by_id:
                    related.append(uuid.UUID(str(rid)))

            cards.append(
                DecisionCard(
                    id=uuid.uuid4(),
                    owner_id=owner_id,
                    kpi_id=kpi.id,
                    document_id=kpi.document_id,
                    kpi_name=kpi.name,
                    current_value=kpi.value,
                    unit=kpi.unit,
                    period=kpi.period,
                    domain=kpi.domain.value if hasattr(kpi.domain, "value") else str(kpi.domain),
                    trend=_normalize_trend(item.get("trend")),
                    health=_normalize_health(item.get("health")),
                    what_happened=str(item["what_happened"]).strip(),
                    why_it_happened=str(item["why_it_happened"]).strip(),
                    business_impact=str(item.get("business_impact") or "Impact not quantified from evidence.").strip(),
                    risks=[str(r).strip() for r in (item.get("risks") or []) if str(r).strip()],
                    opportunities=[
                        str(o).strip() for o in (item.get("opportunities") or []) if str(o).strip()
                    ],
                    recommendation=str(item["recommendation"]).strip(),
                    forecast_value=(
                        str(item["forecast_value"]).strip() if item.get("forecast_value") else None
                    ),
                    forecast_horizon=(
                        str(item["forecast_horizon"]).strip() if item.get("forecast_horizon") else None
                    ),
                    forecast_explanation=(
                        str(item["forecast_explanation"]).strip()
                        if item.get("forecast_explanation")
                        else None
                    ),
                    confidence=_clamp_confidence(item.get("confidence")),
                    evidence_mode=mode,
                    evidence_chunk_ids=evidence_ids,
                    related_kpi_ids=related,
                    created_at=now,
                )
            )

        if not cards:
            raise ValidationError("No valid decision cards were produced")

        saved_cards = await self._decisions.replace_cards(owner_id, cards, document_id)
        documents = await self._docs.list_by_owner(owner_id)
        ready = sum(1 for d in documents if d.status == DocumentStatus.ready)
        failed = sum(1 for d in documents if d.status == DocumentStatus.failed)
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

        report_confidence = _clamp_confidence(payload.get("confidence") if isinstance(payload, dict) else None)
        if report_confidence == 0.5 and saved_cards:
            report_confidence = sum(c.confidence for c in saved_cards) / len(saved_cards)

        report = await self._decisions.save_executive_report(
            ExecutiveReport(
                id=uuid.uuid4(),
                owner_id=owner_id,
                summary=summary,
                health_score=health_score,
                health_label=health_label,
                timeline=normalized_timeline,
                document_id=document_id,
                confidence=report_confidence,
                created_at=now,
            )
        )
        await self._audit.log_decisions_generated(
            owner_id, report.id, card_count=len(saved_cards), health_score=health_score
        )
        return {"report": report, "cards": saved_cards}

    async def list_cards(
        self, owner_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> list[DecisionCard]:
        return await self._decisions.list_cards(owner_id, document_id)

    async def get_card(self, card_id: uuid.UUID, owner_id: uuid.UUID) -> DecisionCard:
        card = await self._decisions.get_card(card_id, owner_id)
        if not card:
            raise NotFoundError("DecisionCard", card_id)
        return card

    async def get_executive(
        self, owner_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> ExecutiveReport:
        report = await self._decisions.get_latest_executive_report(owner_id, document_id)
        if not report:
            raise NotFoundError("ExecutiveReport", owner_id)
        return report

    async def list_forecasts(
        self, owner_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        cards = await self._decisions.list_cards(owner_id, document_id)
        results: list[dict[str, Any]] = []
        for c in cards:
            has_value = bool(c.forecast_value)
            explanation = c.forecast_explanation
            if has_value:
                status = "ok"
            else:
                status = "insufficient_history"
                explanation = explanation or (
                    "Insufficient historical data to produce a forecast."
                )
            results.append(
                {
                    "kpi_id": str(c.kpi_id),
                    "kpi_name": c.kpi_name,
                    "current_value": c.current_value,
                    "unit": c.unit,
                    "forecast_value": c.forecast_value,
                    "forecast_horizon": c.forecast_horizon,
                    "forecast_explanation": explanation,
                    "trend": c.trend.value,
                    "confidence": c.confidence,
                    "evidence_mode": c.evidence_mode.value,
                    "status": status,
                }
            )
        return results

    async def _evidence_for_kpis(self, kpis: list[KPI]) -> dict[str, str]:
        result: dict[str, str] = {}
        for kpi in kpis:
            chunks = await self._chunks.get_by_ids(list(kpi.evidence_chunk_ids))
            result[str(kpi.id)] = "\n\n".join(
                f"[chunk:{c.id}]\n{c.content[:500]}" for c in chunks
            )
        return result

    @staticmethod
    def _fallback_summary(cards: list[DecisionCard], score: int, label: HealthLabel) -> str:
        top = ", ".join(c.kpi_name for c in cards[:3])
        return (
            f"Business health is {label.value} ({score}/100). "
            f"Priority KPIs under review: {top}. "
            f"{len(cards)} decision cards generated with evidence-backed recommendations."
        )

    @staticmethod
    def _fallback_timeline(cards: list[DecisionCard]) -> list[dict[str, str]]:
        events = []
        for card in cards[:5]:
            events.append(
                {
                    "title": f"{card.kpi_name}: {card.trend.value}",
                    "detail": card.recommendation[:240],
                    "severity": "high" if card.health == HealthLabel.critical else "medium",
                }
            )
        return events
