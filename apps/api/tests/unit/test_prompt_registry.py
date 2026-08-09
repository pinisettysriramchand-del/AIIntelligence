"""Stage 4I: prompt registry governance + eval coverage."""

from __future__ import annotations

import pytest

from stratiq.infrastructure.ai import prompts
from stratiq.infrastructure.ai.prompt_registry import (
    REGISTRY_VERSION,
    REQUIRED_EVAL_SCENARIOS,
    covered_eval_scenarios,
    get_prompt,
    list_prompts,
    validate_decision_payload,
    validate_kpi_extract_payload,
)


def test_registry_lists_production_prompts():
    ids = {p.id for p in list_prompts()}
    assert ids == {"rag.chat", "kpi.domain_detect", "kpi.extract", "di.decision_cards"}


def test_each_prompt_has_governance_fields():
    for spec in list_prompts():
        assert spec.id
        assert spec.version
        assert spec.purpose
        assert spec.input_schema
        assert spec.output_schema
        assert spec.evidence_rules
        assert spec.failure_behavior
        assert spec.qualified_id == f"{spec.id}@{spec.version}"


def test_required_eval_scenarios_are_covered():
    covered = covered_eval_scenarios()
    missing = REQUIRED_EVAL_SCENARIOS - covered
    assert not missing, f"Missing eval scenarios: {sorted(missing)}"


def test_prompt_version_alias_matches_registry():
    assert prompts.PROMPT_VERSION == REGISTRY_VERSION
    assert get_prompt("di.decision_cards").version == REGISTRY_VERSION


def test_kpi_extract_schema_validator():
    ok = {
        "kpis": [
            {
                "name": "Revenue",
                "value": "100",
                "domain": "financial",
                "evidence_chunk_ids": ["c1"],
            }
        ]
    }
    assert validate_kpi_extract_payload(ok) == []
    bad = {"kpis": [{"name": "Revenue"}]}
    errors = validate_kpi_extract_payload(bad)
    assert any("evidence_chunk_ids" in e for e in errors)


def test_decision_schema_validator():
    ok = {
        "executive_summary": "Stable.",
        "cards": [
            {
                "what_happened": "x",
                "why_it_happened": "y",
                "recommendation": "z",
                "evidence_chunk_ids": ["c1"],
            }
        ],
    }
    assert validate_decision_payload(ok) == []
    assert "missing executive_summary" in validate_decision_payload({"cards": []})


def test_eval_case_must_include_checks_for_rag_missing_evidence():
    spec = get_prompt("rag.chat")
    case = next(c for c in spec.eval_cases if c.scenario == "missing_evidence")
    reply = (
        "Insufficient evidence in uploaded documents to answer this question. "
        "Upload relevant business documents."
    )
    for needle in case.must_include:
        assert needle.lower() in reply.lower()
    for banned in case.must_not_include:
        assert banned not in reply


def test_render_user_templates():
    domain = get_prompt("kpi.domain_detect").render_user(text="Revenue rose.")
    assert "Revenue rose." in domain
    kpi = get_prompt("kpi.extract").render_user(chunks="c1: margin 10%")
    assert "c1: margin 10%" in kpi


@pytest.mark.asyncio
async def test_prompts_api_lists_registry(auth_client):
    client, headers = auth_client
    response = await client.get("/api/v1/ai/prompts", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["registry_version"] == REGISTRY_VERSION
    ids = {p["id"] for p in body["prompts"]}
    assert "kpi.extract" in ids
    assert "di.decision_cards" in ids

    detail = await client.get("/api/v1/ai/prompts/kpi.extract", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["eval_cases"]
    assert detail.json()["output_schema"]["required"] == ["kpis"]
