from typing import Protocol
from uuid import UUID

from core.domain.environment.aggregates.environment import Environment


class EnvironmentRepository(Protocol):
    def resolve(self, project_key: str, name: str, tenant_id: str | None) -> Environment | None:
        ...

    def promote_active_snapshot(self, env_id: UUID, snap_id: UUID, tenant_id: str) -> None:
        ...

    def resolve_or_create(self, project_key: str, name: str, tenant_id: str) -> Environment:
        ...
