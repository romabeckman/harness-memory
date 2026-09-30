from sqlalchemy import Index

from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.relation import Relation


def test_integration_path_plan_indexes_cover_active_graph_and_context_lookups():
    entity_indexes = {index.name for index in Entity.__table__.indexes if isinstance(index, Index)}
    project_indexes = {
        index.name for index in Project.__table__.indexes if isinstance(index, Index)
    }
    relation_indexes = {
        index.name for index in Relation.__table__.indexes if isinstance(index, Index)
    }
    evidence_indexes = {
        index.name for index in Evidence.__table__.indexes if isinstance(index, Index)
    }
    assert {"ix_entities_snapshot_key", "ix_entities_project"} <= entity_indexes
    assert "ix_projects_tenant_active_snapshot" not in project_indexes
    assert "ix_environments_tenant_project_name" in {
        index.name for index in Environment.__table__.indexes
    }
    assert {"ix_relations_source", "ix_relations_target"} <= relation_indexes
    assert "ix_evidence_relation" in evidence_indexes
