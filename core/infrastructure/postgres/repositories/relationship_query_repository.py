from collections import defaultdict
from typing import Callable

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.contracts.dependency_view import DependencyView
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.application.relationship_context.contracts.relation_view import RelationView
from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.relationship_context.types.dependency_relation_type import (
    DependencyRelationType,
)
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from core.application.relationship_context.use_cases.get_context.outbound import GetContextOutput
from core.application.relationship_context.use_cases.get_dependencies.inbound import (
    GetDependenciesInput,
)
from core.application.relationship_context.use_cases.get_dependencies.outbound import (
    GetDependenciesOutput,
)
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.relation_type import RelationType

from ..models.entity import Entity
from ..models.evidence import Evidence
from ..models.project import Project
from ..models.relation import Relation
from ..models.snapshot import Snapshot
from .tenant_scope_predicate import tenant_scope_predicate


class PostgresRelationshipQueryRepository:
    _DEPENDENCY_TYPES = tuple(item.value for item in DependencyRelationType)

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

    def load_context(self, scope: TenantScope, query: GetContextInput) -> GetContextOutput:
        request = (
            query
            if isinstance(query, GetContextInput)
            else GetContextInput.model_validate(query)
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    entity, project, snapshot = self._resolve_entity(
                        session, scope, request.entity_id
                    )
                    relation_rows = self._load_relations(
                        session, scope, snapshot.id, entity.id, request.limit
                    )
                    dependency_rows = self._load_relations(
                        session,
                        scope,
                        snapshot.id,
                        entity.id,
                        request.limit,
                        dependency_only=True,
                    )
                    relation_views = self._map_relations(
                        relation_rows[: request.limit],
                        entity.id,
                        self._load_evidence(
                            session,
                            scope,
                            snapshot.id,
                            relation_rows[: request.limit],
                            request.evidence_limit,
                        ),
                    )
                    dependency_views = self._map_dependencies(
                        dependency_rows[: request.limit],
                        entity.id,
                        self._load_evidence(
                            session,
                            scope,
                            snapshot.id,
                            dependency_rows[: request.limit],
                            request.evidence_limit,
                        ),
                    )
                    owners = tuple(
                        relation.target
                        for relation in relation_views
                        if relation.type is RelationType.OWNED_BY
                        and relation.direction is RelationshipDirection.OUTBOUND
                        and relation.target.type is EntityType.TEAM
                    )
                    return GetContextOutput(
                        entity=self._map_entity(entity),
                        project=ProjectContextItem(
                            key=project.key,
                            name=project.name,
                            snapshot_id=snapshot.id,
                            revision=snapshot.revision,
                        ),
                        owners=owners,
                        relations=tuple(relation_views),
                        dependencies=tuple(dependency_views),
                        relations_truncated=len(relation_rows) > request.limit,
                        dependencies_truncated=len(dependency_rows) > request.limit,
                    )
        except (EntityContextNotFound, RelationshipQueryFailure):
            raise
        except Exception as error:
            raise RelationshipQueryFailure(str(error)) from None

    def load_dependencies(
        self, scope: TenantScope, query: GetDependenciesInput
    ) -> GetDependenciesOutput:
        request = (
            query
            if isinstance(query, GetDependenciesInput)
            else GetDependenciesInput.model_validate(query)
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    entity, _, snapshot = self._resolve_entity(session, scope, request.entity_id)
                    rows = self._load_relations(
                        session,
                        scope,
                        snapshot.id,
                        entity.id,
                        request.limit,
                        dependency_only=True,
                        direction=request.direction,
                    )
                    evidence = self._load_evidence(
                        session, scope, snapshot.id, rows[: request.limit], request.evidence_limit
                    )
                    items = self._map_dependencies(rows[: request.limit], entity.id, evidence)
                    return GetDependenciesOutput(
                        entity=self._map_entity(entity),
                        items=tuple(items),
                        truncated=len(rows) > request.limit,
                    )
        except (EntityContextNotFound, RelationshipQueryFailure):
            raise
        except Exception as error:
            raise RelationshipQueryFailure(str(error)) from None

    @staticmethod
    def _resolve_entity(session: Session, scope: TenantScope, entity_id):
        result = session.execute(
            select(Entity, Project, Snapshot)
            .join(
                Project,
                and_(
                    Project.id == Entity.project_id,
                    tenant_scope_predicate(scope, Project.tenant_id),
                ),
            )
            .join(
                Snapshot,
                and_(
                    Snapshot.id == Entity.snapshot_id,
                    Snapshot.project_id == Entity.project_id,
                    tenant_scope_predicate(scope, Snapshot.tenant_id),
                ),
            )
            .where(
                or_(Entity.id == entity_id, Entity.identity_id == entity_id),
                tenant_scope_predicate(scope, Entity.tenant_id),
                Project.active_snapshot_id == Entity.snapshot_id,
            )
        ).first()
        if result is None:
            raise EntityContextNotFound(entity_id, scope.tenant_id)
        return result

    @classmethod
    def _load_relations(
        cls,
        session: Session,
        scope: TenantScope,
        snapshot_id,
        entity_id,
        limit: int,
        dependency_only: bool = False,
        direction: RelationshipDirection = RelationshipDirection.BOTH,
    ):
        source = aliased(Entity, name="source_entity")
        target = aliased(Entity, name="target_entity")
        source_match = Relation.source_entity_id == entity_id
        target_match = Relation.target_entity_id == entity_id
        if direction is RelationshipDirection.OUTBOUND:
            direction_match = source_match
        elif direction is RelationshipDirection.INBOUND:
            direction_match = target_match
        else:
            direction_match = or_(source_match, target_match)
        predicates = [
            tenant_scope_predicate(scope, Relation.tenant_id),
            Relation.snapshot_id == snapshot_id,
            direction_match,
            source.id == Relation.source_entity_id,
            source.snapshot_id == snapshot_id,
            tenant_scope_predicate(scope, source.tenant_id),
            target.id == Relation.target_entity_id,
            target.snapshot_id == snapshot_id,
            tenant_scope_predicate(scope, target.tenant_id),
        ]
        if dependency_only:
            predicates.append(Relation.relation_type.in_(cls._DEPENDENCY_TYPES))
        peer_key = case(
            (source_match, target.entity_key),
            else_=source.entity_key,
        )
        return session.execute(
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
            .where(*predicates)
            .order_by(Relation.relation_type.asc(), peer_key.asc(), Relation.id.asc())
            .limit(limit + 1)
        ).all()

    @staticmethod
    def _load_evidence(
        session: Session,
        scope: TenantScope,
        snapshot_id,
        rows,
        evidence_limit: int,
    ):
        if evidence_limit == 0 or not rows:
            return {}
        relation_ids = [row[0].id for row in rows]
        rank = (
            func.row_number()
            .over(
                partition_by=Evidence.relation_id,
                order_by=Evidence.id.asc(),
            )
            .label("evidence_rank")
        )
        ranked = (
            select(
                Evidence.id.label("id"),
                Evidence.relation_id.label("relation_id"),
                Evidence.source.label("source"),
                Evidence.excerpt.label("excerpt"),
                Evidence.metadata_json.label("metadata"),
                rank,
            )
            .where(
                tenant_scope_predicate(scope, Evidence.tenant_id),
                Evidence.snapshot_id == snapshot_id,
                Evidence.relation_id.in_(relation_ids),
            )
            .subquery()
        )
        evidence = defaultdict(list)
        result = session.execute(
            select(ranked)
            .where(ranked.c.evidence_rank <= evidence_limit)
            .order_by(ranked.c.relation_id.asc(), ranked.c.id.asc())
        ).mappings()
        for row in result:
            evidence[row["relation_id"]].append(
                EvidenceView(
                    id=row["id"],
                    source=row["source"],
                    excerpt=row["excerpt"],
                    metadata=row["metadata"] or {},
                )
            )
        return {relation_id: tuple(items) for relation_id, items in evidence.items()}

    @staticmethod
    def _map_entity(entity: Entity) -> EntityContextItem:
        return EntityContextItem(
            id=entity.identity_id or entity.id,
            identity_id=entity.identity_id or entity.id,
            key=entity.entity_key,
            name=entity.name,
            type=entity.entity_type,
            metadata=entity.metadata_json or {},
        )

    @classmethod
    def _map_relations(cls, rows, requested_entity_id, evidence):
        return tuple(
            RelationView(
                id=relation.id,
                type=relation.relation_type,
                direction=cls._direction(
                    requested_entity_id, relation.source_entity_id, relation.target_entity_id
                ),
                source=cls._map_entity(source),
                target=cls._map_entity(target),
                provenance=relation.provenance_kind,
                metadata=relation.metadata_json or {},
                evidence=evidence.get(relation.id, ()),
            )
            for relation, source, target in rows
        )

    @classmethod
    def _map_dependencies(cls, rows, requested_entity_id, evidence):
        return tuple(
            DependencyView(
                relation_id=relation.id,
                type=relation.relation_type,
                direction=cls._direction(
                    requested_entity_id, relation.source_entity_id, relation.target_entity_id
                ),
                peer=cls._map_entity(
                    target if relation.source_entity_id == requested_entity_id else source
                ),
                provenance=relation.provenance_kind,
                metadata=relation.metadata_json or {},
                evidence=evidence.get(relation.id, ()),
            )
            for relation, source, target in rows
        )

    @staticmethod
    def _direction(requested_entity_id, source_entity_id, target_entity_id):
        if source_entity_id == requested_entity_id and target_entity_id == requested_entity_id:
            return RelationshipDirection.BOTH
        if source_entity_id == requested_entity_id:
            return RelationshipDirection.OUTBOUND
        return RelationshipDirection.INBOUND
