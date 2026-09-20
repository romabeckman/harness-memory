from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from core.domain.snapshot_publication.errors.persistence_failure import PersistenceFailure
from core.infrastructure.postgres.repositories.snapshot_publication_repository import (
    PostgresSnapshotPublicationRepository,
)


def test_snapshot_publication_uses_read_committed_write_binding():
    engine = Mock()
    write_engine = Mock()
    engine.execution_options.return_value = write_engine

    PostgresSnapshotPublicationRepository(engine=engine)

    engine.execution_options.assert_called_once_with(isolation_level="READ COMMITTED")


def test_snapshot_publication_retries_serialization_failure():
    repository = PostgresSnapshotPublicationRepository(session_factory=lambda: None)
    serialization_origin = type("SerializationOrigin", (), {"pgcode": "40001"})()
    serialization_failure = OperationalError("serialization failure", {}, serialization_origin)
    successful_record = object()

    with patch.object(
        repository,
        "_publish_once",
        side_effect=[serialization_failure, successful_record],
    ) as publish_once:
        result = repository.publish_atomically("tenant-a", object(), "a" * 64)

    assert result is successful_record
    assert publish_once.call_count == 2


def test_snapshot_publication_retries_deadlock_failure():
    repository = PostgresSnapshotPublicationRepository(session_factory=lambda: None)
    deadlock_origin = type("DeadlockOrigin", (), {"pgcode": "40P01"})()
    deadlock = OperationalError("deadlock detected", {}, deadlock_origin)
    successful_record = object()

    with patch.object(
        repository,
        "_publish_once",
        side_effect=[deadlock, successful_record],
    ) as publish_once:
        result = repository.publish_atomically("tenant-a", object(), "a" * 64)

    assert result is successful_record
    assert publish_once.call_count == 2


def test_snapshot_publication_does_not_retry_non_unique_integrity_failure():
    repository = PostgresSnapshotPublicationRepository(session_factory=lambda: None)
    check_origin = type("CheckOrigin", (), {"pgcode": "23514"})()
    check_failure = IntegrityError("check constraint failed", {}, check_origin)

    with patch.object(repository, "_publish_once", side_effect=check_failure) as publish_once:
        with pytest.raises(PersistenceFailure):
            repository.publish_atomically("tenant-a", object(), "a" * 64)

    assert publish_once.call_count == 1
