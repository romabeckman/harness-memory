from typing import Protocol

from core.domain.environment.aggregates.environment import Environment


class EnvironmentRepository(Protocol):
    def resolve(self, project_key: str, name: str, tenant_id: str | None) -> Environment | None: ...

    def resolve_or_create(self, project_key: str, name: str, tenant_id: str) -> Environment: ...

    def create_for_project(self, tenant_id: str, project_key: str, name: str) -> Environment: ...
