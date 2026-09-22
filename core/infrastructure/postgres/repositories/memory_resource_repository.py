from collections import defaultdict
from hashlib import sha256
import json
from typing import Callable

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from core.application.mcp_access_surface.contracts.snapshot_context_item import SnapshotContextItem
from core.application.mcp_access_surface.contracts.snapshot_fact_page import SnapshotFactPage
from core.application.mcp_access_surface.contracts.snapshot_resource_input import (
    SnapshotResourceInput,
)
from core.application.mcp_access_surface.errors.resource_not_found import ResourceNotFound
from core.application.mcp_access_surface.errors.resource_query_failure import ResourceQueryFailure
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds
from core.application.mcp_access_surface.use_cases.get_project_resource.outbound import (
    ProjectResourceOutput,
)
from core.application.mcp_access_surface.use_cases.get_snapshot_resource.outbound import (
    SnapshotResourceOutput,
)
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.contracts.relation_view import RelationView
from core.application.relationship_context.types.relationship_direction import RelationshipDirection

from ..models.entity import Entity
from ..models.evidence import Evidence
from ..models.project import Project
from ..models.relation import Relation
from ..models.snapshot import Snapshot


class PostgresMemoryResourceRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        engine=None,
        session: Session | None = None,
    ):
        if session_factory is not None and not callable(session_factory):
            session = session_factory
            session_factory = None
        if session is not None and session_factory is None:

            def session_factory():
                return session

        if session_factory is None and engine is not None:
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory

    def get_snapshot_entity_fingerprints(
        self, snapshot_id, tenant_id: str | None = None
    ) -> dict[str, str]:
        if tenant_id is None:
            raise ValueError("tenant_id is required")
        with self._session_factory() as session:
            entities = session.scalars(
                select(Entity)
                .where(Entity.snapshot_id == snapshot_id, Entity.tenant_id == tenant_id)
                .order_by(Entity.entity_key.asc())
            ).all()
        return {
            entity.entity_key: sha256(
                json.dumps(
                    {
                        "type": entity.entity_type,
                        "name": entity.name,
                        "metadata": entity.metadata_json or {},
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            for entity in entities
        }

    def load_active_project(
        self,
        request: ProjectResourceInput,
        tenant: TenantScope,
        bounds: ResourceReadBounds,
    ) -> ProjectResourceOutput:
        query = (
            request
            if isinstance(request, ProjectResourceInput)
            else ProjectResourceInput.model_validate(request)
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    row = session.execute(
                        select(Project, Snapshot)
                        .join(
                            Snapshot,
                            and_(
                                Snapshot.id == Project.active_snapshot_id,
                                Snapshot.project_id == Project.id,
                                Snapshot.tenant_id == Project.tenant_id,
                            ),
                        )
                        .where(
                            Project.tenant_id == tenant.tenant_id,
                            Project.key == query.project_key,
                        )
                    ).first()
                    if row is None:
                        raise ResourceNotFound()
                    project, snapshot = row
                    entities = session.execute(
                        select(Entity)
                        .where(
                            Entity.tenant_id == tenant.tenant_id,
                            Entity.project_id == project.id,
                            Entity.snapshot_id == snapshot.id,
                        )
                        .order_by(Entity.entity_key.asc(), Entity.id.asc())
                        .limit(bounds.fact_limit + 1)
                    ).scalars().all()
                    return ProjectResourceOutput(
                        project=self._project_context(project, snapshot),
                        entities=tuple(
                            self._map_entity(entity) for entity in entities[: bounds.fact_limit]
                        ),
                        entities_truncated=len(entities) > bounds.fact_limit,
                    )
        except (ResourceNotFound, ResourceQueryFailure):
            raise
        except Exception as error:
            raise ResourceQueryFailure(str(error)) from None

    def load_snapshot(
        self,
        request: SnapshotResourceInput,
        tenant: TenantScope,
        bounds: ResourceReadBounds,
    ) -> SnapshotResourceOutput:
        query = (
            request
            if isinstance(request, SnapshotResourceInput)
            else SnapshotResourceInput.model_validate(request)
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    row = session.execute(
                        select(Snapshot, Project)
                        .join(
                            Project,
                            and_(
                                Project.id == Snapshot.project_id,
                                Project.tenant_id == Snapshot.tenant_id,
                            ),
                        )
                        .where(
                            Snapshot.id == query.snapshot_id,
                            Snapshot.tenant_id == tenant.tenant_id,
                        )
                    ).first()
                    if row is None:
                        raise ResourceNotFound()
                    snapshot, project = row
                    entity_rows = session.execute(
                        select(Entity)
                        .where(
                            Entity.tenant_id == tenant.tenant_id,
                            Entity.snapshot_id == snapshot.id,
                        )
                        .order_by(Entity.entity_key.asc(), Entity.id.asc())
                        .limit(bounds.fact_limit + 1)
                    ).scalars().all()
                    entities = tuple(
                        self._map_entity(entity) for entity in entity_rows[: bounds.fact_limit]
                    )

                    source = aliased(Entity, name="snapshot_source")
                    target = aliased(Entity, name="snapshot_target")
                    relation_rows = session.execute(
                        select(Relation, source, target)
                        .join(
                            source,
                            and_(
                                source.id == Relation.source_entity_id,
                                source.snapshot_id == Relation.snapshot_id,
                                source.tenant_id == Relation.tenant_id,
                            ),
                        )
                        .join(
                            target,
                            and_(
                                target.id == Relation.target_entity_id,
                                target.snapshot_id == Relation.snapshot_id,
                                target.tenant_id == Relation.tenant_id,
                            ),
                        )
                        .where(
                            Relation.tenant_id == tenant.tenant_id,
                            Relation.snapshot_id == snapshot.id,
                        )
                        .order_by(
                            Relation.relation_type.asc(),
                            source.entity_key.asc(),
                            target.entity_key.asc(),
                            Relation.id.asc(),
                        )
                        .limit(bounds.fact_limit + 1)
                    ).all()
                    selected_relations = relation_rows[: bounds.fact_limit]
                    evidence_rows = session.execute(
                        select(Evidence)
                        .where(
                            Evidence.tenant_id == tenant.tenant_id,
                            Evidence.snapshot_id == snapshot.id,
                        )
                        .order_by(Evidence.id.asc())
                        .limit(bounds.evidence_limit + 1)
                    ).scalars().all()
                    evidence = tuple(
                        self._map_evidence(item)
                        for item in evidence_rows[: bounds.evidence_limit]
                    )
                    evidence_by_relation = defaultdict(list)
                    for item in evidence:
                        source_row = next(
                            (
                                row_item
                                for row_item in evidence_rows[: bounds.evidence_limit]
                                if row_item.id == item.id
                            ),
                            None,
                        )
                        if source_row is not None and source_row.relation_id is not None:
                            evidence_by_relation[source_row.relation_id].append(item)
                    relations = tuple(
                        RelationView(
                            id=relation.id,
                            type=relation.relation_type,
                            direction=RelationshipDirection.BOTH,
                            source=self._map_entity(source_entity),
                            target=self._map_entity(target_entity),
                            provenance=relation.provenance_kind,
                            metadata=relation.metadata_json or {},
                            evidence=tuple(evidence_by_relation.get(relation.id, ())),
                        )
                        for relation, source_entity, target_entity in selected_relations
                    )
                    return SnapshotResourceOutput(
                        snapshot=SnapshotContextItem(
                            id=snapshot.id,
                            project_key=project.key,
                            revision=snapshot.revision,
                            schema_version=snapshot.schema_version,
                            payload_hash=snapshot.payload_hash,
                            metadata=snapshot.metadata_json or {},
                            created_at=snapshot.created_at,
                        ),
                        facts=SnapshotFactPage(
                            entities=entities,
                            relations=relations,
                            evidence=evidence,
                            entities_truncated=len(entity_rows) > bounds.fact_limit,
                            relations_truncated=len(relation_rows) > bounds.fact_limit,
                            evidence_truncated=len(evidence_rows) > bounds.evidence_limit,
                        ),
                    )
        except (ResourceNotFound, ResourceQueryFailure):
            raise
        except Exception as error:
            raise ResourceQueryFailure(str(error)) from None

    @staticmethod
    def _project_context(project: Project, snapshot: Snapshot):
        from core.application.relationship_context.contracts.project_context_item import (
            ProjectContextItem,
        )

        return ProjectContextItem(
            key=project.key,
            name=project.name,
            snapshot_id=snapshot.id,
            revision=snapshot.revision,
        )

    @staticmethod
    def _map_entity(entity: Entity) -> EntityContextItem:
        return EntityContextItem(
            id=entity.id,
            key=entity.entity_key,
            name=entity.name,
            type=entity.entity_type,
            metadata=entity.metadata_json or {},
        )

    @staticmethod
    def _map_evidence(evidence: Evidence) -> EvidenceView:
        return EvidenceView(
            id=evidence.id,
            source=evidence.source,
            excerpt=evidence.excerpt,
            metadata=evidence.metadata_json or {},
        )
