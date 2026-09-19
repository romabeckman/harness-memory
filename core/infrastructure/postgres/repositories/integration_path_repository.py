from collections import defaultdict
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import String, and_, case, cast, func, literal, or_, select, union_all
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

                    if source.id == target.id:
                        ordered_paths = (((source.id,), ()),)
                        expansion_limited = False
                    else:
                        raw_paths, expansion_limited, path_limited = self._load_recursive_paths(
                            session,
                            scope,
                            source.id,
                            target.id,
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
                            complete_paths = self._materialize_raw_paths(raw_paths, relation_by_id)
                            ordered_paths = self._order_raw_paths(complete_paths, entity_by_id)
                        else:
                            ordered_paths = ()

                    if source.id == target.id:
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
                    elif source.id != target.id and (
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
                    Project.tenant_id == scope.tenant_id,
                ),
            )
            .join(
                Snapshot,
                and_(
                    Snapshot.id == Entity.snapshot_id,
                    Snapshot.project_id == Entity.project_id,
                    Snapshot.tenant_id == scope.tenant_id,
                ),
            )
            .where(
                Entity.id == entity_id,
                Entity.tenant_id == scope.tenant_id,
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
        max_path_segments = 8
        start_snapshot = aliased(Snapshot, name="walk_start_snapshot")
        start_project = aliased(Project, name="walk_start_project")
        degree_snapshot = aliased(Snapshot, name="walk_degree_snapshot")
        degree_project = aliased(Project, name="walk_degree_project")
        active_edges = (
            select(
                Relation.source_entity_id.label("source_entity_id"),
                Relation.target_entity_id.label("target_entity_id"),
            )
            .join(
                degree_snapshot,
                and_(
                    degree_snapshot.id == Relation.snapshot_id,
                    degree_snapshot.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                degree_project,
                and_(
                    degree_project.id == degree_snapshot.project_id,
                    degree_project.tenant_id == degree_snapshot.tenant_id,
                    degree_project.active_snapshot_id == degree_snapshot.id,
                ),
            )
            .where(
                Relation.tenant_id == scope.tenant_id,
                Relation.relation_type.in_(
                    tuple(item.value for item in self._policy.eligible_types)
                ),
            )
            .cte("integration_path_edges")
        )
        edge_nodes = union_all(
            select(active_edges.c.source_entity_id.label("node_id")),
            select(active_edges.c.target_entity_id.label("node_id")),
        ).cte("integration_path_edge_nodes")
        edge_degrees = (
            select(
                edge_nodes.c.node_id,
                func.count().label("degree"),
            )
            .group_by(edge_nodes.c.node_id)
            .subquery("integration_path_edge_degrees")
        )
        walk = (
            select(
                Entity.id.label("current_entity_id"),
                cast(Entity.id, String).label("entity_path"),
                literal("", type_=String).label("relation_path"),
                literal(0).label("depth"),
                literal(1).label("expansion_count"),
                cast(Entity.entity_key, String).label("key_1"),
                *(
                    literal(None, type_=String).label(f"key_{index}")
                    for index in range(2, max_path_segments + 1)
                ),
                *(
                    literal(None, type_=Relation.id.type).label(f"relation_{index}")
                    for index in range(1, max_path_segments + 1)
                ),
            )
            .join(
                start_project,
                and_(
                    start_project.id == Entity.project_id,
                    start_project.tenant_id == scope.tenant_id,
                ),
            )
            .join(
                start_snapshot,
                and_(
                    start_snapshot.id == Entity.snapshot_id,
                    start_snapshot.project_id == Entity.project_id,
                    start_snapshot.tenant_id == scope.tenant_id,
                ),
            )
            .where(
                Entity.id == source_id,
                Entity.tenant_id == scope.tenant_id,
                start_project.active_snapshot_id == Entity.snapshot_id,
            )
            .cte("integration_path_walk", recursive=True)
        )
        current = walk.alias("current_walk")
        relation_source = aliased(Entity, name="walk_source")
        relation_target = aliased(Entity, name="walk_target")
        relation_snapshot = aliased(Snapshot, name="walk_snapshot")
        relation_project = aliased(Project, name="walk_project")
        next_entity_id = case(
            (Relation.source_entity_id == current.c.current_entity_id, relation_target.id),
            else_=relation_source.id,
        )
        next_entity_key = case(
            (
                Relation.source_entity_id == current.c.current_entity_id,
                relation_target.entity_key,
            ),
            else_=relation_source.entity_key,
        )
        visited_entities = literal(",") + current.c.entity_path + literal(",")
        next_entity_token = literal("%,") + cast(next_entity_id, String) + literal(",%")
        recursive_step = (
            select(
                next_entity_id.label("current_entity_id"),
                (current.c.entity_path + literal(",") + cast(next_entity_id, String)).label(
                    "entity_path"
                ),
                (current.c.relation_path + literal(",") + cast(Relation.id, String)).label(
                    "relation_path"
                ),
                (current.c.depth + 1).label("depth"),
                (current.c.expansion_count * edge_degrees.c.degree).label("expansion_count"),
                *(
                    case(
                        (current.c.depth == index - 1, next_entity_key),
                        else_=current.c[f"key_{index}"],
                    ).label(f"key_{index}")
                    for index in range(1, max_path_segments + 1)
                ),
                *(
                    case(
                        (current.c.depth == index - 1, Relation.id),
                        else_=current.c[f"relation_{index}"],
                    ).label(f"relation_{index}")
                    for index in range(1, max_path_segments + 1)
                ),
            )
            .select_from(current)
            .join(edge_degrees, edge_degrees.c.node_id == current.c.current_entity_id)
            .join(
                Relation,
                and_(
                    Relation.tenant_id == scope.tenant_id,
                    or_(
                        Relation.source_entity_id == current.c.current_entity_id,
                        Relation.target_entity_id == current.c.current_entity_id,
                    ),
                ),
            )
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
                Relation.relation_type.in_(
                    tuple(item.value for item in self._policy.eligible_types)
                ),
                current.c.current_entity_id != target_id,
                current.c.depth < max_depth,
                or_(
                    next_entity_id == target_id,
                    current.c.expansion_count * edge_degrees.c.degree
                    <= self._policy.max_expansions,
                ),
                ~visited_entities.like(next_entity_token),
            )
        )
        walk = walk.union_all(recursive_step)
        bounded_walk = select(walk).limit(self._policy.max_expansions + 1).cte(
            "integration_path_bounded_walk"
        )
        walk_order = (
            bounded_walk.c.depth.asc(),
            *(
                bounded_walk.c[f"key_{index}"].asc()
                for index in range(1, max_path_segments + 1)
            ),
            *(
                bounded_walk.c[f"relation_{index}"].asc()
                for index in range(1, max_path_segments + 1)
            ),
        )
        walk_rows = session.execute(
            select(bounded_walk)
            .order_by(
                *walk_order,
            )
        ).all()
        path_rows = session.execute(
            select(walk)
            .where(walk.c.current_entity_id == target_id)
            .order_by(
                walk.c.depth.asc(),
                *(walk.c[f"key_{index}"].asc() for index in range(1, max_path_segments + 1)),
                *(
                    walk.c[f"relation_{index}"].asc()
                    for index in range(1, max_path_segments + 1)
                ),
            )
            .limit(max_paths + 1)
        ).all()
        raw_paths = tuple(
            (
                tuple(UUID(part) for part in row.entity_path.split(",") if part),
                tuple(UUID(part) for part in row.relation_path.split(",") if part),
            )
            for row in path_rows
        )
        return (
            raw_paths,
            len(walk_rows) >= self._policy.max_expansions + 1,
            len(raw_paths) > max_paths,
        )

    @staticmethod
    def _materialize_raw_paths(raw_paths, relation_by_id):
        paths = []
        for entity_ids, relation_ids in raw_paths:
            hop_specs = []
            for index, relation_id in enumerate(relation_ids):
                relation, source, target = relation_by_id[relation_id]
                if source.id == entity_ids[index]:
                    direction = PathTraversalDirection.OUTBOUND
                else:
                    direction = PathTraversalDirection.INBOUND
                hop_specs.append((relation, source, target, direction))
            paths.append((entity_ids, tuple(hop_specs)))
        return tuple(paths)

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
                Relation.tenant_id == scope.tenant_id,
                Relation.relation_type.in_(eligible_types),
                *( 
                    [Relation.id.in_(tuple(relation_ids))]
                    if relation_ids
                    else []
                ),
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
            sorted(
                unique.values(), key=lambda path: cls._raw_path_sort_key(path, entity_by_id)
            )
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
        path_entity_ids = {
            entity_id for entity_ids, _ in raw_paths for entity_id in entity_ids
        }
        path_entities = {
            entity_id: entity_by_id[entity_id] for entity_id in path_entity_ids
        }
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
        owner_rank = func.row_number().over(
            partition_by=Relation.source_entity_id,
            order_by=(ranked_target.entity_key.asc(), Relation.id.asc()),
        ).label("owner_rank")
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
                Relation.tenant_id == scope.tenant_id,
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
                    Relation.tenant_id == scope.tenant_id,
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
        evidence_rank = func.row_number().over(
            partition_by=Evidence.relation_id,
            order_by=Evidence.id.asc(),
        ).label("evidence_rank")
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
                Evidence.tenant_id == scope.tenant_id,
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
            key=entity.entity_key,
            name=entity.name,
            type=entity.entity_type,
            metadata=entity.metadata_json or {},
        )
