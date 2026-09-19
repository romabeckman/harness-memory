from datetime import datetime, timezone

import pytest

from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)
from core.domain.snapshot_publication.entities.entity_fact import EntityFact
from core.domain.snapshot_publication.entities.evidence_fact import EvidenceFact
from core.domain.snapshot_publication.entities.relation_fact import RelationFact
from core.domain.snapshot_publication.errors.snapshot_invariant_violation import (
    SnapshotInvariantViolation,
)
from core.domain.snapshot_publication.services.snapshot_builder import SnapshotBuilder
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType
from core.domain.snapshot_publication.value_objects.entity_key import EntityKey
from core.domain.snapshot_publication.value_objects.generated_at import GeneratedAt
from core.domain.snapshot_publication.value_objects.metadata_object import MetadataObject
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey
from core.domain.snapshot_publication.value_objects.relation_reference import RelationReference
from core.domain.snapshot_publication.value_objects.revision import Revision
from core.domain.snapshot_publication.value_objects.schema_version import SchemaVersion


def facts():
    entities = (
        EntityFact(EntityKey("service"), EntityType("service"), "Service", MetadataObject({})),
        EntityFact(EntityKey("api"), EntityType("api"), None, MetadataObject({})),
    )
    relations = (
        RelationFact(
            RelationReference("provides-api"),
            EntityKey("service"),
            RelationType("provides"),
            EntityKey("api"),
            ProvenanceKind("declared"),
            MetadataObject({}),
        ),
    )
    evidence = (
        EvidenceFact(
            "catalog.yaml",
            "service evidence",
            RelationReference("provides-api"),
            MetadataObject({}),
        ),
    )
    return entities, relations, evidence


def build(**changes):
    entities, relations, evidence = facts()
    values = {
        "schema_version": SchemaVersion("1.0"),
        "project_key": ProjectKey("payments"),
        "project_name": "Payments",
        "project_metadata": MetadataObject({}),
        "revision": Revision(1),
        "generated_at": GeneratedAt(datetime(2026, 9, 17, 12, tzinfo=timezone.utc)),
        "entities": entities,
        "relations": relations,
        "evidence": evidence,
    }
    values.update(changes)
    return ProjectKnowledgeSnapshot(**values)


def test_builder_creates_empty_and_populated_immutable_snapshots():
    empty = SnapshotBuilder().build(
        schema_version=SchemaVersion("1.0"),
        project_key=ProjectKey("empty"),
        project_name=None,
        project_metadata=MetadataObject({}),
        revision=Revision(1),
        generated_at=GeneratedAt(datetime(2026, 9, 17, 12, tzinfo=timezone.utc)),
        entities=(),
        relations=(),
        evidence=(),
    )
    populated = build()

    assert empty.entities == ()
    assert populated.relations[0].source_entity_key.value == "service"
    with pytest.raises((TypeError, AttributeError)):
        populated.revision = Revision(2)
    with pytest.raises(TypeError):
        populated.entities[0].metadata.value["x"] = 1


@pytest.mark.parametrize(
    "change",
    [
        {"entities": facts()[0] + (facts()[0][0],)},
        {
            "entities": (
                EntityFact(
                    EntityKey("service-a"),
                    EntityType("service"),
                    "Service A",
                    MetadataObject({}),
                    "shared-service",
                ),
                EntityFact(
                    EntityKey("service-b"),
                    EntityType("service"),
                    "Service B",
                    MetadataObject({}),
                    "shared-service",
                ),
            )
        },
        {"relations": facts()[1] + (facts()[1][0],)},
        {
            "relations": (
                RelationFact(
                    RelationReference("bad"),
                    EntityKey("missing"),
                    RelationType("provides"),
                    EntityKey("api"),
                    ProvenanceKind("declared"),
                    MetadataObject({}),
                ),
            )
        },
        {
            "evidence": (
                EvidenceFact("source", None, RelationReference("missing"), MetadataObject({})),
            )
        },
    ],
)
def test_builder_rejects_duplicate_or_unresolved_references(change):
    with pytest.raises(SnapshotInvariantViolation):
        build(**change)


def test_snapshot_level_evidence_is_allowed():
    snapshot = build(evidence=(EvidenceFact("README.md", None, None, MetadataObject({})),))

    assert snapshot.evidence[0].relation_reference is None


@pytest.mark.parametrize(
    "factory", [SchemaVersion, Revision, ProjectKey, EntityKey, RelationReference]
)
def test_value_objects_reject_invalid_values(factory):
    invalid = 2 if factory is SchemaVersion else (0 if factory is Revision else " " * 256)
    with pytest.raises(ValueError):
        factory(invalid)


def test_value_objects_normalize_time_and_reject_naive_time():
    assert GeneratedAt(datetime.fromisoformat("2026-09-17T08:00:00-04:00")).value == datetime(
        2026, 9, 17, 12, tzinfo=timezone.utc
    )
    with pytest.raises(ValueError):
        GeneratedAt(datetime(2026, 9, 17, 12))


def test_metadata_object_is_json_object_and_bounded():
    with pytest.raises(ValueError):
        MetadataObject([])
    with pytest.raises(ValueError):
        MetadataObject({"value": "x" * (64 * 1024)})
