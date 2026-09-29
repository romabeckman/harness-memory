from sqlalchemy import Index

from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.project import Project


def test_entity_search_models_declare_current_search_indexes():
    names = {index.name for index in Entity.__table__.indexes | Project.__table__.indexes}

    assert {
        "ix_entities_tenant_key_active_search",
        "ix_entities_tenant_type_active_search",
        "ix_entities_tenant_name_prefix_search",
    } <= names
    assert all(
        isinstance(index, Index) for index in Entity.__table__.indexes | Project.__table__.indexes
    )
