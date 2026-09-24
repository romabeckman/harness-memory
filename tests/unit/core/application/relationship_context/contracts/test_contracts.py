from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.contracts.dependency_view import DependencyView
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.application.relationship_context.contracts.relation_view import RelationView
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.application.relationship_context.types.relationship_query_bounds import (
    RelationshipQueryBounds,
)
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from core.application.relationship_context.use_cases.get_context.outbound import GetContextOutput
from core.application.relationship_context.use_cases.get_dependencies.inbound import (
    GetDependenciesInput,
)
from core.application.relationship_context.use_cases.get_dependencies.outbound import (
    GetDependenciesOutput,
)
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType


def _entity(entity_type: EntityType = EntityType.SERVICE) -> EntityContextItem:
    return EntityContextItem(
        id=uuid4(), key="payments", name="Payments", type=entity_type, metadata={"tier": 1}
    )


def _evidence() -> EvidenceView:
    return EvidenceView(id=uuid4(), source="catalog.yaml", excerpt="declared", metadata={})


def _relation(entity: EntityContextItem) -> RelationView:
    return RelationView(
        id=uuid4(),
        type=RelationType.DEPENDS_ON,
        direction=RelationshipDirection.OUTBOUND,
        source=entity,
        target=_entity(EntityType.API),
        provenance=ProvenanceKind.DECLARED,
        metadata={"confidence": 1},
        evidence=(_evidence(), _evidence()),
    )


def test_relationship_bounds_accept_valid_limits_and_defaults():
    assert RelationshipQueryBounds(limit=25, evidence_limit=5).limit == 25
    assert RelationshipQueryBounds().evidence_limit == 5
    assert GetContextInput(entity_id=uuid4()).limit == 100
    assert GetContextInput(entity_id=uuid4(), limit=500).limit == 500
    assert GetContextInput(entity_id=uuid4()).result_limit == 25
    with pytest.raises(ValidationError):
        GetContextInput(entity_id=uuid4(), limit=501)
    with pytest.raises(ValidationError):
        GetContextInput(entity_id=uuid4(), result_limit=26)
    assert GetDependenciesInput(entity_id=uuid4()).direction is RelationshipDirection.BOTH


@pytest.mark.parametrize("selector", ["entity_id", "snapshot_id", "project_id", "tenant_id"])
def test_get_context_accepts_each_selector_on_its_own(selector):
    value = "tenant-a" if selector == "tenant_id" else uuid4()

    request = GetContextInput(**{selector: value})

    assert getattr(request, selector) == value


def test_get_context_requires_a_selector():
    with pytest.raises(ValidationError):
        GetContextInput()


@pytest.mark.parametrize("field,value", [("limit", 0), ("limit", 101)])
def test_relationship_contracts_reject_relation_limits_outside_range(field, value):
    with pytest.raises(ValidationError):
        RelationshipQueryBounds(**{field: value})


@pytest.mark.parametrize("field,value", [("evidence_limit", -1), ("evidence_limit", 21)])
def test_relationship_contracts_reject_evidence_limits_outside_range(field, value):
    with pytest.raises(ValidationError):
        GetContextInput(entity_id=uuid4(), **{field: value})


def test_relationship_contracts_reject_invalid_identity_direction_and_extra_fields():
    with pytest.raises(ValidationError):
        GetContextInput(entity_id="not-a-uuid")
    with pytest.raises(ValidationError):
        GetDependenciesInput(entity_id=uuid4(), direction="recursive")
    with pytest.raises(ValidationError):
        GetContextInput(entity_id=uuid4(), unknown_field="tenant-b")
    assert GetContextInput(entity_id=uuid4(), tenant_id="tenant-b").tenant_id == "tenant-b"


def test_relation_and_dependency_views_preserve_provenance_and_evidence():
    entity = _entity()
    relation = _relation(entity)
    dependency = DependencyView(
        relation_id=relation.id,
        type=relation.type,
        direction=relation.direction,
        peer=relation.target,
        provenance=relation.provenance,
        metadata=relation.metadata,
        evidence=relation.evidence,
    )

    assert relation.provenance is ProvenanceKind.DECLARED
    assert len(relation.evidence) == 2
    assert dependency.relation_id == relation.id
    assert dependency.evidence == relation.evidence


def test_relationship_outputs_are_immutable():
    entity = _entity()
    project = ProjectContextItem(key="payments", name="Payments", snapshot_id=uuid4(), revision=1)
    relation = _relation(entity)
    output = GetContextOutput(
        entity=entity,
        project=project,
        owners=(entity,),
        relations=(relation,),
        dependencies=(),
        relations_truncated=False,
        dependencies_truncated=False,
    )
    dependencies = GetDependenciesOutput(entity=entity, items=(), truncated=False)

    with pytest.raises(ValidationError):
        relation.id = uuid4()
    with pytest.raises(ValidationError):
        output.entity = entity
    with pytest.raises(ValidationError):
        dependencies.truncated = True


def test_tenant_scope_is_not_a_relationship_query_field():
    assert TenantScope("tenant-a").tenant_id == "tenant-a"
