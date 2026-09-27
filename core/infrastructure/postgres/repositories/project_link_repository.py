from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.application.ports.project_link_repository import ProjectLinkRepository
from core.domain.project_link.dtos.linked_project_summary import LinkedProjectSummary
from core.domain.project_link.entities.project_link import ProjectLink
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.project_link import ProjectLinkModel


class PostgresProjectLinkRepository(ProjectLinkRepository):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create_link(
        self, pair: CanonicalProjectPair, created_by: UUID | None = None
    ) -> ProjectLink:
        try:
            with self._session_factory() as session, session.begin():
                model = ProjectLinkModel(
                    id=uuid4(),
                    project_a_id=pair.project_a_id,
                    project_b_id=pair.project_b_id,
                    created_by=created_by,
                    created_at=datetime.now(UTC),
                )
                session.add(model)
                session.flush()
                return ProjectLink(
                    id=model.id,
                    pair=pair,
                    created_by=model.created_by,
                    created_at=model.created_at,
                )
        except IntegrityError as error:
            raise ValueError("project link already exists") from error

    def get_link(self, pair: CanonicalProjectPair) -> ProjectLink | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(ProjectLinkModel).where(
                    ProjectLinkModel.project_a_id == pair.project_a_id,
                    ProjectLinkModel.project_b_id == pair.project_b_id,
                )
            )
            if model is None:
                return None
            return ProjectLink(
                id=model.id,
                pair=pair,
                created_by=model.created_by,
                created_at=model.created_at,
            )

    def delete_link(self, pair: CanonicalProjectPair) -> bool:
        with self._session_factory() as session, session.begin():
            result = session.execute(
                delete(ProjectLinkModel).where(
                    ProjectLinkModel.project_a_id == pair.project_a_id,
                    ProjectLinkModel.project_b_id == pair.project_b_id,
                )
            )
            return bool(result.rowcount and result.rowcount > 0)

    def list_links_for_project(self, project_id: UUID) -> list[LinkedProjectSummary]:
        with self._session_factory() as session:
            links = session.scalars(
                select(ProjectLinkModel).where(
                    or_(
                        ProjectLinkModel.project_a_id == project_id,
                        ProjectLinkModel.project_b_id == project_id,
                    )
                )
            ).all()
            if not links:
                return []
            target_project_ids = [
                link.project_b_id if link.project_a_id == project_id else link.project_a_id
                for link in links
            ]
            projects = session.scalars(
                select(Project).where(Project.id.in_(target_project_ids))
            ).all()
            return [
                LinkedProjectSummary(
                    project_id=p.id,
                    key=p.key,
                    name=p.name,
                    tenant_id=p.tenant_id,
                )
                for p in projects
            ]
