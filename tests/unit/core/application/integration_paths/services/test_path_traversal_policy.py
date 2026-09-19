from uuid import uuid4

from core.application.integration_paths.contracts.integration_path_view import IntegrationPathView
from core.application.integration_paths.contracts.path_entity_view import PathEntityView
from core.application.integration_paths.contracts.path_hop_view import PathHopView
from core.application.integration_paths.services.path_traversal_policy import PathTraversalPolicy
from core.application.integration_paths.types.path_traversal_direction import PathTraversalDirection
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType


def _entity(key):
    return EntityContextItem(id=uuid4(), key=key, type=EntityType.SERVICE)


def _path(keys, relation_ids):
    entities = [_entity(key) for key in keys]
    hops = tuple(
        PathHopView(
            relation_id=relation_id,
            type=RelationType.CONSUMES,
            source=entities[index],
            target=entities[index + 1],
            traversal_direction=PathTraversalDirection.OUTBOUND,
            provenance=ProvenanceKind.DECLARED,
        )
        for index, relation_id in enumerate(relation_ids)
    )
    return IntegrationPathView(
        entities=tuple(PathEntityView(entity=entity) for entity in entities),
        hops=hops,
        hop_count=len(hops),
    )


def test_policy_accepts_only_integration_relation_types():
    policy = PathTraversalPolicy()
    assert all(
        policy.eligible(relation_type)
        for relation_type in (
            RelationType.PROVIDES,
            RelationType.CONSUMES,
            RelationType.DEPENDS_ON,
            RelationType.PUBLISHES,
            RelationType.SUBSCRIBES_TO,
            RelationType.IMPLEMENTS,
        )
    )
    assert not policy.eligible(RelationType.OWNED_BY)
    assert not policy.eligible(RelationType.PART_OF)


def test_policy_keys_parallel_paths_by_ordered_relation_ids():
    first_id, second_id = uuid4(), uuid4()
    first = _path(["a", "b"], [first_id])
    second = _path(["a", "b"], [second_id])
    duplicate = _path(["x", "y"], [first_id])
    assert PathTraversalPolicy.path_key(first) != PathTraversalPolicy.path_key(second)
    assert PathTraversalPolicy.path_key(first) == PathTraversalPolicy.path_key(duplicate)


def test_policy_orders_by_hop_count_then_entity_keys_then_relation_ids():
    short = _path(["a", "z"], [uuid4()])
    same_length_later_key = _path(["b", "c"], [uuid4()])
    assert PathTraversalPolicy.ordering_key(short) < PathTraversalPolicy.ordering_key(
        same_length_later_key
    )
    assert PathTraversalPolicy().max_expansions == 10_000
