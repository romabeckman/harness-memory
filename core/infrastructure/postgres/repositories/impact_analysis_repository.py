from collections import defaultdict
from collections.abc import Callable

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.impact_analysis.contracts.impact_consumer_view import ImpactConsumerView
from core.application.impact_analysis.errors.impact_entity_not_found import ImpactEntityNotFound
from core.application.impact_analysis.errors.impact_query_failure import ImpactQueryFailure
from core.application.impact_analysis.use_cases.analyze_impact.inbound import AnalyzeImpactInput
from core.application.impact_analysis.use_cases.analyze_impact.outbound import AnalyzeImpactOutput
from core.application.integration_paths.contracts.integration_path_view import IntegrationPathView
from core.application.integration_paths.contracts.ownership_view import OwnershipView
from core.application.integration_paths.contracts.path_entity_view import PathEntityView
from core.application.integration_paths.contracts.path_hop_view import PathHopView
from core.application.integration_paths.types.path_traversal_direction import PathTraversalDirection
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.relation_type import RelationType

from ..models.entity import Entity
from ..models.evidence import Evidence
from ..models.project import Project
from ..models.relation import Relation
from ..models.snapshot import Snapshot


class PostgresImpactAnalysisRepository:
    _MAX_AFFECTED_TEAMS = 100
    _MAX_IMPACT_OWNER_ROWS = 100
    _DEPENDENCY_TYPES = tuple(
        relation_type.value
        for relation_type in (
            RelationType.DEPENDS_ON,
            RelationType.CONSUMES,
            RelationType.SUBSCRIBES_TO,
        )
    )

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

    def analyze_impact(
        self, scope: TenantScope, query: AnalyzeImpactInput
    ) -> AnalyzeImpactOutput:
        request = (
            query
            if isinstance(query, AnalyzeImpactInput)
            else AnalyzeImpactInput.model_validate(query)
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    changed, changed_project, changed_snapshot = self._resolve_entity(
                        session, scope, request.entity_id
                    )
                    (
                        records,
                        entity_by_node,
                        project_by_node,
                        traversal_truncated,
                    ) = self._traverse(
                        session,
                        scope,
                        self._node_id(changed),
                        changed,
                        changed_project,
                        changed_snapshot,
                        request.bounds.max_depth,
                        request.bounds.max_consumers,
                    )
                    impacted_ids = tuple(record["node_id"] for record in records)
                    owner_rows = self._load_owner_rows(
                        session,
                        scope,
                        impacted_ids,
                        request.bounds.owner_limit,
                    )
                    owner_rows, owner_limit_truncated = self._trim_owner_rows(
                        owner_rows, request.bounds.owner_limit
                    )
                    owners_truncated = (
                        owner_limit_truncated
                        or len(owner_rows) > self._MAX_IMPACT_OWNER_ROWS
                    )
                    owner_rows = owner_rows[: self._MAX_IMPACT_OWNER_ROWS]
                    relation_ids = [
                        edge["relation"].id
                        for record in records
                        for edge in (*record["edges"], *record.get("context_edges", ()))
                    ]
                    owner_relation_ids = [row[0].id for row in owner_rows]
                    evidence, evidence_truncated = self._load_evidence(
                        session,
                        scope,
                        relation_ids + owner_relation_ids,
                        request.bounds.evidence_limit,
                        request.bounds.max_result_bytes // 3,
                    )
                    owners_by_entity = self._map_owners(owner_rows, evidence)
                    path_records = records[: request.bounds.max_paths]
                    paths = tuple(
                        self._map_path(record, entity_by_node, owners_by_entity, evidence)
                        for record in path_records
                    )
                    direct_consumers, indirect_consumers = self._map_consumers(
                        records,
                        project_by_node,
                        owners_by_entity,
                        evidence,
                    )
                    affected_projects = self._map_projects(
                        records, project_by_node
                    )
                    affected_teams, teams_truncated = self._map_teams(
                        owners_by_entity, impacted_ids
                    )
                    all_evidence = self._flatten_evidence(evidence)
                    truncated = (
                        traversal_truncated
                        or evidence_truncated
                        or owners_truncated
                        or teams_truncated
                        or len(records) > request.bounds.max_paths
                    )
                    unknowns = self._unknowns(
                        records,
                        relation_ids,
                        evidence,
                        truncated,
                        request.bounds.evidence_limit > 0,
                    )
                    output = AnalyzeImpactOutput(
                        changed_entity=self._map_entity(changed),
                        direct_consumers=direct_consumers,
                        indirect_consumers=indirect_consumers,
                        affected_projects=affected_projects,
                        affected_teams=affected_teams,
                        paths=paths,
                        evidence=all_evidence,
                        unknowns=unknowns,
                        truncated=truncated,
                    )
                    return self._fit_result_to_budget(output, request.bounds.max_result_bytes)
        except (ImpactEntityNotFound, ImpactQueryFailure):
            raise
        except Exception as error:
            raise ImpactQueryFailure(str(error)) from None

    @staticmethod
    def _resolve_entity(session, scope: TenantScope, entity_id):
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
            raise ImpactEntityNotFound(entity_id, scope.tenant_id)
        return result

    def _traverse(
        self,
        session,
        scope,
        changed_node_id,
        changed,
        changed_project,
        changed_snapshot,
        max_depth,
        max_consumers,
    ):
        entity_by_node = {changed_node_id: changed}
        project_by_node = {changed_node_id: (changed_project, changed_snapshot)}
        frontier = [(changed_node_id, (changed_node_id,), (), 0)]
        visited = {changed_node_id}
        records = []
        truncated = False

        while frontier:
            depth = frontier[0][3]
            current_ids = tuple(dict.fromkeys(item[0] for item in frontier))
            if depth >= max_depth:
                if self._has_unvisited_adjacent_relations(
                    session, scope, current_ids, visited
                ):
                    truncated = True
                break
            remaining = max_consumers - len(records)
            if remaining <= 0:
                if self._has_unvisited_adjacent_relations(session, scope, current_ids, visited):
                    truncated = True
                break
            rows = self._load_adjacent_relations(session, scope, current_ids, remaining + 1)
            adjacency = defaultdict(list)
            edges = tuple(self._graph_edge(row) for row in rows)
            for edge in edges:
                source_node_id = edge["source_node_id"]
                entity_by_node.setdefault(source_node_id, edge["source"])
                project_by_node.setdefault(
                    source_node_id, (edge["project"], edge["snapshot"])
                )
            for edge in edges:
                target_node_id = edge["target_node_id"]
                entity_by_node.setdefault(target_node_id, edge["target"])
                project_by_node.setdefault(
                    target_node_id, (edge["project"], edge["snapshot"])
                )
                adjacency[target_node_id].append(edge)
            for edges in adjacency.values():
                edges.sort(
                    key=lambda edge: (
                        edge["source"].entity_key,
                        str(edge["relation"].id),
                    )
                )

            candidate_groups = {}
            for current_id, entity_ids, path_edges, _ in frontier:
                for edge in adjacency.get(current_id, ()):
                    next_node_id = edge["source_node_id"]
                    if next_node_id in visited:
                        continue
                    group = candidate_groups.setdefault(
                        next_node_id,
                        {"entity_ids": entity_ids, "path_edges": path_edges, "edges": []},
                    )
                    group["edges"].append(edge)

            candidates = []
            for node_id, group in candidate_groups.items():
                group["edges"].sort(
                    key=lambda edge: (
                        edge["source"].entity_key,
                        str(edge["relation"].id),
                        edge["target"].entity_key,
                    )
                )
                candidates.append(
                    (
                        group["edges"][0],
                        group["entity_ids"],
                        group["path_edges"],
                        tuple(group["edges"]),
                    )
                )

            candidates.sort(
                key=lambda candidate: (
                    candidate[0]["source"].entity_key,
                    str(candidate[0]["relation"].id),
                    candidate[0]["target"].entity_key,
                )
            )
            unique_candidate_ids = tuple(
                dict.fromkeys(candidate[0]["source_node_id"] for candidate in candidates)
            )
            if len(unique_candidate_ids) > remaining:
                truncated = True
            elif len(rows) >= remaining + 1:
                known_nodes = (*visited, *unique_candidate_ids)
                if self._has_unvisited_adjacent_relations(session, scope, current_ids, known_nodes):
                    truncated = True
            next_frontier = []
            for edge, entity_ids, path_edges, context_edges in candidates:
                next_node_id = edge["source_node_id"]
                if next_node_id in visited:
                    continue
                if len(records) >= max_consumers:
                    truncated = True
                    continue
                visited.add(next_node_id)
                next_edges = (*path_edges, edge)
                record = {
                    "entity": edge["source"],
                    "node_id": next_node_id,
                    "entity_ids": (*entity_ids, next_node_id),
                    "edges": next_edges,
                    "context_edges": context_edges,
                    "project_contexts": tuple(
                        (context["project"], context["snapshot"]) for context in context_edges
                    ),
                    "depth": depth + 1,
                }
                records.append(record)
                next_frontier.append(
                    (next_node_id, (*entity_ids, next_node_id), next_edges, depth + 1)
                )
            frontier = next_frontier
        return records, entity_by_node, project_by_node, truncated

    def _load_adjacent_relations(self, session, scope, current_ids, row_limit):
        source = aliased(Entity, name="impact_source")
        target = aliased(Entity, name="impact_target")
        snapshot = aliased(Snapshot, name="impact_snapshot")
        project = aliased(Project, name="impact_project")
        target_node = (
            Relation.target_identity_id.in_(current_ids)
            | target.identity_id.in_(current_ids)
            | Relation.target_entity_id.in_(current_ids)
        )
        return session.execute(
            select(Relation, source, target, project, snapshot)
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
                Relation.relation_type.in_(self._DEPENDENCY_TYPES),
                target_node,
            )
            .order_by(source.entity_key.asc(), target.entity_key.asc(), Relation.id.asc())
            .limit(row_limit)
        ).all()

    @staticmethod
    def _has_unvisited_adjacent_relations(session, scope, current_ids, visited):
        source = aliased(Entity, name="impact_boundary_source")
        target = aliased(Entity, name="impact_boundary_target")
        snapshot = aliased(Snapshot, name="impact_boundary_snapshot")
        project = aliased(Project, name="impact_boundary_project")
        source_node = func.coalesce(
            Relation.source_identity_id,
            source.identity_id,
            Relation.source_entity_id,
        )
        target_node = func.coalesce(
            Relation.target_identity_id,
            target.identity_id,
            Relation.target_entity_id,
        )
        statement = (
            select(Relation.id)
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
                Relation.relation_type.in_(PostgresImpactAnalysisRepository._DEPENDENCY_TYPES),
                target_node.in_(current_ids),
                source_node.not_in(tuple(visited)),
            )
            .limit(1)
        )
        return session.execute(statement).first() is not None

    @staticmethod
    def _node_id(entity):
        return entity.identity_id or entity.id

    @classmethod
    def _graph_edge(cls, row):
        relation, source, target, project, snapshot = row
        return {
            "relation": relation,
            "source": source,
            "target": target,
            "source_node_id": relation.source_identity_id
            or source.identity_id
            or source.id,
            "target_node_id": relation.target_identity_id
            or target.identity_id
            or target.id,
            "project": project,
            "snapshot": snapshot,
        }

    @classmethod
    def _load_owner_rows(cls, session, scope, entity_ids, owner_limit):
        if owner_limit == 0 or not entity_ids:
            return ()
        rank_source = aliased(Entity, name="impact_owner_rank_source")
        rank_target = aliased(Entity, name="impact_owner_rank_target")
        rank_snapshot = aliased(Snapshot, name="impact_owner_rank_snapshot")
        rank_project = aliased(Project, name="impact_owner_rank_project")
        source_node = func.coalesce(
            Relation.source_identity_id,
            rank_source.identity_id,
            Relation.source_entity_id,
        )
        rank = func.row_number().over(
            partition_by=source_node,
            order_by=(
                rank_source.entity_key.asc(),
                rank_target.entity_key.asc(),
                Relation.id.asc(),
            ),
        ).label("impact_owner_rank")
        ranked = (
            select(Relation.id.label("relation_id"), rank)
            .join(
                rank_snapshot,
                and_(
                    rank_snapshot.id == Relation.snapshot_id,
                    rank_snapshot.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                rank_project,
                and_(
                    rank_project.id == rank_snapshot.project_id,
                    rank_project.tenant_id == rank_snapshot.tenant_id,
                    rank_project.active_snapshot_id == rank_snapshot.id,
                ),
            )
            .join(
                rank_source,
                and_(
                    rank_source.id == Relation.source_entity_id,
                    rank_source.snapshot_id == Relation.snapshot_id,
                    rank_source.tenant_id == Relation.tenant_id,
                ),
            )
            .join(
                rank_target,
                and_(
                    rank_target.id == Relation.target_entity_id,
                    rank_target.snapshot_id == Relation.snapshot_id,
                    rank_target.tenant_id == Relation.tenant_id,
                ),
            )
            .where(
                Relation.tenant_id == scope.tenant_id,
                (
                    Relation.source_entity_id.in_(entity_ids)
                    | Relation.source_identity_id.in_(entity_ids)
                    | rank_source.identity_id.in_(entity_ids)
                ),
                Relation.relation_type == RelationType.OWNED_BY.value,
                rank_target.entity_type == EntityType.TEAM.value,
            )
            .subquery("impact_ranked_owners")
        )
        source = aliased(Entity, name="impact_owner_source")
        target = aliased(Entity, name="impact_owner_target")
        snapshot = aliased(Snapshot, name="impact_owner_snapshot")
        project = aliased(Project, name="impact_owner_project")
        rows = session.execute(
            select(Relation, source, target, project, snapshot)
            .join(ranked, ranked.c.relation_id == Relation.id)
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
                Relation.relation_type == RelationType.OWNED_BY.value,
                target.entity_type == EntityType.TEAM.value,
                ranked.c.impact_owner_rank <= owner_limit + 1,
            )
            .order_by(source.entity_key.asc(), target.entity_key.asc(), Relation.id.asc())
            .limit(cls._MAX_IMPACT_OWNER_ROWS + len(entity_ids) + 1)
        ).all()
        return tuple(rows)

    @classmethod
    def _trim_owner_rows(cls, owner_rows, owner_limit):
        if owner_limit == 0:
            return (), False
        bounded = []
        counts = defaultdict(int)
        truncated = False
        for row in owner_rows:
            source_id = cls._node_id(row[1])
            if counts[source_id] >= owner_limit:
                truncated = True
                continue
            counts[source_id] += 1
            bounded.append(row)
        return tuple(bounded), truncated

    @staticmethod
    def _load_evidence(session, scope, relation_ids, evidence_limit, byte_budget):
        if evidence_limit == 0 or not relation_ids:
            return {}, False
        evidence = defaultdict(list)
        consumed = 0
        truncated = False
        for relation_id in dict.fromkeys(relation_ids):
            rows = session.execute(
                select(Evidence)
                .where(
                    Evidence.tenant_id == scope.tenant_id,
                    Evidence.relation_id == relation_id,
                )
                .order_by(Evidence.id.asc())
                .limit(evidence_limit + 1)
            ).scalars().all()
            if len(rows) > evidence_limit:
                truncated = True
            for row in rows[:evidence_limit]:
                item = EvidenceView(
                    id=row.id,
                    source=row.source,
                    excerpt=row.excerpt,
                    metadata=row.metadata_json or {},
                )
                item_bytes = len(item.model_dump_json().encode("utf-8"))
                if consumed + item_bytes > byte_budget:
                    return {key: tuple(items) for key, items in evidence.items()}, True
                evidence[relation_id].append(item)
                consumed += item_bytes
        return {relation_id: tuple(items) for relation_id, items in evidence.items()}, truncated

    @classmethod
    def _map_owners(cls, owner_rows, evidence):
        owners = defaultdict(list)
        for relation, source, target, _, _ in owner_rows:
            owners[cls._node_id(source)].append(
                OwnershipView(
                    relation_id=relation.id,
                    owner=cls._map_entity(target),
                    provenance=relation.provenance_kind,
                    metadata=relation.metadata_json or {},
                    evidence=evidence.get(relation.id, ()),
                )
            )
        return {entity_id: tuple(items) for entity_id, items in owners.items()}

    @classmethod
    def _map_path(cls, record, entity_by_id, owners_by_entity, evidence):
        entities = tuple(
            PathEntityView(
                entity=cls._map_entity(entity_by_id[entity_id]),
                owners=owners_by_entity.get(entity_id, ()),
            )
            for entity_id in record["entity_ids"]
        )
        hops = tuple(
            PathHopView(
                relation_id=edge["relation"].id,
                type=edge["relation"].relation_type,
                source=cls._map_entity(entity_by_id[edge["source_node_id"]]),
                target=cls._map_entity(entity_by_id[edge["target_node_id"]]),
                traversal_direction=PathTraversalDirection.INBOUND,
                provenance=edge["relation"].provenance_kind,
                metadata=edge["relation"].metadata_json or {},
                evidence=evidence.get(edge["relation"].id, ()),
            )
            for edge in record["edges"]
        )
        return IntegrationPathView(entities=entities, hops=hops, hop_count=len(hops))

    @classmethod
    def _map_consumers(cls, records, project_by_entity, owners_by_entity, evidence):
        direct = []
        indirect = []
        for record in records:
            final_edge = record["edges"][-1]
            consumer = record["entity"]
            consumer_evidence = tuple(
                item
                for edge in record["edges"]
                for item in evidence.get(edge["relation"].id, ())
            )
            view = ImpactConsumerView(
                entity=cls._map_entity(consumer),
                project=cls._map_project(project_by_entity[record["node_id"]]),
                depth=record["depth"],
                relation_id=final_edge["relation"].id,
                relation_type=final_edge["relation"].relation_type,
                provenance=final_edge["relation"].provenance_kind,
                metadata=final_edge["relation"].metadata_json or {},
                owners=tuple(
                    owner.owner
                    for owner in owners_by_entity.get(record["node_id"], ())
                ),
                evidence=consumer_evidence,
            )
            (direct if record["depth"] == 1 else indirect).append(view)
        return tuple(direct), tuple(indirect)

    @classmethod
    def _map_projects(cls, records, project_by_entity):
        projects = {}
        for record in records:
            contexts = record.get(
                "project_contexts", (project_by_entity[record["node_id"]],)
            )
            for project in contexts:
                projects[project[0].key] = cls._map_project(project)
        return tuple(projects[key] for key in sorted(projects))

    @classmethod
    def _map_teams(cls, owners_by_entity, impacted_ids):
        teams = {}
        for entity_id in impacted_ids:
            for owner in owners_by_entity.get(entity_id, ()):
                identity_id = owner.owner.identity_id or owner.owner.id
                teams[identity_id] = owner.owner
        ordered_teams = tuple(
            sorted(teams.values(), key=lambda team: (team.key, str(team.identity_id or team.id)))
        )
        return (
            ordered_teams[: cls._MAX_AFFECTED_TEAMS],
            len(ordered_teams) > cls._MAX_AFFECTED_TEAMS,
        )

    @staticmethod
    def _flatten_evidence(evidence):
        unique = {}
        for items in evidence.values():
            for item in items:
                unique[item.id] = item
        return tuple(sorted(unique.values(), key=lambda item: str(item.id)))

    @classmethod
    def _fit_result_to_budget(cls, output, byte_budget):
        def serialized_size(candidate):
            return len(candidate.model_dump_json().encode("utf-8"))

        def component_size_exceeds_budget(candidate):
            consumed = len(candidate.changed_entity.model_dump_json().encode("utf-8"))
            for field_name in (
                "direct_consumers",
                "indirect_consumers",
                "affected_projects",
                "affected_teams",
                "paths",
                "evidence",
            ):
                for item in getattr(candidate, field_name):
                    consumed += len(item.model_dump_json().encode("utf-8"))
                    if consumed > byte_budget:
                        return True
            consumed += sum(len(item.encode("utf-8")) for item in candidate.unknowns)
            return consumed > byte_budget

        if not component_size_exceeds_budget(output) and serialized_size(output) <= byte_budget:
            return output

        def without_entity_metadata(entity):
            return entity.model_copy(update={"metadata": {}})

        def without_consumer_details(consumer):
            return consumer.model_copy(
                update={
                    "entity": without_entity_metadata(consumer.entity),
                    "metadata": {},
                    "owners": tuple(without_entity_metadata(owner) for owner in consumer.owners),
                    "evidence": (),
                }
            )

        direct = tuple(without_consumer_details(item) for item in output.direct_consumers)
        indirect = tuple(without_consumer_details(item) for item in output.indirect_consumers)
        paths = tuple(
            path.model_copy(
                update={
                    "entities": tuple(
                        entity.model_copy(
                            update={
                                "entity": without_entity_metadata(entity.entity),
                                "owners": tuple(
                                    owner.model_copy(
                                        update={
                                            "owner": without_entity_metadata(owner.owner),
                                            "metadata": {},
                                            "evidence": (),
                                        }
                                    )
                                    for owner in entity.owners
                                ),
                            }
                        )
                        for entity in path.entities
                    ),
                    "hops": tuple(
                        hop.model_copy(
                            update={
                                "source": without_entity_metadata(hop.source),
                                "target": without_entity_metadata(hop.target),
                                "metadata": {},
                                "evidence": (),
                            }
                        )
                        for hop in path.hops
                    ),
                }
            )
            for path in output.paths
        )
        byte_unknown = "Impact result was truncated by byte bounds."
        bounded = output.model_copy(
            update={
                "changed_entity": without_entity_metadata(output.changed_entity),
                "direct_consumers": direct,
                "indirect_consumers": indirect,
                "paths": paths,
                "affected_teams": tuple(
                    without_entity_metadata(team) for team in output.affected_teams
                ),
                "evidence": (),
                "truncated": True,
                "unknowns": tuple(dict.fromkeys((*output.unknowns, byte_unknown))),
            }
        )

        def trim_collection(candidate, field_name):
            items = getattr(candidate, field_name)
            lower_bound = 0
            upper_bound = len(items)
            while lower_bound < upper_bound:
                retained_count = (lower_bound + upper_bound + 1) // 2
                trial = candidate.model_copy(update={field_name: items[:retained_count]})
                if serialized_size(trial) <= byte_budget:
                    lower_bound = retained_count
                else:
                    upper_bound = retained_count - 1
            return candidate.model_copy(update={field_name: items[:lower_bound]})

        for field_name in (
            "indirect_consumers",
            "direct_consumers",
            "paths",
            "affected_teams",
            "affected_projects",
        ):
            while serialized_size(bounded) > byte_budget:
                items = getattr(bounded, field_name)
                if not items:
                    break
                trimmed = trim_collection(bounded, field_name)
                if len(getattr(trimmed, field_name)) == len(items):
                    break
                bounded = trimmed

        if serialized_size(bounded) > byte_budget:
            bounded = output.__class__(
                changed_entity=without_entity_metadata(output.changed_entity),
                truncated=True,
                unknowns=tuple(dict.fromkeys((*output.unknowns, byte_unknown))),
            )
            if serialized_size(bounded) > byte_budget:
                raise ImpactQueryFailure("minimum impact response exceeds byte budget")
        return bounded

    @staticmethod
    def _unknowns(records, relation_ids, evidence, truncated, evidence_requested):
        unknowns = []
        if not records:
            unknowns.append("No known consumers were found in the active graph.")
        if evidence_requested and relation_ids and any(
            relation_id not in evidence for relation_id in relation_ids
        ):
            unknowns.append("Some impacted relationships have no linked evidence.")
        if truncated:
            unknowns.append("Impact result was truncated by query or response bounds.")
        return tuple(unknowns)

    @staticmethod
    def _map_entity(entity):
        return EntityContextItem(
            id=entity.id,
            identity_id=entity.identity_id or entity.id,
            key=entity.entity_key,
            name=entity.name,
            type=entity.entity_type,
            metadata=entity.metadata_json or {},
        )

    @staticmethod
    def _map_project(project):
        if isinstance(project, tuple):
            project, snapshot = project
        else:
            snapshot = None
        return ProjectContextItem(
            key=project.key,
            name=project.name,
            snapshot_id=snapshot.id if snapshot is not None else project.active_snapshot_id,
            revision=snapshot.revision
            if snapshot is not None
            else 1,
        )


ImpactAnalysisPostgresRepository = PostgresImpactAnalysisRepository
