from collections.abc import Callable
from uuid import UUID

from sqlalchemy import and_, func, or_, select, union_all
from sqlalchemy.orm import Session, selectinload

from core.application.entity_discovery.contracts.entity_search_criteria import EntitySearchCriteria
from core.application.entity_discovery.contracts.project_environment_item import (
    ProjectEnvironmentItem,
)
from core.application.entity_discovery.contracts.project_link_item import ProjectLinkItem
from core.application.entity_discovery.contracts.project_search_item import ProjectSearchItem
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.knowledge_publication import KnowledgePublication
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.project_link import ProjectLinkModel
from core.infrastructure.postgres.models.relation import Relation
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.models.tenant import Tenant
from core.infrastructure.postgres.repositories.entity_search_repository import (
    PostgresEntitySearchRepository,
)
from core.infrastructure.postgres.repositories.snapshot_payload_reader import (
    SnapshotPayloadReader,
)


class KnowledgeReadRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._payload_reader = SnapshotPayloadReader()

    def tenants(
        self,
        *,
        tenant_id: str | None = None,
        key: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        statement = select(Tenant)
        if tenant_id is not None:
            statement = statement.where(Tenant.id == UUID(tenant_id))
        if key is not None:
            statement = statement.where(Tenant.key == key)
        if status is not None:
            statement = statement.where(Tenant.status == status)
        if query:
            pattern = self._pattern(query)
            statement = statement.where(
                or_(
                    Tenant.key.ilike(pattern),
                    Tenant.name.ilike(pattern),
                    Tenant.status.ilike(pattern),
                )
            )
        with self._session_factory() as session:
            rows = session.scalars(statement.order_by(Tenant.key).limit(limit).offset(offset)).all()
            return [self._tenant(tenant) for tenant in rows]

    def tenant(self, tenant_id: str) -> dict | None:
        with self._session_factory() as session:
            tenant = session.get(Tenant, UUID(tenant_id))
            return self._tenant(tenant) if tenant is not None else None

    def projects(
        self,
        tenant_id: str | None = None,
        *,
        key: str | None = None,
        name: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        statement = select(Project).options(selectinload(Project.environments))
        if tenant_id is not None:
            statement = statement.where(Project.tenant_id == UUID(tenant_id))
        if key is not None:
            statement = statement.where(Project.key == key)
        if name is not None:
            statement = statement.where(Project.name.ilike(self._pattern(name)))
        if query:
            pattern = self._pattern(query)
            statement = statement.where(
                or_(Project.key.ilike(pattern), Project.name.ilike(pattern))
            )
        with self._session_factory() as session:
            projects = session.scalars(
                statement.order_by(Project.tenant_id, Project.key).limit(limit).offset(offset)
            ).all()
            return [self._project(project) for project in projects]

    def project(self, tenant_id: str | None, project_key: str) -> dict | None:
        statement = select(Project).where(Project.key == project_key)
        if tenant_id is not None:
            statement = statement.where(Project.tenant_id == UUID(tenant_id))
        with self._session_factory() as session:
            matches = session.scalars(statement.order_by(Project.tenant_id)).all()
            if len(matches) > 1:
                raise ValueError("project key matches multiple tenants; provide tenant_id")
            return self._project(matches[0]) if matches else None

    def search_projects(
        self,
        scope: TenantScope,
        *,
        key: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[ProjectSearchItem, ...]:
        tenant_id = None if scope.is_admin else scope.tenant_id
        projects = self.projects(
            tenant_id,
            key=key,
            query=query,
            limit=limit,
            offset=offset,
        )
        project_ids = [UUID(project["id"]) for project in projects]
        environments: dict[UUID, list[ProjectEnvironmentItem]] = {
            project_id: [] for project_id in project_ids
        }
        links: dict[UUID, list[ProjectLinkItem]] = {project_id: [] for project_id in project_ids}
        tenant_keys: dict[str, str] = {}
        if project_ids:
            with self._session_factory() as session:
                tenant_keys = {
                    str(tenant_key_id): tenant_key
                    for tenant_key_id, tenant_key in session.execute(
                        select(Tenant.id, Tenant.key).where(
                            Tenant.id.in_([UUID(project["tenant_id"]) for project in projects])
                        )
                    ).all()
                }
                rows = session.execute(
                    select(
                        Environment.project_id,
                        Environment.name,
                        Environment.current_snapshot_id,
                        Environment.type,
                    )
                    .where(Environment.project_id.in_(project_ids))
                    .order_by(Environment.project_id, Environment.name)
                ).all()
                snapshot_ids = [
                    row.current_snapshot_id for row in rows if row.current_snapshot_id is not None
                ]
                counts = (
                    dict(
                        session.execute(
                            select(Entity.snapshot_id, func.count(Entity.id))
                            .where(
                                Entity.snapshot_id.in_(snapshot_ids),
                                Entity.project_id.in_(project_ids),
                            )
                            .group_by(Entity.snapshot_id)
                        ).all()
                    )
                    if snapshot_ids
                    else {}
                )
                for project_id, name, current_snapshot_id, environment_type in rows:
                    environments[project_id].append(
                        ProjectEnvironmentItem(
                            name=name,
                            current_snapshot_id=current_snapshot_id,
                            environment_type=environment_type,
                            entity_count=counts.get(current_snapshot_id, 0)
                            if current_snapshot_id is not None
                            else None,
                        )
                    )

                q1 = (
                    select(
                        ProjectLinkModel.project_a_id.label("source_project_id"),
                        Project.id.label("linked_project_id"),
                        Project.name.label("linked_project_name"),
                        Project.tenant_id.label("linked_tenant_id"),
                    )
                    .join(Project, Project.id == ProjectLinkModel.project_b_id)
                    .where(ProjectLinkModel.project_a_id.in_(project_ids))
                )
                q2 = (
                    select(
                        ProjectLinkModel.project_b_id.label("source_project_id"),
                        Project.id.label("linked_project_id"),
                        Project.name.label("linked_project_name"),
                        Project.tenant_id.label("linked_tenant_id"),
                    )
                    .join(Project, Project.id == ProjectLinkModel.project_a_id)
                    .where(ProjectLinkModel.project_b_id.in_(project_ids))
                )
                links_subquery = union_all(q1, q2).subquery()
                links_rows = session.execute(
                    select(
                        links_subquery.c.source_project_id,
                        links_subquery.c.linked_project_id,
                        links_subquery.c.linked_project_name,
                        links_subquery.c.linked_tenant_id,
                    )
                ).all()
                for source_id, linked_id, linked_name, linked_tenant_id in links_rows:
                    links[source_id].append(
                        ProjectLinkItem(
                            project_id=linked_id,
                            name=linked_name,
                            tenant_id=str(linked_tenant_id),
                        )
                    )
                for project_id in project_ids:
                    links[project_id].sort(
                        key=lambda item: (
                            item.name if item.name is not None else "",
                            str(item.project_id),
                        )
                    )
        return tuple(
            ProjectSearchItem(
                key=project["key"],
                tenant_id=project["tenant_id"],
                tenant_key=tenant_keys.get(project["tenant_id"]),
                project_id=UUID(project["id"]),
                environments=tuple(environments[UUID(project["id"])]),
                links=tuple(links[UUID(project["id"])]),
                name=project["name"],
                has_active_snapshot=project["active_snapshot_id"] is not None,
            )
            for project in projects
        )

    def snapshots(
        self,
        tenant_id: str | None,
        project_key: str,
        *,
        environment_id: UUID | None = None,
        revision: int | None = None,
        payload_hash: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict] | None:
        project = self.project(tenant_id, project_key)
        if project is None:
            return None
        with self._session_factory() as session:
            statement = select(Snapshot).where(Snapshot.project_id == UUID(project["id"]))
            if tenant_id is not None:
                statement = statement.where(Snapshot.tenant_id == UUID(tenant_id))
            if environment_id is not None:
                statement = statement.where(Snapshot.environment_id == environment_id)
            if revision is not None:
                statement = statement.where(Snapshot.revision == revision)
            if payload_hash is not None:
                statement = statement.where(Snapshot.payload_hash == payload_hash)
            rows = session.scalars(
                statement.order_by(Snapshot.created_at.desc(), Snapshot.id.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._snapshot(snapshot, include_payload=False) for snapshot in rows]

    def snapshot(self, tenant_id: str | None, snapshot_id: UUID) -> dict | None:
        statement = select(Snapshot).where(Snapshot.id == snapshot_id)
        if tenant_id is not None:
            statement = statement.where(Snapshot.tenant_id == UUID(tenant_id))
        with self._session_factory() as session:
            snapshot = session.scalar(statement)
            if snapshot is None:
                return None
            return self._snapshot(
                snapshot,
                include_payload=True,
                payload=self._payload_reader.read(session, snapshot),
            )

    def environments(
        self,
        *,
        tenant_id: str | None,
        project_key: str | None,
        name: str | None,
        environment_type: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        statement = select(Environment, Project.key).join(
            Project,
            and_(Project.id == Environment.project_id, Project.tenant_id == Environment.tenant_id),
        )
        if tenant_id is not None:
            statement = statement.where(Environment.tenant_id == UUID(tenant_id))
        if project_key is not None:
            statement = statement.where(Project.key == project_key)
        if name is not None:
            statement = statement.where(Environment.name == name)
        if environment_type is not None:
            statement = statement.where(Environment.type == environment_type)
        if query:
            pattern = self._pattern(query)
            statement = statement.where(
                or_(
                    Environment.name.ilike(pattern),
                    Environment.type.ilike(pattern),
                    Project.key.ilike(pattern),
                )
            )
        with self._session_factory() as session:
            rows = session.execute(
                statement.order_by(Environment.tenant_id, Project.key, Environment.name)
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._environment(environment, key) for environment, key in rows]

    def publications(
        self,
        *,
        tenant_id: str | None,
        project_key: str | None,
        environment_id: UUID | None,
        environment: str | None,
        status: str | None,
        version: str | None,
        deployment_id: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        statement = (
            select(KnowledgePublication, Project.key, Environment.name)
            .join(
                Project,
                and_(
                    Project.id == KnowledgePublication.project_id,
                    Project.tenant_id == KnowledgePublication.tenant_id,
                ),
            )
            .join(
                Environment,
                and_(
                    Environment.id == KnowledgePublication.environment_id,
                    Environment.tenant_id == KnowledgePublication.tenant_id,
                ),
            )
        )
        if tenant_id is not None:
            statement = statement.where(KnowledgePublication.tenant_id == UUID(tenant_id))
        if project_key is not None:
            statement = statement.where(Project.key == project_key)
        if environment_id is not None:
            statement = statement.where(KnowledgePublication.environment_id == environment_id)
        if environment is not None:
            statement = statement.where(Environment.name == environment)
        if status is not None:
            statement = statement.where(KnowledgePublication.status == status)
        if version is not None:
            statement = statement.where(KnowledgePublication.version == version)
        if deployment_id is not None:
            statement = statement.where(KnowledgePublication.deployment_id == deployment_id)
        if query:
            pattern = self._pattern(query)
            statement = statement.where(
                or_(
                    Project.key.ilike(pattern),
                    Environment.name.ilike(pattern),
                    KnowledgePublication.deployment_id.ilike(pattern),
                    KnowledgePublication.version.ilike(pattern),
                    KnowledgePublication.status.ilike(pattern),
                )
            )
        with self._session_factory() as session:
            rows = session.execute(
                statement.order_by(
                    KnowledgePublication.created_at.desc(), KnowledgePublication.id.desc()
                )
                .limit(limit)
                .offset(offset)
            ).all()
            return [
                self._publication(publication, key, environment_name)
                for publication, key, environment_name in rows
            ]

    def snapshot_search(
        self,
        *,
        tenant_id: str | None,
        project_key: str | None,
        environment_id: UUID | None,
        revision: int | None,
        schema_version: str | None,
        payload_hash: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        statement = select(Snapshot, Project.key).join(
            Project,
            and_(Project.id == Snapshot.project_id, Project.tenant_id == Snapshot.tenant_id),
        )
        if tenant_id is not None:
            statement = statement.where(Snapshot.tenant_id == UUID(tenant_id))
        if project_key is not None:
            statement = statement.where(Project.key == project_key)
        if environment_id is not None:
            statement = statement.where(Snapshot.environment_id == environment_id)
        if revision is not None:
            statement = statement.where(Snapshot.revision == revision)
        if schema_version is not None:
            statement = statement.where(Snapshot.schema_version == schema_version)
        if payload_hash is not None:
            statement = statement.where(Snapshot.payload_hash == payload_hash)
        with self._session_factory() as session:
            rows = session.execute(
                statement.order_by(Snapshot.created_at.desc(), Snapshot.id.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._snapshot_with_project(snapshot, key) for snapshot, key in rows]

    def entities(
        self,
        *,
        tenant_id: str | None,
        project_key: str | None,
        snapshot_id: UUID | None,
        entity_type: str | None,
        entity_key: str | None,
        name: str | None,
        query: str | None,
        limit: int,
        offset: int,
        include_history: bool = False,
        environment: str | None = None,
        project_id: UUID | None = None,
    ) -> list[dict]:
        try:
            selected_type = EntityType(entity_type) if entity_type is not None else None
        except ValueError:
            return []
        criteria = EntitySearchCriteria(
            key=entity_key,
            name=name,
            type=selected_type,
            project=project_key,
            query=query,
            tenant_id=tenant_id,
            project_id=project_id,
            snapshot_id=snapshot_id,
            environment=environment,
            include_history=include_history,
            allow_unfiltered=True,
        )
        selected = (
            PostgresEntitySearchRepository._statement(
                TenantScope(tenant_id or "*", is_admin=tenant_id is None),
                criteria,
                None,
                limit,
            )
            .limit(limit)
            .offset(offset)
            .subquery()
        )
        statement = (
            select(Entity, Project.key)
            .join(selected, Entity.id == selected.c.occurrence_id)
            .join(
                Project,
                and_(Project.id == Entity.project_id, Project.tenant_id == Entity.tenant_id),
            )
            .order_by(selected.c.entity_key, selected.c.occurrence_id)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).all()
            return [self._entity(entity, key) for entity, key in rows]

    def relations(
        self,
        *,
        tenant_id: str | None,
        project_key: str | None,
        snapshot_id: UUID | None,
        relation_type: str | None,
        provenance_kind: str | None,
        source_entity_id: UUID | None,
        target_entity_id: UUID | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        source = Entity.__table__.alias("source_entity")
        target = Entity.__table__.alias("target_entity")
        statement = (
            select(Relation, Project.key, source.c.entity_key, target.c.entity_key)
            .join(
                Snapshot,
                and_(Snapshot.id == Relation.snapshot_id, Snapshot.tenant_id == Relation.tenant_id),
            )
            .join(
                Project,
                and_(Project.id == Snapshot.project_id, Project.tenant_id == Relation.tenant_id),
            )
            .join(
                source,
                and_(
                    source.c.id == Relation.source_entity_id,
                    source.c.snapshot_id == Relation.snapshot_id,
                    source.c.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                target,
                and_(
                    target.c.id == Relation.target_entity_id,
                    target.c.snapshot_id == Relation.snapshot_id,
                    target.c.tenant_id == Relation.tenant_id,
                ),
            )
        )
        if tenant_id is not None:
            statement = statement.where(Relation.tenant_id == UUID(tenant_id))
        if project_key is not None:
            statement = statement.where(Project.key == project_key)
        if snapshot_id is not None:
            statement = statement.where(Relation.snapshot_id == snapshot_id)
        if relation_type is not None:
            statement = statement.where(Relation.relation_type == relation_type)
        if provenance_kind is not None:
            statement = statement.where(Relation.provenance_kind == provenance_kind)
        if source_entity_id is not None:
            statement = statement.where(Relation.source_entity_id == source_entity_id)
        if target_entity_id is not None:
            statement = statement.where(Relation.target_entity_id == target_entity_id)
        if query:
            pattern = self._pattern(query)
            statement = statement.where(
                or_(
                    Relation.relation_type.ilike(pattern),
                    Project.key.ilike(pattern),
                    source.c.entity_key.ilike(pattern),
                    target.c.entity_key.ilike(pattern),
                )
            )
        with self._session_factory() as session:
            rows = session.execute(
                statement.order_by(Relation.created_at.desc(), Relation.id)
                .limit(limit)
                .offset(offset)
            ).all()
            return [
                self._relation(relation, key, source_key, target_key)
                for relation, key, source_key, target_key in rows
            ]

    def evidence(
        self,
        *,
        tenant_id: str | None,
        project_key: str | None,
        snapshot_id: UUID | None,
        relation_id: UUID | None,
        source: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        statement = (
            select(Evidence, Project.key)
            .join(
                Snapshot,
                and_(Snapshot.id == Evidence.snapshot_id, Snapshot.tenant_id == Evidence.tenant_id),
            )
            .join(
                Project,
                and_(Project.id == Snapshot.project_id, Project.tenant_id == Evidence.tenant_id),
            )
        )
        if tenant_id is not None:
            statement = statement.where(Evidence.tenant_id == UUID(tenant_id))
        if project_key is not None:
            statement = statement.where(Project.key == project_key)
        if snapshot_id is not None:
            statement = statement.where(Evidence.snapshot_id == snapshot_id)
        if relation_id is not None:
            statement = statement.where(Evidence.relation_id == relation_id)
        if source is not None:
            statement = statement.where(Evidence.source.ilike(self._pattern(source)))
        if query:
            pattern = self._pattern(query)
            statement = statement.where(
                or_(
                    Evidence.source.ilike(pattern),
                    Evidence.excerpt.ilike(pattern),
                    Project.key.ilike(pattern),
                )
            )
        with self._session_factory() as session:
            rows = session.execute(
                statement.order_by(Evidence.created_at.desc(), Evidence.id)
                .limit(limit)
                .offset(offset)
            ).all()
            return [self._evidence(item, key) for item, key in rows]

    @staticmethod
    def _pattern(value: str) -> str:
        return f"%{value.strip()}%"

    @staticmethod
    def _environment(environment: Environment, project_key: str) -> dict:
        return {
            "id": str(environment.id),
            "tenant_id": str(environment.tenant_id),
            "project_id": str(environment.project_id),
            "project_key": project_key,
            "name": environment.name,
            "type": environment.type,
            "current_snapshot_id": (
                str(environment.current_snapshot_id) if environment.current_snapshot_id else None
            ),
            "metadata": environment.metadata_json,
            "created_at": environment.created_at.isoformat(),
            "updated_at": environment.updated_at.isoformat(),
        }

    @staticmethod
    def _publication(publication: KnowledgePublication, project_key: str, environment: str) -> dict:
        return {
            "id": str(publication.id),
            "tenant_id": str(publication.tenant_id),
            "project_id": str(publication.project_id),
            "project_key": project_key,
            "environment_id": str(publication.environment_id),
            "environment": environment,
            "deployment_id": publication.deployment_id,
            "version": publication.version,
            "status": publication.status,
            "snapshot_id": str(publication.snapshot_id) if publication.snapshot_id else None,
            "metadata": publication.metadata_json,
            "created_at": publication.created_at.isoformat(),
        }

    @staticmethod
    def _snapshot_with_project(snapshot: Snapshot, project_key: str) -> dict:
        result = KnowledgeReadRepository._snapshot(snapshot, include_payload=False)
        result["project_key"] = project_key
        return result

    @staticmethod
    def _entity(entity: Entity, project_key: str) -> dict:
        return {
            "id": str(entity.id),
            "tenant_id": str(entity.tenant_id),
            "project_id": str(entity.project_id),
            "project_key": project_key,
            "snapshot_id": str(entity.snapshot_id),
            "identity_id": str(entity.identity_id) if entity.identity_id else None,
            "entity_key": entity.entity_key,
            "entity_type": entity.entity_type,
            "name": entity.name,
            "metadata": entity.metadata_json,
            "created_at": entity.created_at.isoformat(),
        }

    @staticmethod
    def _relation(relation: Relation, project_key: str, source_key: str, target_key: str) -> dict:
        return {
            "id": str(relation.id),
            "tenant_id": str(relation.tenant_id),
            "project_key": project_key,
            "snapshot_id": str(relation.snapshot_id),
            "source_entity_id": str(relation.source_entity_id),
            "source_entity_key": source_key,
            "target_entity_id": str(relation.target_entity_id),
            "target_entity_key": target_key,
            "source_identity_id": (
                str(relation.source_identity_id) if relation.source_identity_id else None
            ),
            "target_identity_id": (
                str(relation.target_identity_id) if relation.target_identity_id else None
            ),
            "relation_type": relation.relation_type,
            "provenance_kind": relation.provenance_kind,
            "metadata": relation.metadata_json,
            "created_at": relation.created_at.isoformat(),
        }

    @staticmethod
    def _evidence(evidence: Evidence, project_key: str) -> dict:
        return {
            "id": str(evidence.id),
            "tenant_id": str(evidence.tenant_id),
            "project_key": project_key,
            "snapshot_id": str(evidence.snapshot_id),
            "relation_id": str(evidence.relation_id) if evidence.relation_id else None,
            "source": evidence.source,
            "excerpt": evidence.excerpt,
            "metadata": evidence.metadata_json,
            "created_at": evidence.created_at.isoformat(),
        }

    @staticmethod
    def _tenant(tenant: Tenant) -> dict:
        return {
            "id": str(tenant.id),
            "key": tenant.key,
            "name": tenant.name,
            "status": tenant.status,
            "metadata": tenant.metadata_json,
        }

    @staticmethod
    def _project(project: Project) -> dict:
        return {
            "id": str(project.id),
            "tenant_id": str(project.tenant_id),
            "key": project.key,
            "name": project.name,
            "active_snapshot_id": (
                str(project.active_snapshot_id) if project.active_snapshot_id else None
            ),
            "metadata": project.metadata_json,
        }

    @staticmethod
    def _snapshot(
        snapshot: Snapshot, *, include_payload: bool, payload: dict | None = None
    ) -> dict:
        result = {
            "id": str(snapshot.id),
            "project_id": str(snapshot.project_id),
            "tenant_id": str(snapshot.tenant_id),
            "environment_id": (str(snapshot.environment_id) if snapshot.environment_id else None),
            "revision": snapshot.revision,
            "schema_version": snapshot.schema_version,
            "payload_hash": snapshot.payload_hash,
            "created_at": snapshot.created_at.isoformat(),
        }
        if include_payload and payload is not None:
            result["payload"] = payload
        return result
