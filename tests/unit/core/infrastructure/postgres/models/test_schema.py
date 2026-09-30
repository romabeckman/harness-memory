from uuid import uuid4

import pytest
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.relation import Relation
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.models.tenant import Tenant


def test_metadata_contains_all_registered_tables():
    assert set(Base.metadata.tables) == {
        "projects",
        "project_links",
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


def test_project_key_is_global_and_current_snapshot_is_environment_owned():
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
    assert "active_snapshot_id" not in project.columns
    assert "payload" not in snapshot.columns
    assert {"project_key", "project_name", "generated_at"} <= set(snapshot.columns.keys())


def test_project_current_snapshot_is_derived_from_environment():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        tenant_id = uuid4()
        tenant = Tenant(id=tenant_id, key="test", name="Test")
        project = Project(tenant_id=tenant_id, key="project")
        session.add_all([tenant, project])
        session.flush()
        snapshot = Snapshot(
            tenant_id=tenant.id,
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        session.commit()

        assert (
            session.scalar(select(Project.active_snapshot_id).where(Project.id == project.id))
            == snapshot.id
        )
        assert project.environments[0].current_snapshot_id == snapshot.id
    engine.dispose()


def test_environment_current_snapshot_must_belong_to_its_project():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        tenant = Tenant(key="test", name="Test")
        session.add(tenant)
        session.flush()
        project_a = Project(tenant_id=tenant.id, key="a")
        project_b = Project(tenant_id=tenant.id, key="b")
        session.add_all([project_a, project_b])
        session.flush()
        own = Snapshot(
            tenant_id=tenant.id,
            project_id=project_a.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
        )
        other = Snapshot(
            tenant_id=tenant.id,
            project_id=project_b.id,
            revision=1,
            schema_version="1.0",
            payload_hash="b" * 64,
        )
        session.add_all([own, other])
        session.flush()
        environment = Environment(
            tenant_id=tenant.id,
            project_id=project_a.id,
            name="production",
            type="production",
            current_snapshot_id=own.id,
        )
        session.add(environment)
        session.commit()

        environment.current_snapshot_id = other.id
        with pytest.raises(IntegrityError):
            session.commit()
    engine.dispose()


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
        and [col.name for col in constraint.columns]
        == ["current_snapshot_id", "project_id", "tenant_id"]
        for constraint in env_table.constraints
    )
