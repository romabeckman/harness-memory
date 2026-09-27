from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, Uuid, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.project_link import ProjectLinkModel
from core.infrastructure.postgres.models.tenant import Tenant


def _sqlite_db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def test_project_link_model_table_metadata():
    table = ProjectLinkModel.__table__
    assert table.name == "project_links"
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key is True

    assert isinstance(table.c.project_a_id.type, Uuid)
    assert table.c.project_a_id.nullable is False

    assert isinstance(table.c.project_b_id.type, Uuid)
    assert table.c.project_b_id.nullable is False

    assert isinstance(table.c.created_by.type, Uuid)
    assert table.c.created_by.nullable is True

    assert any(
        isinstance(c, CheckConstraint)
        and "project_a_id" in str(c.sqltext)
        and "project_b_id" in str(c.sqltext)
        for c in table.constraints
    )

    assert any(
        isinstance(c, UniqueConstraint)
        and [col.name for col in c.columns] == ["project_a_id", "project_b_id"]
        for c in table.constraints
    )


def test_reject_duplicate_link_insertion_in_database():
    engine, session_factory = _sqlite_db()
    with session_factory() as session, session.begin():
        tenant = Tenant(
            id=uuid4(), key="tenant-1", name="Tenant 1", status="active", metadata_json={}
        )
        session.add(tenant)
        session.flush()
        p1 = Project(id=uuid4(), tenant_id=tenant.id, key="p1", name="Project 1")
        p2 = Project(id=uuid4(), tenant_id=tenant.id, key="p2", name="Project 2")
        session.add_all([p1, p2])
        session.flush()

        link1 = ProjectLinkModel(id=uuid4(), project_a_id=p1.id, project_b_id=p2.id)
        session.add(link1)
        session.flush()

        link2 = ProjectLinkModel(id=uuid4(), project_a_id=p1.id, project_b_id=p2.id)
        session.add(link2)
        with pytest.raises(IntegrityError):
            session.flush()


def test_reject_self_referential_link_in_database():
    engine, session_factory = _sqlite_db()
    with session_factory() as session, session.begin():
        tenant = Tenant(
            id=uuid4(), key="tenant-1", name="Tenant 1", status="active", metadata_json={}
        )
        session.add(tenant)
        session.flush()
        p1 = Project(id=uuid4(), tenant_id=tenant.id, key="p1", name="Project 1")
        session.add(p1)
        session.flush()

        link = ProjectLinkModel(id=uuid4(), project_a_id=p1.id, project_b_id=p1.id)
        session.add(link)
        with pytest.raises(IntegrityError):
            session.flush()


def test_project_deletion_cascades_to_project_links():
    engine, session_factory = _sqlite_db()
    with session_factory() as session, session.begin():
        tenant = Tenant(
            id=uuid4(), key="tenant-1", name="Tenant 1", status="active", metadata_json={}
        )
        session.add(tenant)
        session.flush()
        p1 = Project(id=uuid4(), tenant_id=tenant.id, key="p1", name="Project 1")
        p2 = Project(id=uuid4(), tenant_id=tenant.id, key="p2", name="Project 2")
        session.add_all([p1, p2])
        session.flush()

        link = ProjectLinkModel(id=uuid4(), project_a_id=p1.id, project_b_id=p2.id)
        session.add(link)
        session.flush()

        # Delete project p2
        session.delete(p2)
        session.flush()

        remaining_links = session.scalars(select(ProjectLinkModel)).all()
        assert len(remaining_links) == 0
