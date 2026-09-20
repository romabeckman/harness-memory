from sqlalchemy import Index

from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.relation import Relation


def test_relationship_query_indexes_cover_directional_and_evidence_lookups():
    relation_indexes = {
        index.name for index in Relation.__table__.indexes if isinstance(index, Index)
    }
    evidence_indexes = {
        index.name for index in Evidence.__table__.indexes if isinstance(index, Index)
    }

    assert {"ix_relations_source", "ix_relations_target"} <= relation_indexes
    assert "ix_evidence_relation" in evidence_indexes
