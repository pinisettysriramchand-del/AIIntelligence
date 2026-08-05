from pydantic import BaseModel, Field


class GenerateDecisionsRequest(BaseModel):
    document_id: str | None = None


class DecisionCardResponse(BaseModel):
    id: str
    kpi_id: str
    document_id: str
    kpi_name: str
    current_value: str
    unit: str | None = None
    period: str | None = None
    domain: str | None = None
    trend: str
    health: str
    what_happened: str
    why_it_happened: str
    risks: list[str]
    opportunities: list[str]
    recommendation: str
    forecast_value: str | None = None
    forecast_horizon: str | None = None
    forecast_explanation: str | None = None
    evidence_chunk_ids: list[str]
    related_kpi_ids: list[str] = Field(default_factory=list)


class ExecutiveReportResponse(BaseModel):
    id: str
    summary: str
    health_score: int
    health_label: str
    timeline: list[dict]
    document_id: str | None = None


class GenerateDecisionsResponse(BaseModel):
    report: ExecutiveReportResponse
    cards: list[DecisionCardResponse]


class ForecastResponse(BaseModel):
    kpi_id: str
    kpi_name: str
    current_value: str
    unit: str | None = None
    forecast_value: str | None = None
    forecast_horizon: str | None = None
    forecast_explanation: str | None = None
    trend: str
