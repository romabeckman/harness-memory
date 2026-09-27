from collections import defaultdict
from collections.abc import Callable

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.integration_paths.contracts.integration_path_view import IntegrationPathView
from core.application.integration_paths.contracts.ownership_view import OwnershipView
from core.application.integration_paths.contracts.path_entity_view import PathEntityView
from core.application.integration_paths.contracts.path_hop_view import PathHopView
from core.application.integration_paths.errors.integration_path_endpoint_not_found import (
    IntegrationPathEndpointNotFound,
)
from core.application.integration_paths.errors.integration_path_query_failure import (
    IntegrationPathQueryFailure,
)
from core.application.integration_paths.services.path_traversal_policy import PathTraversalPolicy
from core.application.integration_paths.types.path_termination_reason import PathTerminationReason
from core.application.integration_paths.types.path_traversal_direction import (
    PathTraversalDirection,
)
from core.application.integration_paths.use_cases.find_integration_paths.inbound import (
    FindIntegrationPathsInput,
)
from core.application.integration_paths.use_cases.find_integration_paths.outbound import (
    FindIntegrationPathsOutput,
)
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.relation_type import RelationType

from ..models.entity import Entity
from ..models.evidence import Evidence
from ..models.project import Project
from ..models.relation import Relation
from ..models.snapshot import Snapshot
from .tenant_scope_predicate import tenant_scope_predicate


