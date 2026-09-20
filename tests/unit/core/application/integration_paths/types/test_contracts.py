from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.application.integration_paths.contracts.integration_path_view import IntegrationPathView
from core.application.integration_paths.contracts.ownership_view import OwnershipView
from core.application.integration_paths.contracts.path_entity_view import PathEntityView
from core.application.integration_paths.contracts.path_hop_view import PathHopView
from core.application.integration_paths.types.integration_path_bounds import IntegrationPathBounds
from core.application.integration_paths.types.path_termination_reason import PathTerminationReason
from core.application.integration_paths.types.path_traversal_direction import (
    PathTraversalDirection,
)
from core.application.integration_paths.use_cases.find_integration_paths.outbound import (
    FindIntegrationPathsOutput,
)
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType


def _entity(key: str = "service", entity_type: EntityType = EntityType.SERVICE):
    return EntityContextItem(id=uuid4(), key=key, name=key.title(), type=entity_type)


def _evidence():
    return EvidenceView(id=uuid4(), source="catalog.yaml", excerpt="fact")


def _owner(entity, relation_id=None):
    return OwnershipView(
        relation_id=relation_id or uuid4(),
        owner=entity,
        provenance=ProvenanceKind.DECLARED,
        metadata={"source": "catalog"},
        evidence=(_evidence(),),
    )


def _hop(source, target, relation_id=None):
    return PathHopView(
        relation_id=relation_id or uuid4(),
        type=RelationType.CONSUMES,
        source=source,
        target=target,
        traversal_direction=PathTraversalDirection.OUTBOUND,
        provenance=ProvenanceKind.OBSERVED,
        metadata={"confidence": 1},
        evidence=(_evidence(),),
    )


def test_bounds_accept_valid_values_and_apply_defaults():
    bounds = IntegrationPathBounds()
    assert bounds == IntegrationPathBounds(
        max_depth=4, max_paths=10, evidence_limit=5, owner_limit=5
    )
    assert IntegrationPathBounds(max_depth=8, max_paths=25, evidence_limit=0, owner_limit=20)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_depth", 0),
        ("max_depth", 9),
        ("max_paths", 0),
        ("max_paths", 26),
        ("evidence_limit", -1),
        ("evidence_limit", 21),
        ("owner_limit", -1),
        ("owner_limit", 21),
    ],
)
def test_bounds_reject_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        IntegrationPathBounds(**{field: value})


def test_path_hop_retains_orientation_provenance_metadata_and_evidence():
    source = _entity("source")
    target = _entity("target", EntityType.API)
    hop = _hop(source, target)
    assert hop.source is source
    assert hop.target is target
    assert hop.traversal_direction is PathTraversalDirection.OUTBOUND
    assert hop.provenance is ProvenanceKind.OBSERVED
    assert hop.evidence[0].source == "catalog.yaml"


def test_path_rejects_inconsistent_entity_hop_cardinality():
    source = _entity("source")
    target = _entity("target")
    hop = _hop(source, target)
    with pytest.raises(ValidationError):
        IntegrationPathView(
            entities=(PathEntityView(entity=source), PathEntityView(entity=target)),
            hops=(hop, hop),
            hop_count=2,
        )
    with pytest.raises(ValidationError):
        IntegrationPathView(
            entities=(PathEntityView(entity=source), PathEntityView(entity=target)),
            hops=(hop,),
            hop_count=2,
        )


def test_path_accepts_zero_hop_and_explicit_ownership():
    entity = _entity()
    owner = _entity("platform-team", EntityType.TEAM)
    path = IntegrationPathView(
        entities=(PathEntityView(entity=entity, owners=(_owner(owner),)),),
        hops=(),
        hop_count=0,
    )
    assert path.hop_count == 0
    assert path.entities[0].owners[0].owner.type is EntityType.TEAM


def test_contracts_are_immutable():
    entity = _entity()
    bounds = IntegrationPathBounds()
    path = IntegrationPathView(entities=(PathEntityView(entity=entity),), hops=(), hop_count=0)
    output = FindIntegrationPathsOutput(
        source=entity,
        target=entity,
        paths=(path,),
        truncated=False,
        termination_reason=PathTerminationReason.COMPLETE,
    )
    with pytest.raises(ValidationError):
        bounds.max_depth = 8
    with pytest.raises(ValidationError):
        output.source = _entity("other")

