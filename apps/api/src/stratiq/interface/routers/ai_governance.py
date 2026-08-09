"""Prompt registry introspection API (Part 4 Stage 4I)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from stratiq.infrastructure.ai.prompt_registry import (
    REGISTRY_VERSION,
    get_prompt,
    list_prompt_summaries,
)
from stratiq.interface.deps import CurrentUser

router = APIRouter(prefix="/ai", tags=["ai-governance"])


class PromptSummaryResponse(BaseModel):
    id: str
    version: str
    qualified_id: str
    purpose: str
    evidence_rules: list[str]
    failure_behavior: str
    eval_case_count: int
    eval_scenarios: list[str]


class PromptRegistryResponse(BaseModel):
    registry_version: str
    prompts: list[PromptSummaryResponse]


class PromptDetailResponse(BaseModel):
    id: str
    version: str
    qualified_id: str
    purpose: str
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    evidence_rules: list[str]
    failure_behavior: str
    eval_cases: list[dict]


@router.get("/prompts", response_model=PromptRegistryResponse)
async def list_registered_prompts(_user: CurrentUser) -> PromptRegistryResponse:
    summaries = [PromptSummaryResponse(**row) for row in list_prompt_summaries()]
    return PromptRegistryResponse(registry_version=REGISTRY_VERSION, prompts=summaries)


@router.get("/prompts/{prompt_id}", response_model=PromptDetailResponse)
async def get_registered_prompt(prompt_id: str, _user: CurrentUser) -> PromptDetailResponse:
    try:
        spec = get_prompt(prompt_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PromptDetailResponse(
        id=spec.id,
        version=spec.version,
        qualified_id=spec.qualified_id,
        purpose=spec.purpose,
        input_schema=spec.input_schema,
        output_schema=spec.output_schema,
        evidence_rules=list(spec.evidence_rules),
        failure_behavior=spec.failure_behavior,
        eval_cases=[
            {
                "id": c.id,
                "description": c.description,
                "scenario": c.scenario,
                "expected_behavior": c.expected_behavior,
                "must_include": list(c.must_include),
                "must_not_include": list(c.must_not_include),
                "notes": c.notes,
            }
            for c in spec.eval_cases
        ],
    )
