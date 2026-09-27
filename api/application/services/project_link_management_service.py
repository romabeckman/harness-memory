from uuid import UUID

from api.application.ports.project_link_repository import ProjectLinkRepository
from api.application.ports.tenant_project_management_repository import (
    TenantProjectManagementRepository,
)
from core.domain.project_link.dtos.linked_project_summary import LinkedProjectSummary
from core.domain.project_link.entities.project_link import ProjectLink
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair


class ProjectLinkManagementService:
    def __init__(
        self,
        project_link_repository: ProjectLinkRepository,
        project_repository: TenantProjectManagementRepository,
    ) -> None:
        self._link_repo = project_link_repository
        self._project_repo = project_repository

    def create_link(
        self,
        origin_tenant_id: UUID,
        origin_key: str,
        target_key: str,
        target_tenant_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> ProjectLink:
        origin_project = self._project_repo.get_project(origin_tenant_id, origin_key)
        if origin_project is None:
            raise LookupError("project not found")

        effective_target_tenant_id = (
            target_tenant_id if target_tenant_id is not None else origin_tenant_id
        )
        target_project = self._project_repo.get_project(effective_target_tenant_id, target_key)
        if target_project is None:
            raise LookupError("project not found")

        origin_id = UUID(origin_project["id"])
        target_id = UUID(target_project["id"])

        if origin_id == target_id:
            raise ValueError("cannot link project to itself")

        pair = CanonicalProjectPair(origin_id, target_id)
        if self._link_repo.get_link(pair) is not None:
            raise ValueError("project link already exists")

        return self._link_repo.create_link(pair, created_by)

    def delete_link(
        self,
        origin_tenant_id: UUID,
        origin_key: str,
        target_key: str,
        target_tenant_id: UUID | None = None,
    ) -> None:
        origin_project = self._project_repo.get_project(origin_tenant_id, origin_key)
        if origin_project is None:
            raise LookupError("project not found")

        effective_target_tenant_id = (
            target_tenant_id if target_tenant_id is not None else origin_tenant_id
        )
        target_project = self._project_repo.get_project(effective_target_tenant_id, target_key)
        if target_project is None:
            raise LookupError("project not found")

        origin_id = UUID(origin_project["id"])
        target_id = UUID(target_project["id"])

        if origin_id == target_id:
            raise ValueError("cannot link project to itself")

        pair = CanonicalProjectPair(origin_id, target_id)
        if not self._link_repo.delete_link(pair):
            raise LookupError("project link not found")

    def list_links(self, origin_tenant_id: UUID, origin_key: str) -> list[LinkedProjectSummary]:
        origin_project = self._project_repo.get_project(origin_tenant_id, origin_key)
        if origin_project is None:
            raise LookupError("project not found")

        origin_id = UUID(origin_project["id"])
        return self._link_repo.list_links_for_project(origin_id)
