from uuid import uuid4

from sqlalchemy import select

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.integration_paths.types.path_termination_reason import PathTerminationReason
from core.infrastructure.postgres.models import Project, Relation
from core.infrastructure.postgres.repositories.integration_path_repository import (
    PostgresIntegrationPathRepository,
)

from .test_integration_path_traversal import _query, _repository, _seed


def test_repository_returns_at_most_max_paths_and_reports_path_truncation():
    session_factory = _repository()
    ids = _seed(session_factory)
    with session_factory() as session:
        active_snapshot = session.scalar(
            select(Project.active_snapshot_id).where(Project.tenant_id == "tenant-a")
        )
        parallel = Relation(
            id=uuid4(),
            tenant_id="tenant-a",
            snapshot_id=active_snapshot,
            source_entity_id=ids["source"],
            target_entity_id=ids["middle"],
            relation_type="depends_on",
            provenance_kind="declared",
            metadata_json={},
        )
        session.add(parallel)
        session.commit()
    result = PostgresIntegrationPathRepository(session_factory).find_paths(
        TenantScope("tenant-a"), _query(ids["source"], ids["middle"], max_paths=1)
    )
    assert len(result.paths) == 1
    assert result.truncated is True
    assert result.termination_reason is PathTerminationReason.PATH_LIMIT
