from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.relation import Relation
from core.infrastructure.postgres.models.snapshot import Snapshot


def test_metadata_contains_all_registered_tables():
    assert set(Base.metadata.tables) == {
        "projects",
        "snapshots",
        "entities",
        "relations",
        "evidence",
        "users",
        "tokens",
        "service_accounts",
        "tenants",
        "environments",
        "knowledge_publications",
    }


def test_project_key_is_global_and_snapshot_constraints_are_scoped_and_deferred():
    project = Project.__table__
    snapshot = Snapshot.__table__

    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"key"}
        for constraint in project.constraints
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"tenant_id", "project_id", "environment_id", "revision"}
        for constraint in snapshot.constraints
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"tenant_id", "project_id", "environment_id", "payload_hash"}
        for constraint in snapshot.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and constraint.deferrable is True
        and constraint.initially == "DEFERRED"
        for constraint in project.constraints
    )
    assert "payload" not in snapshot.columns
    assert {"project_key", "project_name", "generated_at"} <= set(snapshot.columns.keys())


def test_normalized_graph_rows_keep_snapshot_payload_projection_fields():
    assert {"canonical_key", "graph_position"} <= set(Entity.__table__.columns.keys())
    assert {"relation_ref", "graph_position"} <= set(Relation.__table__.columns.keys())
    assert "graph_position" in Evidence.__table__.columns


def test_graph_fact_constraints_enforce_ownership_and_provenance():
    entity = Entity.__table__
    relation = Relation.__table__
    evidence = Evidence.__table__

    assert sum(isinstance(item, ForeignKeyConstraint) for item in relation.constraints) >= 3
    assert sum(isinstance(item, ForeignKeyConstraint) for item in evidence.constraints) >= 2
    assert any(isinstance(item, CheckConstraint) for item in relation.constraints)
    assert any(isinstance(item, Index) for item in entity.indexes)


def test_environment_and_publication_constraints():
    from core.infrastructure.postgres.models.environment import Environment
    from core.infrastructure.postgres.models.knowledge_publication import KnowledgePublication

    env_table = Environment.__table__
    pub_table = KnowledgePublication.__table__

    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"tenant_id", "project_id", "name"}
        for constraint in env_table.constraints
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"tenant_id", "project_id", "environment_id", "deployment_id"}
        for constraint in pub_table.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [col.name for col in constraint.columns] == ["current_snapshot_id", "tenant_id"]
        for constraint in env_table.constraints
    )
