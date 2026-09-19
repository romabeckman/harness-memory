from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from core.application.snapshot_publication.types.publication_context import PublicationContext
from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
from core.domain.snapshot_publication.errors.stale_revision import StaleRevision
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.repositories.snapshot_publication_repository import (
    PostgresSnapshotPublicationRepository,
)
from tests.unit.core.application.snapshot_publication.helpers import valid_payload


def repository():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, PostgresSnapshotPublicationRepository(sessionmaker(bind=engine))


def test_repository_persists_immutable_graph_switches_pointer_and_is_idempotent():
    engine, store = repository()
    handler = PublishProjectSnapshotHandler(store)
    context = PublicationContext("tenant-a")
    first = handler.execute(PublishProjectSnapshotInput.model_validate(valid_payload()), context)
    retry = handler.execute(PublishProjectSnapshotInput.model_validate(valid_payload()), context)
    second = handler.execute(
        PublishProjectSnapshotInput.model_validate(valid_payload(revision=2)), context
    )

    assert first.status == "ACTIVATED"
    assert retry.status == "ALREADY_PUBLISHED"
    assert second.status == "ACTIVATED"
    with sessionmaker(bind=engine)() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 1
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 2
        assert (
            session.scalar(
                select(Project.active_snapshot_id).where(Project.tenant_id == "tenant-a")
            )
            == second.snapshot_id
        )
        assert session.scalar(select(func.count()).select_from(Entity)) == 2


def test_repository_rejects_divergent_and_stale_publications_without_new_rows():
    engine, store = repository()
    handler = PublishProjectSnapshotHandler(store)
    context = PublicationContext("tenant-a")
    handler.execute(PublishProjectSnapshotInput.model_validate(valid_payload(revision=5)), context)

    with __import__("pytest").raises(RevisionConflict):
        handler.execute(
            PublishProjectSnapshotInput.model_validate(
                valid_payload(
                    revision=5, project={"key": "payments", "metadata": {"changed": True}}
                )
            ),
            context,
        )
    with __import__("pytest").raises(StaleRevision):
        handler.execute(
            PublishProjectSnapshotInput.model_validate(valid_payload(revision=3)), context
        )
    with sessionmaker(bind=engine)() as session:
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 1
