from typing import Protocol
from uuid import UUID

from core.domain.environment.aggregates.environment import Environment


class EnvironmentRepository(Protocol):
    def get_entity_summary(self, snapshot_id: UUID, tenant_id: str | None) -> dict: ...

    def resolve(self, project_key: str, name: str, tenant_id: str | None) -> Environment | None: ...

    def resolve_or_create(self, project_key: str, name: str, tenant_id: str) -> Environment: ...

    def create_for_project(self, tenant_id: str, project_key: str, name: str) -> Environment: ...
