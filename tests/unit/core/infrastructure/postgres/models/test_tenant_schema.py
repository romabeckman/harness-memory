from uuid import UUID
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, Uuid

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.tenant import Tenant
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.relation import Relation
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.knowledge_publication import KnowledgePublication


def test_tenants_table_structure_and_constraints():
    table = Tenant.__table__
    assert table.name == "tenants"
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key is True

    assert str(table.c.key.type) == "VARCHAR(255)"
    assert table.c.key.nullable is False

    assert str(table.c.name.type) == "VARCHAR(255)"
    assert table.c.name.nullable is False

    assert str(table.c.status.type) == "VARCHAR(32)"
    assert table.c.status.nullable is False

    assert table.c.metadata.nullable is False

    assert any(
        isinstance(c, UniqueConstraint) and [col.name for col in c.columns] == ["key"]
        for c in table.constraints
    )


def test_all_tenant_scoped_tables_have_uuid_and_restrict_foreign_key_to_tenants():
    tables = [
        Project.__table__,
        Snapshot.__table__,
        Entity.__table__,
        Relation.__table__,
        Evidence.__table__,
        ApiUser.__table__,
        ApiServiceAccount.__table__,
        Environment.__table__,
        KnowledgePublication.__table__,
    ]

    for table in tables:
        tenant_col = table.c.tenant_id
        assert isinstance(
            tenant_col.type, Uuid
        ), f"Table {table.name}.tenant_id must be Uuid, got {tenant_col.type}"

        fk = next(
            (
                c
                for c in table.constraints
                if isinstance(c, ForeignKeyConstraint)
                and "tenant_id" in [col.name for col in c.columns]
                and any("tenants" in getattr(target, "_target_fullname", "") or "tenants" in getattr(target, "target_fullname", "") for target in c.elements)
            ),
            None,
        )
        assert fk is not None, f"Table {table.name} missing foreign key to tenants.id"
        assert (
            fk.ondelete == "RESTRICT"
        ), f"Table {table.name} fk to tenants must have ondelete='RESTRICT', got {fk.ondelete}"