class PostgresIntegrationPathRepository:
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
        self._policy = PathTraversalPolicy()

    def find_paths(
        self, scope: TenantScope, query: FindIntegrationPathsInput
    ) -> FindIntegrationPathsOutput:
        request = (
            query
            if isinstance(query, FindIntegrationPathsInput)
            else FindIntegrationPathsInput.model_validate(query)
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    source = self._resolve_endpoint(session, scope, request.source_entity_id)
                    target = self._resolve_endpoint(session, scope, request.target_entity_id)
                    entity_by_id = {source.id: source, target.id: target}
                    source_node_id = self._node_id(source)
                    target_node_id = self._node_id(target)

                    if source_node_id == target_node_id:
                        ordered_paths = (((source.id,), ()),)
                        expansion_limited = False
                    else:
                        raw_paths, expansion_limited, path_limited = self._load_recursive_paths(
                            session,
                            scope,
                            source_node_id,
                            target_node_id,
                            request.bounds.max_depth,
                            request.bounds.max_paths,
                        )
                        relation_ids = [
                            relation_id
                            for _, path_relation_ids in raw_paths
                            for relation_id in path_relation_ids
                        ]
                        if raw_paths:
                            rows = self._load_active_relations(session, scope, relation_ids)
                            entity_by_id.update(
                                {
                                    entity.id: entity
                                    for _, source_entity, target_entity in rows
                                    for entity in (source_entity, target_entity)
                                }
                            )
                            relation_by_id = {
                                relation.id: (relation, source_entity, target_entity)
                                for relation, source_entity, target_entity in rows
                            }
                            complete_paths = self._materialize_raw_paths(
                                raw_paths, relation_by_id, source.id
                            )
                            ordered_paths = self._order_raw_paths(complete_paths, entity_by_id)
                        else:
                            ordered_paths = ()

                    if source_node_id == target_node_id:
                        total_path_count = 1
                    else:
                        total_path_count = len(ordered_paths)
                    selected_paths = ordered_paths[: request.bounds.max_paths]

                    path_views = self._hydrate_paths(
                        session,
                        scope,
                        selected_paths,
                        entity_by_id,
                        request.bounds.evidence_limit,
                        request.bounds.owner_limit,
                    )
                    if expansion_limited:
                        truncated = True
                        termination_reason = PathTerminationReason.EXPANSION_LIMIT
                    elif source_node_id != target_node_id and (
                        path_limited or total_path_count > request.bounds.max_paths
                    ):
                        truncated = True
                        termination_reason = PathTerminationReason.PATH_LIMIT
                    else:
                        truncated = False
                        termination_reason = PathTerminationReason.COMPLETE
                    return FindIntegrationPathsOutput(
                        source=self._map_entity(source),
                        target=self._map_entity(target),
                        paths=path_views,
                        truncated=truncated,
                        termination_reason=termination_reason,
                    )
        except (IntegrationPathEndpointNotFound, IntegrationPathQueryFailure):
            raise
        except Exception as error:
            raise IntegrationPathQueryFailure(str(error)) from None

    def _resolve_endpoint(self, session: Session, scope: TenantScope, entity_id):
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
            raise IntegrationPathEndpointNotFound(entity_id, scope.tenant_id)
        return result[0]

    def _load_recursive_paths(
        self,
        session: Session,
        scope: TenantScope,
        source_id,
        target_id,
        max_depth: int,
        max_paths: int,
    ):
        frontier = [((source_id,), (), ())]
        completed = []
        expansions = 0
        expansion_limited = False

        for _depth in range(max_depth):
            frontier.sort(key=lambda path: (path[2], tuple(str(item) for item in path[1])))
            current_ids = tuple(dict.fromkeys(path[0][-1] for path in frontier))
            if not current_ids:
                break
            remaining = self._policy.max_expansions - expansions
            rows = session.execute(
                self._build_adjacent_relations_statement(
                    scope,
                    current_ids,
                    remaining + 1,
                    target_id,
                )
            ).all()
            rows_limited = len(rows) > remaining
            adjacency = defaultdict(list)
            for relation, relation_source, relation_target in rows:
                source_node_id = self._relation_node_id(relation, relation_source, "source")
                target_node_id = self._relation_node_id(relation, relation_target, "target")
                if source_node_id in current_ids:
                    adjacency[source_node_id].append(
                        (
                            relation_target.entity_key,
                            relation.id,
                            target_node_id,
                            relation_target.id,
                        )
                    )
                if target_node_id in current_ids:
                    adjacency[target_node_id].append(
                        (
                            relation_source.entity_key,
                            relation.id,
                            source_node_id,
                            relation_source.id,
                        )
                    )
            for candidates in adjacency.values():
                candidates.sort(
                    key=lambda item: (
                        item[2] != target_id,
                        item[0],
                        str(item[1]),
                    )
                )

            next_frontier = []
            stop = False
            for entity_ids, relation_ids, entity_keys in frontier:
                for next_key, relation_id, next_node_id, _ in adjacency.get(entity_ids[-1], ()):
                    if next_node_id in entity_ids:
                        continue
                    if expansions >= self._policy.max_expansions:
                        expansion_limited = True
                        stop = True
                        break
                    expansions += 1
                    next_path = (
                        (*entity_ids, next_node_id),
                        (*relation_ids, relation_id),
                        (*entity_keys, next_key),
                    )
                    if next_node_id == target_id:
                        completed.append(next_path)
                        if len(completed) > max_paths:
                            stop = True
                            break
                    else:
                        next_frontier.append(next_path)
                if stop:
                    break
            if rows_limited and not stop:
                expansion_limited = True
                stop = True
            if stop or not next_frontier:
                break
            frontier = next_frontier

        completed.sort(
            key=lambda path: (
                len(path[1]),
                path[2],
                tuple(str(item) for item in path[1]),
            )
        )
        raw_paths = tuple((path[0], path[1]) for path in completed[: max_paths + 1])
        return raw_paths, expansion_limited, len(completed) > max_paths

    @staticmethod
    def _build_adjacent_relations_statement(scope, current_ids, row_limit, target_id):
        relation_source = aliased(Entity, name="walk_source")
        relation_target = aliased(Entity, name="walk_target")
        relation_snapshot = aliased(Snapshot, name="walk_snapshot")
        relation_project = aliased(Project, name="walk_project")
        source_node_id = func.coalesce(
            Relation.source_identity_id,
            relation_source.identity_id,
            Relation.source_entity_id,
        )
        target_node_id = func.coalesce(
            Relation.target_identity_id,
            relation_target.identity_id,
            Relation.target_entity_id,
        )
        source_is_current = source_node_id.in_(current_ids)
        next_entity_key = case(
            (source_is_current, relation_target.entity_key),
            else_=relation_source.entity_key,
        )
        next_node_id = case(
            (source_is_current, target_node_id),
            else_=source_node_id,
        )
        target_rank = case((next_node_id == target_id, 0), else_=1)
        eligible_types = tuple(item.value for item in PathTraversalPolicy().eligible_types)
        return (
            select(Relation, relation_source, relation_target)
            .join(
                relation_snapshot,
                and_(
                    relation_snapshot.id == Relation.snapshot_id,
                    relation_snapshot.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                relation_project,
                and_(
                    relation_project.id == relation_snapshot.project_id,
                    relation_project.tenant_id == relation_snapshot.tenant_id,
                    relation_project.active_snapshot_id == relation_snapshot.id,
                ),
            )
            .join(
                relation_source,
                and_(
                    relation_source.id == Relation.source_entity_id,
                    relation_source.snapshot_id == Relation.snapshot_id,
                    relation_source.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                relation_target,
                and_(
                    relation_target.id == Relation.target_entity_id,
                    relation_target.snapshot_id == Relation.snapshot_id,
                    relation_target.tenant_id == Relation.tenant_id,
                ),
            )
            .where(
                tenant_scope_predicate(scope, Relation.tenant_id),
                Relation.relation_type.in_(eligible_types),
                or_(
                    source_node_id.in_(current_ids),
                    target_node_id.in_(current_ids),
                ),
            )
            .order_by(target_rank.asc(), next_entity_key.asc(), Relation.id.asc())
            .limit(row_limit)
        )

    @staticmethod
    def _materialize_raw_paths(raw_paths, relation_by_id, source_entity_id):
        paths = []
        for node_ids, relation_ids in raw_paths:
            hop_specs = []
            entity_ids = [source_entity_id]
            for index, relation_id in enumerate(relation_ids):
                relation, source, target = relation_by_id[relation_id]
                source_node_id = PostgresIntegrationPathRepository._relation_node_id(
                    relation, source, "source"
                )
                if source_node_id == node_ids[index]:
                    direction = PathTraversalDirection.OUTBOUND
                    entity_ids.append(target.id)
                else:
                    direction = PathTraversalDirection.INBOUND
                    entity_ids.append(source.id)
                hop_specs.append((relation, source, target, direction))
            paths.append((tuple(entity_ids), tuple(hop_specs)))
        return tuple(paths)

    @staticmethod
    def _relation_node_id(relation, entity, endpoint):
        identity_id = getattr(relation, f"{endpoint}_identity_id")
        return identity_id or entity.identity_id or entity.id

    @staticmethod
    def _node_id(entity):
        return entity.identity_id or entity.id

    def _load_active_relations(self, session: Session, scope: TenantScope, relation_ids=None):
        source = aliased(Entity, name="path_source")
        target = aliased(Entity, name="path_target")
        snapshot = aliased(Snapshot, name="path_snapshot")
        project = aliased(Project, name="path_project")
        eligible_types = tuple(item.value for item in RelationType if self._policy.eligible(item))
        return session.execute(
            select(Relation, source, target)
            .join(
                snapshot,
                and_(
                    snapshot.id == Relation.snapshot_id,
                    snapshot.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                project,
                and_(
                    project.id == snapshot.project_id,
                    project.tenant_id == snapshot.tenant_id,
                    project.active_snapshot_id == snapshot.id,
                ),
            )
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
                tenant_scope_predicate(scope, Relation.tenant_id),
                Relation.relation_type.in_(eligible_types),
                *([Relation.id.in_(tuple(relation_ids))] if relation_ids else []),
            )
            .order_by(Relation.id.asc())
        ).all()

    @staticmethod
    def _raw_path_sort_key(raw_path, entity_by_id):
        entity_ids, hop_specs = raw_path
        return (
            len(hop_specs),
            tuple(entity_by_id[entity_id].entity_key for entity_id in entity_ids),
            tuple(str(spec[0].id) for spec in hop_specs),
        )

    @classmethod
    def _order_raw_paths(cls, raw_paths, entity_by_id):
        unique = {tuple(spec[0].id for spec in path[1]): path for path in raw_paths}
        return tuple(
            sorted(unique.values(), key=lambda path: cls._raw_path_sort_key(path, entity_by_id))
        )

    def _hydrate_paths(
        self,
        session,
        scope,
        raw_paths,
        entity_by_id,
        evidence_limit,
        owner_limit,
    ):
        relation_ids = [spec[0].id for _, hop_specs in raw_paths for spec in hop_specs]
        path_entity_ids = {entity_id for entity_ids, _ in raw_paths for entity_id in entity_ids}
        path_entities = {entity_id: entity_by_id[entity_id] for entity_id in path_entity_ids}
        owner_rows = self._load_owner_rows(session, scope, path_entities, owner_limit)
        owner_relation_ids = [relation.id for relation, _, _ in owner_rows]
        evidence = self._load_evidence(
            session,
            scope,
            relation_ids + owner_relation_ids,
            evidence_limit,
        )
        owners_by_entity = defaultdict(list)
        for relation, _, target in owner_rows:
            owners_by_entity[relation.source_entity_id].append(
                OwnershipView(
                    relation_id=relation.id,
                    owner=self._map_entity(target),
                    provenance=relation.provenance_kind,
                    metadata=relation.metadata_json or {},
                    evidence=evidence.get(relation.id, ()),
                )
            )
        path_views = []
        for entity_ids, hop_specs in raw_paths:
            entities = tuple(
                PathEntityView(
                    entity=self._map_entity(entity_by_id[entity_id]),
                    owners=tuple(owners_by_entity.get(entity_id, ())),
                )
                for entity_id in entity_ids
            )
            hops = tuple(
                PathHopView(
                    relation_id=relation.id,
                    type=relation.relation_type,
                    source=self._map_entity(source),
                    target=self._map_entity(target),
                    traversal_direction=direction,
                    provenance=relation.provenance_kind,
                    metadata=relation.metadata_json or {},
                    evidence=evidence.get(relation.id, ()),
                )
                for relation, source, target, direction in hop_specs
            )
            path_views.append(
                IntegrationPathView(
                    entities=entities,
                    hops=hops,
                    hop_count=len(hops),
                )
            )
        return tuple(path_views)

    @staticmethod
    def _load_owner_rows(session, scope, entity_by_id, owner_limit):
        if owner_limit == 0 or not entity_by_id:
            return ()
        ranked_source = aliased(Entity, name="owner_rank_source")
        ranked_target = aliased(Entity, name="owner_rank_target")
        ranked_snapshot = aliased(Snapshot, name="owner_rank_snapshot")
        ranked_project = aliased(Project, name="owner_rank_project")
        owner_rank = (
            func.row_number()
            .over(
                partition_by=Relation.source_entity_id,
                order_by=(ranked_target.entity_key.asc(), Relation.id.asc()),
            )
            .label("owner_rank")
        )
        ranked_relation_ids = (
            select(
                Relation.id.label("relation_id"),
                owner_rank,
            )
            .join(
                ranked_snapshot,
                and_(
                    ranked_snapshot.id == Relation.snapshot_id,
                    ranked_snapshot.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                ranked_project,
                and_(
                    ranked_project.id == ranked_snapshot.project_id,
                    ranked_project.tenant_id == ranked_snapshot.tenant_id,
                    ranked_project.active_snapshot_id == ranked_snapshot.id,
                ),
            )
            .join(
                ranked_source,
                and_(
                    ranked_source.id == Relation.source_entity_id,
                    ranked_source.snapshot_id == Relation.snapshot_id,
                    ranked_source.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                ranked_target,
                and_(
                    ranked_target.id == Relation.target_entity_id,
                    ranked_target.snapshot_id == Relation.snapshot_id,
                    ranked_target.tenant_id == Relation.tenant_id,
                ),
            )
            .where(
                tenant_scope_predicate(scope, Relation.tenant_id),
                Relation.relation_type == RelationType.OWNED_BY.value,
                Relation.source_entity_id.in_(tuple(entity_by_id)),
                ranked_target.entity_type == EntityType.TEAM.value,
            )
            .subquery("ranked_owners")
        )
        source = aliased(Entity, name="owner_source")
        target = aliased(Entity, name="owner_target")
        return tuple(
            session.execute(
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
                .join(ranked_relation_ids, ranked_relation_ids.c.relation_id == Relation.id)
                .where(
                    tenant_scope_predicate(scope, Relation.tenant_id),
                    ranked_relation_ids.c.owner_rank <= owner_limit,
                )
                .order_by(
                    source.entity_key.asc(),
                    target.entity_key.asc(),
                    Relation.id.asc(),
                )
            ).all()
        )

    @staticmethod
    def _load_evidence(session, scope, relation_ids, evidence_limit):
        if evidence_limit == 0 or not relation_ids:
            return {}
        evidence_by_relation = defaultdict(list)
        evidence_rank = (
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
                evidence_rank,
            )
            .where(
                tenant_scope_predicate(scope, Evidence.tenant_id),
                Evidence.relation_id.in_(tuple(set(relation_ids))),
            )
            .subquery()
        )
        rows = session.execute(
            select(ranked)
            .where(ranked.c.evidence_rank <= evidence_limit)
            .order_by(ranked.c.relation_id.asc(), ranked.c.id.asc())
        ).mappings()
        for evidence in rows:
            evidence_by_relation[evidence["relation_id"]].append(
                EvidenceView(
                    id=evidence["id"],
                    source=evidence["source"],
                    excerpt=evidence["excerpt"],
                    metadata=evidence["metadata"] or {},
                )
            )
        return {relation_id: tuple(items) for relation_id, items in evidence_by_relation.items()}

    @staticmethod
    def _map_entity(entity) -> EntityContextItem:
        return EntityContextItem(
            id=entity.id,
            identity_id=entity.identity_id or entity.id,
            key=entity.entity_key,
            name=entity.name,
            type=entity.entity_type,
            metadata=entity.metadata_json or {},
        )
