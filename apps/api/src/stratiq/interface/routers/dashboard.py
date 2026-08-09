"""Dashboard router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from stratiq.application.dashboard import DashboardService
from stratiq.interface.deps import CurrentUser, get_dashboard_service
from stratiq.interface.schemas.dashboard import DashboardResponse, DomainSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: CurrentUser,
    dashboard_svc: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    summary = await dashboard_svc.get_summary(current_user.id)
    return DashboardResponse(
        total_kpis=summary["total_kpis"],
        domains=[
            DomainSummary(
                domain=d["domain"],
                kpi_count=d["kpi_count"],
                kpis=d["kpis"],
            )
            for d in summary["domains"]
        ],
        data_quality_warnings=summary.get("data_quality_warnings") or [],
    )
