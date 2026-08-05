from fastapi import APIRouter, Depends

from stratiq.domain.entities import User
from stratiq.interface.deps import Services, get_current_user, get_services
from stratiq.interface.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> DashboardResponse:
    payload = await services.dashboard.build(user.id)
    return DashboardResponse(**payload)
