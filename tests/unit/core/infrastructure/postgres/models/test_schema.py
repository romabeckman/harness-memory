from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.relation import Relation
from core.infrastructure.postgres.models.snapshot import Snapshot


def test_foundation_metadata_contains_exactly_five_tables():
    assert set(Base.metadata.tables) == {
        "projects",
        "snapshots",
        "entities",
        "relations",
        "evidence",
    }


def test_project_and_snapshot_constraints_are_scoped_and_deferred():
    project = Project.__table__
    snapshot = Snapshot.__table__

    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"tenant_id", "key"}
        for constraint in project.constraints
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"tenant_id", "project_id", "revision"}
        for constraint in snapshot.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and constraint.deferrable is True
        and constraint.initially == "DEFERRED"
        for constraint in project.constraints
    )


def test_graph_fact_constraints_enforce_ownership_and_provenance():
    entity = Entity.__table__
    relation = Relation.__table__
    evidence = Evidence.__table__

    assert sum(isinstance(item, ForeignKeyConstraint) for item in relation.constraints) >= 3
    assert sum(isinstance(item, ForeignKeyConstraint) for item in evidence.constraints) >= 2
    assert any(isinstance(item, CheckConstraint) for item in relation.constraints)
    assert any(isinstance(item, Index) for item in entity.indexes)
