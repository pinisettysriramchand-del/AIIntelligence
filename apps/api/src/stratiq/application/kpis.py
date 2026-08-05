"""KPI use-cases: list, get, filter by domain."""

from __future__ import annotations

import uuid
from typing import Any

from stratiq.domain.entities import KPI
from stratiq.domain.enums import KPIDomain
from stratiq.domain.exceptions import AuthorizationError, NotFoundError


class KPIService:
    def __init__(self, kpi_repo: "KPIRepository") -> None:  # noqa: F821
        self._repo = kpi_repo

    async def list_kpis(
        self,
        owner_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        domain: KPIDomain | None = None,
    ) -> list[KPI]:
        return await self._repo.list_by_owner(owner_id, document_id=document_id, domain=domain)

    async def get_kpi(self, kpi_id: uuid.UUID, owner_id: uuid.UUID) -> KPI:
        kpi = await self._repo.get_by_id(kpi_id)
        if kpi is None:
            raise NotFoundError("KPI", kpi_id)
        if kpi.owner_id != owner_id:
            raise AuthorizationError("You do not own this KPI.")
        return kpi

    async def get_evidence_chunks(
        self, kpi_id: uuid.UUID, owner_id: uuid.UUID, chunk_repo: "ChunkRepository"  # noqa: F821
    ) -> list[Any]:
        kpi = await self.get_kpi(kpi_id, owner_id)
        return await chunk_repo.get_by_ids(kpi.evidence_chunk_ids)
