"""Production prompt registry — Part 4 Stage 4I governance.

Every production prompt has: id, version, purpose, input/output schemas,
evidence rules, failure behavior, and evaluation cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptEvalCase:
    """Deterministic evaluation fixture for a prompt."""

    id: str
    description: str
    scenario: str
    input_fixture: dict[str, Any]
    expected_behavior: str
    must_include: tuple[str, ...] = ()
    must_not_include: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class PromptSpec:
    id: str
    version: str
    purpose: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    evidence_rules: tuple[str, ...]
    failure_behavior: str
    system_template: str
    user_template: str | None = None
    eval_cases: tuple[PromptEvalCase, ...] = field(default_factory=tuple)

    @property
    def qualified_id(self) -> str:
        return f"{self.id}@{self.version}"

    def render_system(self, **kwargs: Any) -> str:
        if kwargs:
            return self.system_template.format(**kwargs)
        return self.system_template

    def render_user(self, **kwargs: Any) -> str:
        if not self.user_template:
            raise ValueError(f"Prompt {self.qualified_id} has no user_template")
        return self.user_template.format(**kwargs)


REGISTRY_VERSION = "part4-4i-v1"

# ── Prompt definitions ────────────────────────────────────────────────────────

_RAG_CHAT = PromptSpec(
    id="rag.chat",
    version="part4-4i-v1",
    purpose="Answer user questions using retrieved document chunks with citations.",
    input_schema={
        "type": "object",
        "required": ["context", "question"],
        "properties": {
            "context": {"type": "string", "description": "Retrieved chunk text with ids"},
            "question": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "required": ["answer"],
        "properties": {
            "answer": {"type": "string"},
            "citations": {"type": "array", "items": {"type": "string"}},
        },
    },
    evidence_rules=(
        "Use only supplied context for factual claims.",
        "Cite sources with [chunk_id] notation.",
        "Never invent missing values or documents.",
        "If evidence is insufficient, say so clearly.",
    ),
    failure_behavior=(
        "When retrieval returns no usable chunks, skip the LLM and return a fixed "
        "insufficient-evidence reply without fabricating citations."
    ),
    system_template=(
        "You are StratIQ, an AI strategic intelligence assistant. "
        "You answer questions based solely on provided context. "
        "Always cite sources using [chunk_id] notation. "
        "If evidence is insufficient, say so clearly and do not invent facts.\n\n"
        "Context chunks:\n{context}"
    ),
    user_template="{question}",
    eval_cases=(
        PromptEvalCase(
            id="rag.chat.missing_evidence",
            description="No retrieved chunks → refuse without LLM hallucination",
            scenario="missing_evidence",
            input_fixture={"context": "", "question": "What was Q1 revenue?"},
            expected_behavior="insufficient_evidence_reply",
            must_include=("Insufficient evidence",),
            must_not_include=("[chunk_",),
        ),
        PromptEvalCase(
            id="rag.chat.out_of_period",
            description="Question asks for a period not in context",
            scenario="out_of_period",
            input_fixture={
                "context": "[chunk:1]\nRevenue for FY2024 was 10M USD.",
                "question": "What was revenue in FY2010?",
            },
            expected_behavior="state_insufficient_or_out_of_scope",
            must_include=("insufficient",),
            notes="Model must not invent FY2010 figures.",
        ),
    ),
)

_DOMAIN_DETECT = PromptSpec(
    id="kpi.domain_detect",
    version="part4-4i-v1",
    purpose="Classify strategic domains present in a document preview.",
    input_schema={
        "type": "object",
        "required": ["text"],
        "properties": {"text": {"type": "string", "maxLength": 2000}},
    },
    output_schema={
        "type": "object",
        "required": ["domains"],
        "properties": {
            "domains": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "financial",
                        "operational",
                        "strategic",
                        "risk",
                        "hr",
                        "marketing",
                        "technology",
                        "other",
                    ],
                },
            }
        },
    },
    evidence_rules=(
        "Classify only from the provided document text.",
        "Do not invent domains unsupported by the preview.",
    ),
    failure_behavior="Default domains to ['other'] when parsing fails.",
    system_template="",
    user_template=(
        "You are a domain classifier. Given the following document text (first 2000 chars), \n"
        "identify which strategic domains are present. Return a JSON object with key \"domains\" "
        "containing a list of \ndomain strings from: financial, operational, strategic, risk, hr, "
        "marketing, technology, other.\n"
        'Example: {{"domains": ["financial", "operational"]}}\n'
        "Document text:\n{text}"
    ),
    eval_cases=(
        PromptEvalCase(
            id="kpi.domain_detect.financial_doc",
            description="Financial language maps to financial domain",
            scenario="correct_extraction",
            input_fixture={"text": "Q1 revenue $2.5M, gross margin 42%, EBITDA improved."},
            expected_behavior="domains_include_financial",
            must_include=("financial",),
        ),
    ),
)

_KPI_EXTRACT = PromptSpec(
    id="kpi.extract",
    version="part4-4i-v1",
    purpose="Extract measurable KPIs with evidence chunk ids from document chunks.",
    input_schema={
        "type": "object",
        "required": ["chunks"],
        "properties": {"chunks": {"type": "string"}},
    },
    output_schema={
        "type": "object",
        "required": ["kpis"],
        "properties": {
            "kpis": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "value", "domain", "evidence_chunk_ids"],
                    "properties": {
                        "name": {"type": "string"},
                        "business_meaning": {"type": "string"},
                        "value": {},
                        "unit": {"type": ["string", "null"]},
                        "period": {"type": ["string", "null"]},
                        "domain": {"type": "string"},
                        "confidence": {"type": "number"},
                        "dimensions": {"type": "object"},
                        "evidence_chunk_ids": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        },
    },
    evidence_rules=(
        "evidence_chunk_ids must reference provided chunk ids.",
        "Never invent KPI values not present in chunks.",
        "Distinguish stated values from inferred interpretations.",
        "Preserve units and periods exactly when present.",
    ),
    failure_behavior=(
        "Skip KPIs with empty evidence_chunk_ids; continue extracting others. "
        "If none valid, persist a data-quality warning."
    ),
    system_template="",
    user_template=(
        "You are a KPI extraction specialist. Given the following document chunks, \n"
        "extract all measurable KPIs. For each KPI return:\n"
        "- name: descriptive KPI name\n"
        "- business_meaning: one-sentence business meaning\n"
        "- value: numeric or textual value  \n"
        "- unit: unit of measurement (optional)\n"
        "- period: time period (optional)\n"
        "- domain: one of financial/operational/strategic/risk/hr/marketing/technology/other\n"
        "- confidence: number 0-1 for extraction confidence\n"
        '- dimensions: object of related dimensions (optional), e.g. {{"region": "EMEA"}}\n'
        "- evidence_chunk_ids: list of chunk IDs (strings) that contain evidence for this KPI\n\n"
        'Return JSON: {{"kpis": [{{"name": ..., "business_meaning": ..., "value": ..., '
        '"unit": ..., "period": ..., "domain": ..., "confidence": ..., "dimensions": {{}}, '
        '"evidence_chunk_ids": [...]}}]}}\n\n'
        "Chunks (id: content):\n{chunks}"
    ),
    eval_cases=(
        PromptEvalCase(
            id="kpi.extract.correct",
            description="Clear revenue figure with unit and period",
            scenario="correct_extraction",
            input_fixture={
                "chunks": "c1: Revenue for Q1 2025 was 250 USD million.",
            },
            expected_behavior="extract_revenue_with_evidence",
            must_include=("Revenue", "250", "c1"),
        ),
        PromptEvalCase(
            id="kpi.extract.missing_evidence",
            description="Claim without attributable chunk id must be dropped",
            scenario="missing_evidence",
            input_fixture={"chunks": "c1: Narrative without measurable KPIs."},
            expected_behavior="empty_or_skip_without_evidence",
            notes="Pipeline skips KPIs lacking evidence_chunk_ids.",
        ),
        PromptEvalCase(
            id="kpi.extract.conflicting_evidence",
            description="Two chunks disagree on the same KPI value",
            scenario="conflicting_evidence",
            input_fixture={
                "chunks": (
                    "c1: Revenue Q1 was 100M.\n"
                    "c2: Revenue Q1 was 140M according to revised filing."
                ),
            },
            expected_behavior="surface_conflict_or_lower_confidence",
            notes="Prefer citing both chunks; do not silently pick one value.",
        ),
        PromptEvalCase(
            id="kpi.extract.ambiguous_name",
            description="Ambiguous label 'Growth' without definition",
            scenario="ambiguous_kpi_names",
            input_fixture={"chunks": "c1: Growth was 12% this quarter."},
            expected_behavior="qualify_name_or_low_confidence",
            must_include=("12",),
        ),
        PromptEvalCase(
            id="kpi.extract.incorrect_units",
            description="Unit mismatch in source text must not be normalized away",
            scenario="incorrect_units",
            input_fixture={"chunks": "c1: Revenue 5 (unit unclear; labeled as both USD and EUR)."},
            expected_behavior="preserve_ambiguity_or_flag",
            notes="Do not invent a single currency.",
        ),
    ),
)

_DECISION_INTELLIGENCE = PromptSpec(
    id="di.decision_cards",
    version="part4-4i-v1",
    purpose="Produce Decision Intelligence cards, health score, timeline, and executive summary.",
    input_schema={
        "type": "object",
        "required": ["kpis", "evidence_map"],
        "properties": {
            "kpis": {"type": "array"},
            "evidence_map": {"type": "object"},
        },
    },
    output_schema={
        "type": "object",
        "required": ["executive_summary", "cards"],
        "properties": {
            "executive_summary": {"type": "string"},
            "health_score": {"type": "number"},
            "confidence": {"type": "number"},
            "timeline": {"type": "array"},
            "cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "what_happened",
                        "why_it_happened",
                        "recommendation",
                        "evidence_chunk_ids",
                    ],
                },
            },
        },
    },
    evidence_rules=(
        "evidence_chunk_ids must come from provided chunks.",
        "Distinguish evidence from inference in narrative.",
        "Never fabricate numbers.",
        "Use evidence_mode=insufficient when claims cannot be grounded.",
    ),
    failure_behavior=(
        "Skip invalid cards missing narrative/evidence; if none remain, raise ValidationError. "
        "Insufficient forecast history → null forecast_value with explanation."
    ),
    system_template=(
        "You are StratIQ Executive Decision Intelligence Analyst.\n"
        f"Prompt version: {REGISTRY_VERSION}\n\n"
        "For each KPI, produce a decision topic, KPI signal narrative inputs, root cause, "
        "business impact,\nrisks, opportunities, recommendation, expected outcome, and forecast.\n"
        "Distinguish evidence from inference. Never fabricate numbers.\n\n"
        "Return JSON only:\n"
        "{\n"
        '  "executive_summary": string,\n'
        '  "health_score": number 0-100,\n'
        '  "confidence": number 0-1,\n'
        '  "timeline": [{"title": string, "detail": string, "severity": "low"|"medium"|"high"}],\n'
        '  "cards": [{\n'
        '    "kpi_id": string,\n'
        '    "kpi_name": string,\n'
        '    "topic": string,\n'
        '    "trend": "up"|"down"|"flat",\n'
        '    "health": "healthy"|"watch"|"critical",\n'
        '    "what_happened": string,\n'
        '    "why_it_happened": string,\n'
        '    "business_impact": string,\n'
        '    "risks": [string],\n'
        '    "opportunities": [string],\n'
        '    "recommendation": string,\n'
        '    "expected_outcome": string,\n'
        '    "forecast_value": string|null,\n'
        '    "forecast_horizon": string|null,\n'
        '    "forecast_explanation": string|null,\n'
        '    "confidence": number 0-1,\n'
        '    "evidence_mode": "evidence"|"inference"|"insufficient",\n'
        '    "evidence_chunk_ids": [string],\n'
        '    "related_kpi_ids": [string]\n'
        "  }]\n"
        "}\n"
        "Rules:\n"
        "- topic: short decision framing (what leadership must decide).\n"
        "- expected_outcome: concrete result if the recommendation is followed.\n"
        "- evidence_chunk_ids must come from provided chunks.\n"
        "- Use evidence_mode=insufficient when evidence cannot support a claim.\n"
        "- Label inference explicitly in narrative when extrapolating.\n"
        "- If period history is insufficient for a forecast, set forecast_value and "
        "forecast_horizon to null and set forecast_explanation to a clear "
        "insufficient-history sentence.\n"
    ),
    eval_cases=(
        PromptEvalCase(
            id="di.decision_cards.missing_evidence_mode",
            description="Card without usable chunks must use insufficient mode",
            scenario="missing_evidence",
            input_fixture={"kpis": [], "evidence_map": {}},
            expected_behavior="insufficient_or_skip",
        ),
        PromptEvalCase(
            id="di.decision_cards.conflicting_kpi",
            description="Conflicting KPI signals require careful recommendation",
            scenario="conflicting_evidence",
            input_fixture={
                "kpis": [{"name": "Revenue", "value": "100"}, {"name": "Revenue", "value": "140"}],
            },
            expected_behavior="acknowledge_conflict",
        ),
    ),
)

_PROMPTS: dict[str, PromptSpec] = {
    _RAG_CHAT.id: _RAG_CHAT,
    _DOMAIN_DETECT.id: _DOMAIN_DETECT,
    _KPI_EXTRACT.id: _KPI_EXTRACT,
    _DECISION_INTELLIGENCE.id: _DECISION_INTELLIGENCE,
}

REQUIRED_EVAL_SCENARIOS = frozenset(
    {
        "correct_extraction",
        "missing_evidence",
        "conflicting_evidence",
        "ambiguous_kpi_names",
        "incorrect_units",
        "out_of_period",
    }
)


def get_prompt(prompt_id: str) -> PromptSpec:
    try:
        return _PROMPTS[prompt_id]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt id: {prompt_id}") from exc


def list_prompts() -> list[PromptSpec]:
    return list(_PROMPTS.values())


def list_prompt_summaries() -> list[dict[str, Any]]:
    return [
        {
            "id": p.id,
            "version": p.version,
            "qualified_id": p.qualified_id,
            "purpose": p.purpose,
            "evidence_rules": list(p.evidence_rules),
            "failure_behavior": p.failure_behavior,
            "eval_case_count": len(p.eval_cases),
            "eval_scenarios": sorted({c.scenario for c in p.eval_cases}),
        }
        for p in list_prompts()
    ]


def all_eval_cases() -> list[tuple[PromptSpec, PromptEvalCase]]:
    return [(p, c) for p in list_prompts() for c in p.eval_cases]


def covered_eval_scenarios() -> set[str]:
    return {c.scenario for _, c in all_eval_cases()}


def decision_intelligence_user(kpis: Any, evidence_map: dict[str, str]) -> str:
    """Build the DI user message from KPIs + evidence (shared with decisions service)."""
    lines = ["KPIs:"]
    for kpi in kpis:
        domain = kpi.domain.value if hasattr(kpi.domain, "value") else str(kpi.domain)
        evidence_ids = [str(x) for x in kpi.evidence_chunk_ids]
        lines.append(
            f"- id={kpi.id} name={kpi.name} value={kpi.value} unit={kpi.unit} "
            f"period={kpi.period} domain={domain} evidence={evidence_ids}"
        )
        evidence = evidence_map.get(str(kpi.id), "")
        if evidence:
            lines.append(f"  Evidence:\n{evidence}")
    return "\n".join(lines)


def validate_kpi_extract_payload(payload: dict[str, Any]) -> list[str]:
    """Return structural validation errors for kpi.extract output (empty = ok)."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be an object"]
    kpis = payload.get("kpis")
    if not isinstance(kpis, list):
        return ["missing kpis array"]
    for i, item in enumerate(kpis):
        if not isinstance(item, dict):
            errors.append(f"kpis[{i}] must be object")
            continue
        for key in ("name", "value", "domain", "evidence_chunk_ids"):
            if key not in item:
                errors.append(f"kpis[{i}] missing {key}")
        evidence = item.get("evidence_chunk_ids")
        if evidence is not None and not isinstance(evidence, list):
            errors.append(f"kpis[{i}].evidence_chunk_ids must be array")
    return errors


def validate_decision_payload(payload: dict[str, Any]) -> list[str]:
    """Return structural validation errors for di.decision_cards output."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be an object"]
    if not str(payload.get("executive_summary") or "").strip():
        errors.append("missing executive_summary")
    cards = payload.get("cards")
    if not isinstance(cards, list):
        errors.append("missing cards array")
        return errors
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            errors.append(f"cards[{i}] must be object")
            continue
        for key in ("what_happened", "why_it_happened", "recommendation"):
            if not str(card.get(key) or "").strip():
                errors.append(f"cards[{i}] missing {key}")
    return errors
